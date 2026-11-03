"""The OAuth consent page -- what Supabase's OAuth 2.1 server sends a person
to when an MCP client (Claude) asks to act on their studio (2026-10-07,
docs/directory/OAUTH_TEST.md Finding 3).

WHY IT IS OURS TO SERVE. Supabase is the authorization server: it validates
the client, PKCE and the redirect, issues the code and the tokens. It does
NOT draw the consent screen. Its /oauth/authorize redirects the person to
`<Site URL><Authorization Path>?authorization_id=<id>` and waits for the
app to answer, AS THE PERSON, either

    GET  /auth/v1/oauth/authorizations/{id}           -> the details, or a
                                                         redirect_url when
                                                         they consented before
    POST /auth/v1/oauth/authorizations/{id}/consent   {"action": "approve"|"deny"}
                                                      -> {"redirect_url": ...}

(read off supabase-js's `_getAuthorizationDetails` / `_approveAuthorization`
/ `_denyAuthorization`, 2026-10-07). Until this page existed the connector
could not be connected from claude.ai at all: the flow ended on a 404.

WHERE THE PERSON'S TOKEN COMES FROM. Both calls need the person's own
Supabase access token, and this app keeps none -- the phantra_session cookie
carries only the verified user id (app/auth.py's docstring says why). So
the page sends the person through the ordinary sign-in, whichever door
they like, and `resume` -- called from `auth._finish`, which every door
ends in -- parks THAT sign-in's access token in the starlette session for
this one step, beside a CSRF value, keyed to the authorization id. The
POST spends it and drops it. The same pattern as the password reset
(`RESET_TOKEN_SESSION_KEY`): a token minted for one write, never stored
past it. Signing in here also runs `_provision`, so a person whose first
contact with the studio is the connector gets their workspace on this
page, which is the "one web sign-in first" Mike chose for first contact.

WHAT IT SHOWS. The client's name, the HOST of the redirect URI in bold
(the connector checklist's "display the redirect URI's hostname clearly",
with the spec's extra warning when it is a loopback address -- any local
process can claim one), the scopes, and who is signing in. Nothing here
spends money or reads the board.
"""
from __future__ import annotations

import hmac
import os
import re
import secrets as _secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src import accounts, billing, ledger, mcp_connections, pricing

from . import auth

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

CONSENT_PATH = "/oauth/consent"
PENDING_KEY = "oauth_consent_pending"   # an authorization id waiting on a sign-in
GRANT_KEY = "oauth_consent_grant"       # {"id", "token", "csrf"} for one decision

# Supabase's authorization ids are UUIDs today; accept a little more than
# that, never anything that could break out of a URL path segment.
_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
# A desktop app's own redirect scheme (RFC 8252 7.1), and the schemes no
# app address may use: they run code, read files or stay in the browser.
_APP_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*$")
_NEVER_SCHEMES = {"javascript", "vbscript", "data", "file", "blob", "about",
                  "filesystem", "view-source", "chrome", "ftp", "ws", "wss"}
# How long a consent waits on a sign-in. Past this the pending id is
# forgotten, so a person who walked away is not shown "Connect an app" on
# their next visit. Supabase's own authorization request lasts about TEN
# minutes (measured live 2026-10-08: two requests were gone 10m48s and
# 11m14s after they were made). Deliberately LONGER than that, not equal:
# a person who signs in at minute twelve should come back here and be
# told the request expired (EXPIRED), not be dropped in the studio with
# no word about the app they were connecting.
PENDING_MAX_AGE = 15 * 60
# How long a sign-in ALREADY UNDER WAY still comes back here. The sign-in
# page drops a stale id when it is drawn (`pending`), but a person who
# opened it in time and finished signing in past PENDING_MAX_AGE never
# draws it again: `resume` must still send them back, so the page can say
# the request expired, not drop them in the studio. Measured 2026-11-02:
# a Google sign-in begun 29 minutes after the page opened landed in the
# studio with no word about the app. Bounded, so a forgotten tab cannot
# turn a sign-in hours later into a connection screen.
RESUME_MAX_AGE = 60 * 60
PAID_EXPIRED = ("Your plan is active. The connection request timed out while you were "
                "checking out -- they last about ten minutes. Go back to the app you came "
                "from and connect again; it goes straight through this time.")
EXPIRED = ("This connection request has expired -- they last about ten minutes. "
           "Go back to the app you came from and connect again.")


# THE PLAN PICKER (2026-11-03, Mike: "do what Krea does, but still have
# the free plan for people that don't have accounts"). Connecting an app
# shows the three plans first, Krea's shape. A workspace made in THIS
# connection -- the person had no account and signed up on the way here --
# may also continue on the free trial. An older workspace with no plan
# must pick one. Passing straight through: a plan, credit_exempt, or paid
# credit still unspent (a top-up, or the adjustment grant a directory
# reviewer's account is given). Only the connect step is gated: the
# connector itself still serves every workspace (pricing.py, 2026-10-21),
# so an app connected before this keeps working, and Supabase skips this
# page for a person who already consented to that app.
PAYWALL_ENV = "PHANTRA_CONNECT_PAYWALL"      # "0" turns the picker off
NEW_ACCOUNT_WINDOW = 60 * 60                # "made in this connection"
PAID_KINDS = ledger.BEYOND_TRIAL_KINDS


def _valid_id(authorization_id: str) -> bool:
    return bool(_ID.match(authorization_id or ""))


def _waiting(request: Request, max_age: float) -> Optional[str]:
    """The pending authorization id while it is younger than `max_age`;
    an older one is forgotten."""
    value = request.session.get(PENDING_KEY)
    if not isinstance(value, dict) or not _valid_id(value.get("id") or ""):
        return None
    if time.time() - float(value.get("at") or 0) > max_age:
        request.session.pop(PENDING_KEY, None)
        return None
    return value["id"]


def pending(request: Request) -> Optional[str]:
    """The authorization id a sign-in on this browser is FOR, if any --
    what /signin reads to say why the person is there and to skip its
    already-signed-in shortcut (the consent needs a fresh Supabase
    session even when our own cookie is good)."""
    return _waiting(request, PENDING_MAX_AGE)


def resume(request: Request, session: dict) -> Optional[RedirectResponse]:
    """Called from auth._finish with the GoTrue session a sign-in just
    produced. When a consent was waiting, keep that sign-in's access token
    for the decision and go back to the page; otherwise None and the
    sign-in finishes as it always has. Read against RESUME_MAX_AGE, not
    PENDING_MAX_AGE: past ten minutes Supabase has forgotten the request
    and the page says so (EXPIRED)."""
    authorization_id = _waiting(request, RESUME_MAX_AGE)
    request.session.pop(PENDING_KEY, None)
    if authorization_id is None:
        return None
    token = session.get("access_token") or ""
    if not token:
        return None
    request.session[GRANT_KEY] = {"id": authorization_id, "token": token,
                                  "csrf": _secrets.token_urlsafe(24)}
    return RedirectResponse(f"{CONSENT_PATH}?authorization_id={quote(authorization_id)}",
                            status_code=303)


def _grant(request: Request, authorization_id: str) -> Optional[dict]:
    """The parked grant for THIS authorization id, while its token still
    verifies (Supabase access tokens last about an hour)."""
    grant = request.session.get(GRANT_KEY)
    if not isinstance(grant, dict) or grant.get("id") != authorization_id:
        return None
    if not auth.verify_token(grant.get("token") or ""):
        request.session.pop(GRANT_KEY, None)
        return None
    return grant


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(auth._session_secret(), salt="phantra-consent-pending")


def adopt(request: Request, token: Optional[str]) -> None:
    """The receiving end of `_to_signin`: a signed `consent` token on
    /signin becomes this origin's pending authorization id, so the sign-in
    that follows (which runs HERE) resumes the consent. Anything that does
    not verify is ignored -- a forged or stale link changes nothing."""
    if not token:
        return
    try:
        data = _serializer().loads(token, max_age=PENDING_MAX_AGE)
    except BadSignature:
        return
    authorization_id = data.get("id") if isinstance(data, dict) else None
    if isinstance(authorization_id, str) and _valid_id(authorization_id):
        request.session[PENDING_KEY] = {"id": authorization_id, "at": time.time()}
        request.session.pop(GRANT_KEY, None)


def _to_signin(request: Request, authorization_id: str) -> RedirectResponse:
    """Send the person to sign in, carrying the authorization id with them.

    The consent page is reached on the site's origin (Supabase's Site URL,
    proxied by web/next.config.ts) but a sign-in always finishes on the API
    origin, where the OAuth callback lives and where the PKCE verifier was
    set. Cookies do not cross between the two, so a pending id parked in
    THIS origin's session never reached `resume` and the person landed in
    the studio. The id travels instead as a short-lived signed token to
    the API origin's /signin, which adopts it into its own session."""
    request.session[PENDING_KEY] = {"id": authorization_id, "at": time.time()}
    request.session.pop(GRANT_KEY, None)
    token = _serializer().dumps({"id": authorization_id})
    # absolute: url_for names the origin the sign-in callback lives on
    target = str(request.url_for("signin").include_query_params(consent=token))
    return RedirectResponse(target, status_code=303)


def _page(request: Request, status: int = 200, **context: Any) -> HTMLResponse:
    return templates.TemplateResponse(request, "oauth_consent.html", context,
                                      status_code=status)


def _problem(request: Request, message: str, status: int = 400) -> HTMLResponse:
    return _page(request, status, problem=message)


def _gone(status: int, body: Any) -> bool:
    """Supabase no longer knows the authorization -- in practice, it
    expired. Its own words for that are "authorization not found", which
    reads like a bug to the person who just signed in."""
    code = body.get("error_code") if isinstance(body, dict) else None
    return status == 404 or code == "oauth_authorization_not_found"


def _safe_redirect(url: Any) -> Optional[str]:
    """Supabase's redirect_url, followed only when it is an absolute
    http(s) URL or a desktop app's own address (`cursor://...`) -- the
    authorization server validated the client's redirect URI, this just
    refuses a javascript:, a data: or a path. Measured 2026-11-03: Cursor
    registers `cursor://anysphere.cursor-mcp/oauth/callback`, and an
    http-only rule left it on "Needs authentication" after every Allow."""
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    if not parts.netloc:
        return None
    if parts.scheme in ("https", "http"):
        return url
    if _APP_SCHEME.match(parts.scheme) and parts.scheme not in _NEVER_SCHEMES:
        return url
    return None


def _back_to(request: Request, target: str, client_name: str = "") -> Any:
    """Send the person back to the app. A web address is a 303, as it
    always was; a desktop app's address is a page that opens it, with a
    link, because a browser may hold back opening another program until
    the person clicks."""
    if urlsplit(target).scheme in ("https", "http"):
        return RedirectResponse(target, status_code=303)
    return _page(request, back=target, client_name=client_name or "the app")


def _host(uri: Any) -> str:
    try:
        parts = urlsplit(uri or "")
    except ValueError:
        return ""
    return (parts.hostname or "").lower()


def _account_for(grant: dict) -> Optional[dict]:
    """The workspace this sign-in connects: the person's OLDEST membership,
    the rule mcp_auth.account_for_token resolves every MCP call by."""
    user_id = (auth.verify_token(grant.get("token") or "") or {}).get("sub")
    if not user_id:
        return None
    member_of = accounts.memberships(str(user_id))
    if not member_of:
        return None
    return min(member_of, key=lambda a: int(a["id"]))


def _age_seconds(stamp: Any) -> Optional[float]:
    try:
        made = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if made.tzinfo is None:
        made = made.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - made).total_seconds()


def _has_paid_credit(account_id: int) -> bool:
    return any(lot["kind"] in PAID_KINDS and int(lot["credits_remaining"] or 0) > 0
               for lot in ledger.lots(account_id, include_expired=False))


def offer(account: Optional[dict]) -> dict:
    """What the consent page asks of this workspace before Allow:
    {"paywall": bool, "free_trial": bool}. `paywall` False is the old page
    (Allow straight away). `free_trial` True puts "Continue with free
    trial" under the plans. Fails OPEN on any read error: connecting
    spends nothing, so a broken read must never lock a person out."""
    through = {"paywall": False, "free_trial": False}
    if account is None or os.environ.get(PAYWALL_ENV, "1").strip() == "0":
        return through
    if not billing.configured():
        return through          # nothing could be bought: never a dead end
    try:
        account_id = int(account["id"])
        if accounts.plan_of(account_id) or accounts.is_credit_exempt(account_id):
            return through
        if _has_paid_credit(account_id):
            return through
        age = _age_seconds(account.get("created_at"))
    except Exception as exc:  # noqa: BLE001 -- see docstring
        print(f"[oauth-consent] plan check failed, letting through: {exc}", file=sys.stderr)
        return through
    return {"paywall": True,
            "free_trial": age is not None and age <= NEW_ACCOUNT_WINDOW}


def plan_cards() -> list[dict]:
    """The three plans as the picker draws them, both intervals at once
    (the toggle only shows one or the other)."""
    cards = []
    for plan in pricing.PLANS.values():
        cards.append({
            "key": plan.key, "name": plan.name, "blurb": plan.blurb,
            "credits": f"{plan.credits:,}", "monthly_usd": plan.monthly_usd,
            "yearly_monthly_usd": plan.yearly_monthly_usd, "yearly_usd": plan.yearly_usd,
            "popular": plan.popular, "storage_gb": plan.storage_gb,
        })
    return cards


def _consent_url(request: Request, authorization_id: str, extra: str = "") -> str:
    base = str(request.url_for("consent_page"))
    return f"{base}?authorization_id={quote(authorization_id)}{extra}"


def describe(details: dict) -> dict:
    """The details Supabase returned, as the page draws them. Pure, so the
    exact words a person approves are testable without a server."""
    client = details.get("client") or {}
    redirect_host = _host(details.get("redirect_uri"))
    scopes = [s for s in str(details.get("scope") or "").split() if s]
    return {
        "client_name": str(client.get("name") or "An application"),
        "client_host": _host(client.get("uri")),
        "redirect_host": redirect_host or "(no redirect address)",
        "loopback": redirect_host in LOOPBACK,
        "scopes": scopes,
        "email": str((details.get("user") or {}).get("email") or ""),
    }


@router.get(CONSENT_PATH, name="consent_page")
def consent_page(request: Request, authorization_id: str = "", checkout: str = "",
                 session_id: str = ""):
    if not _valid_id(authorization_id):
        return _problem(request, "This link is missing its authorization request. "
                                 "Start the connection again from the app you came from.")
    if not auth.configured():
        return _problem(request, "Sign-in isn't configured on this server.", 503)
    if auth._rate_limited(request, "consent"):
        return _problem(request, "Too many attempts -- wait a minute and try again.", 429)
    grant = _grant(request, authorization_id)
    if grant is None:
        return _to_signin(request, authorization_id)

    status, body = auth.gotrue("GET", f"/oauth/authorizations/{quote(authorization_id)}",
                               token=grant["token"])
    if status == 401:
        return _to_signin(request, authorization_id)
    if status >= 400:
        request.session.pop(GRANT_KEY, None)
        if _gone(status, body):
            return _problem(request, PAID_EXPIRED if checkout == "success" else EXPIRED)
        return _problem(request, auth._error_text(
            body, "This authorization request has expired or was already used. "
                  "Start the connection again from the app you came from."))
    if "authorization_id" not in body:
        # consented before: Supabase hands back the client's redirect directly
        request.session.pop(GRANT_KEY, None)
        target = _safe_redirect(body.get("redirect_url"))
        if target:
            return _back_to(request, target)
        return _problem(request, "The authorization server gave no way back to the app.", 502)
    shown = describe(body)
    # what the person is about to approve, kept beside the grant so the
    # POST can record WHICH client was allowed (the "Connected to Claude"
    # line in the studio's account menus) -- the POST gets only a decision
    account = _account_for(grant)
    asked = offer(account)
    paid = bool(grant.get("paid"))
    if asked["paywall"] and not paid and checkout == "success" and account is not None:
        # back from Checkout before the webhook set the plan: Stripe's own
        # word for THIS session, opened for THIS account, settles it
        paid = billing.checkout_completed(session_id, int(account["id"]))
    request.session[GRANT_KEY] = {**grant, "client_name": shown["client_name"],
                                  "redirect_host": _host(body.get("redirect_uri")),
                                  "paid": paid}
    paywall = asked["paywall"] and not paid
    return _page(request, authorization_id=authorization_id, csrf=grant["csrf"],
                 paywall=paywall, free_trial=asked["free_trial"],
                 trial_credits=accounts.signup_credits(), plans=plan_cards() if paywall else [],
                 save_pct=round(float(pricing.YEARLY_DISCOUNT) * 100),
                 just_paid=paid and checkout == "success",
                 cancelled=checkout == "cancelled", **shown)


def _remember(grant: dict) -> None:
    """An approved connection, recorded for the studio's account menus
    (src/mcp_connections.py). The account is the person's OLDEST
    membership -- the rule `mcp_auth.account_for_token` resolves every MCP
    call by, so the panel and the board agree about whose connection it
    is. Best-effort: the person has already said yes and Supabase has
    already answered, so a failed write here must never stand between
    them and the app they are connecting."""
    try:
        user_id = (auth.verify_token(grant.get("token") or "") or {}).get("sub")
        if not user_id:
            return
        member_of = accounts.memberships(str(user_id))
        if not member_of:
            return      # no workspace: the MCP refuses this person anyway
        mcp_connections.record_approval(
            min(int(a["id"]) for a in member_of), str(user_id),
            str(grant.get("client_name") or ""), str(grant.get("redirect_host") or ""))
    except Exception as exc:  # noqa: BLE001 -- bookkeeping, never the decision
        print(f"[oauth-consent] could not record the connection: {exc}", file=sys.stderr)


@router.post(CONSENT_PATH)
def consent_decision(request: Request, authorization_id: str = Form(""),
                     decision: str = Form(""), csrf: str = Form("")):
    if not _valid_id(authorization_id):
        return _problem(request, "This form is missing its authorization request.")
    if auth._rate_limited(request, "consent"):
        return _problem(request, "Too many attempts -- wait a minute and try again.", 429)
    grant = _grant(request, authorization_id)
    if grant is None:
        # the token expired, or this browser never signed in for it: start over
        return _to_signin(request, authorization_id)
    if not hmac.compare_digest(str(csrf), str(grant.get("csrf") or "")):
        return _problem(request, "This form has expired. Go back and try again.", 403)
    action = "approve" if decision == "approve" else "deny"
    if action == "approve" and not grant.get("paid"):
        asked = offer(_account_for(grant))
        if asked["paywall"] and not asked["free_trial"]:
            # the form had no Allow on it; a hand-made POST gets no further
            return _problem(request, "Pick a plan to connect this app. "
                                     "Go back and choose one.", 402)
    status, body = auth.gotrue(
        "POST", f"/oauth/authorizations/{quote(authorization_id)}/consent",
        json={"action": action}, token=grant["token"])
    # one decision per sign-in: the token is dropped whatever the answer
    request.session.pop(GRANT_KEY, None)
    if status >= 400:
        if _gone(status, body):
            return _problem(request, EXPIRED)
        return _problem(request, auth._error_text(
            body, "The authorization server refused that answer. "
                  "Start the connection again from the app you came from."))
    target = _safe_redirect(body.get("redirect_url"))
    if not target:
        return _problem(request, "The authorization server gave no way back to the app.", 502)
    if action == "approve":
        _remember(grant)
    return _back_to(request, target, str(grant.get("client_name") or ""))


@router.post(CONSENT_PATH + "/plan")
def consent_plan(request: Request, authorization_id: str = Form(""), csrf: str = Form(""),
                 item: str = Form(""), interval: str = Form("month")):
    """A plan picked on the consent page: a Stripe Checkout for the
    workspace this sign-in connects, returning to this same consent step
    (then Allow sends the person back to the app)."""
    if not _valid_id(authorization_id):
        return _problem(request, "This form is missing its authorization request.")
    if auth._rate_limited(request, "consent"):
        return _problem(request, "Too many attempts -- wait a minute and try again.", 429)
    grant = _grant(request, authorization_id)
    if grant is None:
        return _to_signin(request, authorization_id)
    if not hmac.compare_digest(str(csrf), str(grant.get("csrf") or "")):
        return _problem(request, "This form has expired. Go back and try again.", 403)
    key = (item or "").strip().lower()
    if not billing.is_plan(key):
        return _problem(request, "Pick one of the plans shown.")
    account = _account_for(grant)
    if account is None:
        return _problem(request, "This sign-in has no workspace yet. Sign in to the studio "
                                 "once, then connect again.", 403)
    email = (auth.verify_token(grant.get("token") or "") or {}).get("email")
    try:
        url = billing.checkout_url(
            int(account["id"]), key, interval=(interval or "month"), email=email,
            success_url=_consent_url(request, authorization_id,
                                     "&checkout=success&session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=_consent_url(request, authorization_id, "&checkout=cancelled"))
    except billing.BillingUnconfigured:
        return _problem(request, "Plans can't be bought on this server right now.", 503)
    except ValueError as exc:
        return _problem(request, str(exc))
    return RedirectResponse(url, status_code=303)
