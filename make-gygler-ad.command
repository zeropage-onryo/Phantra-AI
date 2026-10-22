#!/bin/bash
# NOW SET TO RESUME: exports the two Gygler ads already built and saves them.
# Makes nothing new and spends nothing. (Step 5 of docs/tasks/task-url-to-ad.md, for
# the outside check. Runs the step-5 branch from a temporary copy, so your
# checkout and its uncommitted work are not touched. SPENDS credits on the
# voiceovers and music beds (capped at 200; it stops before spending if more).
# Output: ~/Downloads/phantra-outside-check/
REPO="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/Downloads/phantra-outside-check"
mkdir -p "$OUT"
WT="$(mktemp -d /tmp/phantra-step5.XXXXXX)"
cd "$REPO" || exit 1
echo "Fetching the step-5 branch…"
if ! git fetch -q origin claude/url-to-ad-step5 || ! git worktree add -q --detach "$WT" FETCH_HEAD; then
  echo "Could not fetch the branch. Nothing was made."; read -n1; exit 1
fi
cd "$WT" || exit 1
set -a; source "$REPO/.env"; set +a
export FAL_RECOVER=0
"$REPO/venv/bin/python" -m ops.outside_check_ad --account phantra --resume --out "$OUT" 2>&1 | tee "$OUT/run-resume.log"
cd "$REPO" && git worktree remove --force "$WT"
echo
echo "Finished. Results are in $OUT. You can close this window."
read -n1
