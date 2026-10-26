"""
LinkedIn Page (src/social/linkedin_page.py, 2026-10-23): the Community
Management app's connect, its Page pick and posting as the Page.

What is worth more than the coverage:

1. Only Pages the member can POST for are offered: an analyst's Page is
   not, and a member with none is refused at connect, never left with a
   row that cannot post (`test_pages_are_the_posting_roles_only`).
2. One Page finishes at once; several wait for the pick, which accepts
   only a listed Page (`test_one_page_finishes_at_once`,
   `test_several_pages_wait_for_the_pick`).
3. A post is BY the Page, owned by the Page, and public whatever the
   member's visibility setting said (`test_a_page_post_is_the_pages`).
"""
from __future__ import annotations

import pytest

from src import social
from src.social import linkedin, linkedin_page
from src.social.base import ConnectRefused


class FakeResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


@pytest.fixture
def page_env(monkeypatch):
    monkeypatch.setenv(linkedin_page.CLIENT_ID_ENV, "pid")
    monkeypatch.setenv(linkedin_page.CLIENT_SECRET_ENV, "psecret")


def _fake(acls, names):
    def fake(method, url, **kw):
        if url == linkedin_page.TOKEN_URL:
            assert kw["data"]["client_id"] == "pid" and kw["data"]["client_secret"] == "psecret"
            return {"access_token": "A", "refresh_token": "R", "expires_in": 5184000,
                    "scope": "w_organization_social,r_organization_admin"}
        if url.endswith("/rest/organizationAcls"):
            assert kw["params"]["q"] == "roleAssignee" and kw["params"]["state"] == "APPROVED"
            assert kw["headers"]["LinkedIn-Version"] == linkedin.LINKEDIN_VERSION
            return {"elements": acls}
        if "/rest/organizations/" in url:
            org = url.rsplit("/", 1)[-1]
            got = {"localizedName": names[org]}
            if org == "5":
                got["logoV2"] = {"original": "urn:li:image:L5"}
            return got
        if "/rest/images/" in url:
            assert url.endswith("urn%3Ali%3Aimage%3AL5")
            return {"downloadUrl": "https://media.licdn.com/logo5.png"}
        raise AssertionError(url)
    return fake


def _acl(org, role, key="organization"):
    return {"role": role, key: f"urn:li:organization:{org}", "roleAssignee": "urn:li:person:m1",
            "state": "APPROVED"}


def test_not_set_up_until_its_own_app_is(monkeypatch):
    monkeypatch.delenv(linkedin_page.CLIENT_ID_ENV, raising=False)
    cat = {p["id"]: p for p in social.catalogue()}
    assert cat["linkedin_page"]["configured"] is False
    assert cat["linkedin_page"]["pending_step"] == "page"
    assert cat["linkedin_page"]["settings"] == []            # always public
    assert social.get("linkedin_page") is linkedin_page
    with pytest.raises(ConnectRefused, match="not set up"):
        linkedin_page.auth_url("https://cb", "st")


def test_auth_url_asks_for_page_posting(page_env):
    url = linkedin_page.auth_url("https://cb", "st")
    assert "client_id=pid" in url and "w_organization_social" in url
    assert "r_organization_admin" in url and "openid" not in url


def test_pages_are_the_posting_roles_only(page_env, monkeypatch):
    monkeypatch.setattr(linkedin_page, "_http", _fake([_acl("7", "ANALYST")], {"7": "Watched"}))
    with pytest.raises(ConnectRefused, match="no posting role"):
        linkedin_page.authenticate("code", "https://cb", {})


def test_one_page_finishes_at_once(page_env, monkeypatch):
    monkeypatch.setattr(linkedin_page, "_http", _fake(
        [_acl("5", "ADMINISTRATOR", key="organizationTarget"), _acl("7", "ANALYST")],
        {"5": "Phantra AI", "7": "Watched"}))
    got = linkedin_page.authenticate("code", "https://cb", {})
    assert got.pending is None and got.external_id == "m1"
    assert got.meta["organization_urn"] == "urn:li:organization:5"
    assert got.display_name == "Phantra AI" and linkedin_page.display_label(got.meta) == "Phantra AI"
    assert got.refresh_token == "R" and got.meta["person_urn"] == "urn:li:person:m1"


def test_several_pages_wait_for_the_pick(page_env, monkeypatch):
    monkeypatch.setattr(linkedin_page, "_http", _fake(
        [_acl("5", "ADMINISTRATOR"), _acl("6", "CONTENT_ADMINISTRATOR"), _acl("5", "ANALYST")],
        {"5": "Phantra AI", "6": "Another Co"}))
    got = linkedin_page.authenticate("code", "https://cb", {})
    assert got.pending == "page" and "organization_urn" not in got.meta
    opts = linkedin_page.options(got.meta)
    assert [(o["id"], o["hint"]) for o in opts] == [("6", "Content admin"), ("5", "Admin")]
    # the picker's cards: a Page with a logo carries it, one without has none
    assert opts[1]["picture"] == "https://media.licdn.com/logo5.png" and "picture" not in opts[0]
    with pytest.raises(ConnectRefused, match="not one you can post for"):
        linkedin_page.pick(got.meta, "7")
    done = linkedin_page.pick(got.meta, "5")
    assert done["organization_urn"] == "urn:li:organization:5" and done["page_name"] == "Phantra AI"


def test_a_page_post_is_the_pages(page_env, monkeypatch, tmp_path):
    still = tmp_path / "still.png"
    still.write_bytes(b"PNG")

    def fake_http(method, url, **kw):
        if "images?action=initializeUpload" in url:
            assert kw["json"]["initializeUploadRequest"]["owner"] == "urn:li:organization:5"
            return {"value": {"uploadUrl": "https://up/1", "image": "urn:li:image:1"}}
        raise AssertionError(url)

    def fake_request(method, url, **kw):
        if url == "https://up/1":
            return FakeResponse()
        if url.endswith("/rest/posts"):
            assert kw["json"]["author"] == "urn:li:organization:5"
            assert kw["json"]["visibility"] == "PUBLIC"
            return FakeResponse(headers={"x-restli-id": "urn:li:share:9"})
        raise AssertionError(url)
    monkeypatch.setattr(linkedin, "_http", fake_http)
    monkeypatch.setattr(linkedin, "_request", fake_request)
    meta = {"person_urn": "urn:li:person:m1", "organization_urn": "urn:li:organization:5"}
    res = linkedin_page.post_start("T", meta, {
        "caption": "A still", "media": {"kind": "image", "path": str(still), "url": ""},
        "settings": {"visibility": "CONNECTIONS"}})
    assert res.status == "completed" and res.release_id == "urn:li:share:9"


def test_refresh_uses_the_page_app(page_env, monkeypatch):
    def fake(method, url, **kw):
        assert kw["data"]["client_id"] == "pid" and kw["data"]["refresh_token"] == "R"
        return {"access_token": "A2", "expires_in": 100}
    monkeypatch.setattr(linkedin, "_http", fake)
    got = linkedin_page.refresh("A", "R")
    assert got is not None and got.access_token == "A2" and got.refresh_token == "R"
    assert linkedin_page.refresh("A", "") is None
