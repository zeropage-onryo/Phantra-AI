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

## After Effects (2026-11-03)

**From:** a side session of "Blender plugin + editor plugin check", on Mike's comparison with
Higgsfield's set: one installer that covers Premiere Pro and After Effects, one panel under
Window > Extensions in each. Built in the panel's own repo (PR
[zeropage-onryo/phantra-premiere-plugin#3](https://github.com/zeropage-onryo/phantra-premiere-plugin/pull/3),
0.3.0); nothing in this repo changes but this file (the MCP freeze is in force).

**The decision, from the code:** the Premiere panel is a UXP plugin (`manifest.json`, the UXP
Developer Tool), and After Effects has no UXP panels. Adobe's plan (blog.developer.adobe.com,
September 2026, "UXP comes to our flagship applications") gives After Effects a UXP public beta
"by November 2026" and no GA date, and keeps CEP in Premiere Pro, After Effects and the rest
until the end of 2029 (Premiere stops taking new CEP Marketplace submissions in December 2027,
After Effects in December 2028; CEP plugins distributed outside the Marketplace are not
affected). Higgsfield's "one installer for both" is a CEP extension (a .dmg on the Mac, a .zxp
through aescripts' ZXP Installer on Windows; Window > Extensions > Higgsfield). So the
both-hosts panel is CEP: one `CSXS/manifest.xml` naming `PPRO` and `AEFT` from 25.0 (the
first release of each on CEP 12, Node 17.7.1), the same `index.html` / `main.js` /
`src/phantra.js`, and a host bridge. The UXP plugin stays for Premiere, where UXP is the
future; the CEP extension is what the installer ships. The "Not in v1" line above ("port once
UXP lands there") is therefore answered the other way round: AE joined on CEP, and the UXP
port is for when AE's UXP ships.

### As built

- `src/host.js` picks the host: `require("premierepro")` resolves -> UXP -> `src/premiere.js`;
  `window.__adobe_cep__` -> CEP -> `src/cep.js`. Both expose the same calls to `main.js`
  (`available`, `deviceName`, `openUrl`, `bringIn`, `selectedClip`, `readMedia`,
  `frameAtPlayhead`), plus `words` (the host's names: "Insert" / "Add to comp", the playhead /
  the comp's current time, put on the panel at start) and `clientApps`.
- `src/cep.js` loads the app's ExtendScript once (`$.evalFile` of `jsx/premiere.jsx` or
  `jsx/aftereffects.jsx` from the extension folder) and calls `PhantraHost.run(name, args)`
  through `__adobe_cep__.evalScript`; every answer is one JSON string, `{"error"}` becomes a
  thrown Error, CEP's `EvalScript error.` marker too. Files and the network go through Node
  (`--enable-nodejs`, `--mixed-context`): `src/node-fetch.js` is `fetch()` over `http`/`https`
  (CEP 11+ enforces CORS for a page from `file://`), handed to `createClient` as `fetchImpl`, so
  **`src/phantra.js` and the sign-in are byte-for-byte the Premiere panel's**. Downloads and
  the token live under `~/Library/Application Support/Phantra/adobe` (Windows `%APPDATA%`), the
  token file mode 0600 (CEP has no `secureStorage`; the UXP path keeps the keychain).
- After Effects (`jsx/aftereffects.jsx`, ES3): `app.project.importFile(new ImportOptions(file))`
  with `sequence = false`, reused when the project already holds the file; a "Phantra" folder
  (`items.addFolder`, found again by name; `item.parentFolder = folder`); placing is
  `comp.layers.add(item)` then `layer.startTime = comp.time` on `app.project.activeItem` when it
  is a `CompItem`, in an undo group; no comp open -> imported, `placed: false`, the panel says
  "Imported. Open a composition to add it as a layer." **Selected layer:** the first selected
  `AVLayer` whose source is file footage; its `file.fsName` and the source range the layer shows,
  `(inPoint - startTime) / (|stretch| / 100)` to the same for `outPoint`, mirrored for a reversed
  layer; `trim_clip` (free) takes that range after the upload, as for Premiere. **Frame at
  current time:** `comp.saveFrameToPng(comp.time, file)`, checked for with `typeof` first (it
  is not in Adobe's guide but has worked since CC 2014).
- Premiere under CEP (`jsx/premiere.jsx`): `importFiles([path], true, bin, false)`, the bin by
  `rootItem.createBin`, `videoTracks[0].insertClip(item, playerPosition.seconds)`,
  `getSelection()` for the clip, `exportFramePNG(time, path)` for the frame.
- Sign-in in After Effects asks `/plugin/v1/pair` for client `aftereffects` and, on
  `bad_client`, retries once as `premiere` (in `main.js`, not in the client). **API gap, not
  built because of the freeze:** `plugin_tokens.CLIENTS` has no `"aftereffects": "After
  Effects"`; until it does, an AE panel pairs as "Premiere Pro" with the device line "macOS,
  After Effects 25.x" telling the person which app it is, and the link page's sentence and the
  Apps card say Premiere Pro. One line in `CLIENTS`, a test beside the Blender one, and the
  sentence on `/studio/link`, once the freeze lifts (the same shape as the Blender gap).
- Installer: `scripts/build-zxp.sh` stages `dist/com.phantra.adobe/` from `install.command`'s
  file list and signs it with Adobe's ZXPSignCmd when it is on the PATH (a self-signed
  certificate, `PHANTRA_ZXP_PASSWORD`), else an unsigned zip, said loudly;
  `scripts/build-pkg.sh` builds the Mac `.pkg` (the Resolve plugin's shape) into
  `/Library/Application Support/Adobe/CEP/extensions/com.phantra.adobe`, the system folder both
  apps read, refused up front on a Mac with neither app; `install.command` copies into the
  per-user CEP folder for development and asks before turning on `PlayerDebugMode`.
  Windows is the `.zxp` through aescripts' ZXP Installer. Proprietary license kept; downloads
  from phantra.ai, never GitHub (`dist/` is ignored).
- Tests: 50 (were 9). `test/aftereffects.test.js` and `test/premiere-jsx.test.js` run the
  ExtendScript under Node's `vm` against fake apps (import once + folder + layer at comp time,
  no comp, stretch and reverse, the frame, every refusal as `{error}`); `test/cep.test.js` the
  bridge with a fake `__adobe_cep__` (host detection, one jsx load, download then import,
  the 450 MB cap, the frame read back, the 0600 token); `test/node-fetch.test.js` the Node
  fetch against a local server with the unchanged client; `test/manifest.test.js` the two
  manifests, `.debug`, the install list and an ES3 screen on the jsx. `test/preview.html`
  gained `&host=aeft`: a fake CEP host, so the real `main.js -> host.js -> cep.js ->
  node-fetch.js` path was driven in a browser (sign-in state, Library with "Add to comp",
  download -> importFile -> placed, Selected layer -> upload -> trim, Frame at current time).

### Not verified

- **Neither Premiere Pro nor After Effects is installed on this Mac** (Creative Cloud holds
  Photoshop and Lightroom), so the panel has not been opened in either host; the first open is
  the real check, with `http://localhost:8089` (`.debug`) for AE's console. In particular:
  whether CEP 12 in 25.x/26.x accepts `ExtensionManifest Version="7.0"` with
  `RequiredRuntime 9.0` (a community report says `12.0` is refused; Adobe's own sample is
  5.0/6.0); CEP's global `require` and the `index.html` bootstrap that resolves `./` against
  the extension folder; `saveFrameToPng` in the installed AE (reported quirks: black edges with
  alpha, a Save dialog in some versions; the render-queue fallback is not built); the new
  layer's time under the "Create Layers at Composition Start Time" preference.
- The `.zxp` is unsigned here (no ZXPSignCmd); the `.pkg` was built and expanded (payload and
  install location right), but the pkg script warns that this shell stamps every file with
  `com.apple.provenance`, which pkgbuild turns into `._` entries: build the release from a plain
  Terminal (the script checks its own payload and says so).
- No sign-in was made and nothing was spent: the live API was not touched.
