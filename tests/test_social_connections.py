"""
Social connections (src/social_connections.py, src/social/*, app/social_routes.py).

What is worth more than the coverage:

1. A token never leaves the vault in the clear: not in a listing, not in
   an error, not on a row (`test_the_row_holds_no_clear_token`).
2. A grant that cannot publish is refused, not stored -- the Instagram
   toggle the person can switch off (`test_instagram_without_publish_is_refused`).
3. The callback trusts the signed state and this origin's nonce, never a
   cookie alone: a start URL lifted from one browser cannot finish in
   another, and a state for one workspace cannot write another's row.
4. Every read is one account's (`test_one_workspace_never_sees_anothers`).
5. publish_review.token_for prefers the person's own connection and keeps
   the operator's env token only as the TikTok fallback.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import requests
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app import social_routes
from app.main import app
from src import accounts, db, publish_review, social, social_connections
from src.social import discord, instagram
from src.social.base import Connected, ConnectRefused, Renewed

client = TestClient(app, follow_redirects=False)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def env(pg, monkeypatch):
    accounts.init(pg)
    social_connections.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-for-real-use")
    monkeypatch.setenv("SOCIAL_TOKEN_SECRET", "vault-secret-for-tests")
    monkeypatch.setenv("STUDIO_URL", "https://studio.example")
    monkeypatch.setenv("SOCIAL_REDIRECT_ORIGIN", "https://api.example")
    monkeypatch.setenv(discord.CLIENT_ID_ENV, "dc-id")
    monkeypatch.setenv(discord.CLIENT_SECRET_ENV, "dc-secret")
    monkeypatch.setenv(discord.BOT_TOKEN_ENV, "bot-token-secret")
    monkeypatch.setenv(instagram.APP_ID_ENV, "ig-id")
    monkeypatch.setenv(instagram.APP_SECRET_ENV, "ig-secret")
    social_connections._ready.clear()
    client.cookies.clear()
    a = accounts.upsert_account("studio", "Studio", dsn=pg)
    b = accounts.upsert_account("other", "Other", dsn=pg)
    ua = accounts.create_user("a@example.com", claimed=True, dsn=pg)
    ub = accounts.create_user("b@example.com", claimed=True, dsn=pg)
    accounts.add_member(a, ua, dsn=pg)
    accounts.add_member(b, ub, dsn=pg)
    return {"dsn": pg, "a": a, "b": b, "ua": ua, "ub": ub}


def sign_in(user_id: str, account_id: int | None = None) -> None:
    """The session cookie, and -- for the /api routes -- the account the
    conftest override would otherwise answer None for (its unowned pool)."""
    client.cookies.set(auth_mod.SESSION_COOKIE, auth_mod._serializer().dumps({"uid": user_id}))
    if account_id is not None:
        app.dependency_overrides[auth_mod.current_account_id] = lambda: account_id


def found(**over) -> Connected:
    base = dict(external_id="17841400000001", display_name="Phantra", handle="phantra.ai",
                avatar_url="https://cdn.example/p.jpg", access_token="IG-LONG-TOKEN",
                expires_in=60 * 86400, scopes=list(instagram.SCOPES), meta={"ig_user_id": "1784"})
    base.update(over)
    return Connected(**base)


class HttpError(requests.RequestException):
    def __init__(self, status, text):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


# --------------------------------------------------------------------------
# the vault and the rows
# --------------------------------------------------------------------------

def test_the_row_holds_no_clear_token(env):
    row = social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    assert "token" not in " ".join(row.keys()) and "IG-LONG-TOKEN" not in str(row)
    with db.connect(env["dsn"]) as conn:
        raw = conn.execute("SELECT token_enc FROM social_connections WHERE account_id = %s",
                           (env["a"],)).fetchone()["token_enc"]
    assert raw and "IG-LONG-TOKEN" not in raw
    token, conn_ = social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])
    assert token == "IG-LONG-TOKEN" and conn_["id"] == row["id"]


def test_no_secret_means_no_connection(env, monkeypatch):
    monkeypatch.delenv("SOCIAL_TOKEN_SECRET")
    monkeypatch.delenv("SESSION_SECRET")
    assert not social_connections.vault_ready()
    with pytest.raises(social_connections.VaultError, match="SOCIAL_TOKEN_SECRET"):
        social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    assert social_connections.list_for(env["a"], dsn=env["dsn"]) == []


def test_a_token_sealed_under_another_secret_does_not_open(env, monkeypatch):
    social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    monkeypatch.setenv("SOCIAL_TOKEN_SECRET", "a-different-secret")
    with pytest.raises(social_connections.VaultError, match="connect the account again"):
        social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])


def test_one_workspace_never_sees_anothers(env):
    social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    assert social_connections.list_for(env["b"], dsn=env["dsn"]) == []
    mine = social_connections.list_for(env["a"], dsn=env["dsn"])
    assert [c["handle"] for c in mine] == ["phantra.ai"]
    assert social_connections.get(env["b"], mine[0]["id"], dsn=env["dsn"]) is None
    assert not social_connections.remove(env["b"], mine[0]["id"], dsn=env["dsn"])
    with pytest.raises(ConnectRefused, match="Connect your Instagram"):
        social_connections.token_for(env["b"], "instagram", dsn=env["dsn"])


def test_reconnecting_the_same_account_updates_in_place(env):
    first = social_connections.save(env["a"], "instagram", found(access_token="OLD"), dsn=env["dsn"])
    second = social_connections.save(env["a"], "instagram", found(access_token="NEW", handle="phantra"),
                                     dsn=env["dsn"])
    assert first["id"] == second["id"] and second["handle"] == "phantra"
    token, _ = social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])
    assert token == "NEW"
    assert len(social_connections.list_for(env["a"], dsn=env["dsn"])) == 1


def test_disconnect_is_soft_and_wipes_the_token(env):
    row = social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    assert social_connections.remove(env["a"], row["id"], dsn=env["dsn"])
    assert social_connections.list_for(env["a"], dsn=env["dsn"]) == []
    with db.connect(env["dsn"]) as conn:
        r = conn.execute("SELECT token_enc, deleted_at FROM social_connections "
                         "WHERE id = %s AND account_id = %s", (row["id"], env["a"])).fetchone()
    assert r["deleted_at"] is not None and r["token_enc"] == ""
    # and connecting again is a NEW row, the old one kept as history
    again = social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    assert again["id"] != row["id"]


# --------------------------------------------------------------------------
# renewal
# --------------------------------------------------------------------------

def test_a_token_near_expiry_is_renewed_on_read(env, monkeypatch):
    social_connections.save(env["a"], "instagram", found(expires_in=3 * 86400), dsn=env["dsn"])
    calls = []

    def fake_refresh(access, refresh):
        calls.append(access)
        return Renewed(access_token="RENEWED", expires_in=60 * 86400)
    monkeypatch.setattr(instagram, "refresh", fake_refresh)
    token, conn_ = social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])
    assert token == "RENEWED" and calls == ["IG-LONG-TOKEN"]
    # and it is written down: the next read needs no renewal
    far = datetime.now(timezone.utc) + timedelta(days=50)
    assert datetime.fromisoformat(conn_["expires_at"]) > datetime.now(timezone.utc) + timedelta(days=30)
    calls.clear()
    token, _ = social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])
    assert token == "RENEWED" and calls == []
    assert far > datetime.now(timezone.utc)


def test_a_failed_renewal_marks_reconnect(env, monkeypatch):
    social_connections.save(env["a"], "instagram", found(expires_in=3 * 86400), dsn=env["dsn"])

    def broken(access, refresh):
        raise ConnectRefused("Instagram did not renew the token: HTTP 400")
    monkeypatch.setattr(instagram, "refresh", broken)
    with pytest.raises(ConnectRefused, match="did not renew"):
        social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])
    row = social_connections.list_for(env["a"], dsn=env["dsn"])[0]
    assert row["status"] == "reconnect"
    with pytest.raises(ConnectRefused, match="reconnected"):
        social_connections.token_for(env["a"], "instagram", dsn=env["dsn"])


def test_an_expired_token_is_a_reconnect_never_a_post(env):
    social_connections.save(env["a"], "instagram", found(expires_in=1), dsn=env["dsn"])
    later = datetime.now(timezone.utc) + timedelta(seconds=5)
    with pytest.raises(ConnectRefused, match="expired"):
        social_connections.token_for(env["a"], "instagram", dsn=env["dsn"], now=later)
    assert social_connections.list_for(env["a"], dsn=env["dsn"])[0]["status"] == "reconnect"


# --------------------------------------------------------------------------
# the providers, behind their one seam
# --------------------------------------------------------------------------

def test_instagram_authenticate_exchanges_for_a_long_lived_token(env, monkeypatch):
    seen = []

    def fake(method, url, **kw):
        seen.append((method, url))
        if url == instagram.TOKEN_URL:
            assert kw["data"]["code"] == "abc"        # the "#_" is stripped
            return {"access_token": "SHORT", "user_id": 1784,
                    "permissions": ",".join(instagram.SCOPES)}
        if url.endswith("/access_token"):
            assert kw["params"]["access_token"] == "SHORT"
            return {"access_token": "LONG", "expires_in": 5183944}
        if url.endswith("/me"):
            return {"user_id": "1784", "username": "phantra.ai", "name": "Phantra",
                    "profile_picture_url": "https://cdn/p.jpg"}
        raise AssertionError(url)
    monkeypatch.setattr(instagram, "_http", fake)
    got = instagram.authenticate("abc#_", "https://api.example/cb", {})
    assert got.access_token == "LONG" and got.external_id == "1784"
    assert got.handle == "phantra.ai" and got.expires_in == 5183944 and got.pending is None
    assert [u for _, u in seen][0] == instagram.TOKEN_URL


def test_instagram_without_publish_is_refused(env, monkeypatch):
    def fake(method, url, **kw):
        if url == instagram.TOKEN_URL:
            return {"access_token": "SHORT", "user_id": 1784,
                    "permissions": "instagram_business_basic,instagram_business_manage_insights"}
        raise AssertionError("must not get past the permissions check: " + url)
    monkeypatch.setattr(instagram, "_http", fake)
    with pytest.raises(ConnectRefused, match="publish"):
        instagram.authenticate("abc", "https://api.example/cb", {})


def test_a_provider_error_is_redacted(env, monkeypatch):
    def fake(method, url, **kw):
        raise HttpError(400, "bad client_secret ig-secret and code abc")
    monkeypatch.setattr(instagram, "_http", fake)
    with pytest.raises(ConnectRefused) as e:
        instagram.authenticate("abc", "https://api.example/cb", {})
    assert "ig-secret" not in str(e.value) and "<redacted>" in str(e.value)


def test_instagram_asks_for_exactly_the_four_scopes(env):
    url = instagram.auth_url("https://api.example/cb", "st")
    assert "scope=" + "%2C".join(instagram.SCOPES) in url
    assert "client_id=ig-id" in url and "state=st" in url


def test_discord_connect_is_a_server_then_a_channel(env, monkeypatch):
    def fake(method, url, **kw):
        if url == discord.TOKEN_URL:
            return {"access_token": "USER-TOK", "refresh_token": "R", "expires_in": 604800,
                    "scope": "identify guilds bot", "guild": {"id": "g1", "name": "Phantra HQ", "icon": "ic"}}
        if url.endswith("/users/@me"):
            return {"id": "u9", "username": "mike"}
        if url.endswith("/guilds/g1/channels"):
            assert kw["headers"]["Authorization"] == "Bot bot-token-secret"
            return [{"id": "c0", "type": 4, "name": "General"},
                    {"id": "c1", "type": 0, "name": "showcase", "parent_id": "c0", "position": 2},
                    {"id": "c2", "type": 2, "name": "voice"},
                    {"id": "c3", "type": 5, "name": "news", "position": 0}]
        raise AssertionError(url)
    monkeypatch.setattr(discord, "_http", fake)
    got = discord.authenticate("code", "https://api.example/cb", {"guild_id": "g1"})
    assert got.pending == "channel" and got.external_id == "g1" and got.handle == "mike"
    assert got.avatar_url == f"{discord.CDN}/icons/g1/ic.png"
    row = social_connections.save(env["a"], "discord", got, dsn=env["dsn"])
    assert row["status"] == "pending"
    with pytest.raises(ConnectRefused, match="Finish connecting"):
        social_connections.token_for(env["a"], "discord", dsn=env["dsn"])
    opts = social_connections.options(env["a"], row["id"], dsn=env["dsn"])
    assert [o["id"] for o in opts] == ["c3", "c1"]          # text + announcement only
    with pytest.raises(ConnectRefused, match="not one the bot can post to"):
        social_connections.pick(env["a"], row["id"], "c2", dsn=env["dsn"])
    done = social_connections.pick(env["a"], row["id"], "c1", dsn=env["dsn"])
    assert done["status"] == "connected" and done["meta"]["channel_id"] == "c1"
    assert done["label"] == "Phantra HQ · #showcase"
    with pytest.raises(ConnectRefused, match="already finished"):
        social_connections.pick(env["a"], row["id"], "c1", dsn=env["dsn"])


def test_discord_without_the_bot_is_refused(env, monkeypatch):
    def fake(method, url, **kw):
        if url == discord.TOKEN_URL:
            return {"access_token": "USER-TOK", "scope": "identify"}
        raise AssertionError(url)
    monkeypatch.setattr(discord, "_http", fake)
    with pytest.raises(ConnectRefused, match="not added to a server"):
        discord.authenticate("code", "https://api.example/cb", {})


def test_the_catalogue_says_what_this_server_can_connect(env, monkeypatch):
    cat = {p["id"]: p for p in social.catalogue()}
    assert cat["discord"]["configured"] and cat["instagram"]["configured"]
    assert cat["discord"]["pending_step"] == "channel"
    monkeypatch.delenv(discord.BOT_TOKEN_ENV)
    assert not {p["id"]: p for p in social.catalogue()}["discord"]["configured"]


# --------------------------------------------------------------------------
# the door
# --------------------------------------------------------------------------

def _start(provider="instagram"):
    r = client.get(f"/auth/social/{provider}/start")
    assert r.status_code == 303, r.text
    return r.headers["location"]


def test_start_needs_this_origins_session(env):
    r = client.get("/auth/social/instagram/start")
    assert r.status_code == 303 and r.headers["location"].startswith("/signin?next=")


def test_start_goes_to_the_platform_with_a_signed_state(env):
    sign_in(env["ua"])
    url = _start()
    assert url.startswith(instagram.AUTHORIZE_URL)
    from urllib.parse import parse_qs, urlsplit
    q = parse_qs(urlsplit(url).query)
    assert q["redirect_uri"] == ["https://api.example/auth/social/instagram/callback"]
    state = social_routes.read_state(q["state"][0])
    assert state["a"] == env["a"] and state["u"] == env["ua"] and state["p"] == "instagram"


def test_callback_writes_the_row_for_the_workspace_in_the_state(env, monkeypatch):
    sign_in(env["ua"])
    url = _start()
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(url).query)["state"][0]
    monkeypatch.setattr(instagram, "authenticate", lambda code, uri, q: found())
    r = client.get(f"/auth/social/instagram/callback?code=abc&state={state}")
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://studio.example/studio/settings/connections?connected=instagram&id=")
    rows = social_connections.list_for(env["a"], dsn=env["dsn"])
    assert len(rows) == 1 and rows[0]["connected_by"] == env["ua"]
    assert social_connections.list_for(env["b"], dsn=env["dsn"]) == []


def test_callback_refuses_a_state_from_another_browser(env, monkeypatch):
    sign_in(env["ua"])
    url = _start()
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(url).query)["state"][0]
    monkeypatch.setattr(instagram, "authenticate", lambda code, uri, q: found())
    client.cookies.clear()                      # a different browser: no nonce
    r = client.get(f"/auth/social/instagram/callback?code=abc&state={state}")
    assert r.status_code == 303 and "error=" in r.headers["location"]
    assert social_connections.list_for(env["a"], dsn=env["dsn"]) == []


def test_callback_refuses_a_forged_or_stale_state(env, monkeypatch):
    sign_in(env["ua"])
    _start()
    monkeypatch.setattr(instagram, "authenticate", lambda code, uri, q: found())
    forged = auth_mod._serializer().dumps({"a": env["b"], "u": "", "p": "instagram", "n": "x"})
    r = client.get(f"/auth/social/instagram/callback?code=abc&state={forged}")
    assert "error=" in r.headers["location"]
    assert social_connections.list_for(env["b"], dsn=env["dsn"]) == []
    assert social_connections.list_for(env["a"], dsn=env["dsn"]) == []


def test_a_cancelled_consent_lands_with_the_reason(env):
    sign_in(env["ua"])
    url = _start()
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(url).query)["state"][0]
    r = client.get(f"/auth/social/instagram/callback?error=access_denied&state={state}")
    assert "error=Instagram" in r.headers["location"]


def test_a_refused_grant_lands_with_the_words_and_writes_nothing(env, monkeypatch):
    sign_in(env["ua"])
    url = _start()
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(url).query)["state"][0]

    def refuse(code, uri, q):
        raise ConnectRefused("Instagram was connected without permission to publish.")
    monkeypatch.setattr(instagram, "authenticate", refuse)
    r = client.get(f"/auth/social/instagram/callback?code=abc&state={state}")
    assert "permission+to+publish" in r.headers["location"]
    assert social_connections.list_for(env["a"], dsn=env["dsn"]) == []


def test_a_discord_callback_lands_on_the_channel_pick(env, monkeypatch):
    sign_in(env["ua"])
    url = _start("discord")
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(url).query)["state"][0]
    monkeypatch.setattr(discord, "authenticate", lambda code, uri, q: Connected(
        external_id="g1", display_name="HQ", access_token="T", pending="channel",
        meta={"guild_id": "g1", "guild_name": "HQ"}))
    r = client.get(f"/auth/social/discord/callback?code=abc&state={state}&guild_id=g1")
    assert "pick=" in r.headers["location"] and "connected=discord" in r.headers["location"]


def test_an_unconfigured_provider_never_leaves_the_studio(env, monkeypatch):
    sign_in(env["ua"])
    monkeypatch.delenv(instagram.APP_SECRET_ENV)
    r = client.get("/auth/social/instagram/start")
    assert r.status_code == 303 and "not+set+up" in r.headers["location"]
    assert client.get("/auth/social/myspace/start").status_code == 404


# --------------------------------------------------------------------------
# the settings page's routes
# --------------------------------------------------------------------------

def test_the_api_routes_are_one_accounts(env, monkeypatch):
    row = social_connections.save(env["a"], "instagram", found(), dsn=env["dsn"])
    sign_in(env["ua"], env["a"])
    got = client.get("/api/social/connections").json()["connections"]
    assert [c["id"] for c in got] == [row["id"]] and "token" not in str(got)
    providers = client.get("/api/social/providers").json()
    assert providers["vault_ready"] and {p["id"] for p in providers["providers"]} == {"discord", "instagram"}
    assert providers["providers"][0]["start_url"].startswith("/auth/social/")
    # the other workspace's person: nothing to see, nothing to delete
    sign_in(env["ub"], env["b"])
    assert client.get("/api/social/connections").json()["connections"] == []
    assert client.delete(f"/api/social/connections/{row['id']}").status_code == 404
    assert client.get(f"/api/social/connections/{row['id']}/options").status_code == 400
    sign_in(env["ua"], env["a"])
    assert client.delete(f"/api/social/connections/{row['id']}").status_code == 200
    assert client.get("/api/social/connections").json()["connections"] == []


def test_the_pick_route_finishes_a_pending_connection(env, monkeypatch):
    row = social_connections.save(env["a"], "discord", Connected(
        external_id="g1", display_name="HQ", access_token="T", pending="channel",
        meta={"guild_id": "g1", "guild_name": "HQ"}), dsn=env["dsn"])
    monkeypatch.setattr(discord, "options", lambda meta: [{"id": "c1", "label": "#showcase", "hint": ""}])
    sign_in(env["ua"], env["a"])
    assert client.get(f"/api/social/connections/{row['id']}/options").json()["options"][0]["id"] == "c1"
    bad = client.post(f"/api/social/connections/{row['id']}/pick", json={"choice": "c9"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "connect_refused"
    ok = client.post(f"/api/social/connections/{row['id']}/pick", json={"choice": "c1"}).json()
    assert ok["status"] == "connected" and ok["meta"]["channel_name"] == "#showcase"


# --------------------------------------------------------------------------
# publish_review.token_for
# --------------------------------------------------------------------------

def test_publish_prefers_the_persons_own_connection(env, monkeypatch):
    monkeypatch.setenv(publish_review.OPERATOR_ENV, "studio")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "operator-env-token")
    # no connection of their own: the operator's env token, for TikTok only
    assert publish_review.token_for(env["a"], "tiktok", dsn=env["dsn"]) == "operator-env-token"
    with pytest.raises(publish_review.PublishError, match="Connect your Instagram"):
        publish_review.token_for(env["a"], "instagram", dsn=env["dsn"])
    with pytest.raises(publish_review.PublishError, match="Connect your TikTok"):
        publish_review.token_for(env["b"], "tiktok", dsn=env["dsn"])
    # their own Instagram connection answers for instagram
    social_connections.save(env["a"], "instagram", found(access_token="MINE"), dsn=env["dsn"])
    assert publish_review.token_for(env["a"], "instagram", dsn=env["dsn"]) == "MINE"
    # ...and one that needs reconnecting is said so, never the operator's token
    social_connections.save(env["a"], "instagram", found(access_token="LATE", expires_in=1), dsn=env["dsn"])
    monkeypatch.setattr(social_connections, "_now",
                        lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(publish_review.PublishError, match="expired"):
        publish_review.token_for(env["a"], "instagram", dsn=env["dsn"])
