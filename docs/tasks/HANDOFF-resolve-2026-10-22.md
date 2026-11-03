# Handoff: DaVinci Resolve with Claude and Phantra (2026-10-22)

From a Cowork session to Claude Code on Mike's Mac. Mike has **DaVinci Resolve Studio (paid)**
and **no Premiere Pro**, so Resolve is the editor to build for and test against first. Three
jobs, in this order: (1) Claude Desktop drives Resolve, (2) Claude Code drives Resolve and
Phantra, (3) a Phantra panel inside Resolve, the Resolve version of the Premiere panel.

## State right now

- **This checkout is on `main` at `dcc76e5`.** The Premiere work is NOT here yet: it is PR
  **#457**, branch `claude/premiere-plugin` (`7e3021b`), open, not merged, not deployed. It adds
  the panel's API door (`src/plugin_tokens.py`, `app/plugin_api.py`, router `/plugin/v1`), the
  sign-in-by-code page `/studio/link` and an Apps card in Settings > Connect MCP. Read
  `docs/tasks/task-premiere-plugin.md` on that branch before touching any of it.
- **The Premiere panel's code** (UXP, v0.2.0, commit `45e1f19`) is NOT on GitHub: creating the
  public repo `zeropage-onryo/phantra-premiere-plugin` was refused by a permission check and is
  Mike's to do. The code is in `data/phantra-premiere-plugin.zip` (unzip it beside this repo as
  `../phantra-premiere-plugin`). `src/phantra.js` there is host-free and tested
  (`node --test test/`, 9 pass); it is the part the Resolve panel reuses unchanged.
- **The Resolve MCP** (community, github.com/samuelgursky/davinci-resolve-mcp) is cloned at
  `~/Documents/davinci-resolve-mcp`. Its installer is `install.py` (the `install.sh` in older
  guides no longer exists). It merges a `davinci-resolve` entry into Claude Desktop's config
  and keeps every other entry (read and dry-run checked).
- **`setup-resolve-claude.command`** (repo root, untracked, NOT run yet: there is no
  `data/resolve-setup.log`): finds a Python 3.10+, opens Resolve, waits for Cmd+Q on Claude
  Desktop, backs up the config, runs `install.py --clients claude-desktop`, checks that both
  `phantra-ai` and `davinci-resolve` are in the config (restores `phantra-ai` from the backup if
  it went missing), runs the connector's `scripts/doctor.py`, logs it all to
  `data/resolve-setup.log` and reopens Claude.
- **Trap: two names for one Mac?** Mike's Terminal prompt says user `mikemassaad`; Claude
  Desktop's files are under `/Users/iphone`. Check `id -un` and `echo $HOME` first. If they are
  two different homes, an install from Terminal writes a config Claude Desktop never reads.
- **Resolve's setting** Preferences > System > General > *External scripting using* must be
  **Local** (Studio only; no script can set it). Resolve must be open for every Resolve tool.
- `ops/claude-desktop-mcp.json` holds ONE entry, `phantra-ai`. Do not add the Resolve entry
  there: that file is this repo's server only.

## What was verified

- `install.py` read: it merges into `mcpServers` and writes a `.backup` first; with no tty its
  prompts take their defaults. A dry run against a copy of a config showed the entry it writes:
  `{"command": "<repo>/venv/bin/python", "args": ["<repo>/src/server.py"], "env": {}}`.
- Nothing has been run on the Mac yet. Claude Desktop currently loads one local server,
  `phantra-ai`.

## What is next

Rules for the whole run: **no renders and no paid calls** (a price shown is fine; only Mike
approves a spend); tests + `ruff` before every push; commit and push only when Mike says so;
nothing in `src/mcp_server.py`, `app/mcp_mount.py` or `app/mcp_auth.py` changes (the connector
is in directory review); never print a secret.

### 1. Claude Desktop drives Resolve (no branch, no code)

1. `id -un; echo $HOME` (the trap above).
2. Mike runs `open "/Users/iphone/Documents/PRODUCTION PIPLINE .GIT/setup-resolve-claude.command"`
   and presses Cmd+Q in Claude Desktop when it asks. (Running it from inside Claude Desktop
   kills the session that started it; run it from Terminal or Finder.)
3. Read `data/resolve-setup.log`. Every `FAIL` line from the doctor is the work. Usual ones:
   scripting not set to Local; Resolve not open; `fusionscript.so` not found (set
   `RESOLVE_SCRIPT_LIB` to the one inside the installed `DaVinci Resolve.app`, re-run
   `python3 install.py --clients claude-desktop` with Claude quit); the venv's Python 3.13 and
   Resolve's loader disagreeing (re-run the installer with a 3.12: `python3.12 install.py ...`).
4. Done when, with Resolve open on a project, Claude Desktop answers "what's in my media pool?"
   AND the Phantra tools still work in the same chat.

### 2. Claude Code drives Resolve and Phantra (no branch; user-scope config only)

1. Resolve, user scope (NOT the installer's `--clients claude-code`: that writes `.mcp.json`
   into the current folder, and inside this repo it would get committed):
   ```bash
   R=~/Documents/davinci-resolve-mcp
   API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
   claude mcp add davinci-resolve -s user \
     -e RESOLVE_SCRIPT_API="$API" \
     -e RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so" \
     -e PYTHONPATH="$API/Modules/" \
     -- "$R/venv/bin/python" "$R/src/server.py"
   ```
   Use the same paths the installer wrote for Claude Desktop (read them from
   `~/Library/Application Support/Claude/claude_desktop_config.json`), not these guesses, if
   they differ.
2. Phantra, one of two (Mike's call below):
   - **Local studio server** (the same one Claude Desktop runs, every tool):
     `claude mcp add phantra-ai -s user -- bash -c 'cd "/Users/iphone/Documents/PRODUCTION PIPLINE .GIT" && exec venv/bin/python -m src.mcp_server'`
   - **Hosted connector** (the ChatGPT listing, renders, signs in with OAuth):
     `claude mcp add --transport http phantra -s user https://api.phantra.ai/mcp`
3. `claude mcp list` shows both connected; in a Claude Code session `/mcp` lists their tools.
4. Done when one Claude Code session can list Phantra's Library, `share_link` a finished render,
   download it, and `ImportMedia` it into a "Phantra" bin in Resolve. Free steps only.
5. Optional (Mike's call): a skill `phantra-to-resolve` (find the render, download, import into
   a bin, append at the playhead) so this is one sentence next time.

### 3. Phantra panel inside Resolve: BUILT (2026-10-22, same Cowork session)

- **API: PR #462** (branch `claude/resolve-plugin`, stacked on #457): `CLIENTS` gains
  `resolve`, the link page names the client, a test. Merge #457 first, then #462.
- **Panel: `phantra-resolve-plugin`**, commit `86eac44`, public at
  https://github.com/zeropage-onryo/phantra-resolve-plugin (2026-10-23), cloned at
  `~/Documents/phantra-resolve-plugin/`. Read its README and
  `docs/resolve-apis.md`, and `docs/tasks/task-resolve-plugin.md` on the #462 branch (design,
  as built, the review's ten fixes).
- Verified: 61 node tests (bridge rules, Resolve layer on a fake Resolve in plain and promise
  API, timecode, URL hosts, names, token store); a real run on Electron 36.3.2 (Resolve's own
  version) against a local API: sign in by code, Library, a priced image, a page-driven approve
  stopped by the native confirm dialog, forged calls refused, download, sign-out revoking.
- **What's left is the run inside Resolve**, and it can only happen on this Mac:
  1. Quit Resolve; double-click `~/Documents/phantra-resolve-plugin/install.command` (asks for the Mac
     password; copies `WorkflowIntegration.node` from Resolve's own developer folder).
  2. Resolve: Workspace > Workflow Integrations > Phantra. It points at api.phantra.ai, so
     sign-in works only once #457 + #462 are deployed. Before that, run the local API and set
     `PHANTRA_API_BASE=http://127.0.0.1:8000` for Resolve (`launchctl setenv`, then restart it).
  3. Check, free steps only: sign in, Library, Import, Insert at playhead (watch which track and
     how long a still lands), Clip on the timeline, Frame at playhead, a price shown and
     CANCELLED in the confirm window. No Approve unless Mike says so.
  4. Anything that misbehaves: note the Resolve version and fix in `src/resolve.js` with a test
     in `test/resolve.test.js` first.

## Mike's calls

1. **Order:** merge and deploy #457 first, or build the Resolve API change on its branch? (A
   merge needs `QUOTE_SIGNING_SECRET` set on Fly, or every spending tool answers 503.)
2. **Phantra in Claude Code:** the local studio server (every tool, your Mac only) or the hosted
   connector (works anywhere, OAuth sign-in)?
3. **Public repos:** done 2026-10-23: `zeropage-onryo/phantra-premiere-plugin` and
   `zeropage-onryo/phantra-resolve-plugin`, both public, CI on `npm test`.
4. **Premiere:** park it until someone with Premiere 25.6+ can test it, and lead with Resolve?
5. **Distribution:** Blackmagic has no plugin store, so the Resolve panel ships as a download
   from phantra.ai (an installer `.pkg`, later signed and notarized). OK?
6. **The `phantra-to-resolve` Claude Code skill:** build it in step 2 or not?
