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
- [ ] **MIKE:** D1. Add `generate_image` and `image_models` to the listed connector? They spend
  credits behind the same signed quote the studio surface uses. Risk: the Claude directory
  checklist refuses connectors that generate images through AI models; `approve` already does
  this on purpose (`docs/directory/RENDER_DESIGN.md`), so this widens an accepted risk, not a new one.
  - Done when: Mike has answered yes or no in chat. Record it under "Decisions" at the bottom.
- [ ] **MIKE:** D2. Keep the reference gate as is (a scene needs at least one photo)? Recommended:
  keep it, and fix the gap with step 2's tool instead of loosening the gate.
  - Done when: answered and recorded.

### 1. Unblock today, no code
- [ ] **MIKE** (or Claude in Chrome, with his go): add one element with a photo in the studio at
  `https://zpf-web.vercel.app/studio/elements` ("+ Add element", a name, one image).
  - Done when: the connector's `elements` tool returns `count >= 1` with a `ref` on the photo.

### 2. Add `add_element` to the connector
- [ ] Branch: `git switch -c claude/connector-add-element origin/main`.
- [ ] In `src/mcp_server.py`, write `add_element(kind, name, source, notes="", ...)`:
  `kind` is character | prop | location; `source` is ONE of an `https://` image URL, a
  `gen:<id>` the account owns (a render, the "Make element" move), or an `asset:<id>` upload.
  It calls an injected `create_element` callable and returns the new element with its photo
  `ref`s, the same shape `elements` lists.
  - Done when: the function exists and refuses: a non-https URL, a host `refbin.public_host`
    rejects, a `gen:`/`asset:` that is not the caller's, an empty name, an unknown kind.
- [ ] Do NOT draw a reference sheet here. A sheet is a Nano Pro still (33 credits) and needs its
  own quote; pass `sheet=False`.
  - Done when: a test asserts no model or image call is made by `add_element`.
- [ ] In `app/mcp_mount.py`, inject `create_element`: a thin wrapper over `api._create_entity` /
  the locations route body, called with `photo_urls=[...]` and the caller's `account_id`. No
  second implementation.
  - Done when: the wrapper is under 30 lines and calls the existing create body.
- [ ] Publish it: `TITLES`, `DESCRIPTIONS`, `HINTS` (`read: False, destructive: False,
  idempotent: False, open_world: True`), and add `"add_element"` to `LISTED_TOOLS` right after
  `"elements"`, and to `STUDIO_TOOLS` the same.
  - Done when: `venv/bin/python -m pytest tests/test_mcp_server.py -q` passes after updating the
    tool-list assertions (around lines 686-692) to the new tuple.
- [ ] Rate and size: one image per call, the editor's upload cap, counted by the mount's existing
  per-account limit.
  - Done when: a test feeds an oversize image and gets a plain refusal, not a 500.

### 3. If D1 = yes: images on the listed connector
- [ ] Add `"image_models"` and `"generate_image"` to `LISTED_TOOLS`.
- [ ] Confirm the listed door goes through `approval_gate` exactly as the studio door does: no
  `quote_token` -> a quote and no spend; the token once -> a job; again -> `already_used`.
  - Done when: a test in `tests/test_mcp_mount.py` drives the real streamable-HTTP app as a
    signed-in caller through quote -> approve -> repeat, with fal stubbed.
- [ ] Unknown from here: whether `QUOTE_SIGNING_SECRET` is set on the Fly app. Check by name only:
  `fly secrets list -a zeropage-studio | grep QUOTE_SIGNING_SECRET`.
  - Done when: the name is listed, or **MIKE** sets it (without a secret, quotes answer with no
    token and nothing can be approved).

### 4. Prove it end to end, locally
- [ ] `venv/bin/python -m pytest tests/ -q` and `venv/bin/ruff check .`.
  - Done when: both are clean.
- [ ] A mount test: alice `add_element` from `gen:<id>` -> `elements` lists it -> `write_scene`
  with that `ref` succeeds -> bob cannot see it or use its ref.
  - Done when: the test passes and fails if `_allowed_refs` is bypassed.

### 5. Docs
- [ ] Update `CLAUDE.md`: the "it has ten" line under "NO IDEA BOARD", the `LISTED_TOOLS` list in
  "THE LISTED SERVER", and one sentence on `add_element`.
  - Done when: `grep -n "add_element" CLAUDE.md` finds it in both places.

### 6. Ship
- [ ] Push the branch and open a PR to `main` with what changed and the test names.
  - Done when: CI is green on the PR.
- [ ] **MIKE:** merge, then deploy per `docs/DEPLOY_FLY.md`.
  - Done when: `curl -s https://zeropage-studio.fly.dev/.well-known/oauth-protected-resource`
    answers 200 after the deploy.
- [ ] Live check in a claude.ai chat with the connector: `add_element` from a public image URL,
  then `elements`, then `write_scene`, then `quote`. **Stop at the quote; ask Mike before
  `approve`.**
  - Done when: the quote comes back with credits and a balance.

### 7. Park, don't build
- [ ] Add a BACKLOG item: persist `app/jobs.py` job status (only fal renders survive a restart
  today, through `fal_requests`). Say what was seen and leave it.
  - Done when: `docs/BACKLOG.md` has the entry.

## Done means

- A brand-new account can go from an empty studio to a priced scene entirely from a Claude chat:
  add a picture, write the scene, see the quote.
- If D1 was yes, the same chat can quote and (after Mike's yes) make a still.
- The reference gate and the signed-quote spend gate are unchanged.
- Tests and CI green, CLAUDE.md says what the connector now has.

## Decisions

- D1:
- D2:
