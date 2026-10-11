# Connecting the studio to Claude

Three commands and one paste. Everything below runs on THIS Mac.

## 1. Install the MCP package into the venv

```bash
cd "/Users/iphone/Documents/PRODUCTION PIPLINE .GIT"
venv/bin/pip install "mcp>=2"
```

## 2. Check the server actually starts

```bash
venv/bin/python -m src.mcp_server
```

(`--engine` or `--surface board` in an older config is harmless: both are
accepted and ignored, and the server says so on stderr.)

It should print nothing and sit there — that is correct. A stdio server
talks down a pipe, so silence *is* the healthy state. `Ctrl+C` to stop.

If it exits with a traceback instead, that is the thing to fix before
going any further; the desktop app will show you nothing useful.

## 3. Register it with Claude Desktop

The block lives in `ops/claude-desktop-mcp.json`: `zeropage` (the studio:
images, video, effects, projects). It goes into `mcpServers` in
`~/Library/Application Support/Claude/claude_desktop_config.json`.

There is one entry. Until 2026-10-11 there was a second, `zeropage-board`,
for the idea board's tools; the board was removed
(`docs/tasks/task-higgsfield-shape.md`), and the script below takes that
entry out of the config if it finds it.

**The edit only sticks while the app is quit.** Claude Desktop reads
`mcpServers` when it starts and rewrites that file from memory while it
runs, so a block written under a running app is gone the next time the app
saves (seen twice on 2026-10-10: once after seven seconds, once after under
three minutes). So, from the repo folder, in Terminal — not in the app's
own terminal, which quits with it:

```bash
open -a Terminal ops/register-claude-desktop.command
```

It waits for you to quit Claude Desktop **completely** (⌘Q — closing the
window is not enough, and it ends every running session), writes a backup
of the config, adds the `zeropage` block, removes a leftover
`zeropage-board` one, leaves every other key alone and opens Claude again.
The studio's tools appear under the connector icon.

By hand it is the same order: quit first, then paste the block into
`mcpServers` beside any servers already there (and delete `zeropage-board`
if it is there), then reopen.

### If a server shows "Server disconnected" right after a start

Claude Desktop launches each local server twice within a few seconds
and keeps the second. Until 2026-10-10 the two copies could deadlock
each other's table setup in Postgres and one of them died -- about half
of all starts. The server now takes a lock around that setup, so the
copies take turns instead.

One copy's table setup takes about 15 seconds against the live database
(measured 2026-10-10 from this Mac), and on that day the copy Desktop
keeps answered after about 30, because it waited for the dropped copy to
finish its setup first. Since 2026-10-11 the dropped copy notices that
nobody is listening and leaves without doing the setup, so a start is
back to one setup. Measured that day against the live database: the copy
Desktop keeps answered in 15 to 16 seconds, and with two copies started
together (a second entry, when there still was one) the second answered
in about 27. Expect more when the Mac is busy: with test runs going it
was 23 to 27 seconds for a single start.

If a server does disconnect, the reason is in
`~/Library/Logs/Claude/mcp-server-zeropage.log`: the last traceback there
is the thing to fix. Two lines starting `note:` are worth knowing.
"starting without it" means the lock could not be taken. "nobody to
serve" is the dropped copy leaving, which is normal once per start; if it
is the LAST thing in the log before "Server disconnected", the kept copy
left by mistake and that is a bug in the check (`stdin_dropped` in
`src/mcp_server.py`).

## Does Claude Desktop draw a panel for it? (the MCP Apps probe)

The inline viewer (a render shown in the chat, a drop zone for files)
needs Claude Desktop to render an MCP App for a local server, and reports
say it sometimes silently does not. This is the test, and it takes two
minutes:

1. Add one line to this checkout's `.env`: `ZEROPAGE_MCP_APPS_PROBE=1`
2. Quit Claude Desktop completely (⌘Q) and open it again. If `zeropage` is
   not registered yet, the script above does both: it waits for the quit,
   adds the block and reopens the app.
3. In a normal chat, ask: *"Call the zeropage `ui_probe` tool, then
   `ui_probe_report`, and tell me what the report says."*

If MCP Apps works, a small panel titled **Zero Page · MCP Apps probe**
appears with five ticks; press its button, then ask for the report again.
If nothing appears, the report still says how far the app got -- whether
it said it supports panels, whether it fetched the panel, whether the
panel ever ran -- in one sentence.

Take the line out of `.env` afterwards and restart once more. The probe
adds three test tools and nothing else; it spends nothing, reads nothing
and is never on the web connector. `src/mcp_apps_probe.py` has the detail.

## Why stdio and not a tunnel

The desktop app launches this process itself and talks to it over a
pipe. No port, no bearer token on the public internet, nothing to leave
running, and nothing to restart when a tunnel hostname changes. The
desktop app also proxies its local MCP servers up to cloud sessions, so
the studio is reachable from a phone through the same connection — the
tunnel was only ever buying the part the desktop already does.

`START_SERVER.md` still documents the HTTP mount. That is for the case
stdio cannot serve: something that is NOT Claude Desktop reaching the
studio over a network. A signed-in person reaches the hosted connector
there (their projects and elements, `add_element` to bring a picture in,
and `write_scene` / `quote` / `approve`); the operator's key in `.env`
reaches the same studio surface
this page describes, without `import_file`. `ZEROPAGE_MCP=1` turns the
mount on.

## What it can and cannot do

The server Claude Desktop launches is the **studio surface**: images,
video and effects made with Claude. Every image, clip, effect and element sheet is two
calls -- the first returns a quote in credits (with your balance before
and after) and spends nothing; only after you say yes does Claude call
again with that quote's `quote_token`. The token is signed for exactly
that request and works once: a changed model, length, prompt or option is
refused, and a repeated call returns the first job instead of charging
again. Approving needs `QUOTE_SIGNING_SECRET` set in `.env` (generate one
with the command in `src/pricing.py`'s `SIGNING_COMMAND`); without it the
quotes still answer and nothing can be approved.

| tool | what it does |
|---|---|
| `image_models` / `video_models` | the models, their options and prices |
| `effects` | image edits, Kling / PixVerse template effects, camera moves, and clip finishing: upscale / frame rate, added sound, re-framing a clip to a new shape (`reframe`, `reframe-hq`), removing a clip's background (`remove-video-background`, `remove-video-background-pro`) -- options and price rules |
| `elements` | your characters, props and places, with the photo `ref`s a render can use |
| `renders` | your recent renders as `gen:<id>` |
| `images_for` | web reference images, as `candidate:<id>` |
| `prompt_craft` | the studio's prompt-writing guides, for Claude to apply |
| `projects` / `project` | your projects; open one to get its brief, look, scenes, the reference images they used, its renders and its latest chat |
| `project_chat` | page back through a project's chat history |
| `create_project` | start a project (it shows on the studio's projects board) |
| `save_chat` | keep this conversation with a project, so it is there when the project is reopened -- here or in the studio |
| `generate_image` / `generate_video` / `apply_effect` | quoted, then (after your yes) run as a job; the result lands on the Assets wall, and in a project when given its `project_id` |
| `job` | poll a running render |
| `import_file` | bring an image (jpg, png, webp) or a clip (mp4, mov) from your Downloads or Desktop folder into the studio, by its full path -- it comes back as an `asset:<id>` you can use as a reference, an effect source or a clip to join. Reads nothing outside those folders |
| `edit_clip` | change something in a clip by instruction ("make the jacket red"). Two approvals: first ONE frame is edited as a still for a few credits, and its quote shows what the whole clip would cost on each model; after you have seen the frame, the clip is edited (Kling O1 by default, FLUX.3 as the cheap option). The clip edit only accepts the frame made for that clip and that instruction |
| `assemble_clips` | join 2-20 of your clips (`gen:<id>`) into one video -- hard cuts or crossfades, an optional music bed (`renders` with `kind=audio` lists your uploaded audio). Spends no credits; the result is a new clip on the Assets wall and an editable cut in the editor. Clips of different shapes are refused unless you ask for letterboxing |
| `cancel_job` | stop a render, effect or sheet this connector started. Not yet sent, or still waiting in fal's queue: nothing charged. Already rendering: fal is asked to stop; if it finishes anyway it is kept and charged at the quoted price, otherwise nothing is charged. Finished: too late. A sheet already being drawn finishes |

## There is no idea board

Until 2026-10-11 a second, **board** surface carried the pre-production
board: `board`, `idea`, `search`, `capture`, `pick`, `archive`, `shoot`,
`stats`, the spark bank (`add_spark`, `tonight`, `sparks`, `images`,
`reference`) and, behind `--engine`, `research` and `generate`. The studio
no longer has a board -- a scene is made in a project and rendered from
the scene, with the price shown -- so that surface and those tools were
removed (`docs/tasks/task-higgsfield-shape.md`, step 3).

What that changes on this machine:

- `ops/claude-desktop-mcp.json` has one entry. `--surface board` and
  `--engine` in an old config are accepted and ignored.
- The idea-agent skill drove the board tools and has nothing to drive.
  Whether it and the research agent are deleted or rebuilt is step 9 of
  that task doc, and has not been decided.
- The scout and the graph still run by hand: `python -m src.scout run`,
  `python -m src.trigger`. `ops/bank.py` still banks a spark or a
  reference.

**Nothing here renders without a yes.** Every spending tool answers with a
quote first and runs only on the quote's own token.
