"""ops/connector_walk.py: the connector's own OAuth client and reviewer walker,
checked with no network and no database (docs/tasks/task-connector-submission.md,
step 1). A fake HTTP layer answers canned documents; a fake door answers canned
tool results; what is asserted is the shape of what the client sends, what it
writes, and that no token ever reaches a file it should not.
"""

import json
import os
import stat

import pytest

from ops import connector_walk as cw

AS = "https://ewkbrenbjsiggufegrnd.supabase.co/auth/v1"
AS_DOC = {"issuer": AS,
          "authorization_endpoint": AS + "/oauth/authorize",
          "token_endpoint": AS + "/oauth/token",
          "registration_endpoint": AS + "/oauth/clients/register",
          "code_challenge_methods_supported": ["S256", "plain"]}
RFC_FORM = "https://ewkbrenbjsiggufegrnd.supabase.co/.well-known/oauth-authorization-server/auth/v1"


def reply(status, body="", headers=None):
    headers = dict(headers or {})
    if isinstance(body, (dict, list)):
        body = json.dumps(body)
        headers.setdefault("content-type", "application/json")
    return cw.Reply(status, headers, body)


class FakeHttp:
    """Routes (method, url-without-query) -> a Reply, or a callable taking the
    request keywords. Every request is recorded."""

    def __init__(self, routes):
        self.routes = dict(routes)
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        handler = self.routes.get((method, url.split("?")[0]))
        if handler is None:
            raise AssertionError(f"unexpected {method} {url}")
        return handler(kw) if callable(handler) else handler


def discovery_routes(door="claude", rfc_form=False):
    path = cw.DOORS[door]
    meta_url = f"{cw.API}/.well-known/oauth-protected-resource{path}"
    routes = {
        ("POST", cw.API + path): reply(401, {"error": "unauthorized"},
                                      {"www-authenticate": f'Bearer resource_metadata="{meta_url}"'}),
        ("GET", meta_url): reply(200, {"resource": cw.API + path, "authorization_servers": [AS],
                                       "bearer_methods_supported": ["header"]}),
    }
    if rfc_form:
        routes[("GET", AS + "/.well-known/oauth-authorization-server")] = reply(404, "not here")
        routes[("GET", RFC_FORM)] = reply(200, AS_DOC)
    else:
        routes[("GET", AS + "/.well-known/oauth-authorization-server")] = reply(200, AS_DOC)
    return routes


# --- discovery ----------------------------------------------------------------

def test_the_challenge_names_the_metadata_document():
    url = cw.parse_challenge('Bearer resource_metadata="https://x/.well-known/oauth-protected-resource/mcp"')
    assert url == "https://x/.well-known/oauth-protected-resource/mcp"
    with pytest.raises(cw.WalkError):
        cw.parse_challenge("Bearer")


@pytest.mark.parametrize("door", ["claude", "render"])
def test_discovery_follows_the_401_to_the_authorization_server(door):
    http = FakeHttp(discovery_routes(door))
    disc = cw.discover(door, http)
    assert disc["url"] == cw.API + cw.DOORS[door]
    assert disc["resource"] == cw.API + cw.DOORS[door]
    assert disc["issuer"] == AS
    assert disc["as"]["token_endpoint"] == AS + "/oauth/token"
    # the unsigned probe carried the streamable-HTTP Accept header
    method, url, kw = http.calls[0]
    assert (method, url) == ("POST", cw.API + cw.DOORS[door])
    assert kw["headers"]["Accept"] == cw.ACCEPT


def test_discovery_falls_back_to_the_rfc_8414_form():
    http = FakeHttp(discovery_routes(rfc_form=True))
    disc = cw.discover("claude", http)
    assert disc["as"]["authorization_endpoint"] == AS + "/oauth/authorize"
    assert [u for m, u, _ in http.calls if m == "GET"][-1] == RFC_FORM


def test_as_metadata_urls_try_the_issuer_form_then_the_rfc_form():
    assert cw.as_metadata_urls(AS) == [AS + "/.well-known/oauth-authorization-server", RFC_FORM]
    assert cw.as_metadata_urls("https://as.example") == [
        "https://as.example/.well-known/oauth-authorization-server"]


def test_a_door_that_does_not_answer_401_is_refused():
    routes = discovery_routes()
    routes[("POST", cw.API + "/mcp/claude")] = reply(307, "", {"location": "/mcp/"})
    with pytest.raises(cw.WalkError, match="307"):
        cw.discover("claude", FakeHttp(routes))


def test_an_unknown_door_is_refused():
    with pytest.raises(cw.WalkError):
        cw.door_url("board")


# --- PKCE, registration, the authorize URL ----------------------------------------

def test_pkce_is_s256_over_an_unpadded_urlsafe_verifier():
    import base64
    import hashlib

    verifier, challenge = cw.pkce()
    assert 43 <= len(verifier) <= 128
    assert "=" not in verifier and "=" not in challenge
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected
    assert cw.pkce()[0] != verifier


def test_registration_is_a_public_client_with_the_loopback_redirect():
    http = FakeHttp({("POST", AS + "/oauth/clients/register"):
                     reply(201, {"client_id": "cid-1", "redirect_uris": [cw.REDIRECT]})})
    doc = cw.register_client(AS_DOC, http)
    assert doc["client_id"] == "cid-1"
    body = http.calls[0][2]["json_body"]
    assert body["redirect_uris"] == ["http://localhost:53682/callback"]
    assert body["token_endpoint_auth_method"] == "none"
    assert body["grant_types"] == ["authorization_code", "refresh_token"]
    assert body["response_types"] == ["code"]


def test_a_registration_without_a_client_id_is_refused():
    http = FakeHttp({("POST", AS + "/oauth/clients/register"): reply(201, {"ok": True})})
    with pytest.raises(cw.WalkError, match="client_id"):
        cw.register_client(AS_DOC, http)


def test_the_authorize_url_carries_pkce_state_and_the_loopback_redirect():
    from urllib.parse import parse_qs, urlsplit

    url = cw.authorize_url(AS_DOC, "cid-1", "chal", "st8")
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == AS + "/oauth/authorize"
    q = parse_qs(parts.query)
    assert q["code_challenge"] == ["chal"] and q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["http://localhost:53682/callback"]
    assert q["state"] == ["st8"] and q["client_id"] == ["cid-1"] and q["response_type"] == ["code"]
    assert "scope" not in q
    assert "scope=openid" in cw.authorize_url(AS_DOC, "cid-1", "chal", "st8", scope="openid")


# --- the session file ---------------------------------------------------------------

def _disc(door="claude"):
    return {"door": door, "url": cw.door_url(door), "resource": cw.door_url(door),
            "issuer": AS, "as": AS_DOC, "metadata_url": "x"}


def test_the_session_file_is_owner_only(tmp_path):
    session = cw.session_from_tokens("claude", _disc(), "cid-1",
                                     {"access_token": "at-1", "refresh_token": "rt-1",
                                      "expires_in": 3600}, now=1000.0)
    path = cw.session_path("claude", tmp_path / "sessions")
    cw.write_session(path, session)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700
    back = json.loads(path.read_text())
    assert back["access_token"] == "at-1" and back["refresh_token"] == "rt-1"
    assert back["expires_at"] == 4600.0 and back["client_id"] == "cid-1"
    assert back["token_endpoint"] == AS + "/oauth/token"
    # a rewrite keeps the mode
    cw.write_session(path, {**session, "access_token": "at-2"})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_a_refresh_keeps_the_old_refresh_token_when_none_comes_back():
    previous = cw.session_from_tokens("claude", _disc(), "cid-1",
                                      {"access_token": "at-1", "refresh_token": "rt-1"}, now=0.0)
    previous["whoami"] = {"workspace": {"slug": "zp-billing-test"}}
    fresh = cw.session_from_tokens("claude", _disc(), "cid-1", {"access_token": "at-2"},
                                   now=10.0, previous=previous)
    assert fresh["refresh_token"] == "rt-1" and fresh["access_token"] == "at-2"
    assert fresh["whoami"]["workspace"]["slug"] == "zp-billing-test"


def test_the_render_door_reuses_the_claude_session(tmp_path):
    root = tmp_path / "s"
    cw.write_session(cw.session_path("claude", root),
                     cw.session_from_tokens("claude", _disc(), "cid", {"access_token": "at"}, now=0))
    session, path = cw.load_session("render", root)
    assert session["access_token"] == "at" and path.name == "claude.json"
    door = cw.Door("render", session, path, FakeHttp({}))
    assert door.url == cw.API + "/mcp"            # the request goes to the render door
    assert door.session["url"] == cw.API + "/mcp/claude"   # the file stays the Claude door's


def test_no_session_says_how_to_sign_in(tmp_path):
    with pytest.raises(cw.WalkError, match="signin --door render"):
        cw.load_session("render", tmp_path)
    with pytest.raises(cw.WalkError, match="signin --door claude"):
        cw.load_session("claude", tmp_path)


# --- the caller -----------------------------------------------------------------------

def _sse(*messages):
    return "".join(f"event: message\r\ndata: {json.dumps(m)}\r\n\r\n" for m in messages)


def test_the_reply_is_read_off_sse_or_json():
    rpc = {"jsonrpc": "2.0", "id": 2, "result": {"ok": True}}
    sse = cw.Reply(200, {"content-type": "text/event-stream"},
                   _sse({"jsonrpc": "2.0", "method": "notifications/message", "params": {}}, rpc))
    assert cw.parse_rpc_reply(sse, 2)["result"] == {"ok": True}
    plain = cw.Reply(200, {"content-type": "application/json"}, json.dumps(rpc))
    assert cw.parse_rpc_reply(plain, 2)["result"] == {"ok": True}
    with pytest.raises(cw.WalkError):
        cw.parse_rpc_reply(cw.Reply(200, {"content-type": "text/event-stream"}, ""), 2)


def test_a_tool_answer_is_structured_content_or_the_text_as_json():
    assert cw.unwrap_result({"content": [{"type": "text", "text": '{"a": 1}'}],
                             "structuredContent": {"a": 2}}) == {"a": 2}
    assert cw.unwrap_result({"content": [{"type": "text", "text": '{"a": 1}'}]}) == {"a": 1}
    assert cw.unwrap_result({"content": [{"type": "text", "text": "plain words"}]}) == "plain words"
    with pytest.raises(cw.Refused, match="no scene 375"):
        cw.unwrap_result({"isError": True, "content": [{"type": "text", "text": "no scene 375"}]})


def _door(tmp_path, http, *, expires_at=10_000.0, refresh="rt-1", clock=lambda: 1000.0):
    root = tmp_path / "s"
    session = cw.session_from_tokens("claude", _disc(), "cid-1",
                                     {"access_token": "at-1", "refresh_token": refresh}, now=0.0)
    session["expires_at"] = expires_at
    path = cw.session_path("claude", root)
    cw.write_session(path, session)
    return cw.Door("claude", session, path, http, clock=clock)


def _door_handler(state):
    """The door: initialize, notifications/initialized, then tools/call, each
    answering as the deployed server does; a 401 until the token is at-2 when
    `state["needs_fresh"]`."""
    def handle(kw):
        body = kw["json_body"]
        auth = kw["headers"]["Authorization"]
        if state.get("needs_fresh") and auth != "Bearer at-2":
            return reply(401, {"error": "invalid_token", "detail": "token not accepted"})
        state.setdefault("seen", []).append((body["method"], auth, kw["headers"].get("MCP-Protocol-Version")))
        if body["method"] == "initialize":
            return cw.Reply(200, {"content-type": "text/event-stream"},
                            _sse({"jsonrpc": "2.0", "id": body["id"],
                                  "result": {"protocolVersion": "2025-06-18", "capabilities": {},
                                             "serverInfo": {"name": "zeropage-studio"}}}))
        if body["method"] == "notifications/initialized":
            return reply(202, "")
        if body["method"] == "tools/call":
            name = body["params"]["name"]
            if name == "scene" and body["params"]["arguments"].get("scene_id") == 375:
                result = {"isError": True, "content": [{"type": "text", "text": "no scene 375"}]}
            else:
                payload = {"tool": name, "args": body["params"]["arguments"]}
                result = {"content": [{"type": "text", "text": json.dumps(payload)}],
                          "structuredContent": payload}
            return cw.Reply(200, {"content-type": "text/event-stream"},
                            _sse({"jsonrpc": "2.0", "id": body["id"], "result": result}))
        raise AssertionError(body["method"])
    return handle


def test_call_initializes_once_then_calls_and_a_refusal_is_the_tools_sentence(tmp_path):
    state = {}
    http = FakeHttp({("POST", cw.API + "/mcp/claude"): _door_handler(state)})
    door = _door(tmp_path, http)
    assert door.call("whoami") == {"tool": "whoami", "args": {}}
    assert door.call("project", {"project_id": 7}) == {"tool": "project", "args": {"project_id": 7}}
    with pytest.raises(cw.Refused, match="no scene 375"):
        door.call("scene", {"scene_id": 375})
    methods = [m for m, _, _ in state["seen"]]
    assert methods == ["initialize", "notifications/initialized", "tools/call", "tools/call", "tools/call"]
    assert all(auth == "Bearer at-1" for _, auth, _ in state["seen"])
    assert all(proto == "2025-06-18" for _, _, proto in state["seen"])


def test_a_401_refreshes_the_token_once_and_rewrites_the_file_owner_only(tmp_path):
    state = {"needs_fresh": True}
    refreshed = {}

    def token_endpoint(kw):
        refreshed.update(kw["data"])
        return reply(200, {"access_token": "at-2", "refresh_token": "rt-2", "expires_in": 3600})
    http = FakeHttp({("POST", cw.API + "/mcp/claude"): _door_handler(state),
                     ("POST", AS + "/oauth/token"): token_endpoint})
    door = _door(tmp_path, http)
    door.initialized = True
    assert door.call("whoami") == {"tool": "whoami", "args": {}}
    assert refreshed == {"grant_type": "refresh_token", "refresh_token": "rt-1", "client_id": "cid-1"}
    back = json.loads(door.path.read_text())
    assert back["access_token"] == "at-2" and back["refresh_token"] == "rt-2"
    assert stat.S_IMODE(os.stat(door.path).st_mode) == 0o600
    # one refresh, one retry: never a loop
    assert [m for m, u, _ in http.calls] == ["POST", "POST", "POST"]


def test_a_token_near_its_expiry_is_refreshed_before_the_call(tmp_path):
    state = {"needs_fresh": True}
    http = FakeHttp({("POST", cw.API + "/mcp/claude"): _door_handler(state),
                     ("POST", AS + "/oauth/token"):
                         reply(200, {"access_token": "at-2", "expires_in": 3600})})
    door = _door(tmp_path, http, expires_at=1000.0 + 30, clock=lambda: 1000.0)
    door.initialized = True
    door.call("balance")
    assert http.calls[0][1] == AS + "/oauth/token"           # refreshed first
    assert door.session["refresh_token"] == "rt-1"           # kept when none came back


def test_an_expired_session_with_no_refresh_token_says_to_sign_in(tmp_path):
    http = FakeHttp({("POST", cw.API + "/mcp/claude"):
                     reply(401, {"error": "invalid_token", "detail": "token not accepted"})})
    door = _door(tmp_path, http, refresh=None)
    door.initialized = True
    with pytest.raises(cw.WalkError, match="signin --door claude"):
        door.call("whoami")
    assert len(http.calls) == 1


def test_a_rate_limit_is_reported_with_retry_after_and_never_retried(tmp_path):
    http = FakeHttp({("POST", cw.API + "/mcp/claude"):
                     reply(429, {"error": "rate_limited", "detail": "over 120 requests in 60s -- wait 18s"},
                           {"retry-after": "18"})})
    door = _door(tmp_path, http)
    door.initialized = True
    with pytest.raises(cw.RateLimited, match="Retry-After 18s"):
        door.call("whoami")
    assert len(http.calls) == 1


def test_a_403_is_the_servers_own_sentence(tmp_path):
    http = FakeHttp({("POST", cw.API + "/mcp/claude"):
                     reply(403, {"error": "no_account", "detail": "this sign-in has no workspace yet"})})
    door = _door(tmp_path, http)
    door.initialized = True
    with pytest.raises(cw.WalkError, match="no workspace yet"):
        door.call("whoami")


# --- the upload page --------------------------------------------------------------------

def test_upload_posts_the_file_field_then_opens_the_page_again(tmp_path):
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"\x89PNG rest")
    url = "https://api.phantra.ai/u/tok.abc.sig"
    http = FakeHttp({
        ("POST", url): reply(200, "<html><style>p{}</style><h1>Saved</h1><div>Filed as</div>"
                                  "<div>asset:9</div><div>Size</div><div>512 &times; 512</div>"),
        ("GET", url): reply(410, "<p>this upload link was already used -- ask the chat for another</p>"),
    })
    pages = cw.upload_file(url, icon, http)
    method, posted_url, kw = http.calls[0]
    assert (method, posted_url) == ("POST", url)
    assert kw["files"] == {"file": ("icon.png", b"\x89PNG rest")}
    assert pages["posted"] == {"status": 200, "text": "Saved Filed as asset:9 Size 512 × 512"}
    assert pages["again"]["status"] == 410 and "already used" in pages["again"]["text"]


def test_html_text_reads_a_page_as_a_person_does():
    assert cw.html_text("<script>x()</script><p>a</p>\n<p>b &amp; c</p>") == "a b & c"


# --- redaction ------------------------------------------------------------------------

def test_redaction_hides_tokens_query_strings_and_upload_links():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV"
    value = {"access_token": "at-secret", "quote": {"quote_token": "phq.body.mac", "credits": 10},
             "url": "https://r2.example/file.mp4?X-Amz-Signature=sig123&X-Amz-Expires=300",
             "page": "https://api.phantra.ai/u/tok.abc.sig",
             "note": f"bearer {jwt} and phq.aaa.bbb", "n": 3, "list": [{"token": "t"}]}
    out = cw.redact(value)
    text = json.dumps(out)
    for secret in ("at-secret", "phq.body.mac", "sig123", "tok.abc.sig", jwt, "phq.aaa.bbb"):
        assert secret not in text
    assert out["url"] == "https://r2.example/file.mp4?…"
    assert out["page"] == "https://api.phantra.ai/u/…"
    assert out["quote"]["credits"] == 10 and out["n"] == 3 and out["list"] == [{"token": "…"}]


def test_dollar_keys_are_found_anywhere():
    assert cw.dollar_keys({"clip": {"estimate_usd": 1, "renders": [{"usd": 2}]}, "credits": 3}) == [
        "clip.estimate_usd", "clip.renders[0].usd"]
    assert cw.dollar_keys({"credits": 3, "balance": 4}) == []


# --- the walk -----------------------------------------------------------------------------

TONAL = "props/tonal-one/front.jpg"
SOLENE = "props/solene/bottle.jpg"
UPLOAD_URL = "https://api.phantra.ai/u/tok.abc.sig"


class FakeDoor:
    """Canned answers shaped as the deployed tools answer (src/mcp_server.py),
    stateful where the walk's order matters."""

    def __init__(self):
        self.calls = []
        self.elements_calls = 0
        self.recipe_version = 0
        self.prefs = {"aspect": None, "seconds": None, "video_model": None, "image_model": None,
                      "draft_first": None}
        self.polled = {}
        self.session = {"whoami": {"workspace": {"slug": "zp-billing-test"}}}

    def scene_view(self, sid):
        return {"scene_id": sid, "project_id": 7, "title": "Reviewer check",
                "shots": [{"n": 1, "start": 0, "end": 3, "clip": None}, {"n": 2, "start": 3, "end": 8, "clip": None}],
                "reference_photos": 2, "roles": {SOLENE: "light"}, "keyframe": None, "clips": [],
                "rendered": False, "studio_url": "https://phantra.ai/studio/scene/%d" % sid}

    def call(self, tool, args=None):
        args = args or {}
        self.calls.append((tool, args))
        if tool == "whoami":
            return {"workspace": {"id": 5, "slug": "zp-billing-test", "name": "ZP billing test"},
                    "plan": None, "member": {"name": "Reviewer", "role": "owner"}, "signed_in_person": True}
        if tool == "projects":
            return {"count": 1, "projects": [{"id": 7, "title": "Spring product spots", "scenes": 4}]}
        if tool == "project":
            if args.get("project_id") == 1:
                raise cw.Refused("no project 1")
            return {"id": 7, "title": "Spring product spots", "brief": "four products", "scenes": []}
        if tool == "elements":
            self.elements_calls += 1
            items = [{"kind": "prop", "name": "Tonal One headphones", "photos": [{"ref": TONAL, "label": "front.jpg"}]},
                     {"kind": "prop", "name": "Solene perfume", "photos": [{"ref": SOLENE, "label": "bottle.jpg"}]}]
            if self.elements_calls > 1:
                items.append({"kind": "prop", "name": "Reviewer check",
                              "photos": [{"ref": "props/reviewer-check/up-1.jpg", "label": "up-1.jpg"}]})
            return {"count": len(items), "elements": items}
        if tool == "upload_link":
            return {"url": UPLOAD_URL, "expires_in_minutes": 30, "credits": 0}
        if tool == "write_scene":
            assert args["refs"] == [TONAL, SOLENE] and args["roles"] == {SOLENE: "light"}
            assert args["project_id"] == 7 and "(0-3s)" in args["prompt"]
            return {**self.scene_view(410), "next": "`quote` scene_id=410"}
        if tool == "scene":
            if args.get("scene_id") == 375:
                raise cw.Refused("no scene 375")
            return self.scene_view(args["scene_id"])
        if tool == "quote":
            out = {"scene_id": 410, "status": "written",
                   "keyframes": {"missing": 2, "credits": 20},
                   "clip": {"credits": 174, "renders": [{"part": 1, "credits": 87}, {"part": 2, "credits": 87}]},
                   "balance": 501, "credits_needed": 194, "affordable": True,
                   "approve_url": "https://phantra.ai/studio/scene/410"}
            if self.prefs.get("video_model") and not args.get("model"):
                out["preference"] = {"provider": "fal", "model": self.prefs["video_model"],
                                     "frame": "480p" if self.prefs.get("draft_first") else "720p",
                                     "note": "your default"}
            return out
        if tool == "library":
            return {"count": 2, "items": [
                {"id": "gen:71", "kind": "video", "origin": "render", "seconds": 8.0, "aspect": "9:16",
                 "media_url": "https://r2.example/71.mp4?X-Amz-Signature=sig71"},
                {"id": "asset:9", "kind": "image", "origin": "upload", "aspect": "1:1"}]}
        if tool == "reformat":
            assert args == {"ref": "gen:71", "aspect": "1:1", "fit": "crop", "title": "Reviewer check 1:1"}
            return {"ok": True, "job_id": 1, "plan": {"credits": 0}}
        if tool == "trim_clip":
            assert args["ref"] == "gen:71" and (args["start"], args["end"]) == (0, 1)
            return {"ok": True, "job_id": 2, "plan": {"credits": 0}}
        if tool == "assemble_clips":
            assert args["clips"] == ["gen:101", "gen:102"] and args["letterbox"] is True
            return {"ok": True, "job_id": 3, "plan": {"credits": 0}}
        if tool == "job":
            assert args["wait"] == 15
            n = self.polled.get(args["job_id"], 0) + 1
            self.polled[args["job_id"]] = n
            if n == 1:
                return {"id": args["job_id"], "status": "running", "progress": 0.5}
            return {"id": args["job_id"], "status": "done", "credits": 0,
                    "result": {"ok": True, "ref": f"gen:{100 + args['job_id']}", "credits": 0}}
        if tool == "share_link":
            if args.get("hours") == 200:
                raise cw.Refused("hours is 1 to 168 (seven days), got 200")
            return {"ref": args["ref"], "url": "https://r2.example/103.mp4?X-Amz-Signature=sig103",
                    "hours": 24, "expires_at": "2026-10-14T00:00:00+00:00"}
        if tool == "balance":
            return {"available": 501, "held": 0, "plan": None,
                    "lots": [{"kind": "grant", "credits": 501, "remaining": 501}]}
        if tool == "credit_history":
            return {"items": [{"id": 1, "kind": "grant", "credits": 501, "what": "credits added",
                               "balance_after": 501}], "count": 1}
        if tool == "recent":
            return {"projects": [{"id": 7}], "scenes": [{"scene_id": 410}], "renders": []}
        if tool == "search":
            return {"q": "headphones", "elements": [{"kind": "prop", "name": "Tonal One headphones"}],
                    "scenes": [{"scene_id": 410, "title": "Reviewer check"}], "projects": []}
        if tool == "video_models":
            return {"default": "ltx2.3", "models": [
                {"id": "ltx2.3", "credits_by_frame": {"1080p": 87}, "draft": None},
                {"id": "wan3", "credits_by_frame": {"480p": 36, "720p": 72}, "draft": "480p"},
                {"id": "seedance2.5", "credits_by_frame": {"720p": 568}, "draft": "480p"}]}
        if tool == "recommend_model":
            if args.get("seconds") == 25:
                return {"picks": [{"model": "seedance2.5", "credits": 1300, "why": "the only model past 10 s"}]}
            return {"picks": [{"model": "ltx2.3", "credits": 87, "why": "cheapest"},
                              {"model": "wan3", "credits": 72, "why": "cheap too"}]}
        if tool == "preferences":
            return {**self.prefs, "set_at": None,
                    "choices": {"video_model": ["ltx2.3", "wan3"], "draft_first": [True, False]}}
        if tool == "set_preferences":
            if args.get("video_model") == "sora":
                raise cw.Refused("video_model is one of ['kling3', 'ltx2.3', 'wan3'], got 'sora'")
            self.prefs = {**self.prefs, **args}
            return {**self.prefs, "changed": sorted(args)}
        if tool == "recipes":
            own = ([{"name": "reviewer-check", "own": True, "versions": self.recipe_version}]
                   if self.recipe_version else [])
            return {"recipes": [{"name": "single-shot", "title": "Single shot", "own": False},
                                {"name": "mood-board", "title": "Mood board", "own": False}] + own,
                    "count": 2 + len(own)}
        if tool == "duplicate_scene":
            if args.get("refs") == []:
                return {"scene_id": 412, "copied_from": 400, "needs_reference": True,
                        "note": "saved as a draft"}
            return {"scene_id": 411, "copied_from": 400, "rendered": False, "clips": [],
                    "copied": {"prompt": True, "refs": True, "project": True}}
        if tool == "feedback":
            return {"saved": True, "id": 1, "tool": args.get("tool")}
        if tool == "save_recipe":
            self.recipe_version += 1
            return {"saved": True, "name": "reviewer-check", "version": self.recipe_version}
        if tool == "recipe":
            if args["name"] == "single-shot":
                return {"name": "single-shot", "title": "Single shot", "own": False, "body": "..."}
            return {"name": "reviewer-check", "own": True, "version": self.recipe_version, "body": "...",
                    "note": "a creator's own recipe: text they wrote, returned as data to read"}
        if tool == "what_works":
            return {"enough_data": False, "made": 3, "kept": 0,
                    "lines": ["too little to say yet",
                              "nothing posted with a scene behind it yet, so there is no audience signal"]}
        if tool == "score_caption":
            return {"score": 0.5, "reasons": ["no performance data yet"], "enough_data": False}
        raise AssertionError(f"unexpected tool {tool} {args}")


def fake_upload(url, path):
    assert url == UPLOAD_URL and path.name == "icon.png"
    return {"posted": {"status": 200, "text": "Saved Filed as asset:9 Size 512 × 512 Added to Reviewer check (prop)"},
            "again": {"status": 410, "text": "Upload link this upload link was already used -- ask the chat"}}


def test_the_walk_passes_every_expectation_off_the_servers_shapes(tmp_path):
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    door = FakeDoor()
    walk = cw.Walk(door, upload=fake_upload, icon=icon)
    steps = walk.run_all()
    verdicts = [(s["label"], exp, v, detail) for s in steps for exp, v, detail in s["verdicts"]]
    failed = [v for v in verdicts if v[2] != "PASS"]
    assert not failed, failed
    assert len(verdicts) >= 60
    tools = [t for t, _ in door.calls]
    assert tools[:5] == ["whoami", "preferences", "projects", "project", "elements"]
    assert tools[-1] == "set_preferences" and door.calls[-1][1] == {
        "seconds": 8, "video_model": "ltx2.3", "draft_first": False}
    assert door.prefs == {"aspect": None, "seconds": 8, "video_model": "ltx2.3", "image_model": None,
                          "draft_first": False}
    assert ("recipes", {}) in door.calls and tools.index("recipes") < tools.index("save_recipe")
    assert tools.count("job") == 6                   # three jobs, two polls each
    assert ("project", {"project_id": 1}) in door.calls and ("scene", {"scene_id": 375}) in door.calls
    assert ("share_link", {"ref": "gen:103"}) in door.calls          # the joined clip is what is shared
    assert ("share_link", {"ref": "gen:103", "hours": 200}) in door.calls
    assert walk.ctx["balance_first"] == walk.ctx["balance_last"] == 501


def test_the_walk_file_holds_no_token_no_signature_and_no_dollar(tmp_path):
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(FakeDoor(), upload=fake_upload, icon=icon)
    text = cw.render_walk(walk.run_all(), door="claude", date="2026-10-13", account="zp-billing-test")
    assert text.startswith("# Reviewer walk: /mcp/claude as zp-billing-test (2026-10-13)")
    assert "| # | tool | expectation | verdict | detail |" in text
    assert "CHECK" not in text.split("## Answers")[0].replace("CHECK means", "")
    for secret in ("tok.abc.sig", "sig71", "sig103", "X-Amz-Signature"):
        assert secret not in text
    assert "/u/…" in text and "?…" in text
    assert "$" not in text
    assert "usd" not in text.lower()
    assert "refused: no scene 375" in text and "refused: no project 1" in text
    assert "hours is 1 to 168" in text


def test_a_refusal_is_recorded_as_the_sentence_and_the_walk_goes_on(tmp_path):
    class Stubborn(FakeDoor):
        def call(self, tool, args=None):
            if tool == "whoami":
                self.calls.append((tool, args or {}))
                raise cw.Refused("this sign-in has no workspace yet")
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(Stubborn(), upload=fake_upload, icon=icon)
    steps = walk.run_all()
    first = steps[0]
    assert first["tool"] == "whoami" and first["refused"] == "this sign-in has no workspace yet"
    assert all(v == "CHECK" for _, v, _ in first["verdicts"])
    assert steps[1]["tool"] == "preferences" and "result" in steps[1]
    assert [t for t, _ in walk.client.calls].count("whoami") == 1      # never retried


def test_a_job_that_never_ends_is_a_check_not_a_loop(tmp_path):
    class Stuck(FakeDoor):
        def call(self, tool, args=None):
            if tool == "job":
                self.calls.append((tool, args))
                return {"id": args["job_id"], "status": "running"}
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(Stuck(), upload=fake_upload, icon=icon)
    steps = walk.run_all()
    jobs = [s for s in steps if s["tool"] == "job"]
    assert jobs and jobs[0]["polls"] == cw.JOB_POLLS_MAX
    assert any(v == "CHECK" for _, v, _ in jobs[0]["verdicts"])


# --- the commands ---------------------------------------------------------------------------

def test_a_dry_run_prints_the_authorize_url_and_opens_no_browser(monkeypatch, capsys, tmp_path):
    routes = discovery_routes()
    routes[("POST", AS + "/oauth/clients/register")] = reply(201, {"client_id": "cid-9"})
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp(routes))
    monkeypatch.setattr(cw.webbrowser, "open", lambda url: pytest.fail("a dry run opened a browser"))
    monkeypatch.setattr(cw, "catch_code", lambda *a, **k: pytest.fail("a dry run listened"))
    code = cw.main(["--sessions", str(tmp_path), "signin", "--door", "claude", "--dry-run"])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(out) == 1
    assert out[0].startswith(AS + "/oauth/authorize?")
    assert "code_challenge=" in out[0] and "code_challenge_method=S256" in out[0]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A53682%2Fcallback" in out[0]
    assert "client_id=cid-9" in out[0]
    assert not list(tmp_path.glob("*.json"))              # nothing saved on a dry run


def test_signin_writes_the_session_and_prints_only_the_workspace(monkeypatch, capsys, tmp_path):
    routes = discovery_routes()
    routes[("POST", AS + "/oauth/clients/register")] = reply(201, {"client_id": "cid-9"})
    exchanged = {}

    def token_endpoint(kw):
        exchanged.update(kw["data"])
        return reply(200, {"access_token": "at-live", "refresh_token": "rt-live", "expires_in": 3600})
    routes[("POST", AS + "/oauth/token")] = token_endpoint
    state = {}
    door_handler = _door_handler(state)

    def door(kw):
        if "Authorization" not in kw["headers"]:
            return routes_unsigned
        body = kw["json_body"]
        if body["method"] == "tools/call":
            payload = {"workspace": {"id": 5, "slug": "zp-billing-test"}, "member": {"role": "owner"}}
            return cw.Reply(200, {"content-type": "text/event-stream"},
                            _sse({"jsonrpc": "2.0", "id": body["id"],
                                  "result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}))
        return door_handler(kw)
    routes_unsigned = routes[("POST", cw.API + "/mcp/claude")]
    routes[("POST", cw.API + "/mcp/claude")] = door
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp(routes))
    monkeypatch.setattr(cw.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(cw, "catch_code", lambda expected_state, **k: "the-code")
    code = cw.main(["--sessions", str(tmp_path), "signin", "--door", "claude"])
    out = capsys.readouterr().out
    assert code == 0
    assert "signed in as workspace zp-billing-test" in out
    assert "at-live" not in out and "rt-live" not in out and "the-code" not in out
    assert exchanged["grant_type"] == "authorization_code" and exchanged["code"] == "the-code"
    assert exchanged["redirect_uri"] == cw.REDIRECT and exchanged["client_id"] == "cid-9"
    assert "code_verifier" in exchanged
    path = tmp_path / "claude.json"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    saved = json.loads(path.read_text())
    assert saved["access_token"] == "at-live" and saved["whoami"]["workspace"]["slug"] == "zp-billing-test"


def test_env_never_writes_the_token_to_stdout(monkeypatch, capsys, tmp_path):
    cw.write_session(cw.session_path("claude", tmp_path),
                     {**cw.session_from_tokens("claude", _disc(), "cid", {"access_token": "at-9"}, now=0),
                      "expires_at": 10 ** 12})
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp({}))
    assert cw.main(["--sessions", str(tmp_path), "env", "claude"]) == 1
    out, err = capsys.readouterr()
    assert out == "" and "at-9" not in err and "--fd" in err
    r, w = os.pipe()
    try:
        assert cw.main(["--sessions", str(tmp_path), "env", "claude", "--fd", str(w)]) == 0
    finally:
        os.close(w)
    with os.fdopen(r) as f:
        assert f.read() == "export TOKEN=at-9\n"
    assert capsys.readouterr().out == ""


def test_inspector_runs_npx_with_the_header_and_saves_the_listing(monkeypatch, capsys, tmp_path):
    cw.write_session(cw.session_path("claude", tmp_path),
                     {**cw.session_from_tokens("claude", _disc(), "cid", {"access_token": "at-9"}, now=0),
                      "expires_at": 10 ** 12})
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp({}))
    seen = {}

    class Done:
        returncode = 0
        stdout = json.dumps({"tools": [{"name": "whoami", "title": "Which workspace"},
                                       {"name": "projects", "title": "List your projects"}]})
        stderr = ""

    def fake_run(argv, **kw):
        seen["argv"] = argv
        return Done()
    monkeypatch.setattr(cw.subprocess, "run", fake_run)
    out = tmp_path / "screens" / "inspector-claude.json"
    assert cw.main(["--sessions", str(tmp_path), "inspector", "claude", "--out", str(out)]) == 0
    argv = seen["argv"]
    assert argv[:4] == ["npx", "-y", "@modelcontextprotocol/inspector", "--cli"]
    assert argv[4] == cw.API + "/mcp/claude"
    assert argv[argv.index("--transport") + 1] == "http"
    assert argv[argv.index("--method") + 1] == "tools/list"
    assert argv[argv.index("--header") + 1] == "Authorization: Bearer at-9"
    printed = capsys.readouterr().out
    assert "2 tools on" in printed and "at-9" not in printed
    assert json.loads(out.read_text())["tools"][1]["name"] == "projects"


def test_call_prints_the_result_and_a_refusal_exits_2(monkeypatch, capsys, tmp_path):
    cw.write_session(cw.session_path("claude", tmp_path),
                     {**cw.session_from_tokens("claude", _disc(), "cid", {"access_token": "at-9"}, now=0),
                      "expires_at": 10 ** 12})
    state = {}
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp(
        {("POST", cw.API + "/mcp/claude"): _door_handler(state)}))
    assert cw.main(["--sessions", str(tmp_path), "call", "claude", "project", "--json", '{"project_id": 7}']) == 0
    assert json.loads(capsys.readouterr().out) == {"tool": "project", "args": {"project_id": 7}}
    assert cw.main(["--sessions", str(tmp_path), "call", "claude", "scene", "--json", '{"scene_id": 375}']) == 2
    assert json.loads(capsys.readouterr().out) == {"refused": "no scene 375"}
    assert cw.main(["--sessions", str(tmp_path), "call", "claude", "scene", "--json", "not json"]) == 1


def test_a_walk_with_no_session_fails_before_touching_the_network(monkeypatch, tmp_path):
    monkeypatch.setattr(cw, "Http", lambda *a, **k: FakeHttp({}))
    assert cw.main(["--sessions", str(tmp_path), "walk", "claude", "--out", str(tmp_path / "w.md")]) == 1
    assert not (tmp_path / "w.md").exists()


# --- the review's findings (2026-10-12), each pinned -----------------------------------

def test_a_refused_reformat_does_not_stop_the_trim_and_the_join(tmp_path):
    class NoReformat(FakeDoor):
        def call(self, tool, args=None):
            if tool == "reformat":
                self.calls.append((tool, args))
                raise cw.Refused("gen:71 cannot be measured right now")
            if tool == "assemble_clips":
                self.calls.append((tool, args))
                return {"ok": True, "job_id": 3, "plan": {"credits": 0}}
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(NoReformat(), upload=fake_upload, icon=icon)
    steps = walk.run_all()
    labels = [s["label"] for s in steps]
    assert "job (the trim)" in labels and walk.ctx["trim_ref"] == "gen:102"
    assert "job (the join)" not in labels                      # needs both halves
    assert any(s["label"] == "share_link" for s in steps)      # shares what there is
    assert steps[-1]["label"] == "set_preferences (back)"


def test_a_transport_error_is_recorded_and_the_walk_goes_on_and_still_resets(tmp_path):
    class Dropped(FakeDoor):
        def call(self, tool, args=None):
            if tool == "search":
                self.calls.append((tool, args))
                raise ConnectionError("connection reset by peer")
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(Dropped(), upload=fake_upload, icon=icon)
    steps = walk.run_all()
    search = next(s for s in steps if s["tool"] == "search")
    assert search["error"] == "ConnectionError: connection reset by peer"
    assert all(v == "CHECK" for _, v, _ in search["verdicts"])
    assert steps[-1]["label"] == "set_preferences (back)" and "result" in steps[-1]
    assert walk.client.prefs["video_model"] == "ltx2.3"


def test_a_crash_inside_the_list_still_runs_the_tail_reset(tmp_path):
    class Boom(FakeDoor):
        def call(self, tool, args=None):
            if tool == "what_works":
                raise RuntimeError("the fake exploded")
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    walk = cw.Walk(Boom(), upload=fake_upload, icon=icon)
    steps = walk.run_all()
    assert next(s for s in steps if s["tool"] == "what_works")["error"] == "RuntimeError: the fake exploded"
    assert steps[-1]["label"] == "set_preferences (back)"


def test_a_rate_limit_is_waited_out_once_and_the_call_asked_once_more(tmp_path):
    class Busy(FakeDoor):
        limited = 0

        def call(self, tool, args=None):
            if tool == "search" and self.limited == 0:
                self.limited += 1
                raise cw.RateLimited("18", "over 120 requests in 60s")
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    slept = []
    walk = cw.Walk(Busy(), upload=fake_upload, icon=icon, sleep=slept.append)
    steps = walk.run_all()
    search = next(s for s in steps if s["tool"] == "search")
    assert slept == [19.0] and search["waited"] == "18" and "result" in search
    assert all(v == "PASS" for _, v, _ in search["verdicts"])
    assert not walk.stopped


def test_a_second_rate_limit_stops_the_walk_and_sends_nothing_more(tmp_path):
    class Closed(FakeDoor):
        def call(self, tool, args=None):
            if tool in ("search", "video_models"):
                self.calls.append((tool, args))
                raise cw.RateLimited("42", "over 120 requests in 60s")
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    slept = []
    walk = cw.Walk(Closed(), upload=fake_upload, icon=icon, sleep=slept.append)
    steps = walk.run_all()
    assert slept == [43.0]                                     # one wait, not one per step
    tools = [t for t, _ in walk.client.calls]
    assert tools.count("search") == 2 and "video_models" not in tools
    after = steps[next(i for i, s in enumerate(steps) if s["tool"] == "search") + 1:]
    assert after and all(s.get("error", "").startswith("not run: rate limited") for s in after)
    assert steps[-1]["label"] == "set_preferences (back)" and steps[-1]["error"].startswith("not run")
    text = cw.render_walk(steps, door="claude", date="2026-10-13")
    assert "rate limited once; waited Retry-After 42" in text


def test_the_walk_restores_the_preferences_it_found(tmp_path):
    door = FakeDoor()
    door.prefs = {**door.prefs, "seconds": 10, "video_model": "kling3", "draft_first": False}
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    steps = cw.Walk(door, upload=fake_upload, icon=icon).run_all()
    assert door.calls[-1] == ("set_preferences", {"seconds": 10, "video_model": "kling3", "draft_first": False})
    assert door.prefs["video_model"] == "kling3"
    failed = [(s["label"], e, d) for s in steps for e, v, d in s["verdicts"] if v != "PASS"]
    assert not failed, failed


def test_the_second_run_counts_recipe_versions_from_what_it_finds(tmp_path):
    door = FakeDoor()
    door.recipe_version = 2                                     # a previous walk saved twice
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    steps = cw.Walk(door, upload=fake_upload, icon=icon).run_all()
    failed = [(s["label"], e, d) for s in steps for e, v, d in s["verdicts"] if v != "PASS"]
    assert not failed, failed
    assert door.recipe_version == 4


def test_a_walk_with_no_rendered_clip_says_so_in_a_row(tmp_path):
    class NoClip(FakeDoor):
        def call(self, tool, args=None):
            if tool == "library":
                return {"count": 1, "items": [{"id": "asset:9", "kind": "image", "origin": "upload"}]}
            return super().call(tool, args)

    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    steps = cw.Walk(NoClip(), upload=fake_upload, icon=icon).run_all()
    skipped = next(s for s in steps if s["tool"] == "(skipped)")
    assert "no rendered clip" in skipped["error"]
    assert "skipped" in cw.render_walk(steps, door="claude", date="2026-10-13")


def test_discovery_refuses_a_document_for_another_resource_or_issuer():
    routes = discovery_routes()
    meta_url = f"{cw.API}/.well-known/oauth-protected-resource/mcp/claude"
    routes[("GET", meta_url)] = reply(200, {"resource": "https://elsewhere.example/mcp",
                                            "authorization_servers": [AS]})
    with pytest.raises(cw.WalkError, match="names resource"):
        cw.discover("claude", FakeHttp(routes))
    routes = discovery_routes()
    routes[("GET", AS + "/.well-known/oauth-authorization-server")] = reply(
        200, {**AS_DOC, "issuer": "https://other.example/auth/v1"})
    with pytest.raises(cw.WalkError, match="names issuer"):
        cw.discover("claude", FakeHttp(routes))


def test_only_our_own_state_ends_the_callback_wait():
    assert cw.callback_outcome({"code": ["c1"], "state": ["ours"]}, "ours") == ("code", "c1")
    assert cw.callback_outcome({"code": ["c1"], "state": ["theirs"]}, "ours")[0] == "ignore"
    assert cw.callback_outcome({"code": ["c1"]}, "ours")[0] == "ignore"
    assert cw.callback_outcome({"state": ["ours"]}, "ours")[0] == "ignore"
    assert cw.callback_outcome({"error": ["access_denied"], "error_description": ["the person said no"],
                                "state": ["ours"]}, "ours") == ("error", "access_denied: the person said no")
    assert cw.callback_outcome({"error": ["access_denied"], "state": ["theirs"]}, "ours")[0] == "ignore"


def test_a_requests_error_is_a_walk_error_not_a_traceback(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("connection refused")
    monkeypatch.setattr(requests, "request", boom)
    with pytest.raises(cw.WalkError, match="ConnectionError"):
        cw.Http().request("POST", "https://api.phantra.ai/mcp/claude?x=1")


def test_a_non_json_200_is_a_walk_error():
    page = cw.Reply(200, {"content-type": "text/html"}, "<html>Bad gateway</html>")
    with pytest.raises(cw.WalkError, match="not JSON"):
        cw.parse_rpc_reply(page, 1)


def test_a_session_without_a_refresh_token_is_used_until_the_server_says_no(tmp_path):
    state = {}
    http = FakeHttp({("POST", cw.API + "/mcp/claude"): _door_handler(state)})
    door = _door(tmp_path, http, refresh=None, expires_at=1000.0 + 10, clock=lambda: 1000.0)
    door.initialized = True
    assert door.call("whoami") == {"tool": "whoami", "args": {}}     # not refused 90 s early
