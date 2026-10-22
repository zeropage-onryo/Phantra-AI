# The submission pack

> **2026-10-15 (directory-review fixes; read this first):** `PORTAL_PASTE.md` holds the
> current text of every portal field and wins over the drafts below. What changed: the Claude
> listing is no longer described as an "AI image and video generator" -- it plans, writes,
> organises, prices and edits scenes from the person's own photos and clips, and renders are
> approved and made in the Phantra studio, never in the chat (Anthropic's Software Directory
> Policy 4B refuses software that uses AI models to generate images, video or audio). Its
> documentation URL is `https://phantra.ai/mcp/claude`, which documents only that address.
> Tool counts: 37 on `/mcp` (the effects change is on main), 32 on `/mcp/claude`. Packages:
> the Claude plugin 0.6.0 and the ChatGPT plugin 1.3.0. Test account: `review@phantra.ai`.
>
> **2026-10-11:** there are now TWO listed servers and no board on either -- read
> `TWO_LISTINGS.md` first; where it and this file disagree, it wins.
>
> **2026-10-12 (the overnight build, `docs/tasks/task-connector-overnight.md`):** the
> tool set grew again -- 35 tools on `/mcp` then (37 since the effects change of 2026-10-13,
> now on main), 32 on `/mcp/claude` (`TWO_LISTINGS.md`'s "The overnight build" table). None of the new ones generates media or spends credits.
> The portal fields, the reviewer steps and the data table below are rewritten for that
> set; the status tables are still the 2026-10-07/08 record.

Phase 6 of `docs/tasks/task-directory-listing.md`, 2026-10-07. Item numbers
are `REQUIREMENTS.md`'s; grades are `AUDIT.md`'s, updated for what Phase 4
landed on this branch (not yet deployed — a push to `main` deploys Fly).

> **THE TOOL SET CHANGED ON 2026-10-11** (`docs/tasks/task-higgsfield-shape.md`,
> step 3: no idea board). The listed server no longer has `board`, `idea`,
> `search`, `capture`, `pick`, `shoot`, `archive` or `stats`. It has ten
> tools: `projects`, `project`, `project_chat`, `create_project`,
> `save_chat`, `elements`, `write_scene`, `quote`, `approve`, `job`.
> `write_scene` makes the scene itself (in a project or on its own) and
> returns a `scene_id`; `quote` and `approve` take that `scene_id`, and
> nothing is picked first. The portal fields, the reviewer steps and the
> data table below are rewritten for that. The status tables above them are
> the 2026-10-07/08 record and still name the old tools where they report
> what was tested then. **Three things follow that are not done:** the live
> walk was made on the old tool set and has to be made again before
> submitting; the test account's four ideas were set up for
> `pick` → `quote` → `approve` and need one scene written with the new
> `write_scene`; and if the listing has already been submitted, the
> reviewers need to be told the tools changed.

## Status report

### Connector items

| # | item | status | note |
|---|---|---|---|
| C1 | read/write split | PASS | |
| C2 | custom query tools name the API | PASS (n/a) | |
| C3 | title + hints on every tool | **PASS after Phase 4** (was FAIL) | `TITLES` / `HINTS` constants, pinned by test |
| C4 | names ≤ 64 | PASS | |
| C5 | narrow, accurate descriptions | **PASS after Phase 4** (was FAIL) | `DESCRIPTIONS`, operator vocabulary screened |
| C6 | no prompt-injection patterns | PASS after Phase 4 | workflow steering moved into the plugin's skills |
| C7 | valid input → success, no generic errors | PASS | a database outage still surfaces as the SDK's generic text; that is a server fault |
| C8 | validate inputs, actionable errors | PASS after Phase 4 | `images` on an unknown id now errors; caps named |
| C9 | response size | PASS after Phase 4 | 7.6 KB default board; `truncated` + note at the cap |
| C10 | no conversation-data collection | PASS | |
| C11 | first-party API | PASS | declare the image-search lanes as proxied APIs |
| C12 | no AI image/video/audio generation | **PASS on the Claude listing (2026-10-11)** -- `/mcp/claude` carries no `approve`; see TWO_LISTINGS.md. Historical note: | Built as Mike chose: `approve` renders stills and clips after a quote and a yes in chat. The checklist says such connectors "aren't accepted"; the Compliance step asks for the acknowledgment. Answer it truthfully; if refused, drop `approve` from LISTED_TOOLS (one line) and the Queue is the approve |
| C13–C19 | OAuth, 401, metadata, AS metadata, DCR, PKCE, scopes | PASS | verified live from here 2026-10-07 |
| C20 | callback URLs (incl. Claude Code loopback) | **PASS live 2026-10-08** | a Claude Code-shaped client registered `http://localhost:<port>/callback` through DCR (201) and completed the code flow (OAUTH_TEST.md, live results) |
| C21 | consent screen | **PASS live 2026-10-08** | shown and approved live; the Site URL is `https://api.phantra.ai` since the same day, so the consent page no longer meets Chrome's lookalike warning (OAUTH_TEST.md Finding 4) |
| C22–C24 | token endpoint, latency, no tokens in URLs | PASS | |
| C25 | remote HTTPS | PASS | |
| C26 | tested in Claude + Inspector | **PASS 2026-10-12** | claude.ai on Mike's own workspace (the 2026-10-12 live check, 32 tools); the reviewer list as the test account through `ops/connector_walk.py` on both doors (`walk-2026-10-13-claude.md`, `walk-2026-10-13-render.md`); the MCP Inspector's CLI (`--cli … --method tools/list`) read 32 tools on `/mcp/claude` and 35 on `/mcp` that day (37 on `/mcp` since the effects change; re-capture `inspector-render.json` before submitting), saved as `screens/inspector-claude.json` / `inspector-render.json` |
| C27 | listing materials | PARTIAL | privacy/terms live; docs URL and icon: see "By hand" |
| C28 | test account | **READY once the login exists** | the reviewer signs in as `review@phantra.ai` (created 2026-10-15) on account 5 (slug `zp-billing-test`, display name Phantra Review), populated 2026-10-08 and 2026-10-12 (below); the password goes in the portal field only |
| C29 | public documentation | PASS (2026-10-15) | `https://phantra.ai/mcp/claude` (the Claude connector's own page, this address only) and the plugin README; `/mcp` documents the render address for ChatGPT |
| C39 | no clientInfo gating | PASS | |
| — | rate limit | **PASS live 2026-10-08** | 120/min per account, 1200/min operator key; 429 + Retry-After; a deploy mid-window resets the in-process count |
| — | token: audience, expiry, issuer | PASS after Phase 2 | issuer check added |
| — | cross-tenant isolation (board, idea, search, capture, pick, archive, shoot, job, stats, projects, project, project_chat, create_project, save_chat) | **PASS live 2026-10-08** for the first nine with a second account; all of them through the real transport in tests | the project tools arrived after the walk; `stats` no longer reports the shared bank's size to a signed-in caller (Finding 6) |
| — | cross-tenant: sparks / images bank | **PASS** -- not on the listed server | Mike's call 2026-10-07; the operator's door keeps them |
| — | spend without a quote + approval | **PASS on the listed server** (a scene's keyframes included only since 2026-10-11: until then `approve` drew them without the quote's token) | `quote` then `approve` (tokens for the keyframes and for each clip render, hold before submit); `imagine_reference` is not on the listed server |

### Plugin items

| # | item | status |
|---|---|---|
| P1–P2 | layout and manifest | PASS — `.claude-plugin/plugin.json`, `.mcp.json`, `README.md`, `LICENSE`, 22 `skills/*/SKILL.md` (0.6.0) |
| P3–P5 | name, writing system, version | PASS — `phantra-ai`, 0.6.0 (2026-10-15; was `zeropage-studio` 0.1.0 at this audit) |
| P6 | README ≥ 40 words | PASS (661 words outside code) |
| P7 | license | PASS — MIT (Mike's pick), file and field |
| P8–P12 | system files, names, size, text only, no symlinks | PASS — `.gitignore` carries the four and `.claude/`; all text |
| P13–P16 | `.mcp.json`, same URL, no secrets, no launchers | PASS |
| P17–P21 | skills | PASS — each under 100 lines, frontmatter `name` + `description` with a "NOT for" line |
| P22 | `claude plugin validate` | PASS — `✔ Validation passed`, 2026-10-07, Claude Code 2.1.285 |
| P23 | loaded on each surface | UNKNOWN — Mike: `claude --plugin-dir ./phantra-claude-plugin`, then the zip upload on claude.ai |
| P24 | GitHub repo, public before going live | PASS — https://github.com/zeropage-onryo/phantra-claude-plugin, public |
| P25–P28 | portal steps | drafted below |

### What changed in Phase 4 (on this branch, not deployed)

- Every tool has a title, `readOnlyHint`, `destructiveHint`, `idempotentHint`,
  `openWorldHint`, true to what it does.
- Descriptions rewritten for a stranger, as constants, with a vocabulary
  screen in the tests. The server's `instructions` too.
- `status`, `brand`, `lanes` published as enums; `brand` defaults so a
  stranger never has to type it.
- `board` / `search` name their cap and answer `truncated` with a note.
- `images` on an unknown direction errors instead of answering an empty list.
- `capture`'s hint no longer prints a shell command.
- `capture` / `pick` / `shoot` / `archive` honour the explicit account the
  Guide builds its server for (F-9).

### What changed on 2026-10-12 (merged and live; the submission run, `docs/tasks/task-connector-submission.md`)

- **#283** (`claude/mcp-bare-path`, Fly v292): the bare `/mcp` address, with no trailing
  slash, is served and answers 401 with its OAuth challenge instead of `307 → /mcp/`, which
  claude.ai's "Add custom connector" check read as "Not found". Checked live the same
  morning: `POST https://api.phantra.ai/mcp` → 401; both metadata documents
  (`/.well-known/oauth-protected-resource/mcp` and `/mcp/claude`) name the Supabase
  authorization server.
- **#284** (`claude/upload-page-still-length`, Fly v293): the one-time upload page shows a
  picture's Size and never a Length (it printed "Length 600.0s", the editor's still
  placeholder, on 2026-10-12).
- **#281** (this pack and the As built report) and **#282** (the `/connector` page's Limits
  sentence: a picture also reaches the connector through the one-time upload page), Fly
  v294; the sentence is live on `phantra.ai/connector`.
- **The plugin's v0.3.0** (`zeropage-onryo/phantra-claude-plugin` pull 4, b1c6b93):
  seventeen new skills naming the overnight tools, merged once the connector was live.
- **The icon** was drawn then under the old name; it was removed on 2026-10-13 with the rename, and a Phantra icon is still to be supplied.
- **`ops/connector_walk.py`** (#285): the connector's own OAuth client and reviewer walker,
  which is how the reviewer steps are walked as the test account without a person at the
  keyboard after the one sign-in. **`PORTAL_PASTE.md`** holds every portal field in paste
  order.

### What needs Mike's decision (answered 2026-10-07 unless marked open)

- Render path: **B, built** — `elements` / `write_scene` / `quote` / `approve`
  on the listed server; Claude writes the scene in chat (no model credit),
  the studio renders after a quote and a yes. The listed set is
  `mcp_server.LISTED_TOOLS`; the spark bank and the engine tools stay on the
  operator's door (Mike's call).
- First contact: **require one web sign-in**; the 403 body and the connector
  description should say so (one string in `app/mcp_mount.py`, not yet changed).
- License: **MIT**. Support: **GitHub issues on the plugin repo**.
- Sparks bank: **off the listed server** (decided). `reference`'s URL
  argument (AUDIT.md F-6) and the Create cap now concern the operator's door
  only; neither is reachable by a stranger.

### Live checks only Mike can do

- `fly releases --app phantra-api`: which commit is live; whether
  `PHANTRA_MCP_ENGINE` is set there (inferred from the tool list).
- ~~The second-account script, `OAUTH_TEST.md`, steps 0–11.~~ **Walked
  2026-10-08** (step 10 skipped); results and Findings 4–7 in `OAUTH_TEST.md`.
- Reachability of `ewkbrenbjsiggufegrnd.supabase.co` from Anthropic's egress
  range (no WAF is in front of it, so expected PASS).

## The portal fields (MCP connector)

**Connection** — `https://api.phantra.ai/mcp/claude` for the Claude listing (the `/mcp` door is the
render listing), Universal URL. `PORTAL_PASTE.md` has every field in paste order.

**Tools** — sync from the server; a signed-in reviewer sees the listed set,
every tool with a title and hints. On `/mcp/claude` (32 tools, 2026-10-12):
read-only — projects, project, project_chat, elements, video_models, scene,
quote, job, library, share_link, balance, search, whoami, recent,
credit_history, recommend_model, preferences, recipes, recipe, what_works,
score_caption. Write, none destructive — create_project, add_element,
upload_link, write_scene (destructive: a `scene_id` replaces that scene's
text), duplicate_scene, reformat, trim_clip, assemble_clips, feedback,
set_preferences, save_recipe. `/mcp` adds image_models, generate_image,
approve, effects and apply_effect (37 tools; generate_image, approve and
apply_effect spend after a quote).

**Listing**

- Name (≤100): `Phantra AI`
- One-liner (≤200): `Plan, write, organise, price and edit short video scenes from your own photos and clips in a conversation. Renders are approved and made in the Phantra studio, never in the chat.`
- Description (≤2,000): `PORTAL_PASTE.md` section 1, "Description, paste as one block"
  (rewritten 2026-10-15: it leads with planning and says renders are approved and made in the
  Phantra studio, never in the chat).

- Categories (1–5): Creative & Design; Productivity; Marketing (pick what the
  portal offers closest to video / creative).
- Documentation URL: `https://phantra.ai/mcp/claude` (2026-10-15: the Claude
  connector's own page, documenting only `/mcp/claude` and its 32 tools), with
  the plugin README (`https://github.com/zeropage-onryo/phantra-claude-plugin#readme`).
- Privacy policy URL: `https://phantra.ai/privacy` (200 on 2026-10-07).
- Terms: `https://phantra.ai/terms` (200).
- Support contact: `support@phantra.ai` (https://phantra.ai/support); plugin bugs also on its GitHub issues.
- Icon: **to be supplied** (a Phantra icon; the old one was removed 2026-10-13). Upload
  whichever size the portal asks for.
- Slug: `phantra-ai` (permanent once published).

**Use cases** — as `PORTAL_PASTE.md` section 1 (2026-10-15): "Plan a short ad
or video as timed scenes in a project, held to my own product or character
photos"; "Reopen a project with its brief, references and chat and carry on";
"Price a scene in credits and get the link to approve its render in the
Phantra studio". Users need: a Phantra account (free sign-in with trial
credits; renders are approved and paid for in credits in the studio). Reads
and writes data: both.

**Company** — Phantra, `https://phantra.ai`, primary contact:
Mike's email for review updates (not shown publicly).

**Authentication** — OAuth with dynamic client registration (Supabase OAuth
2.1 server, PKCE S256). No lazy auth: every tool needs the account.

**Data handling** — as `PORTAL_PASTE.md` section 1: the API is our own; the
connector's one outbound fetch is the picture or product page a person names in
`add_element`, and `share_link` signs a download address off the studio's own
bucket. (`images_for` and the image-search lanes are the studio surface's, on
neither listed server.) No personal health data. No sponsored content.

**Test & launch** — reviewer instructions:

1. Account: account 5 (slug `zp-billing-test`, shown as Phantra Review) — a
   real workspace, kept for billing checks. The reviewer signs in as
   `review@phantra.ai` (created 2026-10-15, a member of account 5); its
   password goes in the portal's test-credentials field only. **Populated 2026-10-08** through the product's own code, nothing
   rendered: four product elements with one photo each, all invented brands
   off the /make wall (Solene perfume, Tonal One headphones, Fuego Dulce hot
   sauce, Kumo matcha; described, no sheets); four ideas filed under the
   project "Spring product spots" -- #398 and #401 open, #399 picked (idea
   only), #400 with a written two-shot scene (8s) on the headphones and the
   matcha; 501 credits (lot 11, expires 2026-12-08), which covers the
   keyframes and one small clip. The two old billing-test copies (#385,
   #386) are archived. **Since 2026-10-11** `quote` and `approve` take
   #400's id directly as `scene_id` (nothing is picked first), and a
   reviewer can make their own with `write_scene`. The reviewer's password is
   typed into the portal field only. **What the
   2026-10-12 reviewer walk added** (`walk-2026-10-13-claude.md`,
   `walk-2026-10-13-render.md`): the prop "Reviewer check" with the studio icon
   as its photo (uploaded through a one-time page, asset:3); scene #408
   "Reviewer check: Tonal One push-in" (two shots, 8 s, the headphones and the
   hot sauce as its light reference, project "Spring product spots"), with its
   two keyframes drawn; #409 (a copy of #400) and #410 (a copy with no photos, a
   draft); #411 (a one-window copy of #408) rendered on LTX 2.3 -- gen:107 -- and
   its free edits gen:108 (1:1), gen:109 (the first second), gen:110 (the two
   joined); the still gen:104 (FLUX 1.1 Pro); the recipe `reviewer-check` v1-v2;
   one feedback row; preferences left at `seconds=8 / ltx2.3 / draft_first=false`.
   Balance 384 (117 spent on 2026-10-12).
2. Steps (2026-10-12, on `/mcp/claude`): sign in once at
   https://phantra.ai with those credentials (workspace exists already);
   add the connector; approve the consent page; then in a chat call
   `projects` → `project` (the project above) → `elements` → `upload_link`
   (open the page it returns, pick a photo, see it land as an `asset:<id>`
   and on the named element) → `write_scene` (a prompt of timed shots,
   `refs` from `elements`, `roles` for one of them, `project_id` from
   `projects`) → `scene` → `quote` (the `scene_id`; the answer carries
   `approve_url`, the scene's page in the studio) → `library` → `reformat`
   (a render to 1:1) → `job` (with `wait=15`, until done) → `share_link`.
   Then the reads: `balance`, `credit_history`, `whoami`, `recent`,
   `search`, `video_models`, `recommend_model`, `what_works`,
   `score_caption`, `preferences`; and the writes: `set_preferences`,
   `duplicate_scene`, `save_recipe` / `recipes` / `recipe`, `feedback`.
   On `/mcp` the same plus `image_models` / `generate_image` (a still, after
   a quote and a yes), `approve` (keyframes, then clip, with a balance that
   covers one small render) and `effects` / `apply_effect` (an effect on a
   library item, after a quote and a yes).
3. What it must NOT be able to do: read any other account's work (a
   project, scene, render or upload id that is not its own answers "no
   project N" / "no scene N" / "no render N" / "no upload N"); buy credits or
   change a plan (not possible through the connector); post anywhere; delete
   or overwrite anything (every edit is a new item; rewriting a scene replaces
   its text and the skill asks first); render or draw from `/mcp/claude`.
4. The open question the reviewer may hit: a brand-new sign-up through the
   connector gets "no account" until they sign in once on the web (Mike's
   decision; the description says so).
5. Confirm "tested every tool in Claude and Inspector" only after
   `OAUTH_TEST.md` is walked.

**Compliance** — seven acknowledgments. The "AI media generation" one is the
open risk (C12); answer truthfully.

### Screenshots (for the review note and the README; none required for a
non-App connector)

Under `docs/directory/screens/` since 2026-10-12:

- `tool-list.png` — the Claude listing's 32 tools with titles, hints and a line of
  each description, rendered from `inspector-claude.json` (the MCP Inspector's own
  listing). The claude.ai Tool-permissions page of Mike's connector was not
  screenshotted by the run; take it from his connector's page if a browser shot is
  wanted.
- `cross-tenant-refused.png` — `scene 375` (another workspace's) as the test
  account → "no scene 375" (walk-2026-10-13-claude.md, step 37).
- `inspector-claude.json`, `inspector-render.json` — the two listings as read.
- The 429 numbers are `OAUTH_TEST.md`'s of 2026-10-08 (120 × 200 then 429 with
  `Retry-After: 18`); no `rate-limit-429.png` was taken.
- **Mike's:** `consent-page.png` (the consent page naming the client and the
  redirect host, during his sign-in of 2026-10-12 as the test account).
- Historical, never taken: `empty-board.png`, `shared-sparks.png` (the board is
  gone).

### What each tool does with user data

| tool | reads | stores | sends to a model | sends to a provider |
|---|---|---|---|---|
| elements, quote, job | the caller's rows | — | — | — |
| projects, project, project_chat | the caller's projects: brief, look, scenes, the reference images they used, renders, chat history | — | — | — |
| write_scene | — | a scene under the caller's account (the scene prompt and the photo refs chosen), in the project named or on its own | — | — |
| create_project, save_chat | — | a project, or chat turns Claude passes (the conversation's text), under the caller's account; kept until the person deletes the project in the studio | — | — |
| approve (keyframes) | — | the stills under the caller's renders; a ledger charge | the scene prompt and the attached photos, to the studio's image model | Google's image model (Nano Banana) |
| approve (clip) | — | the clip under the caller's renders; a ledger charge | the shot prompt, its still and the attached photos, to the renderer | fal.ai (the model quoted) |
| upload_link (2026-10-12) | — | a signed, single-use claim (`upload_claims`: the account, the person, the purpose, what the upload made); the file the person then uploads, as an `asset:<id>` under the caller's account (and on an element when asked) | — | — |
| add_element from a product page (2026-10-12) | one fetch of the page the person gave, https only, and its main picture | the picture as the element's photo; the page's stated facts in the element's notes as quoted text | the photo, to the studio's vision description (the Elements page's own step) | Google's vision model (the description) |
| library, share_link, video_models, recommend_model, balance, credit_history, whoami, recent, search, preferences, recipes, recipe, what_works, score_caption | the caller's rows (renders, uploads, scenes, projects, elements, credit ledger, outcomes, posted videos) | — (a `share_link` to a render is recorded as a download) | — | — (`share_link` signs a time-limited download address off the storage bucket) |
| reformat, trim_clip, assemble_clips | the caller's own renders and uploads | a new item under the caller's renders and an editable cut in the studio's editor; nothing charged | — | — (ffmpeg on the studio's own server) |
| duplicate_scene | one of the caller's scenes | a new scene under the caller's account (words, photos, roles, project; never a render) | — | — |
| feedback | — | the note, the person and the tool it is about (`mcp_feedback`), read by a person at the studio | — | — |
| set_preferences | — | a new row of the workspace's defaults (`mcp_preferences`; the newest wins, nothing overwritten) | — | — |
| save_recipe | — | a new version of the recipe's text under the caller's account (`mcp_recipes`), returned to a chat as the person's own text | — | — |

Not on the listed server: the studio surface's tools (`generate_image`, `generate_video`, `apply_effect`, `element_sheet`, `edit_clip`, `assemble_clips`, `images_for`, the model lists), which are the operator's door and the desktop app's. The idea-board, spark-bank and engine tools (`board` … `stats`, `sparks`, `tonight`, `add_spark`, `images`, `reference`, `imagine_reference`, `research`, `generate`) were removed from every door on 2026-10-11.

## The portal fields (plugin bundle)

- Repository: `zeropage-onryo/phantra-claude-plugin` (public). Plugin path:
  root. Branch: `main`, once 0.6.0 (`claude/directory-review-fixes`) is merged.
- Validate → listing details come from `plugin.json` and the README.
- Data handling: reads personal data — only the account's own projects, scenes and chat text;
  sends data to services other than the declared connector — no; retention —
  the studio's (privacy policy); for people under 18 — no.
- Compliance: contact email; four acknowledgments.
- Review and submit: GitHub push webhook (needs repo admin).

## Everything Mike must do by hand, in order

1. **Merge the PR** once CI is green (built 2026-10-07: the consent page is
   in it). A push to `main` deploys Fly.
2. **Push this branch and open the PR** (nothing is pushed). Merging to
   `main` deploys Fly with Phase 4 and the rate limit.
3. **Supabase dashboard** (Authentication → OAuth Server): set the
   Authorization Path to `/oauth/consent` (done 2026-10-07). The Site URL is
   the API origin, `https://api.phantra.ai` (moved from
   `zeropage-studio.fly.dev` on 2026-10-08, which Chrome flagged as a
   lookalike on the consent page; `OAUTH_TEST.md` Finding 4).
4. **Fly**: `fly releases` to confirm the live commit. `QUOTE_SIGNING_SECRET`
   is already set there, so `quote` will carry tokens. Optionally set
   `PHANTRA_MCP_RATE` / `PHANTRA_MCP_RATE_OPERATOR` (defaults 120 / 1200
   per minute) and `PHANTRA_SIGNUP_URL` (default https://phantra.ai).
5. ~~**Walk `OAUTH_TEST.md`**~~ walked 2026-10-08 with a fresh sign-up
   (account 5 cannot sign in); the claude.ai screenshots are still to take.
6. ~~**Populate the test account**~~ done 2026-10-08 (reviewer item 1); set
   its password, then put its credentials in the portal only.
7. ~~Create the GitHub repo~~ **Done 2026-10-07:**
   https://github.com/zeropage-onryo/phantra-claude-plugin, public, `main`,
   Issues on (the support contact), MIT detected by GitHub. Commits are
   authored as Phantra <reply@phantra.ai>.
8. **Icon**: a square PNG. The 2026-10-11 icon carried the old name and was removed on
   2026-10-13; a Phantra icon is still to be supplied.
9. **Portal, connector**: claude.ai/directory/manage → Submit new → MCP
   connector → fill the fields above → Test & launch → Compliance → submit.
10. **Portal, plugin**: Submit new → Plugin bundle → repository → Validate →
    Data handling → Compliance → submit; set up the push webhook.
11. **Pair** the two listings once both exist.
12. After publishing: watch the connector dashboard; `directory@anthropic.com`
    / `mcp-review@anthropic.com` for a stuck submission.

### Added by the overnight build (2026-10-12), in order

13. ~~**Merge PRs #276–#280 one at a time**, in order (each is stacked on the
    previous), after reading each PR's "Live check after deploy". A push to
    `main` deploys Fly.~~ **Done 2026-10-12** (merged 03:11–03:13 UTC, Fly v291);
    #283, #284, #281 and #282 followed the same morning (Fly v292–v294), see "What
    changed on 2026-10-12" above.
14. ~~**Set the test account's password** (`zp-billing-test`, member
    `deals4michael@gmail.com`): sign in as it and set one in
    /studio/settings.~~ **Done 2026-10-12** by Mike. The email alone is in
    `PORTAL_PASTE.md`; the password goes into the portal's test-credentials field
    only, and nowhere in this repository.
15. ~~**Walk reviewer step 2 above as the test account on `/mcp/claude`**
    (the `upload_link` page on a phone, `library`, `reformat`, `job`), and
    once on `/mcp` for the still and the approve.~~ **Done 2026-10-12** through
    `ops/connector_walk.py` after Mike's one sign-in: `walk-2026-10-13-claude.md`
    (72 expectations, every one PASS once a clip existed; two addenda say what
    the first pass could not reach and why) and `walk-2026-10-13-render.md`
    (117 credits: the still, two keyframes, one LTX 2.3 shot; the 174-credit
    two-shot clip skipped as over the cap).
16. ~~**Merge the plugin's v0.3.0 PR** (`zeropage-onryo/phantra-claude-plugin` pull 4,
    https://github.com/zeropage-onryo/phantra-claude-plugin/pull/4)
    after the connector is live: its skills name the new tools.~~ **Done 2026-10-12**
    (b1c6b93, merged after Fly v294 was live; `plugin.json` on `main` reads 0.3.0).
17. **Optional Fly env**: `PHANTRA_UPLOAD_ORIGIN` only if the upload page
    should live somewhere other than the API origin (it defaults to the
    origin of `PHANTRA_MCP_RESOURCE`).
18. ~~**One sentence on `/connector`** (web/): its Limits list says a picture
    reaches the connector as a web address or one of the person's renders;
    it also reaches it through the one-time upload page now.~~ **Done 2026-10-12**
    (#282, d70b22a; Vercel built it, and `phantra.ai/connector` carries the
    sentence).
19. Submit the connector (both portals), then the plugin, then pair.
