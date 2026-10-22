#!/bin/bash
# Pushes the homepage branch (wide-screen Vesper stage, orange ripple hero,
# Vesper back to full size on the homepage) and opens its pull request.
cd "$(dirname "$0")" || exit 1
git push origin refs/claude-tmp/vesper-wide:refs/heads/claude/vesper-wide-desktop || { echo "Push failed."; read -n1 -p "Press any key..."; exit 1; }
if command -v gh >/dev/null; then
  gh pr create --head claude/vesper-wide-desktop --base main \
    --title "Homepage: full-bleed Vesper stage, orange ripple hero, homepage Vesper back to full size" \
    --body "- Vesper section fills wide desktop screens (>=1281px); layout at <=1280px unchanged.
- Orange ASCII ripple layer behind the hero (click to send a ring).
- Homepage Vesper back to full size; only the studio's floating assistant stays smaller.

🤖 Generated with [Claude Code](https://claude.com/claude-code)" && gh pr view --web
else
  open "https://github.com/zeropage-onryo/Phantra-AI/compare/main...claude/vesper-wide-desktop?expand=1"
fi
read -n1 -p "Done. Press any key to close."
