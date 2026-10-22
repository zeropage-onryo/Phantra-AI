# Task: a Phantra panel inside DaVinci Resolve Studio

**From:** a Cowork session, 2026-10-22. **Mike's call (in chat):** "make the resolve plugin in a
separate repo as well adding whatever is needed". He has Resolve Studio (paid) and no Premiere,
so this is the panel he can actually test. Standing rules: no changes to the MCP connector
while it is in directory review; nothing spends without a price the person saw; no renders
during the build.

Read `docs/tasks/task-premiere-plugin.md` first: the Resolve panel uses the same API door
(`/plugin/v1`), the same sign-in by code and the same Phantra client file.

## What changed in this repo

- `src/plugin_tokens.py`: `CLIENTS` gains `"resolve": "DaVinci Resolve"`. A Resolve panel pairs
  by code exactly as the Premiere one does, and the link page and the Apps card name it.
- `web/src/components/studio/link-app.tsx`: the warning names the client the pairing says it is
  ("Only connect a code your own DaVinci Resolve panel is showing you"), not "Premiere" by hand;
  the intro and the empty Apps card name both apps.
- `tests/test_plugin_api.py`: a Resolve pairing end to end (pair, preview, connect, the Apps
  list, the token, `/me`).

## The panel: `phantra-resolve-plugin` (beside this repo)

A Resolve **Workflow Integration**: an Electron app Resolve Studio loads from
`/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/com.phantra.resolve/`
and lists under Workspace → Workflow Integrations.

- `main.js` (main process) owns the Resolve bridge (`WorkflowIntegration.node`, copied from the
  installed Resolve by the installer, never committed), the Phantra client and token
  (encrypted with Electron `safeStorage`), downloads (to `~/Movies/Phantra`) and uploads
  (streamed from disk). IPC answers only its own window.
- `preload.js`: one named call per action; the sandboxed page gets no Node, no Electron and no
  Resolve object.
- `src/bridge.js`: the rules, tested alone. The page never sees the token or a quote_token (a
  price is a card plus an opaque id; Approve runs that id once); `tool` reaches only free and
  reading tools; spending tools only through `price` then `approve`; any `quote_token` / `tokens`
  argument is refused; downloads only from addresses Phantra handed out (`src/urls.js`); the
  browser opens only phantra.ai.
- `src/resolve.js`: the Phantra bin, import (ImportMedia lands in the current folder, so the bin
  is made current and the person's folder restored), placement at the playhead through
  `AppendToTimeline` (absolute `recordFrame`, never below the timeline start; a free track is
  picked because an overlapping append is silently dropped; the track is read back to prove it
  landed), the selected clip (`GetSelectedClips` on 21.0.4+, else the clip under the playhead)
  with its range, the frame (`ExportCurrentFrameAsStill`).
- `src/phantra.js` is the Premiere panel's file, now taking `app` ("premiere" / "resolve").
- `install.command` / `uninstall.command` for macOS.

## As built (2026-10-22)

- API: `13d955c` on branch `claude/resolve-plugin` (off `claude/premiere-plugin`, PR #457).
  `tests/test_plugin_api.py` + `tests/test_tenancy.py`: 101 passed; ruff clean; web typecheck and
  304 node tests pass.
- Panel: 52 node tests (`npm test`): the client, the bridge rules, timecode (drop-frame
  included), the URL book, the token store, and the Resolve layer against a fake Resolve in
  both the plain and the promise API.
- **Run for real on Electron 36.3.2** (the version Resolve 20.1+ embeds) against a local API on
  this branch, driven by Playwright: the page has no `require` or `process`; sign-in by code ->
  typed code approved at `/api/plugin/link` -> signed in (workspace and balance); five forged
  calls from the page all refused (a spending tool through `tool`, a forged `quote_token`, an
  unknown approval id, a download from an address Phantra never gave, a non-phantra.ai link);
  an image priced at 0 credits is the plain refusal and nothing is spent; a seeded Library item
  downloaded into `~/Movies/Phantra` and then refused only because Resolve wasn't there; sign
  out revoked the token (gone from the Apps list). The installer was run against a fake
  `/Library` and its installed copy booted.
- **Not run inside Resolve** (no Resolve here). `docs/resolve-apis.md` in the panel repo lists
  each Resolve call, its source, and the two things only a real run can settle: a still's
  placement length and which audio track a video-with-sound's audio takes.

## Left for later

A signed and notarized installer `.pkg` (Blackmagic has no plugin store, so the panel ships as a
download from phantra.ai); Windows (`%PROGRAMDATA%` paths, a `.cmd` installer); the Resolve-side
`RenderStart` / `RenderStop` callbacks; a public repo (Mike's to create); a license (Mike's
call).
