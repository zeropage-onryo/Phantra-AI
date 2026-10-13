# Two listings: Claude and ChatGPT (2026-10-11)

Mike's call: list the connector in both directories at once, and get rid
of the idea board on both. This replaces the single "listed server" of
2026-10-07 with two, served from the same mount.

## Why two

The directories disagree on one rule:

- **Anthropic** (connector pre-submission checklist, "Unsupported use
  cases"): connectors that "generate images, video, or audio through AI
  models" are not accepted. `approve` renders through fal, so it cannot be
  on the Claude listing. (`REQUIREMENTS.md` C12, `RENDER_DESIGN.md`.)
- **OpenAI** (plugin guidelines, checked 2026-10-11): no such ban. Its
  rules that matter here are commerce, where only physical goods may be
  sold and no credits, subscriptions or upsells may be shown, while
  "users may sign in to an existing paid account and access features
  already included"; a ban on tools that ask for the conversation; and
  explicit `readOnlyHint` / `destructiveHint` / `openWorldHint` on
  every tool.

## The two servers

| | Render listing (ChatGPT, and anyone adding it by hand) | Claude listing |
|---|---|---|
| URL | `https://api.phantra.ai/mcp` | `https://api.phantra.ai/mcp/claude` |
| built by | `build_server(listed=True)` | `build_server(listed="claude")` |
| tools | `projects` `project` `project_chat` `create_project` `elements` `add_element` `upload_link` `image_models` `video_models` `effects` `generate_image` `apply_effect` `write_scene` `scene` `quote` `approve` `job` `library` `share_link` `reformat` `trim_clip` `assemble_clips` `balance` `search` `whoami` `recent` `credit_history` `recommend_model` `duplicate_scene` `feedback` `preferences` `set_preferences` `recipes` `recipe` `save_recipe` `what_works` `score_caption` (37 since the effects change below; 35 from the overnight build) | the same, minus `approve`, `image_models`, `generate_image`, `effects` and `apply_effect` (32 tools; `job` is back because the free edits start jobs). Counted by the MCP Inspector on 2026-10-12, before the effects change: 35 and 32 |
| renders? | yes: `quote`, the person's yes, then `approve` (signed tokens, credit held before submit); a still through `generate_image` and an effect through `apply_effect`, each quoted first with a signed single-use token | no: `quote` returns `approve_url`, the scene's page in the studio, and the person approves the render on its Render card. Nothing is drawn either |
| OAuth metadata | `/.well-known/oauth-protected-resource/mcp` | `/.well-known/oauth-protected-resource/mcp/claude` (its own `resource`, so a client that checks the URL it dialled is satisfied) |

The operator's static key reaches the full server at `/mcp`, as before,
and the Claude server at `/mcp/claude`, so Mike can see exactly what a
reviewer sees there.

## What changed on both

- **No board** (that part landed on main first, in #226's higgsfield-shape
  work): the board tools are gone from every server, `write_scene` makes the
  scene itself (`project_id` files it, `scene_id` rewrites one), and
  `approve` needs no pick. What THIS change adds on top: the Claude listing,
  and `scene`, which reads a scene back in a short form (status, shots, the
  clips so far, a studio link). That status outlives the in-memory `job`.
  Neither form carries judge scores or operator vocabulary.
- **No `save_chat`.** It sends the conversation to the server, which
  OpenAI refuses outright and Anthropic asks connectors to avoid. It
  stays on the studio surface (stdio) and the operator's server.
- **Credits, never dollars.** A listed `quote` drops `estimate_usd`.
- **Honest descriptions.** No listed description points at a tool its
  server lacks. The operator's `INSTRUCTIONS` no longer claim "nothing
  here renders" next to an `approve` tool. `write_scene` is marked
  destructive (passing an id replaces a scene, and OpenAI counts an
  overwrite as destructive).
- **`job` after a restart** points at `scene`. Jobs still live in
  memory, but a render lands on its scene (fal recovery reattaches it),
  so `scene` is the status that survives a deploy.
- **`llms.txt` rewritten.** It is both listings' `resource_documentation`,
  and it still pitched photographed rooms and real footage.
- **The domain.** `PHANTRA_MCP_RESOURCE` is now `api.phantra.ai`
  (fly.toml). Both directories expect the server's domain to match the
  service.

## Added the same evening: a picture, a still, a draft (2026-10-11)

Mike's calls, `docs/tasks/task-connector-elements.md`. A new person had no
elements, `write_scene` took photo refs only from `elements`, and nothing
on either listing could add one, so the first scene anybody tried was
refused.

- **`add_element` on both listings.** One picture -- the https address of
  an image file, or a `gen:<id>` of the person's own -- filed as a
  character, prop or location. It draws nothing and spends no credits, so
  it belongs on the Claude listing too: the tool writes one element and
  reaches the web for one image (`openWorldHint: true`), which is not AI
  media generation. The address is fetched https-only with every redirect
  checked, capped at 15 MB, and refused with the reason when it is a page
  rather than a picture.
- **`image_models` and `generate_image` on the render listing only.** A
  still, behind the same signed single-use quote the desktop surface
  uses, answered in credits (no dollars). Never on `/mcp/claude`.
- **A scene with no photos is saved as a draft.** `write_scene` used to
  refuse it. It now answers `needs_reference` and says what to do;
  `quote` still refuses a draft, and nothing renders against no
  photograph from either listing or from the studio.

What this changes for the submissions: the Inspector pass (task step 5)
has three more tools on `/mcp` and one more on `/mcp/claude`; the ChatGPT
listing text may say a still can be drawn, and must still not mention
prices; the Anthropic answer is unchanged (it writes, adds a picture and
prices; rendering and drawing happen in the studio).

## The overnight build (2026-10-11 → 10-12, `docs/tasks/task-connector-overnight.md`)

Mike's call: build the list so both listings can be submitted within two
days. Five stacked PRs (#276–#280) add twenty-one tools to BOTH listings;
none of them generates media or spends credits, so the Anthropic answer is
still unchanged and the ChatGPT listing gains the same set.

| group | tools | what they are |
|---|---|---|
| files in (PR 1) | `upload_link` | a one-time page on the API origin (`/u/<token>`, 30 minutes, one file, jpg/png/webp/heic or mp4/mov typed by their bytes) that files the upload as an `asset:<id>` and, when asked, onto an element. `add_element` also takes a product PAGE now: its main picture, and the page's stated facts in the notes as quoted data |
| library and free edits (PR 2) | `library` `share_link` `reformat` `trim_clip` `assemble_clips` `job` | the person's renders and uploads by id; a presigned download link (at most seven days); a copy in a new shape (pad or crop), a range of a clip, clips joined — all through the studio's editor on its own server, each a new item, nothing spent; `job` (with `wait`) because they run as jobs |
| reading (PR 3) | `balance` `search` `whoami` `recent` `credit_history` `video_models` `recommend_model` | all read-only, every answer in credits only (`video_models` prices each frame in credits on a listed server; `recommend_model` is a pure ranking) |
| writes (PR 4) | `duplicate_scene` `feedback` `preferences` `set_preferences` `recipes` `recipe` `save_recipe`, and `roles` on `write_scene` | every one makes a NEW row: a copy of a scene (never its renders), a note to the studio, a workspace's defaults (checked against the live catalogue, newest row wins), the studio's recipe shelf beside a person's own (versioned, returned as quoted data) |
| insights (PR 5) | `what_works` `score_caption` | what the person kept and posted; a caption scored against their own posts; neutral and saying so with too little data |

Three new OWNED tables (`mcp_feedback`, `mcp_preferences`, `mcp_recipes`)
plus `upload_claims`, each listed in `SUBMISSION.md`'s data table. The
plugin's v0.3.0 (its own PR) adds seventeen skills that name only these.

## Effects on the render listing (2026-10-13)

Mike's call, in the ChatGPT plugin handoff of that date: the studio's
effects table (`src/effects.py`: image edits, animated templates and camera
moves on a still, upscale, added sound, re-framing, background removal) is
reachable from `/mcp`, and only from `/mcp`.

- **`effects`** lists the table as a stranger reads it: each effect's
  options and legal values, and `credits` at its default options (null when
  the price hangs on the clip it is given). No dollar rate, no provider
  page, no word about a tool that listing lacks.
- **`apply_effect`** is the second spending tool on that listing, behind
  the same gate as a still (`approval_gate` / `start_approved`): no
  `quote_token` returns a quote in credits and spends nothing; the quote's
  own token runs it once, as a job. A token quoted for one effect, option
  or source runs no other.
- **Sources are the caller's own ids only:** `gen:<id>` or `asset:<id>`, as
  `library` lists them. An address, an element photo and a search candidate
  are refused before anything is read; somebody else's id is refused exactly
  as a missing one is. (The studio surface still takes its wider grammar.)
- **Never on `/mcp/claude`.** An effect is AI media generation, which
  Anthropic's directory refuses. That listing is unchanged at 32 tools.
- **Also changed on the way, both on the render listing:** its spending
  tools' descriptions no longer promise an `upgrade_url` (a listed refusal
  for credits carries the numbers and no link, since 2026-10-12), and a
  failed still or effect is said in a customer's words
  (`src/failures.plain`) instead of the provider's raw error, which goes to
  the server's log. Its `elements` description now says an effect takes
  library ids rather than an element photo. The Claude listing's published
  tools, descriptions and instructions are byte for byte what they were
  (compared against `origin/main` tool by tool).

What this changes for the submission: `/mcp` publishes 37 tools once this is
deployed, so `screens/inspector-render.json` (35, captured 2026-10-12) needs
a fresh capture then; the ChatGPT package gains an `effects` skill in its own
repository, to be merged only after this is live. One thing to weigh before
submitting: OpenAI's guidelines ask for "each operation as its own tool" and
no "generic executor". `apply_effect` takes an `effect` name and an `options`
object, but it reaches only the thirteen rows of a closed table, each checked
and refused off-table, the way `generate_image` takes a `model`. If a
reviewer reads it otherwise, the remedy is one tool per category.

## Listing materials (2026-10-11)

Checked live the day the `/connector` page went out (PR #245):

- **Docs URL, both listings:** `https://phantra.ai/connector` (200, in
  the sitemap). It says what the connector does, gives both addresses and
  the steps to add it, and prints no price, plan or rating. It was reworded
  the same day for the tools above (`add_element`, the still on `/mcp`,
  draft scenes). `https://api.phantra.ai/llms.txt` (200) stays the
  `resource_documentation` both OAuth documents publish.
- **Privacy policy URL:** `https://phantra.ai/privacy` (200). Since
  the revision dated 11 Oct 2026 it has a section, "Connecting a chat app":
  how a connection is made, what the chat app can read and do, what leaves
  the Studio for the chat app's company, what the Studio receives and
  records, and how to disconnect. The API origin serves the same text at
  `https://api.phantra.ai/privacy`. (Written on branch
  `claude/privacy-connector`; it is the policy only once that is merged.)
- **Terms:** `https://phantra.ai/terms` (200).
- **Support contact:** the address `/terms`, `/privacy` and `/connector`
  print (`LEGAL_CONTACT` in `web/src/components/legal-page.tsx`).
- **A change to what the connector does is a change to `/connector`.** Its
  top comment lists what each sentence was checked against.

## By hand, before submitting (none of this is code)

1. ~~Fly secret `PHANTRA_MCP_HOSTS` must include `api.phantra.ai`.~~
   Not needed: the resource's own host is always allowed
   (`mcp_mount.allowed_hosts`).
2. **Reconnect Mike's own Claude connector** at the new address
   (`/mcp/claude` to see what reviewers will see, or `/mcp` to keep
   rendering from chat). The old fly.dev address publishes a resource
   that no longer matches.
3. **Test account** (both directories want one that is fully populated):
   `zp-billing-test` from `SUBMISSION.md` C28. Give its user a password,
   upload at least one element, and leave one written scene and one
   project in it.
4. **OpenAI**: verify the organization on the OpenAI Platform (Owner
   role), submit with the MCP URL, test credentials, a privacy-policy
   URL, a support contact and example prompts. No screenshots or CSP
   are needed, because there is no UI component. Choose a global (not
   EU) data-residency project. The listing text must not mention prices
   or plans.
5. **Anthropic**: submit `https://api.phantra.ai/mcp/claude` through
   the MCP directory form. Its tools are all ones the checklist accepts
   (they read, write scenes and price), and nothing in it renders.
   Answer the AI-media acknowledgment truthfully: the connector writes
   and prices scenes, and rendering happens in the studio after the
   person approves it there.
6. **Run both through the MCP Inspector** and as a custom connector in
   each product. Both checklists ask for this.
7. ~~**After the overnight build is merged and deployed (2026-10-12):** walk
   the reviewer steps in `SUBMISSION.md` once as the test account on
   `/mcp/claude` -- they now include `upload_link` (open the page on a
   phone), `library`, `reformat` and `job` -- and set the test account's
   password first. Merge the plugin's v0.3.0 PR after the connector is
   live, since its skills name the new tools.~~ **Done 2026-10-12**
   (`docs/tasks/task-connector-submission.md`): the build is live (Fly v294),
   the password is set, the plugin's v0.3.0 is merged (b1c6b93), and the
   reviewer walk as the test account is recorded in
   `docs/directory/walk-2026-10-13-claude.md` (the Claude listing) and
   `walk-2026-10-13-render.md` (the `/mcp` half). What is left is item 5's and
   item 4's own last line: submit the connector, then the plugin, and pair them.
