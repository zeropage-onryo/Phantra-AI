#!/bin/bash
# Double-click me (Claude, 2026-10-03). Finishes the Phantra AI cleanup:
#   1. pushes branch chore/zeropage-studio-cleanup and opens its PR (you merge it)
#   2. stops the local server and the nightly LaunchAgents
#   3. renames this folder to "Phantra AI"
#   4. repoints everything that hard-codes the old path: venv scripts,
#      LaunchAgents, Claude Desktop's zeropage MCP entry, Dev Studio.app,
#      run_morning_prompts.sh, git worktrees
#   5. renames the zeropage account's label in the live database
#   6. turns the LaunchAgents back on
# Close other Claude sessions working in this folder first. Log:
# ~/Library/Logs/phantra-rename.log
set -u
OLD_NAME="PRODUCTION PIPLINE .GIT"
NEW_NAME="Phantra AI"
OLD_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT="$(dirname "$OLD_DIR")"
NEW_DIR="$PARENT/$NEW_NAME"
LOG="$HOME/Library/Logs/phantra-rename.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee "$LOG") 2>&1
pause() { echo; read -n1 -r -p "Press any key to close."; exit "${1:-0}"; }
step() { echo; echo "== $*"; }

if [ "$(basename "$OLD_DIR")" = "$NEW_NAME" ]; then echo "Already renamed."; pause 0; fi
if [ -e "$NEW_DIR" ]; then echo "STOP: $NEW_DIR already exists. Nothing changed."; pause 1; fi
cd "$OLD_DIR" || pause 1

step "1. Push the cleanup branch"
B=chore/zeropage-studio-cleanup
if git push -u origin "$B"; then
  if command -v gh >/dev/null; then
    gh pr create --base main --head "$B" \
      --title "chore: clean out dead files, rename the product to Phantra AI" \
      --body "Removes finished one-off scripts, the unused Pinterest lane, stale launchers and a .bak; every visible name now reads Phantra AI. Slugs, env vars, URLs, module names and LLM prompts unchanged. Full suite green on a Postgres throwaway (3036 passed).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Ni4qm2dc3KWA1t9hhhshex" || true
  else
    open "https://github.com/zeropage-onryo/video-pipeline/compare/main...$B?expand=1"
  fi
else
  echo "Push failed -- carrying on with the rename; push the branch later."
fi

step "2. Stop the server and the LaunchAgents"
PORT="${PHANTRA_PORT:-8000}"
PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null)"
[ -n "$PIDS" ] && { echo "stopping server pid(s) $PIDS"; kill $PIDS 2>/dev/null; sleep 3; }
pkill -f "uvicorn app.main:app" 2>/dev/null
AGENTS=()
for p in "$HOME"/Library/LaunchAgents/*.plist; do
  [ -f "$p" ] && grep -q "$OLD_NAME" "$p" && AGENTS+=("$p")
done
for p in "${AGENTS[@]+"${AGENTS[@]}"}"; do
  echo "unloading $(basename "$p")"
  launchctl bootout "gui/$(id -u)" "$p" 2>/dev/null || launchctl unload "$p" 2>/dev/null
done

step "3. Rename the folder"
cd "$PARENT" || pause 1
mv "$OLD_DIR" "$NEW_DIR" || { echo "STOP: rename failed (is something open in it?). Nothing else changed."; pause 1; }
cd "$NEW_DIR" || pause 1
echo "now: $NEW_DIR"

step "4. Repoint hard-coded paths"
fix() {  # fix <file>: swap the old folder name for the new one, in place
  [ -f "$1" ] || return 0
  grep -q "$OLD_NAME" "$1" || return 0
  sed -i '' "s|$OLD_NAME|$NEW_NAME|g" "$1" && echo "  fixed: $1"
}
for f in venv/bin/*; do [ -f "$f" ] && ! [ -L "$f" ] && [ "$(head -c2 "$f")" = "#!" ] && fix "$f"; done
for f in venv/lib/python*/site-packages/*.pth venv/lib/python*/site-packages/__editable__*; do fix "$f"; done
for f in run_morning_prompts.sh start-studio.command START_SERVER.md ops/connect-claude.md \
         ops/claude-desktop-mcp.json "Dev Studio.app/Contents/MacOS/DevStudio" \
         "/Applications/Dev Studio.app/Contents/MacOS/DevStudio"; do fix "$f"; done
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CFG" ] && grep -q "$OLD_NAME" "$CFG"; then
  cp "$CFG" "$CFG.bak-before-phantra-rename"; fix "$CFG"
  echo "  (quit and reopen Claude Desktop so the zeropage connector picks up the new path)"
fi
for p in "${AGENTS[@]+"${AGENTS[@]}"}"; do fix "$p"; done
git worktree repair 2>/dev/null
for w in .claude/worktrees/*; do [ -d "$w" ] && git worktree repair "$w" 2>/dev/null; done
git worktree prune
echo "  git worktrees repaired"

step "5. Rename the account label in the live database"
venv/bin/python - <<'PY' || echo "  skipped (DB not reachable) -- harmless, only the label"
from dotenv import load_dotenv; load_dotenv()
from src.db import connect
with connect() as c:
    n = c.execute("UPDATE accounts SET display_name = %s WHERE slug = 'zeropage'",
                  ("Phantra AI",)).rowcount
print(f"  accounts updated: {n}")
PY

step "6. Turn the LaunchAgents back on"
for p in "${AGENTS[@]+"${AGENTS[@]}"}"; do
  launchctl bootstrap "gui/$(id -u)" "$p" 2>/dev/null || launchctl load "$p" 2>/dev/null
  echo "  loaded $(basename "$p")"
done

echo; echo "DONE. Folder is now: $NEW_DIR"
echo "Double-click studio.command to start the server again."
mv "$NEW_DIR/rename-to-zeropage-studio.command" "$NEW_DIR/_to_delete/" 2>/dev/null
pause 0
