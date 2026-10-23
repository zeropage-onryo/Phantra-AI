"""
The editing-app panels' API (2026-10-22, docs/tasks/task-premiere-plugin.md).

A Premiere Pro panel signs in with a code (src/plugin_tokens.py) and then
holds a bearer token, not the studio's cookie, so its door is here, OUTSIDE
/api -- the same placement as the MCP mount and for the same reason.

ONE RULE: THE PANEL RUNS THE CONNECTOR'S CODE. Making, quoting, approving,
effects, the Library and job polling are the render listing's tools (what
the ChatGPT connector reaches), called by name on a server built exactly as
app/mcp_mount builds that listing, with the same injected job registry and
approve bodies. So the signed single-use quote tokens, the ledger hold, the
balance refusals and the plain-words failures are the ones already reviewed
and tested -- nothing here prices or spends on its own, and nothing in
src/mcp_server.py, app/mcp_mount.py or app/mcp_auth.py changed for it (the
connector is in directory review). `PLUGIN_TOOLS` is the subset a panel
reaches.

The caller's account rides `mcp_server.CALLER_ACCOUNT` (and the person
`CALLER_USER`) for the length of one tool call and is reset in a
`finally`, the MCP guard's own rule: a value left set is one caller reading
another's work.

Two routers:

- `router` (`/plugin/v1/...`): pairing (no auth: the device secret is the
  credential), then everything else behind the bearer token.
- `studio_router` (`/api/plugin/...`, included into app/api.py's router so
  the tenancy audit covers it): the studio's half -- approving a code,
  listing and disconnecting panels -- behind the cookie session.
"""
from __future__ import annotations

import json
import sys
import threading
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src import plugin_tokens

from . import auth

router = APIRouter(prefix="/plugin/v1", tags=["plugin"])
studio_router = APIRouter(prefix="/plugin", tags=["plugin"])

# What a panel reaches: the render listing's tools, minus the chat-only ones
# (a project's chat history, recipes, caption scoring, preferences) a panel
# has no screen for. Every spending tool here is quoted first and runs only
# with that quote's token -- the connector's own gate.
PLUGIN_TOOLS = (
    "whoami", "balance", "credit_history",
    "projects", "project", "create_project",
    "elements", "add_element", "upload_link",
    "image_models", "video_models", "recommend_model",
    "library", "share_link",
    "generate_image", "edit_image", "remove_background", "animate_still",
    "camera_move", "upscale_clip", "add_sound", "reframe_clip",
    "write_scene", "scene", "quote", "approve", "job",
    "reformat", "trim_clip",
    "feedback",
    "edit_clip",
)

# The one tool the panel takes from the STUDIO surface rather than the render
# listing (2026-10-22, "send selected clip to Phantra"): editing a clip from
# the timeline by instruction, a frame first and then the clip
# (mcp_server.run_edit_clip). It is on no listing, so it is reached through a
# studio-surface server built here; the listings are unchanged.
STUDIO_SURFACE_TOOLS = ("edit_clip",)

# every tool here that can start a spend once given a token (or, for
# `approve`, given no token on a server that signs none)
SPENDING_TOOLS = ("generate_image", "edit_image", "remove_background", "animate_still",
                  "camera_move", "upscale_clip", "add_sound", "reframe_clip", "approve",
                  "edit_clip")

DEFAULT_RATE = 240            # tool calls per account per minute (a panel polls `job`)

_wiring: dict[str, Any] = {}
_server = None
_studio = None
_server_lock = threading.Lock()


def configure(*, start_job=None, job_status=None, approve_render=None,
              approve_keyframes=None, create_element=None, dsn=None) -> None:
    """What app.main hands the MCP mount, handed here too. Building waits
    for the first call, so a deployment that never sees a panel never
    builds the server (and one without the `mcp` package still starts)."""
    global _server, _studio
    with _server_lock:
        _wiring.clear()
        _wiring.update(start_job=start_job, job_status=job_status,
                       approve_render=approve_render,
                       approve_keyframes=approve_keyframes,
                       create_element=create_element, dsn=dsn)
        _server = None
        _studio = None


def _listed_server():
    """The render listing, built once per process the way app/mcp_mount
    builds it. None (and a line on stderr) when it cannot be built."""
    global _server
    if _server is not None:
        return _server
    with _server_lock:
        if _server is None:
            try:
                from src import mcp_server

                from .mcp_mount import connector_element
                _server = mcp_server.build_server(
                    dsn=_wiring.get("dsn"),
                    start_job=_wiring.get("start_job"),
                    job_status=_wiring.get("job_status"),
                    approve_render=_wiring.get("approve_render"),
                    approve_keyframes=_wiring.get("approve_keyframes"),
                    listed=True,
                    create_element=connector_element(_wiring.get("create_element")),
                )
            except Exception as e:                                  # noqa: BLE001
                print(f"note: the plugin API could not build its tools "
                      f"({type(e).__name__}: {e})", file=sys.stderr)
                return None
    return _server


def _studio_server():
    """A studio-surface server for STUDIO_SURFACE_TOOLS, built once, the way
    app/mcp_mount builds the operator's (no `import_file`: that reads this
    server's own disk)."""
    global _studio
    if _studio is not None:
        return _studio
    with _server_lock:
        if _studio is None:
            try:
                from src import mcp_server

                from .mcp_mount import connector_element
                _studio = mcp_server.build_server(
                    dsn=_wiring.get("dsn"),
                    start_job=_wiring.get("start_job"),
                    job_status=_wiring.get("job_status"),
                    surface="studio",
                    local_files=False,
                    create_element=connector_element(_wiring.get("create_element")),
                )
            except Exception as e:                                  # noqa: BLE001
                print(f"note: the plugin API could not build its studio tools "
                      f"({type(e).__name__}: {e})", file=sys.stderr)
                return None
    return _studio


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message, **extra}})


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    return header[len("Bearer "):].strip() if header.startswith("Bearer ") else ""


_limiter_box: list = []


def _limiter():
    """The MCP mount's fixed-window limiter class, one instance of our own
    (a panel's calls must not spend a connector's budget, or the reverse)."""
    if not _limiter_box:
        from .mcp_mount import RateLimiter
        _limiter_box.append(RateLimiter())
    return _limiter_box[0]


_ip_hits: dict = {}


def _client_ip(request: Request) -> str:
    """Who is asking, for a brake. Fly's edge sets Fly-Client-IP itself;
    the app's uvicorn trusts X-Forwarded-For from anywhere
    (--forwarded-allow-ips='*'), so request.client.host is whatever the
    caller wrote first in that header and cannot key a limit."""
    return (request.headers.get("fly-client-ip") or
            (request.client.host if request.client else "?")).strip()[:64]


def _braked(request: Request, bucket: str, limit: int) -> Optional[JSONResponse]:
    """A per-address limit for the doors a token does not guard yet."""
    ok, retry = _limiter().allow((bucket, _client_ip(request)), limit)
    if ok:
        return None
    return JSONResponse(status_code=429, headers={"Retry-After": str(retry)},
                        content={"error": {"code": "rate_limited",
                                           "message": "Too many tries. Wait a minute.",
                                           "retry_after": retry}})


def link_url(code: str = "") -> str:
    """Where the person approves a code: the studio's /studio/link page.
    The code is NOT put in the address (review, 2026-10-22): a link with
    the code already in it is a one-click phishing kit -- start a pairing,
    send the link, the victim presses Connect. Typing the code the panel
    shows is what proves the panel is in front of the person."""
    origin = auth.studio_url() or "https://phantra.ai"
    return f"{origin}/studio/link"


# --- pairing: no auth, the device secret is the credential -----------------

class PairBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client: str = Field("premiere", max_length=40)
    device: str = Field("", max_length=200)


class SecretBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secret: str = Field(..., max_length=200)


@router.post("/pair")
def pair_start(body: PairBody, request: Request):
    """A new sign-in: the code to show, the link to open, and the secret
    the panel keeps (handed out here once, stored nowhere)."""
    braked = _braked(request, "plugin_pair", 10)
    if braked:
        return braked
    try:
        started = plugin_tokens.start(body.client, body.device)
    except ValueError as e:
        return _error(400, "bad_client", str(e))
    return {**started, "link_url": link_url()}


@router.post("/pair/token")
def pair_token(body: SecretBody, request: Request):
    """Polled every `interval` seconds by the panel holding the secret.
    200 once a person approved it; 400 `authorization_pending` until then;
    400 `expired_token` after ten minutes (start again)."""
    braked = _braked(request, "plugin_poll", 60)   # one panel polls every 5 s
    if braked:
        return braked
    state = plugin_tokens.poll(body.secret)
    if state == "approved":
        row = plugin_tokens.resolve(body.secret)
        return {"ok": True, "token": body.secret, "client": (row or {}).get("client")}
    if state == "pending":
        return _error(400, "authorization_pending", "Waiting for you to approve the code.")
    if state == "expired":
        return _error(400, "expired_token", "The code expired. Start signing in again.")
    return _error(400, "invalid_grant", "That sign-in isn't one we know. Start again.")


# --- the bearer door -----------------------------------------------------

def _caller(request: Request) -> Optional[dict]:
    secret = _bearer(request)
    return plugin_tokens.resolve(secret) if secret else None


def _over_limit(caller: dict) -> Optional[JSONResponse]:
    ok, retry = _limiter().allow(("plugin", int(caller["account_id"])), DEFAULT_RATE)
    if ok:
        return None
    return JSONResponse(status_code=429, headers={"Retry-After": str(retry)},
                        content={"error": {"code": "rate_limited",
                                           "message": "Slow down a moment.",
                                           "retry_after": retry}})


def _unauthorized() -> JSONResponse:
    return JSONResponse(status_code=401, headers={"WWW-Authenticate": "Bearer"},
                        content={"error": {"code": "unauthorized",
                                           "message": "Sign in to Phantra again from the panel."}})


def _result_of(result) -> tuple[bool, Any]:
    """(ok, payload) from an MCP CallToolResult: the typed answer when the
    tool returned one, else its text (parsed as JSON when it is)."""
    if isinstance(result, tuple) and len(result) == 2:        # (content, structured)
        content, structured = result
        is_error = False
    else:
        content = getattr(result, "content", None) or []
        structured = getattr(result, "structuredContent", None)
        is_error = bool(getattr(result, "isError", False))
    text = "\n".join(getattr(c, "text", "") for c in content if getattr(c, "text", None))
    if is_error:
        return False, text or "the tool failed"
    if isinstance(structured, dict):
        inner = structured.get("result") if set(structured) == {"result"} else structured
        return True, inner
    try:
        return True, json.loads(text)
    except (TypeError, ValueError):
        pass
    # the studio surface answers a line for the model, then the JSON
    start = text.find("{")
    if start >= 0:
        try:
            parsed = json.loads(text[start:])
            if isinstance(parsed, dict):
                return True, parsed
        except ValueError:
            pass
    return True, {"text": text}


def refusal_text(name: str, message: str) -> str:
    """A refusal as the panel shows it: the SDK's "Error executing tool
    <name>: " prefix off, the connector's listed wording kept."""
    from src import mcp_server
    prefix = f"Error executing tool {name}: "
    text = message[len(prefix):] if message.startswith(prefix) else message
    return mcp_server.listed_text(text).strip()


async def run_tool(name: str, args: dict, caller: dict) -> JSONResponse | dict:
    """One tool call as the caller. The account and the person are set for
    this call only and reset whatever happens."""
    from src import mcp_server
    server = _studio_server() if name in STUDIO_SURFACE_TOOLS else _listed_server()
    if server is None:
        return _error(503, "unavailable", "Phantra's tools aren't available right now. "
                                          "Nothing was charged.")
    account = mcp_server.CALLER_ACCOUNT.set(int(caller["account_id"]))
    person = mcp_server.CALLER_USER.set(str(caller.get("user_id") or "") or None)
    try:
        try:
            result = await server.call_tool(name, args)
        except Exception as e:                                       # noqa: BLE001
            # The SDK's own split: a ToolError is a refusal the connector
            # words for a person (a bad id, a spent quote, bad arguments);
            # an UnexpectedToolError is a crash, whose text stays here.
            from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
            if isinstance(e, ToolError) and not isinstance(e, UnexpectedToolError):
                return _error(400, "refused", refusal_text(name, str(e)))
            cause = e.__cause__ or e
            print(f"plugin tool {name} crashed: {type(cause).__name__}: {cause}",
                  file=sys.stderr)
            return _error(500, "tool_failed", "Something went wrong on our side. Check "
                                              "Jobs and your Library before trying again.")
    finally:
        mcp_server.CALLER_USER.reset(person)
        mcp_server.CALLER_ACCOUNT.reset(account)
    ok, payload = _result_of(result)
    if not ok:
        return _error(400, "refused", str(payload))
    return {"ok": True, "result": payload}


@router.get("/me")
async def me(request: Request):
    """Who this panel is signed in as, and the balance."""
    caller = _caller(request)
    if caller is None:
        return _unauthorized()
    limited = _over_limit(caller)
    if limited:
        return limited
    who = await run_tool("whoami", {}, caller)
    if isinstance(who, JSONResponse):
        return who
    balance = await run_tool("balance", {}, caller)
    return {"ok": True, "client": caller.get("client"), "whoami": who["result"],
            "balance": balance.get("result") if isinstance(balance, dict) else None}


@router.post("/tools/{name}")
async def tool(name: str, request: Request):
    """Call one of PLUGIN_TOOLS with a JSON object of its arguments."""
    caller = _caller(request)
    if caller is None:
        return _unauthorized()
    if name not in PLUGIN_TOOLS:
        return _error(404, "unknown_tool", f"no tool {name!r} here")
    limited = _over_limit(caller)
    if limited:
        return limited
    if name in SPENDING_TOOLS:
        from src import pricing
        if not pricing.configured():
            # without a signing secret `approve` takes no token at all, so
            # this door would spend on a bare call: it refuses instead
            return _error(503, "cannot_approve", "Spending isn't available from the "
                                                 "panel on this server. Nothing was charged.")
    try:
        args = await request.json() if (await request.body()) else {}
    except ValueError:
        return _error(400, "bad_json", "the body must be a JSON object of arguments")
    if not isinstance(args, dict):
        return _error(400, "bad_json", "the body must be a JSON object of arguments")
    return await run_tool(name, args, caller)


UPLOAD_CHUNK = 1 << 20


@router.post("/upload")
async def upload(request: Request):
    """A file from the editing app -- a clip on the timeline, a frame at the
    playhead -- filed in the person's Library as an `asset:<id>`, free. The
    body is the file's raw bytes. The same body as the connector's upload
    page (app/upload_page.py): typed by its first bytes, never its name,
    capped while it is read, a picture normalised to a JPEG."""
    caller = _caller(request)
    if caller is None:
        return _unauthorized()
    limited = _over_limit(caller)
    if limited:
        return limited
    from src.cut import uploads as cut_uploads

    from . import upload_page
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    cap = upload_page.VIDEO_CAP
    if declared > cap:
        return _error(413, "too_big", f"That file is over {cap // upload_page.MB} MB. "
                                      "Trim or export a shorter clip first.")
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > cap:
            return _error(413, "too_big", f"That file is over {cap // upload_page.MB} MB. "
                                          "Trim or export a shorter clip first.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        return _error(400, "empty", "That file is empty.")
    sniffed = upload_page.sniff(data)
    if sniffed is None:
        return _error(400, "not_media", f"Phantra takes {upload_page.TAKES}.")
    kind, ext = sniffed
    if kind == "image" and len(data) > upload_page.IMAGE_CAP:
        return _error(413, "too_big", f"That picture is over "
                                      f"{upload_page.IMAGE_CAP // upload_page.MB} MB.")
    try:
        saved = upload_page._save(data, kind, ext, {"account_id": int(caller["account_id"])})
    except cut_uploads.UploadRefused as e:
        return _error({"too_big": 413, "out_of_storage": 507}.get(e.code, 400), e.code, str(e))
    except Exception as e:                                          # noqa: BLE001
        print(f"plugin upload failed: {type(e).__name__}: {e}", file=sys.stderr)
        return _error(500, "upload_failed", "The file couldn't be saved just now. Try again.")
    return {"ok": True, **saved}


@router.get("/download/{ref}")
def download(ref: str, request: Request):
    """A render's file as an attachment (`gen:<id>`), through the Library's
    own download body: a short-lived bucket link, or this machine's file."""
    caller = _caller(request)
    if caller is None:
        return _unauthorized()
    limited = _over_limit(caller)
    if limited:
        return limited
    kind, _, raw = (ref or "").partition(":")
    if kind != "gen" or not (raw.isascii() and raw.isdecimal()):
        return _error(400, "bad_ref", "name a render as gen:<id>, from `library`")
    from . import api
    return api.asset_download_generated(int(raw), account_id=int(caller["account_id"]))


@router.get("/scenes/{scene_id}/clips")
def scene_clips(scene_id: int, request: Request):
    """A rendered scene's clips, shot by shot, as addresses the panel can
    download (`scene` lists their stored names, which only the studio can
    open). The caller's own scene only; anyone else's is a plain 404."""
    caller = _caller(request)
    if caller is None:
        return _unauthorized()
    limited = _over_limit(caller)
    if limited:
        return limited
    from src import mcp_server, preprod
    account_id = int(caller["account_id"])
    concept = preprod.get_concept(int(scene_id), account_id=account_id)
    if concept is None:
        return _error(404, "not_found", f"no scene {scene_id}")
    view = mcp_server._scene_view(concept, account_id)
    shots = view.get("shots") or []
    if shots:
        clips = [{"n": s.get("n"), "seconds": s.get("seconds"),
                  "url": mcp_server._view(s["clip"], account_id)}
                 for s in shots if s.get("clip")]
    else:
        clips = [{"n": 1, "seconds": view.get("seconds"),
                  "url": mcp_server._view(c, account_id)} for c in view.get("clips") or []]
    return {"ok": True, "scene_id": int(scene_id), "title": view.get("title"),
            "shots_written": view.get("shots_written"), "clips": clips}


@router.post("/signout")
def signout(request: Request):
    """The panel signing itself out: its token stops working at once."""
    secret = _bearer(request)
    return {"ok": True, "revoked": plugin_tokens.revoke_secret(secret) if secret else False}


# --- the studio's half (/api/plugin/..., cookie session) -------------------

class LinkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., max_length=40)


def _person_id(request: Request) -> str:
    return str((auth.current_user(request) or {}).get("id") or "")


@studio_router.get("/link")
def link_preview(code: str, request: Request,
                 account_id: int = Depends(auth.current_account_id)):
    """What the link page shows before the click: which app is asking.
    Reveals nothing about any account."""
    braked = _braked(request, "plugin_link", 10)
    if braked:
        return braked
    found = plugin_tokens.pending(code)
    if not found:
        return _error(404, "bad_code", "That code isn't waiting to connect. Check it against "
                                       "your panel, or get a new one.")
    # the workspace the approval WILL bind: the tenant, not the one open
    home = auth.tenant_account(request, account_id) or {}
    return {"ok": True, **found,
            "workspace": home.get("display_name") or home.get("slug") or None}


@studio_router.post("/link")
def link_approve(body: LinkBody, request: Request,
                 account_id: int = Depends(auth.current_account_id)):
    """The person approved a code: that panel is now signed in to their
    workspace (the tenant, as every /api route acts). The mutation header
    makes another site's background form unable to do this for them."""
    from . import model_connections
    model_connections.mutation_header(request)
    braked = _braked(request, "plugin_link", 10)
    if braked:
        return braked
    try:
        made = plugin_tokens.approve(body.code, account_id, _person_id(request))
    except plugin_tokens.PairingRefused as e:
        return _error(400, e.code, str(e))
    return {"ok": True, "connection": made}


@studio_router.get("/connections")
def list_connections(request: Request, account_id: int = Depends(auth.current_account_id)):
    """This person's connected panels on this workspace."""
    return {"items": plugin_tokens.connections(account_id, _person_id(request))}


@studio_router.post("/connections/{token_id}/revoke")
def revoke_connection(token_id: int, request: Request,
                      account_id: int = Depends(auth.current_account_id)):
    """Disconnect one panel. Someone else's id is a plain 404."""
    from . import model_connections
    model_connections.mutation_header(request)
    if not plugin_tokens.revoke(token_id, account_id, _person_id(request)):
        return _error(404, "not_found", "no such connection")
    return {"ok": True}
