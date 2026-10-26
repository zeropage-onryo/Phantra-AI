"""
The JSON API behind /ui -- the ported studio.html skin. One rule from
its build spec governs everything here: every control in that UI is
backed by a working endpoint, and GET /api/capabilities is derived
from what is actually wired (key presence, store reachability), never
a static dict someone forgets to update.

Adaptations from the spec, decided 2026-08-21: the pipeline surface is
the real pre-production loop (concepts -> approve = plan a shot list,
deny = reasons + note recorded as a correction AND a RAG feedback
chunk), not the removed pitch/editgen chain. Assets are the real
grounding entities (locations, characters, props); footage ingest is a
later phase. Analytics reads the real metrics snapshots -- no daily
rollups exist yet, so no daily chart is served.
"""
import hashlib
import json
import os
import re
import statistics
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src import (
    accounts,
    asset_shelf,
    autonomy,
    brand_kits,
    crag,
    db,
    edit_teach,
    element_sheet,
    entities,
    evalstore,
    generative,
    imagery,
    instagram,
    manual_lane,
    outcomes,
    preprod,
    presets,
    pricing,
    projects,
    providers,
    rag,
    rag_eval,
    refbin,
    render_assets,
    render_specs,
    settings,
    storage_quota,
    timeline,
    winners,
    workflows,
    youtube,
)
from src import free_looks as looks
from src.approvals import ApproveRefused, ElementRefused
from src.locations import IMAGE_EXTENSIONS

from . import (
    auth,
    jobs,
    mcp_auth,
    model_connections,
    post_routes,
    publish_routes,
    social_routes,
    whats_new_routes,
    workflow_runner,
)
from . import creative_projects as creative_projects_routes

router = APIRouter(prefix="/api")

# Both live in their own module and mount UNDER /api, which is what makes
# their client paths /api/creative-projects and /api/model-connections.
# They are included here rather than in main.py so they inherit this
# router's auth dependency along with every other /api route -- and so a
# reader looking for "what is under /api" finds all of it in one place.
router.include_router(creative_projects_routes.router)
router.include_router(model_connections.router)
router.include_router(publish_routes.router)
router.include_router(social_routes.api_router)
router.include_router(post_routes.router)
router.include_router(whats_new_routes.router)

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
LOCATIONS_DIR = PROJECT_ROOT / "locations"
CHARACTERS_DIR = PROJECT_ROOT / "characters"
PROPS_DIR = PROJECT_ROOT / "props"
CRAG_REWRITE_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")

# The deny screen's vocabulary. An enum, not free text, so denial
# reasons aggregate instead of fragmenting into synonyms.
DENY_REASONS = (
    "wrong location", "off-tone", "character drift",
    "pacing", "retrieval missed", "too generic",
)


def _eval_k() -> int:
    """How many results the eval scores per query -- a Dev Studio
    tunable (settings -> EVAL_K env -> 5), resolved per run so a
    change takes effect on the next run, no restart."""
    return settings.eval_k()


def _form_project(form, account_id: int) -> Optional[dict]:
    """The project a multipart form names (`project_id`), or None when it
    names none or one this account does not own."""
    raw = (form.get("project_id") or "").strip()
    if not raw:
        return None
    try:
        return projects.get(int(raw), account_id=account_id)
    except (TypeError, ValueError):
        return None


def _form_kit(form, account_id: int):
    """(kit, refusal): the brand kit a composer form PICKED (`brand_kit_id`,
    2026-10-22: a kit chosen for a conversation outside a project). No pick
    is (None, None); a kit that is not this account's is a 404."""
    raw = (form.get("brand_kit_id") or "").strip()
    if not raw:
        return None, None
    kit = brand_kits.get(int(raw), account_id=account_id) if raw.isdigit() else None
    if kit is None:
        return None, _error(404, "not_found", f"no brand kit {raw}")
    return kit, None


def _in_project(project: Optional[dict], work):
    """A job body that runs inside `project` (src/project_context.py): the
    ContextVar is set on the worker thread, where the prompts are built."""
    from src import project_context

    def run(job):
        with project_context.active(project):
            return work(job)
    return run


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message}})


def _create_gate(account_id: Optional[int]) -> Optional[JSONResponse]:
    """A Create costs no credits (2026-09-29, Mike's call: included in the
    subscription, priced into the plans). It is refused -- 402, BEFORE any
    job or model call -- only for an account with no plan and no credit
    balance, or a trial whose included thinking is used up
    (charge.create_refusal_code: the code and the message. The MCP tools
    ask the same predicate through its wrapper, charge.create_refusal,
    which gives the message alone).

    EVERY ROUTE THAT SPENDS MODEL TEXT ASKS IT (2026-10-08, the spend
    holes, docs/tasks/task-spend-holes-and-credits.md): the Guide, the
    brief draft, an element's vision describe, Direct and Polish, the
    canvas's Ground / Enhance / Run all, the research crawl, the evals and
    the cut's index and agent. Each stays free per click; this is the one
    question of whether the account has anything for it to be included in.
    A new route that calls a model asks it too."""
    from src import charge as charging
    refused = charging.create_refusal_code(account_id)
    if refused:
        # subscribe_or_top_up, or trial_thinking_used once the sign-up
        # trial's included thinking is spent (2026-10-08)
        return _error(402, *refused)
    return None


def _out_of_credits(e, what: str) -> JSONResponse:
    from src import charge as charging
    return _error(402, "out_of_credits", charging.refusal(e, what))


# --- capabilities -----------------------------------------------------------

def _gemini_key(account_id: Optional[int] = None) -> Optional[str]:
    """The installation's Gemini key (GEMINI_API_KEY), or None. It was
    per account while BYOK existed; since 2026-09-26 it is the operator's
    for every account (docs/tasks/task-fal-only.md). `account_id` stays
    so the call sites need not change."""
    from src import gemini_utils
    return gemini_utils.api_key_for(account_id)


def _rag_reachable() -> bool:
    """A real connect, not a config guess -- localhost Postgres answers in
    single-digit ms, and 'the store is down' must gate retrieve/evals
    honestly rather than surfacing as a wall of failed fetches."""
    try:
        conn = rag.connect()
        try:
            conn.close()
        except Exception:
            pass
        return True
    except Exception:
        return False


def compute_capabilities(account_id: Optional[int] = None) -> dict:
    """What the shell may render. Derived live, never a static dict.

    `account_id` is the TENANT, resolved server-side, and it exists for
    exactly one key: `manual_lane`. Everything else here is a property of
    the INSTALLATION -- a key is set or it is not -- and is the same
    answer for every caller, which is why this route is allowed to take
    no account at all (tests/test_tenancy.py's exempt list). The lane is
    a property of the ACCOUNT, so it needs one, and `None` -- nobody
    signed in, or a user with no membership -- reads as no lane, which is
    also what manual_lane's fail-closed rule says.
    """
    from src import promptgen

    gemini = bool(_gemini_key(account_id))
    store = _rag_reachable()
    return {
        # per-shot polish needs the in-flight promptgen.refine_prompt to
        # have landed, plus the shelf and the key it refines with
        "polish": gemini and store and hasattr(promptgen, "refine_prompt"),
        "assets.list": True,
        "assets.create": True,
        "retrieve": store and gemini,          # query embeds with Gemini
        "pipeline.concepts": True,
        "pipeline.run": gemini,
        # the guide's default provider is Gemini on the same key; the
        # personal providers are reported per-account by
        # /api/model-connections, which is a different question
        "creative_guide": gemini,
        "pipeline.deny": True,                  # correction always lands; RAG chunk is best-effort
        "evals.golden": True,
        "evals.run": store and gemini,
        "analytics": True,
        "analytics.youtube": bool(os.environ.get("YOUTUBE_API_KEY")),
        "analytics.instagram": bool(instagram.access_token()),
        # the video renderer (fal, since 2026-09-26) is configured -- the
        # Director's Generate node and the Queue render on it
        "video.generate": providers.renderer_for(
            account_id, needs="generate_from_prompt") is not None,
        # whether a price comes with a signed quote a client can echo on
        # approve (pricing.sign; QUOTE_SIGNING_SECRET set)
        "quote.sign": pricing.configured(),
        # `video.spend` is TRUE for anything a person drives (2026-09-09):
        # the click is the approval, so the key is the whole gate on a
        # human surface. It stays a live read for the unattended paths,
        # which still need FAL_SPEND_OK set for them on purpose -- see
        # fal.spend_approved. The UI reads it to decide whether to dim a
        # button, and dimming a button a person is allowed to press was
        # the whole complaint.
        "video.spend": providers.renderer_for(
            account_id, needs="generate_from_prompt") is not None,
        "nano.generate": gemini,               # Nano Banana rides the Gemini key
        "workflows": True,
        "jobs": True,
        # deployment posture (app/main.py's DEV_TOOLS, read live like the
        # keys above): gates /ui elements that point into the dev console,
        # e.g. the rail's "legacy" link -- on a public deployment there is
        # no /studio to link to
        "dev_tools": os.environ.get("DEV_TOOLS") == "1",
        # The operator-only subscription lane (src/manual_lane.py), so
        # the Queue view can leave its section out entirely for everyone
        # else instead of rendering a panel that 404s.
        #
        # PRESENTATION ONLY, and this is the line worth not crossing: a
        # capability is what the shell may DRAW, never what the server
        # may DO. Every lane route re-asks manual_lane against the
        # account it resolved itself, so a caller who fakes this flag --
        # it is a JSON field in a response they can edit in a console --
        # gains a section full of cards that refuse. There is also no
        # write twin: the flag is granted with
        # `python -m src.accounts operator <slug> --on` and nowhere else,
        # because an account that can grant itself the lane is not gated.
        "manual_lane": manual_lane.manual_lane_allowed(account_id),
        # the free, non-generative looks (src/free_looks.py, 2026-10-22): listed in
        # the effects gallery and runnable through /effects/run only when
        # PHANTRA_FREE_LOOKS=1; off, the gallery is exactly what it was
        "free_looks": looks.enabled(),
        # The Effects tab (/studio/effects, 2026-10-22, docs/tasks/
        # task-effects-tab.md): a page over the same effects table the
        # composer's gallery reads. OFF by default; PHANTRA_EFFECTS_TAB=1
        # turns it on for the installation. With it off the page is a 404
        # and the rail has no entry, so production is unchanged.
        "effects_tab": os.environ.get("PHANTRA_EFFECTS_TAB", "").strip() == "1",
        # The Create page's v2 layout (docs/tasks/task-create-page-v2.md,
        # 2026-10-22): the Runway / Higgsfield-shaped sections under the
        # composer, every card a showcase render. ON by default since the
        # visuals pass (Mike, 2026-10-22 evening: "so the new Create page
        # ships when the PRs merge"); PHANTRA_CREATE_V2=0 turns it off, and
        # with it off the page is the same component tree it was.
        # Presentation only, like the rest: nothing the sections draw
        # spends without its own priced card.
        "create_v2": os.environ.get("PHANTRA_CREATE_V2", "1").strip() != "0",
        # THE OVERNIGHT FLAGS (2026-10-22, docs/tasks/task-overnight-2026-10-22.md),
        # off by default; with each off, the studio is what it was.
        # vesper_v2 (docs/tasks/task-vesper-v2.md): the media-first Create
        # layout, the storyboard, the autonomy dial, tappable questions and
        # the next steps after a render. PHANTRA_VESPER_V2=1 turns it on.
        "vesper_v2": vesper_v2_on(),
        # kling_4: the parked Kling 4.0 slot (fal.SLOTS) is READY -- its
        # flag set, its official ids filled in and its price published --
        # so a picker may draw it. Off today, and off with the flag alone.
        "kling_4": _kling4_ready(),
    }


def _kling4_ready() -> bool:
    from src import fal  # local, as the other src readers here
    return fal.slot_ready("kling4")


def vesper_v2_on() -> bool:
    """The vesper_v2 flag, read live off the environment."""
    return os.environ.get("PHANTRA_VESPER_V2") == "1"


@router.get("/capabilities")
def capabilities(account_id: Optional[int] = Depends(auth.optional_account_id)):
    """What the shell may draw. `optional_account_id` and not
    `current_account_id`, because this is the one route the shell asks
    BEFORE it knows whether the person has an account at all -- a 403
    here blanks the whole UI -- and because None is a perfectly good
    answer to "does this account have the lane": no."""
    return compute_capabilities(account_id)


def _account_card(a: dict) -> dict:
    """accounts rows name the label display_name and the accent
    accent_color; the shell wants the shorter names."""
    return {"id": a["id"], "slug": a["slug"],
            "label": a.get("display_name") or a["slug"],
            "accent": a.get("accent_color"), "role": a.get("role")}
@router.get("/scene-lengths")
def scene_lengths(account_id: int = Depends(auth.current_account_id)):
    """The scene lengths the composer offers, and which is the default --
    timeline.SCENE_SECONDS_CHOICES and scene_seconds() projected, so the
    select cannot drift from what the route will clamp to. The default
    follows PHANTRA_SCENE_SECONDS, which is also what the night writes."""
    default = timeline.scene_seconds()
    choices = sorted(set(timeline.SCENE_SECONDS_CHOICES) | {default})
    return {"choices": choices, "default": default,
            "min": timeline.MIN_SCENE_SECONDS, "max": timeline.MAX_SCENE_SECONDS}


@router.get("/skills")
def skills_list(account_id: int = Depends(auth.current_account_id)):
    """The skill shelf for the composer's `/` menu (src/skills.py): the
    name, the title, one line on when it is the right recipe, and which
    output it usually ends in. A PROJECTION of prompts/skills/, like the
    brains below -- never the recipes themselves, which only the brain reads."""
    from src import skills
    return {"items": skills.catalogue()}


@router.get("/brains")
def brains(account_id: int = Depends(auth.current_account_id)):
    """The model tiers the composer may offer, as a PROJECTION of
    gemini_utils.BRAINS rather than a second list (providers.render_options'
    rule). A hardcoded <option> in the template is a copy that goes stale
    the first time a tier is added or a model id moves.

    Not a capability: a capability answers "may the shell draw this", and
    the answer for the tiers is the same as for Create itself
    (`pipeline.run` -- the Gemini key). This is the menu behind a control
    that is already gated.

    Takes the account even though the menu is installation-wide, unlike
    /capabilities beside it. That route is exempt because the shell asks
    it BEFORE it knows whether the person has an account at all; this one
    is asked from inside Studio, which is already behind sign-in, so
    there is nothing to gain from being the one /api route a signed-in
    stranger can reach (tests/test_tenancy.py enforces exactly that).

    Local import: src.gemini_utils pulls in google.genai, and this module
    stays cheap to import (the shootgen convention above).
    """
    from src import gemini_utils
    return {"brains": gemini_utils.brain_options(),
            "default": gemini_utils.DEFAULT_BRAIN}


# The composer's image models (2026-10-04, Mike's call: "images don't just
# pull from nano banana, they use fal.ai and can choose between different
# image models"). A PROJECTION, the /brains rule: Nano Banana on the Gemini
# key, plus every entry of fal.IMAGE_MODELS when the fal key is set. `id`
# is what the composer posts back as `image_model`; `credits` is the price
# of one still at 1MP, the number the balance pill will move by.
NANO_IMAGE_MODEL = "nano"


def image_model_options(account_id: Optional[int] = None) -> dict:
    """The models that can draw a still. One owner since 2026-10-11:
    src/model_menu.py, which also hands the same rows to the brain
    (`list_models`), so the picker and a proposal are read off one list."""
    from src import model_menu
    return model_menu.image_menu(account_id)


@router.get("/image-models")
def image_models(account_id: int = Depends(auth.current_account_id)):
    """Which model draws a still, for the composer's picker."""
    return image_model_options(account_id)


@router.get("/clip-models")
def clip_models(account_id: int = Depends(auth.current_account_id)):
    """The clip models a scene can be rendered on, with the catalogue's own
    line and price for each (src/model_menu.py `video_menu`) -- what the
    brain's `list_models` lists, so the composer can name the model a scene
    was proposed for. Read-only; the Render card is still where one is
    picked and paid for."""
    from src import model_menu
    return {"items": model_menu.video_menu(account_id)}


@router.get("/render-choices")
def render_choices(account_id: int = Depends(auth.current_account_id)):
    """The frames a scene can be written for, PROJECTED from
    src/render_specs.FRAME_SIZES rather than listed again here.

    There is deliberately no "resolution" beside it: a ratio in this
    project is a frame SIZE ("720:1280"), so width and height are the
    same choice, and offering a second control for a dimension the
    renderers do not take would be a pill that changes nothing.

    The label is derived, not stored -- one place decides that 720:1280
    is 9:16, so a size added to FRAME_SIZES shows up here correctly
    without anyone remembering to name it.
    """
    from math import gcd

    def label(size: str) -> str:
        try:
            w, h = (int(n) for n in size.split(":"))
        except ValueError:
            return size
        step = gcd(w, h) or 1
        return f"{w // step}:{h // step}"

    return {
        "ratios": [{"id": r, "label": label(r), "size": r}
                   for r in render_specs.FRAME_SIZES],
        "default": render_specs.RATIO_9_16,
    }


@router.get("/me")
def me(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Who is signed in and which account they are acting as -- the
    account block at the bottom of the React shell's rail (2026-09-11).
    Composed from the same helpers the Jinja shell reads
    (auth.current_user / current_account / accounts.memberships), so the
    two shells can never disagree about who you are. Identity fields
    are the profile mirror's; the active account is real membership,
    with the `brand` cookie only a preference among the accounts you
    belong to."""
    user = auth.current_user(request) or {}
    member_of = accounts.memberships(user["id"]) if user.get("id") else []
    # The OPEN workspace, not the tenant (BACKLOG #19, 2026-09-21). This
    # used to match on `account_id`, which is current_account_id -- the
    # oldest membership whatever the cookie says -- so a switch set the
    # cookie and this went on answering the first workspace: the React
    # account menu looked dead. auth.current_account is what /ui reads for
    # `data-account`, so the two shells resolve the workspace by one rule.
    # `account_id` stays declared: it is the gate (401/403), not the answer.
    slug = (auth.current_account(request, user or None) or {}).get("slug")
    active = next((a for a in member_of if a["slug"] == slug), None)
    return {
        "user": {"id": user.get("id"), "email": user.get("email"),
                 "display_name": user.get("display_name") or (user.get("email") or "").split("@")[0],
                 "avatar_url": user.get("avatar_url")},
        "account": _account_card(active) if active else None,
        "accounts": [_account_card(a) for a in member_of],
        # the account menus' "Connect to Claude" panel (2026-10-08): the
        # address to paste into claude.ai, from the one place it is
        # defined, and the directory listing once there is one. Both are
        # null when there is nothing to connect to; no database read.
        "mcp_url": mcp_auth.connector_url(),
        "claude_directory_url": mcp_auth.directory_url(),
    }


@router.get("/account/members")
def account_members(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Who is in the workspace the person has open (Settings -> Workspace,
    2026-10-11). READ ONLY: membership is still granted by members
    (`src.accounts invite`), never from a page -- an invite UI is BACKLOG
    #22 and its own decision.

    The workspace is `auth.current_account` -- the one /api/me calls
    `account` and the shell marks active -- which is backed by REAL
    membership: the `brand` cookie only picks among accounts the caller
    belongs to, so there is no id in the request to point at somebody
    else's workspace. `account_id` stays declared because it is the gate
    (401, and 403 for a member of nothing), as it is on /api/me.

    An OWNER is shown every member's address. A member is shown names
    only, and nobody's address but their own: an address is how a person
    is reached and signed in as, and being in a workspace with someone is
    not a reason to be handed theirs. A person with no name on file is
    "Member" to another member, never the front half of their address."""
    user = auth.current_user(request) or {}
    active = auth.current_account(request, user or None)
    if not active:
        return _error(403, "no_account", "you are not in a workspace yet")
    owner = (active.get("role") or "") == "owner"
    members = []
    for row in accounts.members_of(int(active["id"])):
        you = str(row["id"]) == str(user.get("id"))
        address = row.get("email") or ""
        shown = owner or you
        members.append({
            "name": (row.get("display_name") or "").strip()
                    or (address.split("@")[0] if shown else "Member"),
            "email": address if shown else None,
            "avatar_url": row.get("avatar_url"),
            "role": row.get("role") or "member",
            # has this person ever signed in? an invite sits unclaimed until then
            "claimed": bool(row.get("claimed_at")),
            "you": you,
        })
    # Whose rows the studio is working in. Every data route acts on
    # `account_id` -- the caller's FIRST workspace (auth.current_account_id
    # says why) -- whichever one is open, so for somebody in two workspaces
    # the page can say where their credits and scenes live instead of
    # letting the switch imply they moved.
    home = auth.tenant_account(request, account_id)
    return {"account": {"id": active["id"], "slug": active["slug"],
                        "label": active.get("display_name") or active["slug"]},
            "role": active.get("role") or "member",
            "can_see_emails": owner,
            "members": members,
            "home": ({"id": home["id"], "slug": home["slug"],
                      "label": home.get("display_name") or home["slug"]} if home else None)}


@router.get("/mcp/connection")
def mcp_connection(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Whether THIS person has connected Claude to THIS account, for the
    account menus' Connect to Claude panel (src/mcp_connections.py says
    what the studio can and cannot see). The tenant, not the brand: an
    MCP call resolves to the person's oldest membership, so that is the
    account a connection was recorded under. Never another account's,
    never another member's. Nothing here calls Supabase or claude.ai."""
    user = auth.current_user(request) or {}
    from src import mcp_connections
    return mcp_connections.status(account_id, str(user.get("id") or ""))


# --- settings: the person's own row and their password --------------------
# /studio/settings (2026-10-03, Mike: "Supabase didn't send a code or allow
# a new user to create a password ... we need to build out settings and
# password change etc"). Everything here is about the signed-in PERSON
# (the users mirror row, their GoTrue identity), not the account, which
# is why each route reads auth.current_user; `account_id` stays declared
# because it is the gate every /api route stands behind.
#
# A password write re-proves the person first (app/auth.py: their
# current password, or a code mailed by POST /me/security/code), takes a
# one-call session from GoTrue, writes through PUT /user and drops the
# token. Nothing of Supabase's is stored here.

class ProfileBody(BaseModel):
    display_name: Optional[str] = None


class PasswordBody(BaseModel):
    password: str
    password2: Optional[str] = None
    # exactly one of these proves the person
    current_password: Optional[str] = None
    code: Optional[str] = None


class EmailChangeBody(BaseModel):
    email: str
    current_password: Optional[str] = None
    code: Optional[str] = None


def _refresh_user(request: Request) -> Optional[dict]:
    """auth.current_user caches the mirror row per request; after a write
    the answer must be the row as it now is."""
    user = auth.current_user(request) or {}
    if user.get("id"):
        request.state.auth_user = accounts.get_user(user["id"])
    return request.state.auth_user


def _security_card(user: dict) -> dict:
    return {
        "email": user.get("email"),
        # what THIS app knows (db.add_password_set_at_column): unknown
        # reads as False, and a password login or a change stamps it
        "has_password": bool(user.get("password_set_at")),
        "password_set_at": user.get("password_set_at"),
        # the emailed-code door works only when Supabase is wired; a
        # password check needs the same, so one flag for both
        "can_change": auth.configured(),
        "min_password_len": auth.MIN_PASSWORD_LEN,
    }


def _prove_person(user: dict, current_password: Optional[str],
                  code: Optional[str]):
    """A GoTrue session for the signed-in person, minted by the proof
    they offered: their current password, else a code from their inbox.
    Returns (session, error_response)."""
    email = user.get("email") or ""
    if not email:
        return None, _error(400, "no_email", "this account has no email on file")
    if current_password:
        session = auth.user_session_by_password(email, current_password)
        if not session:
            return None, _error(400, "wrong_password", "that password is not right")
    elif code:
        session = auth.user_session_by_code(email, code, "recovery")
        if not session:
            return None, _error(400, "bad_code",
                                "that code didn't work -- check it, or send a new one")
    else:
        return None, _error(400, "proof_required",
                            "send your current password, or a code from your email")
    claims = auth.verify_token(session.get("access_token") or "") or {}
    if claims.get("sub") != user.get("id"):
        # a code typed for somebody else's address cannot reach here (the
        # email is the signed-in person's), but the check costs nothing
        return None, _error(403, "not_you", "that session is not yours")
    return session, None


@router.patch("/me")
def me_update(request: Request, body: ProfileBody,
              account_id: int = Depends(auth.current_account_id)):
    """Rename yourself. Blank clears the name and the shell falls back
    to the email's local part, as it always has."""
    user = auth.current_user(request) or {}
    fields = body.model_dump(exclude_unset=True)
    if "display_name" not in fields:
        return _error(400, "nothing_to_change", "send display_name")
    name = (fields["display_name"] or "").strip()
    if len(name) > 80:
        return _error(400, "too_long", "a name is at most 80 characters")
    accounts.set_display_name(user["id"], name)
    _refresh_user(request)
    return me(request, account_id)


@router.get("/me/security")
def me_security(request: Request, account_id: int = Depends(auth.current_account_id)):
    user = auth.current_user(request) or {}
    return _security_card(user)


@router.post("/me/security/code")
def me_security_code(request: Request,
                     account_id: int = Depends(auth.current_account_id)):
    """Mail a code to the signed-in person's address, to prove it before
    a password or email change. No PKCE and no redirect on purpose: the
    link in that email would land on an origin holding no verifier (the
    studio reaches this API through its proxy), so the CODE is the thing
    the settings page asks for."""
    user = auth.current_user(request) or {}
    if not auth.configured():
        return _error(503, "not_configured", "sign-in isn't configured (SUPABASE_URL)")
    if not user.get("email"):
        return _error(400, "no_email", "this account has no email on file")
    if auth._rate_limited(request, "otp"):
        return _error(429, "rate_limited", "too many codes requested -- wait a minute")
    error = auth.send_recovery_code(user["email"])
    if error:
        return _error(502, "not_sent", error)
    return {"sent": True, "email": user["email"]}


@router.post("/me/password")
def me_password(request: Request, body: PasswordBody,
                account_id: int = Depends(auth.current_account_id)):
    """Set or change the password. The proof is the current password or
    an emailed code (`_prove_person`); the write is GoTrue's PUT /user."""
    user = auth.current_user(request) or {}
    if not auth.configured():
        return _error(503, "not_configured", "sign-in isn't configured (SUPABASE_URL)")
    if auth._rate_limited(request, "password"):
        return _error(429, "rate_limited", "too many attempts -- wait a minute")
    problem = auth.password_problem(body.password, body.password2)
    if problem:
        return _error(400, "weak_password", problem)
    session, refused = _prove_person(user, body.current_password, body.code)
    if refused:
        return refused
    error = auth.set_user_fields(session["access_token"], {"password": body.password})
    if error:
        return _error(502, "not_changed", error)
    accounts.mark_password_set(user["id"])
    return {"ok": True, **_security_card(_refresh_user(request) or user)}


@router.post("/me/email")
def me_email(request: Request, body: EmailChangeBody,
             account_id: int = Depends(auth.current_account_id)):
    """Ask GoTrue to move the identity to another address. Not done when
    this returns: Supabase mails a confirmation (to both addresses under
    its "secure email change" default) and the change lands when it is
    clicked; the mirror row follows at the next sign-in (accounts.claim).
    The answer says exactly that."""
    user = auth.current_user(request) or {}
    if not auth.configured():
        return _error(503, "not_configured", "sign-in isn't configured (SUPABASE_URL)")
    if auth._rate_limited(request, "password"):
        return _error(429, "rate_limited", "too many attempts -- wait a minute")
    new_email = body.email.strip().lower()
    if not auth._valid_email(new_email):
        return _error(400, "bad_email", "enter a real email address")
    if new_email == (user.get("email") or "").lower():
        return _error(400, "same_email", "that is already your address")
    if accounts.get_user_by_email(new_email):
        return _error(409, "email_taken", "that address belongs to another account here")
    session, refused = _prove_person(user, body.current_password, body.code)
    if refused:
        return refused
    error = auth.set_user_fields(session["access_token"], {"email": new_email})
    if error:
        return _error(502, "not_changed", error)
    return {"ok": True, "pending": new_email,
            "note": ("check the inbox at the new address (and the old one) and "
                     "confirm the change -- it applies at your next sign-in")}


# --- the creative guide -----------------------------------------------------
# Conversational brief development. It writes NOTHING: no concept, no
# render, no spend beyond the one model call -- the Create button is
# still the only thing that writes scenes, which is why this route can
# be as chatty as it likes.
#
# Restored 2026-09-10 after being overwritten. src/creative_guide.py,
# app/creative_projects.py, app/model_connections.py and the client all
# survived; this route and the two include_routers above did not, and
# are rebuilt from the contract the client still states. Diff it against
# your editor's local history before trusting it to be what was there.

@router.post("/creative-guide")
async def creative_guide_reply(request: Request,
                               account_id: int = Depends(auth.current_account_id)):
    """One turn of the conversation, as a job.

    A job rather than a plain response because the reasoning tier takes
    tens of seconds and an open request that long is indistinguishable
    from a hang -- the client polls /api/jobs/{id} and shows `detail`.

    The header check is model_connections' own: a studio session is
    SameSite=None, so a cross-site form post must not be able to spend a
    personal model connection. It runs for every provider, not just the
    personal ones, because the cheapest place to refuse is before any
    work happens.
    """
    from src import creative_guide, scene_chain

    model_connections.mutation_header(request)
    form = await request.form()
    raw = form.get("conversation") or ""
    try:
        conversation = creative_guide.Conversation.model_validate_json(raw)
    except Exception:
        return _error(400, "bad_conversation", "that conversation could not be read")
    # A turn is a REPLY to something the person said, so the history has
    # to end with them. An assistant-last history would ask the model to
    # talk to itself, and it is worth refusing before anything is billed
    # rather than after.
    if conversation.messages[-1].role != "user":
        return _error(400, "bad_conversation",
                      "the conversation has to end with your own message")

    # A form's `brand` is ignored (2026-10-13): nothing here reads one.

    provider = (form.get("guide_provider") or "gemini").strip().lower()
    model = (form.get("guide_model") or "").strip() or None
    personal = provider != "gemini"
    # Which brain answers (2026-09-18): the composer's Fast / Reasoning
    # pill, the same one Create sends, clamped against BRAINS here the
    # way scenes_run clamps it. Absent or unknown -> the Guide's own
    # default (fast). Only the Gemini path reads it; a personal
    # connection is the person's own model and has no tier.
    from src import gemini_utils
    brain_raw = (form.get("brain") or "").strip().lower()
    brain = brain_raw if brain_raw in gemini_utils.BRAINS else creative_guide.DEFAULT_BRAIN

    # The assistant pill (2026-09-26, src/assistant_brain.py): a turn
    # that says which page it floats over / which step the project is on
    # gets the step's playbook, what is already known (look, must-not
    # list, the board's picks and passes), the reference hunt as a tool
    # and a judged set of directions. `brain=auto` picks the tier per
    # step. A turn without `assistant` is the Guide exactly as it was.
    assistant = None
    if (form.get("assistant") or "").strip() in ("1", "true", "on"):
        from src import assistant_brain
        assistant = {
            "name": assistant_brain.clean_name(form.get("assistant_name")),
            "tone": assistant_brain.clean_tone(form.get("assistant_tone")),
            "stage": assistant_brain.clean_stage(form.get("stage")),
            "page": assistant_brain.clean_page(form.get("page")),
        }
        last = conversation.messages[-1].content
        brain = assistant_brain.pick_brain(brain_raw, assistant["stage"], last)

    scope = None
    if personal:
        scope = model_connections.connection_scope(request, account_id)
        if not _personal_connected(provider, scope):
            # 409, and the client reads it as "offer the studio
            # assistant" -- checked BEFORE the job so a disconnected
            # provider never silently falls back onto Gemini credit.
            return _error(409, "model_not_connected",
                          f"Connect your {provider} account first.")
    elif not _gemini_key(account_id):
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")

    # gated like Create (2026-10-08, the spend holes): a turn is free per
    # click but runs the guide, the reference hunt, the link reader and the
    # story judge -- refused here, before any of them and before an upload
    # is saved, for an account with no plan and no balance
    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    image_refs, ref_urls, _ = await _collect_refs(form, account_id=account_id)
    idea = (form.get("idea") or form.get("prompt") or "").strip()
    # The composer's Image | Video switch (2026-10-04): with it, the turn
    # is a MAKER turn -- the model is handed make_image / make_video and
    # told which one a "make it" means (creative_guide.OUTPUT_NOTES). A
    # proposal naming one comes back unrun, as every write does, and the
    # composer's own send runs it against /generate/run or /scenes/run.
    # The pill sends `still` (2026-10-08): make_image only, drawn behind the
    # same step card and Approve. Absent (older callers), the turn is what
    # it was.
    output = (form.get("output") or "").strip().lower()
    output = output if output in creative_guide.OUTPUT_NOTES else None
    # A skill the person picked from the composer's `/` menu (2026-10-10,
    # src/skills.py): its recipe rides on this turn already loaded. A name
    # that is not on the shelf is no pick at all, never an error -- the
    # menu is drawn off GET /api/skills, and a stale tab must still send.
    from src import skills
    skill = skills.clean_name(form.get("skill"))
    # What this conversation has made, by the numbers the person sees on it
    # (2026-10-11, src/result_refs.py): the model is told the list, and a
    # number its tools name is held to it. Cleaned here like any form field;
    # absent (the dock, an older tab) means no number names anything.
    from src import result_refs
    results = result_refs.clean(form.get("results")) if form.get("results") else None
    # The Guide talks inside the same project a Create would write into
    # (2026-09-28), so its suggestions follow that project's brief and memory.
    project = _form_project(form, account_id)
    if (form.get("project_id") or "").strip() and project is None:
        return _error(404, "no_project", f"no project {form.get('project_id')}")
    if project is not None:
        # where it stands, so "what's next?" is answered from the rows
        # (src/projects.py standing; absent when it cannot be read)
        where = projects.standing(project["id"], account_id=account_id)
        if where:
            project = {**project, "standing": where["line"]}
    # THE PROJECT'S CHAT HISTORY (2026-10-07): a turn inside a project
    # workspace is written to project_messages as it happens -- the
    # person's message and the reply, once there is one -- so reopening
    # the project carries the conversation on where it left off. Only
    # when the client asks (`remember=1`) and only inside a project: the
    # studio-wide thread outside any project stays working memory.
    remember = project is not None and (form.get("remember") or "").strip() in ("1", "true", "on")
    # ... and an ask sent AGAIN ("Switch to Make" on an exploring project's
    # card sends the same message once more) is already in that history:
    # only its new answer is written
    again = (form.get("again") or "").strip() in ("1", "true", "on")
    # EXPLORE (2026-10-11, item 13 of docs/tasks/task-studio-agent.md): read
    # off the PROJECT'S ROW, never off the form -- whatever a page sends, a
    # turn inside a project switched to Explore is handed no tool that makes
    # (guide_tools.session(explore=True)) and is told so. The switch back is
    # the person's own PATCH /api/projects/<id>.
    exploring = bool(project and project.get("explore"))
    # THE AUTONOMY DIAL AND TAPPABLE QUESTIONS (2026-10-22, vesper_v2): only
    # with the flag on is the turn handed ask_choice and told the dial's
    # setting; neither changes what spends (make_plan.runs_unasked holds the
    # rule, the studio's runner holds the same one).
    from src import make_plan
    v2 = vesper_v2_on()
    autonomy = (form.get("autonomy") or "").strip().lower()
    autonomy = autonomy if v2 and autonomy in make_plan.AUTONOMY else None
    # A link the person pasted (2026-10-01, src/linkrefs.py): read off
    # THEIR OWN last message, here, never off a tool argument -- the
    # model never handles a URL (guide_tools.check_args). Its frames go
    # first on reply.sheet; the model is told only that they are there.
    from src import linkrefs
    pasted = linkrefs.extract_links(conversation.messages[-1].content)
    # THE BRAND KIT IN PLAY (2026-10-21, src/brand_kits.py): the project's
    # pick, else one of this account's kits the person named in the
    # conversation. With one, the brain is shown the kit (words, logo, look
    # references) and its reads answer the brand from the kit, never the web.
    picked, refused = _form_kit(form, account_id)
    if refused is not None:
        return refused
    kit = _guide_kit(project, conversation, account_id, picked=picked)
    # THE CLIP MODEL THE PERSON PICKED (2026-10-22): the composer's Video line
    # is Auto (the brain may propose) or one model, which is then theirs. A
    # name the table does not have is Auto, never an error.
    from src import direct, model_menu
    clip_pick = model_menu.video_id(form.get("clip_model"))
    clip_label = direct.video_label(clip_pick) if clip_pick else None

    def work(job):
        result = _guide_turn(job)
        if remember:
            _remember_turn(project["id"], conversation, result["reply"], account_id,
                           again=again)
        return result

    def _guide_turn(job):
        # Grounded through scene_chain.ground -- the same scoped set a
        # Create would be handed (named in the idea, or explicitly
        # picked), so what the guide proposes is shaped by the material
        # a scene could actually be written from. It writes nothing.
        grounding = scene_chain.ground(idea, account_id=account_id,
                                       refs=ref_urls)
        # What this person keeps, per model (src/outcomes.py taste), so a
        # proposal can lean on it. Absent when there is too little to say;
        # first, so the grounding's 24k cut never drops it.
        from src import outcomes
        kept = outcomes.taste(account_id=account_id)
        if kept and isinstance(grounding, dict):
            grounding = {"what_you_keep": kept, **grounding}

        # What the assistant's face reads off the job while the turn runs
        # (2026-10-08, docs/ASSISTANT_AVATARS.md): `detail` is the line under
        # it, `steps` {done, of} fills its arc -- only while a tool can say
        # how far along it is (the reference hunt); a note clears it, so the
        # arc goes back to sweeping -- and `partial` is the answer's own
        # words as the model writes them, for the card to type out.
        def note(text):
            if text:
                jobs.update(job["id"], progress=0.5, detail=text, steps=None)

        def on_step(done, of, text):
            jobs.update(job["id"], progress=done / of if of else 0.5, detail=text,
                        steps={"done": done, "of": of} if of else None)

        def on_text(text):
            jobs.update(job["id"], partial=text)

        if assistant is not None:
            from src import assistant_brain
            note("remembering what you like")
            assistant["memory"] = assistant_brain.memory(account_id)
        links = None
        if pasted:
            from src import assistant_brain
            note("reading the link you pasted")
            links = assistant_brain.link_sheet(pasted, account_id=account_id)
        if personal:
            reply = creative_guide.respond_personal(
                conversation, provider=provider, scope=scope, model=model, grounding=grounding, image_refs=image_refs,
                assistant=assistant, links=links,
                # no "a make it means..." line for a project that is exploring
                output=None if exploring else output, skill=skill, brand_kit=kit)
        else:
            from google import genai
            # The Guide's tools (src/guide_tools.py): READ tools run
            # inside the turn, a WRITE tool comes back as
            # `reply.proposal` for the confirm card, and nothing here
            # spends. local=True for EVERY Guide turn, not just the
            # pill's: find_references comes back as reply.sheet, which
            # both threads draw (2026-10-01).
            tools, run_tool = _guide_tools(account_id, local=True,
                                           maker=output is not None,
                                           makes=creative_guide.MAKES_FOR.get(output or ""),
                                           on_step=on_step, in_project=project is not None,
                                           explore=exploring,
                                           kit=brand_kits.for_project(project) if project else None,
                                           brand_kit=kit, questions=v2)
            reply = creative_guide.respond(
                conversation, client=genai.Client(api_key=_gemini_key(account_id)),
                grounding=grounding, image_refs=image_refs,
                account_id=account_id, on_retry=note, tools=tools, run_tool=run_tool,
                brain=brain, assistant=assistant, links=links, output=output,
                project=project, on_text=on_text, skill=skill, results=results,
                explore=exploring, brand_kit=kit, autonomy=autonomy,
                clip_model=clip_label,
                lone_kit=_lone_kit(account_id) if kit is None and project is None else None)
        # `billing` says WHOSE plan paid: a personal connection spends
        # the person's own ChatGPT/Claude subscription and never touches
        # this install's Gemini credit, and /costs must not count it.
        return {"reply": reply, "reference_urls": ref_urls,
                "billing": "personal_plan" if personal else "studio_credits",
                "brain": None if personal else brain,
                "output": output,
                # what the turn ran as: a page holding an older copy of the
                # project learns here that it is exploring
                "explore": exploring,
                "detail": "ready", "steps": None, "partial": None}

    job = jobs.start("guide", "creative guide", _in_project(project, work),
                     account_id=account_id)
    return {"job_id": job["id"]}


# What a reply carries beside its words, kept with the turn so a reopened
# conversation draws the same cards (src/projects.py project_messages).
_REMEMBERED_REPLY_KEYS = ("proposal", "tool_runs", "choices", "questions",
                          "directions", "nudge", "stage", "brief", "research")


def _remember_turn(project_id: int, conversation, reply: dict, account_id: int,
                   again: bool = False) -> None:
    """The person's last message and the Guide's answer, into the
    project's history. Best-effort: history is bookkeeping on top of a
    turn that already happened, and must never fail it. `again` says the
    message was already written by the turn it repeats: the answer alone."""
    try:
        if not again:
            projects.append_message(project_id, "user", conversation.messages[-1].content,
                                    account_id=account_id)
        extras = {k: reply.get(k) for k in _REMEMBERED_REPLY_KEYS if reply.get(k)}
        projects.append_message(project_id, "assistant", reply.get("message") or "",
                                account_id=account_id, tool_calls=extras or None)
    except Exception as exc:                      # pragma: no cover - never fails the turn
        print(f"  project history not written: {exc}", file=sys.stderr)


def _guide_kit(project, conversation, account_id: int, picked=None):
    """The brand kit a Guide turn works under, or None: the project's pick
    first, then the kit picked in the composer for this conversation
    (2026-10-22), else a kit of this account the person named in their own
    messages (newest first). Never raises."""
    from src import brand_kits
    kit = brand_kits.for_project(project) if project else None
    if kit:
        return kit
    if picked and not project:
        return picked
    said = [m.content for m in conversation.messages if m.role == "user"]
    return brand_kits.named_in(said, account_id=account_id)


def _lone_kit(account_id: int) -> Optional[str]:
    """The name of the account's ONLY brand kit, else None (none, or a
    choice of several). Never raises: the offer is an addition."""
    from src import brand_kits
    try:
        kits = brand_kits.list_kits(account_id=account_id)
    except Exception as exc:
        print(f"  kits not read for the offer: {exc}", file=sys.stderr)
        return None
    return kits[0].get("name") if len(kits) == 1 else None


def _guide_tools(account_id: int, *, local: bool = False,
                 maker: bool = False, makes=None, on_step=None, in_project: bool = False,
                 explore: bool = False, kit=None, brand_kit=None, questions: bool = False):
    """(specs, run_tool) for a Guide turn, or (None, None) when they
    cannot be gathered. Never raises: tools that cannot be offered cost
    the answer its tools, not the person their turn. `local` adds the
    assistant's own tools (find/keep references, the footage search, the
    skills, the project tools); `maker` adds the composer's make_image /
    make_video (guide_tools.MAKE_TOOLS); `on_step` hears the reference
    hunt's progress; `in_project` adds set_project_look (a look is kept
    only where there is a project to keep it); `explore` says that project
    is switched to Explore -- no make tool, and switch_to_make in their
    place; `kit` is the project's brand kit, which adds propose_kit_change.
    No board tools since 2026-10-11, so nothing here opens an MCP server
    any more."""
    from src import guide_tools

    try:
        return guide_tools.session(account_id=account_id, local=local,
                                   maker=maker, makes=makes, on_step=on_step,
                                   in_project=in_project, explore=explore, kit=kit,
                                   brand_kit=brand_kit, questions=questions)
    except Exception as exc:
        print(f"  guide tools unavailable: {exc}", file=sys.stderr)
        return None, None


@router.post("/creative-guide/act")
async def creative_guide_act(request: Request,
                             account_id: int = Depends(auth.current_account_id)):
    """The confirm card's click: run ONE write tool the Guide proposed.

    The model never reaches this -- a proposal comes back off a turn
    unrun, and the person's click is the only thing that posts here.
    Same header guard as the turn (a cross-site form post must not be
    able to write either); the tool must be one `guide_tools.is_write`
    knows, checked again here rather than trusted from the body; and the
    URL rule is enforced by `guide_tools.check_args` on the way in. Runs
    inline: keeping references or creating a project is milliseconds.
    """
    from src import guide_tools

    model_connections.mutation_header(request)
    try:
        body = await request.json()
    except Exception:
        return _error(400, "bad_request", "expected JSON {tool, args}")
    tool = str((body or {}).get("tool") or "")
    args = (body or {}).get("args") or {}
    if not guide_tools.is_write(tool):
        return _error(400, "bad_tool", f"`{tool}` is not an action the Guide can take")
    if guide_tools.is_make(tool) or guide_tools.is_quick(tool):
        # made by the composer's own send against the generation routes
        # (a free edit: against /quick-edit, with the source the page bound)
        # (their price, their charge, their job) -- never off this body
        return _error(400, "bad_tool", f"`{tool}` is made by the studio's send, not here")
    if guide_tools.is_switch(tool):
        # the Explore / Make switch is the project's own (PATCH
        # /api/projects/<id>, the person's click) -- nothing to run here
        return _error(400, "bad_tool", f"`{tool}` is the project's own switch, not an action")
    if guide_tools.is_ask(tool):
        # a tappable question is answered by the person's tap, which is
        # their next message -- nothing to run here
        return _error(400, "bad_tool", f"`{tool}` is a question for you, not an action")
    if not isinstance(args, dict):
        return _error(400, "bad_request", "args must be an object")
    if guide_tools.is_project(tool):
        # PROJECTS ARE MADE THROUGH THE GUIDE (2026-10-07, Mike's call):
        # create_project names one; save_as_project turns the conversation
        # the person has been having into one, carrying its turns and the
        # scenes it made. Both need the thread, which only the client holds
        # -- it rides on this body, bounded, and is user content filed
        # under the account that posts it.
        try:
            result = guide_tools.run_project_tool(
                tool, args, account_id=account_id,
                conversation=(body or {}).get("conversation"),
                scenes=(body or {}).get("scenes"))
        except guide_tools.Refused as exc:
            return _error(400, "refused", str(exc))
        return {"ok": True, "tool": tool, "result": result["summary"],
                "project": result["project"]}
    if guide_tools.is_look(tool):
        # A LOOK SAVED FROM THE CHAT (2026-10-11, item 10 of
        # docs/tasks/task-studio-agent.md): the project is the one the
        # CLIENT is in -- the model never names one -- and it is read under
        # this account, so another account's project is "no project N".
        # `previous` is the look this one replaced: what an Undo puts back.
        try:
            result = guide_tools.run_look_tool(
                args, project_id=(body or {}).get("project_id"), account_id=account_id)
        except guide_tools.Refused as exc:
            return _error(400, "refused", str(exc))
        return {"ok": True, "tool": tool, "result": result["summary"],
                "project": result["project"], "previous": result["previous"]}
    if guide_tools.is_kit(tool):
        # A BRAND KIT CHANGED FROM THE CHAT (2026-10-21): the kit is the one
        # the project the CLIENT is in picked, checked again as it is now;
        # `previous` is the spec it replaced, which an Undo PATCHes back.
        from app.brand_routes import view as kit_view
        try:
            result = guide_tools.run_kit_tool(
                args, project_id=(body or {}).get("project_id"), account_id=account_id)
        except guide_tools.Refused as exc:
            return _error(400, "refused", str(exc))
        return {"ok": True, "tool": tool, "result": result["summary"],
                "kit": kit_view(result["kit"]), "previous": result["previous"]}
    try:
        result = guide_tools.run(tool, args, account_id=account_id)
    except guide_tools.Refused as exc:
        return _error(400, "refused", str(exc))
    if tool == "keep_references":
        # {kept: [{id, url: "/refs/<sha>.jpg", ...}], refused: [...]} --
        # the composer adds each `url` to its asset_photos picks.
        try:
            return {"ok": True, "tool": tool, "result": json.loads(result)}
        except ValueError:
            pass
    return {"ok": True, "tool": tool, "result": result}


# --- the assistant pill's memory (2026-09-29, src/assistant_store.py) --------
# The persona and the open project used to live in the browser (localStorage
# and sessionStorage), so a closed tab lost the conversation and every new
# browser asked for the persona again. The writes carry the same header
# guard as a Guide turn: a cross-site form must not be able to rewrite them.

async def _json_body(request: Request) -> Optional[dict]:
    try:
        body = await request.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


@router.get("/assistant")
def assistant_get(account_id: int = Depends(auth.current_account_id)):
    """The persona (None until set up) and the open project (None until the
    first turn or draft is saved): its turns, step and the composer's draft."""
    from src import assistant_store
    return {"persona": assistant_store.get_persona(account_id=account_id),
            "project": assistant_store.open_project(account_id=account_id)}


@router.put("/assistant/persona")
async def assistant_persona(request: Request,
                            account_id: int = Depends(auth.current_account_id)):
    model_connections.mutation_header(request)
    body = await _json_body(request)
    if body is None:
        return _error(400, "bad_request", "expected JSON {name, avatar, tone}")
    from src import assistant_store
    return {"persona": assistant_store.save_persona(
        body.get("name"), body.get("avatar"), body.get("tone"), account_id=account_id)}


@router.put("/assistant/project")
async def assistant_project_save(request: Request,
                                 account_id: int = Depends(auth.current_account_id)):
    model_connections.mutation_header(request)
    body = await _json_body(request)
    if body is None or not isinstance(body.get("turns"), list):
        return _error(400, "bad_request", "expected JSON {turns: [...], stage, draft?}")
    # the composer's draft rides beside the thread (2026-10-02); a body
    # without one -- or with something that is not an object -- leaves the
    # stored draft alone, so the pill's save never blanks the box
    draft = body.get("draft")
    if draft is not None and not isinstance(draft, dict):
        return _error(400, "bad_request", "draft must be an object")
    from src import assistant_store
    project = assistant_store.save_project(body["turns"], body.get("stage"),
                                           draft=draft, account_id=account_id)
    # the thread and the draft are the client's; echoing them back would
    # double every save
    return {"project": {k: v for k, v in project.items() if k not in ("turns", "draft")}}


@router.delete("/assistant/project")
async def assistant_project_clear(request: Request,
                                  account_id: int = Depends(auth.current_account_id)):
    """Clear the conversation: the row is DELETED, never archived
    (2026-10-02, Mike's call -- a conversation is working memory; what it
    made is on the concept). The pill's button and a finished Create both
    end here."""
    model_connections.mutation_header(request)
    from src import assistant_store
    assistant_store.clear_project(account_id=account_id)
    return {"ok": True}


@router.post("/assistant/project/new")
async def assistant_project_new(request: Request,
                                account_id: int = Depends(auth.current_account_id)):
    """The older name for the same clear, kept for a client that still
    posts it."""
    return await assistant_project_clear(request, account_id)


@router.post("/assistant/reference-verdicts")
async def assistant_reference_verdicts(request: Request,
                                       account_id: int = Depends(auth.current_account_id)):
    """The Keep click, against the checker: one row per frame on the sheet.
    Ids only a hunt served are recorded."""
    model_connections.mutation_header(request)
    body = await _json_body(request)
    if body is None or not isinstance(body.get("frames"), list):
        return _error(400, "bad_request", "expected JSON {frames: [...]}")
    from src import assistant_store
    project = assistant_store.open_project(account_id=account_id)
    n = assistant_store.record_verdicts(body["frames"], account_id=account_id,
                                        project_id=project["id"] if project else None)
    return {"recorded": n, "agreement": assistant_store.agreement(account_id=account_id)}


@router.get("/assistant/reference-agreement")
def assistant_reference_agreement(account_id: int = Depends(auth.current_account_id)):
    from src import assistant_store
    return assistant_store.agreement(account_id=account_id)


def _personal_connected(provider: str, scope) -> bool:
    """Is this person's own model account connected?

    Deliberately the narrow question, not model_connections.provider_status:
    that one also reports whether the CLI is installed and what models
    exist, which is what the settings panel needs and more than a guide
    turn should depend on. Never raises -- an unreachable connection
    reads as not connected, which is the safe answer.
    """
    from src import personal_models

    try:
        if provider == "chatgpt":
            return bool(personal_models.codex_session(scope).status().get("connected"))
        if provider == "claude":
            return bool(personal_models.claude_status(scope).get("connected"))
    except Exception:
        return False
    return False


# --- assets -----------------------------------------------------------------
# Path helpers mirror app/main.py's (photos_for / _entity_photos /
# safe_space_name); duplicated rather than imported to keep main -> api
# a one-way street.

def _slug(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip().replace(" ", "-").lower()
    return cleaned.strip("-.")


def _photo_names(base_dir: Path, folder: str) -> list:
    """An element's photos on disk, the drawn sheet FIRST (2026-10-12,
    Mike's call, reversing 2026-09-18's sheet-last): the sheet is the
    element now -- the card's picture and `refs[0]`, what a clip anchors on."""
    directory = base_dir / folder
    if not directory.is_dir():
        return []
    return element_sheet.sheet_first(
        p.name for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def _sheet_of(photos: list, thumbs: list):
    """(sheet url, sheet thumb) off an element's photo lists, or Nones."""
    for url, thumb in zip(photos, thumbs):
        if element_sheet.is_sheet(str(url).split("?")[0].rsplit("/", 1)[-1]):
            return url, thumb
    return None, None


def _asset_photo_urls(kind: str, base_dir: Path, slug: str,
                      account_id: Optional[int] = None) -> list:
    """One asset's photos, as the URL they ride on everywhere.

    Through asset_shelf rather than an f-string (2026-09-08, Mike: "the
    reference photos aren't appearing"). These strings are not only what
    the gallery draws -- _auto_refs stores them on the shot, and a
    site-relative /characters/... path is true only on the machine
    holding the folder. characters/, props/ and locations/ are
    gitignored AND dockerignored, so the deployed site 404s every one:
    four refs on the row, four empty tiles on the card, and a renderer
    reaching for a face it cannot fetch.

    What is RETURNED is the storable name; `_asset_photo_thumbs` below
    is what the gallery draws. Keeping them apart is the whole point --
    `refs[0]` is the single frame a clip is anchored on, and a list
    that quietly carried 480px versions would anchor the clip on one.
    """
    from src import asset_shelf as _shelf

    # Disk first, so Mike's Mac reads its own photos. When the folder is
    # missing -- the deployed API: characters/ props/ locations/ are
    # gitignored AND dockerignored, so on Fly every asset answered
    # photos: [] and the studio could attach none of them (2026-09-15) --
    # the listing comes from the bucket, under THIS account's keys, as the
    # same storable name photo_url returns.
    #
    # AND ONLY WHERE THE FOLDER IS THIS ACCOUNT'S (2026-10-11, BACKLOG
    # #25). The folder is named by slug alone: `characters/me/` is one
    # folder for every account on the machine, and reading it first
    # listed each of two people who named a character "Me" the other's
    # photo. asset_shelf.folder_is_store is the one rule; everybody else
    # is listed their own bucket keys and nothing from the folder.
    if _shelf.folder_is_store(account_id):
        local = [_shelf.photo_url(kind, slug, fn) for fn in _photo_names(base_dir, slug)]
        if local:
            return local
    return _shelf.r2_photo_urls(kind, slug, account_id)


def _asset_photo_thumbs(urls: list, account_id: Optional[int] = None) -> list:
    """The drawable URL for each of those photos, small where a small
    one exists.

    BACKLOG #0: a Queue card drew four full-size tiles, which off an
    iPhone is a 4.6MB JPEG each -- 18MB to render one card, on a phone,
    to show four thumbnails. The derivative is made at mirror time
    (src/media.mirror) and lives under its own `t/` prefix.

    Falls back to `?thumb=1`, the local handler that has always done
    this off disk, whenever there is no derivative to point at -- R2
    off, a photo added before the migration, a foreign URL. A fallback
    and not a failure: the tile is slow, never missing.
    """
    from src import media

    out = []
    for url in urls:
        small = media.thumb_url_for(url, account_id)
        if small:
            out.append(small)
        elif url.startswith("http"):
            out.append(url)          # no local handler to ask for a thumb
        else:
            out.append(f"{url}?thumb=1")
    return out


def _asset_photo_full(urls: list, account_id: Optional[int] = None) -> list:
    """The full-size URL to DRAW for each of those photos, parallel to
    the list: the address src/media.py mints for this account (the
    bucket when it is configured, the local route when it is not).

    `photos` stays the stored NAME -- it is what goes on a shot, and
    `refs[0]` anchors a clip -- so a page that only wants to show the
    picture large (the element panel's main frame) reads this instead of
    asking the photo route to redirect it there (2026-10-11: that
    redirect pointed at a key the bucket no longer held, and the panel
    drew a dead picture). Never a thumbnail: that is `photo_thumbs`.
    """
    from src import media

    return [media.url_for(url, account_id) for url in urls]


def _location_photos(space: str, account_id: Optional[int] = None) -> list:
    return _asset_photo_urls("location", LOCATIONS_DIR, space, account_id)


def _description_text(desc) -> str:
    """locations.description_json -> one readable paragraph."""
    if isinstance(desc, str):
        try:
            desc = json.loads(desc)
        except (ValueError, TypeError):
            return desc
    if not isinstance(desc, dict):
        return ""
    parts = []
    for key in ("space", "light_sources", "textures", "angles", "constraints"):
        value = desc.get(key)
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        if value:
            parts.append(f"{key.replace('_', ' ')}: {value}")
    return " · ".join(parts)


# Which half of the bank a caller wants (2026-09-18, Mike's call: Assets
# are generated content, Elements are the characters / props / places a
# scene is held to -- two things, not four chips on one wall). `all`
# stays the default so every existing caller and test reads as before.
ASSET_SCOPES = ("all", "elements", "generated")
ELEMENT_CATEGORIES = ("location", "character", "prop")


def _assets_all(account_id: Optional[int] = None, scope: str = "all") -> list:
    if scope not in ASSET_SCOPES:
        scope = "all"
    items = []
    if scope == "generated":
        return _generated_assets(account_id)
    for loc in preprod.list_locations(account_id=account_id):
        photos = _location_photos(loc["name"], account_id)
        thumbs = _asset_photo_thumbs(photos, account_id)
        sheet, sheet_thumb = _sheet_of(photos, thumbs)
        items.append({
            "id": f"location-{loc['id']}", "category": "location",
            "name": loc["name"], "photos": photos, "photo_thumbs": thumbs,
            "photo_full": _asset_photo_full(photos, account_id),
            "poster": sheet_thumb or (thumbs[0] if thumbs else None),
            "sheet": sheet,
            "text": _description_text(loc.get("description")
                                      or loc.get("description_json") or ""),
            "meta": {"photo_count": loc.get("photo_count")},
            "created_at": loc.get("created_at"),
        })
    for c in entities.list_characters(account_id=account_id):
        slug = _slug(c["name"])
        photos = _asset_photo_urls("character", CHARACTERS_DIR, slug, account_id)
        thumbs = _asset_photo_thumbs(photos, account_id)
        sheet, sheet_thumb = _sheet_of(photos, thumbs)
        items.append({
            "id": f"character-{c['id']}", "category": "character",
            "name": c["name"], "photos": photos, "photo_thumbs": thumbs,
            "photo_full": _asset_photo_full(photos, account_id),
            "poster": sheet_thumb or (thumbs[0] if thumbs else None),
            "sheet": sheet,
            "text": c.get("notes") or c.get("role") or "",
            "meta": {"role": c.get("role")},
            "created_at": c.get("created_at"),
        })
    for p in entities.list_props(account_id=account_id):
        slug = _slug(p["name"])
        photos = _asset_photo_urls("prop", PROPS_DIR, slug, account_id)
        thumbs = _asset_photo_thumbs(photos, account_id)
        sheet, sheet_thumb = _sheet_of(photos, thumbs)
        items.append({
            "id": f"prop-{p['id']}", "category": "prop",
            "name": p["name"], "photos": photos, "photo_thumbs": thumbs,
            "photo_full": _asset_photo_full(photos, account_id),
            "poster": sheet_thumb or (thumbs[0] if thumbs else None),
            "sheet": sheet,
            "text": p.get("notes") or p.get("category") or "",
            "meta": {"kind": p.get("category")},
            "created_at": p.get("created_at"),
        })
    if scope == "all":
        items.extend(_generated_assets(account_id))
    return items


def _project_of(meta: dict, linked: dict, filed_titles: dict) -> tuple:
    """(project id, title) for one render on the wall: its scene's
    project, else the project it was filed under when made -- if that
    project is still this account's -- else (None, None)."""
    scene = linked.get(meta.get("concept_id"))
    if scene:
        return scene.get("id"), scene.get("title")
    pid = meta.get("project_id")
    if pid in filed_titles:
        return pid, filed_titles[pid]
    return None, None


def _generated_assets(account_id: Optional[int]) -> list:
    from src import drafts, media
    items = []
    rows = render_assets.list_all(account_id=account_id)
    try:
        # the clips that are a cheap draft still sitting on their shot
        drafted = drafts.on_the_wall(rows, account_id=account_id)
    except Exception:                                       # noqa: BLE001
        drafted = {}                # a label, never a reason to lose the wall
    for rendered in rows:
        url = rendered["media_url"]
        kind = rendered["media_kind"]
        meta = {
            "provider": rendered["provider"],
            "model": rendered["model"],
            "type": kind,
        }
        for key in ("ratio", "duration", "resolution", "references", "source", "framing",
                    "prompt_image", "project_id"):
            if rendered["metadata"].get(key) is not None:
                meta[key] = rendered["metadata"][key]
        for key in ("project", "concept_id", "shot_n"):
            if rendered.get(key) is not None:
                meta[key] = rendered[key]
        items.append({
            "id": f"generated-{rendered['id']}", "category": "generated",
            "generated_id": rendered["id"],
            "name": f"{rendered['provider']} {kind}",
            "photos": [url] if kind == "image" else [],
            "media": [{"url": url, "kind": kind}],
            "media_url": url, "media_kind": kind,
            # a clip's poster is its t/ derivative (media.mirror_poster at
            # publish time); None when R2 is off or it predates 2026-09-28
            "poster": url if kind == "image" else media.thumb_url_for(url, account_id),
            "text": rendered["prompt"], "meta": meta,
            "folder": rendered.get("folder"),
            "starred": bool(rendered.get("starred")),
            "created_at": rendered.get("created_at"),
            # a clip rendered at its model's cheapest tier that is still
            # the clip on its shot (src/drafts.py): {"frame", "model"} or None
            "draft": drafted.get(rendered["id"]),
        })
    return items


def _element_key(item: dict) -> Optional[tuple]:
    """(kind, slug) for an element, the way its photos' URLs name it --
    asked of asset_shelf.parse_ref, THE parser, so a local route, a flat
    R2 URL and a storable name all read the same. An element with no
    photo falls back to the folder its photos would live under."""
    for url in item.get("photos") or []:
        ref = asset_shelf.parse_ref(url)
        if ref and ref["kind"] == item["category"]:
            return (ref["kind"], ref["slug"])
    if item["category"] == "location":
        return ("location", item["name"])
    if item["category"] in ("character", "prop"):
        return (item["category"], _slug(item["name"]))
    return None


def _count_uses(items: list, account_id: int) -> None:
    """`used_in` on each element: how many open concepts' refs name it
    (2026-09-25). The Elements page computed this in the browser from
    the whole board -- ~0.9 MB of database egress for a number per card
    -- with a regex that only matched the old local `/characters/<slug>/`
    shape, so every canonical R2 ref counted as nothing. Same window as
    that board read (the newest 100 of the account, all brands, not
    archived), now off preprod.board_index's refs alone."""
    uses: dict = {}
    for row in preprod.board_index(account_id=account_id, refs=True):
        named = set()
        for url in row["refs"]:
            ref = asset_shelf.parse_ref(url) if isinstance(url, str) else None
            if ref and ref["kind"] != "refs":
                named.add((ref["kind"], ref["slug"]))
        for key in named:
            uses[key] = uses.get(key, 0) + 1
    for item in items:
        key = _element_key(item)
        if key:
            item["used_in"] = uses.get(key, 0)


@router.get("/assets")
def assets_list(q: Optional[str] = None, category: Optional[str] = None,
                limit: int = 200, scope: str = "all",
                account_id: int = Depends(auth.current_account_id),
):
    items = _assets_all(account_id, scope)
    if scope == "elements":
        _count_uses(items, account_id)
    counts = {"all": len(items)}
    for cat in ("location", "character", "prop", "generated"):
        counts[cat] = sum(1 for i in items if i["category"] == cat)
    if category in ("location", "character", "prop", "generated"):
        items = [i for i in items if i["category"] == category]
    if q:
        needle = q.lower().strip()
        items = [i for i in items
                 if needle in (i["name"] + " " + (i["text"] or "")).lower()]
    return {"items": items[:limit], "total": len(items), "counts": counts}


@router.get("/media")
def media_list(q: Optional[str] = None, category: Optional[str] = None,
               kind: str = "image", limit: int = 500, scope: str = "all",
               folder: Optional[str] = None, starred: bool = False,
               provider: Optional[str] = None,
               account_id: int = Depends(auth.current_account_id)):
    """This account's saved media as one flat, newest-first list.

    Image-only is the safe default because this endpoint also feeds image
    reference pickers.  The Asset Bank requests ``kind=all`` so generated
    clips appear in its gallery without being offered as still-image
    inputs to Nano or a renderer. Photo dates come from the file on disk;
    generated media from its record.
    """
    from datetime import datetime, timezone

    # `media` below is each asset's list, so the module goes by _media
    from src import media as _media
    from src import model_menu

    items = []
    assets = _assets_all(account_id, scope)
    # a photo's date is read off the folder only where the folder is this
    # account's (asset_shelf.folder_is_store): it is shared by name, and
    # the file there may be another account's. Elsewhere the listing came
    # from the account's own bucket keys and only the date is unknown.
    own_folder = asset_shelf.folder_is_store(account_id)
    # which project each render's scene sits in (2026-10-07): one query
    # for the wall, so a solo render says "no project" rather than nothing
    linked = projects.for_concepts(
        [(a.get("meta") or {}).get("concept_id") for a in assets
         if a["category"] == "generated"], account_id=account_id)
    # ...and a render no scene carries, filed under a project when it was
    # made (the MCP's project_id, 2026-10-08): titled in one more query,
    # only when there is one, and only for this account's projects
    filed = [(a.get("meta") or {}).get("project_id") for a in assets
             if a["category"] == "generated"
             and not linked.get((a.get("meta") or {}).get("concept_id"))]
    filed_titles = (projects.titles(filed, account_id=account_id)
                    if any(filed) else {})
    for asset in assets:
        generated = asset["category"] == "generated"
        media = asset.get("media") or [
            {"url": url, "kind": "image"} for url in asset["photos"]]
        for entry in media:
            url = entry["url"]
            media_kind = entry.get("kind", "image")
            if kind != "all" and media_kind != kind:
                continue
            if generated:
                try:
                    mtime = datetime.fromisoformat(
                        str(asset.get("created_at") or "").replace("Z", "+00:00"))
                    if mtime.tzinfo is None:
                        mtime = mtime.replace(tzinfo=timezone.utc)
                except ValueError:
                    mtime = datetime.now(timezone.utc)
            else:
                target = _resolve_asset_photo(url) if own_folder else None
                if target is None:
                    # Not on THIS disk. Once a photo's canonical URL is
                    # its R2 one (2026-09-08) that is the normal case on
                    # any machine but the one that saved it -- dropping
                    # it here would empty the reference picker on the
                    # deployed site while /api/assets listed the same
                    # photo happily. It is only the sort date that is
                    # unknown, so it sorts oldest rather than vanishing.
                    if own_folder and not str(url).startswith("http"):
                        continue
                    mtime = datetime.fromtimestamp(0, tz=timezone.utc)
                else:
                    mtime = datetime.fromtimestamp(target.stat().st_mtime,
                                                    tz=timezone.utc)
            row = {
                "url": url, "asset_id": asset["id"],
                "asset_name": asset["name"], "category": asset["category"],
                "kind": media_kind,
                "haystack": (asset["name"] + " " + (asset["text"] or "")).lower(),
                "date": mtime.date().isoformat(),
                "ts": mtime.timestamp(),
            }
            if generated:
                # what the Assets wall organizes by (2026-09-18)
                meta = asset.get("meta") or {}
                row.update({
                    "generated_id": asset.get("generated_id"),
                    "provider": meta.get("provider"),
                    "model": meta.get("model"),
                    # the model's public name ("FLUX.2 Pro"), what the viewer
                    # is titled with -- never the host ("fal"); None when no
                    # table knows the id (2026-10-20)
                    "model_label": model_menu.label_for(meta.get("model")),
                    "concept_id": meta.get("concept_id"),
                    "shot_n": meta.get("shot_n"),
                    # the project its scene is filed under, or None: a
                    # video made outside any project lands here and on no
                    # board (2026-10-07, Mike's call)
                    "project_id": _project_of(meta, linked, filed_titles)[0],
                    "project_title": _project_of(meta, linked, filed_titles)[1],
                    "prompt": asset.get("text") or "",
                    "folder": asset.get("folder"),
                    "starred": bool(asset.get("starred")),
                    "poster": asset.get("poster") if media_kind == "video" else None,
                    # a still's 480px thumbnail for the wall's tiles
                    # (2026-10-19): None when R2 has none, and the tile
                    # draws the master; the viewer always draws `url`
                    "thumb": (_media.thumb_url_for(url, account_id)
                              if media_kind == "image" else None),
                    # when it was made, for the viewer's Created row
                    "created_at": (str(asset["created_at"])
                                   if asset.get("created_at") else None),
                    # {"frame", "model"} when this clip is a cheap draft of
                    # its shot (src/drafts.py), else None
                    "draft": asset.get("draft"),
                })
            items.append(row)
    items.sort(key=lambda x: x["ts"], reverse=True)
    # counts are set totals, before any filter -- same rule as /api/assets
    counts = {"all": len(items)}
    for cat in ("location", "character", "prop", "generated"):
        counts[cat] = sum(1 for i in items if i["category"] == cat)
    # the Assets wall's own tallies (2026-09-18), beside `counts` rather
    # than inside it so the category contract above is unchanged
    wall = {"image": sum(1 for i in items if i["kind"] == "image"),
            "video": sum(1 for i in items if i["kind"] == "video"),
            "starred": sum(1 for i in items if i.get("starred"))}
    folders: dict = {}
    providers: dict = {}
    for i in items:
        if i.get("folder"):
            folders[i["folder"]] = folders.get(i["folder"], 0) + 1
        if i.get("provider"):
            providers[i["provider"]] = providers.get(i["provider"], 0) + 1
    if category in ("location", "character", "prop", "generated"):
        items = [i for i in items if i["category"] == category]
    if folder:
        items = [i for i in items if i.get("folder") == folder]
    if starred:
        items = [i for i in items if i.get("starred")]
    if provider:
        items = [i for i in items if i.get("provider") == provider]
    if q:
        needle = q.lower().strip()
        items = [i for i in items if needle in i["haystack"]]
    for item in items:
        item.pop("haystack", None)
    return {"items": items[:limit], "counts": counts, "wall": wall,
            "folders": dict(sorted(folders.items())),
            "providers": dict(sorted(providers.items()))}


@router.get("/assets/search")
def assets_search(q: str = "", limit: int = 8, account_id: int = Depends(auth.current_account_id)):
    """Cross-category name search over characters/props/locations -- the
    `@` mention autocomplete's endpoint. Name-prefix matches rank first,
    substring matches after; slim rows (name, category, thumb) because
    the dropdown needs nothing heavier."""
    needle = q.lower().strip()
    # an @-mention is an element by definition: a render is not a thing
    # a shot can be held to, and `@runway-image` was showing up here
    items = _assets_all(account_id, "elements")
    if needle:
        starts = [i for i in items if i["name"].lower().startswith(needle)]
        start_ids = {i["id"] for i in starts}
        contains = [i for i in items
                    if needle in i["name"].lower() and i["id"] not in start_ids]
        items = starts + contains
    return {"items": [{"name": i["name"], "category": i["category"],
                       "thumb": i["poster"]}
                      for i in items[:max(1, min(limit, 20))]]}


def _drawable(raw: Optional[str], account_id: Optional[int]) -> Optional[str]:
    """A stored reference as something an <img> can draw, small where a
    small one exists: `_ref_thumbs`' choice, minted through media.url_for
    when it fell back to the stored string (a logical name is not a URL
    on the tenant rung)."""
    from src import media

    if not raw:
        return None
    small = _ref_thumbs([raw], account_id)[0]
    return small if small != raw else media.url_for(raw, account_id)


def _element_photos(kind: str, name: str, account_id: Optional[int]) -> list:
    """An element's photos by the kind the Elements page names it."""
    if kind == "place":
        return _location_photos(name, account_id)
    if kind == "character":
        return _asset_photo_urls("character", CHARACTERS_DIR, _slug(name), account_id)
    return _asset_photo_urls("prop", PROPS_DIR, _slug(name), account_id)


@router.get("/search")
def global_search(q: str = "", limit: int = 5, account_id: int = Depends(auth.current_account_id)):
    """The ⌘K palette's one question (2026-10-08, src/search.py): projects,
    scenes (title and PROMPT), elements, renders and cuts that match every
    word of `q`, for this account, each group capped at `limit`. An empty
    `q` is the recent list. Slim rows with one drawable thumbnail each --
    the palette needs a face, not a gallery. Reads only; nothing spends."""
    from src import media, search

    out = search.run(q, account_id=account_id, limit=limit)
    groups = out["groups"]
    for item in groups["projects"] + groups["scenes"]:
        item["thumb"] = _drawable(item.pop("cover", None), account_id)
    for item in groups["elements"]:
        photos = _element_photos(item["kind"], item["name"], account_id)
        item["frames"] = len(photos)
        item["thumb"] = _asset_photo_thumbs(photos[:1], account_id)[0] if photos else None
    for item in groups["renders"]:
        url = item.pop("media_url", None) or ""
        item["thumb"] = (None if not url else _drawable(url, account_id) if item["kind"] == "image"
                         else media.thumb_url_for(url, account_id))
    return out


# Registered BEFORE /assets/{category}/{item_id} on purpose: that route would
# otherwise take "generated" for a category and answer for these two.
def _download_name(row: dict) -> str:
    """`phantra-<what made it>-<id>.<ext>`, plain ASCII: the name the
    browser saves a render under."""
    import re
    from urllib.parse import urlparse
    suffix = Path(urlparse(row.get("media_url") or "").path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{2,5}", suffix or ""):
        suffix = ".mp4" if row.get("media_kind") == "video" else ".png"
    label = re.sub(r"[^a-z0-9]+", "-", str(row.get("provider") or "render").lower()).strip("-")
    return f"phantra-{label or 'render'}-{row['id']}{suffix}"


# registered before /assets/generated/{asset_id}, which would take "trash"
# for an id and answer 422
@router.get("/assets/generated/trash")
def generated_trash(account_id: int = Depends(auth.current_account_id)):
    from src import media as _media
    storage_quota.purge_due(account_id)
    items = []
    for row in storage_quota.trashed(account_id):
        url, kind = row["media_url"], row["media_kind"]
        items.append({
            "generated_id": row["id"], "kind": kind, "url": _media.url_for(url, account_id),
            "poster": (_media.url_for(url, account_id) if kind == "image"
                       else _media.thumb_url_for(url, account_id)),
            "provider": render_assets._label(row["tool"], row["model"]),
            "prompt": row.get("prompt"), "deleted_at": row["deleted_at"],
            "purge_at": row["purge_at"],
        })
    return {"items": items, "trash_days": storage_quota.TRASH_DAYS}


@router.get("/assets/generated/{asset_id}")
def asset_get_generated(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """One render on the wall, for a page that was handed only its id (the
    composer's `?on=gen:<id>`, 2026-10-10): what it is, a tile to draw and
    the `ref` an effect names it by. 404 for a removed render or another
    account's."""
    from src import media
    row = render_assets.get(asset_id, account_id=account_id)
    if not row or row.get("deleted_at"):
        return _error(404, "not_found", "no such generated asset")
    url, kind = row["media_url"], row["media_kind"]
    full = media.url_for(url, account_id)
    # the small derivative when one exists; a still is its own tile, a clip
    # with no poster has none
    thumb = media.thumb_url_for(url, account_id) or (full if kind == "image" else None)
    from src import drafts
    return {"id": asset_id, "ref": f"gen:{asset_id}", "kind": kind, "url": full,
            "thumb": thumb, "label": row.get("provider") or "",
            "prompt": row.get("prompt") or "",
            "concept_id": row.get("concept_id"),
            "draft": drafts.on_the_wall([row], account_id=account_id).get(asset_id)}


@router.get("/assets/generated/{asset_id}/download")
def asset_download_generated(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """Save a render to the person's computer (2026-10-10). The wall's
    button only ever OPENED the file: a browser ignores `download` on a
    link to another origin, and the bucket is one. So the bucket is asked
    to send it as an attachment -- a 302 to a five-minute presigned URL,
    the bytes going bucket -> browser -- and a machine with no bucket
    serves its own file. 404 for a removed render, another account's, or
    one whose file is nowhere."""
    from fastapi.responses import FileResponse, RedirectResponse

    from src import media, storage
    row = render_assets.get(asset_id, account_id=account_id)
    if not row or row.get("deleted_at"):
        return _error(404, "not_found", "no such generated asset")
    name = _download_name(row)
    if storage.configured():
        for key in dict.fromkeys(k for k in (media.master_key(row["media_url"], account_id),
                                             media.legacy_key(row["media_url"])) if k):
            if storage.key_exists(key):
                url = storage.download_url_for_key(key, name)
                if url:
                    outcomes.record("download", asset_id=asset_id, account_id=account_id,
                                    source="library")
                    return RedirectResponse(url, status_code=302)
    # this machine's own copy: only ever a file under data/renders
    root = (Path(__file__).resolve().parent.parent / "data" / "renders").resolve()
    local = Path(row.get("output_path") or "")
    try:
        target = local.resolve() if local.is_absolute() else (root.parent.parent / local).resolve()
    except OSError:
        target = None
    if target and root in target.parents and target.is_file():
        outcomes.record("download", asset_id=asset_id, account_id=account_id, source="library")
        return FileResponse(str(target), filename=name)
    return _error(404, "no_file", "that render's file is not in the studio's storage")


@router.get("/assets/{category}/{item_id}")
def asset_detail(category: str, item_id: int, account_id: int = Depends(auth.current_account_id)):
    asset = next((i for i in _assets_all(account_id)
                  if i["id"] == f"{category}-{item_id}"), None)
    if asset is None:
        return _error(404, "not_found", "no such asset")
    return asset


# --- asset creation ----------------------------------------------------------
# The always-on create path (2026-08-26): /ui's Assets view creates
# entities through these, so asset creation survives a public deploy
# where the dev console (and its old form routes) is never registered.
# Every save also lands a small text chunk on the RAG "assets" shelf --
# the upload IS the grounding source, closing the gap where the memory
# bank and the vector library sat side by side without talking.

ASSETS_DOMAIN = asset_shelf.DOMAIN

# The shelf's format and source keys live in src/asset_shelf.py so this
# route and the backfill there write identical chunks -- two formats on
# one shelf means a re-ingest duplicates instead of replacing.
ingest_asset_chunk = asset_shelf.ingest_one
_drop_asset_chunk = asset_shelf.drop_one


def describe_entity_photos(kind: str, name: str, photos: list,
                           account_id: Optional[int] = None) -> dict:
    """The vision step for a character or prop, mirroring what a
    location has always got on upload. This is what makes the asset
    *searchable*: the RAG library is text-only, so an undescribed
    character retrieves on its typed name alone, never on how it looks.

    Never raises -- a failed vision call must not lose the photos or
    the entity row, exactly the locations contract."""
    api_key = _gemini_key(account_id)
    if not (api_key and photos):
        return {"ok": False, "description": None,
                "error": "no photos" if api_key else "no Gemini key"}
    try:
        from google import genai

        from src import locations as locations_mod
        description = locations_mod.describe_entity(
            genai.Client(api_key=api_key), kind, name, photos)
        return {"ok": True, "description": description, "error": None}
    except Exception as e:
        return {"ok": False, "description": None, "error": str(e)}


def _mirror_photos_to_r2(plural: str, slug: str, saved,
                         account_id: Optional[int] = None) -> int:
    """Push newly saved asset photos up, best-effort. Returns how many
    reached the bucket (0 when R2 is off), for the one caller that must
    know: a photo kept nowhere else (`_photo_folder`).

    The counterpart of asset_shelf.photo_url returning an R2 URL: a
    photo added after the 2026-09-08 backfill would otherwise be handed
    out under a URL whose object was never uploaded -- a broken tile
    that looks exactly like the bug this whole change fixes, only newer.

    Delegates to `src/media.mirror`, which owns the key scheme and makes
    the 480px derivative. This function used to build the key itself,
    alongside refbin doing the same thing differently; the account
    prefix is exactly the kind of change that would have landed in one
    of them and not the other.
    """
    from src import media
    sent = 0
    for target in saved:
        if media.mirror(target, f"{plural}/{slug}/{target.name}", account_id,
                        content_type="image/jpeg"):
            sent += 1
            # the same name written again (a sheet redrawn, a photo
            # uploaded twice): the next read is of these bytes
            asset_shelf.forget_cached(f"/{plural}/{slug}/photo/{target.name}", account_id)
    return sent


def _photos_from_urls(directory: Path, urls,
                      account_id: Optional[int] = None) -> list:
    """"Make element" from the Assets wall (2026-09-18): a render's URL
    handed to a create route instead of an upload. The bytes come
    through _photo_bytes (disk first, SSRF-guarded fetch second) and
    are written beside the uploads under a content-hashed name, so the
    same render promoted twice is one file. A URL that yields nothing
    is skipped, never an error -- the element still saves. `account_id`
    is whose bucket keys a stored name is read under."""
    import hashlib
    saved = []
    for url in urls or []:
        url = str(url or "").strip()
        if not url:
            continue
        data = _photo_bytes(url, account_id)
        if not data:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        ext = Path(url.split("?")[0]).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            ext = ".jpg"
        target = directory / f"gen-{hashlib.sha1(data).hexdigest()[:16]}{ext}"
        if not target.exists():
            target.write_bytes(data)
        saved.append(target)
    return saved


def _write_photos(directory: Path, uploads) -> list:
    """(filename, bytes) pairs written under `directory`; the paths."""
    saved = []
    for filename, data in uploads or []:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / Path(filename).name
        target.write_bytes(data)
        saved.append(target)
    return saved


async def _read_uploads(photos) -> list:
    """A form's image uploads as (filename, bytes) pairs -- the one await
    in a create, done by the route so the body below is a plain function
    the connector can call too."""
    return [(p.filename, await p.read()) for p in photos
            if getattr(p, "filename", "") and (p.content_type or "").startswith("image/")]


def _save_uploaded_photos(directory: Path, plural: str, slug: str, uploads,
                          account_id: Optional[int] = None,
                          photo_urls=None, into: Optional[list] = None,
                          must_mirror: bool = False) -> tuple:
    """(first filename, count) -- mirrors the old dev-console handler.
    `uploads` are (filename, bytes) pairs, written under `directory`.
    `into`, when given, is extended with the paths THIS request wrote
    (the sheet is drawn from those, not from an older folder's).
    `must_mirror` is for a photo kept nowhere but the bucket."""
    saved = _write_photos(directory, uploads)
    saved += _photos_from_urls(directory, photo_urls, account_id)
    if into is not None:
        into.extend(saved)
    if not saved:
        return "", 0
    _mirror_or_refuse(plural, slug, saved, account_id, must_mirror)
    return saved[0].name, len(saved)


def _mirror_or_refuse(plural: str, slug: str, saved, account_id: Optional[int],
                      must_mirror: bool) -> None:
    mirrored = _mirror_photos_to_r2(plural, slug, saved, account_id)
    if must_mirror and mirrored < len(saved):
        # the bucket was to be the ONLY copy, and it is not there
        raise ElementRefused(503, "not_saved",
                             "the picture could not be saved just now -- try again")


@contextmanager
def _photo_folder(base_dir: Path, slug: str, private: bool):
    """Where one create writes its photos: the element's folder -- or,
    when `private`, a folder that is gone when the create returns.

    The element folders are named by slug alone, so `characters/me/` is
    ONE folder for every account on the machine (asset_shelf.
    bucket_is_store says why that matters). A create by an account the
    folder is not the store of therefore keeps nothing here: the photo
    goes to the account's own keys and is read back from them, like
    every photo on the deployed machine after its next restart."""
    if not private:
        yield base_dir / slug
        return
    with tempfile.TemporaryDirectory(prefix="element-") as tmp:
        yield Path(tmp) / slug


def _keeps_no_folder(account_id: Optional[int], strict: bool) -> bool:
    """Does this create keep NOTHING in the element folder?

    Yes for every account the folder is not the store of (2026-10-11,
    docs/BACKLOG.md #25: asset_shelf.folder_is_store -- on the deployed
    API that is everybody), from the Elements page and the composer as
    much as from the connector. And yes for a connector create wherever
    the bucket is the per-account store, the folder's owner included:
    every reader on that surface lists bucket keys only
    (mcp_server._catalogue), so a file left in the folder would be a
    photo its own caller could not see."""
    return (not asset_shelf.folder_is_store(account_id)
            or (strict and asset_shelf.bucket_is_store(account_id)))



# What the page is told when an element was saved and its photos could not
# be read by the model just now (no key, a busy model, a refusal): the
# element is real and usable, so the line says that and no provider's
# words (2026-10-10; the raw error is in the log).
NOT_DESCRIBED = "the photos are saved, but could not be described just now"

# ONE CREATE BODY, TWO DOORS (2026-10-11, docs/tasks/task-connector-elements.md).
# The Elements page posts a form; the connector's `add_element` hands over
# one picture it has already fetched and checked (src/mcp_server.py). Both
# run `create_element`, so a photo added from a chat is saved, mirrored,
# described, filed and shelved exactly as one uploaded in the studio. The
# routes read the form and translate a refusal to the JSON error they
# always sent; the mount translates it for a tool (app/mcp_mount.py).
#
# `strict` is the connector's: its caller needs an element that EXISTS with
# a photo on it, or a refusal -- so a picture that could not be saved
# refuses before any row is written (the page keeps a photo-less character,
# which is a thing a person can mean), a place is recorded even when it
# could not be described (the page leaves the photos for a later describe),
# and a name the account already has gains the photo instead of a second
# row of the same name.
#
# AND NOTHING IS KEPT IN A FOLDER THAT IS NOT THE ACCOUNT'S (2026-10-11,
# docs/BACKLOG.md #25). The element folders are shared by name, so a create
# by any account the folder is not the store of -- from either door --
# writes a folder that is gone when it returns, REFUSES when the bucket did
# not take the file (it was to be the only copy), and describes only what
# it just wrote (`_keeps_no_folder`, `_photo_folder`).

def _gate_or_refuse(account_id: Optional[int]) -> None:
    """`_create_gate` for a body that raises: saving an element describes
    its photos (a vision call) and teaches the RAG shelf (an embedding)."""
    refused = _create_gate(account_id)
    if refused is not None:
        err = json.loads(refused.body)["error"]
        raise ElementRefused(refused.status_code, err["code"], err["message"])


def _existing_cast(kind: str, slug: str, account_id: Optional[int]) -> Optional[dict]:
    rows = (entities.list_characters(account_id=account_id) if kind == "character"
            else entities.list_props(account_id=account_id))
    return next((r for r in rows if _slug(r["name"]) == slug), None)


def _create_location(name: str, *, account_id: Optional[int], notes: str = "",
                     uploads=(), photo_urls=(), sheet: bool = False,
                     strict: bool = False) -> dict:
    """Save a space's photos and describe it (vision) -- the describe is
    best-effort so a failed model call keeps the photos on disk to
    retry, exactly the old /locations/upload contract."""
    slug = _slug((name or "").strip())
    if not slug:
        raise ElementRefused(400, "invalid_name", "a space name is required")
    uploads = list(uploads or [])
    photo_urls = [u for u in photo_urls or [] if str(u or "").strip()]
    if not uploads and not photo_urls:
        raise ElementRefused(400, "no_photos", "at least one photo is required")
    # gated like Create (2026-10-08)
    _gate_or_refuse(account_id)

    private = _keeps_no_folder(account_id, strict)
    known = (preprod.get_location_by_name(slug, account_id=account_id)
             if strict else None)
    described = False
    note = None
    description = None
    with _photo_folder(LOCATIONS_DIR, slug, private) as space_dir:
        space_dir.mkdir(parents=True, exist_ok=True)
        saved = _write_photos(space_dir, uploads)
        saved += _photos_from_urls(space_dir, photo_urls, account_id)
        if not saved:
            raise ElementRefused(400, "no_photos", "none of the photos could be read")
        # "Make element": a render that became a reference was kept
        outcomes.record_refs("element_from", photo_urls, account_id=account_id,
                             source="elements")
        _mirror_or_refuse("locations", slug, saved, account_id, private)

        api_key = _gemini_key(account_id)
        photo_count = len(saved) if private else len(sorted(
            p for p in space_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS))
        if known is not None and known.get("description"):
            # a place the connector's caller already has, already described:
            # it gains the photo and keeps its description
            described = True
        elif not api_key:
            note = NOT_DESCRIBED
        else:
            try:
                from google import genai

                from src import locations as locations_mod
                description = locations_mod.describe_location(
                    genai.Client(api_key=api_key), slug, saved)
                preprod.add_location(slug, description,
                                     photo_count=photo_count, account_id=account_id)
                described = True
            except Exception as e:
                # the model's own words go to the log, never to the page
                print(f"  could not describe location {slug}: {e}", file=sys.stderr)
                note = NOT_DESCRIBED
    if strict and not described and known is None:
        # the connector's caller needs the place to be listed; an earlier
        # description is never overwritten with an empty one
        preprod.add_location(slug, {}, photo_count=photo_count,
                             notes=notes or None, account_id=account_id)
    if known is not None and known.get("description"):
        description = known["description"]

    chunk = ingest_asset_chunk("location", slug, slug,
                               {"description": description or {}},
                               project=accounts.slug_of(account_id),
                               account_id=account_id)
    # the connector never draws (a sheet is its quoted tool); the page's
    # own create does, from the account's own photos wherever they live
    sheet_job = _maybe_sheet_job(sheet and not (strict and private), "locations",
                                 slug, slug, notes=notes, account_id=account_id,
                                 photos=saved if private else None)
    return {"ok": True, "slug": slug, "described": described,
            "photos": len(saved), "note": note, "rag": chunk,
            "sheet_job": sheet_job}


def _create_cast(kind: str, name: str, *, account_id: Optional[int], field: str = "",
                 notes: str = "", uploads=(), photo_urls=(), sheet: bool = False,
                 strict: bool = False) -> dict:
    """Characters and props are the same shape: name + one labelled
    field + notes + photos. Save the photos, describe them (vision, so
    appearance is retrievable), store the row, put it on the shelf."""
    base_dir = CHARACTERS_DIR if kind == "character" else PROPS_DIR
    label = "role" if kind == "character" else "category"

    name = (name or "").strip()
    slug = _slug(name)
    if not slug:
        raise ElementRefused(400, "invalid_name", "a name is required")
    # gated like Create (2026-10-08): see _create_location
    _gate_or_refuse(account_id)
    field = (field or "").strip()
    notes = (notes or "").strip()
    photo_urls = list(photo_urls or [])
    plural = "characters" if kind == "character" else "props"
    existing = _existing_cast(kind, slug, account_id) if strict else None
    private = _keeps_no_folder(account_id, strict)
    fresh: list = []
    with _photo_folder(base_dir, slug, private) as directory:
        ref, count = _save_uploaded_photos(directory, plural, slug, uploads, account_id,
                                           photo_urls=photo_urls, into=fresh,
                                           must_mirror=private)
        if strict and not count:
            raise ElementRefused(400, "no_photos", "the picture could not be read")
        if count:       # "Make element": a render that became a reference was kept
            outcomes.record_refs("element_from", photo_urls,
                                 account_id=account_id, source="elements")

        if existing is not None and existing.get("description"):
            # the same name again from the connector, already described: the
            # element gains the photo and keeps its description
            vision = {"ok": True, "description": None, "error": None}
        else:
            # resolved against THIS route's base_dir, not asset_shelf's module
            # constant -- they're the same in production, but the photos that
            # were just written are the ones to describe. A private create
            # describes what it wrote: the shared folder is not its to read.
            saved_photos = (list(fresh) if private else
                            [base_dir / slug / n for n in _photo_names(base_dir, slug)])
            vision = describe_entity_photos(kind, name, saved_photos, account_id)
    description = dict(vision["description"] or {})
    if existing is not None:
        # an element's notes are its own, not the caption of its newest photo
        notes = existing.get("notes") or notes
    if notes:
        description["notes"] = notes

    if existing is not None:
        # the same name again from the connector: the photo joins that
        # element (its folder is the name's), never a second row -- and the
        # shelf chunk below is rewritten from what the element already
        # says about itself plus what is new, never from the new part alone
        before = existing.get("description") or {}
        description = {**before, **description}
        if description != before:
            entities.set_description(kind, existing["id"], description,
                                     account_id=account_id)
        name = existing["name"]
        field = existing.get(label) or field
    else:
        # picked by kind, so the audit that checks every scoped call site
        # cannot see this one -- account_id is passed by hand, and stays that way
        add = entities.add_character if kind == "character" else entities.add_prop
        add(name=name, **{label: field},
            description=description or None,
            reference_image=ref, photo_count=count, notes=notes,
            account_id=account_id)

    chunk = ingest_asset_chunk(kind, slug, name, {
        label: field, "notes": notes, "description": description},
        project=accounts.slug_of(account_id), account_id=account_id)
    if not vision["ok"] and count:
        # the model's own words go to the log, never to the page
        print(f"  could not describe {kind} {slug}: {vision['error']}", file=sys.stderr)
    note = None if vision["ok"] else (NOT_DESCRIBED if count else "no photos to describe")
    # the connector never draws (a sheet is its quoted tool). A page create
    # that kept nothing in the folder still does: the job is told WHICH
    # photos this request wrote and reads them back from the account's keys
    sheet_job = _maybe_sheet_job(sheet and not (strict and private), plural,
                                 slug, name, detail=field, notes=notes,
                                 account_id=account_id, photos=fresh)
    sheet_note = None
    if sheet_job is None and sheet:
        sheet_note = ("no sheet: GEMINI_API_KEY not set" if not _gemini_key(account_id)
                      else "no sheet: no photos to draw it from")
    return {"ok": True, "slug": slug, "photos": count,
            "described": vision["ok"], "note": note, "rag": chunk,
            "sheet_job": sheet_job, "sheet_note": sheet_note}


ELEMENT_KINDS = ("character", "prop", "location")


def create_element(kind: str, name: str, *, account_id: Optional[int], field: str = "",
                   notes: str = "", uploads=(), photo_urls=(), sheet: bool = False,
                   strict: bool = False) -> dict:
    """Make (or add a photo to) one element. `uploads` are (filename,
    bytes) pairs; `photo_urls` are the studio's own references, read
    through `_photo_bytes`. Raises ElementRefused."""
    if kind not in ELEMENT_KINDS:
        raise ElementRefused(404, "not_found", "no such element kind")
    # the plan's storage (2026-10-20): photos are uploads; a photo already
    # in the studio (`photo_urls`) adds a copy, so it still needs room
    try:
        storage_quota.check_upload(account_id, sum(len(b) for _n, b in uploads or ()))
    except storage_quota.StorageFull as e:
        raise ElementRefused(507, "out_of_storage", str(e)) from e
    if kind == "location":
        return _create_location(name, account_id=account_id, notes=notes, uploads=uploads,
                                photo_urls=photo_urls, sheet=sheet, strict=strict)
    return _create_cast(kind, name, account_id=account_id, field=field, notes=notes,
                        uploads=uploads, photo_urls=photo_urls, sheet=sheet, strict=strict)


async def _create_from_form(kind: str, request: Request, account_id: int):
    """The Elements page's create: the form in, `create_element`, and a
    refusal as the JSON error the page has always read."""
    form = await request.form()
    label = "role" if kind == "character" else "category"
    try:
        return create_element(
            kind, form.get("name") or "", account_id=account_id,
            field="" if kind == "location" else (form.get(label) or ""),
            notes=form.get("notes") or "",
            uploads=await _read_uploads(form.getlist("photos")),
            photo_urls=form.getlist("photo_urls"),
            sheet=_sheet_wanted(form))
    except ElementRefused as e:
        return _error(e.status, e.code, e.message)


@router.post("/assets/locations")
async def asset_create_location(request: Request, account_id: int = Depends(auth.current_account_id)):
    return await _create_from_form("location", request, account_id)


async def _create_entity(kind: str, request: Request, account_id: int):
    return await _create_from_form(kind, request, account_id)


@router.post("/assets/characters")
async def asset_create_character(request: Request, account_id: int = Depends(auth.current_account_id)):
    return await _create_entity("character", request, account_id)


@router.post("/assets/props")
async def asset_create_prop(request: Request, account_id: int = Depends(auth.current_account_id)):
    return await _create_entity("prop", request, account_id)


class BackfillBody(BaseModel):
    describe: bool = False


@router.post("/assets/backfill")
def assets_backfill(body: BackfillBody, account_id: int = Depends(auth.current_account_id)):
    """Put everything already on disk onto the shelf -- the catch-up for
    assets created before the shelf existed. `describe` also runs the
    vision step on undescribed cast/props: one billed call each, opt-in,
    and already-described assets are skipped rather than re-described.
    Runs as a job because a real library takes a while."""
    if body.describe and not _gemini_key(account_id):
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        client = None
        if body.describe:
            from google import genai
            client = genai.Client(api_key=_gemini_key(account_id))
        jobs.progress(job, 0.1, "walking assets")
        result = asset_shelf.backfill(db_path=None, describe=body.describe,
                                      gemini_client=client, account_id=account_id)
        detail = f"{result['ingested']} on the shelf"
        if result["described"]:
            detail += f" · {result['described']} described"
        if result["failed"]:
            detail += f" · {result['failed']} failed"
        return {"detail": detail, "output": json.dumps(result)}

    job = jobs.start("backfill", "assets → rag shelf", work, account_id=account_id)
    return {"job_id": job["id"]}


@router.delete("/assets/characters/{character_id}")
def asset_delete_character(character_id: int, account_id: int = Depends(auth.current_account_id)):
    row = entities.get_character(character_id, account_id=account_id)
    if row is None:
        return _error(404, "not_found", "no such character")
    entities.delete_character(character_id, account_id=account_id)
    _drop_asset_chunk("character", _slug(row["name"]), account_id=account_id,
                      project=accounts.slug_of(account_id))
    return {"deleted": character_id}


@router.delete("/assets/locations/{location_id}")
def asset_delete_location(location_id: int, account_id: int = Depends(auth.current_account_id)):
    """The third delete (2026-09-15, Mike: "I want to be able to delete
    assets or elements"): places had create and list but no delete, so
    the element sheet could remove a character or a prop and not a room.
    Same shape as the two below -- the row and its RAG chunk go, the
    photo bytes stay."""
    row = preprod.get_location(location_id, account_id=account_id)
    if row is None:
        return _error(404, "not_found", "no such location")
    preprod.delete_location(location_id, account_id=account_id)
    _drop_asset_chunk("location", _slug(row["name"]), account_id=account_id,
                      project=accounts.slug_of(account_id))
    return {"deleted": location_id}


@router.delete("/assets/props/{prop_id}")
def asset_delete_prop(prop_id: int, account_id: int = Depends(auth.current_account_id)):
    row = entities.get_prop(prop_id, account_id=account_id)
    if row is None:
        return _error(404, "not_found", "no such prop")
    entities.delete_prop(prop_id, account_id=account_id)
    _drop_asset_chunk("prop", _slug(row["name"]), account_id=account_id,
                      project=accounts.slug_of(account_id))
    return {"deleted": prop_id}


SHEET_KINDS = ("characters", "props", "locations")


def _sheet_kind(plural: str) -> tuple:
    """(kind, base_dir) for a create route's plural -- resolved per call,
    so a patched *_DIR is honoured."""
    return {"characters": ("character", CHARACTERS_DIR),
            "props": ("prop", PROPS_DIR),
            "locations": ("location", LOCATIONS_DIR)}[plural]


def _sheet_wanted(form) -> bool:
    """The create routes' `sheet` field: on unless the modal says off."""
    value = str(form.get("sheet") if form.get("sheet") is not None else "1").strip().lower()
    return value not in ("0", "false", "no", "off", "")


def _start_sheet_job(plural: str, slug: str, name: str, *, detail: str = "",
                     notes: str = "", account_id: int,
                     photos: Optional[list] = None) -> dict:
    """Draw an element's reference sheet as a job (2026-09-18): it spends
    (cents, Nano Banana Pro, NANO_DAILY_CAP), so it runs off the request
    like every other billed step, and the element is already saved
    whatever happens here. The sheet lands beside the uploads as
    sheet.jpg, mirrored to R2 like any photo, and `_photo_names` lists
    it last.

    `photos` (2026-10-09): the files the create request just wrote. An
    element saved under a name that already has a folder (Mike's
    characters/michael holds older shoots) would otherwise ground on the
    first six names in that folder, not the photos the person attached."""
    kind, base_dir = _sheet_kind(plural)
    # THE FOLDER ONLY WHERE IT IS THIS ACCOUNT'S (2026-10-11, BACKLOG #25).
    # It is shared by name, and `sheet.jpg` is one name in it: read for
    # another account, the sheet would be drawn from somebody else's
    # photos; written, it would become somebody else's sheet.
    own_folder = asset_shelf.folder_is_store(account_id)
    chosen = ([Path(p) for p in (photos or []) if Path(p).is_file()]
              if own_folder else [])
    # a create that kept nothing in the folder says WHICH photos it wrote;
    # by the time the job runs they exist only under the account's keys
    wrote = [asset_shelf.photo_url(kind, slug, Path(p).name) for p in (photos or [])
             if not element_sheet.is_sheet(Path(p).name)]

    def work(job):
        import tempfile

        jobs.progress(job, 0.1, "reading the photos")
        directory = base_dir / slug
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp)
            # THE FOLDER, ELSE THE BUCKET (2026-10-11). The folder is the
            # old behaviour and stays first: the Mac reads its own files.
            # The deployed API has no folder -- characters/ props/
            # locations/ are gitignored AND dockerignored, so after a
            # deploy an element's photos live in the bucket only -- and the
            # redraw used to find nothing to draw from. The listing is the
            # gallery's own (_sheet_sources); the bytes come through the
            # reader the MCP sheet tool already used.
            photos = []
            if own_folder:
                photos = chosen or [directory / n for n in _photo_names(base_dir, slug)
                                    if not element_sheet.is_sheet(n)]
            if not photos:
                sources = (wrote if wrote and not own_folder
                           else _sheet_sources(kind, base_dir, slug, account_id))
                photos = element_sheet.photo_files(sources, scratch, account_id)
            jobs.progress(job, 0.3, "drawing the sheet")
            result = element_sheet.draw(kind, name, photos,
                                        element_sheet.out_dir_for(directory, photos,
                                                                  scratch, account_id),
                                        detail=detail, notes=notes,
                                        account_id=account_id)
            if not result["ok"]:
                raise RuntimeError(result["error"] or "the sheet did not render")
            # while the scratch folder is alive: a sheet drawn from bucket
            # photos is written there, and the bucket is its only copy
            _mirror_photos_to_r2(plural, slug, [result["path"]], account_id)
        from src import asset_shelf as _shelf
        url = _shelf.photo_url(kind, slug, result["path"].name)
        return {"detail": f"{name} · sheet drawn", "output": url}

    return jobs.start("sheet", f"{name} · reference sheet", work,
                      account_id=account_id)


def _sheet_sources(kind: str, base_dir: Path, slug: str,
                   account_id: Optional[int]) -> list:
    """The real photos a sheet is drawn from, as the element's own listing
    names them (disk first, else the bucket under this account's keys --
    _asset_photo_urls' rule), minus any sheet already drawn, so a redraw
    never grounds on the last drawing."""
    return [u for u in _asset_photo_urls(kind, base_dir, slug, account_id)
            if not element_sheet.is_sheet(str(u).split("?")[0].rsplit("/", 1)[-1])]


def _maybe_sheet_job(wanted: bool, plural: str, slug: str, name: str, *,
                     detail: str = "", notes: str = "",
                     account_id: int, photos: Optional[list] = None) -> Optional[int]:
    """The create body's hook: a job id when a sheet was asked for and
    can be drawn, else None -- with the reason in the response note, not
    an error, because the element itself saved fine."""
    if not wanted or not _gemini_key(account_id):
        return None
    kind, base_dir = _sheet_kind(plural)
    if not _sheet_sources(kind, base_dir, slug, account_id):
        return None
    return _start_sheet_job(plural, slug, name, detail=detail, notes=notes,
                            account_id=account_id, photos=photos)["id"]


@router.post("/assets/{plural}/{item_id}/sheet")
def asset_draw_sheet(plural: str, item_id: int,
                     account_id: int = Depends(auth.current_account_id)):
    """Draw (or redraw) an existing element's reference sheet -- the
    Elements card's button, and how elements saved before 2026-09-18
    get one. Returns the job."""
    if plural not in SHEET_KINDS:
        return _error(404, "not_found", "no such element kind")
    if not _gemini_key(account_id):
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    kind, base_dir = _sheet_kind(plural)
    if kind == "location":
        row = preprod.get_location(item_id, account_id=account_id)
        detail = ""
    elif kind == "character":
        row = entities.get_character(item_id, account_id=account_id)
        detail = (row or {}).get("role") or ""
    else:
        row = entities.get_prop(item_id, account_id=account_id)
        detail = (row or {}).get("category") or ""
    if row is None:
        return _error(404, "not_found", f"no such {kind}")
    slug = _slug(row["name"])
    if not _sheet_sources(kind, base_dir, slug, account_id):
        return _error(400, "no_photos", "add a photo first -- a sheet is drawn from the real ones")
    job = _start_sheet_job(plural, slug, row["name"], detail=detail,
                           notes=row.get("notes") or "", account_id=account_id)
    return {"job_id": job["id"]}


class OrganizeBody(BaseModel):
    folder: Optional[str] = None
    starred: Optional[bool] = None


@router.patch("/assets/generated/{asset_id}")
def asset_organize_generated(asset_id: int, body: OrganizeBody,
                             account_id: int = Depends(auth.current_account_id)):
    """Move a render into a folder and/or star it (2026-09-18). A field
    left out of the body is left alone; `folder: ""` clears it."""
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return _error(400, "nothing_to_change", "send folder and/or starred")
    changed = render_assets.organize(
        asset_id, account_id=account_id,
        folder=fields.get("folder", ...), starred=fields.get("starred"))
    if not changed:
        return _error(404, "not_found", "no such generated asset")
    if fields.get("starred") is True:
        outcomes.record("star", asset_id=asset_id, account_id=account_id, source="library")
    row = render_assets.get(asset_id, account_id=account_id) or {}
    return {"id": asset_id, "folder": row.get("folder"),
            "starred": bool(row.get("starred"))}


@router.delete("/assets/generated/{asset_id}")
def asset_delete_generated(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """A SOFT delete (2026-09-18): the render leaves the wall and the
    assets shelf; the row and the file stay, so a concept whose shot
    carries this clip keeps rendering it."""
    if not render_assets.soft_delete(asset_id, account_id=account_id):
        return _error(404, "not_found", "no such generated asset")
    render_assets.drop_chunk(asset_id)
    outcomes.record("delete", asset_id=asset_id, account_id=account_id, source="library")
    # a deleted render's public page goes too, and an Undo does not bring
    # it back: sharing again is the person's own click
    try:
        from src import shares
        shares.unshare(asset_id, account_id=account_id)
    except Exception as e:                                      # noqa: BLE001
        print(f"  share of {asset_id} not taken down on delete: {e}", file=sys.stderr)
    return {"deleted": asset_id}


# THE STORAGE BAR AND THE TRASH (2026-10-20, Mike's calls; src/storage_quota.py).
# GET /storage is the bar in Settings -> Plan. The trash lists the renders
# deleted in the last TRASH_DAYS days -- Restore is the route below this
# block -- and "Delete forever" empties one now. Both read the workspace's
# usage, which is also what empties the trash of anything past its days.

@router.get("/storage")
def storage_usage(account_id: int = Depends(auth.current_account_id)):
    return storage_quota.public(storage_quota.usage(account_id))


@router.delete("/assets/generated/{asset_id}/forever")
def generated_delete_forever(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """Empty one render out of the trash now (it must already be in it).
    409 `in_use` when a scene or a cut still plays its file."""
    row = next((r for r in storage_quota.trashed(account_id) if r["id"] == asset_id), None)
    if row is None:
        return _error(404, "not_found", "no render with that id in the trash")
    from datetime import datetime, timedelta, timezone
    later = datetime.now(timezone.utc) + timedelta(days=storage_quota.TRASH_DAYS + 1)
    done = storage_quota.purge_due(account_id, now=later, only=asset_id)
    if asset_id in done["kept"]:
        return _error(409, "in_use", f"kept: {done['kept'][asset_id]}")
    if asset_id not in done["purged"]:
        return _error(500, "not_purged", "the file could not be removed just now")
    return {"purged": asset_id}


@router.post("/assets/generated/{asset_id}/restore")
def asset_restore_generated(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """The Undo on a removed render (2026-10-08): back on the wall and
    the assets shelf. 404 for a render that is not removed, or not this
    account's."""
    if not render_assets.restore(asset_id, account_id=account_id):
        return _error(404, "not_found", "no removed render with that id")
    # an undone delete was a slip of the hand, not a verdict on the output
    outcomes.withdraw("delete", asset_id=asset_id, account_id=account_id)
    return {"restored": asset_id}


# A RENDER ON A PUBLIC PAGE (2026-10-20, src/shares.py): nothing is public
# until its owner presses Share on that one item, and Unshare takes the page
# down. The page lives at /v/<token> on the site; its read is the public
# /public/share/<token> (app/share_page.py).

def _share_body(token: Optional[str]) -> dict:
    from src import shares
    return {"shared": bool(token), "token": token,
            "path": f"{shares.PAGE_PATH}/{token}" if token else None}


@router.get("/assets/generated/{asset_id}/share")
def asset_share_status(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    from src import shares
    return _share_body(shares.status(asset_id, account_id=account_id))


@router.post("/assets/generated/{asset_id}/share")
def asset_share(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """Share this render: its live page, or a new one. 404 for one that is
    not this account's, or deleted."""
    from src import shares
    try:
        token = shares.share(asset_id, account_id=account_id)
    except LookupError:
        return _error(404, "not_found", "no such render to share")
    return _share_body(token)


@router.delete("/assets/generated/{asset_id}/share")
def asset_unshare(asset_id: int, account_id: int = Depends(auth.current_account_id)):
    """Take this render's public page down. Sharing again makes a new
    address; the old one never comes back."""
    from src import shares
    shares.unshare(asset_id, account_id=account_id)
    return _share_body(None)


# --- retrieval --------------------------------------------------------------

class RetrieveBody(BaseModel):
    query: str
    k: int = Field(default=5, ge=1, le=20)
    domain: Optional[str] = None


@router.post("/retrieve")
def retrieve(body: RetrieveBody, account_id: int = Depends(auth.current_account_id)):
    """One endpoint serves the Studio grounding rail, the Evals probe,
    and the harness -- the same scorer everywhere, per the spec."""
    query_text = body.query.strip()
    if not query_text:
        return _error(400, "empty_query", "query text is required")
    started = time.perf_counter()
    try:
        conn = rag.connect()
        try:
            hits = rag.query(query_text, rag.make_client(), conn,
                             k=body.k, domain=body.domain or None,
                             prefer_project=accounts.slug_of(account_id))
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return _error(503, "retrieval_unavailable", str(e))
    return {
        "hits": hits,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "model": rag.EMBED_MODEL,
    }


# --- pipeline (adapted to pre-production) -----------------------------------

def _ref_sources(refs: list) -> list:
    """`refs`, one entry each and in the same order, saying what each
    picture IS and where it came from: {url, kind, slug, filename,
    source_url, title, lane}.

    `kind` is asset_shelf.parse_ref's -- the ONE parser, so a local route
    and its R2 twin read the same: character / prop / location (the asset
    bank; `slug` names the asset, and that IS its attribution), `refs` (the
    reference bin) or "" for anything else. `source_url`, `title` and
    `lane` were the page a scouted frame was taken from, off scout_bin;
    the scout went on 2026-10-14, so they are always "" now. `refs`
    itself is unchanged -- it is what the renderers read, and its order is load-bearing (urls[0] anchors)."""
    out = []
    for url in refs or []:
        ref = asset_shelf.parse_ref(url) or {}
        out.append({"url": url, "kind": ref.get("kind") or "",
                    "slug": ref.get("slug") or "",
                    "filename": ref.get("filename") or "",
                    "source_url": "", "title": "", "lane": ""})
    return out


def _keyframe_quote(concept: dict, part: Optional[int] = None) -> Optional[dict]:
    """{stills, each, credits} for drawing this scene's keyframes, or None
    when there is nothing to draw. Priced for the image model THIS server
    draws keyframes with (nano_banana.MODEL), so the label never quotes the
    other model. Whether the account is actually charged is the balance's
    `exempt`, which the card reads beside it. `part` prices ONE shot of a
    timed scene (the Render card's per-shot approve, 2026-10-11)."""
    from src import scene_chain
    return scene_chain.keyframe_quote(concept, part)


def _concept_card(c: dict, subscription_ids: Optional[set] = None) -> dict:
    status = "shot" if c.get("shot_done") else (
        "planned" if c.get("has_shot_list") else "idea")
    location_names = [loc["name"] for loc in c.get("locations") or []]
    # ONE line saying what happens, so the board can be scanned instead
    # of read (2026-08-31). `card_line` is the purpose-written label;
    # `logline` is 2-4 sentences of idea record on the scene-brief path
    # and only a fallback here; the prompt is the last resort.
    first_shot = (c.get("shots") or [{}])[0]
    summary = preprod.concept_summary(
        c.get("card_line") or "",
        c.get("logline") or "",
        first_shot.get("prompt") or "",
    ) if c.get("is_scene") else ""
    grounded = []
    for name in location_names:
        # the row's own account: the bucket fallback is fenced per tenant
        photos = _location_photos(name, c.get("account_id"))
        grounded.append({"name": name,
                         "poster": photos[0] if photos else None})
    return {
        "id": c["id"], "n": f"SHOOT-{c['id']:02d}",
        "title": c.get("title"), "hook": c.get("hook"),
        "logline": c.get("logline") or c.get("hook") or "",
        "card_line": c.get("card_line") or "",
        "summary": summary,
        "spark": c.get("spark"),
        "status": status,
        "shot_count": len(c.get("shots") or []),
        "ai_shot_count": len(c.get("ai_shots") or []),
        # the scene's own (validate_concept, shot_count_warnings) and then the
        # shot planner's (timeline.keep): what it put back and what will not
        # fit, read off a current timeline, so a stale one says nothing
        "warnings": (c.get("warnings") or []) + timeline.warnings_of((c.get("shots") or [{}])[0]),
        "grounded": grounded,
        "judge_overall": c.get("judge_overall"),
        "created_at": c.get("created_at"),
        # a one-shot concept IS a scene: its single prompt, the photos
        # it was written against, and whether it was picked to render
        "is_scene": c.get("is_scene", False),
        "picked": c.get("picked", False),
        "archived": c.get("archived", False),
        # the project this scene is filed under (2026-10-07), or None for
        # a scene made outside any -- which is what decides where its
        # canvas opens (/studio/projects/<id> or /studio/scene/<id>)
        "project_id": c.get("project_id"),
        # parked = the chain took it as far as it can without spending;
        # it is waiting in the Queue on a human. An explicit marker, not
        # "has a reference_image" -- see preprod.set_shot_parked.
        "parked": c.get("parked", False),
        "park_reason": c.get("park_reason") or "",
        "graded": c.get("graded", False),
        "shot_done": c.get("shot_done", False),
        "refs": c.get("refs") or [],
        "prompt": ((c.get("shots") or [{}])[0].get("prompt") or "")
                  if c.get("is_scene") else "",
        # WHICH TOOL THIS SHOT WAS PLANNED FOR. shootgen chose it and
        # nothing downstream ever showed it, so the Queue's renderer
        # picker had no way to default to the plan and defaulted to
        # Runway for everything -- including a scene written for Kling.
        "tool": ((c.get("shots") or [{}])[0].get("tool") or "")
                if c.get("is_scene") else "",
        # the clip model the brain proposed for this scene, and why
        # (src/model_menu.py): only where its Render card opens
        "render_model": ((c.get("shots") or [{}])[0].get("render_model") or "")
                        if c.get("is_scene") else "",
        "render_model_why": ((c.get("shots") or [{}])[0].get("render_model_why") or "")
                            if c.get("is_scene") else "",
        "media_url": ((c.get("shots") or [{}])[0].get("media_url") or "")
                     if c.get("is_scene") else "",
        "reference_image": ((c.get("shots") or [{}])[0].get("reference_image") or "")
                           if c.get("is_scene") else "",
        # THE SHOTS a timed scene is rendered as (2026-09-10) -- each with
        # its window, its own refs, its still and its clip -- or None for a
        # scene that renders whole. Only a CURRENT timeline: one planned
        # from a prompt that has since been edited describes shots nobody
        # will render, and the approve re-plans it first.
        "timeline": _timeline_card((c.get("shots") or [{}])[0], c.get("account_id"))
                    if c.get("is_scene") else None,
        # what drawing this scene's keyframes would cost (2026-09-29, Mike's
        # call: a still is spent only behind a priced approve). None when
        # there is nothing to draw.
        "keyframes": _keyframe_quote(c) if c.get("is_scene") else None,
        # WHO PAID FOR THIS CLIP. A hand-rendered clip off the operator's
        # subscription and an API-rendered one billed to somebody's credit
        # are the same mp4 in the same folder; only `params.source` on the
        # generations row tells them apart, and until this field nobody
        # ever saw it. The board renders it as one word beside RENDERED.
        # Absent set = not asked (a single-card read), which is why the
        # default is False rather than unknown.
        "subscription": bool(subscription_ids and c["id"] in subscription_ids),
        # WHERE EACH REFERENCE CAME FROM (2026-09-17), parallel to `refs`.
        # "A reference must be traceable to where it came from" was kept at
        # banking time and lost on the shot, which stores bare URLs -- so
        # the one surface where someone is about to spend a render on a
        # frame showed it unattributed. See _ref_sources.
        "ref_sources": _ref_sources(c.get("refs") or []),
        # THE DRAWABLE SIZE OF EACH REFERENCE (BACKLOG #0, 2026-09-21),
        # parallel to `refs`. `refs` itself is untouched and stays the
        # master: refs[0] is the frame the clip is anchored on, and a
        # list that quietly carried 480px versions would anchor it on one.
        # The cards try this URL first and fall back to their own chain.
        "ref_thumbs": _ref_thumbs(c.get("refs") or [], c.get("account_id")),
    }


def _ref_thumbs(refs: list, account_id: Optional[int]) -> list:
    """`_asset_photo_thumbs` for a shot's refs: the 480px derivative where
    one exists, else `?thumb=1` on an asset-photo route (the local handler
    that has always done this off disk), else the URL itself. A bin image
    (`/refs/<sha>.jpg`) is served by a static mount that knows no `?thumb`,
    so without a derivative it is drawn as it is -- slow, never missing."""
    from src import media

    out = []
    for url in refs:
        small = media.thumb_url_for(url, account_id)
        if small:
            out.append(small)
            continue
        ref = asset_shelf.parse_ref(url)
        if ref and ref["kind"] != "refs" and not url.startswith("http"):
            out.append(f"{url}?thumb=1")
        else:
            out.append(url)
    return out


def _timeline_card(shot: dict, account_id: Optional[int] = None) -> Optional[dict]:
    """The card's view of a scene's shots: the timeline when it is current,
    else the bare windows the prompt carries (so the Queue can still show
    how many clips an approve will make, and price them), else None."""
    if timeline.is_current(shot):
        tl = shot["timeline"]
        return {"planned": True, "seconds": tl.get("seconds"),
                "planner": tl.get("planner"), "continuity": tl.get("continuity") or "",
                "warnings": timeline.warnings_of(shot),
                "parts": [{**{k: p.get(k) for k in ("n", "start", "end", "seconds", "text",
                                                     "prompt", "refs", "reference_image",
                                                     "media_url")},
                           # parallel to the part's own refs, the card rule
                           "ref_thumbs": _ref_thumbs(p.get("refs") or [], account_id)}
                          for p in tl.get("parts") or []]}
    windows = timeline.parse_windows(shot.get("prompt") or "")
    if not windows:
        return None
    return {"planned": False, "seconds": sum(w["seconds"] for w in windows),
            "planner": None, "continuity": "", "warnings": [],
            "parts": [{"n": i, "start": w["start"], "end": w["end"],
                       "seconds": w["seconds"], "text": w["text"], "prompt": "",
                       "refs": [], "reference_image": None, "media_url": None}
                      for i, w in enumerate(windows, start=1)]}


def _openable(row: dict) -> bool:
    """A board row the Director canvas can open: a scene, still on the
    board, with a prompt that is not blank (the canvas refuses one).
    ONE copy, read by the arrival and the scene switcher, so the two
    cannot disagree about what the Director can open (2026-09-25: it was
    `openable` in web/src/lib/director-arrival.ts until then)."""
    return bool(row.get("is_scene") and not row.get("archived")
                and row.get("has_prompt"))


def _arrival(rows: list) -> Optional[dict]:
    """Where the Director opens when nobody named a scene. The standing
    rule (Mike's, 2026-08-25): arrival is the NODES -- the newest scene's
    graph -- never a composer and never a dead end. Rows come newest
    first; a scene still waiting on work outranks one that already has
    its clip, because the Director is where a scene gets worked; a
    rendered one is the fallback so arrival is still a real graph.
    Moved here from web/src/lib/director-arrival.ts (2026-09-25) so the
    rule lives in one place and the page asks for an id, not the board."""
    scenes = [r for r in rows if _openable(r)]
    return next((r for r in scenes if not r.get("has_media")),
                scenes[0] if scenes else None)


@router.get("/pipeline/arrival")
def pipeline_arrival(account_id: int = Depends(auth.current_account_id)):
    """The ONE concept the Director opens on, `{id}` or `{id: null}`
    (then the page falls back to its local draft). Read off
    preprod.board_index -- the board's window, a few facts per row
    computed in Postgres -- instead of the whole board, which this
    page used to fetch (~0.9 MB of database egress) to keep one id."""
    row = _arrival(preprod.board_index(account_id=account_id))
    return {"id": row["id"] if row else None}


def _scene_menu(account_id: int) -> dict:
    """The Director's scene switcher: the openable rows, as much as a
    menu line draws and no more -- no card, no gates, no sources."""
    return {"items": [
        {"id": r["id"], "n": f"SHOOT-{r['id']:02d}", "title": r["title"],
         "picked": r["picked"], "parked": r["parked"],
         "has_media": r["has_media"]}
        for r in preprod.board_index(account_id=account_id)
        if _openable(r)]}


@router.get("/pipeline/concepts")
def pipeline_concepts(status: Optional[str] = None,
                      archived: bool = False, view: Optional[str] = None,
                      project: Optional[int] = None,
                      account_id: int = Depends(auth.current_account_id),
):
    """The board. `?project=<id>` is one studio project's board
    (src/projects.py, 2026-09-28): the same window, narrowed in SQL. Archived concepts are hidden by default -- they are
    decided about, and the board is for what is still open. They are
    still here (`?archived=true`) and still counted in pick_rate, which
    reads the rows rather than this endpoint.

    `?view=menu` (2026-09-25) is the Director's scene switcher: the
    openable rows as {id, n, title, picked, parked, has_media},
    off a column-only query. It used to take the whole board for a menu.

    ARCHIVED ROWS ON DEMAND (2026-09-25, Mike's call). Every response
    carries `counts` = {open, picked, archived} (preprod.board_counts:
    the same window, scenes only), so the count line can say where every
    card went without the archived cards being fetched to count them.
    The default is the open cards; `?view=archived` is the archived half
    of the same window, which the React board asks for only when its
    Archived filter is opened. `?archived=true` still returns both halves
    (the vanilla shell reads it)."""
    if view == "menu":
        return _scene_menu(account_id)
    shelf = "archived" if view == "archived" else (None if archived else "open")
    # brand goes into the query, not a filter after it -- list_concepts
    # takes the newest 100 of THIS ACCOUNT, and both brands live in one
    # account, so filtering afterwards meant one brand could eat the
    # whole limit and quietly shorten the other's board.
    # one query for the whole board rather than one per card
    subscription_ids = generative.subscription_rendered(account_id=account_id)
    # lean: only what a card draws (2026-09-25) -- see preprod._CARD_COLUMNS
    concepts = preprod.list_concepts(account_id=account_id, lean=True,
                                     shelf=shelf, project_id=project)
    cards = [_concept_card(c, subscription_ids) for c in concepts]
    if status in ("idea", "planned", "shot"):
        cards = [c for c in cards if c["status"] == status]
    return {
        "items": cards,
        "counts": preprod.board_counts(account_id=account_id,
                                       project_id=project),
        "deny_reasons": list(DENY_REASONS),
        "shoot": preprod.shoot_rate(account_id=account_id),
        "pick": preprod.pick_rate(account_id=account_id),
    }


# --- scenes to pick between --------------------------------------------------
# One idea in, N one-shot concepts out. Not a second data model: each is
# exactly the row generate_scene_concept writes, so the scene board,
# Director, render and autopilot keep working unmodified. What is new is
# that you get SEVERAL and the pick is recorded (preprod.pick_rate).

def _photo_bytes(url: str, account_id: Optional[int] = None) -> Optional[bytes]:
    """A reference URL -> its bytes, from disk first and the network
    second, or None.

    `account_id` is WHOSE photo is being read (2026-10-11): an element
    photo comes from that account's store -- the folder only where the
    folder is its (asset_shelf.folder_is_store), its own bucket keys
    everywhere else -- through `_resolver`, so a name two accounts share
    can never read as the other one's bytes.

    The disk half is the old behaviour and stays first: a photo on THIS
    machine costs nothing to read and cannot fail. The network half is
    what a canonical R2 URL needs (2026-09-08) -- on the deployed site
    no asset photo is on disk at all, and without this the composer
    would attach a picked face to the shot and hand the generator
    nothing, which is precisely the silent it-looked-attached failure
    the reference layer exists to prevent. Never raises: fetch_image_bytes
    is SSRF-guarded, image/* only, byte-capped, and returns None on
    anything it does not like.

    A stored NAME is read from the bucket too (2026-10-11). From the
    `tenant` rung up an element photo is listed and stored as its name,
    `/characters/<slug>/photo/<file>`, which is neither a file on the
    deployed machine nor an http URL -- so that same failure came back
    for every photo picked there. `account_id` is whose photo is meant:
    the address is media.bucket_url_for's, minted under that account's
    keys, and an element photo with no account gets nothing rather than
    the flat key every account shares. Tried before a URL as it was
    given, because a row from the `legacy` rung still names a flat key
    the bucket no longer holds -- which was every older still on the
    wall, sent back as a reference or made into an element.
    """
    target = _resolver(account_id)(url)
    if target is not None:
        try:
            return target.read_bytes()
        except OSError:
            return None
    from src import imagery, media
    text = str(url or "")
    # a render still on THIS machine's disk (2026-10-10): a box with no
    # bucket names its own renders /renders/..., and a still made a minute
    # ago is the commonest thing to carry on from -- as a reference, an
    # effect's source, an element's first photo. Only through the guarded
    # reader, which opens nothing outside data/renders.
    path = text.split("?")[0]
    if path.startswith("/renders/"):
        data = imagery.render_bytes(path)
        if data is not None:
            return data
    minted = media.bucket_url_for(text, account_id)
    if minted:
        data = imagery.fetch_image_bytes(minted)
        if data is not None or minted == text:
            return data
    if text.startswith(("http://", "https://")):
        return imagery.fetch_image_bytes(text)
    return None


@router.get("/ref-roles")
def ref_roles_list(account_id: int = Depends(auth.current_account_id)):
    """What an attached reference can be FOR (src/ref_roles.py): the menu
    the composer draws on each reference. A projection of the one table;
    `look_only` marks the roles that never anchor a keyframe or a clip."""
    from src import ref_roles
    return {"roles": ref_roles.options()}


async def _collect_refs(form, want_video: bool = False,
                        account_id: Optional[int] = None):
    """Every reference one composer submission carries, in both the
    forms the pipeline needs: BYTES for the Gemini call happening now,
    and URLS to store on the shot so the keyframe and the clip get them
    too.

    One function because there are three routes that write a concept --
    /scenes/run, /pipeline/run and /generate/run -- and three copies of
    this is exactly how two of them ended up silently discarding the
    URLs (2026-08-28). Returns (image_refs, ref_urls, video_refs).

    `account_id` is the caller's: a picked element photo this machine
    does not hold is read from the bucket under that account's keys
    (_photo_bytes). Every route passes it.
    """
    image_refs: list = []
    # local, like every other shootgen use here (ref_roles.label reaches
    # for it) -- that module pulls in google.genai and this file must stay
    # cheap to import
    from src import ref_roles
    # what each reference is for (the composer's role chips); captions and
    # the order below follow it
    roles = ref_roles.clean(form.get("ref_roles"))
    seen_as: list = []          # the url each image_refs entry came from
    ref_urls: list = []
    video_refs: list = []
    for upload in form.getlist("files"):
        filename = getattr(upload, "filename", "")
        if not filename:
            continue
        mime = _video_mime(filename) if want_video else None
        if mime:
            if len(video_refs) < MAX_VIDEO_REFS:
                video_refs.append((await upload.read(), mime))
            continue
        if len(image_refs) >= MAX_IMAGE_REFS:
            continue
        jpeg = _to_jpeg(await upload.read())
        if not jpeg:
            continue
        saved = _save_upload_ref(jpeg)
        if saved and saved not in ref_urls:
            ref_urls.append(saved)
        image_refs.append((jpeg, "image/jpeg",
                           ref_roles.label(saved or "", roles)))
        seen_as.append(saved or "")
    for picked in form.getlist("asset_photos"):
        picked = str(picked).split("?")[0]
        if not picked or picked in ref_urls or len(ref_urls) >= MAX_IMAGE_REFS:
            continue
        ref_urls.append(picked)
        if len(image_refs) >= MAX_IMAGE_REFS:
            continue
        raw = _photo_bytes(picked, account_id)
        if raw is None:
            continue
        jpeg = _to_jpeg(raw)
        if jpeg:
            image_refs.append((jpeg, "image/jpeg",
                               ref_roles.label(picked, roles)))
            seen_as.append(picked)
    if roles:
        # a reference that only lends its look -- light, palette, framing --
        # is never first: the first one is what a keyframe and a clip
        # anchor on (src/ref_roles.py)
        ref_urls = ref_roles.order(ref_urls, roles)
        rank = {url: i for i, url in enumerate(ref_urls)}
        paired = sorted(zip(seen_as, image_refs), key=lambda p: rank.get(p[0], len(rank)))
        image_refs = [ref for _url, ref in paired]
    return image_refs, ref_urls, video_refs


def _form_ref_roles(form) -> dict:
    """What each attached reference is FOR, as the composer posted it
    (`ref_roles`: JSON {url: role}; src/ref_roles.py). {} when it said
    nothing, which is every request before 2026-10-11."""
    from src import ref_roles
    return ref_roles.clean(form.get("ref_roles"))


def _auto_refs(text: str, already: list,
               account_id: Optional[int] = None, *, idea: Optional[str] = None) -> list:
    """The photos of the assets this scene actually names.

    `idea` (2026-09-05): when given, the assets in scope are the ones
    the IDEA names or `already` explicitly picks -- asset_shelf.in_scope,
    the same rule that decided what the writer was offered -- and the
    finished scene's own text is not scanned. Scanning it back had been
    attaching Michael's photos to scenes whose idea never named him,
    because the writer volunteers his name on his own channel. Without
    `idea` the legacy scene-text scan still runs.

    `format_cast` tells the generator that the cast and props on file
    have "(reference photos on file)", and the scene it writes says so in as
    many words -- but nothing was ever attaching those files, so the
    renderer got the sentence and not the face (2026-08-28). This
    closes that loop: read the finished scene back, find the assets it
    named, and let their photos ride on the shot.

    Two passes, because a slot is worth different things to different
    assets. Pass one takes ONE photo of every asset the scene named, so
    nothing named goes unattached and the anchor slot (a renderer
    reads whichever is first) still holds the character the scene opens on.
    Pass two spends what is left on more angles of the characters.

    Grounding shapes, it doesn't gate: no match, or no assets at all,
    just means the scene renders on its text like it did before.
    """
    try:
        from src import shootgen
        assets = _assets_all(account_id)
    except Exception:
        return []
    picked = list(already)
    if idea is not None:
        from src import asset_shelf
        named = asset_shelf.in_scope(idea, already, assets)
    else:
        named = shootgen.named_assets(text, assets)
    for asset in named:
        if len(picked) >= MAX_IMAGE_REFS:
            return picked
        # an element with a drawn sheet is USED as its sheet (2026-10-12)
        photo = _best_photo(element_sheet.element_refs(asset["photos"]))
        if photo and photo not in picked:
            picked.append(photo)
    # Pass two: whatever slots are left go to MORE ANGLES OF THE FACES,
    # round-robin so two characters share the remainder evenly.
    faces = [a for a in named if a.get("category") == "character"
             and element_sheet.element_refs(a["photos"]) == list(a["photos"])]
    for index in range(1, CHARACTER_REF_PHOTOS):
        for asset in faces:
            if len(picked) >= MAX_IMAGE_REFS:
                return picked
            angles = _asset_photos(asset["photos"], CHARACTER_REF_PHOTOS)
            if index < len(angles) and angles[index] not in picked:
                picked.append(angles[index])
    return picked


# How many photos of one character are worth spending reference slots
# on. A face is the case the one-photo rule below was not written for:
# a guest-character keyframe grounded a three-quarter head turn on a
# single frontal portrait and aged him about ten years, while the
# three-quarter frame it needed sat unused in the same folder
# (2026-08-29). A prop gains almost nothing from a second angle; an
# identity gains most of what it has. Three, because past that the
# photos are duplicates of angles already sent.
CHARACTER_REF_PHOTOS = 3


def _best_photo(photos: list) -> Optional[str]:
    """The one photo that stands for an asset -- a face and a bike, not
    twelve angles of the bike -- preferring one the renderer can
    actually decode."""
    picks = _asset_photos(photos, 1)
    return picks[0] if picks else None


def _asset_photos(photos: list, limit: int) -> list:
    """Up to `limit` of an asset's photos, decodable ones first.

    Same preference _best_photo has always had, applied to a run of
    them: a HEIC the renderer cannot open is worth less than the third
    JPEG, so it sorts last rather than eating a slot."""
    urls = [p.split("?")[0] for p in photos if p]
    native = [u for u in urls if Path(u).suffix.lower() in _DECODES_NATIVELY]
    other = [u for u in urls if u not in native]
    return (native + other)[:max(0, limit)]


_KIND_RANK = {"character": 0, "prop": 1, "location": 2}


def _kit_refs(concept_id: int, refs: list, manual: int, text: str,
              roles: Optional[dict], account_id: Optional[int]) -> tuple[list, Optional[dict]]:
    """The scene's refs with the photo of every product and character its
    brand kit links and its words name (2026-10-22, docs/tasks/
    task-kit-products-and-screens.md Part B), each with the role it plays
    (a product is `product`, a person `subject`; brand_kits.LINK_ROLE).

    The person's own picks stay first and in their order; the inferred
    refs behind them, with the kit's added, keep the one order every
    scene keeps -- character, then prop, then location. No kit, no linked
    element named, or every named one already on the scene: the refs and
    roles come back exactly as they were."""
    try:
        from src import brand_kits, element_sheet, project_context
        kit = (project_context.kit()
               or brand_kits.for_concept(concept_id, account_id=account_id))
        hits = brand_kits.named(kit, text)
        if not hits:
            return refs, roles
        assets = {a["id"]: a for a in _assets_all(account_id)}
        added, said = [], {}
        held = {str(r).split("?")[0] for r in refs}
        for e in hits:
            photos = (assets.get(f"{e['kind']}-{e['id']}") or {}).get("photos") or []
            # one photo (the sheet when drawn), or as many of the person's
            # uploads as the link asks for -- an app's real screens
            picks = [p.split("?")[0]
                     for p in element_sheet.element_photos(photos, int(e.get("photos") or 1))]
            for pick in picks:
                said[pick] = e["role"]
                if pick not in held:
                    added.append(pick)
                    held.add(pick)
        if not said:
            return refs, roles
        if added:
            def rank(r):
                parsed = asset_shelf.parse_ref(r)
                return _KIND_RANK.get(parsed["kind"], 1) if parsed else 1
            inferred = sorted([*refs[manual:], *added], key=rank)
            refs = [*refs[:manual], *inferred][:MAX_IMAGE_REFS]
        # a role the person gave outranks the kit's
        return refs, {**said, **(roles or {})}
    except Exception as e:                       # a kit is an addition, never a gate
        print(f"note: kit products not attached: {type(e).__name__}: {e}", file=sys.stderr)
        return refs, roles


def _attach_scene_refs(concept_id: int, manual: list,
                       account_id: Optional[int] = None, *,
                       idea: Optional[str] = None,
                       roles: Optional[dict] = None) -> list:
    """Store a scene's references on its shot, manual picks first.

    On the shot rather than on the concept because that is what the
    Director graph reads (`ref_urls` on the enhance, keyframe and clip
    nodes), and manual first because an explicit pick outranks anything
    inferred -- and because a clip anchors on whichever one is first.
    """
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None or not concept["shots"]:
        return []
    shots = [dict(sh) for sh in concept["shots"]]
    text = " ".join(str(shots[0].get(k) or "")
                    for k in ("desc", "prompt", "location"))
    refs = _auto_refs(text, manual, account_id, idea=idea)[:MAX_IMAGE_REFS]
    refs, roles = _kit_refs(concept_id, refs, len(manual), f"{idea or ''} {text}",
                            roles, account_id)
    refs = [asset_shelf.storable_ref(r) for r in refs]
    if not refs:
        return []
    if roles:
        # what each reference is for rides BESIDE the refs, under the names
        # the shot stores them by, and a look-only one is never the anchor
        from src import ref_roles
        named = ref_roles.for_refs(ref_roles.rekey(roles, asset_shelf.storable_ref), refs)
        refs = ref_roles.order(refs, named)
        if named:
            shots[0]["ref_roles"] = named
    shots[0]["refs"] = refs
    preprod.update_concept_shots(
        concept_id, {"shots": shots, "duration": concept.get("duration")},
        warnings=concept.get("warnings") or [], account_id=account_id)
    return refs


# ONE Create writes ONE scene (2026-09-10, Mike's call). The composer used
# to offer 1-4 takes off one idea; the picker is gone and this is the gate
# that makes it true -- an old client or a hand-made request posting
# count=4 still gets one scene, never four billed takes.
SCENE_COUNT_MAX = 1
SCENE_COUNT_DEFAULT = 1


@router.post("/scenes/run")
async def scenes_run(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Several takes on one idea, to pick between -- the Studio Create
    button (2026-08-28).

    Multipart, the same shape /pipeline/run takes, because the composer
    that fires it can attach BOTH freshly uploaded photos and ones
    picked out of the asset bank. `asset_photos` are stored ON each
    concept's shot as well as sent as vision input, which is what
    carries them into every node once it reaches Director; an uploaded
    file grounds this call only, since it has no URL to ride on.

    It runs the grounding and writing stages of src/scene_chain.py and
    STOPS there: Create's job ends on the concepts board (2026-08-29,
    Mike's call). Enhancing, keyframing and rendering are the Director
    canvas's work when a person is driving, and the nightly graph's when
    nobody is -- both go through the same stage functions, so there is
    one implementation of each rather than three.
    """
    form = await request.form()
    idea = (form.get("idea") or form.get("prompt") or "").strip()
    if not idea:
        return _error(400, "empty_idea", "type an idea first")
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    # a form's `brand` is accepted and ignored (2026-10-13)
    # The project this Create runs inside (2026-09-28): its brief and memory
    # are appended under the studio's block for the whole job, and the
    # scenes it writes are filed under it. An unknown id is refused -- a
    # Create that silently dropped its project would write off-brief.
    project = _form_project(form, account_id)
    if (form.get("project_id") or "").strip() and project is None:
        return _error(404, "no_project", f"no project {form.get('project_id')}")
    # a brand kit picked in the composer outside a project (2026-10-22): the
    # writer reads its BRAND block and the scenes keep it for their renders.
    # Inside a project the project's own pick is what applies.
    picked_kit, refused = _form_kit(form, account_id)
    if refused is not None:
        return refused
    if project is not None:
        picked_kit = None
    try:
        count = int(form.get("count") or SCENE_COUNT_DEFAULT)
    except (TypeError, ValueError):
        count = SCENE_COUNT_DEFAULT
    count = max(1, min(SCENE_COUNT_MAX, count))

    # Which brain writes (2026-09-09). Clamped HERE against the real
    # table, for the reason the count above is: the select is not the
    # gate, and an unknown tier should write a cheap scene rather than
    # fail a run. resolve_brain does the same clamp a second time at the
    # bottom -- deliberately, since the graph reaches it without passing
    # through this route at all.
    from src import gemini_utils
    brain_raw = (form.get("brain") or "").strip().lower()
    brain = brain_raw if brain_raw in gemini_utils.BRAINS else gemini_utils.DEFAULT_BRAIN

    # The frame the scene is written for, stored on its shot so the Queue
    # card defaults to it instead of asking again. REFUSED rather than
    # clamped when it is not a size the renderers take -- the same rule
    # providers.check_render_choice follows, and for the same reason: a
    # silently corrected frame is a clip that comes back the wrong shape.
    ratio = (form.get("ratio") or "").strip()
    if ratio and ratio not in render_specs.FRAME_SIZES:
        return _error(400, "bad_ratio",
                      f"{ratio} is not a frame the renderers take")
    # The scene's total length (2026-09-10). Clamped by scene_seconds,
    # never refused -- the select is not the gate, same as the count.
    seconds = timeline.scene_seconds(form.get("seconds"))

    # Videos too (2026-09-10): they ground the WRITING only -- Gemini
    # watches them -- and never land on the shot, since no renderer takes
    # a video as a reference. MAX_VIDEO_REFS caps them, same as Generate.
    image_refs, refs, video_refs = await _collect_refs(
        form, want_video=True, account_id=account_id)
    # what each attached reference is for; stored beside the scene's refs
    roles = _form_ref_roles(form)
    # the camera preset the composer sent with the idea, if any (its words
    # already ride in the idea; the id is only for counting)
    used_preset = presets.get_preset((form.get("preset") or "").strip())
    # the clip model the brain proposed for this scene (src/model_menu.py):
    # kept only when the catalogue has it, and only as where the scene's
    # Render card opens -- nothing is rendered or chosen here
    from src import model_menu
    render_model = model_menu.video_id(form.get("render_model"))
    render_why = model_menu.clean_why(form.get("render_model_why")) if render_model else ""
    # a render handed back in as a reference was kept (src/outcomes.py);
    # an upload or an element's photo is not an output and records nothing
    outcomes.record_refs("ref_reuse", refs, account_id=account_id, source="composer")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        from google import genai

        from src import scene_chain

        client = genai.Client(api_key=api_key)
        video_parts = [p for p in (video_part(client, data, mime)
                                   for data, mime in video_refs) if p is not None]
        if video_refs:
            jobs.progress(job, 0.05,
                          f"{len(video_parts)}/{len(video_refs)} reference video(s) ready")

        # ground -> write -> attach, and STOP: pressing Create writes
        # concepts and lands on the board. The enhance, the keyframe and
        # the clip are the Director canvas's job when a person is doing
        # this by hand -- and the nightly graph's job when nobody is
        # (src/orchestrator.py calls the same stage functions).
        from src import project_context
        with project_context.active(project), project_context.kit_active(picked_kit):
            result = scene_chain.run(
                idea, count=count, refs=refs, image_refs=image_refs or None,
                db_path=None, account_id=account_id,
                gemini_client=client, video_parts=video_parts,
                resolve_photo=_resolver(account_id),
                attach_refs=_attach_scene_refs, roles=roles,
                brain=brain, ratio=ratio or None, seconds=seconds,
                progress=lambda fraction, detail: jobs.progress(job, fraction, detail))
        saved = result["scenes"]
        if project and saved:
            projects.tag_concepts([s["concept_id"] for s in saved], project["id"],
                                  account_id=account_id)
        if picked_kit and saved:
            brand_kits.pick_for_concepts([s["concept_id"] for s in saved], picked_kit["id"],
                                         account_id=account_id)
        if used_preset:
            # a label on the scene, so its outputs count against the preset
            for s in saved:
                try:
                    preprod.set_shot_preset(s["concept_id"], 1, used_preset["id"],
                                            account_id=account_id)
                except Exception:                           # noqa: BLE001
                    pass
        if render_model:
            for s in saved:
                try:
                    preprod.set_shot_render_model(s["concept_id"], 1, render_model,
                                                  account_id=account_id, why=render_why)
                except Exception:                           # noqa: BLE001
                    pass
        detail = f"{len(saved)} concept(s)"
        if brain != gemini_utils.DEFAULT_BRAIN:
            detail += f" · {brain}"
        for note in result["notes"]:
            detail += f" · {note}"
        return {"detail": detail,
                "ref_id": saved[0]["concept_id"] if saved else None}

    job = jobs.start("scenes", f"concepts · {idea[:60]}", work, account_id=account_id)
    return {"job_id": job["id"], "image_refs": len(image_refs),
            "video_refs": len(video_refs), "brain": brain, "seconds": seconds,
            "project_id": project["id"] if project else None}


# --- studio projects (2026-09-28) ---------------------------------------------
# One brief and one memory per piece of work -- src/projects.py says why.
# Since 2026-10-07 (Mike's call) the Projects BOARD is the studio's home
# and a project is made only through the Guide (guide_tools.PROJECT_TOOLS,
# run by /creative-guide/act): POST /projects stays as the door that click
# posts to and for the CLI, but no page offers a "New project" form. A
# project's workspace (/studio/projects/<id>) is its scenes, the Director
# canvas and the pill scoped to it; its chat history lives here too.


class ProjectBody(BaseModel):
    title: Optional[str] = None
    brief: Optional[str] = None
    look: Optional[str] = None
    # the Explore / Make switch (PATCH only; a new project starts in Make)
    explore: Optional[bool] = None


class ProjectDraftBody(BaseModel):
    title: str = ""
    answers: dict = Field(default_factory=dict)


class ProjectArchiveBody(BaseModel):
    archived: bool = True


class ProjectForgetBody(BaseModel):
    at: str


@router.get("/projects")
def projects_list(archived: bool = False,
                  account_id: int = Depends(auth.current_account_id)):
    """The Projects board (2026-10-07): one card per project, newest
    touched first, each with its counts and a cover -- the stored ref of
    its newest scene, minted here for the browser (media.url_for, and the
    480px tile beside it), never handed out as the stored string."""
    from src import media

    items = projects.list_projects(account_id=account_id, include_archived=archived)
    for p in items:
        raw = p.get("cover")
        p["cover"] = media.url_for(raw, account_id) if raw else None
        p["cover_thumb"] = _ref_thumbs([raw], account_id)[0] if raw else None
    return {"items": items,
            "questions": [{"key": k, "label": label} for k, label in projects.QUESTIONS]}


@router.post("/projects")
def projects_create(body: ProjectBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return projects.create(body.title or "", body.brief or "", account_id=account_id,
                               look=body.look or "")
    except ValueError as e:
        return _error(400, "bad_project", str(e))


@router.post("/projects/draft-brief")
def projects_draft_brief(body: ProjectDraftBody,
                         account_id: int = Depends(auth.current_account_id)):
    """The chat-built half of a brief: three answers in, a draft out, for the
    person to edit before saving. Nothing is stored here."""
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    if not any((body.answers.get(k) or "").strip() for k, _ in projects.QUESTIONS):
        return _error(400, "no_answers", "answer at least one question first")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    from google import genai
    try:
        brief = projects.draft_brief(body.title or "untitled",
                                     {k: str(v) for k, v in body.answers.items()},
                                     genai.Client(api_key=api_key), account_id=account_id)
    except Exception as e:  # the draft IS the deliverable here
        return _error(502, "draft_failed", f"couldn't draft the brief: {e}"[:300])
    return {"brief": brief}


@router.get("/projects/{project_id}")
def projects_get(project_id: int, account_id: int = Depends(auth.current_account_id)):
    project = projects.get(project_id, account_id=account_id)
    if project is None:
        return _error(404, "not_found", f"no project {project_id}")
    return project


@router.patch("/projects/{project_id}")
def projects_update(project_id: int, body: ProjectBody,
                    account_id: int = Depends(auth.current_account_id)):
    try:
        return projects.update(project_id, account_id=account_id,
                               title=body.title, brief=body.brief, look=body.look,
                               explore=body.explore)
    except ValueError as e:
        return _error(404 if "no project" in str(e) else 400, "bad_project", str(e))


@router.post("/projects/{project_id}/archive")
def projects_archive(project_id: int, body: ProjectArchiveBody,
                     account_id: int = Depends(auth.current_account_id)):
    try:
        projects.set_archived(project_id, body.archived, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"ok": True, "archived": body.archived}


@router.post("/projects/{project_id}/forget")
def projects_forget(project_id: int, body: ProjectForgetBody,
                    account_id: int = Depends(auth.current_account_id)):
    try:
        removed = projects.forget(project_id, body.at, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"ok": True, "removed": removed}


@router.get("/projects/{project_id}/standing")
def projects_standing(project_id: int, account_id: int = Depends(auth.current_account_id)):
    """Where the project stands (src/projects.py standing): the counts and
    the one line Vesper opens with when it is reopened in Create. Free, no
    model."""
    found = projects.standing(project_id, account_id=account_id)
    if found is None:
        return _error(404, "not_found", f"no project {project_id}")
    return found


@router.get("/projects/{project_id}/scenes")
def projects_scenes(project_id: int, account_id: int = Depends(auth.current_account_id)):
    """Every scene filed under the project and whether it is rendered --
    what the delete confirm lists as "left detached" (2026-10-07). Not
    the board's window: the board is bounded, this is the whole project."""
    if projects.get(project_id, account_id=account_id) is None:
        return _error(404, "not_found", f"no project {project_id}")
    return {"items": projects.scenes_to_detach(project_id, account_id=account_id)}


@router.delete("/projects/{project_id}")
def projects_delete(project_id: int, request: Request,
                    account_id: int = Depends(auth.current_account_id)):
    """Delete a project for good (2026-10-07, Mike's call) -- its brief,
    look, memory and chat history. Its scenes are detached, never
    deleted, so a rendered clip stays on the Assets wall. The one place
    this app deletes rather than archives; the confirm is the page's."""
    model_connections.mutation_header(request)
    try:
        counts = projects.delete(project_id, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"ok": True, **counts}


@router.get("/projects/{project_id}/messages")
def projects_messages(project_id: int, before: Optional[int] = None, limit: int = 40,
                      account_id: int = Depends(auth.current_account_id)):
    """The project's chat history, newest `limit` turns oldest-first;
    `?before=<message id>` pages back. Written by the Guide turn itself
    (`remember=1` on /creative-guide inside a project)."""
    if projects.get(project_id, account_id=account_id) is None:
        return _error(404, "not_found", f"no project {project_id}")
    return projects.messages(project_id, account_id=account_id, limit=limit, before=before)


def _stills_drawn(result: dict, part: Optional[int] = None,
                  quoted: Optional[int] = None) -> str:
    """The keyframe job's closing line: how many stills THIS job drew, which
    is how many were charged. Read off the draw's own count (`drawn`), never
    off `frames`: a timed scene's `frames` lists the stills its shots already
    had as well, and for a scene with no timed shots this line used to add
    one to a list that already held the first still -- two drawn read as
    "3 still(s)" (2026-10-11, docs/BACKLOG.md #29).

    `quoted` is the count the price was for. When fewer were drawn the line
    says why, because the person was shown the larger number: a strip a
    failed still cut short, or a scene priced "up to" that many whose shot
    turned out to hold one moment (scene_chain.keyframe_quote)."""
    count = result.get("drawn")
    if count is None:       # a draw that does not say: one for a single shot
        count = 1 if part is not None else (len(result.get("frames") or []) or 1)
    if not count:
        return "already drawn"
    line = "1 still" if count == 1 else f"{count} stills"
    if quoted and count < quoted:
        if result.get("error"):
            line += f" of {quoted} · the rest were not drawn"
        elif not result.get("parts") and part is None:
            line += " · the shot holds one moment"
    return line


def _keyframe_on_pick(concept: dict, account_id: int, part: Optional[int] = None,
                      limit: Optional[int] = None):
    """Render the picked scene's still(s), in the background. Returns a
    job id, or None when there is nothing to do. Called by the priced
    approve (`scene_keyframes`), not by the pick, since 2026-09-29.
    `part` draws one shot of a timed scene (2026-10-11). `limit` is the
    most stills the job may draw: the count the price was for, passed by
    every priced approve -- the page's button and a chat's signed quote --
    so no draw spends past the number the person was shown.

    WHY HERE AND NOT IN THE NIGHT (2026-09-08, Mike's call). The nightly
    graph's keyframe step is off (`PHANTRA_KEYFRAME=0`, a deliberate
    cost cut on 09-07): a 40-spark walk that draws every scene spends the
    whole Nano cap on concepts nobody has looked at, and 75 of 75 stills
    from one night is not a review queue, it is wallpaper. The pick is
    the first moment a human has said this scene is worth something, so
    it is the cheapest possible place to spend cents on an image -- and
    the image arrives before the Queue, which is where the dollars are.

    Never fatal, and never in the request. The pick itself has already
    been recorded by the time this runs; a keyframe that fails (no key,
    NANO_DAILY_CAP, a 503 from the image model) leaves a failed job in
    the rail and a scene that is picked, prompted and simply not drawn
    yet -- exactly what every scene looked like before this existed.
    Set PHANTRA_KEYFRAME_ON_PICK=0 to turn it off without touching the
    route.

    Deliberately skipped for a scene that already HAS a still: unpicking
    and re-picking a card must not quietly re-bill it, and the Director
    canvas's own keyframe is the one a person chose.
    """
    from src import scene_chain

    api_key = _gemini_key(account_id)
    if not api_key:
        return None
    # The guard is scene_chain's, asked here so a skip costs no job at
    # all, and asked again inside draw_on_pick so the MCP door cannot
    # drift away from this one.
    if scene_chain.pick_skip_reason(concept, part):
        return None
    concept_id = concept.get("id")
    title = (concept.get("title") or f"concept {concept_id}")[:60]
    if part is not None:
        title = f"{title} · shot {part}"

    def work(job):
        from google import genai

        from src import scene_chain

        jobs.progress(job, 0.2, "rendering keyframe")
        result = scene_chain.draw_on_pick(
            concept_id, db_path=None, account_id=account_id,
            resolve_photo=_resolver(account_id),
            gemini_client=genai.Client(api_key=api_key), part=part,
            **({"limit": limit} if limit is not None else {}))
        if result.get("skipped"):
            return {"detail": result["skipped"]}
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "keyframe failed")
        out = {"detail": _stills_drawn(result, part, limit), "ref_id": concept_id}
        if result.get("drawn") is not None:
            out["stills"] = result["drawn"]     # what this job drew: the plan's step says it
        return out

    job = jobs.start("keyframe", f"keyframe · {title}", work,
                     account_id=account_id)
    # named from the start, not only in the result: see approve_render
    jobs.update(job["id"], ref_id=concept_id)
    return job["id"]


def _refused(e: ApproveRefused) -> JSONResponse:
    """An ApproveRefused as the JSON error the routes have always sent."""
    return _error(e.status, e.code, e.message)


KEYFRAME_QUOTE_TOOL = "approve_keyframes"     # quote_redemptions.tool


def _held_keyframe_token(tokens: list, concept: dict, account_id: Optional[int],
                         part: Optional[int]):
    """The keyframe quote among `tokens` -- ours, unexpired, this account's
    and for this scene -- or None when none of them is one. A caller may
    hand over every token its quote carried, so a token for another render
    (a clip's) is passed over, as _verify_tokens passes one over; any other
    refusal is the answer. Whether the quote still describes the scene is
    asked later (scene_chain.check_keyframe_quote). Raises
    pricing.QuoteRefused or SigningUnconfigured."""
    from src import scene_chain
    for token in [t for t in tokens if isinstance(t, str) and t.strip()]:
        try:
            return scene_chain.read_keyframe_token(token, concept, account_id, part)
        except pricing.QuoteRefused as e:
            if e.reason != "wrong_render":
                raise
    return None


def _not_recorded(e: Exception) -> ApproveRefused:
    """The redemption table could not be read or written: an approval
    nobody can prove was used once is not spent."""
    print(f"[quote] keyframe approval not recorded: {type(e).__name__}: {e}",
          file=sys.stderr)
    return ApproveRefused(503, "approval_not_recorded",
                          "the approval could not be recorded, so nothing was "
                          "started or spent -- try again")


def _already_used(earlier: dict) -> dict:
    """What a second approve with a spent keyframe quote is handed: the
    first one's answer (its job), marked, and nothing new."""
    return {"ok": True, **(earlier.get("response") or {}), "already_used": True}


def approve_keyframes(concept_id: int, account_id: Optional[int],
                      part: Optional[int] = None, *,
                      tokens: Optional[list] = None,
                      require_quote: bool = False) -> dict:
    """The priced approve for a scene's keyframes, as a callable (2026-10-07):
    the route below and the MCP `approve` tool run this same body, so the
    two doors cannot drift. Returns the route's JSON; raises ApproveRefused
    with the status and code the route answers. `part` approves ONE shot's
    still: it is priced, checked against the balance and drawn alone.

    WHAT COUNTS AS THE APPROVAL DIFFERS BY DOOR (2026-10-11). On the page
    the price is printed on the button and the click is the approval, so
    the route passes nothing more. A chat app has no button: its door
    passes `require_quote=True`, and then this needs the signed token
    `quote` gave for these stills (scene_chain.keyframe_token), exactly as
    a clip needs its own -- 400 `missing_quote` without one, and the
    token's own refusal (`expired`, `stale_content`, ...) when it does not
    verify for the scene as it stands. Until that day the chat's `approve`
    drew the strip on the scene id alone.

    The requirement is the clip's (`_quote_required`): a server with no
    QUOTE_SIGNING_SECRET handed out no token and asks for none. A token
    that IS sent is verified either way, and then two things follow from
    it. It is spent ONCE (src/quote_redemptions.py): a second approve with
    it is handed the first one's job and starts nothing -- asked BEFORE the
    token is held against the scene, because the strip the first approve is
    drawing is what makes its token stale, and "re-quote" would send a
    repeat off to buy the rest of it a second time. And the job draws no
    more stills than the token priced.

    NEITHER DOOR DRAWS PAST ITS PRICE (2026-10-11, docs/BACKLOG.md #29). The
    count is scene_chain.stills_to_draw -- the most the draw can make -- and
    both doors hand it to the job as its cap: the token's own count for a
    chat, the quote computed here for the page. `keyframes` in the answer
    is that quote; `up_to` on it means the count is a ceiling (a scene with
    no timed shots, drawn as one still per moment of its move), so fewer
    stills may be drawn and charged, never more."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        raise ApproveRefused(404, "not_found", "no such concept")
    held = None
    if tokens:
        try:
            held = _held_keyframe_token(tokens, concept, account_id, part)
        except (pricing.QuoteRefused, pricing.SigningUnconfigured) as e:
            raise _quote_refused(e, account_id)
    from src import quote_redemptions, scene_chain
    if held is not None:
        try:
            earlier = quote_redemptions.redeemed(held.token_id, account_id)
        except Exception as e:
            raise _not_recorded(e)
        if earlier is not None:
            return _already_used(earlier)
    quote = _keyframe_quote(concept, part)
    if not quote:
        raise ApproveRefused(409, "nothing_to_draw",
                             scene_chain.pick_skip_reason(concept, part) or "nothing to draw")
    if not _gemini_key(account_id):
        raise ApproveRefused(503, "generation_unavailable", "GEMINI_API_KEY not set")
    if held is None and (tokens or (require_quote and pricing.configured())):
        raise _quote_refused(
            pricing.QuoteRefused("missing_quote", "no quote for these keyframes"), account_id)
    if held is not None:
        try:
            scene_chain.check_keyframe_quote(held, concept, part)
        except pricing.QuoteRefused as e:
            raise _quote_refused(e, account_id)
    from src import accounts, ledger
    from src import charge as charging
    # the unowned pool and the operator's exempt accounts are never charged
    # (ledger.hold_for_render), so they are never refused here either
    if account_id is not None and not accounts.is_credit_exempt(account_id):
        have = ledger.available(account_id)
        if have < quote["credits"]:
            # "up to" when the count is a ceiling: the balance has to cover
            # the most the draw can make, though fewer may be charged
            what = (f"{'up to ' if quote.get('up_to') else ''}{quote['stills']} "
                    f"keyframe{'s' if quote['stills'] != 1 else ''}")
            raise ApproveRefused(402, "out_of_credits", charging.refusal(
                ledger.InsufficientCredit(account_id, quote["credits"], have), what))
    if held is None:
        # THE BUTTON IS CAPPED AT ITS OWN PRICE (2026-10-11, Mike's call;
        # docs/BACKLOG.md #29). The page has no token to carry a count, so
        # the count is the quote just computed above -- the one in the
        # response, and the one the balance was checked against. Without it
        # the job could draw past the number on the button: a scene whose
        # timeline is re-planned inside the job has as many shots as the
        # planner finds.
        job_id = _keyframe_on_pick(concept, account_id, part=part, limit=quote["stills"])
        return {"ok": True, "job_id": job_id, "keyframes": quote}
    # Claimed only now, after every refusal above: a balance that was short
    # leaves the token good for the hour. The claim is what decides a race.
    try:
        first = quote_redemptions.claim(held.token_id, account_id,
                                        tool=KEYFRAME_QUOTE_TOOL, credits=held.credits)
    except Exception as e:
        raise _not_recorded(e)
    if first is not None:
        return _already_used(first)

    def unspend():
        # nothing ran and nothing was held: the person's yes is still good
        try:
            quote_redemptions.forget(held.token_id, account_id)
        except Exception:
            pass

    try:
        job_id = _keyframe_on_pick(concept, account_id, part=part, limit=held.stills)
    except Exception:
        unspend()
        raise
    out = {"ok": True, "job_id": job_id, "keyframes": quote}
    if job_id is None:      # no job to start after all (drawn in the meantime)
        unspend()
        return out
    try:
        quote_redemptions.record(held.token_id, account_id, out)
    except Exception as e:      # the claim already stands: a repeat still starts nothing
        print(f"[quote] keyframe quote {held.token_id} redeemed but its job was "
              f"not recorded ({type(e).__name__}: {e})", file=sys.stderr)
    return out


class KeyframesBody(BaseModel):
    """`part`: draw ONE shot of a timed scene (2026-10-11); absent means
    every shot still without a still, as before."""
    part: Optional[int] = None


@router.post("/scenes/{concept_id}/keyframes")
@router.post("/concepts/{concept_id}/keyframes")     # the old name, kept one release
def scene_keyframes(concept_id: int, body: Optional[KeyframesBody] = None,
                    account_id: int = Depends(auth.current_account_id)):
    """The priced approve for a scene's keyframes (2026-09-29, Mike's call:
    "an approve button before each render that spends credits"). The card
    shows `keyframes` -- how many stills, what they cost -- and nothing is
    drawn until this is pressed.

    The WHOLE strip must be affordable before anything is drawn: a strip
    that runs dry halfway leaves a scene half-anchored, so it is refused
    with "top up" instead (402 out_of_credits). Each still still holds and
    settles its own credit inside nano_banana, exactly as before; this is
    the check in front of them. Exempt accounts are never refused.

    With `{"part": n}` (2026-10-11; re-cut from #142) ONE shot's still is
    priced and drawn, and the scene's other shots are left exactly as they
    are -- so a person who is unsure of one shot can look at it for the
    price of one still before paying for the strip. The balance has to
    cover that one still only. A shot the scene does not have, one that
    already has a still, and a scene that is not timed are 409.

    NO TOKEN IS ASKED FOR HERE (2026-10-11, when the chat connector's door
    onto this same body started needing one): the price is printed on the
    button this request comes from, and pressing it is the approval.

    THE NUMBER ON THE BUTTON IS THE MOST THAT IS CHARGED (2026-10-11,
    Mike's calls; docs/BACKLOG.md #29). The job is capped at the stills the
    quote counted. Two scenes used to be priced as one still and drawn as
    more: one with no timed shots, which is drawn as a still per moment of
    its move -- now priced for up to shootgen.BEATS_PER_SHOT of them and
    marked `up_to`, charged for as many as are drawn -- and a timed scene
    edited since it was planned, now priced for every shot its prompt
    carries while none of them has a still."""
    try:
        return approve_keyframes(concept_id, account_id,
                                 part=body.part if body is not None else None)
    except ApproveRefused as e:
        return _refused(e)


class ArchiveBody(BaseModel):
    archived: bool = True


BOARD_PASS_NOTE = "passed on the board"
BOARD_PICK_NOTE = "picked on the board"
BOARD_NOTES = (BOARD_PASS_NOTE, BOARD_PICK_NOTE)


# The notes the board's two taps filed lessons under until 2026-10-11, when
# the board went (docs/tasks/task-higgsfield-shape.md): pick filed the
# prompt to be imitated, pass filed it to be avoided, neither ingested until
# the Teach tab's pass. Nothing files one any more. The names stay because
# rows carrying them are still in `winning_prompts`, and two things still
# read them: a hand edit replaces a pending board tap (_teach_prompt_edit),
# and putting a scene back withdraws one (_withdraw_board_verdict).


def _teach_prompt_edit(account_id, concept: dict, shot: dict,
                       before: str, after: str, note: str) -> bool:
    """Record a hand edit of one shot's prompt as a draft -> fix PAIR,
    pending on the Teach tab. True if one was filed (src/edit_teach.py,
    2026-09-18, Mike's call: his edits should teach; other tenants' do not).

    Gated on the account's own row and fails closed, so for every
    account that is off this is a no-op that touches nothing -- not even
    the shot, whose `model_prompt` key is written only here.

    The failed side is the model's draft: what the shot remembers as the
    last model-written text, else the text that stood before this edit.
    The fix is the edit. Same text, or no draft, teaches nothing.

    Replacement: a pending board tap (BOARD_NOTES, from before 2026-10-11)
    or an earlier pending edit on this ref is replaced (one pending pair
    per shot, latest wins); a Grade-tab verdict is never touched; anything
    ingested is never touched.
    """
    if not edit_teach.allowed(account_id):
        return False
    draft = edit_teach.draft_of(shot, before)
    after = (after or "").strip()
    if not draft or not after:
        return False
    ref = f"concept-{concept['id']}-shot-{shot.get('n') or 1}"
    existing = winners.recorded(ref)
    if any(w.get("ingested") for w in existing):
        return False
    if any((w.get("note") or "") not in BOARD_NOTES
           and not edit_teach.is_edit_note(w.get("note"))
           for w in existing):
        return False        # a considered verdict from the Grade tab wins
    if draft == after:
        # edited back to the draft: there is no fix to teach, and a pair
        # filed by an earlier edit now claims a fix the shot no longer
        # says -- withdraw it (pending only; a board tap is not ours)
        if any(edit_teach.is_edit_note(w.get("note")) for w in existing):
            winners.discard_pending(ref)
        return False
    winners.discard_pending(ref)
    winners.record_pair(
        shot.get("tool"), draft, after, note=note,
        video_ref=ref, ingest=False)
    shot[edit_teach.DRAFT_KEY] = draft
    return True


def _withdraw_board_verdict(concept: dict) -> int:
    """Undo a board ruling that has not taught anything yet. Un-picking or
    un-archiving must take its verdict with it, or the shelves learn from
    a decision that was reversed."""
    withdrawn = 0
    for sh in (concept.get("shots") or []):
        if not sh.get("prompt"):
            continue
        ref = f"concept-{concept['id']}-shot-{sh.get('n') or 1}"
        if all((w.get("note") or "") in BOARD_NOTES
               for w in winners.recorded(ref)):
            withdrawn += winners.discard_pending(ref)
    return withdrawn


@router.post("/concepts/{concept_id}/archive")
def concept_archive(concept_id: int, body: ArchiveBody,
                    account_id: int = Depends(auth.current_account_id)):
    """Hide a scene, or put it back. Never a delete: the row, its prompt
    and anything rendered from it stay where they are.

    A PLAIN HIDE SINCE 2026-10-11 (docs/tasks/task-higgsfield-shape.md,
    Mike's call: no idea board). From 2026-09-02 this was a verdict as
    well -- it filed the scene's prompt on the avoid shelf and wrote a
    "passed" lesson into the project's memory -- because an unpicked row
    was the board's one negative signal. The eval layer reads what happens
    to OUTPUTS now, so removing a scene says nothing about its writing and
    teaches nothing. A `reason` in the body is ignored.

    Putting a scene back still withdraws what an earlier pass filed and
    has not taught yet (a pending board verdict, the project's "passed"
    lesson): a scene that is back in its project must not keep a lesson
    saying it was turned down.

    account_id comes from the dependency, NOT from a bare default
    (2026-09-02). Written as `account_id: Optional[int] = None` it was a
    *query parameter* to FastAPI, so every call arrived with None and
    set_archived's `WHERE ... AND account_id IS ?` matched nothing."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", f"no concept {concept_id}")
    try:
        preprod.set_archived(concept_id, body.archived, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    if not body.archived:
        _withdraw_board_verdict(concept)
        projects.withdraw_decision(concept, "pass", account_id=account_id)
    # `ruled` stays in the answer for clients that read it; nothing rules
    return {"ok": True, "archived": body.archived, "ruled": False}


# --- the approval gate ------------------------------------------------------
# Rendering costs money, so it sits behind a priced approve -- and since
# 2026-10-11 (docs/tasks/task-higgsfield-shape.md) that approve is on the
# scene itself: GET /scenes/{id}/render is the card, POST /scenes/{id}/approve
# is the click that calls the renderer (fal). Until then a scene had to be
# picked on the board first and was approved from a Queue page; the
# `/queue/...` routes below are what is left of that. They still answer --
# the old `/ui` shell and the operator's manual import lane read them -- and
# "waiting" (`_is_waiting`) now means a scene whose render was started, or
# that a graph run parked, and that has no clip yet.


def _render_state(account_id: Optional[int] = None) -> dict:
    """The default renderer's state for the chips and older cards: what a
    clip on it is, what it costs, and whether it can happen. fal's default
    model since 2026-09-26 (it was `_runway_state`, keyed `runway`). The
    daily count reads the generations log, which a database that has never
    rendered anything does not have yet -- it degrades to None rather than
    500ing, and the gate is still reported."""
    from src import fal
    try:
        today = fal.generations_today(db_path=None, account_id=account_id)
    except Exception:
        today = None
    pick = providers.check_render_choice()
    spec = providers.model_options(pick["provider"], pick["model"])
    axis = spec["duration"]
    # what the studio shows: credits, never the provider's dollars
    # (2026-10-08) -- the same conversion pricing.display makes per render
    try:
        credits = pricing.credits_for(pricing.usd_micros(pick["estimate_usd"]))
    except pricing.PricingRefused:
        credits = None
    return {"label": providers.RENDER_LABELS.get(pick["provider"], pick["provider"]),
            "provider": pick["provider"],
            "available": fal.has_key(account_id),
            # TRUE whenever the key is: the click is the approval (2026-09-09)
            "spend_ok": fal.has_key(account_id),
            "model": pick["model"],
            # the provider's cost, for the operator's pages; the studio reads `credits`
            "estimate_usd": pick["estimate_usd"],
            "credits": credits,
            "duration": pick["duration"],
            "resolution": pick["frame"],
            # every model with what a second of it costs at its default
            # resolution -- projected off fal.VIDEO_MODELS, never a copy
            "models": [{"id": m["id"], "label": m["label"],
                        "usd_per_second": round(
                            fal.price_per_second(m["id"], m["frame"]["default"]), 4)}
                       for m in providers.models_for(pick["provider"])],
            "durations": (list(axis["values"]) if axis["kind"] != "range"
                          else list(range(axis["min"], axis["max"] + 1))),
            "today": today}


def _renderers_state(account_id: Optional[int] = None, ctx=None) -> dict:
    """Every renderer the Queue may spend on, with its gates and its legal
    options (providers.render_options) -- fal alone since 2026-09-26."""
    return providers.render_options(account_id, ctx=ctx)


def _is_waiting(concept: dict) -> bool:
    """The queue predicate on a parsed concept -- parked or picked, not
    archived, a scene, no clip yet, not marked shot by hand. ONE copy,
    shared by `_waiting` (the listing) and `queue_count` (the badge), so
    the two cannot disagree about what "waiting" means. Reads the same
    fields `_concept_card` copies onto the card."""
    shots = concept.get("shots") or [{}]
    return bool((concept.get("picked") or concept.get("parked"))
                and not concept.get("archived")
                and concept.get("is_scene")
                and not (shots[0].get("media_url") or "")
                # marked shot by hand (the camera button) -- a card you
                # already made yourself isn't waiting on you to spend
                and not concept.get("shot_done"))


def _waiting(account_id: Optional[int], include_blocked: bool = False) -> list[tuple[dict, dict]]:
    """The queue predicate -- parked by the chain or picked on the board,
    not archived, a scene, no clip yet -- as (concept, card) pairs.

    ONE definition of "waiting" for every surface that reads it: the
    Queue page and the manual-lane list must not be able to disagree
    about which shots are outstanding, or a human renders something the
    Queue never asked for. (ops/render_queue.py keeps its own copy on
    purpose and says so; it has to run without importing app/.)

    AND IT MUST CARRY REFERENCE PHOTOS (2026-09-08, Mike's call). The
    writers already archive an ungrounded concept, so in the normal case
    nothing reaches here to refuse -- this is the check that makes that
    true rather than merely likely. Three ways a row gets here without
    photos anyway: it was written before the gate existed, somebody
    un-archived it, or a later edit cleared the shot's refs. In every one
    of them the next click spends real money on a scene rendering from
    its own text.

    Deliberately NOT a prompt check as well. A prompt is on `shots_json`
    only because score_prompts put it there, and a second bar here would
    be a different opinion from the one that already ran.

    `include_blocked` (2026-09-17, Mike's call) is for the Queue PAGE
    alone. Those three ways in are real, and a picked scene that simply
    was not on the Queue read as a lost pick -- nothing anywhere said why.
    So the page may ask for the ungrounded rows too; each comes back with
    `card["blocked"]` = the gate's own reason, and is drawn locked, with
    its approve dead and "add references" on it. WHAT DID NOT CHANGE: the
    default is still spendable-only, so the manual lane (a person's hands
    on a render) never sees one; `approve_render` still asks
    `reference_gate` itself and refuses; ops/render_queue.py is untouched.
    Listing a scene is not a way to spend on it."""
    # WHICH rows first, then the rows (2026-09-25). This used to read the
    # whole board -- list_concepts' SELECT * over the newest 100, plus the
    # holds, scores and bin sources of every one -- to keep a handful:
    # ~0.9 MB of database egress per Queue visit. The window and the rule
    # are queue_count's (preprod.queue_candidates + the one `_is_waiting`),
    # so the badge and the page still count the same rows; only the cards
    # that survive are loaded whole, and only they are batched for
    # sources. Scoped in SQL by account, see above.
    out = []
    ids = [c["id"] for c in preprod.queue_candidates(account_id=account_id)
           if _is_waiting(c)]
    concepts = preprod.get_concepts(ids, account_id=account_id)
    for concept in concepts:
        # asked again on the whole row: it may have moved between the two
        # reads, and this is the copy the card is built from
        if not _is_waiting(concept):
            continue
        card = _concept_card(concept)
        # nothing reaches a spend ungrounded -- see above
        blocked = preprod.reference_gate(concept)
        if blocked and not include_blocked:
            continue
        card["blocked"] = blocked or ""
        out.append((concept, card))
    # spendable first: a locked card must never be the first thing under
    # the pointer on the page whose primary button spends money
    out.sort(key=lambda pair: bool(pair[1]["blocked"]))
    return out


def _card_quote(concept: dict, account_id: Optional[int], *, ctx=None, **pick) -> dict:
    """What approving this card would render and cost, for the pick given
    (none = the card's own default) -- pricing.display, or {"error"} when
    that intent has no price. Never raises: a card that cannot be priced
    still has to be listed, with the reason where the number would be.

    `ctx` is the listing's providers.RenderContext (see queue_pending);
    every other caller leaves it out and prices against fresh lookups."""
    if ctx is not None:
        pick["ctx"] = ctx
    try:
        return pricing.display(account_id=account_id, shot=concept["shots"][0],
                               shot_id=concept["id"], **pick)
    except Exception as e:
        return {"error": str(e)}


def _generate_node_quote(concept: dict, account_id: Optional[int]) -> dict:
    """The Director Generate node's price: ONE clip, at the adapter's own
    default length and frame, on the renderer workflow_exec_generate and
    Run all resolve (providers.renderer_for, needs=generate_from_prompt).
    {"error"} when no renderer is keyed or the intent has no price."""
    pick = providers.renderer_for(account_id, needs="generate_from_prompt")
    if pick is None:
        return {"error": "video rendering is not configured on this server"}
    return _card_quote(concept, account_id, provider=pick["provider"],
                       model=pick["model"], whole=True)


@router.get("/queue/pending")
def queue_pending(account_id: int = Depends(auth.current_account_id)):
    """What is waiting on you to spend: parked by the chain or picked on
    the board, not archived, no clip yet. Derived from the rows, so it
    survives a restart -- the jobs registry does not, and an approval
    that vanished on restart would be a queue that lies.

    Two ways in, because there are two ways a scene gets here: the
    Studio chain parks it (concept written, prompt enhanced, keyframe
    rendered -- the next step is the one that costs money), or you pick
    a text-only concept off the board yourself."""
    items = []
    # WHAT THIS ACCOUNT HOLDS, ASKED ONCE (2026-09-18). Which vendors are
    # keyed, whose key each is and today's counts are facts about the
    # account, not about a card -- but every card asked them again, per
    # vendor, each on its own connection: four cards took ~45s from a
    # laptop and the React Queue draws nothing until this answers.
    ctx = providers.render_context(account_id)
    for concept, card in _waiting(account_id, include_blocked=True):
        # THE CARD'S OWN DEFAULT RENDERER, resolved here rather than in
        # the browser. The mapping from a shot's planned tool to a
        # (provider, model) pair lives in providers.platform_default and
        # is the same one the approve route resolves with, so what the
        # card offers first and what an empty approve body would spend on
        # cannot come apart -- which they would the moment the browser
        # held its own copy of fal.PLATFORM_MODELS.
        #
        # AND ONE THIS ACCOUNT CAN RENDER (2026-09-11). The plan leads when
        # the account holds its key; when it does not, the card opens on
        # the cheapest renderer the account can use instead of on a dead
        # button -- providers.render_default, the same call an empty
        # approve body makes below.
        items.append({**card,
                      "render_default": providers.render_default(
                          card.get("tool"), account_id, ctx,
                          model=card.get("render_model")),
                      "quote": _card_quote(concept, account_id, ctx=ctx)})
    return {"items": items,
            # how many of `items` can actually be approved. The rail's badge
            # reads THIS, not len(items): it has always meant "waiting on you
            # to spend", and a locked card is waiting on references instead.
            "spendable": sum(1 for c in items if not c["blocked"]),
            "renderer": _render_state(account_id),
            "renderers": _renderers_state(account_id, ctx)}


@router.get("/queue/count")
def queue_count(account_id: int = Depends(auth.current_account_id)):
    """How many cards are waiting -- and NOTHING else (2026-09-18).

    The rail's badge is on every studio page and re-asks on every pick,
    decision and finished job. It used to call /queue/pending for one
    number, and that route prices every card: signed quotes, a render
    default and the renderer state per request. Timed against the live
    database for four cards: the rows 2.4s, the quotes 21.7s, the defaults
    12.9s, the renderer state 7.4s -- and the badge fired it unbranded on
    top of the page's own call, so the Queue page waited behind its own
    badge. This walks the same `_waiting` rows the listing does and counts
    them, so the two cannot disagree about what "waiting" means. (Since
    2026-09-21 it reads the same window through the lean
    preprod.queue_candidates and the shared `_is_waiting`, rather than
    building every card.)

    `spendable` is the badge's number (the listing's own field, same
    meaning: a card the reference gate blocks is waiting on photographs,
    not on a spend); `blocked` is the rest."""
    # 2026-09-21: counts off preprod.queue_candidates -- the same window
    # and the same `_is_waiting` + reference_gate as the listing, but only
    # the columns that decide it. Going through `_waiting` built every
    # card (holds, scores, bin sources) to throw it away, ~1 MB a poll.
    spendable = blocked = 0
    for concept in preprod.queue_candidates(account_id=account_id):
        if not _is_waiting(concept):
            continue
        if preprod.reference_gate(concept):
            blocked += 1
        else:
            spendable += 1
    return {"spendable": spendable, "blocked": blocked}


@router.get("/renders/unfinished")
def renders_unfinished(account_id: int = Depends(auth.current_account_id)):
    """The scenes a render was started on and that have no clip yet, for
    the Renders page (2026-10-11): one whose render failed or was cut
    short, a timed scene with some of its shots rendered, and anything
    picked or parked before the board went.

    Read off the ROWS, so it survives a restart -- the job registry beside
    it on that page does not, and a render that failed before a deploy
    would otherwise be listed nowhere. The same window and the same
    `_is_waiting` as the old Queue listing, with nothing priced: the page
    only links each one to its scene, where the Render button is. `blocked`
    is the reference gate's reason, or "". Spends nothing."""
    ids = [c["id"] for c in preprod.queue_candidates(account_id=account_id)
           if _is_waiting(c)]
    items = []
    for concept in preprod.get_concepts(ids, account_id=account_id):
        if not _is_waiting(concept):
            continue
        card = _concept_card(concept)
        card["blocked"] = preprod.reference_gate(concept) or ""
        items.append(card)
    return {"items": items}


@router.get("/queue/manual")
def queue_manual(account_id: int = Depends(auth.current_account_id)):
    """The same waiting shots, addressed to a pair of hands: the generic
    clip import (src/manual_lane.py). A clip rendered anywhere -- a
    vendor's web app, a local model -- is dropped on its card and filed
    free. It was the Runway Unlimited lane until 2026-09-26; Runway retired
    Unlimited in June 2026 and fal became the only API renderer.

    THE OPERATOR'S LANE, AND ONLY THE OPERATOR'S. It files a render with
    no ledger hold, so it sits behind the operator gate (the one the
    Higgsfield-MCP lane had, until that lane was removed 2026-09-28).

    So the gate is `manual_lane.manual_lane_allowed(account_id)`, called
    on the TENANT resolved server-side by `auth.current_account_id` --
    never a query parameter, a header or a body field, because all three
    are things a caller writes. Since 2026-09-08 that reads ONE column on
    the account's own row (`accounts.manual_lane_operator`, set by hand
    with `python -m src.accounts operator <slug> --on`) rather than an
    env var this process could have been started with, and membership of
    an operator's account grants nothing. A database nobody has been
    turned on in allows nobody.

    The refusal is a 404 carrying `manual_lane.REFUSAL` and nothing
    else, the same for every caller: it must read like a route that does
    not exist, and must never let someone learn from the difference
    between two refusals whether the lane exists for somebody else.

    Read-only, and its POST twin is `queue_manual_import` (2026-09-08),
    which takes the finished mp4 dropped onto a card. That used to be the
    CLI's alone -- "the file is on the human's machine, so the terminal
    is where it gets filed" -- which was true and was still a terminal
    standing between the owner and a lane he drives from a browser. A
    multipart upload carries the file perfectly well; what mattered was
    that the new door be the same door, so it re-asks this same gate and
    calls the same `import_clip` rather than growing a second way to
    write a lane row.
    """
    if not manual_lane.manual_lane_allowed(account_id):
        return _error(404, "not_found", manual_lane.REFUSAL)
    items = []
    for concept, card in _waiting(account_id):
        # PICKED scenes only (2026-09-14, Mike's call). The Queue above
        # lists what the night parked too, and approving one of those is
        # what picks it -- a one-click spend. The lane is minutes of a
        # person's hands in Chrome per clip, so it takes only what a
        # person already chose on the board (or sent from the Director);
        # a parked scene reaches it the moment it is picked.
        if not card["picked"]:
            continue
        shot = (concept.get("shots") or [{}])[0]
        try:
            duration = int(shot.get("duration"))
        except (TypeError, ValueError):
            duration = manual_lane.LANE_DURATION
        items.append({
            "concept_id": card["id"],
            "title": card["title"],
            "shot_n": shot.get("n", 1),
            "prompt": card["prompt"],
            # the frame that gets dragged into the start-image slot
            "keyframe_url": card["reference_image"],
            "duration": duration,
            "ratio": shot.get("ratio") or manual_lane.LANE_RATIO,
            "lane": manual_lane.LANES["manual"],
        })
    return {"items": items, "lane": manual_lane.LANES["manual"],
            # A clip rendered anywhere has no list of legal models to
            # check a claim against, so the card takes the model as free
            # text and the row records it unverified (render_specs).
            "models": [],
            "default_model": None,
            "import_with": "ops/render_queue.py --provider manual import"}


# --- the manual lane's drop target ------------------------------------------
# The other half of /queue/manual: the card shows what to paste and what
# to drag in, and this takes back the mp4 that comes out the far end. It
# exists so the owner never has to leave /ui for this lane -- until
# 2026-09-08 filing a clip meant a terminal and a full `ops/render_queue.py
# import` command line, which is a lot of ceremony for a file that is
# already sitting in ~/Downloads.

# What a rendered clip actually weighs: a 10s 9:16 render is tens of
# megabytes. The cap is generous against that and still bounded,
# because an unbounded multipart body is a way to fill the disk this
# app's own renders live on. Enforced while STREAMING (see below), not
# after the read, or the cap would be enforced by first accepting the
# thing it exists to refuse.
MANUAL_CLIP_MAX_BYTES = 256 * 1024 * 1024

# Enough bytes to see the ISO base-media file-type box. Byte 4..8 of an
# mp4 is the literal `ftyp`; the four after it are the major brand.
_MAGIC_BYTES = 12

# QuickTime uses the SAME ftyp box with this brand, and a .mov is not an
# mp4 however much the filename insists. Named rather than allow-listing
# mp4 brands, because that list is long, vendor-specific and still
# growing (isom, iso2, mp41, mp42, avc1, dash, mmp4...) -- an allowlist
# that refuses a real render is worse than a denylist that lets a
# rare sibling format through to ffprobe.
_NOT_MP4_BRANDS = (b"qt  ",)


def _looks_like_mp4(head: bytes) -> bool:
    """Whether these first bytes are an mp4, asked of the FILE and never
    of its name.

    The extension is the uploader's opinion; `.mp4` on a zip is one
    rename away and the browser's own content-type is no better -- both
    are client-supplied strings. The ftyp box is the file itself saying
    what it is. This is a cheap sanity check, not a parser: what it
    stops is a wrong file being copied into data/renders/ and attached to
    a shot as a render that happened.
    """
    if len(head) < _MAGIC_BYTES or head[4:8] != b"ftyp":
        return False
    return head[8:12] not in _NOT_MP4_BRANDS


async def _spool_clip(upload, dest: Path) -> Optional[JSONResponse]:
    """The upload onto disk, in chunks, refusing before it is all here.

    Returns an error response, or None when `dest` now holds the clip.
    Chunked because the two things worth refusing -- the wrong format and
    an oversized body -- are both knowable early: the magic number from
    the first chunk, the cap the moment it is crossed. Reading the whole
    body first and checking afterwards would mean holding a quarter of a
    gigabyte of somebody's mistake in memory to decide it was a mistake.
    """
    size = 0
    head = b""
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            if not head:
                head = chunk[:_MAGIC_BYTES]
                if not _looks_like_mp4(head):
                    return _error(
                        400, "not_an_mp4",
                        "that is not an mp4 -- the file's own header says so, "
                        "whatever it is called. Drop the rendered clip.")
            size += len(chunk)
            if size > MANUAL_CLIP_MAX_BYTES:
                return _error(
                    413, "clip_too_large",
                    f"clip is over {MANUAL_CLIP_MAX_BYTES // (1024 * 1024)}MB -- "
                    f"that is not a 10-second render")
            out.write(chunk)
    if not size:
        return _error(400, "empty_upload", "no file arrived")
    return None


@router.post("/queue/manual/{concept_id}/clip")
async def queue_manual_import(concept_id: int, request: Request,
                              account_id: int = Depends(auth.current_account_id)):
    """Drag the finished mp4 onto its card and it is filed. The lane's
    one writing surface on /ui.

    THE SAME GATE, NOT A SECOND ONE. `manual_lane.require` on the account
    `auth.current_account_id` resolved server-side, refusing with the
    byte-identical `manual_lane.REFUSAL` in a 404 exactly as
    `queue_manual` does -- a new door onto an operator-only lane must not
    be a weaker one, and two refusals that differ are a way to learn
    whether the lane exists here at all. The `manual_lane` capability
    flag is presentation and is deliberately not consulted here: it is a
    field in a response the caller can edit.

    THE VERIFICATION IS NOT REIMPLEMENTED HERE. `ops/render_queue.py`'s
    `import_clip` is the SINGLE IMPLEMENTATION of filing a lane clip --
    the model/ratio/duration claims checked against `src/render_specs.py`
    and REFUSED rather than clamped, the ffprobe measurement written
    beside the claim as `duration_measured_s`/`duration_source`, `_place`
    putting the file where the /renders mount can serve it, and the
    `generations` row with `cost_usd` NULL and the `manual-unlimited`
    marker that makes `ledger.is_billable` refuse a hold. This route
    calls it. It does not repeat it, and it must never grow a copy: a
    second implementation of "is this claim legal" is how the CLI and the
    UI come to disagree about what was rendered, which is the exact
    failure the checks were added to catch. Its refusals are SystemExit
    (the script's idiom) and arrive here as a 400 carrying the message
    render_specs wrote.

    WHAT THIS ROUTE OWNS, because it is about the upload and not about
    the lane: the file is an mp4 by MAGIC NUMBER rather than by name, it
    is under MANUAL_CLIP_MAX_BYTES, and it is written under a name this
    server chose (`concept<id>-shot<n>.mp4`) rather than the uploader's
    -- `_place` names the served file after the one it is handed, and a
    filename is caller-supplied text.

    A SECOND DROP ON THE SAME SHOT IS REFUSED, not silently applied.
    Dropping is a gesture, and gestures repeat: a browser can fire twice,
    a hand can drop again when the card did not visibly change, and the
    two are indistinguishable from a deliberate replacement. Applying it
    would leave the shot pointing at the newer file with an older
    `generations` row still claiming to be this shot's render -- two
    attempts recorded for one, which is exactly what the tool scoreboard
    counts -- and the first mp4 orphaned in data/renders/ where nothing
    names it. Refusing costs one clear sentence and is undoable (clear
    the shot's media_url and drop again); replacing is not. The CLI keeps
    its overwrite behaviour on purpose: a full command line naming
    --concept and --shot is a stated intention, and a drop is not.
    """
    if not manual_lane.manual_lane_allowed(account_id):
        return _error(404, "not_found", manual_lane.REFUSAL)

    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return _error(400, "no_file", "attach the rendered mp4")

    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", f"no concept {concept_id}")
    try:
        shot_n = int(form.get("shot_n") or (concept.get("shots") or [{}])[0].get("n", 1))
    except (TypeError, ValueError):
        shot_n = 1
    shot = next((s for s in concept.get("shots") or [] if s.get("n") == shot_n), None)
    if shot is None:
        return _error(404, "not_found", f"concept {concept_id} has no shot {shot_n}")
    if shot.get("media_url"):
        return _error(
            409, "already_filed",
            "this shot already has a clip -- it left the queue when the "
            "first one landed. Clear its media_url if you meant to replace it.")

    # free text: whatever rendered it, as the person says (recorded
    # unverified -- there is no list to check a clip from anywhere against)
    model = (form.get("model") or "").strip()[:120] or "unspecified"
    ratio = (form.get("ratio") or "").strip() or None
    duration_raw = (form.get("duration") or "").strip()
    try:
        duration = int(duration_raw) if duration_raw else None
    except (TypeError, ValueError):
        return _error(400, "bad_duration", f"duration {duration_raw!r} is not seconds")
    anchored = str(form.get("anchored") or "").lower() in ("1", "true", "on", "yes")

    import tempfile

    from ops import render_queue

    with tempfile.TemporaryDirectory() as tmp:
        landing = Path(tmp) / f"concept{concept_id}-shot{shot_n}.mp4"
        refused = await _spool_clip(upload, landing)
        if refused is not None:
            return refused
        try:
            filed = render_queue.import_clip(
                concept_id, shot_n, str(landing), model, None, None, anchored,
                account_id=account_id, provider="manual",
                duration=duration, ratio=ratio)
        except SystemExit as refusal:
            # render_specs said no (a model, a ratio or a length this
            # lane cannot have produced), or the concept moved under us.
            # Nothing was copied and no row was written -- that is
            # import_clip's own contract.
            return _error(400, "refused", str(refusal))
    return {"ok": True, **filed}


class ApproveBody(BaseModel):
    """WHICH RENDERER this approve spends on, and how.

    Every field is optional, and an empty body is the pre-2026-09-08
    call: it resolves to the tool the shot was actually PLANNED for
    (`providers.platform_default`), falling back to fal's default. So an older
    client keeps working, and what it gets is the plan rather than a
    hardcoded vendor -- which is what the route did before, and was
    wrong about for every concept shootgen wrote for Kling or Seedance.

    `frame` is the resolution tier ("720p") -- a pricing input, since
    fal bills per second per resolution. providers.FRAME_AXIS names it
    per renderer so the card can label its control.
    """
    provider: Optional[str] = None
    model: Optional[str] = None
    duration: Optional[int] = None
    frame: Optional[str] = None
    # The signed quotes the card showed (pricing.display's `renders[].token`,
    # one per shot to render), echoed back so the price approved is
    # provably the price rendered. REQUIRED whenever the card was handed
    # them (step 5 of docs/tasks/task-pricing-and-quotes.md): a render
    # that is billable here, on a server that can sign, is a 400
    # `missing_quote` without one. A render on a server with no
    # QUOTE_SIGNING_SECRET was never given a token and
    # approves without one -- a dev box with no secret is not locked out.
    # Tokens that ARE sent are verified either way.
    tokens: Optional[list[str]] = None


def _verify_tokens(tokens: list, priced: dict, shot: dict, shot_id: int,
                   account_id: Optional[int]) -> list:
    """Every render `priced` would make, matched to a token that verifies
    for it -- and says the same provider, model, length, frame and
    credits the card is about to spend on. Returns the Quotes in render
    order. Raises pricing.QuoteRefused (reason on it) or
    SigningUnconfigured; never returns a partial answer."""
    spare = [t for t in tokens if isinstance(t, str) and t.strip()]
    quotes = []
    for render in priced["renders"]:
        bound = None
        for token in list(spare):
            try:
                bound = pricing.verify(token, account_id=account_id, shot=shot,
                                       shot_id=shot_id, part=render["part"])
            except pricing.QuoteRefused as e:
                # another shot's token is not a refusal yet -- it may be
                # the next render's; anything else about it is
                if e.reason != "wrong_render":
                    raise
                continue
            spare.remove(token)
            break
        if bound is None:
            raise pricing.QuoteRefused(
                "missing_quote", f"no quote for shot {render['part']}" if render["part"]
                else "no quote for this render")
        same = (bound.provider == priced["provider"] and bound.model == priced["model"]
                and bound.frame == priced["frame"] and bound.seconds == render["seconds"]
                and bound.credits == render["credits"])
        if not same:
            raise pricing.QuoteRefused(
                "wrong_render", "the renderer, length or frame changed since this "
                                "price -- re-quote")
        quotes.append(bound)
    return quotes


def _quote_kw(quote) -> dict:
    """`quote=` for an adapter call, only when there is one: an unsigned
    render reaches the adapter exactly as it did before."""
    return {"quote": quote} if quote is not None else {}


def _quote_required(account_id: Optional[int], provider: str) -> bool:
    """Whether a render on `provider` must arrive with a signed quote:
    it is billable (every render, since 2026-09-26) AND this server can sign.
    The same predicate as pricing.display()'s `signed`, for the routes
    that have no display() in hand."""
    return pricing.configured() and pricing.billable(account_id, provider)


_QUEUE_ONLY = ("this render is billed in credits, and its price is quoted and approved "
               "on the scene's Render button -- open the scene and render it there")


def _quote_refused(e: Exception, account_id: Optional[int]) -> ApproveRefused:
    """A token that did not verify, as the refusal to raise: 503 with the
    generation command when nothing can be verified here, else 400 with
    the refusal's own reason as the code. wrong_account is logged at
    warning -- it cannot happen through the UI, so it is a replay."""
    if isinstance(e, pricing.SigningUnconfigured):
        return ApproveRefused(503, "signing_unconfigured", str(e))
    if e.reason == "wrong_account":
        print(f"[quote] wrong_account: a quote issued to another tenant was "
              f"presented by account {account_id!r}", file=sys.stderr)
        return ApproveRefused(400, "wrong_account", "this quote isn't valid -- get a fresh price")
    return ApproveRefused(400, e.reason, str(e))


def _quote_refusal(e: Exception, account_id: Optional[int]):
    """The response form of _quote_refused, for the routes that answer
    HTTP directly."""
    return _refused(_quote_refused(e, account_id))


@router.get("/scenes/{concept_id}/render")
def scene_render_state(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """Everything the Render card on a scene draws, in one answer
    (2026-10-11, docs/tasks/task-higgsfield-shape.md step 1): the scene as
    a card -- its shots, stills, clips, references, the keyframes still to
    draw and what they cost -- the renderer it opens on, the price of that
    pick with its signed tokens, why it cannot be rendered when it cannot
    (`blocked` = the reference gate's own reason), and the renderers this
    account can use with each model's legal lengths and frames.

    It is the Queue listing's one card, asked for by id: the same
    `_concept_card`, `providers.render_default` and `_card_quote`, so the
    price on a scene and the price the approve checks are one computation.
    Any scene can be asked about -- no pick comes first. Spends nothing and
    writes nothing; changing the pick asks /quote below."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None or not concept.get("shots"):
        return _error(404, "not_found", "no such scene")
    ctx = providers.render_context(account_id)
    card = _concept_card(concept)
    card["blocked"] = preprod.reference_gate(concept) or ""
    card["render_default"] = providers.render_default(card.get("tool"), account_id, ctx,
                                                      model=card.get("render_model"))
    card["quote"] = _card_quote(concept, account_id, ctx=ctx)
    # what a look at each landed clip saw (src/render_qc.py), by shot
    from src import render_qc
    card["checks"] = render_qc.for_concept(concept_id, account_id=account_id)
    return {"scene": card,
            "renderer": _render_state(account_id),
            "renderers": _renderers_state(account_id, ctx)}


@router.get("/scenes/{concept_id}/quote")
@router.get("/queue/{concept_id}/quote")             # the old name, kept one release
def scene_quote(concept_id: int, provider: Optional[str] = None,
                model: Optional[str] = None, duration: Optional[int] = None,
                frame: Optional[str] = None,
                account_id: int = Depends(auth.current_account_id)):
    """What approving this scene WITH THIS PICK would render and cost --
    pricing.display for the same four fields the approve body takes, so
    the button's number and the approve's number are one computation
    (2026-09-17). The Render card already carries this for its default
    pick; it asks here when the person moves a control, instead of
    doing the arithmetic -- and the window-fitting -- a second time in
    JavaScript. Spends nothing and writes nothing."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None or not concept.get("shots"):
        return _error(404, "not_found", "no such concept")
    try:
        return pricing.display(account_id=account_id, shot=concept["shots"][0],
                               shot_id=concept_id, provider=provider, model=model,
                               seconds=duration, frame=frame)
    except ValueError as e:
        return _error(400, "bad_render_choice", str(e))


@router.post("/scenes/{concept_id}/approve")
@router.post("/queue/{concept_id}/approve")          # the old name, kept one release
def scene_approve(concept_id: int, body: Optional[ApproveBody] = None,
                  account_id: int = Depends(auth.current_account_id)):
    """Approve = render. The priced button on the scene is the whole
    decision (2026-10-11): there is no board to pick it on first.

    The scene's stored prompt goes through the renderer picked on the
    card (anchored on its keyframe when it has one) and the clip comes
    back attached to the shot. picked_at is stamped here and nowhere else,
    and means "rendered on purpose".

    It deliberately does NOT archive the siblings any more. That tidy-up
    inferred "you have answered this batch" from which rows were picked,
    which was safe while picking was a separate bulk step done first:
    pick two, approve one, both survived. Now that approval is the pick,
    approving take 1 would archive takes 2-4 out from under you -- and
    nondeterministically, since it ran after the render returned ~90s
    later.  Rejecting archives explicitly, and that is the honest signal.

    ANY REGISTERED RENDERER, not just Runway (2026-09-08, Mike's call).
    The old body named `runway` in three places -- the key check, the
    render call and the button's price -- so the one surface that spends
    money could reach exactly one of four working adapters, and a scene
    planned for Kling was rendered on Runway without ever saying so. It
    dispatches through providers.VIDEO_PROVIDERS now, which is the same
    registry orchestrator.generate_render's connectors dict is built
    from, so the nightly graph and this button can no longer disagree
    about which vendor a tool name means.

    WHAT DID NOT CHANGE, and each of these is load-bearing:
      * the gates run in the same order and refuse the same things --
        no prompt, no reference photos (`not_queued` went on 2026-10-11:
        a scene no longer has to be picked first);
      * the reference gate is asked HERE and not only in the listing,
        because this route is reachable by id and a concept can lose its
        refs between the two requests;
      * the pick is recorded BEFORE the spend, so a render that fails
        halfway still leaves the row saying you chose this one;
      * the spend approval is still checked inside the adapter's own
        generate_video and NOT here. That looks like something to hoist
        up for a nicer error, and it is not: the gate has to sit where
        the money is spent so no caller can spend around it, and a
        route-level copy would be a second opinion that can drift from
        the one that actually holds.

    WHAT SATISFIES THAT APPROVAL CHANGED (2026-09-09, Mike's call). It
    used to be `*_SPEND_OK=1` in the server's environment, which meant
    this button did nothing until somebody restarted the server with a
    variable set -- and once set for one render it stayed set for the
    session, which is the "approval that's always on" the gate was
    written to prevent, reached the long way round. The click IS the
    approval now: this route passes `approved=True` and the unattended
    callers (orchestrator.py, autopilot.py) pass nothing, so they still
    need their own env flag on purpose. The daily caps are untouched and
    are now the only automatic wall -- see generative.cap_error.
    """
    try:
        return approve_render(concept_id, account_id, body)
    except ApproveRefused as e:
        return _refused(e)


def approve_render(concept_id: int, account_id: Optional[int],
                   body: Optional[ApproveBody] = None) -> dict:
    """scene_approve's body as a callable (2026-10-07): the route and the
    MCP `approve` tool run this one function. `body` may be an ApproveBody
    or a plain dict of its fields. Returns the route's JSON; raises
    ApproveRefused with the status and code the route answers."""
    if isinstance(body, dict):
        body = ApproveBody(**body)
    body = body or ApproveBody()
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        raise ApproveRefused(404, "not_found", "no such concept")
    if not concept["shots"]:
        raise ApproveRefused(400, "no_prompt", "this concept carries no prompt to render")
    # NO PICK IS ASKED FOR (2026-10-11, docs/tasks/task-higgsfield-shape.md):
    # until then a scene had to be picked on the board, or parked by a graph
    # run, before this would spend on it (400 `not_queued`). The board is
    # gone; the priced button on the scene is the decision, and every other
    # refusal below is unchanged and in the same order.
    #
    # The reference gate is asked HERE, where the money is spent: the price
    # and the approve are two requests, a scene can lose its refs between
    # them, and this function is reachable by id from the chat connector.
    ungrounded = preprod.reference_gate(concept)
    if ungrounded:
        raise ApproveRefused(400, "no_reference",
                             f"this concept has no reference photos attached "
                             f"({ungrounded}) — rendering it would generate from "
                             f"text alone. Attach references and try again.")

    shot = concept["shots"][0]
    shot_n = shot.get("n", 1)
    # A SCENE OF SEVERAL TIMED SHOTS renders as that many clips, one after
    # another (2026-09-10, src/timeline.py). What decides it is the prompt
    # carrying windows, not whether the timeline happens to be planned yet
    # -- a stale or missing one is planned inside the job, before the first
    # clip, so the card can never render the old split of an edited scene.
    # pricing.windows_to_render is that rule; `timed` below is its answer.

    # The plan is the default, the body overrides it -- and BOTH are
    # resolved, checked and priced in one place (src/pricing.py,
    # 2026-09-17). A named provider is honoured exactly; an empty body
    # resolves as the card's default did (providers.render_default: the
    # plan if this account can render it, else the cheapest renderer it
    # can); a shot's planned tool means one model here and in
    # orchestrator.generate_render (providers.platform_default). The card
    # printed pricing.display() for this same intent, so the number on the
    # button and the number in this response are one computation.
    #
    # A timed scene's LENGTHS are its windows', fitted to the model -- the
    # card's duration does not apply, so it is not checked either.
    try:
        priced = pricing.display(account_id=account_id, shot=shot, shot_id=concept_id,
                                 provider=body.provider, model=body.model,
                                 seconds=body.duration, frame=body.frame)
    except ValueError as e:
        # REFUSED, never clamped: a length or a frame outside the model's
        # own set is evidence the card and the model have come apart, and
        # quietly rounding it spends real money on something nobody
        # picked. (The adapters clamp internally -- that is their contract
        # with the nightly graph, which has no human to refuse to.)
        raise ApproveRefused(400, "bad_render_choice", str(e))
    # priced["signed"] is "billable AND a secret to sign with" -- exactly
    # the renders display() minted a token for, so the requirement and the
    # offer are one predicate and cannot disagree
    # The verified Quotes are KEPT (2026-09-21): they used to be checked and
    # dropped, and the adapter then held its own estimate -- the same number
    # only because both go through pricing.credits_for. Keyed by part (None
    # for a whole scene), each rides into the render it priced, where
    # src/charge.py holds `quote.credits` rather than re-deriving them.
    quotes: dict = {}
    if priced["signed"] or body.tokens:
        try:
            quotes = {q.part: q for q in _verify_tokens(
                body.tokens or [], priced, shot, concept_id, account_id)}
        except (pricing.QuoteRefused, pricing.SigningUnconfigured) as e:
            raise _quote_refused(e, account_id)
    timed = priced["timed"]
    choice = {"provider": priced["provider"], "model": priced["model"],
              "duration": None if timed else priced["durations"][0],
              "frame": priced["frame"], "estimate_usd": priced["estimate_usd"]}
    if timed:
        choice["durations"] = priced["durations"]

    module = providers.VIDEO_PROVIDERS[choice["provider"]]
    label = providers.RENDER_LABELS.get(choice["provider"], choice["provider"])
    # the operator's key -- the only one since 2026-09-26
    if not module.has_key(account_id):
        raise ApproveRefused(503, "renderer_unavailable",
                             f"{label} is not configured on this server (FAL_KEY is unset)")

    # the frame axis is a resolution tier ("720p") -- providers.FRAME_AXIS
    frame_kw = "resolution"
    render_kwargs = {"model": choice["model"],
                     "duration": choice["duration"],
                     frame_kw: choice["frame"]}

    # `picked_at` is stamped here and nowhere else now: it means "this scene
    # was rendered on purpose". BEFORE the spend, not after it: a render
    # that fails halfway still leaves the row saying it was chosen. The
    # project the scene is filed under learns the same thing once (it used
    # to learn it from the board's pick).
    if not concept.get("picked"):
        preprod.set_picked(concept_id, True, account_id=account_id)
        projects.remember_decision(concept, "pick", account_id=account_id)

    def work(job):
        if timed:
            return _render_timeline(job, concept_id, shot_n, module, label, choice,
                                    frame_kw, account_id, quotes=quotes)
        jobs.progress(job, 0.2, f"rendering via {label} ({choice['model']})")
        result = module.generate_for_shot(
            concept_id, shot_n, db_path=None,
            resolve_photo=_resolver(account_id),
            # A PERSON PRESSED THE PRICED BUTTON. That is the approval
            # the adapter's gate is asking for -- see spend_approved.
            approved=True,
            account_id=account_id,
            # the price this click was shown, when it was shown one
            **_quote_kw(quotes.get(None)),
            **render_kwargs)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "render failed")
        _check_clip(job, concept_id, None, result, concept["shots"][0].get("prompt") or "",
                    account_id)
        return {"ref_id": concept_id, "detail": "clip attached"}

    job = jobs.start("render",
                     f"approved · {concept['title']} · {label} {choice['model']}",
                     work, account_id=account_id)
    # The job names its scene FROM THE START, not only in its result: the
    # Render card reads the live jobs to say "rendering" on the scene that
    # is being rendered, and a failed render's row links back to its scene.
    jobs.update(job["id"], ref_id=concept_id)
    # `render` keeps the shape clients already read; `quote` beside it is
    # the same intent as pricing.display printed it on the card
    return {"job_id": job["id"], "render": choice, "quote": priced}


def _render_timeline(job, concept_id: int, shot_n, module, label: str, choice: dict,
                     frame_kw: str, account_id: int, quotes: Optional[dict] = None) -> dict:
    """Render a timed scene ONE SHOT AT A TIME, in order (2026-09-10).

    Each part is its own call through the SAME adapter entry point a whole
    scene goes through (`generate_for_shot(..., part=n)`), so every wall is
    unchanged per clip: the spend approval inside generate_video, the daily
    cap before each call, a generations row per attempt. Its length is its
    window fitted to the model (timeline.fit_seconds), its anchor its own
    still, its prompt the scene's continuity followed by that shot.

    Parts that already have a clip are skipped, and the loop stops at the
    first failure -- usually the daily cap -- keeping what rendered. The
    scene stays in the Queue until every part has its clip, so approving
    again renders the rest rather than paying for shot 1 twice."""
    jobs.progress(job, 0.05, "planning the shots")
    tl = timeline.ensure(concept_id, shot_n, resolve_photo=_resolver(account_id),
                         account_id=account_id)
    if not tl:
        raise RuntimeError("this scene's shots could not be planned -- open it in "
                           "Director or approve again")
    axis = providers.model_options(choice["provider"], choice["model"])["duration"]
    parts = tl.get("parts") or []
    todo = [p for p in parts if not p.get("media_url")]
    done = len(parts) - len(todo)
    for i, part in enumerate(todo):
        seconds = timeline.fit_seconds(axis, part.get("seconds"))
        jobs.progress(job, 0.1 + 0.85 * i / max(1, len(todo)),
                      f"shot {part['n']} of {len(parts)} · {seconds}s via {label} "
                      f"({choice['model']})")
        result = module.generate_for_shot(
            concept_id, shot_n, db_path=None, part=part["n"],
            resolve_photo=_resolver(account_id),
            approved=True,          # the priced button -- see scene_approve
            account_id=account_id,
            # THIS shot's quote (one token per render). A part the re-plan
            # above renumbered has none and falls back to the estimate.
            **_quote_kw((quotes or {}).get(part["n"])),
            model=choice["model"], duration=seconds, **{frame_kw: choice["frame"]})
        if not result.get("ok"):
            raise RuntimeError(
                f"shot {part['n']} of {len(parts)} failed: "
                f"{result.get('error') or 'render failed'} -- {done} of {len(parts)} "
                f"rendered; approve again to render the rest")
        done += 1
        _check_clip(job, concept_id, part["n"], result,
                    part.get("prompt") or part.get("text") or "", account_id)
    return {"ref_id": concept_id, "detail": f"{done} of {len(parts)} shots rendered"}


def _check_clip(job, concept_id: int, part, result: dict, prompt: str,
                account_id: Optional[int]) -> None:
    """Watch a clip that just landed against its ask (src/render_qc.py):
    free, advice only, never raises, and the job's line says so while it
    looks. PHANTRA_RENDER_QC=0 skips it."""
    from src import brand_kits, render_qc
    if account_id is None or not render_qc.enabled():
        return
    try:
        jobs.update(job["id"], detail=f"checking shot {part}" if part else "checking the clip")
        kit = brand_kits.for_concept(concept_id, account_id=account_id)
        render_qc.check_shot(concept_id, part, result, prompt=prompt,
                             account_id=account_id, kit=kit)
    except Exception as e:                       # advice, never the render's failure
        print(f"  render check skipped: {type(e).__name__}: {e}", file=sys.stderr)


@router.post("/queue/{concept_id}/reject")
def queue_reject(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """Rejected here means: not worth the spend. Any pick comes off and
    the concept archives, so it reads as generated-but-not-picked in
    pick_rate -- which is the truth about it. This is the only thing
    that takes a sibling off the board now; approving no longer infers
    it (see scene_approve)."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    preprod.set_picked(concept_id, False, account_id=account_id)
    preprod.set_archived(concept_id, True, account_id=account_id)
    return {"ok": True, "pick": preprod.pick_rate(account_id=account_id)}


class ShotBody(BaseModel):
    shot: bool = True


@router.post("/queue/{concept_id}/shot")
def queue_mark_shot(concept_id: int, body: ShotBody,
                    account_id: int = Depends(auth.current_account_id)):
    """The camera: you made this yourself, outside the render pipeline --
    a render in a vendor's own app, a hand-tweaked prompt, your own stills, cut
    together by hand -- and it worked. `shot_done` is the ground-truth
    column shoot_rate() has always read (preprod.py's own docstring:
    "you generate several concepts and go shoot some of them; that
    choice is ground truth about what's actually worth making"). It
    predates the render pipeline and was never wired to a button on
    /ui -- this is that wire, not a new label.

    Deliberately does nothing else. It does NOT touch picked_at (a
    manual shoot proves the idea, not that the system's OWN automated
    render was good -- scene_approve already owns that meaning and
    stays as-is). It does NOT attach media -- paste the finished clip's
    URL through /concepts/{id}/shots/{n}/media, same as any clip
    rendered by hand. And it does NOT rule for RAG -- grade the corrected
    prompt and the reason it worked on the Grade/Teach tabs same as
    anything else; this button only marks that the shoot happened, not
    what it taught. Toggleable, so a wrong click un-marks it.

    Marking it shot takes the card off the Queue's pending list (see
    queue_pending's filter) -- one you already made by hand isn't
    waiting on you to spend anything."""
    try:
        preprod.mark_shot(concept_id, body.shot, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"ok": True, "shot_done": body.shot,
            "shoot": preprod.shoot_rate(account_id=account_id)}


class ConceptRefsBody(BaseModel):
    refs: list[str] = []


@router.post("/concepts/{concept_id}/refs")
def concept_refs(concept_id: int, body: ConceptRefsBody, account_id: int = Depends(auth.current_account_id)):
    """The reference photos a scene grounds on -- a LIST, because a face
    and a jacket are two references. Stored on the shot itself, so they
    ride into the enhance, the keyframe and the clip."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None or not concept["shots"]:
        return _error(404, "not_found", "no such scene")
    shots = [dict(s) for s in concept["shots"]]
    shots[0]["refs"] = [asset_shelf.storable_ref(r)
                        for r in body.refs if r][:MAX_IMAGE_REFS]
    # a plan dict, not a bare list: update_concept_shots re-validates the
    # whole plan, and carrying the existing warnings/duration through
    # keeps attaching a reference from rewriting anything else
    preprod.update_concept_shots(
        concept_id,
        {"shots": shots, "duration": concept.get("duration")},
        warnings=concept.get("warnings") or [], account_id=account_id)
    return {"ok": True, "refs": shots[0]["refs"]}


@router.get("/concepts/{concept_id}")
def concept_detail(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """The scene board's data: the full shot list, each shot carrying its
    stored per-tool AI prompt plus the OpenArt Director rendering
    (pure text composition, zero model calls). This is the surface the
    render-by-hand loop works from: copy a shot's prompt, generate in
    the tool's own UI, paste the rendered clip's URL back onto the shot."""
    from src import shootgen

    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    # director_prompt (the OpenArt rendering) ships with in-progress
    # shootgen work; until that lands, the field is empty and the UI
    # renders no Director toggle -- degrade, don't crash.
    director = getattr(shootgen, "director_prompt", None)
    shots = []
    for shot in concept.get("shots") or []:
        shots.append({**shot,
                      "director_prompt": director(shot, concept) if director else ""})
    card = _concept_card(concept)
    return {**card, "duration": concept.get("duration"),
            "edit_note": concept.get("edit_note") or concept.get("edit"),
            "shots": shots,
            # the render button's copy is server-sourced: availability,
            # the spend gate's state, and what one clip would cost
            "renderer": _render_state(account_id),
            # ... and what the Generate node would ACTUALLY spend on, priced
            # by pricing.display for this concept
            "generate": _generate_node_quote(concept, account_id)}


class ShotMediaBody(BaseModel):
    url: str


@router.post("/concepts/{concept_id}/shots/{shot_n}/media")
def shot_media_attach(concept_id: int, shot_n: int, body: ShotMediaBody,
                      account_id: int = Depends(auth.current_account_id)):
    """Attach the rendered clip's URL to one shot -- the paste-back half
    of the render-by-hand loop, and the field autopilot.build_plan() requires
    before it will ever emit a post action."""
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        return _error(400, "invalid_url",
                      "paste the clip's public http(s) URL")
    try:
        preprod.set_shot_media_url(concept_id, shot_n, url, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"concept_id": concept_id, "shot_n": shot_n, "media_url": url}


class DirectBody(BaseModel):
    note: str


def _teach_direct_note(account_id, concept_id: int, before: dict, note: str) -> int:
    """After a Direct note revised the scene: for every shot whose prompt
    changed, file (prompt before the note -> revision) as a pending pair
    carrying the note, through the same gate and rules as a hand edit.
    Returns how many were filed; 0 for an account that is off.

    The revision is model-written, but the NOTE is the person's stated
    reason, which is the lesson. The model saw the whole shot JSON and
    may echo `model_prompt` back; it is dropped here because a model
    just rewrote the shot, so the next hand edit must snapshot afresh.
    """
    if not edit_teach.allowed(account_id):
        return 0
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return 0
    shots = concept.get("shots") or []
    filed = 0
    dirty = False
    for shot in shots:
        n = shot.get("n")
        old = before.get(n)
        if old is None:
            continue
        if edit_teach.DRAFT_KEY in shot:
            edit_teach.forget_draft(shot)
            dirty = True
        # the draft for THIS pair is the pre-note text, never a remembered
        # one: forget_draft above makes draft_of read `old`
        if _teach_prompt_edit(account_id, concept, shot, old,
                              shot.get("prompt") or "", edit_teach.direct_note(note)):
            filed += 1
            # _teach_prompt_edit remembers the pre-note text as the draft;
            # the revision is the model's, so that memory is wrong here
            edit_teach.forget_draft(shot)
            dirty = True
    if dirty:
        preprod.update_concept_shots(
            concept_id,
            {"duration": concept.get("duration"), "shots": shots,
             "edit": concept.get("edit_note") or concept.get("edit")},
            warnings=concept.get("warnings"), account_id=account_id)
    return filed


@router.post("/concepts/{concept_id}/direct")
def concept_direct(concept_id: int, body: DirectBody, account_id: int = Depends(auth.current_account_id)):
    """Director mode: one note revises the stored scene in place --
    validated, attachments carried over, refused when the revision
    comes back broken. One billed call per note."""
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    note = body.note.strip()
    if not note:
        return _error(400, "empty_note", "an empty note directs nothing")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")

    before_shots = {s.get("n"): (s.get("prompt") or "")
                    for s in (concept.get("shots") or [])}

    def work(job):
        from google import genai

        from src import director
        jobs.progress(job, 0.3, "revising the scene")
        # account_id was not passed here before 2026-09-18, so on an owned
        # row (every live concept) the job died with "no concept N" while
        # the route's own lookup above had just found it
        result = director.direct_scene(
            concept_id, note, gemini_client=genai.Client(api_key=api_key),
            db_path=None, account_id=account_id)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "direction failed")
        detail = result.get("summary") or "revised"
        if result.get("warnings"):
            detail += f" · {len(result['warnings'])} warning(s)"
        taught = _teach_direct_note(account_id, concept_id, before_shots, note)
        if taught:
            detail += f" · {taught} pair(s) on the Teach tab"
        return {"ref_id": concept_id, "detail": detail}

    job = jobs.start("direct", f"direct · {note[:60]}", work, account_id=account_id)
    return {"job_id": job["id"]}


@router.post("/concepts/{concept_id}/shots/{shot_n}/refine")
def shot_refine(concept_id: int, shot_n: int, account_id: int = Depends(auth.current_account_id)):
    """Technique-aware polish for one shot's AI prompt, grounded in the
    ai_prompting shelf. Falls back to unchanged on anything broken."""
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        from google import genai

        from src import director
        jobs.progress(job, 0.3, "polishing against technique references")
        result = director.refine_shot_prompt(
            concept_id, shot_n, gemini_client=genai.Client(api_key=api_key),
            db_path=None, account_id=account_id)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "polish failed")
        return {"ref_id": concept_id, "detail": result.get("summary") or "polished"}

    job = jobs.start("refine", f"polish · shot {shot_n}", work, account_id=account_id)
    return {"job_id": job["id"]}


@router.post("/concepts/{concept_id}/shots/{shot_n}/generate")
def shot_generate(concept_id: int, shot_n: int, account_id: int = Depends(auth.current_account_id)):
    """One click, one render: the shot's stored prompt through fal on the
    model its planned tool binds to (providers.render_default -- the same
    answer the Queue card opens on), anchored on its reference_image when
    set, the clip downloaded, logged as a generations row, and attached to
    the shot.

    Billed, held and capped. The click is the spend approval (2026-09-09)
    -- this route passes approved=True into generate_for_shot, and the gate
    itself still lives inside generate_video, with the credit hold, so
    nothing here spends around it. FAL_DAILY_CAP is what stops a stuck
    loop."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    shot = next((s for s in concept.get("shots") or [] if s.get("n") == shot_n), None)
    planned = providers.render_default((shot or {}).get("tool"), account_id,
                                       model=(shot or {}).get("render_model"))
    pick = providers.renderer_for(account_id, planned["provider"], planned["model"])
    if pick is None:
        return _error(503, "renderer_unavailable", "FAL_KEY is not set")
    # No surface prints a price for this button and no front end calls it
    # any more, so it mints and takes no quote: when the server signs
    # quotes, a billable render -- every render, since 2026-09-26 -- is
    # sent to the Queue (step 5). A server that cannot sign renders here.
    if _quote_required(account_id, pick["provider"]):
        return _error(400, "missing_quote", _QUEUE_ONLY)
    module = providers.VIDEO_PROVIDERS[pick["provider"]]

    def work(job):
        jobs.progress(job, 0.2, f"rendering via {pick['model']}")
        result = module.generate_for_shot(
            concept_id, shot_n, db_path=None, model=pick["model"],
            resolve_photo=_resolver(account_id), approved=True,
            account_id=account_id)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "render failed")
        return {"ref_id": concept_id,
                "detail": f"clip attached to shot {shot_n}"}

    job = jobs.start("render", f"{pick['model']} · {concept['title']} shot {shot_n}",
                     work, account_id=account_id)
    return {"job_id": job["id"]}


# Cap what one Create sends to Gemini, same as the composer's MAX_ATTACH
# and scene_chain.MAX_REFS. 6 -> 12 on 2026-09-10: the extras ground the
# writing and the per-shot planner; Mike narrows them afterwards.
MAX_IMAGE_REFS = 12

_PHOTO_ROOTS = {
    "locations": LOCATIONS_DIR,
    "characters": CHARACTERS_DIR,
    "props": PROPS_DIR,
}


# Composer uploads. A photo dragged onto the composer is a reference
# in exactly the sense a picked asset photo is -- it just had nowhere to
# live, so it grounded one Gemini call and vanished. It lives here now,
# beside the rendered clips, under the same gitignored data/ roof.
#
# The directory, the content-addressed name and the JPEG normalisation
# moved to src/refbin.py once the scout started writing research images
# into the same bin: src/ cannot import app/, so leaving the rule here
# would have meant a second implementation of it, and a second writer
# that drifts is how one photo ends up stored under two names. These
# two names stay as the app-side spelling -- app/main.py mounts
# UPLOAD_REFS_DIR, and several routes call _save_upload_ref.
UPLOAD_REFS_DIR = refbin.REFS_DIR


def _save_upload_ref(jpeg: bytes) -> Optional[str]:
    """Persist one uploaded reference, return the URL it rides on.
    Best-effort: a full disk costs the reference, never the scene that
    was being written."""
    return refbin.save(jpeg)


@router.post("/refs/upload")
async def refs_upload(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Upload reference photos from disk, return the URLs they ride on.

    The Director canvas's reference cards only took a pasted URL
    (2026-09-18, Mike: "I'd have to paste a url"). This is the same
    bin the composer's uploads land in -- normalised to JPEG,
    content-addressed, mirrored to R2 -- so a frame added here resolves
    exactly like one attached at Create, on this machine and on the
    deploy. Field `photos` (the element create routes' name -- `files`
    is the concept writers' collector, and the drift guard keeps that
    one read to one place), up to MAX_IMAGE_REFS; anything that is not
    a readable image is skipped and counted, never a 500. This writes
    no concept: the card's frames reach a shot through the graph."""
    form = await request.form()
    urls: list = []
    skipped = 0
    for upload in form.getlist("photos"):
        if not getattr(upload, "filename", ""):
            continue
        if len(urls) >= MAX_IMAGE_REFS:
            skipped += 1
            continue
        jpeg = _to_jpeg(await upload.read())
        saved = refbin.save(jpeg, account_id) if jpeg else None
        if saved:
            if saved not in urls:
                urls.append(saved)
        else:
            skipped += 1
    return {"urls": urls, "skipped": skipped}


def _resolve_asset_photo(url_path: str) -> Optional[Path]:
    """A reference URL -> the file on disk, or None.

    Delegates to src/asset_shelf.resolve_photo (2026-08-31). The rule
    moved down there because the nightly graph resolves references at
    6am with no web app running and cannot call this; two copies of a
    path-traversal guard is the shape of bug where one of them is weaker
    and nobody notices. Behaviour is unchanged: both URL shapes, the
    ?thumb strip, and anything escaping its root silently dropped.

    Composer uploads (/refs/<name>.jpg) resolve here too, because every
    caller that turns a reference URL into bytes -- the scene writer,
    the Director graph's enhance/keyframe/clip nodes -- goes through
    this one function. The research scout writes into the same bin, so
    a crawled image needs no new route and no new resolver.
    """
    # roots injected (the tests point them at a tmp_path); the refs
    # directory deliberately NOT injected -- src/refbin.py owns it in
    # both directions, so the reader has to follow refbin.REFS_DIR or
    # it moves while the writer stays on the real folder.
    return asset_shelf.resolve_photo(url_path, roots=_PHOTO_ROOTS)


def _resolver(account_id: Optional[int]):
    """The reader every stage is handed, bound to WHOSE photos it may
    read (2026-10-11, docs/BACKLOG.md #25): reference URL -> file or None.

    `_resolve_asset_photo` above names no account, and the element
    folders it reads are named by slug alone -- `characters/me/photo.jpg`
    is whichever account wrote it last. So a stage is never handed that
    function any more. It is handed this: the folder only where the
    folder is this account's store, and the account's own bucket keys
    everywhere else (asset_shelf.resolver holds the rule; the disk half
    stays this module's, so the tests' tmp roots are still honoured)."""
    return asset_shelf.resolver(account_id, disk=lambda url: _resolve_asset_photo(url))


MAX_VIDEO_REFS = 2   # a video ref is heavy; two is plenty of grounding

# Under this, a clip rides inline as Part.from_bytes -- the same shape
# image refs use, just a video mime. Over it, the Gemini Files API is
# the documented path (inline requests cap out around 20MB total).
INLINE_VIDEO_LIMIT = 19_000_000

VIDEO_MIMES = {
    ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".webm": "video/webm", ".m4v": "video/x-m4v",
}


def _video_mime(filename: str) -> Optional[str]:
    from pathlib import PurePosixPath
    return VIDEO_MIMES.get(PurePosixPath(filename or "").suffix.lower())


def video_part(client, data: bytes, mime: str):
    """One video reference -> something a Gemini call can take as vision
    input. Small clips ride inline as bytes; anything bigger goes
    through the Files API (upload, poll until ACTIVE, hand back the file
    handle -- the SDK accepts it directly in contents). None on any
    failure: a reference is an enhancement, never a gate."""
    import io
    import time as _time

    from google.genai import types

    try:
        if len(data) <= INLINE_VIDEO_LIMIT:
            return types.Part.from_bytes(data=data, mime_type=mime)
        handle = client.files.upload(file=io.BytesIO(data),
                                     config={"mime_type": mime})
        deadline = _time.time() + 120
        while getattr(handle.state, "name", str(handle.state)) == "PROCESSING" \
                and _time.time() < deadline:
            _time.sleep(2)
            handle = client.files.get(name=handle.name)
        if getattr(handle.state, "name", str(handle.state)) != "ACTIVE":
            return None
        return handle
    except Exception:
        return None


# Photo formats Pillow reads out of the box. IMAGE_EXTENSIONS also
# lists .heic -- correctly, an iPhone export IS a photo and belongs in
# the gallery -- but Pillow only decodes it with pillow-heif present,
# and a reference that fails to decode is dropped SILENTLY, which is
# the worst way for a reference to fail. Preferring a sibling the
# renderer can definitely read costs nothing when there is one.
_DECODES_NATIVELY = {".jpg", ".jpeg", ".png", ".webp"}


def _to_jpeg(data: bytes) -> Optional[bytes]:
    """Any readable upload -> upright RGB JPEG. See src/refbin.to_jpeg
    for why the EXIF transpose has to happen before the RGB convert."""
    return refbin.to_jpeg(data)


def scene_grounding(spark, client=None) -> str:
    """
    Everything a scene generation grounds on, composed at the edge (the
    reference_block contract: generators stay hermetic). Degrades to ""
    rather than failing a generation.

    Until 2026-10-13 a brand's inspiration accounts rode in front of the
    retrieved references. That list was one shared table keyed by brand,
    so with one label for everybody it would have steered every account's
    scenes with one person's handles; it is gone (Mike's call, D4 of
    docs/tasks/task-remove-brand-labels.md).
    """
    from src import shootgen

    return shootgen.reference_block(spark=spark, client=client, db_path=None)


@router.post("/pipeline/run")
async def pipeline_run(request: Request, account_id: int = Depends(auth.current_account_id)):
    """The Create button: one full concept from the composer's prompt,
    grounded exactly the way /concepts/generate grounds -- reference
    block first, then the generator. Multipart: `prompt` plus optional
    attached media (`files` uploads and `asset_photos` picked from the
    media panel), which ride into the generation as vision input.
    Billed, so it only exists when the key does."""
    form = await request.form()
    prompt = (form.get("prompt") or "").strip()
    if not prompt:
        return _error(400, "empty_prompt", "a prompt is required")
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")

    image_refs, refs, _ = await _collect_refs(form, account_id=account_id)

    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        return _brief_work(job)

    def _brief_work(job):
        from google import genai

        from src import scene_chain, shootgen
        gemini_client = genai.Client(api_key=api_key)
        jobs.progress(job, 0.15, "grounding in references")
        references = scene_grounding(prompt, client=gemini_client)
        # Named in the prompt, or picked (asset_photos/uploads) -- the
        # same rule Studio's Create button follows, not the old
        # cast=None default that showed this brief every character and
        # prop on file regardless of whether the brief named any of
        # them (2026-09-03, Mike's call). Split out of scene_chain.ground()
        # so this doesn't also re-run reference_block, which scene_grounding
        # already queried above.
        try:
            cast, _locs = scene_chain.scoped_cast_and_locations(
                prompt,refs, db_path=None, account_id=account_id)
        except Exception:
            cast = None
        jobs.progress(job, 0.35,
                      "writing the scene prompt"
                      + (f" · {len(image_refs)} image ref(s)" if image_refs else ""))
        # One concept = one scene = one paste-ready prompt (2026-08-26).
        # The old idea -> shot-list split is still reachable through the
        # two-stage path; this button no longer produces it.
        result = shootgen.generate_scene_concept(spark=prompt,
            gemini_client=gemini_client,
            db_path=None, references=references, cast=cast,
            image_refs=image_refs or None,
        )
        title = (result.get("concept") or {}).get("title") or "untitled"
        warnings = result.get("warnings") or []
        detail = f'"{title}"'
        if warnings:
            detail += f" · {len(warnings)} warning(s)"
        # the same grounding /scenes/run does: this concept goes to
        # Director too, and a brief-written scene needs its face as
        # much as a Create-written one
        try:
            if result.get("concept_id"):
                attached = _attach_scene_refs(result["concept_id"], refs, account_id,
                                              idea=prompt)
                if attached:
                    detail += f" · {len(attached)} reference(s)"
        except Exception:
            pass
        return {"ref_id": result.get("concept_id"), "detail": detail}

    job = jobs.start("concept", f"concept · {prompt[:60]}", work, account_id=account_id)
    return {"job_id": job["id"], "image_refs": len(image_refs)}


# --- generate tab (one-shot generation) --------------------------------------
# One run through the same four primitives Concept uses -- Reference /
# Ground / Enhance / Generate -- for a single image or clip. The result
# is NOT a second data model: it saves as an ordinary shoot_concepts
# row with exactly one shot (or appends a shot to an existing concept),
# so teach-to-RAG, generation history, and the scene board all keep
# working unmodified.

# --- effects (2026-10-10; docs/tasks/task-studio-agent.md item 3) -------------
# The effects table (src/effects.py) was reachable only from the Claude
# Desktop connector. These three routes are the studio's own door onto it:
# the gallery, the price, and the run. The same checks the connector runs
# (effects.spec / check_options / check_prompt / check_sources / quote_usd)
# and the same runner (effects.run: cap, credit hold, generations row,
# settle, the Assets wall) -- only the gate differs. The connector takes a
# signed token because an agent speaks for the person; here the person's
# own click on the card is the approval, as it is for a composer still, and
# `expect_credits` holds the route to the price that card showed.

# What the gallery says under each effect, in a customer's words: no vendor
# page, no dollars (the table's own `note` and `pricing` are the operator's).
EFFECT_BLURBS = {
    "nano-banana-edit": "Change an image by describing the change. Keeps faces and identity.",
    "flux-kontext-pro": "Precise local edits: swap an object, change text, restyle one area.",
    "seedream-edit": "Combine up to four images into one, or restyle one.",
    "remove-background": "Cut the subject out on a transparent background.",
    "kling-effect": "One-click animated templates on a still: 98 looks, 5 or 10 seconds.",
    "pixverse-effect": "One-click animated templates on a still: 154 looks, 5 seconds.",
    "camera-move": "A named camera move on a still: push in, orbit, crane, and more.",
    "upscale": "Sharpen a clip to twice its size, or smooth its motion to 24, 30 or 60 fps.",
    "add-sound": "Sound effects and ambience made to fit a clip's picture.",
    "reframe": "The same clip in a new shape: the frame is extended, not cropped.",
    "reframe-hq": "A new shape for a clip, at higher quality and a higher price.",
    "remove-video-background": "Cut a clip's subject out on a transparent background.",
    "remove-video-background-pro": "Remove or replace a clip's background, sound kept.",
    # the free looks (src/free_looks.py, 2026-10-22): their own words, from the table
    **{name: look["blurb"] for name, look in looks.LOOKS.items()},
}
EFFECT_CATEGORY_LABELS = {"image_edit": "Edit an image", "video_effect": "Animate a still",
                          "camera": "Camera moves", "finish": "Finish a clip",
                          "look": "Free looks"}
# What each effect is FOR, as the Effects tab filters it (2026-10-22,
# docs/tasks/task-effects-tab.md): cinematic / social / product. A row in
# src/effects.py may carry its own `tags` (the free looks do); this is the
# projection's fallback for the rows that predate the field, so every
# effect lands under at least one filter. Vocabulary, not vendor names.
EFFECT_TAGS = {
    "nano-banana-edit": ("product", "social"),
    "flux-kontext-pro": ("product",),
    "seedream-edit": ("product", "social"),
    "remove-background": ("product",),
    "kling-effect": ("social",),
    "pixverse-effect": ("social",),
    "camera-move": ("cinematic", "product"),
    "upscale": ("cinematic",),
    "add-sound": ("cinematic",),
    "reframe": ("social",),
    "reframe-hq": ("social", "cinematic"),
    "remove-video-background": ("product",),
    "remove-video-background-pro": ("product",),
}
EFFECT_SOURCES_MAX = 4


class EffectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effect: str
    # what it acts on: gen:<id> for a render on the Assets wall (the only
    # way a CLIP is named), or a reference exactly as the composer holds it
    sources: list[str] = []
    prompt: str = ""
    options: dict = {}
    # /effects/run only: the credits the card showed the person
    expect_credits: Optional[int] = None
    # FINISH a draft (src/drafts.py): the one source is a scene's draft
    # clip, and what the upscale makes is put on that shot in its place
    finish: bool = False


def _effect_view(name: str) -> dict:
    """One effect for the gallery: what it takes and makes, its options
    with every legal value, and what it costs in CREDITS at its defaults --
    None when the price depends on the clip it is given."""
    from src import effects, ledger
    row = effects.catalogue(effect=name)[0]
    spec = effects.spec(name)
    usd = effects.default_usd(name)
    # FREE is a property of the table row (`free`, the no-provider looks, read
    # from the row, else the spec), or of a price that is exactly nothing;
    # never guessed from the name. A free row lists at 0: the ledger's floor
    # (CREDIT_FLOOR) is for a priced call, and a free one takes no hold at all.
    free = (bool(row.get("free")) or bool(spec.get("free"))
            or (usd is not None and float(usd) == 0.0))
    credits = 0 if free else None if usd is None else ledger.charge_credits(usd)
    # the Effects tab's Cinematic / Social / Product filters: the row's own
    # tags (the free looks), else the spec's, else EFFECT_TAGS for the rows
    # that predate the field
    tags = tuple(row.get("tags") or spec.get("tags") or EFFECT_TAGS.get(name, ()))
    return {"id": name, "label": row["label"], "category": row["category"],
            "blurb": EFFECT_BLURBS.get(name, row["label"]),
            "takes": row["takes"], "output": row["output"],
            "sources": row["sources"], "prompt": row["prompt"],
            "options": {k: {"values": v["values"], "default": v["default"],
                            "required": v["required"]} for k, v in row["options"].items()},
            "credits": credits,
            # the Effects tab's Free / Pro badge and its filters (2026-10-22,
            # docs/tasks/task-effects-tab.md)
            "free": free, "tags": list(tags)}


@router.get("/effects")
def effects_list(account_id: int = Depends(auth.current_account_id)):
    """The effects gallery: a PROJECTION of src/effects.py, never a second
    table. Browsing it runs nothing and costs nothing."""
    from src import effects, fal, ledger
    names = effects.listed_names()          # the free looks only when switched on
    shown = {effects.EFFECTS[n]["category"] for n in names}
    return {"items": [_effect_view(name) for name in names],
            "categories": [{"id": c, "label": EFFECT_CATEGORY_LABELS.get(c, c)}
                           for c in effects.CATEGORIES if c in shown],
            "ready": fal.has_key(account_id),
            "exempt": ledger.credit_exempt(account_id)}


def _effect_request(account_id: int, body: EffectBody) -> dict:
    """Everything about one effect request checked and PRICED, nothing
    spent and nothing uploaded. Raises ValueError with what is wrong."""
    from src import effects, ledger, mcp_server
    name = (body.effect or "").strip()
    row = effects.spec(name)
    opts = effects.check_options(name, body.options)
    prompt = effects.check_prompt(name, body.prompt)
    named = list(dict.fromkeys(str(r).strip() for r in body.sources if str(r).strip()))
    if len(named) > EFFECT_SOURCES_MAX:
        raise ValueError(f"at most {EFFECT_SOURCES_MAX} sources")
    effects.check_sources(name, len(named), opts)
    probe = None
    if row["takes"] == "video":
        # a clip is named by id, and priced off its measured length and size
        clip = mcp_server._clip_row(named[0], None, account_id)
        local = clip.get("output_path") or ""
        probe = effects.probe_video(local if local and Path(local).is_file() else clip["media_url"])
    usd = effects.quote_usd(name, opts, probe)
    free = bool(row.get("free"))             # a look: 0 credits, nothing charged
    target = None
    if body.finish:
        from src import drafts
        if name != drafts.FINISH_EFFECT:
            raise ValueError(f"a draft is finished with {drafts.FINISH_EFFECT}, nothing else")
        target = drafts.finish_target(named[0] if named else "", account_id=account_id)
    return {"effect": name, "row": row, "options": opts, "prompt": prompt, "sources": named,
            "probe": probe, "usd": usd,
            "credits": 0 if free else ledger.charge_credits(usd),
            "charged": False if free else not ledger.credit_exempt(account_id),
            "free": free, "finish": target}


def _effect_urls(req: dict, account_id: int) -> list[str]:
    """The request's sources as URLs the effects service can FETCH. Done at
    run time only: an image the composer holds has to be uploaded first.
    Raises ValueError when a source cannot be read or made fetchable -- an
    effect must not be paid for against a picture it never saw."""
    from src import fal, mcp_server
    row = req["row"]
    if row.get("provider") == "local":
        return []           # a free look reads its clip from this disk by id (src/free_looks.py)
    if row["takes"] == "video":
        urls, _ = mcp_server._video_sources(req["sources"], None, account_id)
        return urls
    urls = []
    for ref in req["sources"]:
        kind, _, rest = ref.partition(":")
        if kind in ("gen", "asset") and rest.isdigit():
            urls += mcp_server.resolve_references([ref], limit=1, who=row["label"],
                                                  account_id=account_id)
            continue
        # a reference as the composer holds it: the same reader, and the
        # same wall, as a still's own references (_collect_refs)
        raw = _photo_bytes(ref.split("?")[0], account_id)
        jpeg = _to_jpeg(raw) if raw else None
        url = fal.as_image_url(jpeg, account_id=account_id) if jpeg else None
        if not url:
            raise ValueError("one of the images could not be read or made fetchable")
        urls.append(url)
    return urls


@router.post("/effects/quote")
def effects_quote(body: EffectBody, account_id: int = Depends(auth.current_account_id)):
    """What this effect, with these options, on these sources, costs --
    in credits. Spends nothing; the card calls it as its options change."""
    try:
        req = _effect_request(account_id, body)
    except ValueError as e:
        return _error(400, "bad_effect", str(e))
    return {"effect": req["effect"], "label": req["row"]["label"], "output": req["row"]["output"],
            "options": req["options"], "credits": req["credits"], "charged": req["charged"],
            **({"clip": {k: req["probe"][k] for k in ("seconds", "width", "height")}}
               if req["probe"] else {}),
            # a finish says where the finished clip will go
            **({"finish": {k: req["finish"][k] for k in ("concept_id", "shot_n", "part",
                                                         "label", "title")}}
               if req["finish"] else {})}


@router.post("/effects/run")
def effects_run(body: EffectBody, account_id: int = Depends(auth.current_account_id)):
    """Run one effect, as a job. The person's click on the priced card is
    the approval, and `expect_credits` is the price that card showed: a
    request whose price is no longer that one is refused (409), never run
    at another number. The hold, the cap, the generations row and the
    Assets wall are effects.run's, exactly as for the connector."""
    from src import effects, failures, fal
    try:
        req = _effect_request(account_id, body)
    except ValueError as e:
        return _error(400, "bad_effect", str(e))
    if body.expect_credits is None:
        return _error(400, "missing_price", "say what the card showed: expect_credits")
    if body.expect_credits != req["credits"]:
        return JSONResponse(status_code=409, content={
            "error": {"code": "price_changed",
                      "message": f"this costs {req['credits']} credits now"},
            "credits": req["credits"]})
    row = req["row"]
    if not req["free"] and not fal.has_key(account_id):
        return _error(503, "effects_unavailable", "effects are not set up on this server")

    def work(job):
        jobs.progress(job, 0.1, "getting the source ready")
        try:
            urls = _effect_urls(req, account_id)
        except ValueError as e:
            raise RuntimeError(str(e)) from e
        jobs.progress(job, 0.3, f"running {row['label']}")
        target = req["finish"]
        res = effects.run(req["effect"], urls, req["prompt"], req["options"], usd=req["usd"],
                          sources=req["sources"], probe=req["probe"],
                          account_id=account_id, source="queue" if target else "composer",
                          extra=({"finish_of": req["sources"][0],
                                  "concept_id": target["concept_id"],
                                  "shot_n": target["shot_n"], "part": target["part"]}
                                 if target else None))
        if not res.get("ok"):
            print(f"  effect {req['effect']} was not made: {res.get('error')}", file=sys.stderr)
            raise RuntimeError(failures.plain(res.get("error"), "The effect"))
        done = {"detail": f"{row['label']} · done" + (" · free" if req["free"] else ""),
                "output": res.get("media_url"),
                # `media`, never `kind`: a job's result is merged onto the job,
                # and `kind` is the job's own ("effect"), which the tray reads
                "media": row["output"],
                "asset": f"gen:{res['asset_id']}" if res.get("asset_id") else None,
                # Make It Pro's Sound Pass SLOT (src/free_looks.py): a priced card
                # the studio may open on the result; nothing ran for it
                **({"next": res["next"]} if res.get("next") else {})}
        if target:
            # the finished clip takes the draft's place on its shot. It was
            # paid for and is on the wall whatever happens here, so a shot
            # that has gone is said on the job, never a failed job
            from src import drafts
            try:
                drafts.attach(target, res["media_url"], res.get("asset_id"),
                              account_id=account_id)
                done.update(detail=f"{target['label']} finished", finished=True,
                            ref_id=target["concept_id"])
            except Exception as e:                          # noqa: BLE001
                print(f"  finished clip not attached to {target['label']}: {e}", file=sys.stderr)
                done.update(detail="Finished and in your Library, but its shot is gone, "
                                   "so it was not put on the scene.", finished=False)
        return done

    job = jobs.start("effect", f"effect · {row['label']}", work, account_id=account_id)
    return {"job_id": job["id"], "credits": req["credits"], "charged": req["charged"]}


# --- a talking photo (2026-10-20, docs/tasks/task-talking-photo.md) ----------
# The studio's door onto src/talking_photo.py, which the connector reached
# first (mcp_server.run_voice_preview / run_talking_photo). Two spends, each
# its own card price and click, like an effect: a voice preview (a typed
# script read aloud, filed as an asset:<id> the person hears) and the clip
# (a photo plus that voice, or an uploaded .mp3/.wav). The checks, the price
# and the runner are talking_photo's -- shared with the connector -- and only
# the gate differs: here the person's click on the card is the approval and
# `expect_credits` holds the run to the price the card showed (409 if not).

class VoicePreviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    script: str
    voice: str = ""
    language: str = ""
    expect_credits: Optional[int] = None


class TalkingPhotoBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # gen:<id> (a still on the Assets wall), asset:<id> (an upload), or a
    # photo exactly as the composer holds it (an attachment, an element's)
    photo: str
    # asset:<id>: a voice preview or an uploaded .mp3 / .wav
    audio: str
    prompt: str = ""
    consent: bool = False
    project_id: Optional[int] = None
    expect_credits: Optional[int] = None


def _price_moved(credits: int) -> JSONResponse:
    return JSONResponse(status_code=409, content={
        "error": {"code": "price_changed", "message": f"this costs {credits} credits now"},
        "credits": credits})


@router.get("/talking-photo")
def talking_photo_menu(account_id: int = Depends(auth.current_account_id)):
    """What the card offers: the voices, the script's bounds, this account's
    longest voice. Browsing it runs nothing and costs nothing."""
    from src import fal, ledger
    from src import talking_photo as tp
    return {"voices": list(tp.VOICES), "default_voice": tp.DEFAULT_VOICE,
            "script_min": tp.SCRIPT_MIN_CHARS, "script_max": tp.SCRIPT_MAX_CHARS,
            "audio_min": tp.AUDIO_MIN_SECONDS, "audio_cap": tp.audio_cap(account_id),
            "audio_types": list(tp.AUDIO_TYPES), "prompt_max": tp.PROMPT_MAX,
            "ready": fal.has_key(account_id), "exempt": ledger.credit_exempt(account_id)}


def _voice_request(body: VoicePreviewBody, account_id: int) -> dict:
    from src import ledger
    from src import talking_photo as tp
    req = tp.voice_request(body.script, body.voice, body.language)
    return {**req, "credits": ledger.charge_credits(req["usd"]),
            "charged": not ledger.credit_exempt(account_id)}


@router.post("/talking-photo/voice/quote")
def talking_photo_voice_quote(body: VoicePreviewBody,
                              account_id: int = Depends(auth.current_account_id)):
    """What reading this script aloud costs, in credits. Spends nothing."""
    try:
        req = _voice_request(body, account_id)
    except ValueError as e:
        return _error(400, "bad_voice", str(e))
    return {"voice": req["voice"], "language": req["language"],
            "characters": req["characters"], "credits": req["credits"],
            "charged": req["charged"]}


@router.post("/talking-photo/voice/run")
def talking_photo_voice_run(body: VoicePreviewBody,
                            account_id: int = Depends(auth.current_account_id)):
    """Read the script aloud, as a job, at the price the card showed. The
    job's result names the voice (`audio`, an asset:<id>), its measured
    `seconds` and an address to play it (`output`)."""
    from src import failures, fal, media
    from src import talking_photo as tp
    try:
        req = _voice_request(body, account_id)
    except ValueError as e:
        return _error(400, "bad_voice", str(e))
    if body.expect_credits is None:
        return _error(400, "missing_price", "say what the card showed: expect_credits")
    if body.expect_credits != req["credits"]:
        return _price_moved(req["credits"])
    if not fal.has_key(account_id):
        return _error(503, "effects_unavailable", "voices are not set up on this server")

    def work(job):
        jobs.progress(job, 0.2, f"reading it as {req['voice']}")
        res = tp.run_voice(req, account_id=account_id, source="composer")
        if not res.get("ok"):
            print(f"  voice preview was not made: {res.get('error')}", file=sys.stderr)
            raise RuntimeError(failures.plain(res.get("error"), "The voice"))
        seconds = res.get("seconds")
        return {"detail": f"{req['voice']} · {seconds:.1f}s" if seconds else req["voice"],
                "output": media.url_for(res["stored"], account_id), "media": "audio",
                "audio": res["audio"], "seconds": seconds}

    job = jobs.start("effect", f"voice · {req['voice']}", work, account_id=account_id)
    return {"job_id": job["id"], "credits": req["credits"], "charged": req["charged"]}


def _talk_request(body: TalkingPhotoBody, account_id: int) -> dict:
    """A talking photo checked and PRICED, nothing spent. The photo is
    measured here (the model takes 300-6000px, 0.4-2.5 wide); it is made
    fetchable only at run time. Raises ValueError with what is wrong."""
    import io

    from PIL import Image

    from src import ledger, mcp_server
    from src import talking_photo as tp
    photo = (body.photo or "").strip()
    if not photo:
        raise ValueError("pick the photo that speaks")
    prompt = tp.check_prompt(body.prompt)
    kind, _, rest = photo.partition(":")
    image_url = None
    if kind in ("gen", "asset") and rest.isdigit():
        (image_url,) = mcp_server.resolve_references([photo], limit=1, who="A talking photo",
                                                     account_id=account_id)
        size = tp.image_size(image_url)
    else:
        raw = _photo_bytes(photo.split("?")[0], account_id)
        if not raw:
            raise ValueError("that photo could not be read")
        try:
            size = Image.open(io.BytesIO(raw)).size
        except Exception:
            raise ValueError("that photo could not be read") from None
    req = tp.talk_request(photo, (body.audio or "").strip(), size=size, prompt=prompt,
                          account_id=account_id)
    filed = mcp_server._filed_under(body.project_id, None, account_id)
    return {**req, "image_url": image_url, "credits": ledger.charge_credits(req["usd"]),
            "charged": not ledger.credit_exempt(account_id), **filed}


@router.post("/talking-photo/quote")
def talking_photo_quote(body: TalkingPhotoBody,
                        account_id: int = Depends(auth.current_account_id)):
    """What this photo speaking this voice costs, in credits: the voice's
    measured length, rounded up to the whole second. Spends nothing; the
    consent box is asked at the run, so the price shows before it is ticked."""
    try:
        req = _talk_request(body, account_id)
    except ValueError as e:
        return _error(400, "bad_talking_photo", str(e))
    return {"credits": req["credits"], "charged": req["charged"],
            "audio_seconds": round(req["seconds"], 2), "billed_seconds": req["billed_seconds"],
            "audio_cap": req["cap"], "photo_size": [req["width"], req["height"]]}


@router.post("/talking-photo/run")
def talking_photo_run(body: TalkingPhotoBody,
                      account_id: int = Depends(auth.current_account_id)):
    """Render the talking photo, as a job, at the price the card showed. The
    clip lands in the Library like an effect's (`asset`: gen:<id>)."""
    from src import failures, fal
    from src import talking_photo as tp
    try:
        tp.check_consent(body.consent)
        req = _talk_request(body, account_id)
    except ValueError as e:
        return _error(400, "bad_talking_photo", str(e))
    if body.expect_credits is None:
        return _error(400, "missing_price", "say what the card showed: expect_credits")
    if body.expect_credits != req["credits"]:
        return _price_moved(req["credits"])
    if not fal.has_key(account_id):
        return _error(503, "effects_unavailable", "talking photos are not set up on this server")

    def work(job):
        jobs.progress(job, 0.1, "getting the photo ready")
        image_url = req["image_url"]
        if not image_url:
            raw = _photo_bytes(req["photo"].split("?")[0], account_id)
            jpeg = _to_jpeg(raw) if raw else None
            image_url = fal.as_image_url(jpeg, account_id=account_id) if jpeg else None
            if not image_url:
                raise RuntimeError("The photo could not be read or made fetchable. "
                                   "Nothing was charged.")
        jobs.progress(job, 0.3, f"{tp.TALK['label']} · {req['billed_seconds']}s")
        res = tp.run_talk(req, image_url, account_id=account_id, source="composer",
                          project_id=body.project_id)
        if not res.get("ok"):
            print(f"  talking photo was not made: {res.get('error')}", file=sys.stderr)
            raise RuntimeError(failures.plain(res.get("error"), "The talking photo"))
        return {"detail": f"Talking photo · {req['billed_seconds']}s",
                "output": res.get("media_url"), "media": "video",
                "asset": f"gen:{res['asset_id']}" if res.get("asset_id") else None}

    job = jobs.start("effect", "talking photo", work, account_id=account_id)
    return {"job_id": job["id"], "credits": req["credits"], "charged": req["charged"]}


class QuickEditBody(BaseModel):
    """A free edit the brain proposed (src/guide_tools.py QUICK_TOOLS), as the
    studio runs it: the tool, the source the page bound (gen:<id> or
    asset:<id>, never an address) and the tool's own arguments."""
    model_config = ConfigDict(extra="forbid")
    tool: str
    source: str
    aspect: Optional[str] = None
    fit: str = "pad"
    start: Optional[float] = None
    end: Optional[float] = None
    project_id: Optional[int] = None


def _quick(body: QuickEditBody, account_id: int, *, dry_run: bool) -> dict:
    """The connector's own runners (src/mcp_server.py run_reformat /
    run_trim_clip over src/cut/quick.py): checked and planned on a dry run,
    made otherwise. Raises ValueError with what is wrong."""
    from src import mcp_server
    if body.tool == "reformat":
        return mcp_server.run_reformat(body.source, body.aspect or "", body.fit,
                                       project_id=body.project_id, account_id=account_id,
                                       dry_run=dry_run)
    if body.tool == "trim_clip":
        if body.start is None or body.end is None:
            raise ValueError("a trim needs start and end, in seconds")
        return mcp_server.run_trim_clip(body.source, body.start, body.end,
                                        project_id=body.project_id, account_id=account_id,
                                        dry_run=dry_run)
    raise ValueError("the free edits are reformat and trim_clip")


@router.post("/quick-edit")
def quick_edit(body: QuickEditBody, account_id: int = Depends(auth.current_account_id)):
    """Run a free edit, as a job (2026-10-19, the Vesper review). It spends
    nothing -- ffmpeg on this server, no provider, no hold -- so the studio
    runs it the moment the brain proposes it, as it writes a scene. Checked
    before the job starts (a 400 with the reason); the result lands on the
    Assets wall as a gen:<id>, and the job carries it the way an effect's
    does (output, media, asset)."""
    from src import failures
    try:
        _quick(body, account_id, dry_run=True)
    except ValueError as e:
        return _error(400, "bad_edit", str(e))
    label = "Reformat" if body.tool == "reformat" else "Trim"

    def work(job):
        jobs.progress(job, 0.2, f"{label.lower()}ing on the studio's server")
        try:
            res = _quick(body, account_id, dry_run=False)
        except ValueError as e:
            raise RuntimeError(str(e)) from e
        if not res.get("ok"):
            print(f"  free edit {body.tool} was not made: {res.get('error')}", file=sys.stderr)
            raise RuntimeError(failures.plain(res.get("error"), f"The {label.lower()}"))
        return {"detail": f"{label} · done · free", "output": res.get("media_url"),
                # `media`, never `kind`: as an effect's job (the tray reads kind)
                "media": res.get("media_kind"), "asset": res.get("ref")}

    job = jobs.start("effect", f"{label.lower()} · free", work, account_id=account_id)
    return {"job_id": job["id"], "credits": 0}


def _render_failed(raw, what: str) -> str:
    """A draw that did not happen, as the job's line: the provider's own
    words go to the log (and are on the generations row), the page gets a
    sentence a customer can act on (src/failures.py, 2026-10-10)."""
    from src import failures
    print(f"  {what.lower()} was not made: {raw}", file=sys.stderr)
    return failures.plain(raw, what)


GENERATE_OUTPUTS = ("image", "video", "prompt")
# The image shapes the composer may ask Nano Banana for (2026-10-02). An id
# outside this set is ignored and the still is drawn at the module default
# (NANO_ASPECT_RATIO), never a refused or failed call.
GENERATE_ASPECTS = ("1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9")


@router.get("/presets")
def presets_list():
    """The curated camera/framing scaffolds (prompts/presets.json) the
    Generate tab and Director nodes fold into the Enhance step, plus
    the enhancement instruction (prompts/enhance_system.txt) the
    Director chain seeds its Instructions node with."""
    return {"items": presets.load_presets(),
            "enhance_system": workflows._enhance_system_text()}


@router.get("/presets/counts")
def presets_counts(account_id: int = Depends(auth.current_account_id)):
    """Presets as tested recipes (2026-10-11): for THIS account, how many
    outputs were made on a scene written with each preset and how many of
    them were kept. `/presets` itself stays the same bytes for everyone;
    the composer merges the two and lists the tested ones first."""
    return {"counts": outcomes.preset_counts(account_id=account_id)}


@router.get("/trending")
def trending_week(account_id: int = Depends(auth.current_account_id)):
    """Trending this week on the Create page (src/trending.py, 2026-10-22):
    the effects THIS account ran most over the last seven days, the briefs
    it wrote scenes from, and how it treated the week's outputs. Scoped to
    the caller's own account -- the tenancy rules allow no cross-account
    read -- which the answer says (`scope: "account"`). Carries no price."""
    from src import trending
    return trending.trending(account_id=account_id)


@router.get("/director/landing")
def director_landing(request: Request, account_id: int = Depends(auth.current_account_id)):
    """Director tab's chat-first entry: a real pre-filled sample brief
    (the gold-standard exemplar, shortened to its style + action blocks).
    `chips` stays in the shape for the client but is always empty: the
    only chips were Zero Page's "wrongness" format skeletons, a brand idea
    removed on 2026-10-04."""
    from src import shootgen

    sample = shootgen.gold_standard_example()
    if sample:
        paragraphs = [p for p in sample.split("\n\n") if p.strip()]
        sample = "\n\n".join(paragraphs[:2])
    return {"sample_prompt": sample, "chips": []}


def _enhance_generate_prompt(gemini_client, prompt: str, *, preset=None,
                             references: str = "", image_refs=None,
                             video_refs=None) -> str:
    """The Enhance primitive for one Generate-tab run: the typed prompt,
    the picked preset's scaffold, and the RAG references folded into one
    billed Gemini call, with image/video references riding as real
    vision input. Raises on failure -- here the model call IS the
    deliverable, the promptgen contract."""
    from google.genai import types

    from src import shootgen
    from src import workflows as _workflows
    from src.gemini_utils import generate_with_retry

    blocks = [_workflows._enhance_system_text()]
    if preset:
        blocks.append("CAMERA / FRAMING SCAFFOLD -- build the prompt around "
                      f"this move:\n{preset['label']}: {preset['how']}")
    if references:
        blocks.append("REFERENCES -- ground the prompt in these:\n" + references)
    if image_refs or video_refs:
        blocks.append("(Reference media is attached above -- ground the prompt "
                      "in what it actually shows, don't ignore it.)")
    blocks.append("PROMPT TO ENHANCE:\n" + prompt)

    # caption then image, so the model is told which photo is the face
    # and which is the jacket rather than inferring it from the prose
    parts: list = []
    for ref in image_refs or []:
        if len(ref) > 2 and ref[2]:
            parts.append(ref[2])
        parts.append(types.Part.from_bytes(data=ref[0], mime_type=ref[1]))
    for data, mime in video_refs or []:
        part = video_part(gemini_client, data, mime)
        if part is not None:
            parts.append(part)
    parts.append("\n\n".join(blocks))
    return generate_with_retry(gemini_client, shootgen.MODEL, parts, stage="enhance").strip()


def _generate_title(prompt: str) -> str:
    words = prompt.split()
    title = " ".join(words[:8])
    return title + ("…" if len(words) > 8 else "")


CREATE_AUTONOMY = ("ask", "checkpoints", "autopilot")      # web/src/lib/autonomy.ts
CREATE_PICKERS = ("person", "vesper", "default")


def _prompt_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256((text or "").strip().encode()).hexdigest()[:16]


def _create_provenance(form, output: str, account_id: Optional[int] = None) -> dict:
    """What the Create box knew when it posted (2026-10-24, the Vesper audit):
    the fields its keep rate is read by, per model, picker, autonomy and
    brain. Anything off its list is dropped, never stored as sent. The
    conversation and how far into it are read here, from the open thread
    (src/assistant_store.py), not taken from the form; best-effort."""
    from src.gemini_utils import BRAINS

    def pick(name, allowed):
        v = (form.get(name) or "").strip().lower()
        return v if v in allowed else None

    told = {"door": "create", "output": output,
            "autonomy": pick("autonomy", CREATE_AUTONOMY),
            "brain": pick("brain", tuple(BRAINS)),
            "model_picked_by": pick("model_picked_by", CREATE_PICKERS)}
    if account_id is not None:
        try:
            from src import assistant_store
            thread = assistant_store.open_project(account_id=account_id)
            if thread:
                told.update(thread_id=thread["id"], turn_n=len(thread.get("turns") or []))
        except Exception:                               # noqa: BLE001
            pass
    return {k: v for k, v in told.items() if v is not None}


def _sent_provenance(told: dict, shown: str, sent: str, kit, said: str,
                     preset=None) -> dict:
    """The record that "sent as shown" is checked by on live rows: the hash
    of the prompt the card showed beside the hash of what the model got, and
    the lines added between them, each one the card shows on its own."""
    added = [name for name, on in (("camera_preset", bool(preset)),
                                   ("brand_kit", bool(brand_kits.look_suffix(kit))),
                                   ("reference_roles", bool(said))) if on]
    return {**told, "shown_prompt_hash": _prompt_hash(shown),
            "sent_prompt_hash": _prompt_hash(sent), "sent_additions": added}


@router.post("/generate/run")
async def generate_run(request: Request, account_id: int = Depends(auth.current_account_id)):
    """The Generate button: preset + prompt (+ attached image/video
    references) -> Ground -> Enhance -> saved one-shot concept -> the
    render. The render is best-effort and honestly gated: an image goes
    through Nano Banana (cheap, capped) and lands as the shot's
    reference_image; a video goes through fal's spend gate and credit hold
    and lands as media_url; a refusal still leaves the saved concept +
    prompt."""
    form = await request.form()
    prompt = (form.get("prompt") or "").strip()
    if not prompt:
        return _error(400, "empty_prompt", "a prompt is required")
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    output = form.get("output")
    if output not in GENERATE_OUTPUTS:
        output = "image"
    preset = presets.get_preset(form.get("preset"))
    aspect = form.get("aspect")
    aspect = aspect if aspect in GENERATE_ASPECTS else None
    # which model draws (2026-10-04): a fal.IMAGE_MODELS id, else Nano.
    # Checked here so a model this install has no key for is refused
    # before the job rather than after the enhance has been paid for.
    from src import fal
    image_model = (form.get("image_model") or "").strip() or NANO_IMAGE_MODEL
    if output == "image" and image_model != NANO_IMAGE_MODEL:
        if image_model not in fal.IMAGE_MODELS:
            return _error(400, "bad_model", f"no image model '{image_model}'")
        if not fal.has_key(account_id):
            return _error(503, "generation_unavailable", "FAL_KEY not set")
    concept_id_raw = (form.get("concept_id") or "").strip()
    attach_to = int(concept_id_raw) if concept_id_raw.isdigit() else None
    if attach_to is not None and preprod.get_concept(attach_to, account_id=account_id) is None:
        return _error(404, "not_found", "no such concept to attach to")
    # the composer thread's project (2026-10-21): a still drawn there takes
    # the project's brand kit look, unless the composer's kit chip was
    # switched off for this send (`brand_kit=off`)
    project_raw = (form.get("project_id") or "").strip()
    project_id = int(project_raw) if project_raw.isdigit() else None
    if project_id is not None and projects.get(project_id, account_id=account_id) is None:
        return _error(404, "not_found", "no such project")
    kit_on = (form.get("brand_kit") or "").strip().lower() not in ("off", "0", "false")
    # a kit picked in the composer for a conversation outside a project
    # (2026-10-22): it dresses the still as a project's pick would
    picked_kit, refused = _form_kit(form, account_id)
    if refused is not None:
        return refused
    # the video branch spends on fal with no price shown anywhere and no
    # front end posting it -- a billable one goes to the Queue (step 5),
    # refused BEFORE the job so no Gemini call is made for a clip that
    # will not render
    video_pick = (providers.renderer_for(account_id, needs="generate_from_prompt")
                  if output == "video" else None)
    if video_pick and _quote_required(account_id, video_pick["provider"]):
        return _error(400, "missing_quote", _QUEUE_ONLY)
    # gated like Create (2026-10-02): the composer's Image button made this
    # a front door, and every run grounds, enhances and saves a concept
    # before the still's own hold can refuse -- refused here, before any of
    # it, for an account with no plan and no balance
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    image_refs, ref_urls, video_refs = await _collect_refs(
        form, want_video=True, account_id=account_id)
    roles = _form_ref_roles(form)
    # what this make says about earlier outputs (src/outcomes.py): a render
    # sent back as a reference was reused, and a Variation names the still
    # it continues -- both BEFORE the new output is recorded, so the one it
    # came from is never read as passed over
    outcomes.record_refs("ref_reuse", ref_urls, account_id=account_id, source="composer")
    continued = (form.get("continued_from") or "").strip()
    if continued:
        outcomes.record_ref("continued", continued, account_id=account_id, source="variation")
    told = _create_provenance(form, output, account_id)

    def work(job):
        # NOT `def work(job, account_id=None)` (2026-09-02): jobs.start
        # calls fn(job), so that parameter shadowed the route's
        # dependency with None and every concept this route saved
        # belonged to nobody until backfill_owner handed it to the
        # bootstrap account at the next startup.
        from google import genai

        from src import nano_banana, shootgen
        gemini_client = genai.Client(api_key=api_key)

        if output == "image":
            # A still is sent AS APPROVED (2026-10-24, the Vesper audit): the
            # prompt on the step card, or typed into the box, IS the brief.
            # The enhancer is a video shot editor -- it gave every still a
            # (0-5s) window, camera moves and music -- and its RAG block was
            # words nobody saw. Only a picked camera preset is added, as the
            # one line the person chose (the scene writer's own shape).
            enhanced = f"{prompt}\n\nCamera: {preset['how']}" if preset else prompt
        else:
            jobs.progress(job, 0.1, "grounding in references")
            references = shootgen.reference_block(spark=prompt, db_path=None)

            refs_note = ""
            if image_refs or video_refs:
                refs_note = f" · {len(image_refs) + len(video_refs)} ref(s)"
            jobs.progress(job, 0.3, "enhancing prompt" + refs_note)
            enhanced = _enhance_generate_prompt(
                gemini_client, prompt, preset=preset, references=references,
                image_refs=image_refs, video_refs=video_refs)
            if not enhanced:
                raise RuntimeError("enhancement came back empty")

        jobs.progress(job, 0.55, "saving concept")
        shot = {"n": 1, "type": "BROLL", "source": "AI",
                "tool": shootgen.DEFAULT_SCENE_TOOL,
                "desc": prompt, "prompt": enhanced,
                # which camera preset shaped it: a label, so what this makes
                # can be counted against the preset (outcomes.preset_counts)
                **({"preset": preset["id"]} if preset else {})}
        location_names = [loc["name"]
                          for loc in preprod.list_locations(account_id=account_id)]
        if attach_to is not None:
            concept = preprod.get_concept(attach_to, account_id=account_id)
            shots = list(concept.get("shots") or [])
            shot["n"] = max((s.get("n") or 0 for s in shots), default=0) + 1
            shots.append(shot)
            warnings = shootgen.validate_concept(
                {**concept, "shots": shots}, location_names,
                use_pov=bool(concept.get("use_pov")))
            preprod.update_concept_shots(attach_to, {"shots": shots},
                                         warnings=warnings, account_id=account_id)
            concept_id = attach_to
        else:
            concept_dict = {"title": _generate_title(prompt), "hook": "",
                            "logline": prompt, "shots": [shot]}
            warnings = shootgen.validate_concept(
                concept_dict, location_names)
            concept_id = preprod.save_concept(
                concept_dict, spark=prompt,
                warnings=warnings, account_id=account_id)
            # a one-shot generation is a concept like any other and
            # opens in Director like any other, so it grounds like any
            # other -- best-effort, never fails the generation
            try:
                _attach_scene_refs(concept_id, ref_urls, account_id, roles=roles)
            except Exception:
                pass

        # The brand kit dresses a still ONCE, here (2026-10-24; it used to be
        # here AND in the renderer, so the look landed twice): the project's
        # pick, the scene's, the conversation's, or a kit the prompt NAMES
        # (Vesper outside a project). Not when the kit chip is off. The
        # renderer is handed the kit to record, never to add again.
        kit = None
        sent = enhanced
        if output == "image" and kit_on:
            kit = (brand_kits.for_project_id(project_id, account_id=account_id)
                   or brand_kits.for_concept(concept_id, account_id=account_id)
                   or picked_kit
                   or brand_kits.named_in([prompt], account_id=account_id))
            sent = brand_kits.dress(enhanced, kit)

        notes = []
        # the still's id on the Assets wall, when it was banked there: how
        # a later effect names it (src/effects.py takes ids, never URLs)
        asset = None
        if output == "image" and image_model != NANO_IMAGE_MODEL:
            label = fal.IMAGE_MODELS[image_model]["label"]
            jobs.progress(job, 0.7, f"rendering image via {label}")
            # fal's servers FETCH a reference, so each one goes up public
            # first (as_image_url); one that cannot is dropped, and the
            # result's `references` count says how many the model saw
            urls = [fal.as_image_url(raw, account_id=account_id)
                    for raw, _mime, _label in image_refs]
            urls = [u for u in urls if u]
            # these models take pictures with no caption slot, so what each
            # one is FOR rides in the prompt, named by position
            from src import ref_roles
            said = ref_roles.prompt_note(ref_urls, roles)
            sent = f"{sent}\n\n{said}" if said else sent
            result = fal.generate_image_from_prompt(
                sent,
                model=image_model, aspect=aspect,
                reference_urls=urls, concept_id=concept_id,
                # a person asked for this still from the composer
                approved=True, db_path=None, account_id=account_id,
                project_id=project_id, brand_kit=False, dressed_kit=kit,
                provenance=_sent_provenance(told, prompt, sent, kit, said, preset))
            if result.get("ok"):
                asset = result.get("asset_id")
                preprod.set_shot_reference_image(
                    concept_id, shot["n"], result["media_url"], account_id=account_id)
                note = f"image rendered on {label} → shot reference"
                if image_refs and not result.get("references"):
                    note += f" · {label} takes no reference images, drawn from the prompt"
                notes.append(note)
            else:
                notes.append(_render_failed(result.get("error"), "The still"))
        elif output == "image":
            jobs.progress(job, 0.7, "rendering image via Nano Banana")
            # EVERY attached reference, each under its caption (2026-10-11).
            # Only the first one used to be sent, bare: a product photo and
            # a frame attached for its light arrived as one unnamed picture.
            # LITERAL (2026-10-24): as_still_frame un-videos a video prompt,
            # and this one is a still brief already. The captions still name
            # each picture (they are about the pictures, not the words).
            result = nano_banana.generate_from_prompt(
                sent,
                reference_image=([(label, data) for data, _mime, label in image_refs]
                                 if image_refs else None),
                db_path=None, account_id=account_id, literal=True,
                project_id=project_id, brand_kit=False, dressed_kit=kit,
                provenance=_sent_provenance(told, prompt, sent, kit, "", preset),
                **({"aspect_ratio": aspect} if aspect else {}))
            if result.get("ok"):
                asset = result.get("asset_id")
                preprod.set_shot_reference_image(
                    concept_id, shot["n"], result["media_url"], account_id=account_id)
                notes.append("image rendered → shot reference")
            else:
                notes.append(_render_failed(result.get("error"), "The still"))
        elif output == "video":
            if video_pick:
                jobs.progress(job, 0.7, f"rendering via {video_pick['model']}")
                result = providers.VIDEO_PROVIDERS[video_pick["provider"]].generate_from_prompt(
                    enhanced,
                    reference_image=image_refs[0][0] if image_refs else None,
                    model=video_pick["model"],
                    # a person asked for a video from this composer
                    approved=True,
                    db_path=None, account_id=account_id)
                if result.get("ok"):
                    preprod.set_shot_media_url(
                        concept_id, shot["n"], result["media_url"], account_id=account_id)
                    notes.append("clip rendered and attached")
                else:
                    notes.append(_render_failed(result.get("error"), "The clip"))
            else:
                notes.append(_render_failed("FAL_KEY not set", "The clip"))

        detail = "prompt saved" if output == "prompt" else (notes[0] if notes else "saved")
        if warnings:
            detail += f" · {len(warnings)} warning(s)"
        # the one-shot scene keeps the picked kit (2026-10-22), so a clip made
        # from it later renders under it too -- set AFTER the still, which the
        # kit has already dressed above (a scene's kit dresses fal's again)
        if picked_kit and kit_on and attach_to is None and not project_id:
            try:
                brand_kits.pick_for_concepts([concept_id], picked_kit["id"],
                                             account_id=account_id)
            except Exception:                           # noqa: BLE001
                pass
        return {"ref_id": concept_id, "detail": detail, "output": enhanced,
                "shot_n": shot["n"], **({"asset": f"gen:{asset}"} if asset else {})}

    job = jobs.start("generate", f"generate · {prompt[:60]}", work, account_id=account_id)
    return {"job_id": job["id"],
            "image_refs": len(image_refs), "video_refs": len(video_refs)}


# --- the direct generators (2026-10-22, docs/tasks/task-direct-generators.md)
# /studio/image and /studio/video: one prompt, one model the person picked,
# one priced button. The menus and prices are src/direct.py's projections
# of the tables every other door prices with; here is only the gate. The
# person's click on the priced button is the approval and `expect_credits`
# holds the run to the number the button showed (409 if it moved), exactly
# as an effect's card. The prompt goes to the model AS TYPED: no enhance,
# no brain turn, no scene written. A result lands on the Library wall.

class DirectVideoQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    seconds: Optional[int] = None
    resolution: Optional[str] = None
    aspect: Optional[str] = None
    start_frame: bool = False
    references: int = 0


class DirectImageQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    aspect: Optional[str] = None
    references: int = 0


@router.get("/direct/video")
def direct_video_menu(account_id: int = Depends(auth.current_account_id)):
    """Every clip model the Video page offers, with what each can be asked
    for and its opening price. Reading it costs nothing."""
    from src import direct
    return direct.video_menu(account_id)


@router.post("/direct/video/quote")
def direct_video_quote(body: DirectVideoQuote, account_id: int = Depends(auth.current_account_id)):
    """The price of exactly this pick, or 400 naming what the model does
    not take. Spends nothing."""
    from src import direct
    try:
        q = direct.video_quote(account_id, model=body.model, seconds=body.seconds,
                               resolution=body.resolution, aspect=body.aspect,
                               start_frame=body.start_frame,
                               references=body.references)
    except ValueError as e:
        return _error(400, "bad_choice", str(e))
    return direct.public(q)


@router.get("/direct/image")
def direct_image_menu(account_id: int = Depends(auth.current_account_id)):
    """Every model the Image page offers (the composer's own picker), with
    the frames and how many pictures reach each one."""
    from src import direct
    return direct.image_menu(account_id)


@router.post("/direct/image/quote")
def direct_image_quote(body: DirectImageQuote, account_id: int = Depends(auth.current_account_id)):
    from src import direct
    try:
        q = direct.image_quote(account_id, model=body.model, aspect=body.aspect,
                               references=body.references)
    except ValueError as e:
        return _error(400, "bad_choice", str(e))
    return direct.public(q)


def _expected_credits(form) -> Optional[int]:
    raw = str(form.get("expect_credits") or "").strip()
    return int(raw) if raw.isdigit() else None


def _form_int(form, name: str) -> Optional[int]:
    raw = str(form.get(name) or "").strip()
    return int(raw) if raw.lstrip("-").isdigit() else None


@router.post("/direct/video/run")
async def direct_video_run(request: Request, account_id: int = Depends(auth.current_account_id)):
    """One clip on the model the person picked, as a job. Multipart: the
    prompt, model, seconds, resolution, aspect and `expect_credits`, plus an
    optional start frame as `files` (an upload) or `asset_photos` (a picked
    picture). With `ref_mode=references` (2026-10-25) those pictures are
    instead ALL held as references on the model's reference endpoint
    (fal.REF2V), named in the prompt by their tags. No photograph is
    required (Mike's call): this writes no scene, so the reference gate --
    which guards scenes -- has nothing to guard here."""
    from src import direct, fal
    form = await request.form()
    model = str(form.get("model") or "")
    try:
        prompt = direct.clean_prompt(form.get("prompt"),
                                     video_model=model if model in fal.VIDEO_MODELS else None)
    except ValueError as e:
        return _error(400, "empty_prompt", str(e))
    expected = _expected_credits(form)
    if expected is None:
        return _error(400, "missing_price", "say what the button showed: expect_credits")
    if not fal.has_key(account_id):
        return _error(503, "generation_unavailable", "video is not set up on this server")
    image_refs, ref_urls, _videos = await _collect_refs(form, account_id=account_id)
    held = str(form.get("ref_mode") or "") == "references"
    pictures = [r[0] for r in image_refs] if held else []
    start = image_refs[0][0] if image_refs and not held else None
    try:
        q = direct.video_quote(account_id, model=model,
                               seconds=_form_int(form, "seconds"),
                               resolution=str(form.get("resolution") or ""),
                               aspect=str(form.get("aspect") or ""),
                               start_frame=start is not None,
                               references=len(pictures))
    except ValueError as e:
        return _error(400, "bad_choice", str(e))
    if q["credits"] != expected:
        return _price_moved(q["credits"])
    if ref_urls:
        outcomes.record_refs("ref_reuse", ref_urls if held else ref_urls[:1],
                             account_id=account_id, source="direct")
    label = q["label"]

    def work(job):
        jobs.progress(job, 0.1, f"rendering on {label}")
        res = fal.generate_from_prompt(
            prompt, reference_image=start, model=q["model"],
            duration=q["seconds"], resolution=q["resolution"],
            aspect_ratio=q["aspect"],
            # the person pressed the priced button on the Video page
            approved=True, account_id=account_id, source="direct", bank=True,
            **({"references": pictures} if pictures else {}))
        if not res.get("ok"):
            raise RuntimeError(_render_failed(res.get("error"), "The clip"))
        asset = res.get("asset_id")
        return {"detail": f"{label} · {q['seconds']}s · done",
                "output": res.get("media_url"), "media": "video",
                "asset": f"gen:{asset}" if asset else None}

    job = jobs.start("make", f"video · {label} · {prompt[:50]}", work,
                     cancellable=True, account_id=account_id)
    return {"job_id": job["id"], "credits": q["credits"], "charged": q["charged"]}


@router.post("/direct/image/run")
async def direct_image_run(request: Request, account_id: int = Depends(auth.current_account_id)):
    """One still on the model the person picked, as a job. Multipart: the
    prompt, model, aspect and `expect_credits`, with references as `files`
    and `asset_photos` (as the composer sends them)."""
    from src import direct, fal, model_menu, nano_banana
    form = await request.form()
    try:
        prompt = direct.clean_prompt(form.get("prompt"))
    except ValueError as e:
        return _error(400, "empty_prompt", str(e))
    expected = _expected_credits(form)
    if expected is None:
        return _error(400, "missing_price", "say what the button showed: expect_credits")
    model = str(form.get("model") or "").strip()
    image_refs, ref_urls, _videos = await _collect_refs(form, account_id=account_id)
    try:
        q = direct.image_quote(account_id, model=model, aspect=str(form.get("aspect") or ""),
                               references=len(image_refs))
    except ValueError as e:
        return _error(400, "bad_choice", str(e))
    nano = q["model"] == model_menu.NANO_ID
    if nano and not nano_banana.has_key(account_id):
        return _error(503, "generation_unavailable", "Nano Banana is not set up on this server")
    if not nano and not fal.has_key(account_id):
        return _error(503, "generation_unavailable", "image models are not set up on this server")
    if q["credits"] != expected:
        return _price_moved(q["credits"])
    if ref_urls:
        outcomes.record_refs("ref_reuse", ref_urls, account_id=account_id, source="direct")
    label = q["label"]
    refs = image_refs[:direct.image_max_refs(q["model"])]

    def work(job):
        jobs.progress(job, 0.1, f"drawing on {label}")
        if nano:
            res = nano_banana.generate_from_prompt(
                prompt, reference_image=[(lab, data) for data, _mime, lab in refs] or None,
                aspect_ratio=q["aspect"], literal=True, bank=True, source="direct",
                db_path=None, account_id=account_id, brand_kit=False)
        else:
            urls = [u for u in (fal.as_image_url(raw, account_id=account_id)
                                for raw, _mime, _lab in refs) if u]
            res = fal.generate_image_from_prompt(
                prompt, model=q["model"], aspect=q["aspect"], reference_urls=urls,
                approved=True, db_path=None, account_id=account_id,
                source="direct", bank=True, brand_kit=False)
        if not res.get("ok"):
            raise RuntimeError(_render_failed(res.get("error"), "The still"))
        asset = res.get("asset_id")
        note = ""
        if refs and not nano and not res.get("references"):
            note = f" · {label} takes no reference images, drawn from the prompt"
        return {"detail": f"{label} · done{note}", "output": res.get("media_url"),
                "media": "image", "asset": f"gen:{asset}" if asset else None}

    job = jobs.start("make", f"image · {label} · {prompt[:50]}", work, account_id=account_id)
    return {"job_id": job["id"], "credits": q["credits"], "charged": q["charged"]}


# --- director mode: per-shot save-back --------------------------------------

class ShotPromptBody(BaseModel):
    prompt: str


class ShotGraphBody(BaseModel):
    # An unknown field is a 422 naming it, not a silent drop. Both of this
    # file's canvas models were loose, and that is how `images` was dropped
    # without a word in 2026-08-28 (see WfGenerateBody) and how a save
    # carrying seed_hash was accepted-and-ignored for weeks afterwards: the
    # route answered 200 and the caller had no way to learn otherwise.
    model_config = ConfigDict(extra="forbid")

    graph: dict
    states: Optional[dict] = None
    name: Optional[str] = None
    # what the canvas was drawn against (from the GET); a save carrying a
    # hash the shot no longer matches is refused rather than applied
    seed_hash: Optional[str] = None


@router.put("/concepts/{concept_id}/shots/{shot_n}/graph")
def shot_graph_save(concept_id: int, shot_n: int, body: ShotGraphBody,
        account_id: int = Depends(auth.current_account_id)):
    """Keep a shot's canvas — the node tree AND what each node produced.

    Run all used to save the graph to a throwaway workflow row purely so
    the runner had something to execute, and reopening the concept
    rebuilt the canvas from the shot and cleared every output. That made
    re-running a paid Gemini enhance the only way to see the enhanced
    prompt again (2026-08-28)."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    current = _shot_seed_hash(concept, shot_n)
    if current is None:
        return _error(404, "not_found", "no such shot")
    if not body.graph.get("nodes"):
        return _error(400, "empty_graph", "nothing to save")
    # The React canvas hands back the seed_hash it loaded against. A shot
    # revised underneath it (Direct, Polish, a replan) means the drawing
    # is of words the shot no longer says -- refuse, and the client
    # re-reads a fresh seed instead of overwriting a canvas it never saw.
    if body.seed_hash and body.seed_hash != current:
        return _error(409, "stale_canvas",
                      "the scene changed since this canvas was drawn -- reload it")
    workflow_id = workflows.save_shot_graph(
        concept_id, shot_n, body.graph, states=body.states,
        name=body.name or concept.get("title"),
        seed_hash=current,
        account_id=account_id)
    return {"ok": True, "id": workflow_id, "seed_hash": current}


def _shot_seed_hash(concept: dict, shot_n: int) -> Optional[str]:
    """What the canvas was drawn against. A saved graph carries a copy
    of the shot's prompt in its User Prompt node, so if the shot's
    prompt changes underneath it -- a Direct revision, a Polish, a
    replan -- the stored drawing is of a shot that no longer says that.

    The refs are in the hash for the same reason and were missed for a
    worse one: the graph freezes them into `ref_urls` on every billed
    node, so a shot whose references improve while its prompt stays
    identical restores a canvas still grounded on the old ones, and the
    next keyframe silently renders against a set nobody meant to use
    (2026-08-29 -- found re-attaching a scene's photos). A drawing of
    the wrong references is as stale as a drawing of the wrong words.
    """
    shot = next((s for s in (concept.get("shots") or [])
                 if s.get("n") == shot_n), None)
    if shot is None:
        return None
    seed = [shot.get("prompt") or ""]
    seed.extend(str(ref) for ref in (shot.get("refs") or []))
    return hashlib.sha256("\x00".join(seed).encode()).hexdigest()


@router.get("/concepts/{concept_id}/shots/{shot_n}/graph")
def shot_graph_get(concept_id: int, shot_n: int, account_id: int = Depends(auth.current_account_id)):
    """The saved canvas, or `graph: null` meaning build a fresh one.

    Staleness is checked HERE rather than invalidated from the handful
    of routes that can rewrite a prompt (direct, refine, approve, the
    canvas's own save). Comparing on read is self-healing: a route
    added later that rewrites a prompt cannot forget to call anything.
    """
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    current = _shot_seed_hash(concept, shot_n)
    if current is None:
        return _error(404, "not_found", "no such shot")
    saved = workflows.get_shot_graph(concept_id, shot_n,
                                     account_id=account_id)
    # `seed_hash` is always the CURRENT one -- what a save must carry --
    # so a fresh canvas and a stale one both learn what they are drawn against
    if saved is None:
        return {"graph": None, "states": None, "updated_at": None,
                "stale": False, "seed_hash": current}
    if saved.get("seed_hash") and saved["seed_hash"] != current:
        return {"graph": None, "states": None,
                "updated_at": saved["updated_at"], "stale": True,
                "seed_hash": current}
    saved["stale"] = False
    saved["seed_hash"] = current
    return saved


@router.delete("/concepts/{concept_id}/graph")
def shot_graph_reset(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """Throw the saved canvases away and rebuild from the shots — the
    escape hatch for a graph that has gone stale against its prompt.
    Someone else's concept is a 404, the same as a missing one."""
    if preprod.get_concept(concept_id, account_id=account_id) is None:
        return _error(404, "not_found", "no such concept")
    removed = workflows.delete_shot_graphs(concept_id,
                                           account_id=account_id)
    return {"ok": True, "removed": removed}


@router.post("/concepts/{concept_id}/shots/{shot_n}/prompt")
def shot_prompt_update(concept_id: int, shot_n: int, body: ShotPromptBody,
        account_id: int = Depends(auth.current_account_id)):
    """Persist one shot's edited prompt from the Director canvas --
    through update_concept_shots (so the picked title/hook/logline are
    never touched), re-validated the same way a fresh plan is. The
    other shots ride along unchanged."""
    from src import shootgen

    text = body.prompt.strip()
    if not text:
        return _error(400, "empty_prompt", "an empty prompt renders nothing")
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    shots = concept.get("shots") or []
    shot = next((s for s in shots if s.get("n") == shot_n), None)
    if shot is None:
        return _error(404, "not_found", f"no shot {shot_n}")
    before = shot.get("prompt") or ""
    # the edit teaches, for an account turned on (src/edit_teach.py) --
    # recorded BEFORE the write, against the text that stood until now
    taught = _teach_prompt_edit(account_id, concept, shot, before, text,
                                edit_teach.EDIT_NOTE)
    shot["prompt"] = text
    warnings = shootgen.validate_concept(
        {**concept, "shots": shots},
        [loc["name"] for loc in preprod.list_locations(account_id=account_id)],
        use_pov=bool(concept.get("use_pov")))
    preprod.update_concept_shots(concept_id, {"shots": shots},
                                 warnings=warnings, account_id=account_id)
    # the canvas that made this edit is still a true drawing of the shot;
    # hand it the new hash, or its very next autosave is refused as stale
    return {"concept_id": concept_id, "shot_n": shot_n, "warnings": warnings,
            "taught": taught,
            "seed_hash": _shot_seed_hash({**concept, "shots": shots}, shot_n)}


class ShotRefsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refs: list[str]
    # what the canvas was drawn against; a mismatch means someone else
    # re-grounded the scene since, and this list must not overwrite it
    seed_hash: Optional[str] = None


@router.put("/concepts/{concept_id}/shots/{shot_n}/refs")
def shot_refs_update(concept_id: int, shot_n: int, body: ShotRefsBody,
                     account_id: int = Depends(auth.current_account_id)):
    """The Director's reference wiring, saved back onto the scene
    (2026-09-18, Mike's call).

    The canvas's element cards used to live only in the saved graph, so
    rewiring a face changed what the canvas rendered but not the scene:
    the Pipeline card, the reference gate and the Queue's approve all
    kept reading the refs Create attached. Now the list the canvas has
    wired in IS `shot["refs"]`.

    An empty list is refused rather than stored. `preprod.reference_gate`
    keeps a scene with no refs out of the Queue, so clearing the canvas
    would silently make the scene unapprovable -- the scene keeps its
    last references instead, and the caller says so."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    current = _shot_seed_hash(concept, shot_n)
    if current is None:
        return _error(404, "not_found", f"no shot {shot_n}")
    if body.seed_hash and body.seed_hash != current:
        return _error(409, "stale_canvas",
                      "the scene changed since this canvas was drawn -- reload it")
    refs: list[str] = []
    for ref in body.refs:
        ref = (ref or "").strip()
        if not ref:
            continue
        if not ref.startswith(("http://", "https://", "/")):
            return _error(400, "invalid_url",
                          "a reference is a public http(s) URL or a site-relative path")
        stored = asset_shelf.storable_ref(ref)
        if stored not in refs:
            refs.append(stored)
    refs = refs[:MAX_IMAGE_REFS]
    if not refs:
        return _error(400, "no_references",
                      "a scene with no references can't reach the Queue -- "
                      "it keeps the ones it has")
    shots = [dict(s) for s in concept["shots"]]
    shot = next(s for s in shots if s.get("n") == shot_n)
    if refs == [asset_shelf.storable_ref(r) for r in (shot.get("refs") or [])]:
        return {"ok": True, "changed": False, "refs": refs, "seed_hash": current}
    shot["refs"] = refs
    preprod.update_concept_shots(
        concept_id, {"shots": shots, "duration": concept.get("duration")},
        warnings=concept.get("warnings") or [], account_id=account_id)
    return {"ok": True, "changed": True, "refs": refs,
            "seed_hash": _shot_seed_hash({**concept, "shots": shots}, shot_n)}


class ShotReferenceBody(BaseModel):
    url: str


@router.post("/concepts/{concept_id}/shots/{shot_n}/reference")
def shot_reference_attach(concept_id: int, shot_n: int, body: ShotReferenceBody,
                          account_id: int = Depends(auth.current_account_id)):
    """Attach (or clear, with "") an image URL as one shot's reference
    anchor -- how a Director-canvas Nano render lands back on the shot.
    The /ui JSON twin of the dev console's form route."""
    url = body.url.strip()
    if url and not url.startswith(("http://", "https://", "/")):
        return _error(400, "invalid_url",
                      "paste a public http(s) URL or a site-relative path")
    try:
        preprod.set_shot_reference_image(concept_id, shot_n, url, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    return {"concept_id": concept_id, "shot_n": shot_n,
            "reference_image": url or None}


@router.post("/concepts/{concept_id}/approve")
def concept_approve(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """Approve an idea = write ITS scene prompt (2026-08-26). Stage two
    used to explode an idea into a shot list; a concept is one scene now,
    so this fills in that one prompt. Only an idea needs it -- a concept
    that already carries its scene has nothing to write."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    if concept.get("shots"):
        return _error(409, "already_written",
                      "this concept already has its scene prompt")
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        from google import genai

        from src import shootgen
        jobs.progress(job, 0.2, "grounding in references")
        references = shootgen.reference_block(
            spark=concept.get("title"), db_path=None)
        jobs.progress(job, 0.4, "writing the scene prompt")
        result = shootgen.write_scene_for_concept(
            concept_id, gemini_client=genai.Client(api_key=api_key),
            references=references, db_path=None,
        )
        warnings = result.get("warnings") or []
        detail = "scene written"
        if warnings:
            detail += f" · {len(warnings)} warning(s)"
        return {"ref_id": concept_id, "detail": detail}

    job = jobs.start("plan", f"scene · {concept['title']}", work, account_id=account_id)
    return {"job_id": job["id"], "concept_id": concept_id}


class DenyBody(BaseModel):
    reasons: list[str]
    note: Optional[str] = None


@router.post("/concepts/{concept_id}/deny")
def concept_deny(concept_id: int, body: DenyBody, account_id: int = Depends(auth.current_account_id)):
    """Deny records WHY, then vacates the slot: the reasons + note become
    a correction the next generation's spark folds in (autonomy's
    human_note channel, consumed once), and the same text is written to
    the RAG 'denials' shelf as evidence. The correction always lands;
    the chunk is best-effort -- a down store must not lose the label."""
    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None:
        return _error(404, "not_found", "no such concept")
    reasons = [r for r in body.reasons if r in DENY_REASONS]
    if not reasons:
        return _error(400, "invalid_reasons",
                      f"reasons must be one or more of: {', '.join(DENY_REASONS)}")
    note = (body.note or "").strip()

    summary = f"Denied \"{concept['title']}\": {', '.join(reasons)}"
    if note:
        summary += f" — {note}"
    correction_id = autonomy.add_correction(summary)

    chunk_written = 0
    chunk_error = None
    text = "\n".join(filter(None, [
        f"DENIED CONCEPT: {concept['title']}",
        f"Reasons: {', '.join(reasons)}",
        f"Note: {note}" if note else None,
        f"Logline: {concept.get('logline') or ''}",
        f"Spark: {concept.get('spark') or ''}",
    ]))
    try:
        conn = rag.connect()
        try:
            rag.init_store(conn)
            # project is the TENANT that taught the lesson, not the brand
            # (src/rag.py's docstring says why the brand was the wrong key)
            chunk_written = rag.ingest_records(
                [{"source": f"denials/concept-{concept_id}", "text": text,
                  "domain": "denials",
                  "project": accounts.slug_of(account_id),
                  "source_ref": None}],
                rag.make_client(), conn,
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        chunk_error = str(e)

    preprod.delete_concept(concept_id, account_id=account_id)
    return {
        "denied": concept_id,
        "correction_id": correction_id,
        "chunks_written": chunk_written,
        "chunk_error": chunk_error,
    }


# --- evals ------------------------------------------------------------------

@router.get("/evals/golden")
def evals_golden(account_id: int = Depends(auth.current_account_id)):
    return {"items": evalstore.list_golden()}


class GoldenBody(BaseModel):
    query: str
    relevant: list[str]
    source: str = "probe"


@router.post("/evals/golden")
def evals_golden_add(body: GoldenBody, account_id: int = Depends(auth.current_account_id)):
    try:
        golden_id = evalstore.add_golden(body.query, body.relevant,
                                         source=body.source)
    except ValueError as e:
        return _error(400, "invalid_golden", str(e))
    return {"id": golden_id}


@router.delete("/evals/golden/{golden_id}")
def evals_golden_delete(golden_id: int, account_id: int = Depends(auth.current_account_id)):
    evalstore.delete_golden(golden_id)
    return {"deleted": golden_id}


@router.get("/evals/runs")
def evals_runs(account_id: int = Depends(auth.current_account_id)):
    return {"items": evalstore.list_runs()}


@router.get("/evals/runs/{run_id}")
def evals_run_detail(run_id: int, account_id: int = Depends(auth.current_account_id)):
    run = evalstore.get_run(run_id)
    if run is None:
        return _error(404, "not_found", "no such run")
    return run


class EvalRunBody(BaseModel):
    label: Optional[str] = None


@router.post("/evals/run")
def evals_run(body: EvalRunBody, account_id: int = Depends(auth.current_account_id)):
    """Compare one-shot retrieval with the complete CRAG retry path.

    Every metric is computed server-side and stored with the exact golden
    set, model, threshold, and reference-library identity that produced it.
    """
    golden = evalstore.list_golden()
    if not golden:
        return _error(400, "empty_golden", "the golden set is empty")
    api_key = _gemini_key(account_id)
    if not (api_key and _rag_reachable()):
        return _error(503, "evals_unavailable",
                      "needs the RAG store and GEMINI_API_KEY")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    cases = [{"query": g["query"], "relevant": g["relevant"]} for g in golden]
    # the view already appends "· n queries · k=…", so the default label
    # stays bare to avoid stuttering
    label = (body.label or "").strip() or "run"
    k = _eval_k()

    def work(job):
        conn = rag.connect()
        try:
            client = rag.make_client()
            times: list[float] = []
            done = {"n": 0}

            total_steps = len(cases) * 2

            def base_retrieve(query_text, k):
                jobs.check_cancelled(job)
                started = time.perf_counter()
                hits = rag.query(query_text, client, conn, k=k)
                times.append((time.perf_counter() - started) * 1000)
                done["n"] += 1
                jobs.progress(job, done["n"] / total_steps,
                              f"{done['n']}/{total_steps} retrieval checks")
                return hits

            def crag_retrieve(query_text, k):
                jobs.check_cancelled(job)
                started = time.perf_counter()
                outcome = crag.retrieve_with_crag(
                    query_text, client, CRAG_REWRITE_MODEL, k=k,
                    threshold=settings.grade_threshold(),
                    record_telemetry=False,
                )
                times.append((time.perf_counter() - started) * 1000)
                done["n"] += 1
                jobs.progress(job, done["n"] / total_steps,
                              f"{done['n']}/{total_steps} retrieval checks")
                return outcome

            result = rag_eval.evaluate_comparison(
                cases, base_retrieve, crag_retrieve, k=k)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        p50 = int(statistics.median(times)) if times else None
        library = rag.reference_library_identity()
        set_fingerprint = rag_eval.case_set_fingerprint(cases)
        result.update({
            "mode": "comparison",
            "library_count": library["count"],
            "library_fingerprint": library["fingerprint"],
            "set_fingerprint": set_fingerprint,
        })
        threshold = settings.grade_threshold()
        run_id = evalstore.save_run(
            label, result, p50_ms=p50,
            config={
                "k": k, "model": rag.EMBED_MODEL,
                "rewrite_model": CRAG_REWRITE_MODEL, "mode": "comparison",
                "threshold": threshold,
                "library_count": library["count"],
                "library_fingerprint": library["fingerprint"],
                "set_fingerprint": set_fingerprint,
            })
        return {"ref_id": run_id,
                "detail": f"CRAG hit@{k} {result['hit_rate']:.2f} · "
                          f"base {result['base_hit_rate']:.2f} · "
                          f"re-query {result['requery_rate']:.0%}"}

    job = jobs.start("eval", f"eval · {len(cases)} queries", work, account_id=account_id,
                     cancellable=True)
    return {"job_id": job["id"]}


# --- analytics --------------------------------------------------------------

def _video_rows(account_id: Optional[int] = None) -> list:
    """This account's videos with their latest numbers."""
    return db.latest_metrics_by_video(account_id=account_id)


@router.get("/analytics/summary")
def analytics_summary(platform: Optional[str] = None,
        account_id: int = Depends(auth.current_account_id)):
    rows = _video_rows(account_id)
    counts = {"all": len(rows)}
    for p in db.PLATFORMS:
        counts[p] = sum(1 for r in rows if r["platform"] == p)
    if platform in db.PLATFORMS:
        rows = [r for r in rows if r["platform"] == platform]
    return {
        "tiles": {
            "views": sum(r["views"] or 0 for r in rows),
            "likes": sum(r["likes"] or 0 for r in rows),
            "comments": sum(r["comments"] or 0 for r in rows),
            "saves": sum(r["saves"] or 0 for r in rows),
            "videos": len(rows),
        },
        "platform_counts": counts,
    }


@router.get("/analytics/posts")
def analytics_posts(platform: Optional[str] = None,
        account_id: int = Depends(auth.current_account_id)):
    rows = _video_rows(account_id)
    if platform in db.PLATFORMS:
        rows = [r for r in rows if r["platform"] == platform]
    ranked = sorted(rows, key=lambda r: (r["views"] is None, -(r["views"] or 0)))
    max_views = next((r["views"] for r in ranked if r["views"] is not None), 0)
    return {"items": [
        {**r, "pct": round((r["views"] or 0) / max_views * 100, 1) if max_views else 0}
        for r in ranked
    ]}


@router.get("/costs")
def costs_summary(runs: int = 14, account_id: int = Depends(auth.current_account_id)):
    """The cost tracker's numbers for this account (src/costs.summary):
    cost per kept clip per tool, cost per stage per night from the LLM
    meter, wasted spend, and today against the caps. Estimates."""
    from src import costs
    return costs.summary(account_id=account_id,
                         runs=max(1, min(int(runs), 90)))


@router.get("/analytics/accounts")
def analytics_accounts(account_id: int = Depends(auth.current_account_id)):
    """What is actually connected: platform key presence (real config, not
    a wish list) plus the autonomy channels and their levels."""
    return {
        "apis": [
            {"platform": "youtube", "label": "YouTube Data API v3",
             "configured": bool(os.environ.get("YOUTUBE_API_KEY"))},
            {"platform": "instagram", "label": "Instagram Graph API",
             "configured": bool(instagram.access_token())},
        ],
        "channels": [],
    }


@router.post("/videos/{video_id}/refresh")
def video_refresh(video_id: int, account_id: int = Depends(auth.current_account_id)):
    video = db.get_video(video_id, account_id=account_id)
    if video is None:
        return _error(404, "not_found", "video not found")
    if video["platform"] == "instagram":
        result = instagram.refresh_metrics_for_video(
            video, token=instagram.access_token(), db_path=None)
    else:
        result = youtube.refresh_metrics_for_video(
            video, api_key=os.environ.get("YOUTUBE_API_KEY"), db_path=None)
    if not result.get("ok"):
        return _error(502, "refresh_failed", str(result.get("error")))
    return result


# --- workflows --------------------------------------------------------------
# The node-graph canvas. A workflow row is LiteGraph's serialize() JSON
# stored whole; execution (Run all) walks it server-side in topological
# order through app/workflow_runner.py, one node at a time -- billed
# calls are sequential on purpose. The Generate node goes through
# fal.generate_from_prompt. Its spend gate still lives inside
# generate_video so this surface cannot become a second route that
# spends around it -- what satisfies the gate here is the person running
# the canvas (approved=True), not an environment variable.

class WorkflowBody(BaseModel):
    name: Optional[str] = None
    graph: Optional[dict] = None


@router.get("/workflows")
def workflows_list(account_id: int = Depends(auth.current_account_id)):
    """This account's canvases."""
    return {"items": workflows.list_workflows(account_id=account_id)}


@router.post("/workflows")
def workflows_create(body: WorkflowBody, request: Request,
                     account_id: int = Depends(auth.current_account_id)):
    # the body's `brand` is ignored: a canvas carries no label (2026-10-13)
    workflow_id = workflows.create_workflow(
        body.name or "Untitled workflow", body.graph or {},
        account_id=account_id)
    return {"id": workflow_id}


# the exec routes sit above /workflows/{workflow_id} so "exec" is never
# read as an id -- the /jobs/stream registration-order rule.

class GroundBody(BaseModel):
    spark: str = ""


@router.post("/workflows/exec/ground")
def workflow_exec_ground(body: GroundBody, account_id: int = Depends(auth.current_account_id)):
    """The Ground in References node: the existing RAG-grounding step
    (shootgen.reference_block) as a visible, wireable call. Degrades to
    "" with the store down, same as everywhere else."""
    from src import shootgen

    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    references = shootgen.reference_block(
        spark=body.spark.strip() or None, db_path=None)
    return {"references": references}


class EnhanceBody(BaseModel):
    system: str = ""
    user: str = ""
    images: list[str] = []
    references: str = ""
    ground: bool = False   # pull the RAG block server-side (Director chain)


@router.post("/workflows/exec/enhance")
def workflow_exec_enhance(body: EnhanceBody, account_id: int = Depends(auth.current_account_id)):
    """The Gemini 2.5 Flash enhance node's own Run: one billed Gemini
    call through generate_with_retry, images riding as vision input and
    the Ground node's references folded in as grounding. A job, so the
    canvas lights the node from the same SSE feed everything uses."""
    api_key = _gemini_key(account_id)
    if not api_key:
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")
    refused = _create_gate(account_id)
    if refused is not None:
        return refused

    def work(job):
        from google import genai

        from src import shootgen
        references = body.references
        if body.ground and not references:
            jobs.progress(job, 0.15, "grounding in references")
            references = shootgen.reference_block(
                spark=body.user.strip() or None, db_path=None)
        jobs.progress(job, 0.3, "enhancing prompt")
        text = workflow_runner.enhance(
            body.system, body.user, images=body.images or None,
            references=references,
            gemini_client=genai.Client(api_key=api_key),
            resolve_photo=_resolver(account_id), account_id=account_id)
        return {"detail": text[:80], "output": text}

    job = jobs.start("enhance", f"enhance · {(body.user or body.system)[:50]}", work,
                     account_id=account_id)
    return {"job_id": job["id"]}


class WfGenerateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    image: Optional[str] = None
    # The canvas posts the node's WHOLE reference list as `images`
    # (workflows.js referenceUrls), the same shape the enhance node
    # sends. Declaring only `image` meant pydantic dropped it without a
    # word, so a per-node Run on Nano Banana or Generate rendered with
    # no references at all -- the face, the jacket and the bike arrived
    # as a sentence and never as pixels (2026-08-28). `image` stays for
    # any caller that sends one.
    images: Optional[list[str]] = None
    # Optional: which renderer to spend on. Unset -- the canvas today --
    # means whatever this account can render (providers.renderer_for).
    provider: Optional[str] = None
    model: Optional[str] = None
    # Optional: the shot this node belongs to. Named, the render checks
    # the concept is this account's BEFORE any job starts, falls back to
    # the shot's own refs when the node posts none, and attaches its
    # output to the shot when it finishes -- a render that completes
    # after the browser closed still lands where the Director expects it.
    concept_id: Optional[int] = None
    shot_n: Optional[int] = None
    # the signed quote the chip showed (`generate.renders[0].token` on the
    # concept) -- optional, see ApproveBody.tokens
    token: Optional[str] = None

    def reference_urls(self) -> list[str]:
        urls, seen = [], set()
        for url in [*(self.images or []), self.image]:
            if isinstance(url, str) and url and url not in seen:
                seen.add(url)
                urls.append(url)
        return urls


_NO_SUCH_SHOT = object()


def _exec_shot(body: "WfGenerateBody", account_id: Optional[int]):
    """The shot a per-node render belongs to: None when the node is
    free-standing (no concept named), the shot dict when it is this
    account's, and _NO_SUCH_SHOT when the concept is not -- someone
    else's concept is a 404, the same as a missing one, checked before a
    single billed call. A named concept whose shot number is wrong
    still runs free-standing rather than failing a render over a
    stale n; there is just nothing to attach to."""
    if body.concept_id is None:
        return None
    concept = preprod.get_concept(body.concept_id, account_id=account_id)
    if concept is None:
        return _NO_SUCH_SHOT
    return next((s for s in (concept.get("shots") or [])
                 if s.get("n") == body.shot_n), None)


def _shot_refs(shot) -> list:
    """The references stored on the shot -- read at run time, the rule
    workflow_runner.shot_reference_urls states -- as the fallback when
    the node posted none."""
    if not shot:
        return []
    return [str(u) for u in (shot.get("refs") or []) if u]


@router.post("/workflows/exec/generate")
def workflow_exec_generate(body: WfGenerateBody, account_id: int = Depends(auth.current_account_id)):
    """The Generate node's own Run: one clip from a free-standing prompt
    + optional reference, on the renderer providers.renderer_for resolves
    -- the same resolver the Queue uses (fal, since 2026-09-26). Billed and
    capped; the click is the spend approval (2026-09-09) -- the gate
    still lives inside each adapter's generate_video."""
    shot = _exec_shot(body, account_id)
    if shot is _NO_SUCH_SHOT:
        return _error(404, "not_found", "no such concept")
    pick = providers.renderer_for(account_id, body.provider, body.model,
                                  needs="generate_from_prompt")
    if pick is None:
        return _error(503, "renderer_unavailable",
                      "video rendering is not configured on this server "
                      "(FAL_KEY is unset)")
    label = providers.RENDER_LABELS.get(pick["provider"], pick["provider"])
    required = _quote_required(account_id, pick["provider"])
    quote = None
    if body.token or required:
        if shot is None and body.token:
            return _error(400, "wrong_render",
                          "a quote names a concept's shot; this node has none")
        if shot is None:
            # a free-standing node has no shot for a quote to name, so there
            # is nothing a billable render here could be priced against
            return _error(400, "missing_quote",
                          "this render is billed in credits and needs a quoted price -- "
                          "open a concept's shot, or approve it in the Queue")
        try:
            priced = pricing.display(account_id=account_id, shot=shot, shot_id=body.concept_id,
                                     provider=pick["provider"], model=pick["model"], whole=True)
            quote = _verify_tokens([body.token] if body.token else [], priced, shot,
                                   body.concept_id, account_id)[0]
        except (pricing.QuoteRefused, pricing.SigningUnconfigured) as e:
            return _quote_refusal(e, account_id)
        except ValueError as e:
            return _error(400, "bad_render_choice", str(e))

    def work(job):
        jobs.progress(job, 0.2, f"rendering via {label} ({pick['model']})")
        # Every adapter anchors on exactly ONE frame, so of the references
        # the node carries only the first is usable -- same rule as the
        # graph runner's Generate branch.
        urls = body.reference_urls() or _shot_refs(shot)
        result = workflow_runner.render_generate_node(
            pick, body.prompt, urls[0] if urls else None,
            resolve_photo=_resolver(account_id), db_path=None,
            account_id=account_id, quote=quote)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "render failed")
        if shot is not None:
            preprod.set_shot_media_url(body.concept_id, body.shot_n,
                                       result["media_url"], account_id=account_id)
        return {"detail": f"clip rendered via {label} ({pick['model']})",
                "output": result["media_url"]}

    job = jobs.start("render", f"{label.lower()} · {body.prompt[:50]}", work,
                     account_id=account_id)
    return {"job_id": job["id"]}


@router.post("/workflows/exec/nano")
def workflow_exec_nano(body: WfGenerateBody, account_id: int = Depends(auth.current_account_id)):
    """The Nano Banana node's own Run: one Gemini image render from a
    free-standing prompt + optional reference. The still is charged to
    this account inside generate_from_prompt (2026-09-30: this route passed
    no account, so the still was drawn free and filed under the bootstrap
    account); the node's Run confirm is the approve that says its price."""
    from src import nano_banana

    shot = _exec_shot(body, account_id)
    if shot is _NO_SUCH_SHOT:
        return _error(404, "not_found", "no such concept")
    if not nano_banana.has_key():
        return _error(503, "generation_unavailable", "GEMINI_API_KEY not set")

    def work(job):
        jobs.progress(job, 0.2, "rendering via Nano Banana")
        # every reference, not just one: the face AND the jacket AND the
        # bike, matching the graph runner's Nano branch
        reference = [
            data for data in (
                imagery.image_bytes_for_gemini(
                    url, resolve_photo=_resolver(account_id), account_id=account_id)
                for url in (body.reference_urls() or _shot_refs(shot)))
            if data
        ]
        result = nano_banana.generate_from_prompt(
            body.prompt, reference_image=reference, db_path=None,
            account_id=account_id)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "render failed")
        if shot is not None:
            preprod.set_shot_reference_image(body.concept_id, body.shot_n,
                                             result["media_url"], account_id=account_id)
        return {"detail": "image rendered", "output": result["media_url"]}

    job = jobs.start("render", f"nano · {body.prompt[:50]}", work, account_id=account_id)
    return {"job_id": job["id"]}


@router.get("/workflows/{workflow_id}")
def workflows_get(workflow_id: int, account_id: int = Depends(auth.current_account_id)):
    workflow = workflows.get_workflow(workflow_id, account_id=account_id)
    if workflow is None:
        return _error(404, "not_found", "no such workflow")
    return workflow


@router.put("/workflows/{workflow_id}")
def workflows_update(workflow_id: int, body: WorkflowBody,
                     account_id: int = Depends(auth.current_account_id)):
    if not workflows.update_workflow(workflow_id, name=body.name,
                                     graph=body.graph,
                                     account_id=account_id):
        return _error(404, "not_found", "no such workflow")
    return {"id": workflow_id}


@router.delete("/workflows/{workflow_id}")
def workflows_delete(workflow_id: int, account_id: int = Depends(auth.current_account_id)):
    if not workflows.delete_workflow(workflow_id, account_id=account_id):
        return _error(404, "not_found", "no such workflow")
    return {"deleted": workflow_id}


@router.post("/workflows/{workflow_id}/run")
def workflows_run(workflow_id: int, account_id: int = Depends(auth.current_account_id)):
    """Run all: topological order over the SAVED graph (the client saves
    before it runs), sequential, every node's state pushed over the jobs
    SSE feed so the canvas lights up as nodes complete."""
    workflow = workflows.get_workflow(workflow_id, account_id=account_id)
    if workflow is None:
        return _error(404, "not_found", "no such workflow")
    graph = workflow.get("graph") or {}
    if not graph.get("nodes"):
        return _error(400, "empty_graph", "the workflow has no nodes to run")
    # gated like Create (2026-10-08): the enhance node is free per click
    # but billed to the studio; the Nano and Generate nodes hold credits
    # of their own and refuse on an empty balance regardless
    refused = _create_gate(account_id)
    if refused is not None:
        return refused
    api_key = _gemini_key(account_id)

    def work(job):
        gemini_client = None
        if api_key:
            from google import genai
            gemini_client = genai.Client(api_key=api_key)

        def emit(states, fraction, detail):
            jobs.update(job["id"], node_states=states)
            jobs.progress(job, fraction, detail)

        result = workflow_runner.execute_graph(
            graph, gemini_client=gemini_client,
            resolve_photo=_resolver(account_id), db_path=None,
            emit=emit, check_cancelled=lambda: jobs.check_cancelled(job),
            account_id=account_id)
        jobs.update(job["id"], node_states=result["nodes"])
        failed = [s for s in result["nodes"].values() if s["status"] == "failed"]
        if failed:
            raise RuntimeError(f"{len(failed)} node(s) failed — "
                               + (failed[0].get("error") or "see the board"))
        done = sum(1 for s in result["nodes"].values() if s["status"] == "done")
        return {"ref_id": workflow_id, "detail": f"{done} node(s) executed"}

    job = jobs.start("workflow", f"workflow · {workflow['name']}", work,
                     cancellable=True, account_id=account_id)
    return {"job_id": job["id"]}


# --- jobs -------------------------------------------------------------------

@router.get("/jobs")
def jobs_list(active: Optional[bool] = None,
              account_id: int = Depends(auth.current_account_id)):
    return {"items": jobs.list_jobs(active=active, account_id=account_id)}


@router.get("/jobs/stream")
async def jobs_stream(account_id: int = Depends(auth.current_account_id)):
    """SSE. The job rail, the queue view, and the pipeline cards all
    subscribe here -- the only push channel, nothing polls. Registered
    before /jobs/{job_id} so 'stream' isn't captured as an id.

    The registry publishes every job to every subscriber; the filter
    is here, at the one place the account is known, so a subscriber
    only ever sees its own.

    THE REACT STUDIO'S ONE CONNECTION (2026-10-08, the activity tray):
    - `retry: 3000` first, so a dropped connection is retried in three
      seconds rather than the browser's own guess;
    - `event: hello` with this process's boot id: job ids restart at 1
      with the registry, and a tab that saw another boot drops what it
      held instead of matching a new job 7 with an old one;
    - then every live job and the newest finished ones (`jobs.replay`),
      not everything a long-running process ever ran;
    - `event: job` with the whole job on every change, and `event: gone`
      when one is cleared, so every open tab drops it;
    - `no-transform`: Next's proxy gzips any text/* response it is not
      told to leave alone, and a gzipped stream sits in the compressor --
      the events would arrive in a lump, or never."""
    queue = jobs.subscribe()

    async def gen():
        import asyncio
        try:
            yield "retry: 3000\n\n"
            yield f"event: hello\ndata: {json.dumps({'boot': jobs.BOOT})}\n\n"
            # current state first, so a fresh subscriber isn't blind
            for job in jobs.replay(account_id=account_id):
                yield f"event: job\ndata: {json.dumps(job)}\n\n"
            while True:
                try:
                    job = await asyncio.wait_for(queue.get(), timeout=25)
                    if not jobs.owned_by(job, account_id):
                        continue
                    if job.get("gone"):
                        yield f"event: gone\ndata: {json.dumps({'id': job['id']})}\n\n"
                        continue
                    yield f"event: job\ndata: {json.dumps(job)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            jobs.unsubscribe(queue)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform",
                                      "X-Accel-Buffering": "no"})


@router.delete("/jobs")
def jobs_clear_finished(account_id: int = Depends(auth.current_account_id)):
    """Clear every finished job of yours (the tray's "Clear finished");
    running ones stay. Each one cleared is said on the stream."""
    return {"cleared": jobs.clear_finished(account_id=account_id)}


@router.get("/jobs/{job_id}")
def job_detail(job_id: int, account_id: int = Depends(auth.current_account_id)):
    job = jobs.get(job_id, account_id=account_id)
    if job is None:
        return _error(404, "not_found", "no such job")
    return job


@router.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: int, account_id: int = Depends(auth.current_account_id)):
    job = jobs.cancel(job_id, account_id=account_id)
    if job is None:
        return _error(404, "not_found", "no such job")
    return jobs.snapshot(job)


@router.delete("/jobs/{job_id}")
def job_clear(job_id: int, account_id: int = Depends(auth.current_account_id)):
    removed = jobs.remove(job_id, account_id=account_id)
    if removed is None:
        return _error(404, "not_found", "no such job")
    if not removed:
        return _error(409, "not_finished", "only finished jobs can be cleared")
    return {"deleted": job_id}


# --- billing (2026-09-18) --------------------------------------------------
# The customer-facing Stripe routes live in app/billing.py and are included
# HERE so they sit under /api, behind the session gate, and inside the
# route audit in tests/test_tenancy.py. The webhook is deliberately not.
from . import billing as _billing  # noqa: E402  (bottom of the file on purpose)

for _path, _endpoint, _methods in _billing.API_ROUTES:
    router.add_api_route(_path, _endpoint, methods=_methods, tags=["billing"])


# --- the cut (2026-09-26, docs/tasks/CUT_ASSEMBLE_V0.md) -------------------
# Assemble v0: approved clips -> a versioned timeline -> one MP4. Same
# placement as billing above, for the same reasons.
from . import cut_routes as _cut_routes  # noqa: E402

router.include_router(_cut_routes.router)


# --- brand kits (2026-10-20, docs/tasks/task-brand-kit.md) -----------------
# A client's identity, look, voice and sound that a project picks. Same
# placement as billing and the cut above, for the same reasons.
from . import brand_routes as _brand_routes  # noqa: E402

router.include_router(_brand_routes.router)


# --- editing-app panels (2026-10-22, docs/tasks/task-premiere-plugin.md) ----
# The studio's half of a Premiere panel's sign-in: approving its code, and
# the list of connected panels with Disconnect. The panel's own door
# (/plugin/v1, a bearer token) is app/plugin_api.router, mounted in main.
from . import plugin_api as _plugin_api  # noqa: E402

router.include_router(_plugin_api.studio_router)
