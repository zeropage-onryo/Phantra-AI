> Phantra was named Zero Page until 2026-10-13. This is a dated record and keeps the names of its day.

# Task — let a Claude chat get a picture into the studio, so the connector can make things

**From:** a claude.ai Cowork chat, 2026-10-11, after trying to make a still through the Zero Page
connector and getting stuck. **For:** Claude Code, in `zeropage-onryo/video-pipeline` on Mike's Mac.
**Mike's call:** "I want to start using the zeropage connector." He is also working on the
connector in another session, so check `git log origin/main -- src/mcp_server.py` first and
rebase onto whatever landed.
**Read first:** `CLAUDE.md` (the MCP block under Architecture: "THE LISTED SERVER" and "THE
STUDIO SURFACE"), `src/mcp_server.py` (`LISTED_TOOLS`, `_allowed_refs`, `write_scene`,
`approval_gate`), then `app/api.py` `_create_entity`.

## State right now

- The chat was on the **listed** connector (claude.ai OAuth). Its ten tools: `projects`,
  `project`, `project_chat`, `create_project`, `save_chat`, `elements`, `write_scene`, `quote`,
  `approve`, `job` (`mcp_server.LISTED_TOOLS`).
- On that account `elements` returned `count: 0` and `projects` returned `count: 0`.
- `write_scene` takes refs only from `elements` (`_allowed_refs`), and the reference gate refuses a
  scene with none (`preprod.reference_gate`, Mike's 2026-09-08 rule). **With no elements, the
  listed connector can make nothing**, and it has no tool that adds one. A new user hits this
  on their first try.
- The **studio** surface (stdio, and the operator's key over HTTP) already has `generate_image` /
  `image_models`, priced in credits with a signed, single-use quote (`approval_gate`). The listed
  connector does not have them.
- The element-create path already accepts a picture by URL: `POST /api/assets/characters|props|
  locations` take `photo_urls` (`_create_entity`, fetched through `_photo_bytes`).
- The eight board tools that vanished mid-chat (`board`, `idea`, `search`, `capture`, `pick`,
  `shoot`, `stats`, `archive`) were **removed on purpose** in PR #228 (2026-10-11,
  `docs/tasks/task-higgsfield-shape.md`). That is not instability; no work is needed for it.
- `app/jobs.py` is in memory, so `job` forgets a job when the server restarts. fal renders
  already recover through `src/fal_requests.py`; other jobs do not. Unknown from here: how often
  Fly restarts mid-job in practice.

## Rules for this task

- No renders, stills or any generation unless Mike says so in chat. A live check stops at the
  quote.
- Never print a secret; names only (`QUOTE_SIGNING_SECRET`, `FAL_KEY`).
- Branch from `main`; never commit to `main`. The repo is public: a push publishes.
- `src/` never imports `app/`. Anything the tool needs from `app/` is injected through
  `app/mcp_mount.py`, the way `approve_render` is.
- Every new tool is published from the constants (`TITLES` / `DESCRIPTIONS` / `HINTS`), which a
  test screens for operator vocabulary.

## Steps

### 0. Mike decides (before any code)
- [x] **MIKE:** D1. Add `generate_image` and `image_models` to the listed connector? They spend
  credits behind the same signed quote the studio surface uses. Risk: the Claude directory
  checklist refuses connectors that generate images through AI models; `approve` already does
  this on purpose (`docs/directory/RENDER_DESIGN.md`), so this widens an accepted risk, not a new one.
  - Done when: Mike has answered yes or no in chat. Record it under "Decisions" at the bottom.
- [x] **MIKE:** D2. Keep the reference gate as is (a scene needs at least one photo)? Recommended:
  keep it, and fix the gap with step 2's tool instead of loosening the gate.
  - Done when: answered and recorded.

### 1. Unblock today, no code
- [x] **MIKE** (or Claude in Chrome, with his go; not needed once step 2 is
  deployed -- `add_element` does this from the chat): add one element with a photo in the studio at
  `https://zpf-web.vercel.app/studio/elements` ("+ Add element", a name, one image).
  - Done when: the connector's `elements` tool returns `count >= 1` with a `ref` on the photo.
  - Seen 2026-10-11, after the deploy: `elements` through the signed-in connector answered
    `count: 1` ("Michael", 14 photos, a `ref` on each). Not known from here: who added it
    and when, or whether that is the sign-in whose `elements` answered 0 that morning.

### 2. Add `add_element` to the connector
- [x] Branch: built on `claude/task-connector-elements-54e8af` (the session's own worktree
  branch), on top of `origin/main` at 607ef41 (#221, the two listings), then merged up to
  a2fe0c9 (#229, #236, #237, #238, #240) the same afternoon.
- [x] In `src/mcp_server.py`, write `add_element(kind, name, source, notes="", ...)`:
  `kind` is character | prop | location; `source` is ONE of an `https://` image URL, a
  `gen:<id>` the account owns (a render, the "Make element" move), or an `asset:<id>` upload.
  It calls an injected `create_element` callable and returns the new element with its photo
  `ref`s, the same shape `elements` lists.
  - Done when: the function exists and refuses: a non-https URL, a host `refbin.public_host`
    rejects, a `gen:`/`asset:` that is not the caller's, an empty name, an unknown kind.
- [x] Do NOT draw a reference sheet here. A sheet is a Nano Pro still (33 credits) and needs its
  own quote; pass `sheet=False`.
  - Done when: a test asserts no model or image call is made by `add_element`.
- [x] In `app/mcp_mount.py`, inject `create_element`: a thin wrapper over `api._create_entity` /
  the locations route body, called with `photo_urls=[...]` and the caller's `account_id`. No
  second implementation.
  - Done when: the wrapper is under 30 lines and calls the existing create body.
- [x] Publish it: `TITLES`, `DESCRIPTIONS`, `HINTS` (`read: False, destructive: False,
  idempotent: False, open_world: True`), and add `"add_element"` to `LISTED_TOOLS` right after
  `"elements"`, and to `STUDIO_TOOLS` the same.
  - Done when: `venv/bin/python -m pytest tests/test_mcp_server.py -q` passes after updating the
    tool-list assertions (around lines 686-692) to the new tuple.
- [x] Rate and size: one image per call, the editor's upload cap, counted by the mount's existing
  per-account limit.
  - Done when: a test feeds an oversize image and gets a plain refusal, not a 500.

### 3. If D1 = yes: images on the listed connector
- [x] Add `"image_models"` and `"generate_image"` to `LISTED_TOOLS`.
- [x] Confirm the listed door goes through `approval_gate` exactly as the studio door does: no
  `quote_token` -> a quote and no spend; the token once -> a job; again -> `already_used`.
  - Done when: a test in `tests/test_mcp_mount.py` drives the real streamable-HTTP app as a
    signed-in caller through quote -> approve -> repeat, with fal stubbed.
- [x] Unknown from here: whether `QUOTE_SIGNING_SECRET` is set on the Fly app. Check by name only:
  `fly secrets list -a zeropage-studio | grep QUOTE_SIGNING_SECRET`.
  - Done when: the name is listed, or **MIKE** sets it (without a secret, quotes answer with no
    token and nothing can be approved).
  - Checked 2026-10-11: `QUOTE_SIGNING_SECRET` is listed on `zeropage-studio` (name only).

### 4. Prove it end to end, locally
- [x] `venv/bin/python -m pytest tests/ -q` and `venv/bin/ruff check .`.
  - Done when: both are clean.
- [x] A mount test: alice `add_element` from `gen:<id>` -> `elements` lists it -> `write_scene`
  with that `ref` succeeds -> bob cannot see it or use its ref.
  - Done when: the test passes and fails if `_allowed_refs` is bypassed.

### 5. Docs
- [x] Update `CLAUDE.md`: the "it has ten" line under "NO IDEA BOARD", the `LISTED_TOOLS` list in
  "THE LISTED SERVER", and one sentence on `add_element`.
  - Done when: `grep -n "add_element" CLAUDE.md` finds it in both places.

### 6. Ship
- [x] Push the branch and open a PR to `main` with what changed and the test names.
  - Done when: CI is green on the PR.
  - Pushed and opened 2026-10-11: zeropage-onryo/video-pipeline#244. This box is ticked by
    whoever sees its CI green.
  - Seen green on its last commit (41dc35b) just before the merge: `test` and `web`
    passed, `eval-gate` skipped.
- [x] **MIKE:** merge, then deploy per `docs/DEPLOY_FLY.md`.
  - Done when: `curl -s https://zeropage-studio.fly.dev/.well-known/oauth-protected-resource`
    answers 200 after the deploy.
  - Merged 2026-10-11 15:17 EDT (de413a0); the push deployed it (the Fly Deploy run ended
    15:18:36 EDT). That address answers 200. More under "After the merge".
- [x] Live check in a claude.ai chat with the connector: `add_element` from a public image URL,
  then `elements`, then `write_scene`, then `quote`. **Stop at the quote; ask Mike before
  `approve`.**
  - Done when: the quote comes back with credits and a balance.
  - Run twice on 2026-10-11, on Mike's yes each time: in a claude.ai chat on `/mcp`, and
    from a Claude Code session on `/mcp/claude`. All four calls answered both times; each
    quote was 194 credits beside a balance of 11,486. Nothing was approved. Under "After
    the merge".

### 7. Park, don't build
- [x] Add a BACKLOG item: persist `app/jobs.py` job status (only fal renders survive a restart
  today, through `fal_requests`). Say what was seen and leave it.
  - Done when: `docs/BACKLOG.md` has the entry. (It is #26; #25 is the shared element
    folders, found on the way.)

## Done means

- A brand-new account can go from an empty studio to a priced scene entirely from a Claude chat:
  add a picture, write the scene, see the quote.
- If D1 was yes, the same chat can quote and (after Mike's yes) make a still.
- The signed-quote spend gate is unchanged. The reference gate is unchanged where anything
  is PRICED or SPENT (`quote`, both approve bodies); by D2 it no longer refuses the WRITE.
- Tests and CI green, CLAUDE.md says what the connector now has.

## Decisions

Mike's, in chat, 2026-10-11. PR #221 had landed an hour before the questions were asked, so
there were two listings to decide for, not one.

- D1: **Yes, on `/mcp` only.** `image_models` and `generate_image` join the render listing
  (the ChatGPT one, and anyone who adds `/mcp` by hand), behind the studio surface's own
  signed single-use quote. Never `/mcp/claude`: #221 took `approve` off that listing because
  Anthropic's directory refuses AI-media connectors, and a still is the same thing.
- D2: **Loosen it for the connector.** `write_scene` saves a scene with no photos instead of
  refusing it. The option as it was put: "Approve would still refuse it at render time unless
  that gate is loosened too" -- so ONLY the write loosened. `quote` and both approve bodies
  still ask `preprod.reference_gate`, and nothing renders against no photograph.
- D3 (new, asked with the other two): **`add_element` on both listings.** It draws nothing,
  so the Claude listing has it too -- a new person there is no longer stuck with zero
  elements.

## As built (2026-10-11)

What is in the branch, where it differs from the steps above, and what was found on the way.

**The tool.** `add_element(kind, name, source, notes="")` on all three servers:
`LISTED_TOOLS` (13 tools now), `CLAUDE_LISTED_TOOLS` (9) and `STUDIO_TOOLS` (22). `source` is
one of an https image address, `gen:<id>` or `asset:<id>`. It answers with the element as
`elements` lists it and the new photo's `ref`.

**Where it differs from the steps.**

- *Bytes, not `photo_urls`.* The step said to call the create body with `photo_urls=[...]`.
  That path (`_photo_bytes` -> `imagery.fetch_image_bytes`) follows redirects on its own,
  accepts plain http, and answers None for every failure -- so a public page that redirects
  to a private address would be fetched from inside the network, and a caller could not be
  told why a picture was refused. `add_element` fetches the picture itself
  (`refbin.fetch_public_image`: https at every hop, each hop's host checked, a page or a
  document refused before a byte is read, streamed against the cap, a reason for every no),
  proves it decodes, and hands the create body the bytes as one upload. The create body is
  still the one body: `app/api.create_element`, which the Elements routes now call too.
  `fetch_image_bytes` itself was left alone; its redirect handling is a separate question.
  (Answered the same day: it and `refbin.fetch` now walk every hop through
  `refbin.public_bytes`, the walker `fetch_public_image` is built on. They still take plain
  http and still answer None.)
- *15 MB, not "the editor's upload cap".* The editor takes a 100 MB image. Every later reader
  of an element photo -- the vision description, a sheet, a keyframe -- assumes the 15 MB
  bound a fetch has always had, so that is the cap here, by address and by id.
- *The wrapper lives where the step said, the body one file over.* `mcp_mount.
  connector_element` is 21 lines with its docstring (the step asked for under 30) and only
  adapts (one photo, `sheet=False`, `strict=True`,
  a refusal in the page's words). `app/main.py` hands it `api.create_element`, the way it
  hands over `api.approve_render`.
- *"No model or image call".* No image is drawn and no credits are held: no sheet job, no
  image model, no ledger entry -- tested with an image key present, which is when the page
  WOULD have drawn a sheet. The page's one model call still happens: the vision description
  of the photo, which is what makes an element findable, is free, and sits behind the page's
  own `_create_gate` (asked before the picture is fetched). Skipping it would have made a
  second kind of element.
- *Always registered.* `approve` registers only when its bodies are injected. `add_element`
  registers on every server and says so when a server was built without the create body --
  a test server, mostly -- so the tool lists the tests pin are the lists people see.
- *The desktop (stdio) server has it.* `main()` reaches `app.api` on the first call, not at
  start, and refuses if the server was started on another database with `--db`.

**Found on the way, and closed for this door only: element folders are shared by name.**
`characters/me/` is one folder for every account on a machine, and the listing reads it
first. Two seeded accounts that each added a character called "Me" were each listed the
other's photo. That predates this task and the Elements page still has it
(`docs/BACKLOG.md` #25) -- but a chat tool makes "Me" and "Product" likely names, so the
connector does not use the folder where the bucket is the per-account store
(`asset_shelf.bucket_is_store`): a `strict` create writes a folder that is gone when it
returns and refuses if the bucket did not take the file, and every connector reader lists
the account's own bucket keys (`mcp_server._catalogue`). With no bucket -- one studio, one
machine -- nothing changed. **Unknown from here:** the value of `PHANTRA_MEDIA` on the Fly
app (the secret's name is listed; the value was not read). On `legacy` the bucket is flat
too and this protection does nothing.

**D1, as built.** `generate_image` on `/mcp` is the studio surface's `run_image` with
`listed=True`: the same `approval_gate`, the same `start_approved`, a token that is signed
over the same arguments and spent once. What differs is the answer: credits only, no
dollars, no server path, the image as an address a person can open, and `ref: gen:<id>` --
which `add_element` takes, so a chat can draw a still and keep it as a reference.
`image_models` prices in credits there. No other spending door is listed. `cancel_job` is
not on the listing; the job can still be stopped from the studio's activity tray.

**D2, as built.** `write_scene` with no `refs` saves the scene and answers
`needs_reference: true`, a `note` saying it is a draft that cannot be priced or rendered,
and a `next` naming `add_element` and the `write_scene` call that grounds it. `scene` says
the same for a draft later. `quote` on a draft is refused with the same way out. The
studio's Render card already shows such a scene as blocked.

**Tests.** `tests/test_mcp_add_element.py` (55): the fetch guard; every refusal before
anything is saved; the real create body behind the adapter; two people through the real
streamable-HTTP app (`test_from_an_empty_studio_to_a_priced_scene_and_nobody_elses_photo`,
and `test_that_run_fails_if_the_ref_gate_is_bypassed`); the same-name isolation with a fake
bucket; the still on the listing through quote -> yes -> repeat
(`test_a_signed_in_caller_quotes_approves_and_cannot_spend_the_yes_twice`).
`tests/test_mcp_server.py` gained the draft tests and the new tool lists. Four mutations
were run by hand and each was caught: the ref gate opened, the adapter asking for a sheet,
the connector listing the shared folder, a connector create writing it.

**Not done here.**

- Step 1 (an element added by hand in the studio): not needed once this is deployed.
- Step 6's merge, deploy and live check are Mike's and wait on the merge. The live check
  stops at the quote.
- The other session's work: the plugin repo's skills, the test account, the Inspector pass
  and the listing text (`docs/tasks/task-directory-submission.md`) now have three more tools
  on `/mcp` and one more on `/mcp/claude` to cover.
- `write_scene` still needs the whole prompt again to ground a draft. Letting it take
  `scene_id` and `refs` alone would be kinder to a chat; it changes a published signature,
  so it was left.

## After the merge (2026-10-11, a second session)

#244 was merged at 15:17 EDT and the push deployed it. What was checked on the deployed
app, and what was not.

**Checked.**

- `https://zeropage-studio.fly.dev/.well-known/oauth-protected-resource` answers 200, and so
  do its `/mcp` and `/mcp/claude` forms. `/mcp/` and `/mcp/claude` answer 401 with a
  `WWW-Authenticate` naming the resource document, at `zeropage-studio.fly.dev` and at
  `api.zeropage.studio`. (`/mcp` with no slash answers 307 to `/mcp/`; that is the mount's
  own redirect and this change did not touch it.)
- `elements`, called through the signed-in connector: one element, "Michael", 14 photos,
  each with a `ref`.
- `PHANTRA_MEDIA` on Fly, which "As built" left unknown: those refs came back as names
  (`/characters/michael/photo/<file>`), not as bucket addresses. `asset_shelf.storable_ref`
  answers a name only from the `tenant` rung up, so the app is on `tenant` or `signed`,
  `bucket_is_store` is true for a signed-in caller, and the same-name protection is on.
  Read off the answer's shape; the secret's value was not read.

**The live check, run twice the same afternoon, once on each listing.** Both on Mike's
yes; both stopped at the quote, and nothing was approved, drawn or rendered.

*On the render listing (`/mcp`), by the session that built this,* in a claude.ai chat
driven through Chrome. As that session recorded it: `add_element` by https address
(`credits: 0`, `described: true`), `elements` (the new prop's `ref` matched), `write_scene`
(scene 403, two shots, no warnings), `quote` (20 + 174 = 194 credits, a balance of 11,486,
signed tokens). Its prop, "Connector live check", was on the account when the second check
ran.

*On the Claude listing (`/mcp/claude`), by a second session, at 16:05 EDT,* from Claude
Code. That it was this listing is read off its nine tools, none of them `approve`, and
the quote's `approve_url`.

- `add_element`: a prop, "Connector check", from an https image on zeropage.studio. It
  answered `added: true`, `described: true`, `credits: 0`, and the photo's `ref`.
- `elements`: listed it, with that `ref`.
- `write_scene`: an 8-second scene of two timed shots on that `ref`. It answered scene 404,
  `status: written`, two shots, one reference photo, no warnings, and the studio link.
- `quote`: 20 credits for two keyframes and 174 for the clip (two shots, 6 seconds each, LTX
  2.3 at 1080p), 194 in all, beside a balance of 11,486, `affordable: true`, and
  `approve_url`. No dollars and no token, as that listing is meant to answer.

**Left on the account, all safe to delete:** the props "Connector live check" and
"Connector check", and scenes 403 and 404 (in no project). The connector cannot delete;
the studio can.

**Not checked on the deployed app.**

- `image_models`, the `generate_image` quote and `approve` on `/mcp`.
- `add_element` from a `gen:<id>`, and a `write_scene` with no `refs` (the draft).

**A connector's tool list does not follow a deploy.** Both checks met it.

- claude.ai held ten tools from before the deploy. Customize -> Connectors -> ZeroPage ->
  the menu -> "Refresh tools list" brought the thirteen, with no reconnect (the building
  session's finding).
- A Claude Code session started two minutes before the deploy still listed the board tools
  #228 removed, `write_scene` and `quote` by `idea_id`, and no `add_element`. Tools whose
  name and arguments had not changed (`elements`) still worked. Between two turns the
  connector came back under a new id with the new list; what reconnected it is not known.
