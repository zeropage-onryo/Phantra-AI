#!/usr/bin/env bash
# Lists every remaining Zero Page / ZPF / ZP trace, minus the lines in
# docs/tasks/rename-allowlist.txt (one fixed-string `path:line-text` fragment per line,
# `#` comments allowed, each with a reason). Usage: scripts/brand-grep.sh [-- pathspec...]
set -u
cd "$(git rev-parse --show-toplevel)"
paths=()
if [ "${1:-}" = "--" ]; then shift; paths=("$@"); fi
allow=docs/tasks/rename-allowlist.txt
touch "$allow"
hits=$(git grep -nIiE 'zero[ _.-]?page|\bzpf\b|\bzp\b|zeropage' -- "${paths[@]:-.}" ':!docs/tasks/rename-allowlist.txt' ':!scripts/brand-grep.sh')
pat=$(grep -vE '^\s*(#|$)' "$allow")
if [ -n "$pat" ]; then hits=$(printf '%s\n' "$hits" | grep -vFf <(printf '%s\n' "$pat")); fi
printf '%s\n' "$hits" | sed '/^$/d'
echo "matches: $(printf '%s\n' "$hits" | sed '/^$/d' | wc -l | tr -d ' ')" >&2
exit 0
