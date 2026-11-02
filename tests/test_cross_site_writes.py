"""A write another site's page makes with the person's session is refused
(app/cross_site.py; QA 2026-11-02, E1).

The two doors the QA reproduced it on -- a still that spends credits and
a share that makes a render public -- answer 403 `cross_site` before any
route runs, and the studio's own requests (same-origin through the Next
proxy, the guarded header, a trusted front end, a non-browser caller)
pass the middleware untouched.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, cross_site
from app.main import app

client = TestClient(app, cookies={auth.SESSION_COOKIE: "a-session"})

EVIL = {"origin": "https://evil.example", "sec-fetch-site": "cross-site"}


@pytest.mark.parametrize("path,kwargs", [
    ("/api/direct/image/run", {"files": {"prompt": (None, "a cat")},
                               "data": {"model": "flux2-pro", "expect_credits": "10"}}),
    ("/api/assets/generated/1/share", {}),
])
def test_cross_site_write_with_session_is_refused(path, kwargs):
    r = client.post(path, headers=EVIL, **kwargs)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "cross_site"


def test_old_browser_origin_only_is_refused():
    r = client.post("/api/assets/generated/1/share",
                    headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def _refused(method="POST", session=True, **headers):
    return cross_site.refused(method, {k.replace("_", "-"): v for k, v in headers.items()},
                              session)


def test_what_passes():
    # the studio through the Next proxy, a sibling subdomain, a typed address
    assert not _refused(origin="https://phantra.ai", sec_fetch_site="same-origin")
    assert not _refused(origin="https://phantra.ai", sec_fetch_site="same-site")
    assert not _refused(sec_fetch_site="none")
    # the guarded header forces a preflight
    assert not _refused(origin="https://evil.example", sec_fetch_site="cross-site",
                        x_phantra_model_connection="1")
    # reads, no session, and a caller that is not a browser page
    assert not _refused("GET", origin="https://evil.example", sec_fetch_site="cross-site")
    assert not _refused(session=False, origin="https://evil.example",
                        sec_fetch_site="cross-site")
    assert not _refused()
    # an old browser on this very host
    assert not _refused(origin="https://api.phantra.ai", host="api.phantra.ai")


def test_a_trusted_front_end_passes(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://preview.phantra.test")
    assert not _refused(origin="https://preview.phantra.test", sec_fetch_site="cross-site")
    assert _refused(origin="https://evil.example", sec_fetch_site="cross-site")


def test_what_is_refused():
    assert _refused(origin="https://evil.example", sec_fetch_site="cross-site")
    assert _refused("DELETE", origin="https://evil.example", sec_fetch_site="cross-site")
    assert _refused(sec_fetch_site="cross-site")
    assert _refused(origin="null")
    assert _refused(origin="https://evil.example", host="api.phantra.ai")
