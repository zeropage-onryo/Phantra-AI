#!/bin/bash
# Ships the /mcp page fixes (2026-10-16): puts the patch on a new branch in a
# separate folder (your current branch and uncommitted work are not touched),
# pushes it, and opens the pull request. Vercel builds a preview from it.
set -e
cd "$(dirname "$0")"
REPO="$(pwd)"
PATCH="$REPO/Claude outputs/mcp-page-fixes.patch"
WT="$REPO/../phantra-mcp-page-fixes"
BR="claude/mcp-page-fixes"

echo "== Fetching latest main"
git fetch origin main

if [ -d "$WT" ]; then
  echo "== Using existing folder $WT"
else
  echo "== Making a separate folder for the branch: $WT"
  git worktree add -b "$BR" "$WT" origin/main
fi
cd "$WT"

echo "== Checking the patch applies to the latest main"
if ! git apply --check "$PATCH"; then
  echo ""
  echo "The patch no longer applies cleanly (main changed since it was made)."
  echo "Nothing was committed. Tell Claude and it will rebase the patch."
  read -p "Press Return to close."
  exit 1
fi
git apply "$PATCH"
git add web/public/mcp/how web/src/app/globals.css web/src/app/mcp/page.tsx \
        web/src/components/mcp/hero-connect.tsx web/src/components/mcp/particle-morph.tsx \
        web/src/components/mcp/aurora.tsx
git commit -m "web: /mcp page fixes — ChatGPT first, open+copy connect, particle hero, restyled How to connect with Claude walkthrough video

- Page opens on the ChatGPT pill; hash links still pick a client
- Connect in a minute section removed; its setup facts moved into the
  How to connect modal and two FAQ answers (kept in server HTML for the
  ChatGPT listing's docs URL)
- ChatGPT Connect opens chatgpt.com/plugins and copies the server address
  (ChatGPT has no prefill link; swap to the listing link once approved)
- How to connect button and modal restyled to the approved Figma
- Claude modal plays the walkthrough video (public/mcp/how/), not autoplayed
  under reduced motion
- Hero background: iridescent particle form on black (canvas; still under
  reduced motion, paused off screen, fewer points on phones; aurora removed)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TMu1Tk7u5J3P9psb3Ns2Ut"

echo "== Pushing $BR"
git push -u origin "$BR"

BODY="Fixes to phantra.ai/mcp approved 2026-10-16: ChatGPT pill first; Connect in a minute removed (setup facts moved into the modal + FAQ); ChatGPT Connect opens chatgpt.com/plugins and copies the address; How to connect restyled to the approved Figma with the Claude walkthrough video; iridescent particle-form hero background on black.

Checked: eslint, tsc, next build clean; pills and hash links, copy buttons, modal keyboard/focus, no horizontal scroll at 390, contrast behind the copy (95th percentile: headline 13:1+, grey line 7.6:1+), setup steps present in server HTML. Not checked: video playback in real Chrome/Safari (the test browser can't decode H.264).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01TMu1Tk7u5J3P9psb3Ns2Ut"

if command -v gh >/dev/null 2>&1; then
  gh pr create --base main --head "$BR" --title "web: /mcp page fixes (ChatGPT first, particle hero, How to connect)" --body "$BODY" || true
  gh pr view --web || true
else
  open "https://github.com/zeropage-onryo/Phantra-AI/compare/main...$BR?expand=1"
fi
echo ""
echo "Done. Vercel will post a preview link on the pull request."
read -p "Press Return to close."
