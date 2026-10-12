"""
The web app: reads the same database the pipeline writes to. No build
step, no framework, no component library -- vanilla Jinja2 and CSS.

/ui (behind sign-in) is the product; / is the public landing and the
only indexed URL. /studio is the Dev Studio -- one dev-only page of
tabs (Stats, Grade, RAG Library, Settings, Dataset) that is strictly
stats and system improvement: what happens there (grading, RAG
teaching, threshold tuning) changes what the next real generation on
/ui does, and none of it is shown to end users.
"""
import csv
import io
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlencode

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from starlette.middleware.sessions import SessionMiddleware

from src import accounts as accounts_mod
from src import (
    asset_shelf,
    assistant_store,
    autonomy,
    autopilot,
    db,
    entities,
    evalstore,
    fal_requests,
    generative,
    inspiration,
    instagram,
    ledger,
    locations,
    manual_lane,
    mcp_connections,
    mcp_feedback,
    mcp_preferences,
    mcp_recipes,
    outcomes,
    preprod,
    publish_review,
    quote_redemptions,
    rag,
    render_assets,
    shootgen,
    spend,
    upload_links,
    winners,
    workflows,
    youtube,
)
from src import billing as billing_core
from src import (
    settings as settings_mod,
)
from src.cut import moments as cut_moments
from src.cut import store as cut_store

from . import api, auth, jobs, mcp_auth, mcp_mount, oauth_consent, seo, upload_page
from . import billing as billing_routes
from .sparkline import render_sparkline

load_dotenv()

# Deployment posture. DEV_TOOLS=1 (the local .env) is the dev machine:
# the legacy dev-console pages -- /studio and every per-stage screen --
# register on top of /ui. Unset is a public deployment: those routes are
# never registered at all, so /studio 404s the same as any undefined
# path rather than being a page someone could find by guessing the URL.
# Read once at startup; /api/capabilities reports the same flag live so
# /ui can hide its "legacy" link (data-cap="dev_tools").
DEV_TOOLS = os.environ.get("DEV_TOOLS") == "1"

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
LOCATIONS_DIR = PROJECT_ROOT / "locations"
CHARACTERS_DIR = PROJECT_ROOT / "characters"
PROPS_DIR = PROJECT_ROOT / "props"
THUMB_DIR = PROJECT_ROOT / "data" / "thumbs"
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


def clean_title(title: str) -> str:
    """
    Display form of a video title: the stored title is whatever YouTube
    has, hashtags and all; on screen the tags are noise. A title that is
    nothing but hashtags keeps its raw form rather than going blank.
    """
    stripped = re.sub(r"#\S+", "", title or "").strip()
    stripped = re.sub(r"\s{2,}", " ", stripped)
    return stripped if stripped else title


templates.env.filters["clean_title"] = clean_title

# --- Brands: two separate concepts, one switchable "active brand" ----------
# ANTIHERO = Michael's personal brand (he is the star); Zero Page = the viral
# auto-posting engine (product/trend is the star). They must never blur, so
# the active brand rides a cookie: it drives generation, filters which
# channel's holds and which brand's analytics you see, and shows a distinct
# label + accent everywhere.
BRANDS = tuple(preprod.BRANDS)
DEFAULT_BRAND = "antihero"
BRAND_META = {
    "antihero": {"label": "ANTIHERO", "accent": "#d64550",
                 "note": "personal brand — Michael is the star"},
    "zeropage": {"label": "Zero Page Films", "accent": "#8b5cf6",
                 "note": "viral engine — the product / trend is the star"},
}


def active_brand(request: Request) -> str:
    """The brand the studio is currently 'in', from the cookie. Validated
    against the real brand set, defaulting to ANTIHERO."""
    brand = request.cookies.get("brand", DEFAULT_BRAND)
    return brand if brand in BRANDS else DEFAULT_BRAND


# Jinja globals so the switcher + accent render on every page without
# threading the brand through each route's context.
templates.env.globals["active_brand"] = active_brand
templates.env.globals["BRAND_META"] = BRAND_META
templates.env.globals["BRANDS"] = BRANDS

# "Posted in the last" control -> posted_within_days. "all" -> no cutoff.
POSTED_WINDOWS = {"3": 90, "6": 180, "12": 365, "all": None}


# The note the startup seed wrote on the gold-standard winner until
# 2026-10-02 -- see retire_gold_standard.
GOLD_STANDARD_NOTE = "gold standard structural exemplar"


def retire_gold_standard():
    """Keep the gold-standard exemplar OFF the winners shelf (2026-10-02,
    Mike's call). Until then startup recorded prompts/gold_standard.md as a
    "worked" winner so the RAG loop would reinforce it -- the monster/portal
    dark comedy, i.e. the house style, retrieved as a taught reference into
    look-less runs. It was never a rendered result, only the exemplar, and
    the exemplar already reaches every writer through {example}. The live
    row (#2, 4 chunks) was deleted by hand that day; this runs at boot
    because a process still on the old seed re-adds the row whenever none
    exists, so the first boot of this code clears whatever came back.
    Exact note only -- nothing a person wrote is touched. Never blocks
    startup."""
    try:
        winners.retire_by_note(GOLD_STANDARD_NOTE)
    except Exception:
        pass


# The MCP surface, built before the lifespan so its session manager is
# available to run. Off unless ZEROPAGE_MCP=1, and refused rather than
# served open when ZEROPAGE_MCP_TOKEN is unset -- see app/mcp_mount.py.
# jobs.start/jobs.get are injected because src/ never imports app/.
MCP_APP, MCP_SESSIONS = mcp_mount.build(
    dsn=None, start_job=jobs.start, job_status=jobs.get,
    # the priced approves, as callables: the MCP `approve` tool runs the
    # same bodies the Queue's buttons post to (2026-10-07)
    approve_render=api.approve_render, approve_keyframes=api.approve_keyframes,
    cancel_job=jobs.cancel,
    # ...and the Elements page's create body, for `add_element` (2026-10-11)
    create_element=api.create_element,
)


def init_tables() -> None:
    """Every table the app reads or writes, created if missing, and the
    two seeds that ride with them. Safe to run twice; the lifespan runs
    it through db.run_init."""
    db.init_db()
    preprod.init()
    entities.init()
    autonomy.init()
    winners.init()
    inspiration.init()   # seeds the researched accounts if empty
    evalstore.init()     # golden set seeded from eval_cases.json
    workflows.init()     # saved node graphs for /ui Workflows
    workflows.seed_default()  # "Prompt enhancement" starter canvas
    render_assets.init()  # generated_assets, owned (merged 2026-09-02)
    outcomes.init()       # output_events: what a person did with an output
    cut_store.init()      # timelines / timeline_heads / cut_media (Assemble v0)
    cut_moments.init()    # media_index / media_moments (the index, phase 2)
    spend.init()          # llm_calls, the LLM meter (2026-09-04)
    ledger.init()         # credit_lots / credit_entries, the prepaid ledger
    billing_core.init()   # credit_schedules, a yearly plan's unreleased months
    generative.init()    # generations log the render caps count
    accounts_mod.init()  # users / identities / accounts / members
    settings_mod.init()  # the Dev Studio tunables (gate/threshold/k)
    fal_requests.init()  # fal's queue receipts, persisted at submit
    assistant_store.init()  # the pill's persona, project and Keep clicks
    mcp_connections.init()  # who connected Claude, for the account menus' panel
    quote_redemptions.init()  # which studio quotes the MCP has spent
    publish_review.init()   # posts the person reviews and sends (prepare_post)
    upload_links.init()     # the connector's one-time upload links, spent once
    mcp_feedback.init()     # notes a person leaves through the connector
    mcp_preferences.init()  # a workspace's connector defaults (newest row wins)
    mcp_recipes.init()      # a creator's own recipes, every save a version


@asynccontextmanager
async def lifespan(app: FastAPI):
    with db.connection_pool():
        # One start at a time (2026-10-10): two of these inits side by
        # side deadlock in Postgres, and the stdio MCP server runs nine of
        # the same ones against this database whenever Claude Desktop
        # starts. db.run_init takes the lock that server takes, and runs
        # the block again if it is still picked as a deadlock's victim.
        db.run_init(init_tables)
        # A deploy restarts this process mid-render and app/jobs.py's
        # threads die with it (2026-09-26: #121 and #135 orphaned). The
        # sweep reattaches to any fal job whose worker stopped beating and
        # finishes it -- settle and attach, or release with fal's reason.
        # Off with FAL_RECOVER=0.
        if os.environ.get("FAL_RECOVER", "1") != "0":
            fal_requests.start_background()
        retire_gold_standard()              # the exemplar is not a winner (2026-10-02)
        # The MCP transport is not self-starting: its session manager has
        # to be entered by whoever hosts it. A no-op when MCP is off.
        async with mcp_mount.session_lifespan(MCP_SESSIONS):
            yield


class NoCacheStaticFiles(StaticFiles):
    """Static assets revalidate on every load (ETag round-trip, cheap on
    localhost). Without a Cache-Control header the browser applies
    heuristic freshness and serves stale JS modules for minutes after an
    edit -- on a single-operator dev tool, correctness beats the saved
    round-trip."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def r2_fallback(key: str):
    """A redirect to the same file in R2, or None.

    Registered behind every route that serves a reference photo off
    local disk. characters/, props/, locations/ and data/refs/ are
    gitignored and dockerignored, and data/ on Fly is a fresh volume --
    so on the deployed site NONE of these files exist and every
    reference tile came back 404 (2026-09-08, Mike: "the reference
    photos aren't appearing"). New rows now store the canonical R2 URL
    outright; this covers the rest -- every row written before today,
    every /ui gallery, and any hand-typed path -- with a 302 rather than
    a second copy of the serving logic.
    """
    from src import storage

    url = storage.url_for_key(key)
    return RedirectResponse(url, status_code=302) if url else None


app = FastAPI(lifespan=lifespan)

# CORS: only needed once the frontend is on a different origin than this
# API (e.g. a Vercel-hosted refine app calling the Fly-hosted API). Same-
# origin deployments (frontend served from this app) don't need this at
# all, but it's harmless to leave on. Origins come from FRONTEND_ORIGINS
# in .env, comma-separated, no trailing slashes -- empty by default so
# nothing cross-site is allowed until you set it.
_frontend_origins = [
    o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()
]
if _frontend_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Starlette session middleware: used ONLY for the OAuth state/nonce dance
# (Authlib stores its CSRF state here). The login session itself is the
# separate signed zp_session cookie in app/auth.py.
app.add_middleware(SessionMiddleware, secret_key=auth._session_secret(),
                   same_site="lax", https_only=False)
# Cross-origin access for a separate frontend (the Next.js app). Its
# fetches are credentialed (the zp_session cookie), so the allow-list must
# be explicit origins -- a wildcard is illegal with credentials -- and
# allow_credentials must be on. FRONTEND_ORIGIN_REGEX adds dynamic hosts an
# explicit list can't enumerate (per-deploy Vercel preview URLs). Neither
# set => no cross-origin frontend registered, i.e. the API's own /ui only,
# exactly as before.
_frontend_origins = auth.frontend_origins()
_frontend_origin_regex = auth.frontend_origin_regex()
if _frontend_origins or _frontend_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_frontend_origins,
        allow_origin_regex=_frontend_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.mount("/static", NoCacheStaticFiles(directory=str(APP_DIR / "static")), name="static")
# Rendered clips (data/renders/, gitignored with the rest of data/) --
# what the scene board plays when no public R2 URL exists yet.
RENDERS_DIR = PROJECT_ROOT / "data" / "renders"
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/renders", NoCacheStaticFiles(directory=str(RENDERS_DIR)), name="renders")
# Composer reference uploads (data/refs/) -- a photo dragged onto the
# Studio composer needs a URL to ride on, or it can ground the writing
# call and nothing after it.
UPLOAD_REFS_DIR = PROJECT_ROOT / "data" / "refs"
UPLOAD_REFS_DIR.mkdir(parents=True, exist_ok=True)
class RefsStaticFiles(NoCacheStaticFiles):
    """The bin, with R2 behind it. A composer upload or a scouted image
    saved on one machine is not on the next one's disk; the bytes were
    mirrored up at save time (refbin.mirror_to_r2), so a miss here is a
    redirect rather than a broken tile."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 404 and "/" not in path and path not in (".", ".."):
            redirect = r2_fallback(f"refs/{path}")
            if redirect is not None:
                return redirect
        return response


app.mount("/refs", RefsStaticFiles(directory=str(UPLOAD_REFS_DIR)), name="refs")
# Every /api route now requires a session -- the /ui shell is gated, so
# its backing endpoints are too (401 JSON, which shared.js surfaces as a
# stateline). The legacy /studio pages stay open as the dev console.
# The MCP endpoint carries its own bearer auth (mcp_mount.guarded), not
# the zp_session cookie: the callers are agents holding a token, not
# browsers holding a login. Mounted only when build() returned an app.
if MCP_APP is not None:
    app.mount(mcp_mount.MOUNT_PATH, MCP_APP, name="mcp")

    # The OAuth discovery document (RFC 9728), and the reason it is
    # registered HERE rather than on the mount: a client reads it BEFORE
    # it has a token, so it cannot live behind the bearer guard -- and it
    # must not exist at all on a deployment with no MCP surface, which is
    # the `dev` router's omission-not-a-second-check rule. Both paths are
    # served: the spec puts the resource's path after the well-known
    # segment, and clients in the wild still ask for the bare one.
    @app.get(mcp_auth.METADATA_PATH)
    @app.get(f"{mcp_auth.METADATA_PATH}{mcp_mount.MOUNT_PATH}")
    def oauth_protected_resource():
        return JSONResponse(mcp_auth.protected_resource_metadata())

    # The Claude directory's listing is its own resource (/mcp/claude).
    @app.get(f"{mcp_auth.METADATA_PATH}{mcp_mount.MOUNT_PATH}{mcp_mount.CLAUDE_PATH}")
    def oauth_protected_resource_claude():
        return JSONResponse(mcp_auth.protected_resource_metadata(mcp_auth.CLAUDE_SUFFIX))
app.include_router(api.router, dependencies=[Depends(auth.require_user_api)])
app.include_router(auth.router)
# the OAuth consent step Supabase's OAuth server sends a connector's user to
app.include_router(oauth_consent.router)
# the connector's one-time upload page (/u/<token>): the token is the auth
app.include_router(upload_page.router)
# Stripe's webhook: outside /api, because Stripe cannot sign in -- its
# authentication is the signature over the raw body (app/billing.py)
app.include_router(billing_routes.webhook)


def signin_showcase() -> list[dict]:
    """The sign-in page's left panel: a few clips, one after another, each
    with a label under its progress bar (Higgsfield's shape).
    `SIGNIN_SHOWCASE` is a JSON list of {"label", "video"|"image",
    "poster"?}; unset or unreadable falls back to SIGNIN_SHOWCASE_DEFAULT,
    and an empty list shows the gradient panel alone. Only http(s) and
    site-relative sources are kept."""
    import json
    raw = os.environ.get("SIGNIN_SHOWCASE")
    try:
        items = json.loads(raw) if raw else SIGNIN_SHOWCASE_DEFAULT
    except ValueError:
        items = SIGNIN_SHOWCASE_DEFAULT
    ok = lambda u: isinstance(u, str) and (u.startswith(("https://", "http://", "/")))  # noqa: E731
    out = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        src = {k: item[k] for k in ("video", "image", "poster") if ok(item.get(k))}
        if src.get("video") or src.get("image"):
            out.append({"label": str(item.get("label") or "")[:40], **src})
    return out[:5]


# Real studio output, the same R2 keyframes the landing page shows
# (web/src/content/landing-media.ts), under the landing hero's four steps
# (hero-media.ts HERO_STEPS) -- so the door looks like the site the person
# just left, and never shows stock or a mock-up.
# They live under account 1's tenant prefix (`m/1/...`, the 2026-09-15
# media migration); the flat `renders/nano/...` keys this pointed at are
# gone from the bucket and 404'd on this page until 2026-10-07. Absolute
# keys rather than media.url_for, so the door does not depend on which
# rung of ZEROPAGE_MEDIA the serving machine is on.
#
# 2026-10-07 (Mike's pick off a contact sheet): two product ads first, then
# two cinematic keyframes, so the door shows both kinds of work the studio
# makes and opens on something bright rather than the creature. The ads are
# the made-up products on the /make page's wall (SOLÈNE perfume, KUMO
# matcha), served from the public site -- never the four real-brand stills
# on that wall, which on a sign-in page would read as endorsements.
_R2_NANO = "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/1/renders/nano"
_ADS = "https://zeropage.studio/make/ai-product-ad-generator"
SIGNIN_SHOWCASE_DEFAULT: list[dict] = [
    {"label": "Bring a spark", "image": f"{_ADS}/fragrance.jpg"},
    {"label": "Write the scene", "image": f"{_ADS}/matcha.jpg"},
    {"label": "Pick the frame", "image": f"{_R2_NANO}/c361-20260911-161358.png"},
    {"label": "Render the clip", "image": f"{_R2_NANO}/c348-20260908-073120.png"},
]


def _site_origin(url: Optional[str]) -> Optional[str]:
    """scheme://host of a URL, or None."""
    from urllib.parse import urlsplit
    if not url:
        return None
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


@app.get("/signin")
def signin(request: Request, error: Optional[str] = None,
           mode: Optional[str] = None, email: Optional[str] = None,
           next: Optional[str] = None, step: Optional[str] = None,
           open: Optional[str] = None, notice: Optional[str] = None):
    """The one door (2026-09-24, InVideo's shape): Google / Discord /
    Apple, or an email that gets a one-time code. Logging in and signing
    up are the same form -- `mode=signup` only changes the heading -- and
    `step=code` is the second screen of the email door. Email+password
    survives behind "Use a password instead". Already signed in ->
    straight to the shell.

    `next` lets a trusted external frontend (FRONTEND_ORIGINS) ask to be
    returned to itself after sign-in: stashed in the starlette session so
    it survives both the email/password POST and the OAuth round-trip, and
    validated against frontend_origins in auth._post_login_redirect -- so
    it is never an open redirect."""
    if next:
        request.session["post_login_redirect"] = next
    # A sign-in FOR an OAuth consent needs a fresh Supabase session even
    # when our own cookie is good (app/oauth_consent.py), so it skips the
    # already-signed-in shortcut and the page says why it is asking.
    consenting = oauth_consent.pending(request) is not None
    user = auth.current_user(request)
    if user and not consenting:
        # somebody who signed in while the door was invite-only has a
        # session and no workspace; walking through it now makes one
        auth._provision(user["id"], user.get("email"), user.get("display_name"))
        # already signed in HERE; a trusted front end still needs the
        # session on its own origin (auth.handoff_redirect says why)
        destination = auth._post_login_redirect(request)
        if destination:
            return auth.handoff_redirect(destination, user["id"])
        return (auth.studio_handoff(user["id"])
                or RedirectResponse("/ui", status_code=303))
    # the second screens: `code` (a sign-in code was sent), `reset` (a
    # recovery code was sent -- code + new password), `newpassword` (the
    # recovery LINK was clicked -- the new password alone; the session
    # cookie holds the proof, so no email is needed on the page)
    if step == "newpassword":
        screen = "newpassword"
    elif step in ("code", "reset") and email:
        screen = step
    else:
        screen = "start"
    return templates.TemplateResponse(
        request, "signin.html",
        {"error": error, "mode": mode if mode in ("signin", "signup") else "signin",
         "email": email, "step": screen, "consenting": consenting,
         # the code step's own line, when the door that sent the code has
         # something to say about it (a sign-up: the code confirms the address)
         "notice": notice if screen == "code" else None,
         # the terms and privacy pages live on the public site (web/), the
         # origin STUDIO_URL names; no front end, no legal line
         "site_url": _site_origin(auth.studio_url()),
         "open": open if open in auth.OPEN_STEPS else None,
         # the promo row ("Sign up & get N free credits") shows only when a
         # welcome grant is actually configured -- never a promise the
         # ledger does not keep
         "signup_credits": accounts_mod.signup_credits() if accounts_mod.open_signup() else 0,
         "showcase": signin_showcase(),
         # live key presence, the /api/capabilities rule applied to the
         # modal: a provider button only renders when it can actually work
         "providers": auth.providers_available()})


@app.get("/ui/accounts")
def ui_accounts(request: Request):
    """The account picker -- or, for a signed-in user with no
    account_members row, the explicit no-access state. Membership is
    granted by members, never by signing up (the gate)."""
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    auth._provision(user["id"], user.get("email"), user.get("display_name"))
    member_of = accounts_mod.memberships(user["id"])
    return templates.TemplateResponse(
        request, "accounts.html", {"user": user, "member_of": member_of})


@app.get("/ui")
def ui(request: Request):
    """
    The ported ZPF Studio skin (prototype/studio.html made real): one
    shell, client-side views, every control backed by /api and gated by
    /api/capabilities. Requires a session; the active brand comes from
    real membership (current_account), not the raw cookie.

    One block of the page is decided HERE rather than by a data-cap
    attribute: the Queue's manual-lane section. `data-cap` hides markup
    that was still served, and this lane is operator-only for a reason
    that is not cosmetic (src/manual_lane.py) -- so a non-operator's page
    does not contain the section at all. The flag is read from the
    account's own row, server-side, and the lane's routes re-ask the same
    gate anyway; nothing here is what protects it.
    """
    # The React studio is the studio when this deployment has one
    # (STUDIO_URL): a /ui address -- an old bookmark, the landing page,
    # a sign-in with no return address -- lands there, session in hand,
    # with its ?view= translated. ?legacy=1 keeps this shell reachable as
    # the reference implementation the React one was ported from.
    studio = auth.studio_url()
    legacy = request.query_params.get("legacy") == "1"
    user = auth.current_user(request)
    if user is None:
        if studio and not legacy:
            target = f"{studio}{auth.studio_path_for_ui(request)}"
            return RedirectResponse(f"/signin?{urlencode({'next': target})}",
                                    status_code=303)
        return RedirectResponse("/signin", status_code=303)
    if studio and not legacy:
        handoff = auth.studio_handoff(user["id"], auth.studio_path_for_ui(request))
        if handoff is not None:
            return handoff
    account = auth.current_account(request, user)
    if account is None:
        # signed in, zero memberships: the no-access state, never a
        # silent grant into the real accounts
        return RedirectResponse("/ui/accounts", status_code=303)
    # the TENANT, not the brand -- the lane is a property of the account
    # that owns the rows, the same id every /api route acts as
    return templates.TemplateResponse(
        request, "zpf.html",
        {"brand": account["slug"], "user": user,
         "director_url": os.environ.get("DIRECTOR_FRONTEND_URL", "").rstrip("/") or (
             f"http://{request.url.hostname}:3000/studio/flows"
             if request.url.hostname in ("localhost", "127.0.0.1") else ""),
         "manual_lane": manual_lane.manual_lane_allowed(
             auth.optional_account_id(request))})


def benchmark_class(score, median) -> str:
    """
    "above median" / "below median" per BUILD_SPEC's Design Direction --
    neutral (no class) when either value is missing or they're equal,
    so a lone video isn't coloured against itself.
    """
    if score is None or median is None:
        return ""
    if score > median:
        return "good"
    if score < median:
        return "bad"
    return ""


def performance_rows(at_days: int = 7, posted_within: str = "6",
                     account_id: Optional[int] = None) -> dict:
    """
    The feedback loop: what's performing, compared at equal age. The
    benchmark uses the same window as the ranking or the colouring
    lies -- an all-time median would make an average recent video look
    good against the long tail, or bad against one old outlier. The
    current skin doesn't render the strip, but the discipline is pinned
    by tests here so a future skin inherits it rather than reinventing
    it wrong.
    """
    posted_within_days = POSTED_WINDOWS.get(posted_within, 180)
    top = db.get_top_performers(
        at_days=at_days, posted_within_days=posted_within_days, limit=5,
    
        account_id=account_id,)
    bench = db.benchmark(
        at_days=at_days, posted_within_days=posted_within_days,
    
        account_id=account_id,)
    rows = []
    for t in top:
        history = db.get_video_history(t["video_id"], account_id=account_id)
        rows.append({
            **t,
            "sparkline": render_sparkline(history),
            "css_class": benchmark_class(t["score"], bench["median"]),
        })
    return {"rows": rows, "at_days": at_days}


@app.get("/")
def landing(request: Request):
    """
    The marketing front door and the only indexed page. A template rather
    than a static file purely so the canonical URL and the JSON-LD graph
    are built from SITE_URL -- hardcoding a domain into the markup is how
    a canonical tag ends up pointing at localhost in production. The
    workspace lives at /studio.
    """
    # The CTA points at whichever workspace exists on this deployment: the
    # React studio when there is one (STUDIO_URL), /studio on the dev
    # machine, /ui (behind sign-in) everywhere else -- a public front door
    # must not link into a 404.
    studio = auth.studio_url()
    return templates.TemplateResponse(
        request,
        "landing.html",
        {"site_url": seo.site_url(), "schema_json": seo.homepage_schema_json(),
         "studio_href": (f"{studio}/studio" if studio
                         else "/studio" if DEV_TOOLS else "/ui")},
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Fly liveness probe: startup already proves the database schemas init."""
    return {"ok": True}


@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy(request: Request):
    """Public legal page -- also doubles as the privacy-policy URL every
    OAuth app registration (Instagram, Pinterest, ...) needs on file. The
    studio site renders the same policy (web/src/app/privacy/page.tsx);
    a change to one is a change to both."""
    return templates.TemplateResponse(
        request, "privacy.html",
        {"site_url": seo.site_url(),
         # the pricing page lives on the studio site, the origin
         # STUDIO_URL names; without one the link stays on this origin
         "studio_site": _site_origin(auth.studio_url()) or seo.site_url()},
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    """Public page open to everyone including the AI crawlers; the app
    itself kept out of the index."""
    return seo.robots_txt()


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    """A markdown brief for language models: what the product is, what
    'grounded' means here, and the hard specs — the answer we'd want cited
    when someone asks an assistant about grounded pre-production."""
    return seo.llms_txt()


@app.get("/sitemap.xml")
def sitemap_xml():
    return Response(content=seo.sitemap_xml(), media_type="application/xml")


def _belongs_to(request: Request, slug: str) -> bool:
    """Is the signed-in person a member of the account with this slug?"""
    try:
        user = auth.current_user(request)
        return bool(user) and any(
            a["slug"] == slug for a in accounts_mod.memberships(user["id"]))
    except Exception:           # noqa: BLE001 -- an unreadable session is "no"
        return False


@app.post("/brand/{name}")
def set_brand(request: Request, name: str, next: str = Form("/studio")):
    """Flip the active brand. Persists in a cookie so generation and the
    holds / analytics views follow it until you switch back.

    The cookie is also what picks the active WORKSPACE (auth.current_account
    reads it as a preference among the accounts you belong to). Until
    2026-10-11 only the two brand names could be written to it, so the
    switch in the account menus and on Settings -> Workspace did nothing
    for any other workspace: asking for `mara-films` stored the default
    brand, which is nobody's workspace, and current_account then fell back
    to the caller's first membership -- whichever was clicked. A slug the
    signed-in person IS A MEMBER OF is accepted now. Anything else (a
    stranger's slug, a made-up one, no session) is still the default, and
    every reader of the cookie as a brand LABEL already falls back to the
    default for a name that is not one."""
    brand = name if name in BRANDS or _belongs_to(request, name) else DEFAULT_BRAND
    resp = RedirectResponse(safe_next(next, "/studio"), status_code=303)
    resp.set_cookie("brand", brand, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


# --- the dev console --------------------------------------------------------
# Every route from here to the end of the file registers on `dev`, not
# `app`: /studio and the per-stage screens are the operator's engine
# room, and they exist only in the dev posture (the conditional
# include_router at the bottom of the file). The rule is "anything that
# isn't /ui, /api, auth, or the public landing surface is dev-only" --
# a new legacy-style page belongs on this router, not on `app`.
dev = APIRouter()


@dev.get("/dashboard")
def dashboard():
    """
    Gone. The app is one page now: what the dashboard showed -- counts,
    pick rate, top performers at equal age -- lives on the studio canvas,
    where it sits next to the work that produced it instead of on a
    screen you had to remember to visit. Kept as a redirect because it
    was the app's front door for months and is in muscle memory.
    """
    return RedirectResponse("/studio", status_code=308)


# --- the Dev Studio ---------------------------------------------------------
# One page (this route), five tabs. Strictly stats and system
# improvement: the numbers about how well the pipeline works, a
# randomized grading queue, the RAG library, the tunables, and the
# eval dataset. Everything an end user creates with lives on /ui; what
# happens here only changes what /ui's next generation does.

# Grade and Teach went on 2026-10-11 (docs/tasks/task-higgsfield-shape.md
# step 5): nobody grades a concept any more. What a person does with an
# output is recorded as it happens (src/outcomes.py) and read on Stats.
DEV_TABS = ("stats", "library", "settings", "dataset")

# --- distribution: the number the Stats tab now leads with ------------------
# (2026-09-07) Every other figure on this page measures how well the
# machine THINKS. This one measures whether anything came out of it:
# posts per week per brand per platform, what each one cost, and what
# last night actually did. It leads because a pipeline that reasons
# beautifully and publishes nothing is a pipeline with a zero here, and
# no agreement percentage below would say so.
DISTRIBUTION_WEEKS = 4


def _week_starts(weeks: int = DISTRIBUTION_WEEKS) -> list:
    """The Monday of each of the last `weeks` weeks, oldest first. Weeks
    are Mondays rather than rolling 7-day windows so two page loads a day
    apart show the same buckets -- a chart whose columns move under you
    cannot be compared with yesterday's."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return [monday - timedelta(weeks=n) for n in range(weeks - 1, -1, -1)]


def _distribution(account_id: Optional[int], weeks: int = DISTRIBUTION_WEEKS) -> dict:
    """Posts per week per brand per platform, and cost per post --
    read-only, and every part of it degrades rather than 500s.

    Only PIPELINE posts count. `videos.legacy` marks the hand-made
    uploads that predate the loop (db.add_legacy_column), and counting
    them here would credit the machine with Mike's own back catalogue --
    so the query carries db.excludes_legacy's predicate, the same one
    the teaching readers use, rather than a second hand-rolled filter
    that could disagree with it.
    """
    starts = _week_starts(weeks)
    since = starts[0].isoformat()
    dist = {
        "weeks": [{"start": s.isoformat(), "label": s.strftime("%b %-d")} for s in starts],
        "rows": [], "posts": 0, "since": since,
        "spend_usd": 0.0, "cost_per_post": None,
        "available": True,
    }

    counts: dict = {}
    try:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT COALESCE(v.brand, '—') AS brand, v.platform, "
                "substr(v.posted_at, 1, 10) AS day FROM videos v "
                "WHERE v.account_id IS NOT DISTINCT FROM %s "
                "AND substr(v.posted_at, 1, 10) >= %s"
                + (" AND NOT v.legacy" if db.excludes_legacy(False) else ""),
                (account_id, since),
            ).fetchall()
            for r in rows:
                key = (r["brand"], r["platform"])
                bucket = counts.setdefault(key, [0] * weeks)
                for i, start in enumerate(starts):
                    end = start + timedelta(days=7)
                    if start.isoformat() <= r["day"] < end.isoformat():
                        bucket[i] += 1
                        break
    except Exception:
        dist["available"] = False
        return dist

    dist["rows"] = [
        {"brand": brand, "platform": platform, "counts": bucket,
         "total": sum(bucket)}
        for (brand, platform), bucket in sorted(counts.items())
    ]
    dist["posts"] = sum(r["total"] for r in dist["rows"])

    # What those posts cost: the LLM meter plus metered renders over the
    # same window. Both are estimates written at call time (src/costs.py's
    # honesty rules), and a render with no price was paid for by a
    # subscription -- it is missing from this sum rather than counted as
    # $0, which is the same call /costs makes.
    spent = 0.0
    try:
        spent += sum(float(s["cost_usd"] or 0)
                     for s in spend.by_stage(account_id=account_id, since=since))
    except Exception:
        pass
    try:
        with db.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM generations "
                "WHERE created_at >= %s AND account_id IS NOT DISTINCT FROM %s",
                (since, account_id),
            ).fetchone()
            spent += float(row[0] or 0)
    except Exception:
        pass
    dist["spend_usd"] = round(spent, 2)
    # Zero posts shows "—", never a division: "$18.40 per post" with no
    # posts is either a crash or a lie, and both are worse than a dash.
    dist["cost_per_post"] = round(spent / dist["posts"], 2) if dist["posts"] else None
    return dist


def _library_context(q: Optional[str], domain: Optional[str]) -> dict:
    """The RAG Library tab's data -- the old /library page's context
    unchanged: must render with Postgres down, search errors surface as
    a line, never a 500."""
    context = {"available": False, "sources": [], "results": [],
               "domains": [], "q": q, "domain": domain, "error": None}
    conn = None
    try:
        conn = rag.connect()
        context["sources"] = rag.list_sources(conn)
        # "assets" always offered even before the first asset lands on
        # the shelf -- it's where entity uploads ingest to.
        context["domains"] = sorted(
            {s["domain"] for s in context["sources"]} | {"assets"})
        context["available"] = True
        if q:
            try:
                context["results"] = rag.query(
                    q, rag.make_client(), conn, k=5, domain=domain or None
                )
            except Exception as e:
                context["error"] = f"search failed: {e}"
    except Exception as e:
        context["error"] = f"library unavailable: {e}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return context


def _tab_counts(account_id: int) -> dict:
    """Live counts for the tab column (2026-09-14).

    The queue depth is the whole point of this console and it used to
    take a click to find: the tabs were pills with labels and nothing
    else, so "184 concepts are waiting on you" was invisible from five
    of the six tabs. Every count is best-effort and swallowed -- a badge
    that 500s the console is strictly worse than a badge that is absent,
    and this runs on every Dev Studio render.
    """
    counts: dict[str, int] = {}
    for key, fn in (("dataset", lambda: len(evalstore.list_golden())),):
        try:
            counts[key] = fn()
        except Exception:
            pass
    return counts


@dev.get("/studio")
def studio(request: Request, tab: Optional[str] = None, message: Optional[str] = None,
           q: Optional[str] = None, domain: Optional[str] = None,
           account_id: int = Depends(auth.dev_account_id),
):
    """The Dev Studio shell. Each tab reuses the existing backend --
    preprod/autonomy calcs, the /api/evals endpoints (via the same
    evals_dev.js the old /evals page used), the rag module, the
    settings table, the evalstore -- nothing is reimplemented."""
    active_tab = tab if tab in DEV_TABS else "stats"
    context = {"active_tab": active_tab, "active_nav": "home",
               "message": message}
    context["tab_counts"] = _tab_counts(account_id)
    if active_tab == "stats":
        # what people did with what was made (src/outcomes.py): one
        # account's numbers, by week -- never averaged across accounts
        context["outputs"] = outcomes.summary(account_id=account_id)
        context["killed"] = autonomy.killed()
        context["distribution"] = _distribution(account_id)
    elif active_tab == "library":
        context["library"] = _library_context(q, domain)
    elif active_tab == "settings":
        context["settings_rows"] = settings_mod.describe()
        context["channels"] = autonomy.list_channels()
        context["killed"] = autonomy.killed()
    elif active_tab == "dataset":
        context["golden"] = evalstore.list_golden()
        context["runs"] = list(reversed(evalstore.list_runs()))
    return templates.TemplateResponse(request, "dev_studio.html", context)


@dev.post("/studio/settings")
async def studio_settings(request: Request):
    """Save the tunables. Each key validates independently; an empty
    field clears the stored value so env/default takes over. Values
    take effect on the next run -- every call site reads them live."""
    form = dict(await request.form())
    errors = []
    for key in settings_mod.TUNABLES:
        if key in form:
            try:
                settings_mod.set_value(key, form.get(key) or "")
            except ValueError as e:
                errors.append(str(e))
    message = ("; ".join(errors) if errors
               else "Saved — takes effect on the next generation/eval run.")
    return RedirectResponse(
        f"/studio?tab=settings&message={quote(message)}", status_code=303)


DATASET_EXPORTS = {
    ("golden", "csv"), ("golden", "json"), ("runs", "csv"), ("runs", "json"),
}


@dev.get("/dataset/export")
def dataset_export(what: str = "golden", fmt: str = "json"):
    """The dataset, portable: the golden set or the run history as a
    plain CSV/JSON download over evalstore's tables."""
    if (what, fmt) not in DATASET_EXPORTS:
        raise HTTPException(status_code=400,
                            detail="what must be golden|runs, fmt csv|json")
    if what == "golden":
        rows = [{"id": g["id"], "created_at": g["created_at"],
                 "query": g["query"], "relevant": g["relevant"],
                 "source": g["source"]}
                for g in evalstore.list_golden()]
    else:
        rows = [{**r, "config": r.get("config")}
                for r in evalstore.list_runs()]
    filename = f"zeropage-{what}.{fmt}"
    if fmt == "json":
        body = json.dumps(rows, indent=2)
        media = "application/json"
    else:
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow({k: (json.dumps(v) if isinstance(v, (list, dict))
                                     else v)
                                 for k, v in row.items()})
        body = buf.getvalue()
        media = "text/csv"
    return Response(content=body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'})


# --- the Dev Studio's own JSON surface --------------------------------------
# The Stats tab's eval instruments are a client-side shell, and every
# /api/* route sits behind the session gate -- which left half the tab
# ("evals unavailable, sign in first") locked while the pipeline metrics
# beside it rendered fine, purely because those come from the server.
# The Dev Studio is the operator's own console: it reads every stat in
# the project without a login, same as the rest of the dev router.
#
# These are thin delegations to the SAME app/api.py functions, not a
# second implementation -- the numbers cannot drift from /ui's. They
# register on `dev`, so a public deployment has no ungated eval surface
# at all: the routes simply don't exist there.

@dev.get("/studio/api/evals/runs")
def dev_evals_runs():
    return api.evals_runs()


@dev.get("/studio/api/evals/runs/{run_id}")
def dev_evals_run_detail(run_id: int):
    return api.evals_run_detail(run_id)


@dev.get("/studio/api/evals/requeries")
def dev_evals_requeries():
    """Production CRAG telemetry is dev-only even though it observes the
    shared retrieval path used by the product at /ui."""
    return evalstore.crag_summary()


@dev.get("/studio/api/evals/golden")
def dev_evals_golden():
    return api.evals_golden()


@dev.post("/studio/api/evals/golden")
def dev_evals_golden_add(body: api.GoldenBody):
    return api.evals_golden_add(body)


@dev.delete("/studio/api/evals/golden/{golden_id}")
def dev_evals_golden_delete(golden_id: int):
    return api.evals_golden_delete(golden_id)


@dev.post("/studio/api/evals/run")
def dev_evals_run(body: api.EvalRunBody):
    """Billed (embeddings per golden query), like every other model-
    touching button on the dev console -- the gate that matters is
    DEV_TOOLS, which is what makes this router exist."""
    return api.evals_run(body)


@dev.post("/studio/api/retrieve")
def dev_retrieve(body: api.RetrieveBody):
    return api.retrieve(body)


@dev.get("/studio/api/jobs/{job_id}")
def dev_job_detail(job_id: int):
    return api.job_detail(job_id)


def parse_video_form(form: dict) -> dict:
    """
    Raw form strings -> db.add_video kwargs. Blank optional fields become
    None, not "" -- an empty string stored as a topic is worse than no
    topic at all.
    """
    def clean(key):
        value = (form.get(key) or "").strip()
        return value or None

    idea_id_raw = (form.get("idea_id") or "").strip()
    return {
        "title": form["title"].strip(),
        "platform": form["platform"],
        "posted_at": form["posted_at"],
        "url": clean("url"),
        "timeline": clean("timeline"),
        "topic": clean("topic"),
        "hook_type": clean("hook_type"),
        "idea_id": int(idea_id_raw) if idea_id_raw else None,
    }


@dev.get("/videos/new")
def videos_new_form(request: Request, account_id: int = Depends(auth.dev_account_id)):
    return templates.TemplateResponse(
        request,
        "videos_new.html",
        {
            "platforms": db.PLATFORMS,
            "topics": db.distinct_video_field_values("topic", account_id=account_id),
            "hook_types": db.distinct_video_field_values("hook_type", account_id=account_id),
        },
    )


@dev.post("/videos/new")
async def videos_new_submit(request: Request, account_id: Optional[int] = None):
    form = dict(await request.form())
    parsed = parse_video_form(form)
    parsed.setdefault("brand", active_brand(request))  # tag to the active brand
    try:
        db.add_video(**parsed, account_id=account_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/studio", status_code=303)


@dev.post("/videos/import/youtube")
async def videos_import_youtube(request: Request):
    form = dict(await request.form())
    handle = (form.get("handle") or "").strip()
    if not handle:
        raise HTTPException(status_code=400, detail="a channel handle is required")

    api_key = os.environ.get("YOUTUBE_API_KEY")
    result = youtube.import_channel_videos(handle, api_key=api_key, db_path=None)

    if result["ok"]:
        message = f"Imported {result['added']} video(s) from {handle}"
    else:
        message = f"Could not import from {handle}: {result['error']}"

    return RedirectResponse(f"/studio?message={quote(message)}", status_code=303)


METRICS_FIELDS = ("views", "likes", "comments", "saves")


def parse_metrics_form(form: dict, video_ids: list) -> dict:
    """
    Which videos got a new number typed in, and what. A video with
    nothing typed is entirely absent from the result -- that's what
    "one save writes every changed row" means: empty means "no change
    this week," not "zero views."
    """
    changed = {}
    for vid in video_ids:
        entry = {}
        for field in METRICS_FIELDS:
            raw = (form.get(f"{field}_{vid}") or "").strip()
            if raw:
                entry[field] = int(raw)
        if entry:
            changed[vid] = entry
    return changed


@dev.get("/library")
def library(q: Optional[str] = None, domain: Optional[str] = None,
            message: Optional[str] = None):
    """The library is the Dev Studio's RAG Library tab now (2026-08-26);
    the old URL keeps working as a redirect, search params intact."""
    url = "/studio?tab=library"
    for key, value in (("q", q), ("domain", domain), ("message", message)):
        if value:
            url += f"&{key}={quote(value)}"
    return RedirectResponse(url, status_code=308)


def _uploaded_reference_text(filename: str, raw: bytes) -> str:
    """One uploaded reference file -> plain text for chunking. txt/md
    decode; a PDF extracts per-page through pypdf. Raises ValueError
    with a plain reason on anything unreadable -- the route turns it
    into a message, not a 500."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("PDF support needs pypdf (venv/bin/pip install pypdf)")
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            raise ValueError(f"could not read the PDF: {e}")
    else:
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        raise ValueError("the file has no readable text")
    return text


@dev.post("/library/ingest")
async def library_ingest(source: str = Form(""), domain: str = Form(""),
                         project: str = Form(""), source_ref: str = Form(""),
                         text: str = Form(""),
                         file: Optional[UploadFile] = File(None)):
    """Add to the library: pasted text, or an uploaded file (txt/md/pdf)
    read and chunked server-side -- same rag.ingest_records path either
    way. An uploaded file's own name becomes the source when none is
    typed, mirroring the references-picker upload."""
    filename = (file.filename or "").strip() if file is not None else ""
    body = text
    source_name = source.strip() or filename
    if filename and not text.strip():
        try:
            body = _uploaded_reference_text(filename, await file.read())
        except ValueError as e:
            return RedirectResponse(
                "/studio?tab=library&message=" + quote(str(e)), status_code=303)
    if not (source_name and domain.strip() and body.strip()):
        return RedirectResponse(
            "/studio?tab=library&message="
            + quote("a source name, a shelf (domain), and text (or a file) are all required"),
            status_code=303,
        )
    try:
        conn = rag.connect()
        rag.init_store(conn)
        written = rag.ingest_records(
            [{"source": source_name, "text": body,
              "domain": domain.strip(), "project": project.strip() or None,
              "source_ref": source_ref.strip() or None}],
            rag.make_client(), conn,
        )
        conn.close()
        message = f"stored {written} chunk(s) under '{domain.strip()}'"
    except Exception as e:
        message = f"ingest failed: {e}"
    return RedirectResponse("/studio?tab=library&message=" + quote(message),
                            status_code=303)


@dev.post("/library/backfill-assets")
def library_backfill_assets(describe: str = Form("")):
    """The catch-up: put every asset already on disk onto the shelf.
    Runs inline (not as a job) because this page has no SSE feed --
    it's a one-off operator action, and the count is the whole point.
    Describing is billed, so it rides an explicit checkbox."""
    want_describe = bool(describe)
    client = None
    if want_describe:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return RedirectResponse(
                "/studio?tab=library&message="
                + quote("GEMINI_API_KEY not set — untick describe to ingest text only"),
                status_code=303)
        client = genai.Client(api_key=api_key)
    result = asset_shelf.backfill(db_path=None, describe=want_describe,
                                  gemini_client=client)
    message = f"{result['ingested']} asset(s) on the shelf"
    if result["described"]:
        message += f", {result['described']} newly described"
    if result["skipped_no_photos"]:
        message += f", {result['skipped_no_photos']} had no photos to describe"
    if result["failed"]:
        message += f", {result['failed']} failed — {'; '.join(result['errors'][:2])}"
    return RedirectResponse("/studio?tab=library&message=" + quote(message),
                            status_code=303)


@dev.post("/library/delete")
def library_delete(source: str = Form(...)):
    try:
        conn = rag.connect()
        removed = rag.delete_source(conn, source)
        conn.close()
        message = f"removed '{source}' ({removed} chunk(s))"
    except Exception as e:
        message = f"delete failed: {e}"
    return RedirectResponse("/studio?tab=library&message=" + quote(message),
                            status_code=303)


@dev.get("/evals")
def evals_page():
    """Evals are the Dev Studio's Stats tab now (2026-08-26) -- same
    /api/evals/* endpoints, folded into the one dev page."""
    return RedirectResponse("/studio?tab=stats", status_code=308)


@dev.get("/references/pick")
def references_pick(request: Request, message: Optional[str] = None, account_id: int = Depends(auth.dev_account_id)):
    """
    The references picker: a focused page, opened as a popup from the
    Studio composer's or the Concepts form's References button, for
    grounding ONE generation on named assets from the RAG library --
    the opt-in counterpart to the always-on marketing/ai_prompting
    craft-advice layer (see shootgen.AUTO_IDEATION_DOMAINS /
    ASSET_IDEATION_DOMAINS). Selecting sources here never touches
    generation by itself; the page posts the selection back to the
    opener window (postMessage) and the opener rides it along as
    picked_references on its next Generate.
    """
    context = {"available": False, "sources": [], "domains": [],
              "message": message, "error": None, "active_nav": "workflow"}
    conn = None
    try:
        conn = rag.connect()
        context["sources"] = rag.list_sources(conn)
        context["domains"] = sorted({s["domain"] for s in context["sources"]})
        context["available"] = True
    except Exception as e:
        context["error"] = f"library unavailable: {e}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    # informational grouping only, so the picker can show "these already
    # ground automatically" -- picking one anyway is harmless, just
    # redundant, since fetch_by_sources and the automatic query would
    # both surface it.
    context["auto_domains"] = set(shootgen.AUTO_IDEATION_DOMAINS) | {"ai_prompting"}

    # Cast & props: the checkbox row that used to live directly on the
    # Concepts form now lives here instead, right next to the media
    # upload form -- one picker for everything a generation can be
    # grounded on, not two separate systems. Photo resolution mirrors
    # /studio's Workflow library exactly.
    characters = entities.list_characters(account_id=account_id)
    for c in characters:
        slug = safe_space_name(c["name"])
        c["photos"] = [f"/characters/{slug}/photo/{fn}?thumb=1"
                       for fn in _entity_photos(CHARACTERS_DIR, slug)]
    props = entities.list_props(account_id=account_id)
    for p in props:
        slug = safe_space_name(p["name"])
        p["photos"] = [f"/props/{slug}/photo/{fn}?thumb=1"
                       for fn in _entity_photos(PROPS_DIR, slug)]
    context["characters"] = characters
    context["props"] = props

    return templates.TemplateResponse(request, "references_pick.html", context)


@dev.post("/references/pick/upload")
async def references_pick_upload(file: Optional[UploadFile] = File(None), domain: str = Form(""),
                                 project: str = Form(""), source_ref: str = Form("")):
    """
    Add a file straight from your computer to the RAG library, from the
    picker page -- the file-upload counterpart to /library/ingest's
    paste-text form. The uploaded bytes are never written into the repo;
    the file's own name becomes the source identifier, same as a manual
    /library entry lets you type any source name you like. Stays on the
    picker page (not /library) so you can immediately check the box for
    what you just added.
    """
    filename = (file.filename or "").strip() if file is not None else ""
    if not (filename and domain.strip()):
        return RedirectResponse(
            "/references/pick?message=" + quote("a file and a shelf (domain) are both required"),
            status_code=303,
        )
    try:
        raw = await file.read()
        text = raw.decode("utf-8", errors="replace")
        if not text.strip():
            raise ValueError("file has no readable text")
        conn = rag.connect()
        rag.init_store(conn)
        written = rag.ingest_records(
            [{"source": filename, "text": text, "domain": domain.strip(),
              "project": project.strip() or None, "source_ref": source_ref.strip() or None}],
            rag.make_client(), conn,
        )
        conn.close()
        message = f"stored {written} chunk(s) from '{filename}' under '{domain.strip()}'"
    except Exception as e:
        message = f"upload failed: {e}"
    return RedirectResponse("/references/pick?message=" + quote(message), status_code=303)


@dev.get("/post-image")
def post_image_page(request: Request, url: Optional[str] = None,
                    caption: Optional[str] = None, message: Optional[str] = None):
    """A one-off publish surface: preview an image + caption, then post it
    to Instagram through the pipeline's gated autopilot path. Prefilled
    via ?url= & ?caption= so the trigger can hand it a hosted image."""
    return templates.TemplateResponse(
        request, "post_image.html",
        {"url": url or "", "caption": caption or "", "message": message,
         "active_nav": ""})


@dev.post("/post-image")
async def post_image_fire(request: Request):
    """Fire the post: one instagram post action through autopilot's
    three-condition gate (ZEROPAGE_AUTOPILOT=1 + this approve + no
    data/autopilot.off). instagram.execute_post_action posts an image
    when the action carries image_url."""
    form = dict(await request.form())
    image_url = (form.get("image_url") or "").strip()
    caption = (form.get("caption") or "").strip()

    def back(msg):
        return RedirectResponse(
            f"/post-image?message={quote(msg)}&url={quote(image_url)}"
            f"&caption={quote(caption)}", status_code=303)

    if not image_url:
        return back("Need a public image URL.")
    action = {"kind": "post", "platform": "instagram",
              "image_url": image_url, "caption": caption}
    try:
        result = autopilot.execute({"actions": [action]}, approve=True, dry_run=False)
    except Exception as e:
        return back(f"Post failed: {autopilot.safe_error(e)}")
    if result.get("failed"):
        # execute records an executor's failure rather than raising it
        return back(f"Post failed: {result['failed'][0]['error']}")
    mode = result.get("mode")
    if mode == "live" and result.get("executed"):
        media = (action.get("result") or {}).get("media_id")
        return back(f"Posted to Instagram ✅  (media id {media}).")
    if mode == "disabled":
        return back("Posting is OFF — set ZEROPAGE_AUTOPILOT=1 and restart.")
    if mode == "killed":
        return back("Autopilot kill switch is on (data/autopilot.off).")
    return back(f"Not posted (mode: {mode}).")


@dev.post("/post-image/queue")
async def post_image_queue(request: Request,
                                account_id: int = Depends(auth.dev_account_id)):
    """Semi-auto Midjourney path (BACKLOG #6): take a generated still -- an
    uploaded file or a public URL -- plus a caption, host it on R2 as a JPEG
    if it's a file (Meta rejects PNG/HEIC), and QUEUE it as a held image post
    on the Zero Page channel. You approve it on /holds and it publishes
    through the same gate. One-tap, not fully auto."""
    form = await request.form()
    caption = (form.get("caption") or "").strip()
    image_url = (form.get("image_url") or "").strip()
    channel = (form.get("channel") or "zeropage").strip() or "zeropage"
    upload = form.get("image_file")

    def back(msg):
        return RedirectResponse(
            f"/post-image?message={quote(msg)}&caption={quote(caption)}"
            f"&url={quote(image_url)}", status_code=303)

    # An uploaded file wins over a pasted URL: convert to JPEG and push to R2.
    if getattr(upload, "filename", ""):
        try:
            import io
            import uuid

            from PIL import Image

            from src import media, storage
            data = await upload.read()
            jpeg = Image.open(io.BytesIO(data)).convert("RGB")
            tmp = Path("/tmp") / f"mj-{uuid.uuid4().hex}.jpg"
            jpeg.save(tmp, "JPEG", quality=92)
            image_url = storage.upload_file(
                tmp, key=media.object_key(f"images/{tmp.name}", account_id),
                content_type="image/jpeg")
        except Exception as e:
            return back(f"Upload failed: {e}")

    if not image_url:
        return back("Add a Midjourney image — upload a file or paste a public JPEG URL.")

    hold_id = autonomy.to_hold(
        channel, "Midjourney image queued for approval", caption=caption,
        payload={"image_url": image_url}, status="held",
        account_id=account_id)
    return RedirectResponse(
        "/holds?message=" + quote(f"Queued image post #{hold_id} for approval."),
        status_code=303)


@dev.get("/costs")
def costs_page(request: Request, message: Optional[str] = None,
               account_id: int = Depends(auth.dev_account_id)):
    """The cost tracker (BACKLOG #2, docs/tasks/task-cost-tracker.md):
    four numbers over tables that already exist, rendered from the same
    src/costs.summary GET /api/costs serves, so the page and the JSON
    cannot disagree. Estimates, labelled as such -- never an invoice."""
    from src import costs
    return templates.TemplateResponse(
        request, "costs.html",
        {"c": costs.summary(account_id=account_id),
         "message": message, "active_nav": "costs"})


@dev.get("/winners")
def winners_page(request: Request, prompt: Optional[str] = None,
                 tool: Optional[str] = None, verdict: Optional[str] = None,
                 message: Optional[str] = None):
    """Your outcome loop: paste the final, edited prompt that actually
    worked -- the one behind a finished piece you liked and that did well
    -- and it is saved and taught to the pipeline via the RAG
    'winning_prompts' shelf shootgen grounds on. Arrives prefilled when
    you hand a prompt over from /holds (?prompt=...)."""
    winners.init()
    return templates.TemplateResponse(
        request, "winners.html",
        {"winners": winners.list_all(),
         "prefill_prompt": prompt or "",
         "prefill_tool": (tool or winners.DEFAULT_TOOL).lower(),
         "prefill_verdict": (verdict or "worked").lower(),
         "message": message, "active_nav": "winners"},
    )


@dev.post("/winners")
async def winners_add(request: Request,
                      account_id: int = Depends(auth.dev_account_id)):
    """Save the winner durably, then teach it to the pipeline. Saving
    always succeeds; the RAG ingest is best-effort so a down store never
    loses the winner -- it just re-ingests later."""
    winners.init()
    form = dict(await request.form())
    prompt = (form.get("prompt") or "").strip()
    if not prompt:
        return RedirectResponse(
            f"/winners?message={quote('A winning prompt cannot be empty.')}",
            status_code=303)
    result = winners.record_and_learn(
        form.get("tool") or winners.DEFAULT_TOOL, prompt,
        note=form.get("note") or "", video_ref=form.get("video_ref") or "",
        verdict=form.get("verdict") or "worked",
        project=accounts_mod.slug_of(account_id))
    verb = "avoid" if result.get("verdict") == "didnt_work" else "imitate"
    if result.get("ingested"):
        message = f"Saved and taught — future generations will {verb} it."
    else:
        message = ("Saved. Teaching is pending — start Postgres and re-save to "
                   f"ingest it into RAG. ({result.get('error') or 'store unavailable'})")
    return RedirectResponse(f"/winners?message={quote(message)}", status_code=303)


@dev.get("/holds")
def holds_list():
    """The hold queue's grading UI is /ui's Pipeline view now
    (2026-08-26): approve/reject/post ride the /api/holds endpoints,
    and the agreement numbers live on Dev Studio's Stats tab. The old
    URL keeps working -- morning muscle memory lands on /ui."""
    return RedirectResponse("/ui", status_code=308)


@dev.post("/holds/note")
async def holds_note(request: Request):
    """A standing correction for the next run -- the human_note channel.
    The orchestrator folds pending notes into the next generation's
    spark and consumes them, so each note steers exactly once. Lives on
    the Dev Studio Settings tab now."""
    form = dict(await request.form())
    note = (form.get("note") or "").strip()
    if note:
        autonomy.add_correction(note)
        message = "Noted — the next run folds it in."
    else:
        message = "An empty note steers nothing."
    return RedirectResponse(
        f"/studio?tab=settings&message={quote(message)}", status_code=303)


@dev.post("/channels/{name}/autonomy")
async def channels_autonomy(name: str, request: Request):
    """The promotion (or demotion): one row change. shadow -> queue ->
    auto is earned left to right by the agreement number; moving right
    is a deliberate click, never a default."""
    form = dict(await request.form())
    level = (form.get("autonomy") or "").strip()
    if autonomy.get_channel(name) is None:
        raise HTTPException(status_code=404, detail="no such channel")
    try:
        autonomy.set_autonomy(name, level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(
        f"/studio?tab=settings&message={quote(f'{name} is now {level}')}",
        status_code=303)


@dev.post("/kill")
async def kill_toggle():
    """One place to pull the plug -- and to put it back. Global on
    purpose: every channel holds while it's on."""
    if autonomy.killed():
        autonomy.unkill()
        message = "Kill switch OFF — channels follow their own autonomy again."
    else:
        autonomy.kill("killed from the dev studio")
        message = "Kill switch ON — everything holds."
    return RedirectResponse(
        f"/studio?tab=settings&message={quote(message)}", status_code=303)


@dev.get("/analytics")
@dev.get("/metrics/new")   # old URL, kept so bookmarks and habits still land
def analytics(request: Request, updated: Optional[int] = None, message: Optional[str] = None,
        account_id: int = Depends(auth.dev_account_id)):
    # Scope to the active brand (NULL-inclusive: untagged legacy videos still
    # show, so nothing disappears while the pipeline tags new posts).
    brand = active_brand(request)
    rows = [r for r in db.latest_metrics_by_video(account_id=account_id)
            if r.get("brand") in (None, brand)]

    # One measure (views) across named videos: a sorted bar list, each
    # bar scaled against the current best. Totals are headline numbers,
    # not charts.
    ranked = sorted((r for r in rows if r["views"] is not None),
                    key=lambda r: r["views"], reverse=True)
    max_views = ranked[0]["views"] if ranked else 0
    bars = [
        {**r,
         "pct": round(r["views"] / max_views * 100, 1) if max_views else 0,
         "views_fmt": f"{r['views']:,}"}
        for r in ranked
    ]
    tiles = {
        "views": f"{sum(r['views'] or 0 for r in rows):,}",
        "likes": f"{sum(r['likes'] or 0 for r in rows):,}",
        "comments": f"{sum(r['comments'] or 0 for r in rows):,}",
        "videos": len(rows),
    }
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {"rows": rows, "bars": bars, "tiles": tiles,
         "updated": updated, "message": message, "active_nav": "scoreboard"},
    )


@dev.post("/metrics/new")
async def metrics_new_submit(request: Request, account_id: int = Depends(auth.dev_account_id)):
    form = dict(await request.form())
    video_ids = [r["video_id"] for r in db.latest_metrics_by_video(account_id=account_id)]
    changed = parse_metrics_form(form, video_ids)
    for vid, fields in changed.items():
        db.record_metrics(vid, **fields, account_id=account_id)
    return RedirectResponse(f"/analytics?updated={len(changed)}", status_code=303)


@dev.post("/metrics/refresh/{video_id}")
def metrics_refresh(video_id: int, account_id: int = Depends(auth.dev_account_id)):
    """One dispatch on the video's platform; every branch returns a
    result dict, so a missing key or failed call is a message on the
    analytics page and manual entry keeps working."""
    video = db.get_video(video_id, account_id=account_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")

    if video["platform"] == "instagram":
        result = instagram.refresh_metrics_for_video(
            video, token=instagram.access_token(), db_path=None,
        )
    elif video["platform"] == "tiktok":
        from src import tiktok
        result = tiktok.refresh_metrics_for_video(
            video, token=tiktok.access_token(), db_path=None,
        )
    else:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        result = youtube.refresh_metrics_for_video(video, api_key=api_key,
                                                   db_path=None)

    if result["ok"]:
        message = f"Refreshed {video['title']}: {result['views']} views"
    else:
        message = f"Could not refresh {video['title']}: {result['error']}"

    return RedirectResponse(f"/analytics?message={quote(message)}", status_code=303)


@dev.get("/videos/{video_id}")
def video_detail(request: Request, video_id: int, account_id: int = Depends(auth.dev_account_id)):
    video = db.get_video(video_id, account_id=account_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    history = db.get_video_history(video_id, account_id=account_id)
    return templates.TemplateResponse(
        request,
        "video_detail.html",
        {
            "video": video,
            "history": history,
            "sparkline": render_sparkline(history, width=480, height=120),
        },
    )


def thumbnail_for(source: Path) -> Path:
    """
    A cached small copy. Camera originals are multi-megabyte; sending
    one down the wire to be drawn at 72px is the difference between a
    page that feels built and one that feels slow. Falls back to the
    original if the file can't be read as an image.
    """
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    stat = source.stat()
    cached = THUMB_DIR / f"{source.parent.name}__{source.stem}__{int(stat.st_mtime)}.jpg"
    if cached.is_file():
        return cached

    try:
        from PIL import Image, ImageOps

        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((480, 480))
            img.save(cached, format="JPEG", quality=82)
        return cached
    except Exception:
        return source


def _redirect_with_message(destination: str, message: str) -> RedirectResponse:
    """Every mutating route in this file ends with `?message=...` tacked
    onto wherever it's sending the person next. Split out so the join
    (`?` the first time, `&` after) is right regardless of whether
    `destination` already carries a query string -- `/assets?tab=props`
    plus a message needs `&`, a bare `/assets` needs `?`."""
    sep = "&" if "?" in destination else "?"
    return RedirectResponse(f"{destination}{sep}message={quote(message)}", status_code=303)


# Asset building lives on /ui's Assets view now (2026-08-26): creation
# and deletion are always-on JSON routes in app/api.py (which also
# ingest each save onto the RAG "assets" shelf), so a public deploy
# keeps a working create path. The old console URLs redirect.

@dev.get("/assets")
def assets_list():
    return RedirectResponse("/ui", status_code=308)


@dev.get("/locations")
def locations_list():
    return RedirectResponse("/ui", status_code=308)


def safe_space_name(name: str) -> str:
    """
    A space name becomes a directory name, so it can't be allowed to
    contain separators or climb out of the locations dir.
    """
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip().replace(" ", "-").lower()
    return cleaned.strip("-.")


# Photo serving registers on `app`, not `dev` (moved 2026-08-26): /ui's
# galleries and the API's asset payloads reference these URLs, so on a
# public deployment they must exist even though the console doesn't.

@app.get("/locations/{space}/photo/{filename}")
def location_photo(space: str, filename: str, thumb: Optional[int] = None):
    """
    Serve one photo. Both segments are resolved and checked against the
    locations dir -- a path that climbs out of it is refused rather
    than served, however it was encoded.
    """
    target = (LOCATIONS_DIR / space / filename).resolve()
    root = LOCATIONS_DIR.resolve()
    if root not in target.parents:
        raise HTTPException(status_code=404, detail="not found")
    if target.suffix.lower() not in locations.IMAGE_EXTENSIONS:
        raise HTTPException(status_code=404, detail="not found")
    if not target.is_file():
        # the wall above has already passed: space/filename cannot climb
        redirect = r2_fallback(f"locations/{space}/{filename}")
        if redirect is not None:
            return redirect
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(thumbnail_for(target) if thumb else target)


def _entity_photos(base_dir, slug):
    directory = base_dir / slug
    if not directory.is_dir():
        return []
    return sorted(
        p.name for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in locations.IMAGE_EXTENSIONS
    )


def _entity_photo_response(base_dir, slug, filename, thumb):
    target = (base_dir / slug / filename).resolve()
    root = base_dir.resolve()
    if root not in target.parents:
        raise HTTPException(status_code=404, detail="not found")
    if target.suffix.lower() not in locations.IMAGE_EXTENSIONS:
        raise HTTPException(status_code=404, detail="not found")
    if not target.is_file():
        plural = "characters" if base_dir == CHARACTERS_DIR else "props"
        redirect = r2_fallback(f"{plural}/{slug}/{filename}")
        if redirect is not None:
            return redirect
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(thumbnail_for(target) if thumb else target)


@dev.get("/characters")
def characters_list():
    return RedirectResponse("/ui", status_code=308)


@app.get("/characters/{slug}/photo/{filename}")
def character_photo(slug: str, filename: str, thumb: Optional[int] = None):
    return _entity_photo_response(CHARACTERS_DIR, slug, filename, thumb)


@dev.get("/props")
def props_list():
    return RedirectResponse("/ui", status_code=308)


@app.get("/props/{slug}/photo/{filename}")
def prop_photo(slug: str, filename: str, thumb: Optional[int] = None):
    return _entity_photo_response(PROPS_DIR, slug, filename, thumb)


def _with_director_prompts(concepts: list) -> list:
    """Attach the OpenArt Director rendering to every planned shot --
    pure text composition (shootgen.director_prompt), zero model calls,
    so doing it for every card on every page load costs nothing. Jinja
    can't call functions, so the route computes what the template shows."""
    for c in concepts:
        for s in c.get("shots") or []:
            s["director_prompt"] = shootgen.director_prompt(s, c)
    return concepts


@dev.post("/concepts/{concept_id}/shots/{shot_n}/reference")
async def concept_shot_reference(concept_id: int, shot_n: int, request: Request, account_id: Optional[int] = None):
    """Attach (or clear) the real capture behind one shot -- the acting
    take or room plate its AI generation anchors on. A file is hosted on
    R2 as a JPEG (the /post-image/queue shape exactly); a pasted public
    URL is stored as-is. Every shot is AI-generated now -- a capture is
    reference material feeding the generation, not the delivered shot."""
    form = await request.form()
    destination = safe_next(form.get("next") or "", "/concepts")

    def back(msg):
        return _redirect_with_message(destination, msg)

    try:
        if form.get("remove"):
            preprod.set_shot_reference_image(concept_id, shot_n, "", account_id=account_id)
            return back(f"Reference cleared from shot {shot_n}.")

        image_url = (form.get("reference_url") or "").strip()
        upload = form.get("reference_file")
        if getattr(upload, "filename", ""):
            try:
                import io
                import uuid

                from PIL import Image

                from src import media, storage
                data = await upload.read()
                jpeg = Image.open(io.BytesIO(data)).convert("RGB")
                tmp = Path("/tmp") / f"ref-{uuid.uuid4().hex}.jpg"
                jpeg.save(tmp, "JPEG", quality=92)
                image_url = storage.upload_file(
                    tmp, key=media.object_key(f"references/{tmp.name}", account_id),
                    content_type="image/jpeg")
            except Exception as e:
                return back(f"Reference upload failed: {e}")
        if not image_url:
            return back("Attach a capture — a file, or a public image URL.")
        preprod.set_shot_reference_image(concept_id, shot_n, image_url, account_id=account_id)
    except ValueError as e:
        return back(str(e))
    return back(f"Reference attached to shot {shot_n} — the AI generation anchors on it.")


@dev.get("/concepts")
def concepts_list(message: Optional[str] = None):
    """The old concepts page. Its grading moved to the Dev Studio's Grade
    tab in 2026-08, and that tab went on 2026-10-11, so the URL lands on
    Stats -- still forwarding any message a POST route sent along, so
    every legacy `next=/concepts` keeps landing somewhere real."""
    url = "/studio"
    if message:
        url += f"?message={quote(message)}"
    return RedirectResponse(url, status_code=308)


@dev.post("/concepts/discard-all")
def concepts_discard_all(request: Request, account_id: Optional[int] = None):
    """Clear every concept for the active brand -- a fresh slate when the
    generator's slate isn't landing."""
    brand = active_brand(request)
    n = preprod.delete_all_concepts(brand=brand, account_id=account_id)
    return RedirectResponse(
        "/concepts?message=" + quote(f"Discarded all {n} {brand} concept(s)."),
        status_code=303)


@dev.post("/concepts/scene-brief/{brief_id}/delete")
def scene_brief_delete(brief_id: int, account_id: Optional[int] = None):
    preprod.delete_scene_brief(brief_id, account_id=account_id)
    return RedirectResponse(
        "/concepts?message=" + quote(f"Discarded scene brief #{brief_id}."),
        status_code=303)


@dev.post("/inspiration/add")
def inspiration_add(handle: str = Form(...), note: str = Form(""), profile: str = Form(...)):
    """Add or update an inspiration account -- e.g. once you've pasted posts
    for an account I couldn't reach."""
    try:
        inspiration.add(handle, note, profile)
        msg = f"Saved inspiration @{handle.lstrip('@').strip().lower()}."
    except ValueError as e:
        msg = str(e)
    return RedirectResponse("/concepts?message=" + quote(msg), status_code=303)


@dev.post("/inspiration/{handle}/delete")
def inspiration_delete(handle: str):
    inspiration.delete(handle)
    return RedirectResponse(
        "/concepts?message=" + quote(f"Removed inspiration @{handle}."), status_code=303)


def safe_next(value: Optional[str], default: str) -> str:
    """
    Which screen a form wants to land on. Only a site-relative path is
    honoured -- a `next` that names another host would turn every button
    in the app into an open redirect.
    """
    candidate = (value or "").strip()
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return default


@dev.post("/concepts/{concept_id}/shot")
def concepts_mark_shot(concept_id: int, next: str = Form(""), account_id: int = Depends(auth.dev_account_id)):
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="concept not found")

    preprod.mark_shot(concept_id, shot=not concept["shot_done"], account_id=account_id)
    return RedirectResponse(safe_next(next, "/concepts"), status_code=303)


# The posture switch (see DEV_TOOLS at the top): on a public deployment
# this include never runs, so the dev console isn't hidden -- it doesn't
# exist. This must stay the last statement so every @dev route above is
# already registered on the router when it lands on the app.
if DEV_TOOLS:
    app.include_router(dev)
