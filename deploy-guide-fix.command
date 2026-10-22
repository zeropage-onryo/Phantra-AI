#!/bin/bash
# Ships Claude's 2026-10-01 follow-up (Openverse thumbnail fetch, Accept header): pushes the branch,
# opens the PR, waits for CI, merges (main -> Fly + Vercel deploy).
# Your checked-out branch and working tree are not touched.
cd "$(dirname "$0")" || exit 1
B=fix/openverse-thumb-accept
LOG=data/_to_delete/deploy-thumb-fix.log
exec > >(tee "$LOG") 2>&1
set -e
git fetch data/_to_delete/thumbfix.bundle "$B:$B"
git push -u origin "$B"
if command -v gh >/dev/null; then
  gh pr create --base main --head "$B" \
    --title "fix(refbin): accept */* so Openverse thumbnail fallback answers" \
    --body "Follow-up to #111: live test on the deployed API still showed most frames 'not fetched' -- Flickr refuses Fly, and Openverse's /thumb/ fallback 406s an image-only Accept header.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01L7EGbveeucroFTrhYZzLiq" || true
  echo "Waiting for CI..."
  sleep 20
  gh pr checks "$B" --watch --fail-fast && gh pr merge "$B" --merge --delete-branch && echo "MERGED -- Fly + Vercel deploy from main now."
else
  open "https://github.com/zeropage-onryo/video-pipeline/compare/main...$B?expand=1"
  echo "gh not installed: the PR page is open in your browser -- create it, merge when CI is green."
fi
echo "DONE"
read -n1 -p "Press any key to close."
