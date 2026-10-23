"""
Posts and the publish worker (src/posts.py, src/publish_worker.py,
app/post_routes.py, the post_* half of src/social/*).

What is worth more than the coverage:

1. A post is created only against a finished connection this account
   owns and a source it owns; the checks a 3am worker would fail on run
   at creation (`test_create_checks_everything_up_front`).
2. The worker claims a due row ONCE however many workers tick
   (`test_two_workers_never_send_the_same_post`), and a row being sent
   cannot be moved, edited, cancelled or deleted.
3. What is retried and what is not: a 5xx goes back to the queue with a
   backoff; the platform's no and a dead token are terminal at once.
4. A pending post (Instagram's container) is polled on its own schedule,
   finished once ready, and never published twice on a retry.
5. When a post lands, the audience loop sees it: a `videos` row with the
   concept, and a kept event on the render.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
import requests
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app.main import app
from src import accounts, db, outcomes, posts, publish_worker, render_assets, social_connections
from src.social import discord, instagram
from src.social.base import Connected, PostFailed, PostResult

client = TestClient(app, follow_redirects=False)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def env(pg, monkeypatch):
    accounts.init(pg)
    social_connections.init(pg)
    posts.init(pg)
    render_assets.init(pg)
    outcomes.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-for-real-use")
    monkeypatch.setenv("SOCIAL_TOKEN_SECRET", "vault-secret-for-tests")
    monkeypatch.setenv(discord.BOT_TOKEN_ENV, "bot-token-secret")
    social_connections._ready.clear()
    posts._ready.clear()
    client.cookies.clear()
    a = accounts.upsert_account("studio", "Studio", dsn=pg)
    b = accounts.upsert_account("other", "Other", dsn=pg)
    ua = accounts.create_user("a@example.com", claimed=True, dsn=pg)
    accounts.add_member(a, ua, dsn=pg)
    ig = social_connections.save(a, "instagram", Connected(
        external_id="1784", display_name="Phantra", handle="phantra.ai", access_token="IG-TOKEN",
        expires_in=50 * 86400, meta={"ig_user_id": "1784"}), dsn=pg)
    dc = social_connections.save(a, "discord", Connected(
        external_id="g1", display_name="HQ", access_token="T", pending="channel",
        meta={"guild_id": "g1", "guild_name": "HQ"}), dsn=pg)
    monkeypatch.setattr(discord, "options", lambda meta: [{"id": "c1", "label": "#showcase", "hint": ""}])
    dc = social_connections.pick(a, dc["id"], "c1", dsn=pg)
    # the file is a public https URL already, so no bucket upload is needed
    monkeypatch.setattr(publish_worker, "_fetchable", lambda media, account_id: media.get("media_url") or "")
    return {"dsn": pg, "a": a, "b": b, "ua": ua, "ig": ig, "dc": dc}


def _render(dsn, account_id, *, kind="video", url="https://media.example/clip.mp4",
            seconds=8.0, concept_id=None):
    with db.connect(dsn) as conn:
        row = conn.execute(
            "INSERT INTO generated_assets (created_at, generation_id, tool, model, media_kind, "
            "prompt, media_url, metadata_json, concept_id, account_id) VALUES "
            "('2026-10-22', (SELECT COALESCE(MAX(generation_id), 0) + 1 FROM generated_assets), "
            "'fal', 'kling', %s, 'a shot', %s, %s, %s, %s) RETURNING id",
            (kind, url, json.dumps({"seconds": seconds}), concept_id, account_id)).fetchone()
    return f"gen:{row['id']}"


def sign_in(user_id: str, account_id: int) -> None:
    client.cookies.set(auth_mod.SESSION_COOKIE, auth_mod._serializer().dumps({"uid": user_id}))
    app.dependency_overrides[auth_mod.current_account_id] = lambda: account_id


class HttpError(requests.RequestException):
    def __init__(self, status, text="no"):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


# --------------------------------------------------------------------------
# creating
# --------------------------------------------------------------------------

def test_create_checks_everything_up_front(env):
    a, dsn = env["a"], env["dsn"]
    clip = _render(dsn, a)
    # a connection that is not this account's
    with pytest.raises(posts.PostRefused, match="not connected to this workspace"):
        posts.create(env["b"], connection_id=env["ig"]["id"], source_ref=clip, dsn=dsn)
    # a source that is not this account's
    with pytest.raises(posts.PostRefused, match="no render"):
        posts.create(a, connection_id=env["ig"]["id"], source_ref="gen:999", dsn=dsn)
    # a caption past the platform's limit
    with pytest.raises(posts.PostRefused, match="at most 2200"):
        posts.create(a, connection_id=env["ig"]["id"], source_ref=clip, caption="x" * 2300, dsn=dsn)
    # a kind the platform cannot take
    sound = _render(dsn, a, kind="audio")
    with pytest.raises(posts.PostRefused, match="Instagram takes a video"):
        posts.create(a, connection_id=env["ig"]["id"], source_ref=sound, dsn=dsn)
    # a time that is not one
    with pytest.raises(posts.PostRefused, match="not a time"):
        posts.create(a, connection_id=env["ig"]["id"], source_ref=clip, publish_at="tomorrow-ish", dsn=dsn)
    # a URL is never a source
    with pytest.raises(posts.PostRefused, match="gen:<id>"):
        posts.create(a, connection_id=env["ig"]["id"], source_ref="https://x/y.mp4", dsn=dsn)
    # and the good one
    post = posts.create(a, connection_id=env["ig"]["id"], source_ref=clip, caption="hello",
                        publish_at="2026-10-23T14:00:00Z", dsn=dsn)
    assert post["state"] == "queued" and post["provider"] == "instagram"
    assert post["publish_at"] == "2026-10-23T14:00:00+00:00" and post["media"]["kind"] == "video"
    assert [e["event"] for e in posts.events(a, post["id"], dsn=dsn)] == ["created"]


def test_a_pending_connection_cannot_be_posted_to(env):
    pending = social_connections.save(env["a"], "discord", Connected(
        external_id="g2", display_name="Other server", access_token="T", pending="channel",
        meta={"guild_id": "g2"}), dsn=env["dsn"])
    clip = _render(env["dsn"], env["a"])
    with pytest.raises(posts.PostRefused, match="Finish connecting"):
        posts.create(env["a"], connection_id=pending["id"], source_ref=clip, dsn=env["dsn"])


def test_the_persons_moves(env):
    a, dsn = env["a"], env["dsn"]
    clip = _render(dsn, a)
    post = posts.create(a, connection_id=env["ig"]["id"], source_ref=clip, draft=True, dsn=dsn)
    assert post["state"] == "draft"
    assert posts.set_state(a, post["id"], "queued", dsn=dsn)["state"] == "queued"
    moved = posts.set_date(a, post["id"], "2026-11-01T09:00:00Z", dsn=dsn)
    assert moved["publish_at"].startswith("2026-11-01T09:00")
    assert posts.update(a, post["id"], caption="new words", dsn=dsn)["caption"] == "new words"
    assert posts.set_state(a, post["id"], "cancelled", dsn=dsn)["state"] == "cancelled"
    with pytest.raises(posts.PostRefused, match="cannot become"):
        posts.set_state(a, post["id"], "published", dsn=dsn)   # only the worker lands a post
    # the other account sees and moves nothing
    assert posts.list_for(env["b"], dsn=dsn) == []
    with pytest.raises(posts.PostRefused, match="No such post"):
        posts.set_date(env["b"], post["id"], "2026-11-01T09:00:00Z", dsn=dsn)
    assert posts.remove(a, post["id"], dsn=dsn) and posts.get(a, post["id"], dsn=dsn) is None


def test_the_calendar_read_is_a_window(env):
    a, dsn = env["a"], env["dsn"]
    clip = _render(dsn, a)
    for day in (20, 23, 27):
        posts.create(a, connection_id=env["ig"]["id"], source_ref=clip,
                     publish_at=f"2026-10-{day}T12:00:00Z", dsn=dsn)
    week = posts.list_for(a, start="2026-10-21T00:00:00Z", end="2026-10-28T00:00:00Z", dsn=dsn)
    assert [p["publish_at"][:10] for p in week] == ["2026-10-23", "2026-10-27"]
    assert len(posts.list_for(a, state="queued", dsn=dsn)) == 3


# --------------------------------------------------------------------------
# the worker
# --------------------------------------------------------------------------

def _due(env, connection, **over):
    clip = over.pop("clip", None) or _render(env["dsn"], env["a"], concept_id=over.pop("concept_id", None))
    return posts.create(env["a"], connection_id=connection["id"], source_ref=clip,
                        caption=over.pop("caption", "a clip"), publish_at=over.pop("publish_at", None),
                        dsn=env["dsn"], **over)


def test_a_due_discord_post_is_sent_once_and_recorded(env, monkeypatch):
    sent = []

    def fake(method, url, **kw):
        sent.append((url, kw.get("json")))
        return {"id": "m-1"}
    monkeypatch.setattr(discord, "_http", fake)
    monkeypatch.setattr(discord, "_attachment", lambda media: None)
    post = _due(env, env["dc"], caption="first post", concept_id=None)
    out = publish_worker.tick(env["dsn"])
    assert out["claimed"] == 1 and out["published"] == 1
    assert len(sent) == 1 and sent[0][0].endswith("/channels/c1/messages")
    assert "first post" in sent[0][1]["content"] and "https://media.example/clip.mp4" in sent[0][1]["content"]
    got = posts.get(env["a"], post["id"], dsn=env["dsn"])
    assert got["state"] == "published" and got["release_id"] == "m-1"
    assert got["release_url"] == "https://discord.com/channels/g1/c1/m-1"
    # ticking again sends nothing more
    assert publish_worker.tick(env["dsn"])["claimed"] == 0 and len(sent) == 1
    # and the audience loop has it
    with db.connect(env["dsn"]) as conn:
        video = conn.execute("SELECT platform, url, duration_s FROM videos WHERE id = %s AND account_id = %s",
                             (got["video_id"], env["a"])).fetchone()
    assert video["platform"] == "discord" and video["url"] == got["release_url"] and video["duration_s"] == 8.0
    with db.connect(env["dsn"]) as conn:
        kept = conn.execute("SELECT event FROM output_events WHERE account_id = %s", (env["a"],)).fetchall()
    assert [k["event"] for k in kept] == ["post"]


def test_a_post_in_the_future_waits(env, monkeypatch):
    monkeypatch.setattr(discord, "_http", lambda *a, **k: pytest.fail("must not send"))
    _due(env, env["dc"], publish_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat())
    assert publish_worker.tick(env["dsn"])["claimed"] == 0


def test_two_workers_never_send_the_same_post(env, monkeypatch):
    sent = []
    monkeypatch.setattr(discord, "_attachment", lambda media: None)
    monkeypatch.setattr(discord, "_http", lambda m, u, **k: (sent.append(u), {"id": "m"})[1])
    for _ in range(3):
        _due(env, env["dc"])
    now = datetime.now(timezone.utc)
    first = publish_worker._claim_due(None, "w1", now, env["dsn"])
    second = publish_worker._claim_due(None, "w2", now, env["dsn"])
    assert len(first) == 3 and second == []
    assert all(r["locked_by"] == "w1" and r["state"] == "publishing" for r in first)
    # a row being sent cannot be touched by the person
    row = first[0]
    for move in (lambda: posts.set_date(env["a"], row["id"], None, dsn=env["dsn"]),
                 lambda: posts.set_state(env["a"], row["id"], "cancelled", dsn=env["dsn"]),
                 lambda: posts.update(env["a"], row["id"], caption="x", dsn=env["dsn"]),
                 lambda: posts.remove(env["a"], row["id"], dsn=env["dsn"])):
        with pytest.raises(posts.PostRefused, match="being sent"):
            move()


def test_the_platforms_no_is_terminal_and_a_5xx_is_retried(env, monkeypatch):
    monkeypatch.setattr(discord, "_attachment", lambda media: None)

    def refuse(m, u, **k):
        raise HttpError(400, "Missing Access")
    monkeypatch.setattr(discord, "_http", refuse)
    post = _due(env, env["dc"])
    assert publish_worker.tick(env["dsn"])["error"] == 1
    got = posts.get(env["a"], post["id"], dsn=env["dsn"])
    assert got["state"] == "error" and "Discord refused" in got["error"] and "bot-token-secret" not in got["error"]

    def down(m, u, **k):
        raise HttpError(503, "upstream")
    monkeypatch.setattr(discord, "_http", down)
    again = _due(env, env["dc"])
    assert publish_worker.tick(env["dsn"])["retry"] == 1
    got = posts.get(env["a"], again["id"], dsn=env["dsn"])
    assert got["state"] == "queued" and got["attempts"] == 1 and "503" in got["error"]
    # not before its backoff
    assert publish_worker.tick(env["dsn"])["claimed"] == 0
    # ...and after MAX_ATTEMPTS, an error
    with db.connect(env["dsn"]) as conn:
        conn.execute("UPDATE posts SET attempts = %s, next_attempt_at = NULL WHERE id = %s AND account_id = %s",
                     (publish_worker.MAX_ATTEMPTS, again["id"], env["a"]))
    assert publish_worker.tick(env["dsn"])["error"] == 1
    assert "Gave up" in posts.get(env["a"], again["id"], dsn=env["dsn"])["error"]
    # the person can post again: back to the queue, attempts reset
    back = posts.set_state(env["a"], again["id"], "queued", dsn=env["dsn"])
    assert back["attempts"] == 0 and back["error"] is None


def test_a_dead_token_is_a_reconnect_not_a_retry(env, monkeypatch):
    monkeypatch.setattr(discord, "_http", lambda *a, **k: pytest.fail("must not send"))
    with db.connect(env["dsn"]) as conn:
        conn.execute("UPDATE social_connections SET refresh_needed = TRUE WHERE id = %s AND account_id = %s",
                     (env["dc"]["id"], env["a"]))
    post = _due(env, env["dc"])
    assert publish_worker.tick(env["dsn"])["error"] == 1
    assert "reconnected" in posts.get(env["a"], post["id"], dsn=env["dsn"])["error"]


def test_instagram_is_pending_then_finished_exactly_once(env, monkeypatch):
    calls = []
    status = {"code": "IN_PROGRESS"}

    def fake(method, url, **kw):
        calls.append((method, url.rsplit("/", 1)[-1], kw.get("data") or kw.get("params")))
        if url.endswith("/1784/media"):
            assert kw["data"]["media_type"] == "REELS" and kw["data"]["video_url"].startswith("https://")
            return {"id": "c-77"}
        if url.endswith("/c-77"):
            return {"status_code": status["code"]}
        if url.endswith("/media_publish"):
            return {"id": "18000"}
        if url.endswith("/18000"):
            return {"permalink": "https://www.instagram.com/reel/abc/"}
        raise AssertionError(url)
    monkeypatch.setattr(instagram, "_http", fake)
    post = _due(env, env["ig"], caption="reel")
    out = publish_worker.tick(env["dsn"])
    assert out["claimed"] == 1 and out["pending"] == 1
    got = posts.get(env["a"], post["id"], dsn=env["dsn"])
    assert got["state"] == "publishing" and got["pending"]
    # not polled before its time
    assert publish_worker.tick(env["dsn"])["polled"] == 0
    # polled once its time comes: still processing
    later = datetime.now(timezone.utc) + timedelta(seconds=publish_worker.PENDING_POLL_SECONDS + 1)
    out = publish_worker.tick(env["dsn"], now=later)
    assert out["polled"] == 1 and out["pending"] == 1
    # finished: publish, read the permalink, land
    status["code"] = "FINISHED"
    later2 = later + timedelta(seconds=publish_worker.PENDING_POLL_SECONDS + 1)
    out = publish_worker.tick(env["dsn"], now=later2)
    assert out["polled"] == 1 and out["published"] == 1
    got = posts.get(env["a"], post["id"], dsn=env["dsn"])
    assert got["state"] == "published" and got["release_id"] == "18000"
    assert got["release_url"] == "https://www.instagram.com/reel/abc/"
    assert [c[1] for c in calls] == ["media", "c-77", "c-77", "media_publish", "18000"]
    # a check after a finish never publishes again
    again = instagram.post_check("tok", {}, {"media_id": "18000", "permalink": "p"})
    assert again.status == "completed" and len(calls) == 5


def test_a_container_that_errors_is_terminal(env, monkeypatch):
    def fake(method, url, **kw):
        if url.endswith("/1784/media"):
            return {"id": "c-1"}
        return {"status_code": "ERROR", "status": "Media too long"}
    monkeypatch.setattr(instagram, "_http", fake)
    post = _due(env, env["ig"])
    publish_worker.tick(env["dsn"])
    later = datetime.now(timezone.utc) + timedelta(seconds=publish_worker.PENDING_POLL_SECONDS + 1)
    assert publish_worker.tick(env["dsn"], now=later)["error"] == 1
    assert "could not process" in posts.get(env["a"], post["id"], dsn=env["dsn"])["error"]


def test_a_pending_post_that_never_finishes_gives_up(env, monkeypatch):
    monkeypatch.setattr(instagram, "_http",
                        lambda m, u, **k: {"id": "c-1"} if u.endswith("/media") else {"status_code": "IN_PROGRESS"})
    post = _due(env, env["ig"])
    publish_worker.tick(env["dsn"])
    with db.connect(env["dsn"]) as conn:
        conn.execute("UPDATE posts SET pending_json = %s, next_attempt_at = NULL WHERE id = %s AND account_id = %s",
                     (json.dumps({"container_id": "c-1", "user_id": "1784",
                                  "since": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}),
                      post["id"], env["a"]))
    assert publish_worker.tick(env["dsn"])["error"] == 1
    assert "did not finish" in posts.get(env["a"], post["id"], dsn=env["dsn"])["error"]


def test_a_worker_that_died_mid_send_leaves_an_error_never_a_resend(env, monkeypatch):
    monkeypatch.setattr(discord, "_http", lambda *a, **k: pytest.fail("must not resend"))
    post = _due(env, env["dc"])
    stale = datetime.now(timezone.utc) - timedelta(seconds=posts.STUCK_SECONDS + 60)
    with db.connect(env["dsn"]) as conn:
        conn.execute("UPDATE posts SET state = 'publishing', locked_by = 'dead', locked_at = %s "
                     "WHERE id = %s AND account_id = %s", (stale, post["id"], env["a"]))
    out = publish_worker.tick(env["dsn"])
    assert out["stuck"] == 1 and out["claimed"] == 0
    got = posts.get(env["a"], post["id"], dsn=env["dsn"])
    assert got["state"] == "error" and "Check the platform" in got["error"]


def test_the_discord_provider_posts_the_file_when_it_fits(env, monkeypatch):
    seen = {}

    def fake_send(url, bot, *, data, files):
        seen.update(url=url, data=data, files=files)
        return {"id": "m-9"}
    monkeypatch.setattr(discord, "_send", fake_send)
    monkeypatch.setattr(discord, "_attachment", lambda media: ("clip.mp4", b"bytes", "video/mp4"))
    r = discord.post_start("T", {"guild_id": "g1", "channel_id": "c1"},
                           {"caption": "with file", "media": {"url": "https://x/clip.mp4", "kind": "video"}})
    assert r.status == "completed" and r.release_id == "m-9"
    assert seen["files"]["files[0]"][0] == "clip.mp4"
    assert json.loads(seen["data"]["payload_json"])["content"] == "with file"


def test_the_post_result_contract(env):
    r = PostResult(status="pending", pending={"x": 1})
    assert r.release_id == "" and r.pending == {"x": 1}
    with pytest.raises(PostFailed):
        discord.post_start("T", {"guild_id": "g1"}, {"caption": "no channel"})


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

def test_the_routes_are_one_accounts(env):
    clip = _render(env["dsn"], env["a"])
    sign_in(env["ua"], env["a"])
    made = client.post("/api/posts", json={"connection_id": env["ig"]["id"], "source": clip,
                                           "caption": "hi", "publish_at": "2026-10-23T14:00:00Z"})
    assert made.status_code == 200, made.text
    pid = made.json()["id"]
    assert client.get("/api/posts", params={"start": "2026-10-23", "end": "2026-10-24"}).json()["posts"][0]["id"] == pid
    one = client.get(f"/api/posts/{pid}").json()
    assert one["state"] == "queued" and one["events"][0]["event"] == "created"
    moved = client.put(f"/api/posts/{pid}/date", json={"publish_at": "2026-10-24T10:00:00Z"}).json()
    assert moved["publish_at"].startswith("2026-10-24")
    assert client.patch(f"/api/posts/{pid}", json={"caption": "edited"}).json()["caption"] == "edited"
    bad = client.post("/api/posts", json={"connection_id": env["ig"]["id"], "source": "gen:999"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "post_refused"
    # the other workspace
    sign_in(env["ua"], env["b"])
    assert client.get("/api/posts").json()["posts"] == []
    assert client.get(f"/api/posts/{pid}").status_code == 404
    assert client.delete(f"/api/posts/{pid}").status_code == 404
    sign_in(env["ua"], env["a"])
    assert client.post(f"/api/posts/{pid}/state", json={"state": "cancelled"}).json()["state"] == "cancelled"
    assert client.delete(f"/api/posts/{pid}").status_code == 200
