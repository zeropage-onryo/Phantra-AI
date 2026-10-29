"""
Reddit and LinkedIn (src/social/reddit.py, src/social/linkedin.py,
2026-10-22, docs/tasks/task-social-providers.md), and the per-platform
form a group press carries (posts.create_group(settings_by=...)).

What is worth more than the coverage:

1. Each connect refuses a grant that cannot post (Reddit without
   `submit`, LinkedIn without `w_member_social`) rather than storing a
   channel that lies (`test_*_authenticate`).
2. Reddit's refusal words reach the row: a sub that requires flair says
   so in the error, and a title is the words (`test_reddit_post`).
3. A LinkedIn video is three calls across two ticks and never posts
   twice (`test_linkedin_video_is_pending_then_posted`).
4. A group press carries one platform's own settings per connection,
   and a missing subreddit refuses the whole press before any row is
   written (`test_group_settings_by`).
"""
from __future__ import annotations

import json

import pytest
import requests

from src import accounts, db, outcomes, posts, render_assets, social, social_connections
from src.social import discord, linkedin, reddit
from src.social.base import Connected, ConnectRefused, PostFailed


class HttpError(requests.RequestException):
    def __init__(self, status, text="no"):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


class FakeResponse:
    def __init__(self, headers=None, body=None):
        self.headers = headers or {}
        self._body = body or {}

    def json(self):
        return self._body


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------

def test_catalogue_lists_both_with_their_forms(monkeypatch):
    monkeypatch.delenv(reddit.CLIENT_ID_ENV, raising=False)
    cat = {p["id"]: p for p in social.catalogue()}
    assert cat["reddit"]["configured"] is False
    assert [f["key"] for f in cat["reddit"]["settings"]] == ["subreddit", "flair_id", "nsfw"]
    assert cat["reddit"]["settings"][0]["required"] is True
    assert cat["reddit"]["caption_max"] == 300
    assert cat["linkedin"]["settings"][0]["key"] == "visibility"
    assert cat["instagram"]["settings"][0]["key"] == "post_type"
    assert cat["instagram"]["feed"] is True and cat["discord"]["feed"] is False
    assert social.get("reddit") is reddit and social.get("linkedin") is linkedin


# --------------------------------------------------------------------------
# Reddit
# --------------------------------------------------------------------------

@pytest.fixture
def reddit_env(monkeypatch):
    monkeypatch.setenv(reddit.CLIENT_ID_ENV, "rid")
    monkeypatch.setenv(reddit.CLIENT_SECRET_ENV, "rsecret")


def test_reddit_auth_url_and_authenticate(reddit_env, monkeypatch):
    url = reddit.auth_url("https://api.phantra.ai/auth/social/reddit/callback", "st")
    assert url.startswith(reddit.AUTHORIZE_URL) and "duration=permanent" in url and "submit" in url
    calls = []

    def fake(method, url, **kw):
        calls.append((method, url, kw))
        if url == reddit.TOKEN_URL:
            assert kw["headers"]["Authorization"].startswith("Basic ")
            assert kw["headers"]["User-Agent"] == reddit.USER_AGENT
            return {"access_token": "A", "refresh_token": "R", "expires_in": 3600,
                    "scope": "identity submit read flair mysubreddits"}
        if url.endswith("/api/v1/me"):
            return {"id": "u1", "name": "mike", "icon_img": "https://img/a.png?x=1"}
        raise AssertionError(url)
    monkeypatch.setattr(reddit, "_http", fake)
    found = reddit.authenticate("code", "https://cb", {})
    assert found.display_name == "u/mike" and found.handle == "mike" and found.external_id == "u1"
    assert found.refresh_token == "R" and found.expires_in == 3600 and found.avatar_url == "https://img/a.png"
    assert reddit.display_label(found.meta) == "u/mike"
    # a grant without submit is refused
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: {"access_token": "A", "scope": "identity"})
    with pytest.raises(ConnectRefused, match="posting"):
        reddit.authenticate("code", "https://cb", {})
    # the refresh keeps the refresh token when Reddit does not send a new one
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: {"access_token": "A2", "expires_in": 3600})
    renewed = reddit.refresh("A", "R")
    assert renewed.access_token == "A2" and renewed.refresh_token == "R"
    assert reddit.refresh("A", "") is None


def _rpost(sub="a"):
    return {"caption": "t", "media": {"url": "https://m/x.mp4"}, "settings": {"subreddit": sub}}


def test_reddit_post(reddit_env, monkeypatch):
    src = {"kind": "video", "media_url": "https://media/x.mp4"}
    assert reddit.check_post(src, "", {"subreddit": "aivideo"}) == "A Reddit post needs a title (the words)."
    assert reddit.check_post(src, "A title", {}) == "Name the subreddit to post to."
    assert reddit.check_post(src, "A title", {"subreddit": "r/aivideo"}) is None
    sent = {}

    def fake(method, url, **kw):
        sent.update(kw["data"])
        return {"json": {"errors": [], "data": {"name": "t3_abc", "url": "https://reddit.com/r/aivideo/comments/abc"}}}
    monkeypatch.setattr(reddit, "_http", fake)
    res = reddit.post_start("T", {"username": "mike"}, {
        "caption": "Dawn over the city", "media": {"url": "https://media/x.mp4", "kind": "video"},
        "settings": {"subreddit": "/r/aivideo/", "flair_id": "f1", "nsfw": True}})
    assert res.status == "completed" and res.release_id == "t3_abc" and "comments/abc" in res.release_url
    assert sent["sr"] == "aivideo" and sent["kind"] == "link" and sent["title"] == "Dawn over the city"
    assert sent["url"] == "https://media/x.mp4" and sent["flair_id"] == "f1" and sent["nsfw"] == "true"
    # the sub's own refusal, in its words
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: {"json": {"errors": [
        ["SUBMIT_VALIDATION_FLAIR_REQUIRED", "Your post must contain post flair.", "flair"]]}})
    with pytest.raises(PostFailed, match="r/aivideo refused the post: Your post must contain post flair"):
        reddit.post_start("T", {}, _rpost("aivideo"))
    # a 403 is the platform's no; a 503 is retried
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: (_ for _ in ()).throw(HttpError(403, "banned")))
    with pytest.raises(PostFailed, match="Reddit refused"):
        reddit.post_start("T", {}, _rpost())
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: (_ for _ in ()).throw(HttpError(503)))
    with pytest.raises(HttpError):
        reddit.post_start("T", {}, _rpost())
    # the token never reaches the words
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: (_ for _ in ()).throw(HttpError(400, "bad T-SECRET")))
    with pytest.raises(PostFailed) as e:
        reddit.post_start("T-SECRET", {}, _rpost())
    assert "T-SECRET" not in str(e.value)
    # flairs, for the drawer
    monkeypatch.setattr(reddit, "_http", lambda m, u, **k: [{"id": "f1", "text": "Showcase"}, {"text": "no id"}])
    assert reddit.flairs("T", "aivideo") == [{"id": "f1", "text": "Showcase"}]


# --------------------------------------------------------------------------
# LinkedIn
# --------------------------------------------------------------------------

@pytest.fixture
def linkedin_env(monkeypatch):
    monkeypatch.setenv(linkedin.CLIENT_ID_ENV, "lid")
    monkeypatch.setenv(linkedin.CLIENT_SECRET_ENV, "lsecret")


def test_linkedin_authenticate(linkedin_env, monkeypatch):
    assert "w_member_social" in linkedin.auth_url("https://cb", "st")

    def fake(method, url, **kw):
        if url == linkedin.TOKEN_URL:
            assert kw["data"]["client_secret"] == "lsecret"
            return {"access_token": "A", "expires_in": 5184000, "scope": "openid,profile,email,w_member_social"}
        if url.endswith("/v2/userinfo"):
            return {"sub": "abc", "name": "Mike M", "picture": "https://pic"}
        raise AssertionError(url)
    monkeypatch.setattr(linkedin, "_http", fake)
    found = linkedin.authenticate("code", "https://cb", {})
    assert found.external_id == "abc" and found.display_name == "Mike M"
    assert found.meta["person_urn"] == "urn:li:person:abc" and found.expires_in == 5184000
    assert found.refresh_token == ""
    assert linkedin.refresh("A", "") is None          # self-serve: nothing to renew with
    monkeypatch.setattr(linkedin, "_http", lambda m, u, **k: {"access_token": "A", "scope": "openid profile"})
    with pytest.raises(ConnectRefused, match="posting"):
        linkedin.authenticate("code", "https://cb", {})


def test_linkedin_image_posts_in_one_go(linkedin_env, monkeypatch, tmp_path):
    still = tmp_path / "still.png"
    still.write_bytes(b"PNGBYTES")
    calls = []

    def fake_http(method, url, **kw):
        calls.append(("http", method, url))
        if "images?action=initializeUpload" in url:
            assert kw["headers"]["LinkedIn-Version"] == linkedin.LINKEDIN_VERSION
            return {"value": {"uploadUrl": "https://up/1", "image": "urn:li:image:1"}}
        raise AssertionError(url)

    def fake_request(method, url, **kw):
        calls.append(("req", method, url))
        if url == "https://up/1":
            assert kw["data"] == b"PNGBYTES"
            return FakeResponse()
        if url.endswith("/rest/posts"):
            body = kw["json"]
            assert body["author"] == "urn:li:person:abc" and body["content"]["media"]["id"] == "urn:li:image:1"
            assert body["visibility"] == "CONNECTIONS"
            return FakeResponse(headers={"x-restli-id": "urn:li:share:9"})
        raise AssertionError(url)
    monkeypatch.setattr(linkedin, "_http", fake_http)
    monkeypatch.setattr(linkedin, "_request", fake_request)
    res = linkedin.post_start("T", {"person_urn": "urn:li:person:abc"}, {
        "caption": "A still", "media": {"kind": "image", "path": str(still), "url": ""},
        "settings": {"visibility": "CONNECTIONS"}})
    assert res.status == "completed" and res.release_id == "urn:li:share:9"
    assert res.release_url.endswith("urn:li:share:9")
    assert [c[2].split("/")[-1] for c in calls] == ["images?action=initializeUpload", "1", "posts"]


def test_linkedin_video_is_pending_then_posted(linkedin_env, monkeypatch, tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"0123456789")
    state = {"status": "PROCESSING", "posts": 0}

    def fake_http(method, url, **kw):
        if "videos?action=initializeUpload" in url:
            assert kw["json"]["initializeUploadRequest"]["fileSizeBytes"] == 10
            return {"value": {"video": "urn:li:video:7", "uploadToken": "tok",
                              "uploadInstructions": [{"uploadUrl": "https://up/a", "firstByte": 0, "lastByte": 4},
                                                     {"uploadUrl": "https://up/b", "firstByte": 5, "lastByte": 9}]}}
        if "videos?action=finalizeUpload" in url:
            assert kw["json"]["finalizeUploadRequest"]["uploadedPartIds"] == ["e1", "e2"]
            return {}
        if "/rest/videos/urn%3Ali%3Avideo%3A7" in url:
            return {"status": state["status"]}
        raise AssertionError(url)

    def fake_request(method, url, **kw):
        if url == "https://up/a":
            assert kw["data"] == b"01234"
            return FakeResponse(headers={"etag": "e1"})
        if url == "https://up/b":
            assert kw["data"] == b"56789"
            return FakeResponse(headers={"ETag": "e2"})
        if url.endswith("/rest/posts"):
            state["posts"] += 1
            assert kw["json"]["content"]["media"]["id"] == "urn:li:video:7"
            return FakeResponse(headers={"x-restli-id": "urn:li:ugcPost:5"})
        raise AssertionError(url)
    monkeypatch.setattr(linkedin, "_http", fake_http)
    monkeypatch.setattr(linkedin, "_request", fake_request)
    meta = {"person_urn": "urn:li:person:abc"}
    res = linkedin.post_start("T", meta, {"caption": "A clip", "media": {"kind": "video", "path": str(clip), "url": ""},
                                          "settings": {}})
    assert res.status == "pending" and res.pending["video"] == "urn:li:video:7"
    # still processing: pending; then available: ready; then the finish posts once
    assert linkedin.post_check("T", meta, res.pending).status == "pending"
    state["status"] = "AVAILABLE"
    assert linkedin.post_check("T", meta, res.pending).status == "ready"
    done = linkedin.post_finish("T", meta, res.pending)
    assert done.status == "completed" and done.release_id == "urn:li:ugcPost:5" and state["posts"] == 1
    # a finish called again with the post already made answers the same, never posts twice
    again = linkedin.post_finish("T", meta, {**res.pending, "post": "urn:li:ugcPost:5", "url": done.release_url})
    assert again.status == "completed" and state["posts"] == 1
    state["status"] = "PROCESSING_FAILED"
    with pytest.raises(PostFailed, match="could not process"):
        linkedin.post_check("T", meta, res.pending)
    assert linkedin.check_post({"kind": "audio", "media_url": "x"}, "", {}) == "LinkedIn takes a video or an image."


# --------------------------------------------------------------------------
# a group press with one platform's form per connection
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
    a = accounts.upsert_account("studio", "Studio", dsn=pg)
    rd = social_connections.save(a, "reddit", Connected(
        external_id="u1", display_name="u/mike", handle="mike", access_token="A", refresh_token="R",
        expires_in=3600, meta={"username": "mike"}), dsn=pg)
    li = social_connections.save(a, "linkedin", Connected(
        external_id="abc", display_name="Mike M", access_token="A", expires_in=5184000,
        meta={"person_urn": "urn:li:person:abc", "name": "Mike M"}), dsn=pg)
    with db.connect(pg) as conn:
        row = conn.execute(
            "INSERT INTO generated_assets (created_at, generation_id, tool, model, media_kind, prompt, media_url, "
            "metadata_json, account_id) VALUES ('2026-10-22', 1, 'fal', 'kling', 'video', 'a shot', "
            "'https://media.example/clip.mp4', %s, %s) RETURNING id", (json.dumps({"seconds": 8}), a)).fetchone()
    return {"dsn": pg, "a": a, "rd": rd, "li": li, "clip": f"gen:{row['id']}"}


def test_group_settings_by(env):
    a, dsn = env["a"], env["dsn"]
    # Reddit without a subreddit refuses the press by name, and LinkedIn gets no row either
    with pytest.raises(posts.PostRefused, match="Reddit: Name the subreddit"):
        posts.create_group(a, connection_ids=[env["li"]["id"], env["rd"]["id"]], source_ref=env["clip"],
                           caption="Dawn", publish_at="2026-10-23T13:00:00Z", dsn=dsn)
    assert posts.list_for(a, dsn=dsn) == []
    made = posts.create_group(a, connection_ids=[env["li"]["id"], env["rd"]["id"]], source_ref=env["clip"],
                              caption="Dawn over the city", publish_at="2026-10-23T13:00:00Z",
                              settings={"visibility": "PUBLIC"},
                              settings_by={env["rd"]["id"]: {"subreddit": "aivideo", "flair_id": "f1"}}, dsn=dsn)
    by = {p["provider"]: p for p in made}
    assert by["reddit"]["settings"] == {"visibility": "PUBLIC", "subreddit": "aivideo", "flair_id": "f1"}
    assert by["linkedin"]["settings"] == {"visibility": "PUBLIC"}
    # a Reddit title past 300 is refused by the platform's own limit
    with pytest.raises(posts.PostRefused, match="Reddit takes a caption of at most 300"):
        posts.create_group(a, connection_ids=[env["rd"]["id"]], source_ref=env["clip"], caption="x" * 301,
                           settings_by={env["rd"]["id"]: {"subreddit": "aivideo"}}, dsn=dsn)
