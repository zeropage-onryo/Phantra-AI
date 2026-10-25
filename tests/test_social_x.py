"""
X (src/social/x.py, 2026-10-25): PKCE connect, rotating refresh, and a
post with a still or a video through the v2 chunked upload.

What is worth more than the coverage:

1. The PKCE verifier is derived from the state, so the callback finds
   the same one with nothing stored, and the challenge sent is its S256
   (`test_the_verifier_comes_back_from_the_state`).
2. A refresh keeps X's NEW refresh token; the old one is dead after use
   (`test_refresh_keeps_the_rotated_token`).
3. A video waits for X's processing before the post is created, and X's
   own no is terminal while a 429 goes back for a retry
   (`test_a_video_waits_for_processing`, `test_a_refusal_is_terminal_a_429_is_not`).
"""
from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from src import social
from src.social import x
from src.social.base import ConnectRefused, PostFailed


class FakeResponse:
    def __init__(self, status=200):
        self.status_code = status


class HttpError(requests.RequestException):
    def __init__(self, status, text=""):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


@pytest.fixture
def x_env(monkeypatch):
    monkeypatch.setenv(x.CLIENT_ID_ENV, "xid")
    monkeypatch.setenv(x.CLIENT_SECRET_ENV, "xsecret")


def test_not_set_up_until_its_app_is(monkeypatch):
    monkeypatch.delenv(x.CLIENT_ID_ENV, raising=False)
    cat = {p["id"]: p for p in social.catalogue()}
    assert cat["x"]["configured"] is False and cat["x"]["caption_max"] == 280
    assert social.get("x") is x
    with pytest.raises(ConnectRefused, match="not set up"):
        x.auth_url("https://cb", "st")


def test_the_verifier_comes_back_from_the_state(x_env):
    url = x.auth_url("https://cb", "STATE-1")
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["client_id"] == "xid" and q["code_challenge_method"] == "S256"
    assert q["scope"].split() == list(x.SCOPES) and q["state"] == "STATE-1"
    verifier = x.verifier_for("STATE-1")
    assert 43 <= len(verifier) <= 128 and verifier != x.verifier_for("STATE-2")
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    assert q["code_challenge"] == digest.decode()


def test_authenticate_reads_who_connected(x_env, monkeypatch):
    def fake(method, url, **kw):
        if url == x.TOKEN_URL:
            assert kw["data"]["code_verifier"] == x.verifier_for("ST")
            assert kw["headers"]["Authorization"] == "Basic " + base64.b64encode(b"xid:xsecret").decode()
            return {"access_token": "A", "refresh_token": "R", "expires_in": 7200,
                    "scope": " ".join(x.SCOPES)}
        if url.endswith("/2/users/me"):
            assert kw["headers"]["Authorization"] == "Bearer A"
            return {"data": {"id": "42", "username": "phantra_ai", "name": "Phantra"}}
        raise AssertionError(url)
    monkeypatch.setattr(x, "_http", fake)
    got = x.authenticate("code", "https://cb", {"state": "ST"})
    assert got.external_id == "42" and got.handle == "phantra_ai" and got.refresh_token == "R"
    assert got.expires_in == 7200 and x.display_label(got.meta) == "@phantra_ai"


def test_a_grant_without_posting_is_refused(x_env, monkeypatch):
    monkeypatch.setattr(x, "_http", lambda m, u, **kw: {
        "access_token": "A", "scope": "tweet.read users.read offline.access"})
    with pytest.raises(ConnectRefused, match="without permission to post"):
        x.authenticate("code", "https://cb", {"state": "ST"})


def test_refresh_keeps_the_rotated_token(x_env, monkeypatch):
    def fake(method, url, **kw):
        assert kw["data"] == {"grant_type": "refresh_token", "refresh_token": "R1"}
        return {"access_token": "A2", "refresh_token": "R2", "expires_in": 7200}
    monkeypatch.setattr(x, "_http", fake)
    got = x.refresh("A1", "R1")
    assert got.access_token == "A2" and got.refresh_token == "R2"
    assert x.refresh("A1", "") is None


def test_check_post():
    assert x.check_post({}, "", {}) == "An X post needs words or a clip."
    assert "280" in x.check_post({}, "w" * 281, {})
    assert x.check_post({"kind": "video", "media_url": "u"}, "hi", {}) is None


def _uploader(seen, finalize_info=None):
    def fake_http(method, url, **kw):
        seen.append(url.rsplit("/2/", 1)[-1])
        if url.endswith("/initialize"):
            return {"data": {"id": "M1"}}
        if url.endswith("/finalize"):
            return {"data": {"id": "M1", "processing_info": finalize_info} if finalize_info else {"id": "M1"}}
        if url.endswith("/2/tweets"):
            seen.append(kw["json"])
            return {"data": {"id": "T9"}}
        raise AssertionError(url)
    return fake_http


def test_a_still_posts_at_once(monkeypatch, tmp_path):
    still = tmp_path / "still.png"
    still.write_bytes(b"PNG")
    seen, parts = [], []
    monkeypatch.setattr(x, "_http", _uploader(seen))
    monkeypatch.setattr(x, "_request", lambda m, u, **kw: parts.append(kw["data"]) or FakeResponse())
    res = x.post_start("T", {"username": "phantra_ai"}, {
        "caption": "A still", "media": {"kind": "image", "path": str(still), "url": ""}})
    assert res.status == "completed" and res.release_url == "https://x.com/phantra_ai/status/T9"
    assert seen[:2] == ["media/upload/initialize", "media/upload/M1/finalize"]
    assert seen[-1] == {"text": "A still", "media": {"media_ids": ["M1"]}}
    assert parts == [{"segment_index": "0"}]


def test_a_video_waits_for_processing(monkeypatch, tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"0" * (x.CHUNK_BYTES + 10))
    seen, parts = [], []
    monkeypatch.setattr(x, "_http", _uploader(seen, {"state": "pending", "check_after_secs": 5}))
    monkeypatch.setattr(x, "_request", lambda m, u, **kw: parts.append(kw["data"]) or FakeResponse())
    res = x.post_start("T", {"username": "p"}, {
        "caption": "A clip", "media": {"kind": "video", "path": str(clip), "url": ""}})
    assert res.status == "pending" and res.pending == {"media_id": "M1", "caption": "A clip"}
    assert parts == [{"segment_index": "0"}, {"segment_index": "1"}]

    states = iter(["in_progress", "succeeded"])
    monkeypatch.setattr(x, "_http", lambda m, u, **kw: {
        "data": {"processing_info": {"state": next(states)}}})
    assert x.post_check("T", {}, res.pending).status == "pending"
    assert x.post_check("T", {}, res.pending).status == "ready"

    seen.clear()
    monkeypatch.setattr(x, "_http", _uploader(seen))
    done = x.post_finish("T", {"username": "p"}, res.pending)
    assert done.status == "completed" and done.release_id == "T9"


def test_a_refusal_is_terminal_a_429_is_not(monkeypatch):
    def refuse(status):
        def fake(method, url, **kw):
            raise HttpError(status, "no credit T")
        return fake
    monkeypatch.setattr(x, "_http", refuse(402))
    with pytest.raises(PostFailed, match="X refused"):
        x.post_start("T", {}, {"caption": "words", "media": {}})
    monkeypatch.setattr(x, "_http", refuse(429))
    with pytest.raises(HttpError):
        x.post_start("T", {}, {"caption": "words", "media": {}})
