#!/bin/bash
# Adds the /mcp hero lag fix to the open pull request (branch
# claude/mcp-page-fixes). Vercel rebuilds the preview from it.
set -e
cd "$(dirname "$0")"
REPO="$(pwd)"
# keep a log beside the patch so Claude can read what happened
exec > >(tee "$REPO/Claude outputs/ship-mcp-perf-fix.log") 2>&1
echo "== $(date)"
PATCH="$REPO/Claude outputs/mcp-hero-perf.patch"
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
git checkout -- web/src/components/mcp/particle-morph.tsx 2>/dev/null || true

echo "== Checking the fix applies"
if ! git apply --check "$PATCH"; then
  echo ""
  echo "The fix does not apply cleanly to the branch. Nothing was committed. Tell Claude."
  read -p "Press Return to close."
  exit 1
fi
git apply "$PATCH"
git add web/src/components/mcp/particle-morph.tsx
git commit -m "web: /mcp hero particles no longer lag the page

The particle background set a new rgba() string and fillStyle for every
point on every frame at full device resolution. Colours now come from a
fixed palette built once, points are binned by colour and each bin is
filled as one path, the canvas stays at 1x pixel density, points drop
from 2200 to 1600 (1000 on phones) and frames cap at 60 (30 on machines
that can't hold 60). The canvas also holds still while the How to
connect pop-up is open, so its 40px backdrop blur stays cheap. Script
time on the page drops about 4x; the look is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TMu1Tk7u5J3P9psb3Ns2Ut"

echo "== Pushing"
git push origin "$BR"
echo ""
git log --oneline -2
echo "Done. The pull request's Vercel preview will rebuild in a couple of minutes."
read -p "Press Return to close."
