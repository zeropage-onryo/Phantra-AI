"""
YouTube (src/social/youtube.py, 2026-10-26): a channel through Google
OAuth, and a video posted through the resumable upload.

What is worth more than the coverage:

1. The connect always asks for a refresh token (offline + consent), and a
   Google account with no channel is refused at connect with how to make
   one, never left with a row that cannot post
   (`test_auth_url_asks_for_a_refresh_token`, `test_no_channel_is_refused`).
2. Every upload discloses synthetic media and says not made for kids
   (`test_a_video_is_one_resumable_upload`).
3. A refresh keeps the refresh token Google does not send back
   (`test_refresh_keeps_the_refresh_token`).
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
import requests

from src import social
from src.social import youtube
from src.social.base import ConnectRefused, PostFailed


class FakeResponse:
    def __init__(self, headers=None, body=None):
        self.headers = headers or {}
        self._body = body or {}

    def json(self):
        return self._body


class HttpError(requests.RequestException):
    def __init__(self, status, text=""):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


@pytest.fixture
def yt_env(monkeypatch):
    monkeypatch.setenv(youtube.CLIENT_ID_ENV, "gid")
    monkeypatch.setenv(youtube.CLIENT_SECRET_ENV, "gsecret")


def _channel(**over):
    item = {"id": "UC1", "snippet": {"title": "Phantra AI", "customUrl": "@phantra",
                                     "thumbnails": {"default": {"url": "https://yt/p.jpg"}}},
            "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}
    item.update(over)
    return item


def test_not_set_up_until_its_app_is(monkeypatch):
    monkeypatch.delenv(youtube.CLIENT_ID_ENV, raising=False)
    cat = {p["id"]: p for p in social.catalogue()}
    assert cat["youtube"]["configured"] is False and cat["youtube"]["feed"] is True
    assert [f["key"] for f in cat["youtube"]["settings"]] == ["title", "privacy"]
    with pytest.raises(ConnectRefused, match="not set up"):
        youtube.auth_url("https://cb", "st")


def test_auth_url_asks_for_a_refresh_token(yt_env):
    q = {k: v[0] for k, v in parse_qs(urlparse(youtube.auth_url("https://cb", "ST")).query).items()}
    assert q["access_type"] == "offline" and q["prompt"] == "consent"
    assert q["scope"].split() == list(youtube.SCOPES) and q["state"] == "ST" and q["client_id"] == "gid"


def test_authenticate_reads_the_channel(yt_env, monkeypatch):
    def fake(method, url, **kw):
        if url == youtube.TOKEN_URL:
            assert kw["data"]["client_secret"] == "gsecret" and kw["data"]["code"] == "c"
            return {"access_token": "A", "refresh_token": "R", "expires_in": 3599,
                    "scope": " ".join(youtube.SCOPES)}
        if url.endswith("/channels"):
            assert kw["params"]["mine"] == "true" and kw["headers"]["Authorization"] == "Bearer A"
            return {"items": [_channel()]}
        raise AssertionError(url)
    monkeypatch.setattr(youtube, "_http", fake)
    got = youtube.authenticate("c", "https://cb", {})
    assert got.external_id == "UC1" and got.display_name == "Phantra AI" and got.handle == "phantra"
    assert got.refresh_token == "R" and got.meta["uploads_playlist"] == "UU1"
    assert youtube.display_label(got.meta) == "@phantra"


def test_no_channel_is_refused(yt_env, monkeypatch):
    monkeypatch.setattr(youtube, "_http", lambda m, u, **kw: (
        {"access_token": "A", "scope": " ".join(youtube.SCOPES)} if u == youtube.TOKEN_URL else {"items": []}))
    with pytest.raises(ConnectRefused, match="no YouTube channel"):
        youtube.authenticate("c", "https://cb", {})


def test_a_grant_without_upload_is_refused(yt_env, monkeypatch):
    monkeypatch.setattr(youtube, "_http", lambda m, u, **kw: {
        "access_token": "A", "scope": "https://www.googleapis.com/auth/youtube.readonly"})
    with pytest.raises(ConnectRefused, match="without permission to upload"):
        youtube.authenticate("c", "https://cb", {})


def test_refresh_keeps_the_refresh_token(yt_env, monkeypatch):
    def fake(method, url, **kw):
        assert kw["data"]["grant_type"] == "refresh_token" and kw["data"]["refresh_token"] == "R"
        return {"access_token": "A2", "expires_in": 3599}
    monkeypatch.setattr(youtube, "_http", fake)
    got = youtube.refresh("A", "R")
    assert got.access_token == "A2" and got.refresh_token == "R"
    assert youtube.refresh("A", "") is None


def test_check_post_and_the_title():
    clip = {"kind": "video", "media_url": "https://m/c.mp4"}
    assert "takes a video" in youtube.check_post({"kind": "image", "media_url": "u"}, "hi", {})
    assert "needs a title" in youtube.check_post(clip, "  ", {})
    assert "< or >" in youtube.check_post(clip, "a <b>", {})
    assert "Pick Public" in youtube.check_post(clip, "hi", {"privacy": "friends"})
    assert youtube.check_post(clip, "First line\nmore words", {}) is None
    assert youtube.title_for("First line\nmore", {}) == "First line"
    assert youtube.title_for("x", {"title": "Own title"}) == "Own title"
    long = youtube.title_for("w" * 150, {})
    assert len(long) == youtube.TITLE_MAX and long.endswith("…")


def test_a_video_is_one_resumable_upload(monkeypatch, tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"MP4DATA")
    calls = []

    def fake_request(method, url, **kw):
        calls.append((method, url))
        if method == "POST":
            assert kw["params"] == {"uploadType": "resumable", "part": "snippet,status"}
            assert kw["headers"]["X-Upload-Content-Length"] == "7"
            body = kw["json"]
            assert body["snippet"]["title"] == "My clip" and body["snippet"]["description"] == "My clip\n#ai"
            assert body["status"] == {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False,
                                      "containsSyntheticMedia": True}
            return FakeResponse(headers={"Location": "https://up/session1"})
        assert url == "https://up/session1" and kw["data"] == b"MP4DATA"
        return FakeResponse(body={"id": "vid9"})
    monkeypatch.setattr(youtube, "_request", fake_request)
    res = youtube.post_start("T", {}, {"caption": "My clip\n#ai", "settings": {"privacy": "unlisted"},
                                       "media": {"kind": "video", "path": str(clip), "url": ""}})
    assert res.status == "completed" and res.release_url == "https://youtu.be/vid9"
    assert [m for m, _ in calls] == ["POST", "PUT"]


def test_a_refusal_is_terminal_a_429_is_not(monkeypatch, tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"x")
    post = {"caption": "c", "media": {"kind": "video", "path": str(clip)}}

    def refuse(status):
        def fake(method, url, **kw):
            raise HttpError(status, "quotaExceeded")
        return fake
    monkeypatch.setattr(youtube, "_request", refuse(403))
    with pytest.raises(PostFailed, match="YouTube refused"):
        youtube.post_start("T", {}, post)
    monkeypatch.setattr(youtube, "_request", refuse(503))
    with pytest.raises(HttpError):
        youtube.post_start("T", {}, post)


def test_the_feed_reads_the_uploads_playlist(monkeypatch):
    def fake(method, url, **kw):
        assert url.endswith("/playlistItems") and kw["params"]["playlistId"] == "UU1"
        return {"items": [{"snippet": {"title": "A short", "thumbnails": {"medium": {"url": "https://t"}}},
                           "contentDetails": {"videoId": "v1", "videoPublishedAt": "2026-10-20T10:00:00Z"}}]}
    monkeypatch.setattr(youtube, "_http", fake)
    got = youtube.recent_media("T", {"uploads_playlist": "UU1"})
    assert got == [{"id": "v1", "kind": "video", "thumb": "https://t", "url": "https://youtu.be/v1",
                    "at": "2026-10-20T10:00:00Z", "caption": "A short"}]
    assert youtube.recent_media("T", {}) == []
