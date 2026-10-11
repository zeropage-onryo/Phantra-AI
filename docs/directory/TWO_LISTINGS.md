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
| URL | `https://api.zeropage.studio/mcp` | `https://api.zeropage.studio/mcp/claude` |
| built by | `build_server(listed=True)` | `build_server(listed="claude")` |
| tools | `projects` `project` `project_chat` `create_project` `elements` `add_element` `image_models` `generate_image` `write_scene` `scene` `quote` `approve` `job` | the same, minus `approve`, `job`, `image_models` and `generate_image` (9 tools) |
| renders? | yes: `quote`, the person's yes, then `approve` (signed tokens, credit held before submit); and a still through `generate_image`, quoted first with a signed single-use token | no: `quote` returns `approve_url`, the scene's page in the studio, and the person approves the render on its Render card. Nothing is drawn either |
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
- **The domain.** `ZEROPAGE_MCP_RESOURCE` is now `api.zeropage.studio`
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

## By hand, before submitting (none of this is code)

1. ~~Fly secret `ZEROPAGE_MCP_HOSTS` must include `api.zeropage.studio`.~~
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
5. **Anthropic**: submit `https://api.zeropage.studio/mcp/claude` through
   the MCP directory form. Its tools are all ones the checklist accepts
   (they read, write scenes and price), and nothing in it renders.
   Answer the AI-media acknowledgment truthfully: the connector writes
   and prices scenes, and rendering happens in the studio after the
   person approves it there.
6. **Run both through the MCP Inspector** and as a custom connector in
   each product. Both checklists ask for this.
