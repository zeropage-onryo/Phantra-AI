"""The editing-app panels' sign-in and door (2026-10-22,
docs/tasks/task-premiere-plugin.md; src/plugin_tokens.py, app/plugin_api.py).

What these pin, in the order a mistake would cost:

- a code signs in ONLY the panel that holds its secret, approves once, dies
  after ten minutes, and is approved only by a signed-in person through the
  studio's guarded header (no background form from another site);
- the token is stored as a hash, acts as the APPROVER's tenant and person,
  reaches only PLUGIN_TOOLS, stops at once when revoked (by the person in
  the studio, or the panel signing out), and someone else's connection is
  as missing as one that never existed;
- the caller's account is set for one tool call and reset after it, even
  when the tool refuses;
- a spending tool through this door is the connector's own: no token, a
  quote and nothing spent; a token that is not that quote's, refused.
"""
import pytest
from fastapi.testclient import TestClient
from test_auth import JWT_SECRET, FakeGoTrue

from app import auth as auth_mod
from app import plugin_api
from app.main import app
from src import accounts, db, mcp_server, plugin_tokens, render_assets

client = TestClient(app)
GUARD = {"X-Phantra-Model-Connection": "1"}


@pytest.fixture(autouse=True)
def clean_slate(pg, monkeypatch, account_scope):
    app.dependency_overrides.pop(auth_mod.current_account_id, None)
    accounts.init(pg)
    plugin_tokens.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-for-real-use")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("STUDIO_URL", "https://studio.example.test")
    auth_mod._hits.clear()
    plugin_api._limiter().reset()
    client.cookies.clear()
    return pg


@pytest.fixture
def people(clean_slate, monkeypatch):
    """Mike (two workspaces; the oldest is his tenant) and Ana in her own."""
    fake = FakeGoTrue()
    monkeypatch.setattr(auth_mod, "gotrue", fake)
    out = {}
    for name in ("mike", "ana"):
        uid = fake.register(f"{name}@example.com", f"{name}s-password-1", uid=f"uid-{name}")
        accounts.create_user(f"{name}@example.com", user_id=uid, claimed=True, dsn=clean_slate)
        out[name] = uid
    mikes = accounts.upsert_account("phantra", "Phantra AI", "#e4002b", dsn=clean_slate)
    second = accounts.upsert_account("second-studio", "Second Studio", "#d64550",
                                     dsn=clean_slate)
    anas = accounts.upsert_account("anas-studio", "Ana", "#000000", dsn=clean_slate)
    accounts.add_member(mikes, out["mike"], dsn=clean_slate)
    accounts.add_member(second, out["mike"], dsn=clean_slate)
    accounts.add_member(anas, out["ana"], dsn=clean_slate)
    out.update(mikes=mikes, second=second, anas=anas)
    return out


def _sign_in(name):
    client.cookies.clear()
    response = client.post("/auth/login", data={"email": f"{name}@example.com",
                                                "password": f"{name}s-password-1"},
                           follow_redirects=False)
    assert response.status_code == 303


def _pair(device="Mike's MacBook", app="premiere"):
    response = client.post("/plugin/v1/pair", json={"client": app, "device": device})
    assert response.status_code == 200, response.text
    return response.json()


def _connect(name, app="premiere"):
    """A panel signed in as `name`: the token it ends up holding."""
    started = _pair(app=app)
    _sign_in(name)
    approved = client.post("/api/plugin/link", json={"code": started["code"]}, headers=GUARD)
    assert approved.status_code == 200, approved.text
    client.cookies.clear()
    polled = client.post("/plugin/v1/pair/token", json={"secret": started["secret"]})
    assert polled.status_code == 200, polled.text
    return polled.json()["token"]


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- the module ----------

def test_a_pairing_hands_out_a_code_a_link_and_a_secret(clean_slate):
    started = _pair()
    assert started["secret"].startswith("php_") and len(started["secret"]) > 40
    code = started["code"]
    assert len(code) == 9 and code[4] == "-"
    assert all(ch in plugin_tokens.CODE_ALPHABET for ch in code.replace("-", ""))
    # never the code in the address: a pre-filled link is a one-click phishing kit
    assert started["link_url"] == "https://studio.example.test/studio/link"
    assert code not in started["link_url"]
    assert started["client"] == "Premiere Pro"
    assert started["expires_in"] == plugin_tokens.PAIRING_SECONDS
    # the secret itself is stored nowhere: only its hash
    with db.connect(clean_slate) as conn:
        dumped = str(conn.execute("SELECT * FROM plugin_pairings").fetchall())
    assert started["secret"] not in dumped


def test_a_resolve_panel_signs_in_and_is_named_everywhere(clean_slate, people):
    started = _pair(device="macOS, DaVinci Resolve 20.2", app="resolve")
    assert started["client"] == "DaVinci Resolve"
    _sign_in("mike")
    seen = client.get("/api/plugin/link", params={"code": started["code"]})
    assert seen.json()["client"] == "DaVinci Resolve"
    assert client.post("/api/plugin/link", json={"code": started["code"]}, headers=GUARD).status_code == 200
    listed = client.get("/api/plugin/connections").json()
    assert [c["client"] for c in listed["items"]] == ["DaVinci Resolve"]
    client.cookies.clear()
    token = client.post("/plugin/v1/pair/token", json={"secret": started["secret"]}).json()["token"]
    me = client.get("/plugin/v1/me", headers=_bearer(token)).json()
    assert me["client"] == "DaVinci Resolve"


def test_an_unknown_client_is_refused(clean_slate):
    response = client.post("/plugin/v1/pair", json={"client": "final-cut"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_client"


def test_a_typed_code_is_forgiven_its_case_spaces_and_dash():
    assert plugin_tokens.normalize_code(" kdpx 7qhr ") == "KDPX7QHR"
    assert plugin_tokens.normalize_code("KDPX-7QHR") == "KDPX7QHR"


def test_polling_waits_until_approved(people, clean_slate):
    started = _pair()
    polled = client.post("/plugin/v1/pair/token", json={"secret": started["secret"]})
    assert polled.status_code == 400
    assert polled.json()["error"]["code"] == "authorization_pending"
    assert client.post("/plugin/v1/pair/token",
                       json={"secret": "php_not-a-real-one"}).json()["error"]["code"] == \
        "invalid_grant"


def test_an_expired_code_cannot_be_approved_and_says_so(people, clean_slate):
    started = _pair()
    with db.connect(clean_slate) as conn:
        conn.execute("UPDATE plugin_pairings SET expires_at = now() - interval '1 second'")
    _sign_in("mike")
    refused = client.post("/api/plugin/link", json={"code": started["code"]}, headers=GUARD)
    assert refused.status_code == 400 and refused.json()["error"]["code"] == "expired"
    client.cookies.clear()
    polled = client.post("/plugin/v1/pair/token", json={"secret": started["secret"]})
    assert polled.json()["error"]["code"] == "expired_token"


# ---------- approving a code ----------

def test_approving_needs_a_signed_in_person(people, clean_slate):
    started = _pair()
    response = client.post("/api/plugin/link", json={"code": started["code"]}, headers=GUARD)
    assert response.status_code == 401


def test_approving_needs_the_studios_guarded_header(people, clean_slate):
    """A form on another site cannot set a custom header, so it cannot
    sign its own panel in to a visitor's workspace in the background."""
    started = _pair()
    _sign_in("mike")
    response = client.post("/api/plugin/link", json={"code": started["code"]})
    assert response.status_code == 403
    assert plugin_tokens.poll(started["secret"], dsn=clean_slate) == "pending"


def test_the_link_page_names_the_app_before_the_click(people, clean_slate):
    started = _pair(device="Edit Bay 2")
    _sign_in("mike")
    seen = client.get("/api/plugin/link", params={"code": started["code"].lower()})
    assert seen.status_code == 200
    assert seen.json()["client"] == "Premiere Pro" and seen.json()["device"] == "Edit Bay 2"
    # the workspace the approval binds: Mike's tenant, whichever one is open
    assert seen.json()["workspace"] == "Phantra AI"
    assert client.get("/api/plugin/link", params={"code": "BBBB-BBBB"}).status_code == 404


def test_a_code_approves_once(people, clean_slate):
    started = _pair()
    _sign_in("mike")
    assert client.post("/api/plugin/link", json={"code": started["code"]},
                       headers=GUARD).status_code == 200
    _sign_in("ana")
    again = client.post("/api/plugin/link", json={"code": started["code"]}, headers=GUARD)
    assert again.status_code == 400 and again.json()["error"]["code"] == "already_used"
    assert client.post("/api/plugin/link", json={"code": "ZZZZ-ZZZZ"},
                       headers=GUARD).json()["error"]["code"] == "bad_code"


def test_the_token_is_the_approvers_tenant_and_person(people, clean_slate):
    token = _connect("mike")
    me = client.get("/plugin/v1/me", headers=_bearer(token))
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["client"] == "Premiere Pro"
    assert body["whoami"]["workspace"]["id"] == people["mikes"]      # oldest membership
    assert body["whoami"]["signed_in_person"] is True
    with db.connect(clean_slate) as conn:
        row = conn.execute("SELECT account_id, user_id, token_hash FROM plugin_tokens"
                           ).fetchone()
    assert (row["account_id"], row["user_id"]) == (people["mikes"], people["mike"])
    assert token not in str(row)


def test_two_people_get_their_own_workspaces(people, clean_slate):
    mike, ana = _connect("mike"), _connect("ana")
    seen = {name: client.get("/plugin/v1/me", headers=_bearer(t)).json()["whoami"]
            ["workspace"]["id"] for name, t in (("mike", mike), ("ana", ana))}
    assert seen == {"mike": people["mikes"], "ana": people["anas"]}


# ---------- the door ----------

def test_no_token_or_a_wrong_one_is_a_plain_401(people, clean_slate):
    assert client.get("/plugin/v1/me").status_code == 401
    assert client.get("/plugin/v1/me", headers=_bearer("php_nope")).status_code == 401
    assert client.post("/plugin/v1/tools/whoami",
                       headers=_bearer("not-even-ours")).status_code == 401


def test_only_the_panels_tools_are_reachable(people, clean_slate):
    token = _connect("mike")
    for name in ("project_chat", "save_recipe", "apply_effect", "generate_video", "nope"):
        response = client.post(f"/plugin/v1/tools/{name}", json={}, headers=_bearer(token))
        assert response.status_code == 404, name
    listed = set(plugin_api.PLUGIN_TOOLS) - set(plugin_api.STUDIO_SURFACE_TOOLS)
    assert listed <= set(mcp_server.LISTED_TOOLS)
    assert set(plugin_api.STUDIO_SURFACE_TOOLS) <= set(mcp_server.STUDIO_TOOLS)


@pytest.fixture
def full_schema(clean_slate):
    """Every table the app has (the tools read scenes, the cut bin, the
    wall), in this test's schema: DATABASE_URL already points at it."""
    from app import main as app_main
    app_main.init_tables()
    return clean_slate


def _render(account_id, prompt, dsn):
    return render_assets.record(generation_id=abs(hash(prompt)) % 10_000, tool="fal",
                                model="flux-pro1.1", media_kind="image", prompt=prompt,
                                media_url=f"/renders/fal/{prompt[:8]}.png", dsn=dsn,
                                account_id=account_id)


def test_the_library_is_the_callers_own(people, full_schema, monkeypatch):
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    mine = _render(people["mikes"], "mike's mug on walnut", full_schema)
    hers = _render(people["anas"], "ana's lamp at dusk", full_schema)
    token = _connect("mike")
    listed = client.post("/plugin/v1/tools/library", json={"kind": "image"},
                         headers=_bearer(token))
    assert listed.status_code == 200, listed.text
    ids = [i["id"] for i in listed.json()["result"]["items"]]
    assert f"gen:{mine['id']}" in ids and f"gen:{hers['id']}" not in ids
    # her render's file is as missing as one that never existed
    theirs = client.get(f"/plugin/v1/download/gen:{hers['id']}", headers=_bearer(token),
                        follow_redirects=False)
    assert theirs.status_code == 404
    assert client.get("/plugin/v1/download/asset:1", headers=_bearer(token)).status_code == 400


def test_a_crash_is_said_plainly_and_keeps_its_text_here(people, clean_slate, capsys):
    """The bare schema has no scenes table: the tool crashes, the panel is
    told plainly, and the database's words stay in the server's log."""
    token = _connect("mike")
    crashed = client.post("/plugin/v1/tools/scene", json={"scene_id": 1},
                          headers=_bearer(token))
    assert crashed.status_code == 500
    assert crashed.json()["error"]["code"] == "tool_failed"
    assert "shoot_concepts" not in crashed.text
    assert "UndefinedTable" in capsys.readouterr().err


def test_a_refusal_reads_in_the_connectors_words(people, full_schema):
    token = _connect("mike")
    ok = client.post("/plugin/v1/tools/whoami", json={}, headers=_bearer(token))
    assert ok.status_code == 200 and ok.json()["result"]["workspace"]["id"] == people["mikes"]
    refused = client.post("/plugin/v1/tools/scene", json={"scene_id": 987654},
                          headers=_bearer(token))
    assert refused.status_code == 400 and refused.json()["error"]["code"] == "refused"
    assert not refused.json()["error"]["message"].startswith("Error executing tool")


def test_bad_arguments_are_a_refusal_not_a_crash(people, full_schema):
    token = _connect("mike")
    response = client.post("/plugin/v1/tools/library", json={"limit": "lots"},
                           headers=_bearer(token))
    assert response.status_code == 400
    response = client.post("/plugin/v1/tools/library", content=b"[1, 2]",
                           headers={**_bearer(token), "Content-Type": "application/json"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "bad_json"


def test_an_image_through_the_panel_is_the_connectors_quote(people, clean_slate, monkeypatch):
    """No token: a price and nothing spent. A token that is not this
    quote's: refused, nothing started."""
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "quote-secret-for-tests")
    started = []
    monkeypatch.setattr(mcp_server, "run_image",
                        _guard_run_image(mcp_server.run_image, started))
    token = _connect("mike")
    quoted = client.post("/plugin/v1/tools/generate_image",
                         json={"prompt": "a ceramic mug on a walnut desk, morning light"},
                         headers=_bearer(token))
    assert quoted.status_code == 200, quoted.text
    result = quoted.json()["result"]
    assert result["ok"] is False and result["needs_approval"] is True
    assert result.get("can_approve") is True
    assert isinstance(_find(result, "credits"), int)
    assert _find(result, "quote_token")
    assert started == []
    forged = client.post("/plugin/v1/tools/generate_image",
                         json={"prompt": "a ceramic mug on a walnut desk, morning light",
                               "quote_token": "phs.forged.token"}, headers=_bearer(token))
    assert forged.status_code == 400
    assert forged.json()["error"]["message"].startswith("bad_signature")
    assert started == []


def _guard_run_image(real, started):
    def run(*args, **kwargs):
        if kwargs.get("quote_token") and not kwargs.get("dry_run"):
            started.append(kwargs)
        return real(*args, **kwargs)
    return run


def _find(payload, key):
    """A key wherever the quote nests it (price fields ride beside the note)."""
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find(value, key)
            if found is not None:
                return found
    return None


# ---------- disconnecting ----------

def test_the_studio_lists_and_disconnects_only_the_persons_own(people, clean_slate):
    mike = _connect("mike")
    _connect("ana")
    _sign_in("mike")
    listed = client.get("/api/plugin/connections").json()["items"]
    assert [i["client"] for i in listed] == ["Premiere Pro"]
    mine = listed[0]["id"]
    _sign_in("ana")
    anas = client.get("/api/plugin/connections").json()["items"]
    assert len(anas) == 1 and anas[0]["id"] != mine
    assert client.post(f"/api/plugin/connections/{mine}/revoke",
                       headers=GUARD).status_code == 404            # not hers
    _sign_in("mike")
    assert client.post(f"/api/plugin/connections/{mine}/revoke").status_code == 403
    assert client.post(f"/api/plugin/connections/{mine}/revoke",
                       headers=GUARD).status_code == 200
    client.cookies.clear()
    assert client.get("/plugin/v1/me", headers=_bearer(mike)).status_code == 401


def test_the_panel_can_sign_itself_out(people, clean_slate):
    token = _connect("mike")
    assert client.post("/plugin/v1/signout", headers=_bearer(token)).json()["revoked"] is True
    assert client.get("/plugin/v1/me", headers=_bearer(token)).status_code == 401
    started = _pair()
    assert plugin_tokens.poll(token, dsn=clean_slate) == "unknown"
    assert started["secret"] != token


def test_code_guessing_is_braked(people, clean_slate):
    _sign_in("mike")
    codes = [client.post("/api/plugin/link", json={"code": "ZZZZ-ZZZZ"},
                         headers=GUARD).status_code for _ in range(12)]
    assert codes[:10] == [400] * 10 and 429 in codes[10:]


def test_a_rendered_scenes_clips_come_as_addresses_for_its_owner_only(people, full_schema):
    from src import preprod
    shot = {"n": 1, "type": "BROLL", "source": "AI", "tool": "FAL", "desc": "d",
            "prompt": "a woman lifts the lid of a ceramic mug", "refs": [],
            "media_url": "/renders/fal/clip-1-0123456789abcdef0123456789abcdef.mp4"}
    mine = preprod.save_concept({"title": "Mug reveal", "hook": "", "logline": "",
                                 "shots": [shot]}, prompt_template="T", dsn=full_schema,
                                account_id=people["mikes"])
    hers = preprod.save_concept({"title": "Lamp", "hook": "", "logline": "",
                                 "shots": [shot]}, prompt_template="T", dsn=full_schema,
                                account_id=people["anas"])
    token = _connect("mike")
    assert client.get(f"/plugin/v1/scenes/{mine}/clips").status_code == 401
    got = client.get(f"/plugin/v1/scenes/{mine}/clips", headers=_bearer(token))
    assert got.status_code == 200, got.text
    clips = got.json()["clips"]
    assert len(clips) == 1 and clips[0]["url"].endswith(".mp4")
    assert client.get(f"/plugin/v1/scenes/{hers}/clips",
                      headers=_bearer(token)).status_code == 404


# ---------- the review's findings (2026-10-22), each pinned ----------

def test_the_callers_account_is_reset_in_the_handlers_own_context(people, clean_slate,
                                                                   monkeypatch):
    """The reset is checked where it happens: run_tool sets the account in
    the context it runs in, so after it returns -- normally or through a
    crash -- that context must hold nothing."""
    import asyncio

    seen = []

    class Server:
        def __init__(self, crash):
            self.crash = crash

        async def call_tool(self, name, args):
            seen.append(mcp_server.CALLER_ACCOUNT.get())
            if self.crash:
                raise RuntimeError("boom")
            return ([], {"ok": True})

    caller = {"account_id": people["anas"], "user_id": people["ana"]}

    async def go(crash):
        monkeypatch.setattr(plugin_api, "_listed_server", lambda: Server(crash))
        await plugin_api.run_tool("whoami", {}, caller)
        return mcp_server.CALLER_ACCOUNT.get(), mcp_server.CALLER_USER.get()

    assert asyncio.run(go(False)) == (None, None)
    assert asyncio.run(go(True)) == (None, None)
    assert seen == [people["anas"], people["anas"]]


def test_a_caller_who_is_not_the_bootstrap_account_sees_only_their_own(people, full_schema,
                                                                       monkeypatch):
    """Mike's workspace is the oldest, which is also where an unset caller
    falls through to -- so the fence is proved with Ana's token."""
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    his = _render(people["mikes"], "mike's mug on walnut", full_schema)
    hers = _render(people["anas"], "ana's lamp at dusk", full_schema)
    token = _connect("ana")
    who = client.post("/plugin/v1/tools/whoami", json={}, headers=_bearer(token)).json()
    assert who["result"]["workspace"]["id"] == people["anas"]
    ids = [i["id"] for i in client.post("/plugin/v1/tools/library", json={},
                                        headers=_bearer(token)).json()["result"]["items"]]
    assert f"gen:{hers['id']}" in ids and f"gen:{his['id']}" not in ids


def test_a_token_is_never_more_than_the_membership_behind_it(people, clean_slate):
    token = _connect("ana")
    assert client.get("/plugin/v1/me", headers=_bearer(token)).status_code == 200
    with db.connect(clean_slate) as conn:
        conn.execute("DELETE FROM account_members WHERE account_id = %s AND user_id = %s",
                     (people["anas"], people["ana"]))
    assert client.get("/plugin/v1/me", headers=_bearer(token)).status_code == 401


def test_a_panel_left_unused_signs_in_again(people, clean_slate):
    token = _connect("mike")
    with db.connect(clean_slate) as conn:
        conn.execute("UPDATE plugin_tokens SET last_used_at = now() - make_interval(days => %s),"
                     " created_at = now() - make_interval(days => %s)",
                     (plugin_tokens.IDLE_DAYS + 1, plugin_tokens.IDLE_DAYS + 5))
    assert client.get("/plugin/v1/me", headers=_bearer(token)).status_code == 401


def test_no_spending_door_opens_on_a_server_that_signs_no_quotes(people, clean_slate,
                                                                  monkeypatch):
    """Without QUOTE_SIGNING_SECRET `approve` takes no token at all, so the
    panel's door refuses every spending tool rather than spend on a bare call."""
    monkeypatch.delenv("QUOTE_SIGNING_SECRET", raising=False)
    token = _connect("mike")
    for name, args in (("approve", {"scene_id": 1}),
                       ("generate_image", {"prompt": "a mug on a desk in morning light"})):
        refused = client.post(f"/plugin/v1/tools/{name}", json=args, headers=_bearer(token))
        assert refused.status_code == 503, name
        assert refused.json()["error"]["code"] == "cannot_approve"
    assert set(plugin_api.SPENDING_TOOLS) <= set(plugin_api.PLUGIN_TOOLS)


def test_a_strange_digit_in_a_download_ref_is_a_refusal_not_a_crash(people, clean_slate):
    token = _connect("mike")
    for ref in ("gen:\u00b2", "gen:1x", "gen:", "asset:3"):
        assert client.get(f"/plugin/v1/download/{ref}",
                          headers=_bearer(token)).status_code == 400, ref


def test_a_forged_forwarded_for_does_not_reset_the_brake(clean_slate):
    """uvicorn trusts X-Forwarded-For from anywhere, so the brake keys on
    Fly's own Fly-Client-IP: a caller who rewrites XFF on every request is
    still one caller."""
    codes = [client.post("/plugin/v1/pair", json={"client": "premiere"},
                         headers={"Fly-Client-IP": "203.0.113.9",
                                  "X-Forwarded-For": f"6.6.6.{i}"}).status_code
             for i in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]
    # a different real address has its own allowance
    assert client.post("/plugin/v1/pair", json={"client": "premiere"},
                       headers={"Fly-Client-IP": "198.51.100.4"}).status_code == 200


def test_dead_pairings_are_swept(clean_slate):
    _pair()
    with db.connect(clean_slate) as conn:
        conn.execute("UPDATE plugin_pairings SET expires_at = now() - interval '2 days'")
    _pair()
    with db.connect(clean_slate) as conn:
        assert conn.execute("SELECT count(*) AS n FROM plugin_pairings").fetchone()["n"] == 1


def test_the_panels_description_of_itself_is_kept_plain(clean_slate):
    _pair(device="<b>Phantra Support</b> \u202e urgent!!")
    with db.connect(clean_slate) as conn:
        device = conn.execute("SELECT device FROM plugin_pairings").fetchone()["device"]
    assert "<" not in device and "\u202e" not in device and "!" not in device


# ---------- a file from the timeline (2026-10-22) ----------

def _png_bytes():
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 18), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _mp4_bytes(tmp_path, seconds=2):
    import subprocess
    out = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"testsrc=size=320x180:rate=24:duration={seconds}", "-pix_fmt", "yuv420p",
                    str(out)], check=True)
    return out.read_bytes()


needs_ffmpeg = pytest.mark.skipif(not __import__("shutil").which("ffmpeg"),
                                  reason="ffmpeg is not installed")


def test_a_frame_from_the_timeline_lands_in_the_library(people, full_schema):
    token = _connect("mike")
    assert client.post("/plugin/v1/upload", content=_png_bytes()).status_code == 401
    sent = client.post("/plugin/v1/upload", content=_png_bytes(),
                       headers={**_bearer(token), "Content-Type": "application/octet-stream"})
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assert body["asset"].startswith("asset:") and body["kind"] == "image"
    items = client.post("/plugin/v1/tools/library", json={"kind": "upload"},
                        headers=_bearer(token)).json()["result"]["items"]
    assert body["asset"] in [i["id"] for i in items]


def test_an_upload_is_judged_by_its_bytes(people, full_schema):
    token = _connect("mike")
    for data in (b"", b"#!/bin/sh\necho not a picture", b"%PDF-1.7 a document"):
        refused = client.post("/plugin/v1/upload", content=data,
                              headers={**_bearer(token),
                                       "Content-Type": "application/octet-stream"})
        assert refused.status_code == 400, data[:10]


def test_an_upload_over_the_cap_is_refused_before_it_is_read(people, full_schema):
    from app import upload_page
    token = _connect("mike")
    refused = client.post("/plugin/v1/upload", content=b"x",
                          headers={**_bearer(token), "Content-Length": str(upload_page.VIDEO_CAP + 1)})
    assert refused.status_code == 413


@needs_ffmpeg
def test_a_timeline_clip_is_edited_through_the_studios_own_two_step(people, full_schema,
                                                                     tmp_path, monkeypatch):
    """A clip sent up from the timeline, then `edit_clip`'s first step --
    the frame -- priced through the panel's door: a quote, the price of the
    whole clip on every model beside it, and nothing spent."""
    from src import ledger
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "quote-secret-for-tests")
    ledger.ensure(full_schema)
    ledger.grant(people["mikes"], 500, "purchase", dsn=full_schema)
    token = _connect("mike")
    sent = client.post("/plugin/v1/upload", content=_mp4_bytes(tmp_path, seconds=4),
                       headers={**_bearer(token), "Content-Type": "application/octet-stream"})
    assert sent.status_code == 200, sent.text
    clip = sent.json()
    assert clip["kind"] == "video" and clip["seconds"]
    quoted = client.post("/plugin/v1/tools/edit_clip",
                         json={"source": clip["asset"], "stage": "frame", "at": 0.5,
                               "instruction": "make it look like a rainy night in neon"},
                         headers=_bearer(token))
    assert quoted.status_code == 200, quoted.text
    result = quoted.json()["result"]
    assert result["needs_approval"] is True
    assert result["quote"]["stage"] == "frame" and result["quote"]["quote_token"]
    assert result["quote"]["then"], "the clip's price on each model rides with the frame's"
    assert any(isinstance(o.get("credits"), int) for o in result["quote"]["then"])
    with db.connect(full_schema) as conn:
        assert conn.execute("SELECT count(*) AS n FROM credit_entries WHERE kind = 'hold'"
                            ).fetchone()["n"] == 0      # a quote holds nothing
