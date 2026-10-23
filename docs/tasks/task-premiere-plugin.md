# Task: a Phantra panel inside Adobe Premiere Pro

**From:** a Cowork session, 2026-10-22. **Mike's calls (in chat):** full making inside
Premiere (not just the Library); sign in with a code entered at phantra.ai; the panel's code in
a new repo `phantra-premiere-plugin` beside the Claude and ChatGPT plugin repos (asked for public,
made PRIVATE with a proprietary license on 2026-10-23, Mike's call); the API
side first, because his Mac's Premiere may be older than 25.6. Standing rules that apply: no
changes to the MCP connector while it is in directory review; nothing spends without a price the
person saw; no renders during the build unless Mike says so.

## What the person gets

1. Install the panel (later: from Adobe's Creative Cloud Marketplace), open
   Window > Extensions > Phantra.
2. **Sign in:** the panel shows a code like `KDPX-7QHR` and opens `phantra.ai/studio/link`.
   Signed in to the studio, they TYPE the code and press **Connect Premiere Pro**. The panel is
   connected; no password ever goes into Premiere. (The code is never in the link: see As built.)
3. **Library tab:** their renders and uploads, newest first, filter image / video / audio.
   **Import** puts one in the Premiere project (a "Phantra" bin); **Insert at playhead** also
   drops it on the active sequence.
4. **Make tab:** Image or Video, a prompt, model, frame (and length for video).
   - Image: `generate_image` priced first; the card shows the credits and the balance after; the
     still is drawn only on **Approve**.
   - Video: the scene is written from the prompt and one reference (a Library still or an
     element photo; the reference gate still applies: no picture, no clip), then the render is
     quoted and runs only on **Approve**.
   - Effects on a Library item: upscale, animate a still, camera move, add sound, reframe,
     remove background, edit image, each quoted, each its own Approve.
   - When a job finishes, the result is downloaded and imported, and dropped at the playhead if
     the person ticked that.
5. **Disconnect:** in the panel (signs this copy out), or in the studio's Settings > Connect MCP,
   which lists every connected copy of the panel with its last use.

## How it is built

**One rule:** the panel reaches exactly the code the ChatGPT connector already runs. The API
builds its own instance of the render listing (`mcp_server.build_server(listed=True, ...)`, the
same injected job registry and approve bodies `app.main` hands the MCP mount) and calls its
tools by name with `call_tool`. Quotes, signed single-use tokens, ledger holds, refusals and
job polling are therefore the ones already reviewed and tested. Nothing in `src/mcp_server.py`,
`app/mcp_mount.py` or `app/mcp_auth.py` changes.

- `src/plugin_tokens.py`: two tables.
  - `plugin_pairings` (SHARED: a pairing has no account until a person approves it):
    the device secret's hash, the short code, the client label, expiry (10 minutes), who approved
    it and when, and whether its token was handed out (once).
  - `plugin_tokens` (OWNED): account, person, client label, the token's SHA-256 (the token itself
    is never stored), created / last used / revoked.
  - Tokens are `php_<43 url-safe chars>`. Codes are 8 characters from an alphabet with no
    look-alikes (no 0/O/1/I), shown as `XXXX-XXXX`.
- `app/plugin_api.py`, router `/plugin/v1` (outside `/api`, like the MCP mount: the caller holds
  a token, not a cookie):
  - `POST /plugin/v1/pair` starts a pairing; `POST /plugin/v1/pair/token` is polled with the device
    secret (`authorization_pending`, `expired_token`, then the token, once).
  - `GET /plugin/v1/me`: who and which workspace, and the balance.
  - `POST /plugin/v1/tools/{name}`: one of `PLUGIN_TOOLS` (a subset of the render listing's
    tools) with the bearer token; the caller's account goes on `mcp_server.CALLER_ACCOUNT` for
    that call only, reset in a `finally`, exactly as the MCP guard does. Rate limited per account.
  - `GET /plugin/v1/download/{ref}`: a render's file as an attachment (the Library's own download
    body), for machines with no bucket.
  - `POST /plugin/v1/signout`: revokes the calling token.
- `/api` (cookie, `auth.current_account_id`, the mutation header):
  - `POST /api/plugin/link {code}` approves a pairing for the signed-in person's tenant.
  - `GET /api/plugin/connections`, `POST /api/plugin/connections/{id}/revoke`.
- Studio: `/studio/link` (enter or confirm the code, warns "only enter a code your own Premiere
  panel shows you"), and an "Apps" card in Settings > Connect MCP.

## Security notes

- A code is only useful with the device secret that started it, which never leaves the panel;
  approving needs a signed-in session plus the mutation header (so another site cannot approve a
  code in the background), and an explicit click on a page that names the client.
- Code entry is rate limited; a code expires in 10 minutes and its token is handed out once.
- A revoked or unknown token is a plain 401; a token reaches only `PLUGIN_TOOLS`, never `/api`.

## Not in v1

After Effects (still on Adobe's older CEP system as of 2025; port once UXP lands there), DaVinci
Resolve (next), sending a timeline frame up to Phantra (the panel opens `upload_link`'s page
instead), Marketplace listing (after Mike has tested it in Premiere 25.6+).

## As built (2026-10-22)

- API: `src/plugin_tokens.py`, `app/plugin_api.py`, wired in `app/main.py` (configure, router,
  init) and `app/api.py` (the studio router, at the bottom). `tests/test_plugin_api.py` (31);
  `tests/test_tenancy.py` lists the two hash lookups that cannot name an account first. Full
  suite: 4618 passed; the one failure (`test_generative_init_once` under `-n 8`) passes alone,
  with and without this change.
- Studio: `/studio/link` (`components/studio/link-app.tsx`), the Apps card in Settings > Connect
  MCP (`components/studio/settings/connections.tsx`), helpers at the bottom of
  `lib/studio-api.ts`.
- Panel: [`zeropage-onryo/phantra-premiere-plugin`](https://github.com/zeropage-onryo/phantra-premiere-plugin)
  (private since 2026-10-23, proprietary license; CI runs `npm test`; cloned at `../phantra-premiere-plugin`): `src/phantra.js` (tested under Node),
  `src/premiere.js`, `main.js`; `docs/premiere-apis.md` lists the Adobe calls and their sources.
- Walked end to end on a local API + `next start`: pair, type the code, Connect, poll, `me`,
  `generate_image` (refused for 0 credits, nothing spent).

**An independent security review (same day) changed five things:**

1. **The code is never in the link.** `link_url` is the bare page and the page ignores `?code=`:
   a pre-filled link was a one-click phishing kit (start a pairing, send the link, the victim
   presses Connect and the sender holds a token to their studio). The page says the panel's
   device line is the panel's own claim, and warns against codes someone else sent.
2. **Brakes key on `Fly-Client-IP`.** uvicorn runs `--forwarded-allow-ips='*'`, so
   `request.client.host` is whatever a caller puts first in X-Forwarded-For. The panel's doors
   use their own limiter on Fly's header (`_client_ip`). **`auth._rate_limited` (sign-in, code,
   password brakes) has the same weakness and was NOT changed here: Mike's call.**
3. **A token is never more than its membership**, and dies after 90 idle days (`IDLE_DAYS`).
4. **No spending tool is reachable when `QUOTE_SIGNING_SECRET` is unset** (503
   `cannot_approve`): without it `approve` takes no token at all.
5. Pairings are swept a day after they expire; every bearer route is rate limited; the link
   page names the TENANT workspace (the one the approval binds), not the one open; a crash no
   longer claims "nothing was charged".

**Send selected clip (same day, Mike's yes after comparing Runway's and Higgsfield's panels,
which both lead with editing footage already on the timeline):**

- `POST /plugin/v1/upload`: the raw bytes of a timeline clip or a playhead frame, through the
  connector upload page's own body (`upload_page.sniff` / `_save`): typed by its bytes, capped
  at 500 MB while it is read, filed as `asset:<id>`, free.
- `edit_clip` (prompt edit, frame first then the clip) is the one tool taken from the STUDIO
  surface (`STUDIO_SURFACE_TOOLS`), through a studio-surface server built in `plugin_api`; the
  listings are unchanged. Its answers are a line for the model then JSON, which `_result_of`
  reads.
- The panel trims to the timeline's range with `trim_clip` (free) after the upload, so the
  source goes up once. `localFileSystem` is `fullAccess` so the selected clip's file can be
  read; the panel caps it at 450 MB.

**Left for later:** an email to the person when a panel connects; an owner seeing other
members' panels; the limiter's in-process key growth (the same shape as `auth._hits`).
