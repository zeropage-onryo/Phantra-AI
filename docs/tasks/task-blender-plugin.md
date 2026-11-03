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

Repo: [`zeropage-onryo/phantra-blender-plugin`](https://github.com/zeropage-onryo/phantra-blender-plugin)
(private, proprietary license, created on Mike's word on 2026-11-03 after the session's own
`gh repo create` was refused by the auto-mode classifier; cloned at `../phantra-blender-plugin`;
CI runs the unit tests on Python 3.11).

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

## 0.2.0 as built (2026-11-03): the three things Higgsfield's Blender plugin had and ours lacked

From a session started on Mike's compare of the set against Higgsfield's Blender plugin
(floating bar, Scene Builder, Character Animation, a Bridge MCP, drag-to-install). The API and
the MCP server were frozen (OpenAI's review of the ChatGPT listing), so nothing here changed:
every piece lives in the add-on. Tag `v0.2.0` on the repo's main
(`zeropage-onryo/phantra-blender-plugin`); the zip is `dist/phantra-blender-plugin-0.2.0.zip`,
built by `scripts/build-release.sh` (sha256 `5f0aaa82...ec67`; `dist/` is gitignored, as for
0.1.0, so the zip is a local build, not a tracked file). Installed in this Mac's Blender 4.5.15
over 0.1.0 with Blender's own installer; Mike's running Blender keeps 0.1.0 in memory until it
restarts.

**1. Drag-to-install: nothing was broken.** The 0.1.0 zip already passed Blender's drop path
(`bl_pkg.bl_extension_utils`: `pkg_is_legacy_addon` false, the manifest read from the archive
by `pkg_manifest_dict_from_archive_or_error`; Blender accepts the manifest at the zip root OR in
one top-level folder, which is how ours is laid out). Verified by invoking the exact operator a
dropped `.zip` runs, `extensions.package_install_files` with `url=<zip>`, in a real window: the
console says `DROP FILE: ...`, the "Install from Disk" dialog opens (User Default, Enable
Add-on ticked, OK). The README's install section now says "drag the zip onto any Blender
window" first and the Preferences path second.

**2. Outputs as Blender data** (`phantra_blender/place.py`). Every Library row (images and
clips) and every finished job under Jobs has three buttons beside Import / Insert:
- **Plane**: a mesh plane at the 3D cursor, named `Phantra gen:<id>`, 2 units tall and as wide
  as the picture's aspect, rotated like the active camera so it faces the lens (upright facing
  -Y with no camera), with the picture as an Emission material (a still with alpha keeps it
  through a Transparent / Mix shader). Built from mesh data, no operator, so it also runs from a
  timer and headless. A clip is the same plane with a movie texture (`image.source = MOVIE`,
  `image_user.use_auto_refresh`, starting at the current frame for its own length).
- **World**: an Environment Texture into the world's Background shader (a clip plays along the
  timeline).
- **Camera**: a background image on the active camera (Fit, behind the scene); a clip the same.
`place.place(path, kind, how, scene, bring_in)` is the one door; Import / Insert are `LOAD` /
`SEQUENCER` through it. The README says plainly what the models do not make: geometry, rigs,
animation (Higgsfield's Scene Builder and Character Animation).

**3. The agent bridge.** `phantra_blender/bridge.py` (no bpy: the HTTP server, JSON-RPC, the
tool table), `bridge_tools.py` (the tools inside Blender; scene work handed to the main thread
through a queue the add-on's timer pumps, the network on the bridge's thread through the
add-on's existing client) and `bridge_stdio.py` (a plain-Python shim an agent launches). A
Bridge tab in the panel: on/off, the URL, the per-session token (minted at each start, shown
only there), "Copy setup" for Claude Desktop, Claude Code and Cursor (`window_manager.clipboard`).
On start the add-on writes `<config>/phantra/bridge.json` (0600: port, token, pid) for the shim
and removes it on stop and on unregister. Server posture: `127.0.0.1` only, bearer token
(constant-time compare), any `Origin` header 403, a non-local `Host` 403, only `/mcp`, JSON up
to 1 MB, GET 405 (no server stream; answers are plain JSON, which the streamable-HTTP clients
take). Tools: `scene_summary`, `render_frame` (render or viewport, a frame and a camera
optional, to `<Phantra folder>/frames/`), `send_frame` (only a path `render_frame` returned
this session), `library`, `models`, `price` (image / video / effect: the same arguments the
panel builds, through `ops.effect_args`; the Price lands on the panel as a card marked "Asked
by your agent", the quote token never leaves Blender), `approve` (NEVER spends: `waiting` /
`cancelled` / `approved` with the job's status, result id and loaded files; `wait_seconds` up
to 30), `place_result` (the step-2 doors). The shim answers `initialize` and `tools/list`
itself when the bridge is off, so an agent's config never breaks; a call then says to turn it
on. The README has the three configs (Desktop: the shim in `claude_desktop_config.json`; Code:
`claude mcp add phantra-blender -- python3 <shim>` or `--transport http` with the token; Cursor:
`.cursor/mcp.json` with the URL and the token, or the shim).

**Found on the way, fixed:** `media.phantra.ai` (Cloudflare) answers Python's default
User-Agent with 403, so 0.1.0 could never have downloaded a live render (its import was only
walked against a local API). Every request from the add-on now says `Phantra-Blender/0.2.0`.

**Tests.** 41 under plain Python (`tests/test_bridge.py` added: the server's refusals, the
protocol, a refusal and a crash as tool errors, the shim forwarding, reading the bridge file,
answering on its own when the bridge is off or the token is stale; a User-Agent assertion in
the downloads test) and 6 inside a headless Blender (`scripts/blender-test.sh` runs
`tests/blender/test_in_blender.py` with `--factory-startup`; a fake Phantra client and a local
copy in place of the download): registration, place_file as plane / world / camera /
sequencer (and a file outside the Phantra folder refused), place_item from the Library, the
bridge's scene_summary / render_frame / send_frame, a price from the bridge on the panel then
cancelled, an effect priced from the bridge and approved ON THE PANEL (the fake client's
`run()` called exactly once, the job landing, `approve` reporting done with the file), the
bridge over real HTTP with the 0600 bridge file. CI (ubuntu, 3.11) runs the plain ones only.

**Walked in a real Blender window against the LIVE API** (a second Blender launched by the
session beside Mike's, driven by a scratch timer that runs dropped scripts; desktop control
was declined, so no clicks; screenshots in the session's hand-over note): booted signed in
from the kept token (workspace "Phantra AI", 7,640 credits, Pro, 60 Library items, 8 image and
13 video models, 11 elements); bridge on at 127.0.0.1:7474, `bridge.json` 0600; through the
stdio shim: `initialize` (2025-06-18), `tools/list` (8), `scene_summary`, `library` (the real
rows), `models`; `price` of a 16:9 FLUX 1.1 Pro image (10 credits, 7,640 -> 7,630), the card on
the Make tab, `approve` -> `waiting`, Cancel pressed on the panel, `approve` -> `cancelled`
(three times over the walk; **nothing approved, nothing spent**, balance 7,640 throughout);
`render_frame` render and viewport (1920x1080 PNGs); `place_result` of three real renders:
gen:317 as a 3.56 x 2 plane, gen:316 as the world, gen:315 (a 121-frame clip) as the camera's
background movie, and the panel's own Plane button on gen:316; `claude mcp add` of the shim in
Claude Code -> "Connected" (then removed). Quitting Blender stopped the bridge and removed the
file. The Phantra folder the walk created was removed after.

**Not verified:** a real Finder drag onto the window (the drop operator was invoked instead);
`send_frame` against the live API (it would file a test frame in Mike's Library; checked
headless with the fake client; the upload body is 0.1.0's); a video price through
`write_scene` + `quote` (writes a scene row; the code path is the panel's, unit-tested); an
approved render of any kind (never, on purpose); Claude Desktop and Cursor actually opened
with the config (Claude Code was); Windows and Linux (the shim's bridge-file lookup has paths
for both, unrun); Blender 4.2 to 4.4; the Bridge tab in the Video Sequencer's copy of the panel
(same draw code). A script cannot select the "Phantra" sidebar tab (`active_panel_category` is
read-only), so the walk re-homed the panel into the open tab for the screenshots; the add-on
itself does nothing of the kind.

**What the API would need: nothing for 0.2.0.** The `library` rows carry `media_url` only
(`/plugin/v1/download/{ref}` exists for `gen:` ids and is not needed while the media host is
public). If the `signed` media rung ever lands, the add-on's download path takes a short-lived
`download_url` already (the UrlBook keys), so `library` would then want to return one per row.
