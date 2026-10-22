#!/bin/bash
# Adds the walkthrough-video autoplay fix to the open /mcp pull request
# (branch claude/mcp-page-fixes). Vercel rebuilds the preview from it.
set -e
cd "$(dirname "$0")"
REPO="$(pwd)"
# keep a log beside the patch so Claude can read what happened
exec > >(tee "$REPO/Claude outputs/ship-mcp-video-fix.log") 2>&1
echo "== $(date)"
PATCH="$REPO/Claude outputs/mcp-video-autoplay.patch"
WT="$REPO/../phantra-mcp-page-fixes"
BR="claude/mcp-page-fixes"

if [ ! -d "$WT" ]; then
  echo "== The branch folder is missing; making it again"
  git fetch origin "$BR"
  git worktree prune
  git worktree add "$WT" "$BR"
fi
cd "$WT"
git pull --ff-only origin "$BR" || true
# clear anything a previous run left behind: changed tracked files, and the
# untracked (git-ignored) video files the first push wrote but never committed
git checkout -- . 2>/dev/null || true
mkdir -p /tmp/phantra-mcp-leftovers
for f in web/public/mcp/how/claude-connect.mp4 web/public/mcp/how/claude-connect.webm; do
  if [ -e "$f" ] && ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    mv -f "$f" /tmp/phantra-mcp-leftovers/
  fi
done

echo "== Checking the fix applies"
if ! git apply --check "$PATCH"; then
  echo ""
  echo "The fix does not apply cleanly to the branch. Nothing was committed. Tell Claude."
  read -p "Press Return to close."
  exit 1
fi
git apply "$PATCH"
# -f: the repo's .gitignore skips *.mp4, which is why the first push left the video out
git add -f web/public/mcp/how/claude-connect.mp4 web/public/mcp/how/claude-connect.webm
git add web/src/components/mcp/hero-connect.tsx web/src/app/mcp/page.tsx
git commit -m "web: /mcp walkthrough video plays when the How to connect pop-up opens

The video never played on the Vercel preview because the MP4 was not in
the commit: the repo's .gitignore skips *.mp4. Force-add it, add a WebM
copy offered first, and mute the element by hand on mount and call play(),
since React does not reliably set muted before the browser's autoplay
check. Still waits on its poster under reduced motion.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TMu1Tk7u5J3P9psb3Ns2Ut"

echo "== Pushing"
git push origin "$BR"
echo ""
git log --oneline -2
echo "Done. The pull request's Vercel preview will rebuild in a couple of minutes."
read -p "Press Return to close."
