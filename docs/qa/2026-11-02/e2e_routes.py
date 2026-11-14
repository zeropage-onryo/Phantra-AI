#!/usr/bin/env python
# ruff: noqa: E501 -- a QA script whose result lines read better whole
"""Backend endpoint E2E for Phantra: every route on auth, tenancy and bad input,
plus the ledger (hold -> settle / release) with stubbed providers.

QA pass 2026-11-02 (Agent C). Re-runnable:

    PYTHONPATH="$PWD:<dir holding a sitecustomize.py that drops the editable finder>" \
        venv/bin/python docs/qa/2026-11-02/e2e_routes.py --schema qa1102c

    --keep        keep the schema afterwards (default: dropped)
    --json PATH   write every result as JSON (the report's tables are built from it)
    --no-server   skip the SSE check (it starts uvicorn on 127.0.0.1:8031)
    --openapi PATH  also write app.openapi() there (docs/qa/2026-11-02/openapi.json)
    --only seed   seed the two accounts and stop (debugging the seed)
    --quiet       print only the summary

  The local Postgres.app server at :5432 (role/password phantra) must be up. The
  script creates its schema, seeds accounts A and B through the app's own doors,
  runs every pass in-process (FastAPI TestClient), and drops the schema at the end
  even on a crash. It never touches `public` or any other schema.

WHAT IT MUST NEVER DO (and how it is held to that):
  * Never touch the live database. DATABASE_URL / RAG_DATABASE_URL are set to the
    local throwaway (postgresql://phantra:phantra@localhost:5432/phantra, its OWN
    schema) BEFORE `app` is imported, dotenv.load_dotenv is replaced with a no-op
    (app.main would otherwise load the main checkout's .env), and psycopg refuses
    any host that is not this machine.
  * Never hold a real key. Every provider/storage/billing key name is blanked
    (GEMINI, FAL, R2, STRIPE, SUPABASE, ELEVENLABS, SERPER, social apps ...). The
    QUOTE_SIGNING_SECRET, SESSION_SECRET, STRIPE_WEBHOOK_SECRET and
    SOCIAL_TOKEN_SECRET it sets are local made-up strings.
  * Never reach the network. socket connect / create_connection / getaddrinfo
    refuse anything but loopback; a blocked attempt is RECORDED (which route
    tried) and is a finding, not a crash.
  * Never spend. The ledger phase stubs fal's HTTP layer (`fal._request`,
    `fal._download`) and Gemini's image call (`nano_banana._generate_content`):
    the hold / settle / release code is the real code, only the provider is fake.
    No *_SPEND_OK flag is set; the approval is the route's own (quote token /
    expect_credits), as a person's click would give it.
  * Never write outside its temp dir: every module-level output path the suite's
    conftest registers (OUTPUT_ROOTS), plus the element folders, is pointed at a
    temp directory.

Exit code: 0 when every result matches its expectation or is a listed known
failure (KNOWN_RULES below, each tied to a finding id in 03-backend-e2e.md),
1 on any new failure, 2 when the harness itself crashed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]  # docs/qa/2026-11-02/e2e_routes.py -> repo root

ap = argparse.ArgumentParser()
ap.add_argument("--schema", default="qa1102c")
ap.add_argument("--keep", action="store_true")
ap.add_argument("--json", default="")
ap.add_argument("--no-server", action="store_true")
ap.add_argument("--port", type=int, default=8031)
ap.add_argument("--quiet", action="store_true")
ap.add_argument("--only", default="")
ap.add_argument("--openapi", default="", help="also write app.openapi() to this path")
ARGS = ap.parse_args()
SCHEMA = ARGS.schema
assert re.fullmatch(r"[a-z_][a-z0-9_]{0,40}", SCHEMA), "schema must be a plain identifier"
if SCHEMA in ("public",):
    sys.exit("refusing to use the public schema")

# --------------------------------------------------------------------------
# 1. the environment, BEFORE anything from app/ or src/ is imported
# --------------------------------------------------------------------------
BASE_DSN = "postgresql://phantra:phantra@localhost:5432/phantra"
DSN = f"{BASE_DSN}?options=-c%20search_path%3D{SCHEMA}"

BLANK = """ACCOUNT_KEYS_SECRET ACEDATA_API_KEY FAL_KEY FAL_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
GOOGLE_CSE_ID GOOGLE_CSE_KEY HIGGSFIELD_API_KEY_ID HIGGSFIELD_API_KEY_SECRET IG_ACCESS_TOKEN
IG_BUSINESS_ID IG_GRAPH_TOKEN IG_RESEARCH_APP_ID IG_USER_ID INSTAGRAM_ACCESS_TOKEN
INSTAGRAM_USER_ID FB_GRAPH_TOKEN LANGSMITH_API_KEY LANGSMITH_TRACING R2_ACCESS_KEY_ID
R2_ACCOUNT_ID R2_BUCKET R2_PUBLIC_BASE_URL R2_SECRET_ACCESS_KEY REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET SERPER_API_KEY STRIPE_SECRET_KEY STRIPE_WEBHOOK_ENDPOINT
STRIPE_PRICE_CREATOR STRIPE_PRICE_CREATOR_YEAR STRIPE_PRICE_STARTER STRIPE_PRICE_STARTER_YEAR
STRIPE_PRICE_STUDIO STRIPE_PRICE_STUDIOS STRIPE_PRICE_STUDIO_YEAR STRIPE_PRICE_TOPUP
STRIPE_AFFILIATE_COUPON SUPABASE_ANON_KEY SUPABASE_JWT_SECRET SUPABASE_PROVIDERS SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY SUPABASE_RAG_DATABASE_URL SOCIAL_DISCORD_BOT_TOKEN
SOCIAL_DISCORD_CLIENT_ID SOCIAL_DISCORD_CLIENT_SECRET SOCIAL_INSTAGRAM_APP_ID
SOCIAL_INSTAGRAM_APP_SECRET SOCIAL_LINKEDIN_CLIENT_ID SOCIAL_LINKEDIN_CLIENT_SECRET
SOCIAL_LINKEDIN_PAGE_CLIENT_ID SOCIAL_LINKEDIN_PAGE_CLIENT_SECRET SOCIAL_REDDIT_CLIENT_ID
SOCIAL_REDDIT_CLIENT_SECRET SOCIAL_X_CLIENT_ID SOCIAL_X_CLIENT_SECRET
SOCIAL_YOUTUBE_CLIENT_ID SOCIAL_YOUTUBE_CLIENT_SECRET TIKTOK_ACCESS_TOKEN TIKTOK_OPEN_ID
ELEVENLABS_API_KEY YOUTUBE_API_KEY PHANTRA_FOLDER_ACCOUNT PHANTRA_MEDIA PHANTRA_KEYFRAME
PHANTRA_KEYFRAME_ON_PICK PHANTRA_UNCANNY PHANTRA_AUTOPILOT NIGHTLY_SPARKS JUDGE
PHANTRA_GRAPH_RESEARCH PHANTRA_GRAPH_SCOUT PHANTRA_MCP_ENGINE STUDIO_URL SITE_URL
PUBLISH_MEDIA_BASE_URL BILLING_RETURN_URL PUBLISH_OPERATOR_ACCOUNT""".split()
for _k in BLANK:
    os.environ[_k] = ""
for _k in [k for k in os.environ if k.endswith("_SPEND_OK") or k in ("PHANTRA_RENDER", "PHANTRA_POST_OK")]:
    os.environ.pop(_k)
os.environ.update({
    "DATABASE_URL": DSN, "RAG_DATABASE_URL": DSN,
    "SESSION_SECRET": "qa-local-session-secret-not-real",
    "QUOTE_SIGNING_SECRET": "qa-local-quote-secret-not-real",
    "STRIPE_WEBHOOK_SECRET": "whsec_qa_local_not_real",
    "PHANTRA_MCP": "1", "PHANTRA_MCP_TOKEN": "qa-local-mcp-token-not-real",
    "FAL_RECOVER": "0", "PHANTRA_WHATS_NEW_SYNC": "0", "DEV_TOOLS": "0",
    "PHANTRA_OPEN_SIGNUP": "1", "PHANTRA_CHECKPOINT": "0", "PHANTRA_MCP_APPS_PROBE": "0",
    "PHANTRA_SESSION_HTTPS_ONLY": "0", "PHANTRA_WATERMARK": "0",
})
try:
    from cryptography.fernet import Fernet
    os.environ["SOCIAL_TOKEN_SECRET"] = Fernet.generate_key().decode()
except Exception:  # pragma: no cover
    pass

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *a, **k: False   # app.main must not read any .env

# -- the network wall -------------------------------------------------------
BLOCKED: list[dict] = []
CURRENT = {"route": "(setup)"}
_LOCAL = ("127.0.0.1", "::1", "localhost")
_real_connect = socket.socket.connect
_real_cc = socket.create_connection
_real_gai = socket.getaddrinfo


def _note_block(what):
    BLOCKED.append({"route": CURRENT["route"], "target": str(what)})


def _guard_connect(self, address, *a, **k):
    if not isinstance(address, tuple) or address[0] in _LOCAL:
        return _real_connect(self, address, *a, **k)
    _note_block(address)
    raise ConnectionRefusedError(f"QA network wall: blocked {address}")


def _guard_cc(address, *a, **k):
    if address[0] in _LOCAL:
        return _real_cc(address, *a, **k)
    _note_block(address)
    raise ConnectionRefusedError(f"QA network wall: blocked {address}")


def _guard_gai(host, *a, **k):
    if host in (None, *_LOCAL):
        return _real_gai(host, *a, **k)
    _note_block(host)
    raise socket.gaierror(f"QA network wall: blocked DNS {host}")


socket.socket.connect = _guard_connect
socket.create_connection = _guard_cc
socket.getaddrinfo = _guard_gai

import psycopg  # noqa: E402
from psycopg.conninfo import conninfo_to_dict  # noqa: E402

_pg_sync = psycopg.Connection.connect.__func__


def _pg_guarded(cls, conninfo="", **kwargs):
    params = conninfo_to_dict(conninfo or "", **{k: kwargs[k] for k in ("host", "hostaddr") if kwargs.get(k)})
    host = str(params.get("hostaddr") or params.get("host") or "")
    if host not in ("", *_LOCAL) and not host.startswith("/"):
        raise RuntimeError(f"QA wall: refused Postgres host {host!r}")
    return _pg_sync(cls, conninfo, **kwargs)


psycopg.Connection.connect = classmethod(_pg_guarded)
psycopg.connect = psycopg.Connection.connect

# --------------------------------------------------------------------------
# 2. the schema
# --------------------------------------------------------------------------
_admin = psycopg.connect(BASE_DSN, autocommit=True)
_admin.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
_admin.execute(f"CREATE SCHEMA {SCHEMA}")
TMP = Path(tempfile.mkdtemp(prefix=f"phantra-{SCHEMA}-"))


def drop_schema():
    if not ARGS.keep:
        try:
            _admin.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        except Exception as e:  # pragma: no cover
            print("could not drop schema:", e)


# --------------------------------------------------------------------------
# 3. the app, from THIS checkout
# --------------------------------------------------------------------------
sys.path.insert(0, str(WT))
import app as _app_pkg  # noqa: E402
import src as _src_pkg  # noqa: E402

assert str(Path(_app_pkg.__file__).resolve()).startswith(str(WT)), \
    f"app imported from {_app_pkg.__file__}, not {WT}: drop the editable finder (see header)"
assert str(Path(_src_pkg.__file__).resolve()).startswith(str(WT)), _src_pkg.__file__

import importlib  # noqa: E402

import app.main as app_main  # noqa: E402
from app import auth, jobs  # noqa: E402
from src import accounts, db, ledger  # noqa: E402


def redirect_write_roots():
    """conftest's OUTPUT_ROOTS (read from the file, so a new root is picked up)
    plus every module-level element-folder path, all under TMP."""
    tree = ast.parse((WT / "tests" / "conftest.py").read_text())
    roots = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "OUTPUT_ROOTS" for t in node.targets):
            roots = ast.literal_eval(node.value)
    moved = 0
    for module_name, attr, rel in roots:
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            continue
        setattr(mod, attr, TMP / rel)
        moved += 1
    for module_name in ("src.asset_shelf", "src.locations", "src.mcp_server", "app.main", "app.api",
                        "app.cut_routes"):
        mod = importlib.import_module(module_name)
        for attr in ("LOCATIONS_DIR", "CHARACTERS_DIR", "PROPS_DIR"):
            if hasattr(mod, attr):
                setattr(mod, attr, TMP / getattr(mod, attr).name)
                moved += 1
    from src import asset_shelf
    asset_shelf.PHOTO_DIRS = {"location": TMP / "locations", "character": TMP / "characters",
                              "prop": TMP / "props"}
    for d in ("locations", "characters", "props", "data/renders/fal", "data/renders/nano", "data/refs"):
        (TMP / d).mkdir(parents=True, exist_ok=True)
    return moved


MOVED = redirect_write_roots()

import logging  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)

FA = app_main.app

# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------
RESULTS: list[dict] = []


def record(phase, method, path, status, ok, why="", expect="", excerpt="", route=None):
    RESULTS.append({"phase": phase, "method": method, "path": path, "route": route or path,
                    "status": status, "ok": ok, "why": why, "expect": expect,
                    "excerpt": (excerpt or "")[:240]})
    if not ARGS.quiet and ok is False:
        print(f"  FAIL [{phase}] {method} {path} -> {status} {why} :: {(excerpt or '')[:160]}")


def excerpt_of(resp) -> str:
    try:
        return resp.text[:400].replace("\n", " ")
    except Exception:
        return ""


def readable(resp) -> bool:
    """A 4xx a person (or a client) can act on: JSON with a reason, or short text."""
    try:
        j = resp.json()
        if isinstance(j, dict) and any(j.get(k) for k in ("detail", "error", "message", "code")):
            return True
        return False
    except Exception:
        t = (resp.text or "").strip()
        return 0 < len(t) < 4000


def degraded(resp) -> bool:
    """503 with a reason: a provider or service this server has no key for. With every
    key blanked on purpose, that is the designed answer, not a failure."""
    return resp.status_code == 503 and readable(resp)


def int_params(row) -> set:
    op = (OPENAPI["paths"].get(row["path"]) or {}).get(row["method"].lower()) or {}
    return {p["name"] for p in op.get("parameters", []) if p.get("in") == "path"
            and "integer" in types_of(p.get("schema") or {})}


# --------------------------------------------------------------------------
# 4. the client and the seeds
# --------------------------------------------------------------------------
def png_bytes(w=768, h=1024, color=(180, 90, 40)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


SESSIONS: dict = {}


def cookie_for(user_id: str) -> str:
    return auth._serializer().dumps({"uid": str(user_id)})


def main():  # noqa: C901 -- one long script on purpose: it reads top to bottom
    started = time.time()
    with TestClient(FA, raise_server_exceptions=False) as client:
        for name in ("httpx", "httpcore", "mcp", "mcp.server.streamable_http_manager"):
            logging.getLogger(name).setLevel(logging.WARNING)
            logging.getLogger(name).disabled = True
        print(f"lifespan ran; schema {SCHEMA}; {MOVED} write roots under {TMP}")
        OPENAPI.update(FA.openapi())
        if ARGS.openapi:
            Path(ARGS.openapi).write_text(json.dumps(OPENAPI, indent=1, sort_keys=False) + "\n")
        ctx = seed(client)
        routes = route_table()
        ROUTES.extend(routes)
        if ARGS.only == "seed":
            return
        r = call(client, "GET", f"/public/share/{ctx['B']['share_token']}", None)
        ctx["B"]["share_ok_before"] = r.status_code
        snap_b_before = snapshot_owned(ctx["B"]["account"])
        for fn, args in ((unauth_pass, (client, routes, ctx)), (tenancy_pass, (client, routes, ctx)),
                         (tenancy_keys_pass, (client, ctx)),
                         (bad_input_pass, (client, routes, ctx)), (authed_pass, (client, routes, ctx)),
                         (model_text_pass, (client, ctx)), (body_tenancy_pass, (client, ctx)),
                         (plugin_pass, (client, ctx)), (csrf_pass, (client, ctx)),
                         (quote_token_pass, (client, ctx)),
                         (ledger_pass, (client, ctx)), (jobs_pass, (client, ctx)), (stripe_pass, (client, ctx)),
                         (mcp_pass, (client, ctx)), (shared_tables_pass, (client, ctx)),
                         (delete_pass, (client, routes, ctx))):
            if ARGS.only and fn.__name__ not in ARGS.only.split(","):
                continue
            try:
                fn(*args)
            except Exception as e:
                traceback.print_exc()
                record("harness", "-", fn.__name__, "crashed", False, why=f"{type(e).__name__}: {e}")
        r = call(client, "GET", f"/public/share/{ctx['B']['share_token']}", None)
        record("tenancy", "GET", "/public/share/{B's token} after A's share/unshare calls on B's asset",
               r.status_code, r.status_code == ctx["B"].get("share_ok_before"),
               expect=f"{ctx['B'].get('share_ok_before')} (as before)", excerpt=excerpt_of(r)[:120])
        snap_b_after = snapshot_owned(ctx["B"]["account"])
        changed = sorted(t for t in snap_b_before if snap_b_before[t] != snap_b_after.get(t))
        record("tenancy", "-", "account B's rows, every OWNED table, before vs after A's requests",
               ",".join(changed) or "unchanged", not changed,
               why=("B's rows changed in: " + ", ".join(changed)) if changed else
               f"{len(snap_b_before)} owned tables hashed, none changed")
    for b in BLOCKED:
        expected = any(x in b["route"] for x in EXPECTED_FETCH)
        record("network", "-", b["route"], "blocked", None if expected else False,
               why=(f"its SSRF guard resolving the user's address ({b['target'][:60]})" if expected
                    else f"tried to reach {b['target'][:80]}"))
    report(started, routes)


# -- seeds -------------------------------------------------------------------
def seed(client) -> dict:
    from src import generative, mcp_server, render_assets

    ctx = {}
    for who, color in (("A", (200, 60, 60)), ("B", (60, 60, 200))):
        uid = accounts.create_user(f"qa-{who.lower()}@example.test", f"QA {who}", claimed=True)
        acct = accounts.upsert_account(f"qa-{who.lower()}", f"QA {who}", "#123456")
        accounts.add_member(acct, uid)
        ledger.grant(acct, 2000, "purchase", source_ref=f"qa-seed-{who}", note="qa seed")
        cookie = cookie_for(uid)
        c = {"user": uid, "account": acct, "cookie": cookie, "_who": who}
        ctx[who] = c

        def call(method, path, **kw):
            client.cookies.clear()
            return client.request(method, path, headers={"Cookie": f"phantra_session={cookie}",
                                                         "X-Phantra-Model-Connection": "1"}, **kw)

        # an element with a photo, through the Elements page's own door
        r = call("POST", "/api/assets/characters",
                 data={"name": f"Qa{who} Hero", "role": "lead"},
                 files=[("photos", (f"qa{who}.png", png_bytes(color=color), "image/png"))])
        assert r.status_code < 300, f"element seed {who}: {r.status_code} {r.text[:300]}"
        el = r.json()
        c["element"] = el
        els = call("GET", "/api/assets?scope=elements").json()
        items = els.get("items") or els.get("assets") or els.get("characters") or []
        if isinstance(els, dict) and not items:
            for v in els.values():
                if isinstance(v, list) and v:
                    items = v
                    break
        c["elements_listing"] = items
        ch = next((i for i in items if "Qa" in json.dumps(i)), items[0] if items else {})
        c["character_id"] = ch.get("id")
        photo = None
        for key in ("photos", "photo_refs", "refs", "images"):
            v = ch.get(key)
            if isinstance(v, list) and v:
                photo = v[0] if isinstance(v[0], str) else (v[0].get("ref") or v[0].get("url"))
                break
        photo = photo or ch.get("ref") or ch.get("photo") or ch.get("image")
        c["photo_ref"] = photo
        m = re.match(r"/characters/([^/]+)/photo/([^/?]+)", photo or "")
        c["character_slug"] = m.group(1) if m else (ch.get("slug") or ch.get("name"))
        c["photo_file"] = m.group(2) if m else "qa.png"
        # a prop and a location too, for the DELETE routes
        r = call("POST", "/api/assets/props", data={"name": f"Qa{who} Cup", "category": "product"},
                 files=[("photos", (f"qa{who}p.png", png_bytes(color=color), "image/png"))])
        c["prop"] = r.json() if r.status_code < 300 else {}
        r = call("POST", "/api/assets/locations", data={"name": f"Qa{who} Garage"},
                 files=[("photos", (f"qa{who}l.png", png_bytes(color=color), "image/png"))])
        c["location"] = r.json() if r.status_code < 300 else {}
        if r.status_code >= 300:
            print(f"  seed note: location for {who} -> {r.status_code} {r.text[:200]}")
        # their ids come from the listing ("prop-3", "location-4"), like the character's
        relist = call("GET", "/api/assets?scope=elements").json()
        rows = []
        for v in (relist.values() if isinstance(relist, dict) else [relist]):
            if isinstance(v, list):
                rows += [i for i in v if isinstance(i, dict)]
        if c["location"].get("ok") and not any(str(i.get("id", "")).startswith("location") for i in rows):
            # the Elements page's own create, with the describe call failing (no Gemini key here):
            # "ok", photos saved, yet no locations row, so the place is not in the listing
            record("seed", "POST", "/api/assets/locations (describe fails) -> /api/assets?scope=elements",
                   "not listed", False, expect="the saved place is listed",
                   why=f"ok:true, photos {c['location'].get('photos')}, note {c['location'].get('note')!r}; "
                       f"listing ids {[str(i.get('id')) for i in rows]}")
        for kind in ("prop", "location"):
            hit = next((i for i in rows if str(i.get("id", "")).startswith(kind)), None)
            if hit and _num((c[kind] or {}).get("id")) is None:
                c[kind] = {**(c[kind] or {}), "id": hit["id"]}
        # a project
        r = call("POST", "/api/projects", json={"title": f"QA {who} project", "brief": "a test brief"})
        assert r.status_code < 300, f"project seed {who}: {r.status_code} {r.text[:200]}"
        pj = r.json()
        c["project_id"] = pj.get("id") or (pj.get("project") or {}).get("id")
        # a scene held to the element's photo (the connector's write door, as 10-22 did)
        out = mcp_server.write_scene(
            f"QA {who}: a woman lifts a red cup in a quiet garage, slow push in.",
            seconds=5, refs=[photo] if photo else None, title=f"QA {who} scene",
            project_id=c["project_id"], account_id=acct)
        c["scene_id"] = out.get("scene_id")
        c["scene_write"] = {k: out.get(k) for k in ("scene_id", "needs_reference", "note")}
        # a generated_assets row (a render on the Library wall) with a real file behind it
        name = f"fal/qa-{who.lower()}-still-{'0' * 31}{1 if who == 'A' else 2}.jpg"
        (TMP / "data" / "renders" / name).parent.mkdir(parents=True, exist_ok=True)
        (TMP / "data" / "renders" / name).write_bytes(png_bytes(64, 64, color))
        from src.shot import Shot
        sid = generative.add_shot(Shot(subject="qa", action="seed"), account_id=acct)
        gid = generative.record_generation(sid, "fal", "qa seed still",
                                           params={"provider": "fal", "model": "qa"},
                                           output_path=str(TMP / "data" / "renders" / name),
                                           cost_usd=0.0, account_id=acct)
        asset = render_assets.record(generation_id=gid, tool="fal", model="qa",
                                     media_kind="image", prompt=f"QA {who} still",
                                     media_url=f"/renders/{name}", account_id=acct)
        c["asset_id"] = asset["id"]
        c["gen_handle"] = f"gen:{asset['id']}"
        # a cut project
        r = call("POST", "/api/cut/projects", json={"title": f"QA {who} cut"})
        cj = r.json() if r.status_code < 300 else {}
        c["cut_id"] = cj.get("id") or (cj.get("project") or {}).get("id")
        # a brand kit
        r = call("POST", "/api/brand-kits", json={"name": f"QA {who} kit"})
        kj = r.json() if r.status_code < 300 else {}
        c["kit_id"] = kj.get("id") or (kj.get("kit") or {}).get("id")
        # a workflow canvas
        r = call("POST", "/api/workflows", json={"name": f"QA {who} canvas", "graph": {"nodes": []}})
        wj = r.json() if r.status_code < 300 else {}
        c["workflow_id"] = wj.get("id") or (wj.get("workflow") or {}).get("id")
        # a share of the render (public page token)
        r = call("POST", f"/api/assets/generated/{c['asset_id']}/share")
        sj = r.json() if r.status_code < 300 else {}
        c["share"] = sj
        c["share_token"] = sj.get("token") or (sj.get("share") or {}).get("token")
        # a social connection (sealed with the local made-up secret) and a draft post
        try:
            from src import posts, social_connections
            from src.social.base import Connected
            conn = social_connections.save(acct, "discord", Connected(
                external_id=f"qa-{who}", display_name=f"QA {who} channel", access_token="not-a-token"))
            c["connection_id"] = conn["id"]
            post = posts.create(acct, connection_id=conn["id"], source_ref=c["gen_handle"],
                                caption="qa", draft=True)
            c["post_id"] = post["id"]
        except Exception as e:
            c["connection_err"] = f"{type(e).__name__}: {e}"
        # creative project (the canvas doc)
        r = call("POST", "/api/creative-projects", json={"title": f"QA {who}", "payload": {"brief": "qa"}})
        c["creative"] = r.json() if r.status_code < 300 else {"status": r.status_code, "text": r.text[:200]}
        c["creative_id"] = (c["creative"] or {}).get("id") or ((c["creative"] or {}).get("project") or {}).get("id")
        # a job in the registry
        job = jobs.create("render", f"{who}'s private render", account_id=acct)
        c["job_id"] = job["id"]
        # a plugin token (the editor panels' bearer)
        from src import plugin_tokens
        pair = plugin_tokens.start("premiere", "qa-device")
        made = plugin_tokens.approve(pair["code"], acct, uid)
        c["plugin_secret"] = pair["secret"]
        c["plugin_token_id"] = made["id"]
        c["call"] = call
    for who in ("A", "B"):
        c = ctx[who]
        print(f"seeded {who}: account {c['account']} element {c['character_id']} photo {c['photo_ref']!r} "
              f"project {c['project_id']} scene {c['scene_id']} asset {c['asset_id']} cut {c['cut_id']} "
              f"kit {c['kit_id']} workflow {c['workflow_id']} post {c.get('post_id')} "
              f"conn {c.get('connection_id')} creative {c.get('creative_id')} job {c['job_id']} "
              f"share {bool(c.get('share_token'))} {c.get('connection_err', '')}")
    return ctx


def snapshot_owned(account_id: int) -> dict:
    out = {}
    with db.connect(DSN) as conn:
        for table in sorted(db.OWNED_TABLES):
            try:
                row = conn.execute(
                    f"SELECT count(*) AS n, md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) AS h "
                    f"FROM {table} t WHERE account_id = %s", (account_id,)).fetchone()
                out[table] = (row["n"], row["h"])
            except Exception as e:
                conn.rollback() if hasattr(conn, "rollback") else None
                out[table] = ("err", type(e).__name__)
    return out


# -- the route table -----------------------------------------------------------
SPEND_HINTS = re.compile(
    r"\b(fal\.(generate|run|_submit|_request)|nano_banana\.|genai\.|gemini|_gemini|creative_guide\.respond|"
    r"guide_tools|effects\.run|run_effect|talking_photo|run_voice|run_talk|voice_clone\.|dubbing|tts|"
    r"elevenlabs|stripe|checkout|charge\.|ledger\.hold|approve_render|approve_keyframes|"
    r"keyframe_scene|element_sheet|_create_gate|draw_sheet|generate_scene|shootgen|timeline\.ensure|"
    r"index\.|whisper|look_research|linkrefs|refbin\.public_bytes|clip_edit|quick_edit|music|voiceover|"
    r"render_qc|workflow_runner|scene_chain|orchestrator|evals?_run|run_eval|draft_brief|imagesearch)\b",
    re.I)


def _deps(dependant, seen=None):
    seen = seen or set()
    for d in getattr(dependant, "dependencies", []) or []:
        if id(d) in seen:
            continue
        seen.add(id(d))
        yield d.call
        yield from _deps(d, seen)


def route_table() -> list[dict]:
    import inspect

    import fastapi.routing as fr
    from starlette.routing import Mount, Route
    rows = []

    def add(methods, path, endpoint, dependant, schema, kind="api"):
        try:
            src_ = inspect.getsource(endpoint)
        except Exception:
            src_ = ""
        calls = set(_deps(dependant)) if dependant is not None else set()
        needs_account = auth.current_account_id in calls
        optional = auth.optional_account_id in calls or "optional_account_id" in src_
        for m in sorted(set(methods) - {"HEAD"}) or [""]:
            rows.append({"method": m, "path": path, "endpoint": f"{endpoint.__module__}.{endpoint.__name__}",
                         "schema": schema, "needs_account": needs_account, "optional_account": optional,
                         "source": src_, "kind": kind,
                         "params": re.findall(r"{(\w+)(?::\w+)?}", path)})

    for r in FA.routes:
        if isinstance(r, fr._IncludedRouter):
            for c in r.effective_route_contexts():
                add(c.methods or [], c.path, c.endpoint, c.dependant, bool(c.include_in_schema))
        elif isinstance(r, fr.APIRoute):
            add(r.methods, r.path, r.endpoint, r.dependant, r.include_in_schema)
        elif isinstance(r, Mount):
            rows.append({"method": "*", "path": r.path, "endpoint": type(r.app).__name__, "schema": False,
                         "needs_account": False, "optional_account": False, "source": "", "kind": "mount",
                         "params": []})
        elif isinstance(r, Route):
            add(r.methods or [], r.path, r.endpoint, None, bool(r.include_in_schema), kind="route")
    for row in rows:
        row["class"] = classify(row)
    return rows


SPEND_OVERRIDE = {
    # read by hand: these reach a provider or take a hold even though the text test misses it,
    # or the text test matches a name that only READS a price
}
READ_OVERRIDE_PAT = re.compile(r"/quote$|/menu$|/render$|/prompt-preview$|/insights$")


def classify(row) -> str:
    m, p, s = row["method"], row["path"], row["source"]
    if (m, p) in SPEND_OVERRIDE:
        return SPEND_OVERRIDE[(m, p)]
    if m in ("GET", "") or row["kind"] == "mount":
        return "read"
    if READ_OVERRIDE_PAT.search(p) or p.endswith("/quote"):
        return "write" if m != "GET" else "read"   # a quote spends nothing; POST quotes write nothing either
    if SPEND_HINTS.search(s):
        return "spend"
    return "write"


# -- path filling ------------------------------------------------------------------
def fill(path: str, who: dict, *, bad: str | None = None, only=None) -> tuple[str | None, str]:
    """The path with `who`'s ids, or (None, why) when a param cannot be filled.
    `bad` replaces every int-ish param with that literal."""
    p = path
    params = re.findall(r"{(\w+)(?::\w+)?}", path)
    for name in params:
        val = value_for(path, name, who)
        if val is None:
            return None, f"no value for {{{name}}}"
        if bad is not None and (name in only if only is not None else name not in (
                "category", "plural", "provider", "studio_id", "name", "space", "slug", "filename", "token",
                "handle", "ref")):
            val = bad
        p = re.sub(r"{%s(?::\w+)?}" % name, str(val), p, count=1)
    return p, ""


def _num(v):
    m = re.search(r"(\d+)$", str(v or ""))
    return int(m.group(1)) if m else None


def value_for(path: str, name: str, c: dict):
    if name == "project_id":
        if path.startswith("/api/cut/"):
            return c.get("cut_id")
        if path.startswith("/api/creative-projects"):
            return c.get("creative_id")
        return c.get("project_id")
    if name in ("concept_id", "scene_id"):
        return c.get("scene_id")
    if name == "shot_n":
        return 1
    if name == "asset_id":
        if "/brand-kits/" in path:
            return 1   # no kit asset seeded: probes the 404 path only
        return c.get("asset_id")
    if name == "category":
        return "character"
    if name == "plural":
        return "characters"
    if name in ("item_id",):
        if "/assets/" in path:
            return _num(c.get("character_id"))
        return 1     # what's-new item: shared table, no seeded item
    if name == "character_id":
        return _num(c.get("character_id"))
    if name == "prop_id":
        return _num((c.get("prop") or {}).get("id"))
    if name == "location_id":
        return _num((c.get("location") or {}).get("id"))
    if name == "kit_id":
        return c.get("kit_id")
    if name == "workflow_id":
        return c.get("workflow_id")
    if name == "job_id":
        return c.get("job_id")
    if name == "post_id":
        return c.get("post_id")
    if name == "connection_id":
        return c.get("connection_id")
    if name == "token_id":
        return c.get("plugin_token_id")
    if name == "handle":
        return c.get("gen_handle")
    if name == "ref":
        return c.get("gen_handle")
    if name == "provider":
        return "discord" if "social" in path else "higgsfield"
    if name == "studio_id":
        return "ads"
    if name == "name":
        return "balance"
    if name == "slug":
        return f"qa-{'a' if c.get('_who') == 'A' else 'b'}" if path.startswith("/account") else c.get("character_slug")
    if name == "token":
        return c.get("share_token") if path.startswith("/public/share") else "qa-not-a-token"
    if name == "session_id":
        return "1"
    if name in ("golden_id", "run_id", "video_id"):
        return 1
    if name == "voice_id":
        return "qa-voice"
    if name == "filename":
        return c.get("photo_file") or "qa.png"
    if name == "space":
        return "qa-garage"
    return None


def call(client, method, path, who=None, *, bare=False, **kw):
    client.cookies.clear()
    headers = {**({} if bare else {"X-Phantra-Model-Connection": "1"}), **dict(kw.pop("headers", {}) or {})}
    if who is not None:
        headers["Cookie"] = f"phantra_session={who['cookie']}"
    CURRENT["route"] = f"{method} {path}"
    t0 = time.time()
    try:
        r = client.request(method if method else "GET", path, headers=headers, timeout=60, **kw)
    except Exception as e:
        class _R:
            status_code = 599
            text = f"client error: {type(e).__name__}: {e}"
            headers = {}

            def json(self):
                raise ValueError
        r = _R()
    r.elapsed_s = time.time() - t0
    return r


PUBLIC_BY_DESIGN = {
    # path prefix -> why it is open
    "/auth/": "sign-in doors", "/oauth/consent": "the connector's consent page (signs in itself)",
    "/u/": "one-time upload link, the token is the capability",
    "/public/": "public share page / what's new", "/billing/webhook": "Stripe, signature-checked",
    "/plugin/v1/pair": "panel pairing start (no account yet)",
    "/healthz": "liveness", "/signin": "sign-in page", "/privacy": "policy page", "/favicon.ico": "icon",
    "/icon.png": "icon", "/robots.txt": "crawlers", "/llms.txt": "crawlers", "/sitemap.xml": "crawlers",
    "/locations/": "photo route (404 unless the folder is the caller's)",
    "/characters/": "photo route", "/props/": "photo route", "/ui": "classic shell (hands off to studio)",
    "/docs": "FastAPI docs", "/redoc": "FastAPI docs", "/openapi.json": "FastAPI schema",
    "/account/": "workspace switch (checks membership)",
}


def public_reason(path):
    if path == "/":
        return "landing"
    for pre, why in PUBLIC_BY_DESIGN.items():
        if path.startswith(pre) or path == pre.rstrip("/"):
            return why
    return ""


def schema_body(row, mode="valid"):
    """A JSON body from the route's OpenAPI request schema: `valid` fills required
    fields with plausible values, `wrong` gives every field a wrong type, `huge`
    puts 1 MB in every string field."""
    spec = OPENAPI
    op = (spec["paths"].get(row["path"]) or {}).get(row["method"].lower()) or {}
    content = (op.get("requestBody") or {}).get("content") or {}
    schema = (content.get("application/json") or {}).get("schema")
    if schema is None:
        return None
    schema = deref(schema)
    props = {k: deref(v) for k, v in (schema.get("properties") or {}).items()}
    required = schema.get("required") or []
    if mode == "valid":
        return {k: sample(props.get(k, {})) for k in required}
    if mode == "wrong":
        return {k: wrong(v) for k, v in props.items()} or {"x": 1}
    if mode == "huge":
        big = "A" * 1_000_000
        out = {k: big for k, v in props.items() if "string" in types_of(v)}
        for k in required:
            out.setdefault(k, sample(props.get(k, {})))
        return out or {"prompt": big}
    raise ValueError(mode)


def deref(s):
    while isinstance(s, dict) and "$ref" in s:
        s = OPENAPI["components"]["schemas"][s["$ref"].rsplit("/", 1)[1]]
    return s or {}


def types_of(s):
    s = deref(s)
    if "type" in s:
        return {s["type"]}
    out = set()
    for alt in s.get("anyOf", []) + s.get("oneOf", []):
        out |= types_of(alt)
    return out


def sample(s):
    s = deref(s)
    if "enum" in s:
        return s["enum"][0]
    if "const" in s:
        return s["const"]
    for alt in s.get("anyOf", []) + s.get("oneOf", []):
        if deref(alt).get("type") != "null":
            return sample(alt)
    t = s.get("type")
    return {"string": "qa", "integer": 1, "number": 1.0, "boolean": False, "array": [],
            "object": {}}.get(t, "qa")


def wrong(s):
    ts = types_of(s)
    if "string" in ts:
        return {"not": "a string"}
    if "integer" in ts or "number" in ts:
        return "not-a-number"
    if "boolean" in ts:
        return {"not": "a bool"}
    if "array" in ts:
        return "not-a-list"
    if "object" in ts:
        return "not-an-object"
    return {"x": [1, 2]}


OPENAPI: dict = {}
ROUTES: list = []

# routes whose own-account call is skipped, with the reason (they log the caller out,
# spend for real, or are exercised in their own phase below)
OWN_SKIP = {
    ("POST", "/auth/logout"): "logs the session out (checked in unauth pass)",
    ("GET", "/auth/logout"): "logs the session out",
    ("POST", "/billing/webhook"): "Stripe phase",
    ("GET", "/api/jobs/stream"): "SSE phase (infinite stream; TestClient buffers whole bodies)",
    ("POST", "/plugin/v1/signout"): "revokes the plugin token (plugin phase)",
}


def is_destructive(row):
    return row["method"] == "DELETE" or row["path"].endswith(("/forget", "/archive", "/disconnect",
                                                               "/revoke", "/forever"))


# -- passes ------------------------------------------------------------------------
def unauth_pass(client, routes, ctx):
    print("pass: unauthenticated")
    for row in routes:
        if row["kind"] == "mount" or row["path"] == "/api/jobs/stream":
            continue
        path, why = fill(row["path"], ctx["A"])
        if path is None:
            record("unauth", row["method"], row["path"], "skip", None, why=f"skipped: {why}")
            continue
        body = schema_body(row, "valid") if row["method"] in ("POST", "PUT", "PATCH") else None
        r = call(client, row["method"], path, None, **({"json": body} if body is not None else {}))
        st = r.status_code
        pub = public_reason(row["path"])
        if row["needs_account"]:
            ok = st in (401, 403)
            record("unauth", row["method"], path, st, ok, route=row["path"],
                   expect="401/403", why="" if ok else "account route answered without a session",
                   excerpt=excerpt_of(r))
        elif row["path"] == "/plugin/v1/signout":
            ok = st < 500 and '"revoked":true' not in r.text.replace(" ", "")
            record("unauth", row["method"], path, st, ok if st in (401, 403) else (None if ok else False),
                   route=row["path"], expect="401/403 or a no-op", why="no bearer: answers a no-op" if st < 300 else "",
                   excerpt=excerpt_of(r))
        elif row["path"].startswith("/plugin/v1/") and not row["path"].startswith("/plugin/v1/pair"):
            ok = st in (401, 403)
            record("unauth", row["method"], path, st, ok, route=row["path"], expect="401/403 (bearer)",
                   excerpt=excerpt_of(r))
        else:
            ok = st < 500
            record("unauth", row["method"], path, st, ok, route=row["path"],
                   expect=f"<500 (public: {pub or 'no account dependency'})",
                   why="" if ok else "5xx without a session", excerpt=excerpt_of(r))


def tenancy_pass(client, routes, ctx):
    """A, signed in, asks for B's object ids on every route that takes one."""
    print("pass: tenancy (A asks for B's ids)")
    A, B = ctx["A"], ctx["B"]
    for row in routes:
        if row["kind"] == "mount" or not row["params"]:
            continue
        idish = [p for p in row["params"] if p not in ("category", "plural", "provider", "studio_id", "name",
                                                       "shot_n", "space", "filename")]
        if not idish or (row["method"], row["path"]) in OWN_SKIP:
            continue
        if public_reason(row["path"]) and not row["needs_account"]:
            continue
        if row["path"].startswith("/plugin/v1/"):
            continue   # bearer routes: plugin phase
        path_b, why = fill(row["path"], B)
        path_a, _ = fill(row["path"], A)
        if path_b is None:
            record("tenancy", row["method"], row["path"], "skip", None, why=f"skipped: {why}")
            continue
        if path_b == path_a:
            record("tenancy", row["method"], row["path"], "skip", None,
                   why="skipped: no per-account object for this param (same id for A and B)")
            continue
        kw = {}
        if (row["method"], row["path"]) in TENANCY_BODIES:
            kw = TENANCY_BODIES[(row["method"], row["path"])](ctx)
        elif row["method"] in ("POST", "PUT", "PATCH"):
            body = schema_body(row, "valid")
            kw = {"json": body if body is not None else {}}
        r = call(client, row["method"], path_b, A, **kw)
        st = r.status_code
        if st in (403, 404, 410):
            record("tenancy", row["method"], path_b, st, True, route=row["path"], expect="403/404",
                   excerpt=excerpt_of(r))
        elif st == 400 and re.search(r"no such \w+ on this (workspace|account)", r.text, re.I):
            record("tenancy", row["method"], path_b, st, True, route=row["path"], expect="403/404",
                   why="ownership refusal, answered 400 rather than 404 (E-note)", excerpt=excerpt_of(r))
        elif st in (400, 409, 422) or degraded(r):
            record("tenancy", row["method"], path_b, st, None, route=row["path"], expect="403/404",
                   why="inconclusive: refused before ownership was asked (body/state/no key)", excerpt=excerpt_of(r))
            if degraded(r):
                RECHECK.append((row["method"], path_b, row["path"]))
        else:
            leaked = st < 300 and (B["photo_ref"] or "~") in r.text or "QA B" in r.text
            record("tenancy", row["method"], path_b, st, False, route=row["path"], expect="403/404",
                   why=("B's data in the answer" if leaked else f"answered {st} for another account's id"),
                   excerpt=excerpt_of(r))


RECHECK: list = []
# bodies that get past validation, so the answer is about ownership (B's id, A's body)
TENANCY_BODIES = {
    ("PATCH", "/api/assets/generated/{asset_id}"): lambda c: {"json": {"starred": True}},
    ("POST", "/api/concepts/{concept_id}/shots/{shot_n}/media"):
        lambda c: {"json": {"url": "https://media.example.invalid/qa.mp4"}},
    ("POST", "/api/concepts/{concept_id}/shots/{shot_n}/reference"): lambda c: {"json": {"url": c["A"]["photo_ref"]}},
    ("POST", "/api/cut/projects/{project_id}/agent/keep"):
        lambda c: {"json": {"base_id": 1, "ops": [{"op": "set_title", "args": {"title": "qa"}}]}},
    ("POST", "/api/brand-kits/{kit_id}/assets"):
        lambda c: {"data": {"role": "logo_light"}, "files": {"file": ("qa.png", png_bytes(64, 64), "image/png")}},
}
# routes whose job is to fetch an address the person typed: their DNS lookup is the
# public-host check itself (refbin.public_host), refused here by the wall
EXPECTED_FETCH = ("/api/brand-kits/import", "/api/studios/product-from-link")


def tenancy_keys_pass(client, ctx):
    """The tenancy calls that stopped at 'no key' asked again with every provider
    'configured' (a fake key; the network wall still refuses any call out): the
    ownership answer must come before any provider is reached."""
    print("pass: tenancy, keys present")
    from src import fal, gemini_utils, nano_banana
    saved = (gemini_utils.api_key_for, fal._credential, nano_banana.has_key)
    gemini_utils.api_key_for = lambda account_id=None: "qa-fake-not-a-key"
    fal._credential = lambda account_id=None: "qa-fake-not-a-key"
    nano_banana.has_key = lambda account_id=None: True
    try:
        for method, path, route in RECHECK:
            before = len(BLOCKED)
            row = next((x for x in ROUTES if x["path"] == route and x["method"] == method), None)
            r = call(client, method, path, ctx["A"], json=(schema_body(row, "valid") if row else None) or {})
            tried = len(BLOCKED) > before
            ok = r.status_code in (403, 404) and not tried
            record("tenancy", method, path + " (keys present)", r.status_code, ok, route=route, expect="403/404",
                   why=("reached a provider for another account's id" if tried else
                        "" if ok else f"answered {r.status_code}"), excerpt=excerpt_of(r))
    finally:
        gemini_utils.api_key_for, fal._credential, nano_banana.has_key = saved


def bad_input_pass(client, routes, ctx):
    print("pass: bad input")
    A = ctx["A"]
    for row in routes:
        if row["kind"] == "mount" or (row["method"], row["path"]) in OWN_SKIP:
            continue
        if not row["needs_account"] and not row["path"].startswith(("/auth/", "/u/", "/oauth/", "/plugin/v1/pair")):
            continue
        if is_destructive(row):
            continue
        path, why = fill(row["path"], A)
        if path is None:
            continue
        # 1. path ids: not a number, and past Postgres' integer range
        if int_params(row):
            for label, bad in (("non-numeric id", "abc"), ("id past int8", str(2 ** 63)),
                               ("id past int4", str(2 ** 31))):
                pb, _ = fill(row["path"], A, bad=bad, only=int_params(row))
                kw = {"json": schema_body(row, "valid") or {}} if row["method"] in ("POST", "PUT", "PATCH") else {}
                r = call(client, row["method"], pb, A, **kw)
                st = r.status_code
                ok = True if 400 <= st < 500 else (None if st < 500 or degraded(r) else False)
                record("bad_input", row["method"], pb[:120], st, ok, route=row["path"],
                       expect=f"4xx ({label})", why="" if ok else f"{label} -> {st}",
                       excerpt=excerpt_of(r))
        if row["method"] not in ("POST", "PUT", "PATCH"):
            continue
        # 2. no body / 3. wrong types / 4. a 1 MB string
        for label, kw in (("no body", {}),
                          ("wrong types", {"json": schema_body(row, "wrong") or {"x": {"y": [1]}}}),
                          ("1 MB string", {"json": schema_body(row, "huge")}),
                          ("not JSON", {"content": b"\x00\xffnot json{", "headers": {"Content-Type": "application/json"}})):
            r = call(client, row["method"], path, A, **kw)
            st = r.status_code
            if degraded(r):
                ok, why_ = None, f"{label} -> 503 (no key on this server; body not reached)"
            elif st >= 500:
                ok, why_ = False, f"{label} -> {st}"
            elif st >= 400:
                ok = readable(r)
                why_ = "" if ok else f"{label} -> {st} without a readable reason"
            else:
                ok, why_ = None, f"{label} accepted ({st})"
            record("bad_input", row["method"], path, st, ok, route=row["path"], expect=f"4xx readable ({label})",
                   why=why_, excerpt=excerpt_of(r))


def authed_pass(client, routes, ctx):
    print("pass: authenticated as A, own ids")
    A = ctx["A"]
    for row in routes:
        if row["kind"] == "mount" or (row["method"], row["path"]) in OWN_SKIP or is_destructive(row):
            continue
        path, why = fill(row["path"], A)
        if path is None:
            record("authed", row["method"], row["path"], "skip", None, why=f"skipped: {why}")
            continue
        kw = {}
        if row["method"] in ("POST", "PUT", "PATCH"):
            body = CURATED.get((row["method"], row["path"]), lambda c: None)(ctx) \
                if (row["method"], row["path"]) in CURATED else schema_body(row, "valid")
            kw = {"json": body if body is not None else {}}
        if row["path"].startswith("/plugin/v1/") and not row["path"].startswith("/plugin/v1/pair"):
            kw.setdefault("headers", {})["Authorization"] = f"Bearer {A['plugin_secret']}"
        r = call(client, row["method"], path, A, **kw)
        st = r.status_code
        shape = ""
        try:
            j = r.json()
            shape = type(j).__name__ + (":" + ",".join(sorted(j)[:8]) if isinstance(j, dict) else f"[{len(j)}]")
        except Exception:
            shape = (r.headers.get("content-type") or "")[:40]
        if degraded(r):
            ok, why_ = None, "503: provider not configured here (degrades in words)"
        elif st >= 500:
            ok, why_ = False, "5xx on the account's own request"
        elif st >= 400:
            ok, why_ = (None if readable(r) else False), f"{st} (readable)" if readable(r) else f"{st} unreadable"
        else:
            ok, why_ = True, ""
        record("authed", row["method"], path, st, ok, route=row["path"], expect="2xx", why=why_,
               excerpt=f"[{shape}] " + excerpt_of(r))


def delete_pass(client, routes, ctx):
    """Last, because it removes A's seeds: every destructive route on A's own ids."""
    print("pass: destructive routes, A's own ids")
    A = ctx["A"]
    for row in routes:
        if row["kind"] == "mount" or not is_destructive(row) or (row["method"], row["path"]) in OWN_SKIP:
            continue
        path, why = fill(row["path"], A)
        if path is None:
            record("authed", row["method"], row["path"], "skip", None, why=f"skipped: {why}")
            continue
        kw = {"json": schema_body(row, "valid") or {}} if row["method"] in ("POST", "PUT", "PATCH") else {}
        r = call(client, row["method"], path, A, **kw)
        st = r.status_code
        ok = True if st < 400 else (False if st >= 500 else None)
        record("authed", row["method"], path, st, ok, route=row["path"], expect="2xx",
               why="" if st < 400 else f"{st}", excerpt=excerpt_of(r))


CURATED = {
    ("POST", "/api/effects/quote"): lambda c: {"effect": "nano-banana-edit", "sources": [c["A"]["gen_handle"]], "prompt": "make it blue"},
    ("POST", "/api/direct/image/quote"): lambda c: {"model": "nano-banana", "aspect": "1:1"},
    ("POST", "/api/direct/video/quote"): lambda c: {"model": "ltx", "seconds": 5},
    ("POST", "/api/talking-photo/voice/quote"): lambda c: {"script": "A short line read aloud by the QA pass, long enough for the voice check.", "voice": "Rachel"},
    ("POST", "/api/voice/speak/quote"): lambda c: {"text": "Hello from QA."},
    ("PUT", "/api/scenes/{concept_id}/hook"): lambda c: {"hook": "qa hook"},
    ("POST", "/api/creative-guide"): lambda c: {"message": "make me a short ad for a red cup"},
    ("PATCH", "/api/projects/{project_id}"): lambda c: {"title": "QA A project renamed"},
    ("PATCH", "/api/me"): lambda c: {"display_name": "QA A"},
}


def model_text_pass(client, ctx):
    """Gemini is blank: every model-text route must answer in words, never 500."""
    print("pass: model-text routes with Gemini blank")
    A = ctx["A"]
    cases = [
        ("POST", "/api/creative-guide", {"message": "make me a short ad for a red cup", "history": []}),
        ("POST", "/api/creative-guide/act", {"action": "plan", "message": "a red cup ad"}),
        ("POST", "/api/projects/draft-brief", {"title": "QA", "answers": {"goal": "an ad"}}),
        ("POST", "/api/scenes/run", {"idea": "a red cup on a table", "count": 1}),
        ("POST", f"/api/cut/projects/{A['cut_id']}/agent", {"message": "tighten it"}),
        ("POST", f"/api/cut/projects/{A['cut_id']}/voiceover/script", {"brief": "a red cup"}),
        ("POST", "/api/studios/product-from-link", {"url": "https://example.com/p"}),
        ("POST", "/api/retrieve", {"query": "red cup", "k": 3}),
    ]
    for method, path, body in cases:
        r = call(client, method, path, A, json=body)
        st = r.status_code
        ok = (st < 500 or degraded(r)) and (st < 400 or readable(r))
        record("model_text", method, path, st, ok, expect="degrades: readable, never 5xx",
               why="" if ok else "model-text route failed hard with Gemini blank", excerpt=excerpt_of(r))


def body_tenancy_pass(client, ctx):
    """Ids carried in a BODY or query, not the path: B's objects named by A."""
    print("pass: tenancy, ids in bodies")
    A, B = ctx["A"], ctx["B"]
    cases = [
        ("POST", "/api/effects/quote", {"effect": "nano-banana-edit", "sources": [B["gen_handle"]], "prompt": "make it blue"}),
        ("POST", "/api/cut/assemble", {"concept_id": B["scene_id"]}),
        ("POST", "/api/cut/projects", {"title": "steal", "handles": [B["gen_handle"]]}),
        ("POST", "/api/cut/projects", {"title": "steal", "concept_id": B["scene_id"]}),
        ("POST", "/api/posts", {"connection_id": B.get("connection_id"), "source": A["gen_handle"], "draft": True}),
        ("POST", "/api/posts", {"connection_id": A.get("connection_id"), "source": B["gen_handle"], "draft": True}),
        ("PUT", f"/api/projects/{A['project_id']}/brand-kit", {"kit_id": B["kit_id"]}),
        ("PUT", "/api/assistant/project", {"project_id": B["project_id"], "turns": []}),
        ("POST", f"/api/concepts/{A['scene_id']}/refs", {"refs": [B["photo_ref"]]}),
        ("PUT", f"/api/concepts/{A['scene_id']}/shots/1/refs", {"refs": [B["photo_ref"]]}),
        ("POST", "/api/quick-edit", {"tool": "trim_clip", "source": B["gen_handle"], "start": 0, "end": 1}),
        ("POST", "/api/whats-new/seen", {"ids": ["1"]}),
    ]
    for method, path, body in cases:
        r = call(client, method, path, A, json=body)
        st = r.status_code
        text = r.text
        took = st < 300 and (B["gen_handle"] in text or (B["photo_ref"] or "~") in text
                             or f"\"kit_id\": {B['kit_id']}" in text or "QA B" in text)
        if st >= 500:
            ok, why_ = False, "5xx"
        elif took:
            ok, why_ = False, "accepted B's object id and echoed it"
        elif st < 300:
            ok, why_ = None, "2xx: check the stored row (B snapshot covers writes to B)"
        elif st == 422:
            ok, why_ = None, "inconclusive: refused on the body's shape before ownership"
        else:
            ok, why_ = True, ""
        record("tenancy_body", method, path, st, ok, expect="refused (B's id in the body)", why=why_,
               excerpt=excerpt_of(r))
    # the B id read back through A's own objects
    with db.connect(DSN) as conn:
        row = conn.execute("SELECT shots_json FROM shoot_concepts WHERE id = %s", (A["scene_id"],)).fetchone()
        holds_b = (B["photo_ref"] or "~") in (row["shots_json"] if row else "")
    record("tenancy_body", "-", "A's scene after the ref writes", "holds B's photo" if holds_b else "clean",
           not holds_b, why="A's scene now references B's photo" if holds_b else "")


def plugin_pass(client, ctx):
    print("pass: plugin bearer")
    A, B = ctx["A"], ctx["B"]
    h = {"Authorization": f"Bearer {A['plugin_secret']}"}
    for method, path, kw, expect in (
            ("GET", "/plugin/v1/me", {}, (200,)),
            ("GET", f"/plugin/v1/scenes/{B['scene_id']}/clips", {}, (403, 404)),
            ("GET", f"/plugin/v1/download/{B['gen_handle']}", {}, (403, 404)),
            ("GET", f"/plugin/v1/jobs/{B['job_id']}", {}, (403, 404)),
            ("GET", f"/plugin/v1/scenes/{A['scene_id']}/clips", {}, (200,)),
            ("GET", "/plugin/v1/me", {"headers": {"Authorization": "Bearer phx_not_a_real_token"}}, (401, 403)),
            ("POST", "/plugin/v1/tools/scene", {"json": {"scene_id": B["scene_id"]}}, (400, 403, 404))):
        hh = kw.pop("headers", h)
        r = call(client, method, path, None, headers=hh, **kw)
        ok = r.status_code in expect
        txt = r.text
        if r.status_code < 300 and ("QA B" in txt):
            ok = False
        record("plugin", method, path, r.status_code, ok, expect="/".join(map(str, expect)),
               excerpt=excerpt_of(r))


def csrf_pass(client, ctx):
    """What a cross-site page could make a signed-in browser do. On https the session
    cookie is SameSite=None (app/auth.issue_session), so a top-level form POST from
    another site carries it. A form can only send the three 'simple' content types
    and no custom header, so these calls carry the cookie, a foreign Origin, and NOT
    X-Phantra-Model-Connection. Providers are stubbed (no network)."""
    print("pass: cross-site form posts (CSRF shape)")
    from src import model_menu, nano_banana
    A = ctx["A"]
    evil = {"Origin": "https://evil.example", "Referer": "https://evil.example/page",
            "Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"}
    acct = A["account"]
    saved = (nano_banana.has_key, nano_banana._client, nano_banana._generate_content)
    nano_banana.has_key = lambda account_id=None: True
    nano_banana._client = lambda account_id=None: object()
    nano_banana._generate_content = lambda client_, model, parts, config=None: _fake_gemini_image()
    try:
        q = call(client, "POST", "/api/direct/image/quote", A, json={"model": model_menu.NANO_ID, "aspect": "1:1"})
        credits = (q.json() if q.status_code == 200 else {}).get("credits")
        before = balance(acct)
        n_before = len(entries_for(acct))
        r = call(client, "POST", "/api/direct/image/run", A, bare=True, headers=evil,
                 files={"prompt": (None, "cross-site still"), "model": (None, model_menu.NANO_ID),
                        "aspect": (None, "1:1"), "expect_credits": (None, str(credits))})
        job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 else {}
        spent = before - balance(acct)
        new = [e["kind"] for e in entries_for(acct)[n_before:]]
        record("csrf", "POST", "/api/direct/image/run (multipart, Origin evil.example, no custom header)",
               r.status_code, r.status_code in (400, 403), expect="refused (403)",
               why=(f"accepted from a foreign Origin: job {job.get('status')}, {spent} credits spent, entries {new}"
                    if r.status_code < 300 else ""), excerpt=excerpt_of(r))
    finally:
        nano_banana.has_key, nano_banana._client, nano_banana._generate_content = saved
    for method, path, kw, label in (
            ("POST", f"/api/assets/generated/{A['asset_id']}/share", {}, "no body: makes A's render public"),
            ("POST", f"/api/projects/{A['project_id']}/archive",
             {"content": b"archived=true", "headers": {"Content-Type": "application/x-www-form-urlencoded"}},
             "urlencoded"),
            ("POST", f"/api/scenes/{A['scene_id']}/approve",
             {"content": b'{"tokens": []}', "headers": {"Content-Type": "text/plain"}}, "text/plain JSON"),
            ("POST", "/api/creative-guide",
             {"content": b'{"message": "hi"}', "headers": {"Content-Type": "text/plain"}}, "guarded route, text/plain"),
            ("POST", "/api/projects",
             {"content": b'{"title": "made cross-site"}', "headers": {"Content-Type": "text/plain"}}, "text/plain JSON")):
        hh = {**evil, **kw.pop("headers", {})}
        r = call(client, method, path, A, bare=True, headers=hh, **kw)
        accepted = r.status_code < 300
        record("csrf", method, f"{path} ({label})", r.status_code, not accepted,
               expect="refused", why="accepted from a foreign Origin" if accepted else "", excerpt=excerpt_of(r))
    # undo the share so later passes see A as seeded
    call(client, "DELETE", f"/api/assets/generated/{A['asset_id']}/share", A)


def _fake_gemini_image():
    png = png_bytes(64, 64)

    class _Inline:
        data = png
        mime_type = "image/png"

    class _Part:
        inline_data = _Inline()
        text = None

    class _Content:
        parts = [_Part()]

    class _Cand:
        content = _Content()

    class _Resp:
        candidates = [_Cand()]
        text = None
        usage_metadata = None
    return _Resp()


# -- money ----------------------------------------------------------------------------
def balance(acct):
    return ledger.available(acct, dsn=DSN)


def entries_for(acct, ref_like=None):
    with db.connect(DSN) as conn:
        q = "SELECT id, kind, delta, ref, generation_id FROM credit_entries WHERE account_id = %s"
        args = [acct]
        if ref_like:
            q += " AND ref LIKE %s"
            args.append(ref_like)
        return [dict(r) for r in conn.execute(q + " ORDER BY id", args).fetchall()]


def quote_token_pass(client, ctx):
    """A billable approve without the signed quote -> 400 missing_quote; a token
    for another account -> wrong_account; a token whose scene changed -> stale_content.
    Every refusal must leave the balance where it was and write no hold."""
    print("pass: quote tokens")
    from src import fal
    A, B = ctx["A"], ctx["B"]
    real_cred = fal._credential
    fal._credential = lambda account_id=None: "qa-fake-not-a-key"   # 'configured', HTTP still walled
    try:
        before = balance(A["account"])
        holds_before = len([e for e in entries_for(A["account"]) if e["kind"] == "hold"])
        r = call(client, "GET", f"/api/scenes/{A['scene_id']}/render", A)
        state = r.json() if r.status_code == 200 else {}
        record("quote", "GET", f"/api/scenes/{A['scene_id']}/render", r.status_code, r.status_code == 200,
               expect="200 with a priced quote", excerpt=excerpt_of(r))
        q = (state.get("scene") or {}).get("quote") or {}
        tokens = [x.get("token") for x in (q.get("renders") or []) if x.get("token")]
        ctx["A"]["render_quote"] = q
        record("quote", "-", "the card's quote is signed", f"{len(tokens)} token(s)", bool(tokens),
               why="" if tokens else "no signed token on the card with QUOTE_SIGNING_SECRET set",
               excerpt=json.dumps({k: q.get(k) for k in ("provider", "model", "credits", "signed")})[:200])
        cases = [("no token", {}, "missing_quote"),
                 ("garbage token", {"tokens": ["phq.garbage.mac"]}, "bad_signature")]
        rb = call(client, "GET", f"/api/scenes/{B['scene_id']}/render", B)
        qb = ((rb.json() if rb.status_code == 200 else {}).get("scene") or {}).get("quote") or {}
        tb = [x.get("token") for x in (qb.get("renders") or []) if x.get("token")]
        if tb:
            cases.append(("B's token on A's scene", {"tokens": tb}, ("wrong_account", "wrong_render")))
            cases.append(("B's token on B's scene, presented by A", None, ("not_found", "wrong_account")))
        for label, body, want in cases:
            path = f"/api/scenes/{A['scene_id']}/approve" if body is not None else f"/api/scenes/{B['scene_id']}/approve"
            r = call(client, "POST", path, A, json=body if body is not None else {"tokens": tb})
            code = ""
            try:
                code = r.json().get("error") or r.json().get("code") or (r.json().get("detail") or {}).get("code", "")
            except Exception:
                pass
            want_t = want if isinstance(want, tuple) else (want,)
            ok = r.status_code in (400, 403, 404) and (code in want_t or any(w in r.text for w in want_t))
            record("quote", "POST", f"{path} ({label})", r.status_code, ok, expect=f"4xx {'/'.join(want_t)}",
                   excerpt=excerpt_of(r))
        # stale content: price it, change the shot's words, approve with the old token
        if tokens:
            r = call(client, "POST", f"/api/concepts/{A['scene_id']}/shots/1/prompt", A,
                     json={"prompt": "QA A: the cup is now blue, slow push in."})
            r2 = call(client, "POST", f"/api/scenes/{A['scene_id']}/approve", A, json={"tokens": tokens})
            ok = r2.status_code == 400 and "stale" in r2.text
            record("quote", "POST", f"/api/scenes/{A['scene_id']}/approve (token from before an edit)",
                   r2.status_code, ok, expect="400 stale_content",
                   why="" if ok else f"prompt edit answered {r.status_code}", excerpt=excerpt_of(r2))
        after = balance(A["account"])
        holds_after = len([e for e in entries_for(A["account"]) if e["kind"] == "hold"])
        record("quote", "-", "balance and holds across the refusals", f"{before}->{after}, holds {holds_before}->{holds_after}",
               before == after and holds_before == holds_after, expect="unchanged")
    finally:
        fal._credential = real_cred


class FakeFal:
    """fal's queue, faked at the HTTP layer: submit -> status -> result."""

    def __init__(self, fail_at=None, media="video"):
        self.fail_at, self.media, self.calls = fail_at, media, []

    def __call__(self, url, payload=None, *, account_id=None):
        self.calls.append(url)
        if payload is not None and "/requests/" not in url:
            if self.fail_at == "submit":
                raise RuntimeError("HTTP Error 422: Unprocessable Entity -- qa fake refusal")
            return {"request_id": "qa1", "status_url": "https://queue.fal.run/x/requests/qa1/status",
                    "response_url": "https://queue.fal.run/x/requests/qa1",
                    "cancel_url": "https://queue.fal.run/x/requests/qa1/cancel"}
        if url.endswith("/status"):
            if self.fail_at == "status":
                return {"status": "FAILED", "error": "qa fake: the model failed"}
            return {"status": "COMPLETED"}
        if self.media == "video":
            return {"video": {"url": "https://fal.media/files/qa/out.mp4"}}
        if self.media == "audio":
            return {"audio": {"url": "https://fal.media/files/qa/out.mp3"}}
        return {"images": [{"url": "https://fal.media/files/qa/out.jpg"}]}


BAD_AUDIO = {"on": False}


def _fake_download(url, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix in (".jpg", ".png", ".jpeg", ".webp"):
        out_path.write_bytes(png_bytes(64, 64))
    elif out_path.suffix in (".mp3", ".wav", ".m4a") and not BAD_AUDIO["on"]:
        # one second of real silence (local ffmpeg), so the filing step can measure it
        import shutil
        import subprocess
        ff = shutil.which("ffmpeg") or "/usr/local/bin/ffmpeg"
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1",
                        str(out_path)], check=True)
    else:
        out_path.write_bytes(b"\x00" * 4096)


def wait_job(client, who, job_id, timeout=60):
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        r = call(client, "GET", f"/api/jobs/{job_id}", who)
        if r.status_code == 200:
            last = r.json()
            job = last.get("job", last)
            if job.get("status") in ("done", "failed", "cancelled", "error"):
                return job
        time.sleep(0.3)
    return last.get("job", last) or {"status": "timeout"}


def ledger_pass(client, ctx):
    print("pass: ledger with stubbed providers")
    from src import fal, nano_banana
    A = ctx["A"]
    acct = A["account"]
    saved = (fal._credential, fal._request, fal._download, fal.POLL_SECONDS,
             nano_banana.has_key, nano_banana._client, nano_banana._generate_content)
    fal._credential = lambda account_id=None: "qa-fake-not-a-key"
    fal._download = _fake_download
    fal.POLL_SECONDS = 0
    try:
        # ---- 1. a scene's clip on fal: success, then a failure ----
        for outcome, fake in (("success", FakeFal()), ("failure", FakeFal(fail_at="status"))):
            fal._request = fake
            # a fresh price each time (the scene's clip lands on success; re-render = new hold ref)
            r = call(client, "GET", f"/api/scenes/{A['scene_id']}/render", A)
            q = ((r.json() if r.status_code == 200 else {}).get("scene") or {}).get("quote") or {}
            tokens = [x.get("token") for x in (q.get("renders") or []) if x.get("token")]
            credits = q.get("credits")
            before = balance(acct)
            n_before = len(entries_for(acct))
            r = call(client, "POST", f"/api/scenes/{A['scene_id']}/approve", A, json={"tokens": tokens})
            job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 else {"status": f"http {r.status_code}"}
            after = balance(acct)
            new = entries_for(acct)[n_before:]
            kinds = [e["kind"] for e in new]
            held = -sum(e["delta"] for e in new if e["kind"] == "hold")
            if outcome == "success":
                settled = held - sum(e["delta"] for e in new if e["kind"] == "settle")
                ok = (job.get("status") == "done" and "hold" in kinds and "settle" in kinds
                      and "release" not in kinds and after == before - settled and settled == credits
                      and any(e.get("generation_id") for e in new if e["kind"] == "settle"))
                why = f"quoted {credits}, held {held}, settled {settled}, balance {before}->{after}, entries {kinds}"
            else:
                released = sum(e["delta"] for e in new if e["kind"] == "release")
                ok = (job.get("status") in ("failed", "error") and "hold" in kinds and "release" in kinds
                      and released == held and after == before and "settle" not in kinds)
                why = f"held {held}, released {released}, balance {before}->{after}, entries {kinds}"
            record("ledger", "POST", f"/api/scenes/{{id}}/approve (fal clip, {outcome})", job.get("status"), ok,
                   expect="hold->settle, balance-=quote" if outcome == "success" else "hold->release, balance unchanged",
                   why=why, excerpt=(job.get("error") or job.get("detail") or "")[:200])
            if outcome == "success":
                # the clip landed and a Library row exists for it
                with db.connect(DSN) as conn:
                    n = conn.execute("SELECT count(*) AS n FROM generated_assets WHERE account_id = %s "
                                     "AND concept_id = %s", (acct, A["scene_id"])).fetchone()["n"]
                record("ledger", "-", "the rendered clip is filed in A's Library", n, n >= 1, expect=">=1 row")
        # ---- 2. a still on a fal image model through the Image page ----
        menu = call(client, "GET", "/api/direct/image", A).json()
        models = [m.get("id") or m.get("model") for m in (menu.get("models") or menu.get("items") or [])]
        fal_model = next((m for m in models if m and m in fal.IMAGE_MODELS), None)
        for outcome, fake in (("success", FakeFal(media="image")), ("failure", FakeFal(fail_at="submit", media="image"))):
            fal._request = fake
            if not fal_model:
                record("ledger", "POST", "/api/direct/image/run", "skip", None, why="skipped: no fal image model on the menu")
                break
            qr = call(client, "POST", "/api/direct/image/quote", A, json={"model": fal_model, "aspect": "1:1"})
            credits = (qr.json() if qr.status_code == 200 else {}).get("credits")
            before = balance(acct)
            n_before = len(entries_for(acct))
            r = call(client, "POST", "/api/direct/image/run", A,
                     data={"prompt": "a red cup on a white table", "model": fal_model, "aspect": "1:1",
                           "expect_credits": str(credits)})
            job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 else {"status": f"http {r.status_code}", "error": r.text[:200]}
            after = balance(acct)
            new = entries_for(acct)[n_before:]
            kinds = [e["kind"] for e in new]
            held = -sum(e["delta"] for e in new if e["kind"] == "hold")
            if outcome == "success":
                settled = held - sum(e["delta"] for e in new if e["kind"] == "settle")
                ok = job.get("status") == "done" and kinds[:1] == ["hold"] and "settle" in kinds and \
                    after == before - settled and settled == credits
                why = f"quoted {credits}, held {held}, settled {settled}, balance {before}->{after}, entries {kinds}"
            else:
                released = sum(e["delta"] for e in new if e["kind"] == "release")
                ok = job.get("status") in ("failed", "error") and "release" in kinds and released == held \
                    and after == before
                why = f"held {held}, released {released}, balance {before}->{after}, entries {kinds}"
            record("ledger", "POST", f"/api/direct/image/run (fal {fal_model}, {outcome})", job.get("status"), ok,
                   why=why, excerpt=(job.get("error") or job.get("detail") or "")[:200])
        # ---- 3. a Nano Banana still (Gemini image) ----
        png = png_bytes(64, 64)

        class _Inline:
            data = png
            mime_type = "image/png"

        class _Part:
            inline_data = _Inline()
            text = None

        class _Content:
            parts = [_Part()]

        class _Cand:
            content = _Content()

        class _Resp:
            candidates = [_Cand()]
            text = None
            usage_metadata = None

        nano_banana.has_key = lambda account_id=None: True
        nano_banana._client = lambda account_id=None: object()
        from src import model_menu
        for outcome in ("success", "failure"):
            if outcome == "success":
                nano_banana._generate_content = lambda client_, model, parts, config=None: _Resp()
            else:
                def _boom(client_, model, parts, config=None):
                    raise RuntimeError("qa fake: Gemini said INVALID_ARGUMENT")
                nano_banana._generate_content = _boom
            qr = call(client, "POST", "/api/direct/image/quote", A, json={"model": model_menu.NANO_ID, "aspect": "1:1"})
            credits = (qr.json() if qr.status_code == 200 else {}).get("credits")
            before = balance(acct)
            n_before = len(entries_for(acct))
            r = call(client, "POST", "/api/direct/image/run", A,
                     data={"prompt": "a red cup", "model": model_menu.NANO_ID, "aspect": "1:1",
                           "expect_credits": str(credits)})
            job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 else {"status": f"http {r.status_code}", "error": r.text[:200]}
            after = balance(acct)
            new = entries_for(acct)[n_before:]
            kinds = [e["kind"] for e in new]
            held = -sum(e["delta"] for e in new if e["kind"] == "hold")
            if outcome == "success":
                settled = held - sum(e["delta"] for e in new if e["kind"] == "settle")
                ok = job.get("status") == "done" and "hold" in kinds and "settle" in kinds and \
                    after == before - settled and settled == credits
                why = f"quoted {credits}, held {held}, settled {settled}, balance {before}->{after}, entries {kinds}"
            else:
                released = sum(e["delta"] for e in new if e["kind"] == "release")
                ok = job.get("status") in ("failed", "error") and "release" in kinds and released == held \
                    and after == before
                why = f"held {held}, released {released}, balance {before}->{after}, entries {kinds}"
            record("ledger", "POST", f"/api/direct/image/run (nano, {outcome})", job.get("status"), ok, why=why,
                   excerpt=(job.get("error") or job.get("detail") or "")[:200])
        # ---- 4. a voice (ElevenLabs v3, on fal) ----
        for outcome, fake in (("success", FakeFal(media="audio")), ("failure", FakeFal(fail_at="status", media="audio")),
                              ("made, then filing fails", FakeFal(media="audio"))):
            fal._request = fake
            BAD_AUDIO["on"] = outcome.startswith("made")
            body = {"script": "A short line read aloud by the QA pass, long enough for the voice check.", "voice": "Rachel"}
            qr = call(client, "POST", "/api/talking-photo/voice/quote", A, json=body)
            qj = qr.json() if qr.status_code == 200 else {}
            if qr.status_code != 200:
                record("ledger", "POST", "/api/talking-photo/voice/run", qr.status_code, None,
                       why=f"skipped: quote refused: {qr.text[:120]}")
                break
            before = balance(acct)
            n_before = len(entries_for(acct))
            r = call(client, "POST", "/api/talking-photo/voice/run", A, json={**body, "voice": qj.get("voice", "Rachel"),
                                                                               "expect_credits": qj.get("credits")})
            job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 else {"status": f"http {r.status_code}", "error": r.text[:200]}
            after = balance(acct)
            new = entries_for(acct)[n_before:]
            kinds = [e["kind"] for e in new]
            held = -sum(e["delta"] for e in new if e["kind"] == "hold")
            settled = held - sum(e["delta"] for e in new if e["kind"] == "settle")
            released = sum(e["delta"] for e in new if e["kind"] == "release")
            said = (job.get("error") or job.get("detail") or "")
            extra = ""
            if outcome == "success":
                ok = job.get("status") == "done" and "hold" in kinds and "settle" in kinds and after == before - settled
            elif outcome == "failure":
                ok = "hold" in kinds and "release" in kinds and released == held and after == before
            else:
                # the provider made it (settled); the words must not say nothing was charged
                ok = "settle" in kinds and after == before - settled and "nothing was charged" not in said.lower()
                if "nothing was charged" in said.lower() and after < before:
                    extra = f"; charged {before - after} but told 'Nothing was charged'"
            record("ledger", "POST", f"/api/talking-photo/voice/run (ElevenLabs on fal, {outcome})", job.get("status"),
                   ok, why=f"quoted {qj.get('credits')}, held {held}, entries {kinds}, balance {before}->{after}{extra}",
                   excerpt=said[:200])
        BAD_AUDIO["on"] = False
        # ---- 4b. an effect run on ANOTHER account's render (B's gen id, A's credits) ----
        fake = FakeFal(media="image")
        fal._request = fake
        before, n_before, blocked_before = balance(acct), len(entries_for(acct)), len(BLOCKED)
        body = {"effect": "nano-banana-edit", "sources": [ctx["B"]["gen_handle"]], "prompt": "make it blue"}
        qr = call(client, "POST", "/api/effects/quote", A, json=body)
        r = call(client, "POST", "/api/effects/run", A, json={**body, "expect_credits": (qr.json() if qr.status_code == 200 else {}).get("credits")})
        job = wait_job(client, A, r.json().get("job_id")) if r.status_code == 200 and r.json().get("job_id") else {}
        new = entries_for(acct)[n_before:]
        submitted = [u for u in fake.calls if "/requests/" not in u]
        ok = (r.status_code in (400, 403, 404) or job.get("status") in ("failed", "error")) and not new and not submitted
        record("tenancy_body", "POST", "/api/effects/run (B's render as the source)", r.status_code if not job else job.get("status"),
               ok if r.status_code < 500 else False,
               expect="refused before any hold or provider call",
               why=(("refused inside the job (no hold, no provider call), not at the door" if job else "") if ok else
                    f"entries {[e['kind'] for e in new]}, provider submits {len(submitted)}, "
                    f"blocked {len(BLOCKED) - blocked_before}, balance {before}->{balance(acct)}"),
               excerpt=excerpt_of(r) + (" | job: " + str(job.get("error") or job.get("detail") or "")[:120] if job else ""))
        # ---- 5. price moved: expect_credits off by one -> refused, nothing held ----
        before = balance(acct)
        n_before = len(entries_for(acct))
        r = call(client, "POST", "/api/direct/image/run", A,
                 data={"prompt": "a red cup", "model": model_menu.NANO_ID, "aspect": "1:1", "expect_credits": "1"})
        new = entries_for(acct)[n_before:]
        ok = r.status_code == 409 and not new and balance(acct) == before
        record("ledger", "POST", "/api/direct/image/run (expect_credits not the price)", r.status_code, ok,
               expect="409, no hold", excerpt=excerpt_of(r))
        # ---- 6. the ledger reconciles ----
        bad = [x for x in ledger.reconcile(acct, dsn=DSN) if x.get("drift") or x.get("orphan")]
        record("ledger", "-", "ledger.reconcile(A) after the runs", len(bad), not bad,
               expect="no discrepancies", excerpt=json.dumps(bad)[:200])
        out = ledger.outstanding(acct, dsn=DSN)
        record("ledger", "-", "holds left open on A", out, out == 0, expect="0")
    finally:
        (fal._credential, fal._request, fal._download, fal.POLL_SECONDS,
         nano_banana.has_key, nano_banana._client, nano_banana._generate_content) = saved


def jobs_pass(client, ctx):
    print("pass: jobs and SSE")
    A, B = ctx["A"], ctx["B"]
    r = call(client, "GET", "/api/jobs", A)
    ids = [j.get("id") for j in (r.json().get("items") or [])] if r.status_code == 200 else []
    record("jobs", "GET", "/api/jobs", r.status_code, r.status_code == 200 and B["job_id"] not in ids,
           expect="200, only A's jobs", why="B's job listed" if B["job_id"] in ids else "",
           excerpt=f"ids {ids[:10]}")
    for method, path in (("GET", f"/api/jobs/{B['job_id']}"), ("POST", f"/api/jobs/{B['job_id']}/cancel"),
                         ("DELETE", f"/api/jobs/{B['job_id']}")):
        r = call(client, method, path, A)
        record("jobs", method, path + " (B's job)", r.status_code, r.status_code in (403, 404), expect="404",
               excerpt=excerpt_of(r))
    # a job that runs to its end on its own (a free one: a still of the kit's end card is not a job,
    # so use the registry directly through a route that starts one with nothing to spend: assets backfill)
    r = call(client, "POST", "/api/assets/backfill", A, json={"describe": False})
    if r.status_code == 200 and r.json().get("job_id"):
        job = wait_job(client, A, r.json()["job_id"])
        record("jobs", "POST", "/api/assets/backfill -> /api/jobs/{id}", job.get("status"),
               job.get("status") in ("done",), expect="done", excerpt=json.dumps(job)[:200])
    else:
        record("jobs", "POST", "/api/assets/backfill", r.status_code, None, why="no job to follow",
               excerpt=excerpt_of(r))
    if ARGS.no_server:
        return
    # SSE on a real server: TestClient waits for a whole body, and this one never ends
    import httpx
    import uvicorn
    config = uvicorn.Config(FA, host="127.0.0.1", port=ARGS.port, log_level="warning", lifespan="off",
                            timeout_graceful_shutdown=3)
    server = uvicorn.Server(config)
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    t0 = time.time()
    while not server.started and time.time() - t0 < 15:
        time.sleep(0.1)
    base = f"http://127.0.0.1:{ARGS.port}"
    try:
        subs_before = len(jobs._subscribers)
        mine = jobs.create("render", "A's SSE probe", account_id=A["account"])
        jobs.create("render", "B's private SSE probe", account_id=B["account"])
        events, seen_ids = [], []
        t1 = time.time()
        status, ctype = None, ""
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, read=2.0)) as hc:
                with hc.stream("GET", base + "/api/jobs/stream",
                               headers={"Cookie": f"phantra_session={A['cookie']}"}) as resp:
                    status = resp.status_code
                    ctype = resp.headers.get("content-type", "")
                    for line in resp.iter_lines():
                        if line.startswith("event:"):
                            events.append(line.split(":", 1)[1].strip())
                        if line.startswith("data:") and events and events[-1] == "job":
                            data = json.loads(line[5:])
                            seen_ids.append(data.get("id"))
                            if data.get("account_id") not in (A["account"], None) or "B's private" in line:
                                events.append("LEAK")
                        if mine["id"] in seen_ids or time.time() - t1 > 5:
                            break
        except httpx.ReadTimeout:
            pass   # the stream is idle until its 25 s keep-alive: the end of what we wanted
        first_event_s = round(time.time() - t1, 2)
        record("sse", "GET", "/api/jobs/stream", status,
               status == 200 and "text/event-stream" in ctype and "hello" in events and "LEAK" not in events
               and mine["id"] in seen_ids,
               expect="200 text/event-stream, hello, A's new job, nothing of B's",
               excerpt=f"events {events[:8]} job ids {seen_ids[:10]} in {first_event_s}s")
        t2 = time.time()
        while len(jobs._subscribers) > subs_before and time.time() - t2 < 30:
            time.sleep(0.2)
        record("sse", "-", "subscriber released after the client hung up", len(jobs._subscribers) - subs_before,
               len(jobs._subscribers) == subs_before, expect="0 left",
               why=f"released in {round(time.time() - t2, 1)}s")
        with httpx.Client(timeout=5) as hc:
            r = hc.get(base + "/api/jobs/stream")
        record("sse", "GET", "/api/jobs/stream (no session)", r.status_code, r.status_code == 401, expect="401",
               excerpt=r.text[:120])
    finally:
        server.should_exit = True
        th.join(timeout=10)


def stripe_pass(client, ctx):
    print("pass: Stripe webhook")
    A = ctx["A"]
    before = balance(A["account"])
    lots_before = len(ledger.lots(A["account"], dsn=DSN))
    payload = json.dumps({"id": "evt_qa", "type": "invoice.paid", "data": {"object": {
        "customer": "cus_qa", "subscription": "sub_qa", "billing_reason": "subscription_create",
        "lines": {"data": []}}}}).encode()
    for label, headers in (("no signature", {}),
                           ("bad signature", {"Stripe-Signature": "t=1,v1=deadbeef"}),
                           ("signed with another secret", {"Stripe-Signature": _stripe_sig(payload, "whsec_other")}),
                           ("valid signature, stale timestamp", {"Stripe-Signature": _stripe_sig(payload, os.environ["STRIPE_WEBHOOK_SECRET"], ts=1)})):
        r = call(client, "POST", "/billing/webhook", None, content=payload,
                 headers={"Content-Type": "application/json", **headers})
        ok = 400 <= r.status_code < 500
        record("stripe", "POST", f"/billing/webhook ({label})", r.status_code, ok, expect="4xx, no grant",
               excerpt=excerpt_of(r))
    after = balance(A["account"])
    lots_after = len(ledger.lots(A["account"], dsn=DSN))
    record("stripe", "-", "no grant from the refused webhooks", f"{before}->{after}, lots {lots_before}->{lots_after}",
           before == after and lots_before == lots_after, expect="unchanged")
    r = call(client, "POST", "/api/billing/checkout", A, json={"item": "starter"})
    record("stripe", "POST", "/api/billing/checkout (Stripe unconfigured)", r.status_code,
           (r.status_code < 400) or (400 <= r.status_code < 500 and readable(r)) or degraded(r),
           expect="readable 4xx/503, never 500",
           excerpt=excerpt_of(r))


def _stripe_sig(payload: bytes, secret: str, ts=None) -> str:
    import hmac
    ts = int(ts if ts is not None else time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def mcp_pass(client, ctx):
    print("pass: MCP mount")
    for path, headers in (("/mcp", {}), ("/mcp/claude", {}),
                          ("/mcp", {"Authorization": "Bearer not-the-token"})):
        r = call(client, "POST", path, None, headers={"Content-Type": "application/json",
                                                      "Accept": "application/json, text/event-stream", **headers},
                 content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode())
        record("mcp", "POST", f"{path} ({'no auth' if not headers else 'wrong bearer'})", r.status_code,
               r.status_code in (401, 403), expect="401", excerpt=excerpt_of(r))


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def shared_tables_pass(client, ctx):
    """The SHARED eval golden set (db.SHARED_TABLES: eval_golden): B's row, A's hands.
    Any signed-in customer reaching it is the finding; the handlers declare only
    current_account_id."""
    print("pass: shared tables (eval golden set)")
    from src import evalstore
    A = ctx["A"]
    gid = evalstore.add_golden("qa golden written by the operator", ["qa-doc"], source="qa")
    r = call(client, "GET", "/api/evals/golden", A)
    seen = r.status_code == 200 and any(i.get("id") == gid for i in (r.json().get("items") or []))
    record("shared", "GET", "/api/evals/golden (as a customer)", r.status_code, not seen,
           expect="403 (operator only)", why="a customer lists the shared golden set" if seen else "",
           excerpt=excerpt_of(r))
    r = call(client, "POST", "/api/evals/golden", A, json={"query": "qa customer row", "relevant": ["x"]})
    added = r.status_code < 300
    record("shared", "POST", "/api/evals/golden (as a customer)", r.status_code, not added,
           expect="403 (operator only)", why="a customer writes the shared golden set" if added else "",
           excerpt=excerpt_of(r))
    n_before = len(evalstore.list_golden())
    r = call(client, "DELETE", f"/api/evals/golden/{gid}", A)
    n_after = len(evalstore.list_golden())
    gone = n_after < n_before
    record("shared", "DELETE", "/api/evals/golden/{golden_id} (another party's row)", f"{r.status_code}, rows {n_before}->{n_after}",
           not gone, expect="403 (operator only)", why="a customer deleted a shared golden row" if gone else "",
           excerpt=excerpt_of(r))


# failures already written up in 03-backend-e2e.md: (phase, route regex) -> finding id
KNOWN_RULES = [
    ("csrf", r"^/api/direct/image/run", "E1"),
    ("csrf", r"^/api/assets/generated/\d+/share", "E1"),
    ("shared", r"^/api/evals/golden", "E2"),
    ("tenancy_body", r"^/api/concepts/\d+/(refs|shots/\d+/refs)$", "E3"),
    ("tenancy_body", r"^A's scene after the ref writes", "E3"),
    ("tenancy", r"^/api/assets/generated/\{asset_id\}/share$", "E4"),
    ("ledger", r"^/api/talking-photo/voice/run \(ElevenLabs on fal, made, then filing fails\)", "E5"),
    ("seed", r"^/api/assets/locations \(describe fails\)", "E6"),
]


class _Known(dict):
    def get(self, key, default=None):
        phase, route = key
        for ph, rx, fid in KNOWN_RULES:
            if ph == phase and re.search(rx, route or ""):
                return fid
        return default

    def __contains__(self, key):
        return self.get(key) is not None


KNOWN = _Known()


def report(started, routes):
    unexpected = [r for r in RESULTS if r["ok"] is False and (r["phase"], r["route"]) not in KNOWN]
    by_phase: dict = {}
    for r in RESULTS:
        d = by_phase.setdefault(r["phase"], {"pass": 0, "fail": 0, "note": 0})
        d["pass" if r["ok"] else "fail" if r["ok"] is False else "note"] += 1
    classes: dict = {}
    for row in routes:
        classes[row["class"]] = classes.get(row["class"], 0) + 1
    print("\n== routes:", len(routes), classes)
    print("== results by phase")
    for ph, d in by_phase.items():
        print(f"   {ph:13s} pass {d['pass']:4d}  fail {d['fail']:3d}  note/skip {d['note']:4d}")
    print("== failures")
    for r in RESULTS:
        if r["ok"] is False:
            tag = KNOWN.get((r["phase"], r["route"]), "NEW")
            print(f"   [{tag}] {r['phase']:11s} {r['method']:6s} {r['path'][:90]:90s} {r['status']} {r['why'][:80]}")
    print(f"== {len(unexpected)} unexpected failure(s); network attempts blocked: {len(BLOCKED)}; "
          f"{round(time.time() - started)}s")
    if ARGS.json:
        Path(ARGS.json).write_text(json.dumps({
            "routes": [{k: v for k, v in r.items() if k != "source"} for r in routes],
            "results": RESULTS, "blocked": BLOCKED}, indent=1, default=str))
    return unexpected


if __name__ == "__main__":
    code = 1
    try:
        main()
        code = 1 if [r for r in RESULTS if r["ok"] is False and (r["phase"], r["route"]) not in KNOWN] else 0
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        code = 2
    finally:
        drop_schema()
    sys.exit(code)
