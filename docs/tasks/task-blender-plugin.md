# Task: a Phantra add-on inside Blender

**From:** a session started by another session on 2026-11-03, on Mike's ask for "a Blender
plugin" in the family of the editor panels. Standing rules that applied: no change to the API
or the MCP server (the connector is frozen until ChatGPT lists Phantra); nothing spends without
a price the person saw; never spend credits or sign in as a reviewer account; a private repo
with the Premiere / Resolve proprietary license (Mike, 2026-10-23: offered later as a download
from phantra.ai, never from GitHub).

Read `docs/tasks/task-premiere-plugin.md` first: the Blender add-on uses the same API door
(`/plugin/v1`), the same sign-in by code and the same quote-then-approve as the Premiere Pro
and DaVinci Resolve panels.

## The add-on: `phantra-blender-plugin` (beside this repo)

Repo: `../phantra-blender-plugin` (committed on `main`, 0.1.0). **The GitHub repo is not
created yet**: this session's `gh repo create` was refused twice by the auto-mode classifier.
Mike runs, from that folder:

```bash
gh repo create zeropage-onryo/phantra-blender-plugin --private --source . --remote origin --push --description "Phantra for Blender: make AI images and video and bring your Phantra Library into the project and onto the Video Sequencer."
```

A Blender **4.2+** add-on, installable from one zip (`scripts/build-release.sh` ->
`dist/phantra-blender-plugin-0.1.0.zip`, reproducible, sha256 printed). The zip holds one folder
`phantra_blender/` with both `bl_info` (4.1 and older, Add-ons > Install) and
`blender_manifest.toml` (4.2+, Get Extensions > Install from Disk; Blender finds the manifest
inside the folder). The manifest declares `network` and `files` permissions and a
`LicenseRef-Phantra-Proprietary` license, so it is for phantra.ai's download, never Blender's
extensions platform (which takes GPL-compatible code only).

- `phantra.py`: the Phantra API client, stdlib only, no `bpy`: sign-in by code (`Pending.wait`
  polls `/pair/token`), `me`, `tool`, `price` / `price_scene` (a `Price` whose `run()` is the
  only call that spends), `upload`, `wait_for_job` (backoff on blips), the connector's refusals
  in plain words (`PLAIN`), plus `bad_client` and `cannot_approve`.
- `urls.py` / `downloads.py` / `names.py`: the Resolve panel's rules in Python. A file downloads
  only from an address Phantra handed out in an answer this session, on Phantra's own hosts
  (the API as configured, media.phantra.ai, the R2 presign host; a local API only when the
  add-on points at one), every redirect checked, into one folder (`~/Movies/Phantra`, a
  preference), under a plain name, `.part` then rename, an existing file reused never
  overwritten.
- `store.py`: the token in a 0600 file under Blender's user config (`.../config/phantra/token`).
  Blender's Python has no keychain; the Premiere panel uses UXP secureStorage and the Resolve
  panel Electron safeStorage. Sign out revokes the token (`/signout`) and deletes the file.
- `state.py`: a worker thread per call, answers delivered on the main thread by a
  `bpy.app.timers` pump (4/s), so Blender's UI never waits on the network.
- `host.py`: Blender itself. Import loads an Image / Movie Clip / Sound; Insert also places a
  strip on the Video Sequencer at the playhead on the lowest free channel (3 s for a still, a
  clip's own length plus its sound strip above it). **Send frame to Phantra** renders the current
  frame (or draws the viewport) and uploads it through `/plugin/v1/upload`, free, as an
  `asset:<id>` that the effects then take. `docs/blender-apis.md` in the repo lists every bpy
  call and where it was checked.
- `ops.py` / `ui.py` / `__init__.py`: the operators, the Phantra tab in the sidebar (N) of the
  3D Viewport and the Video Sequencer (Library / Make / Jobs), preferences (download folder, API
  base for development). Approve is its own operator and runs only the price on screen; a
  price taken while the form changed is thrown away; after an Approve the panel never says
  "nothing was charged" but points at the Library and credit history.
- Effects offered: camera move (still -> clip), edit image, remove background, upscale clip,
  add sound, reframe clip. Not in v1: `edit_clip` (the two-step frame-then-clip flow), sending
  a clip from the sequencer up (only a frame), thumbnails in the Library (Blender's sidebar
  cannot show a remote image without a preview collection), Windows and Linux paths beyond
  `~/Movies/Phantra` (they work, the folder name is just Mac-shaped).

Tests: `python3 -m unittest discover -s tests -t .` (31: the client, URL rules, names, store,
downloads, the worker), run on both system Python 3.13 and Blender's own 3.11; CI
(`.github/workflows/test.yml`) runs them on 3.11.

## What the API lacks (not added: the freeze)

`src/plugin_tokens.CLIENTS` has `premiere`, `resolve` and `discord-bot`; `/plugin/v1/pair` with
`client: "blender"` answers 400 `bad_client` on the live API (checked 2026-11-03: Premiere and
Resolve pairings answer a code, Blender is refused). **The whole change is one line:**

```python
CLIENTS = {"premiere": "Premiere Pro", "resolve": "DaVinci Resolve", "blender": "Blender", ...}
```

plus a `tests/test_plugin_api.py` case like `test_a_resolve_panel_signs_in_and_is_named_everywhere`
for `app="blender"`, and the two sentences that name the apps by hand
(`web/src/components/studio/link-app.tsx` line 82, `settings/connections.tsx` line 61: "DaVinci
Resolve or Premiere Pro"). The link page and the Apps card already take the client's label from
the pairing, so "Connect Blender" and the Apps list need nothing else. When the freeze lifts
this goes in its own PR; until then the add-on's Sign in says "This Phantra server doesn't take
Blender sign-ins yet."

Later, the download: `web/src/lib/downloads.ts` (`PanelId` is `resolve | premiere`, each with
its file extension) and `ops/upload_plugin_r2.py` would gain `blender` with `.zip`.

## As built (2026-11-03)

- Blender 4.5.15 LTS was installed on this Mac for the check (Homebrew cask; it was not here).
- **Installed from the zip** with Blender's own installer code (`blender --command extension
  install-file -r user_default -e dist/phantra-blender-plugin-0.1.0.zip`, the same path as
  Preferences > Install from Disk): enabled as `bl_ext.user_default.phantra_blender`; both panels,
  thirteen `phantra.*` operators, the settings and the preferences register; the manifest
  validates (`--command extension validate`).
- **Walked end to end against a local API** on this branch (a throwaway schema on the test
  Postgres, every real key blanked, a fake FAL key, a demo signing secret, and `"blender"` added
  to `CLIENTS` in that process only; a seeded workspace with 500 purchased credits), headless and
  then in a real Blender window with the real timers and the panel's draw code (screenshots in
  the session's hand-over note): Sign in -> the code and the link shown -> the code approved at
  `POST /api/plugin/link` as the seeded person (what the link page does) -> signed in, workspace
  name and 500 credits drawn, 8 image models and 13 video models listed, the token file at 0600;
  Send frame (Workbench, 320x180) -> `asset:1` in the Library, free; Import with Insert -> the
  file in `~/Movies/Phantra` and an image strip on channel 1 at the playhead, 72 frames; Get
  price for an image -> "FLUX 1.1 Pro, 10 credits, balance 500, after 490" on the card, then
  Cancel (**nothing was approved, nothing spent**); a camera-move price on the sent frame was
  the server's own refusal, shown plainly ("cannot be made fetchable for the renderer": the
  local run has no bucket; the live API has one); Sign out -> the token revoked, the file gone,
  `/me` refused.
- **Not verified:** sign-in against the LIVE API (refused at `/pair` until the one-line change
  above lands, so nobody can type a code yet); a video priced through `write_scene` + `quote`
  (needs an element photo; the code path is the Premiere panel's, tested in the client's unit
  tests); an approved render of any kind (never done, on purpose); Blender 4.2 to 4.4 (only
  4.5.15 here; the `strips` / `sequences` rename is handled); Windows and Linux; the zip through
  the Preferences window by hand (the CLI installer is the same code); whether Blender's
  extension system wants `bl_info` removed (4.5 drops it from the module and says nothing).
