"""
The calendar's backend (2026-10-22, docs/tasks/task-calendar.md): posting
times on a connection, the next free slot, a group create, and the feed.

What is worth more than the coverage:

1. Posting times are validated and kept on the connection; a slot that a
   live post already fills is not free, and the zone is the person's
   (`test_next_free_slot_skips_taken_and_reads_the_zone`).
2. A group press writes ALL rows or NONE: a refusal on the third account
   leaves nothing for the first two (`test_group_is_all_or_nothing`).
3. The feed reads the platform once a day and never twice, and never
   500s when the platform does not answer (`test_feed_caches_for_a_day`).
4. Every new route is the account's own.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import requests
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app.main import app
from src import accounts, db, outcomes, posts, render_assets, social_connections
from src.social import discord, instagram
from src.social.base import Connected, ConnectRefused

client = TestClient(app, follow_redirects=False)


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
    yield {"dsn": pg, "a": a, "b": b, "ua": ua, "ig": ig, "dc": dc}
    app.dependency_overrides.clear()


def _render(dsn, account_id, *, kind="video", url="https://media.example/clip.mp4"):
    with db.connect(dsn) as conn:
        row = conn.execute(
            "INSERT INTO generated_assets (created_at, generation_id, tool, model, media_kind, "
            "prompt, media_url, metadata_json, account_id) VALUES "
            "('2026-10-22', (SELECT COALESCE(MAX(generation_id), 0) + 1 FROM generated_assets), "
            "'fal', 'kling', %s, 'a shot', %s, %s, %s) RETURNING id",
            (kind, url, json.dumps({"seconds": 8.0}), account_id)).fetchone()
    return f"gen:{row['id']}"


def sign_in(user_id: str, account_id: int) -> None:
    client.cookies.set(auth_mod.SESSION_COOKIE, auth_mod._serializer().dumps({"uid": user_id}))
    app.dependency_overrides[auth_mod.current_account_id] = lambda: account_id


TIMES = {"tz": "America/New_York", "days": {"mon": ["09:00", "18:30"], "tue": ["09:00"],
                                             "wed": [], "thu": ["09:00", "18:30"], "fri": ["09:00"],
                                             "sat": [], "sun": []}}


# --------------------------------------------------------------------------
# posting times
# --------------------------------------------------------------------------

def test_posting_times_are_checked_and_kept_on_the_connection(env):
    a, dsn, ig = env["a"], env["dsn"], env["ig"]
    assert ig["posting_times"]["tz"] == "UTC"
    assert all(ig["posting_times"]["days"][d] == [] for d in social_connections.DAYS)
    got = social_connections.set_posting_times(a, ig["id"], TIMES, dsn=dsn)
    assert got["posting_times"]["days"]["mon"] == ["09:00", "18:30"]
    assert got["posting_times"]["tz"] == "America/New_York"
    # a sloppy time is normalised, a repeat dropped, the list sorted
    got = social_connections.set_posting_times(
        a, ig["id"], {"tz": "UTC", "days": {"mon": ["18:30", "9:00", "09:00"]}}, dsn=dsn)
    assert got["posting_times"]["days"]["mon"] == ["09:00", "18:30"]
    assert got["posting_times"]["days"]["sun"] == []
    with pytest.raises(ConnectRefused, match="not a time of day"):
        social_connections.set_posting_times(a, ig["id"], {"tz": "UTC", "days": {"mon": ["25:00"]}}, dsn=dsn)
    with pytest.raises(ConnectRefused, match="time zone"):
        social_connections.set_posting_times(a, ig["id"], {"tz": "Mars/Olympus", "days": {}}, dsn=dsn)
    # another account cannot set them
    with pytest.raises(ConnectRefused, match="No such connection"):
        social_connections.set_posting_times(env["b"], ig["id"], TIMES, dsn=dsn)
    # the channel's own meta survives
    assert social_connections.meta_of(a, ig["id"], dsn=dsn)["ig_user_id"] == "1784"


def test_next_free_slot_skips_taken_and_reads_the_zone(env):
    a, dsn, ig = env["a"], env["dsn"], env["ig"]
    # no times -> no slot
    assert posts.next_free_slot(a, ig["id"], after="2026-10-22T12:00:00Z", dsn=dsn) is None
    social_connections.set_posting_times(a, ig["id"], TIMES, dsn=dsn)
    # Thu 22 Oct 2026, noon UTC = 8 AM New York (EDT); the next time is Thu 9:00 NY = 13:00 UTC
    slot = posts.next_free_slot(a, ig["id"], after="2026-10-22T12:00:00Z", dsn=dsn)
    assert slot["publish_at"] == "2026-10-22T13:00:00+00:00"
    assert slot["tz"] == "America/New_York"
    # fill it (on ANY connection: a slot is a moment) and the next one is Thu 18:30 NY
    clip = _render(dsn, a)
    posts.create(a, connection_id=env["dc"]["id"], source_ref=clip, publish_at="2026-10-22T13:00:00Z", dsn=dsn)
    slot = posts.next_free_slot(a, ig["id"], after="2026-10-22T12:00:00Z", dsn=dsn)
    assert slot["publish_at"] == "2026-10-22T22:30:00+00:00"
    # a cancelled post frees its slot
    row = posts.create(a, connection_id=ig["id"], source_ref=clip, publish_at="2026-10-22T22:30:00Z", dsn=dsn)
    assert posts.next_free_slot(a, ig["id"], after="2026-10-22T12:00:00Z", dsn=dsn)["publish_at"] \
        == "2026-10-23T13:00:00+00:00"
    posts.set_state(a, row["id"], "cancelled", dsn=dsn)
    assert posts.next_free_slot(a, ig["id"], after="2026-10-22T12:00:00Z", dsn=dsn)["publish_at"] \
        == "2026-10-22T22:30:00+00:00"
    # a slot already in the past is never offered
    assert posts.next_free_slot(a, ig["id"], after="2026-10-22T23:00:00Z", dsn=dsn)["publish_at"] \
        == "2026-10-23T13:00:00+00:00"
    # the week's empty boxes (Thu 13:00 is taken by the Discord post; Thu 22:30 and Fri 13:00 are free)
    free = posts.free_slots(a, start="2026-10-22T04:00:00Z", end="2026-10-25T04:00:00Z", dsn=dsn)
    assert [s["publish_at"] for s in free] == ["2026-10-22T22:30:00+00:00", "2026-10-23T13:00:00+00:00"]
    assert free[0]["connection_id"] == ig["id"]


def test_slots_between_handles_dst_and_an_empty_week():
    times = {"tz": "America/New_York", "days": {"sun": ["09:00"]}}
    # the Sunday the clocks go back (2026-11-01): 9 AM NY is 14:00 UTC after the change
    got = posts.slots_between(times, datetime(2026, 10, 31, tzinfo=timezone.utc),
                              datetime(2026, 11, 2, tzinfo=timezone.utc))
    assert [d.isoformat() for d in got] == ["2026-11-01T14:00:00+00:00"]
    # a week before, 9 AM NY is 13:00 UTC
    got = posts.slots_between(times, datetime(2026, 10, 24, tzinfo=timezone.utc),
                              datetime(2026, 10, 26, tzinfo=timezone.utc))
    assert [d.isoformat() for d in got] == ["2026-10-25T13:00:00+00:00"]
    assert posts.slots_between({"tz": "UTC", "days": {}}, datetime(2026, 10, 24, tzinfo=timezone.utc),
                               datetime(2026, 10, 26, tzinfo=timezone.utc)) == []


# --------------------------------------------------------------------------
# a group press
# --------------------------------------------------------------------------

def test_group_is_all_or_nothing(env):
    a, dsn = env["a"], env["dsn"]
    clip = _render(dsn, a)
    # a bad third account: nothing is written for the good two
    with pytest.raises(posts.PostRefused, match="not connected"):
        posts.create_group(a, connection_ids=[env["ig"]["id"], env["dc"]["id"], 999],
                           source_ref=clip, caption="hi", publish_at="2026-10-23T13:00:00Z", dsn=dsn)
    assert posts.list_for(a, dsn=dsn) == []
    # a caption too long for ONE of them refuses the press, by name
    with pytest.raises(posts.PostRefused, match="Discord takes a caption of at most 2000"):
        posts.create_group(a, connection_ids=[env["ig"]["id"], env["dc"]["id"]],
                           source_ref=clip, caption="x" * 2100, dsn=dsn)
    assert posts.list_for(a, dsn=dsn) == []
    made = posts.create_group(a, connection_ids=[env["ig"]["id"], env["dc"]["id"], env["ig"]["id"]],
                              source_ref=clip, caption="for both",
                              captions={env["dc"]["id"]: "for the server"},
                              publish_at="2026-10-23T13:00:00Z", dsn=dsn)
    assert len(made) == 2                       # the repeat id counted once
    assert len({p["group_id"] for p in made}) == 1
    assert {p["caption"] for p in made} == {"for both", "for the server"}
    with pytest.raises(posts.PostRefused, match="at least one"):
        posts.create_group(a, connection_ids=[], source_ref=clip, dsn=dsn)


# --------------------------------------------------------------------------
# the feed
# --------------------------------------------------------------------------

def test_feed_caches_for_a_day(env, monkeypatch):
    a, dsn, ig = env["a"], env["dsn"], env["ig"]
    calls = []

    def fake_http(method, url, **kw):
        calls.append(url)
        return {"data": [
            {"id": "m1", "media_type": "VIDEO", "thumbnail_url": "https://cdn/x.jpg",
             "permalink": "https://instagram.com/p/m1", "timestamp": "2026-10-20T10:00:00+0000",
             "caption": "old one"},
            {"id": "m2", "media_type": "IMAGE", "media_url": "https://cdn/y.jpg",
             "permalink": "https://instagram.com/p/m2", "timestamp": "2026-10-19T10:00:00+0000"},
        ]}
    monkeypatch.setattr(instagram, "_http", fake_http)
    clip = _render(dsn, a)
    posts.create(a, connection_id=ig["id"], source_ref=clip, publish_at="2026-10-23T13:00:00Z", dsn=dsn)
    now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
    got = posts.feed(a, ig["id"], dsn=dsn, now=now)
    assert got["offered"] is True
    assert [m["id"] for m in got["recent"]] == ["m1", "m2"]
    assert got["recent"][0]["kind"] == "video" and got["recent"][0]["thumb"] == "https://cdn/x.jpg"
    assert len(got["posts"]) == 1
    assert len(calls) == 1
    # a second read inside the day comes from the row, not Instagram
    got = posts.feed(a, ig["id"], dsn=dsn, now=now)
    assert len(calls) == 1 and [m["id"] for m in got["recent"]] == ["m1", "m2"]
    # the cache never reaches a page
    assert "_feed_cache" not in social_connections.get(a, ig["id"], dsn=dsn)["meta"]
    # a day later Instagram is asked again; if it does not answer, the old cache stands
    monkeypatch.setattr(instagram, "_http", lambda *a_, **k: (_ for _ in ()).throw(requests.ConnectionError("down")))
    later = datetime(2026, 10, 23, 13, tzinfo=timezone.utc)
    got = posts.feed(a, ig["id"], dsn=dsn, now=later)
    assert [m["id"] for m in got["recent"]] == ["m1", "m2"]
    assert got["note"] == "Instagram did not answer for the feed"
    # Discord has no feed
    got = posts.feed(a, env["dc"]["id"], dsn=dsn)
    assert got["offered"] is False and got["recent"] == []
    # a platform post we already released is not shown twice
    with db.connect(dsn) as conn:
        conn.execute("UPDATE posts SET state = 'published', release_id = 'm1' WHERE account_id = %s", (a,))
    got = posts.feed(a, ig["id"], dsn=dsn, now=now)
    assert [m["id"] for m in got["recent"]] == ["m2"]


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

def test_routes_are_the_accounts_own(env, monkeypatch):
    a, dsn, ig = env["a"], env["dsn"], env["ig"]
    sign_in(env["ua"], a)
    r = client.put(f"/api/social/connections/{ig['id']}/posting-times", json=TIMES)
    assert r.status_code == 200, r.text
    assert r.json()["posting_times"]["days"]["mon"] == ["09:00", "18:30"]
    r = client.get(f"/api/social/connections/{ig['id']}/posting-times")
    assert r.json()["posting_times"]["tz"] == "America/New_York"
    r = client.put(f"/api/social/connections/{ig['id']}/posting-times",
                   json={"tz": "UTC", "days": {"mon": ["noon"]}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "connect_refused"

    r = client.get("/api/posts/next-slot", params={"connection_id": ig["id"], "after": "2026-10-22T12:00:00Z"})
    assert r.status_code == 200 and r.json()["slot"]["publish_at"] == "2026-10-22T13:00:00+00:00"
    r = client.get("/api/posts/free-slots", params={"start": "2026-10-22T04:00:00Z", "end": "2026-10-24T04:00:00Z"})
    assert r.status_code == 200 and len(r.json()["slots"]) == 3

    clip = _render(dsn, a)
    r = client.post("/api/posts/group", json={"connection_ids": [ig["id"], env["dc"]["id"]],
                                              "source": clip, "caption": "both",
                                              "publish_at": "2026-10-23T13:00:00Z"})
    assert r.status_code == 200, r.text
    assert len(r.json()["posts"]) == 2 and r.json()["group_id"]

    monkeypatch.setattr(instagram, "_http", lambda *a_, **k: {"data": []})
    r = client.get("/api/posts/feed", params={"connection_id": ig["id"]})
    assert r.status_code == 200 and r.json()["offered"] is True and len(r.json()["posts"]) == 1

    # another workspace sees none of it
    ub = accounts.create_user("b@example.com", claimed=True, dsn=dsn)
    accounts.add_member(env["b"], ub, dsn=dsn)
    sign_in(ub, env["b"])
    assert client.get(f"/api/social/connections/{ig['id']}/posting-times").status_code == 404
    assert client.get("/api/posts/next-slot", params={"connection_id": ig["id"]}).status_code == 400
    assert client.get("/api/posts/feed", params={"connection_id": ig["id"]}).status_code == 400
    assert client.get("/api/posts/free-slots", params={"start": "2026-10-22T04:00:00Z",
                                                        "end": "2026-10-24T04:00:00Z"}).json()["slots"] == []
