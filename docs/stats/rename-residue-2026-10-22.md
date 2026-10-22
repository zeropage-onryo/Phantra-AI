# Rename residue, 2026-10-22

For each file the overnight task's "State right now" lists as still containing
`zeropage`, every occurrence (case-insensitive), with line numbers, and whether
`docs/tasks/rename-allowlist.txt` (read by `scripts/brand-grep.sh`) or
`docs/tasks/brand-allowlist.txt` (the `git grep -niE "antihero|['\"]zeropage['\"]"`
check) covers it. **Nothing was renamed.** Read from `main` at `1d7b7990`.

How "covers" is decided: `brand-grep.sh` drops a line when it contains any
fixed-string fragment from the rename allowlist (`grep -vFf`); the brand
allowlist is a list of `path: what` entries matched by eye against the
quoted-`'zeropage'` check. "Prints" means `scripts/brand-grep.sh -- <file>`
still lists the line today (12 lines over these nine files; the plain grep
finds 15).

| file:line | the text | rename-allowlist | brand-allowlist | prints | what it is |
|---|---|---|---|---|---|
| `src/accounts.py:582` | `# Zero Page and its row deleted, so re-running setup must not bring it` | no | no (its neighbour `:581` "ANTIHERO was merged into" is listed) | yes | dated history in a comment |
| `src/accounts.py:584` | `` # The slug was `zeropage` until 2026-10-14 (ops/rename_account_slug.py). `` | no | no (backticks, so the brand check never prints it) | yes | dated history in a comment |
| `src/accounts.py:746` | `"phantra", "zeropage", "antihero", "shared", ...` (`RESERVED_SLUGS`) | no | **yes** | yes | a slug nobody else may take; must stay |
| `src/mcp_server.py:1161` | `"zeropage", "on the machine", "src.", "hold_queue",` (`INTERNAL_WORDS`) | no | **yes** | yes | the screen that keeps the old name out of tool text; must stay |
| `src/instagram.py:486` | `PUBLISH_FIX = ("re-issue it: Meta app ZeroPageFilms -> Instagram API with ...` | no | no | yes | the Meta developer app's REAL name, printed in an operator error message |
| `src/shootgen.py:783` | `call: no brand ideas). Zero Page used to get none (CAST_BRANDS, the` | no | no | yes | dated history in a docstring |
| `src/shootgen.py:916` | `prompts/shotlist_prompt_zeropage.txt) -- instead of a flat "shots"` | no | no | yes | docstring naming a prompt file that no longer exists (`prompts/` has `shotlist_prompt.txt` only) |
| `src/shootgen.py:927` | `def _flatten_zeropage_scenes(scenes: list) -> list:` | no | no | yes | a function NAME in live code |
| `src/shootgen.py:929` | `Zero Page's shot-plan schema is Scene -> Shots -- a scene concept with` | no | no | yes | that function's docstring |
| `src/shootgen.py:932` | `later (see prompts/shotlist_prompt_zeropage.txt).` | no | no | yes | same stale file name |
| `src/shootgen.py:1688` | `parser.add_argument("--client", ..., help="client or spec type (zeropage only)")` | no | no | yes | CLI help text a person can see (`python -m src.shootgen --help`) |
| `src/rag.py:25` | `(it was "zeropage" until 2026-10-14; ops/rename_account_slug.py moved the` | no | **yes** | yes | dated history in the module docstring |
| `app/auth.py:155` | `# 2026-09-14, found on the live account. The React studio (zeropage-web)` | **yes** (`zeropage-web`) | n/a | no | comment; the Fly app it names was deleted 2026-10-15, so the allowlist's "keeps its name until its own step" reason is stale -- it is history now |
| `app/auth.py:156` | `# and this API (zeropage-studio) are different sites -- fly.dev is on the` | **yes** (`zeropage-studio`) | n/a | no | same |
| `app/mcp_auth.py:75` | `` at `https://zeropage-studio.fly.dev/mcp` will send as `resource`. `` | **yes** (`zeropage-studio.fly.dev`) | n/a | no | docstring example naming a dead address (the app is gone; the live resource is `https://api.phantra.ai/mcp`) |
| `web/src/app/mcp/page.tsx:44` | `// - the plugin: github.com/zeropage-onryo/phantra-claude-plugin (MIT, the` | **yes** (`zeropage-onryo`) | n/a | no | comment |
| `web/src/app/mcp/page.tsx:50` | `const PLUGIN_URL = "https://github.com/zeropage-onryo/phantra-claude-plugin";` | **yes** (`zeropage-onryo`) | n/a | no | a LIVE link on the public /mcp page; correct until the GitHub account is renamed (phase 8, Mike's call) |
| `web/src/app/mcp/claude/page.tsx:41` | `const PLUGIN_URL = "https://github.com/zeropage-onryo/phantra-claude-plugin";` | **yes** (`zeropage-onryo`) | n/a | no | same live link on /mcp/claude |

## Summary

- **Covered by an allowlist, on purpose:** 9 of 18 lines. Six by the rename
  allowlist (the old Fly app names and the GitHub account), three by the brand
  allowlist (`RESERVED_SLUGS`, `INTERNAL_WORDS`, the RAG docstring).
- **Covered by neither, and `brand-grep.sh` still prints them:** 9 lines in
  three files. Two kinds:
  - dated-history comments (`src/accounts.py:582,584`, `src/shootgen.py:783`):
    harmless; either add a fragment to the rename allowlist with the reason, or
    reword them to "the old brand" and let them drop out of the count;
  - names a person or the code can meet: `src/instagram.py:486` (the Meta app
    is really called `ZeroPageFilms`; renaming the string without renaming the
    app would make the error message wrong -- allowlist it, or rename the app
    in Meta's dashboard first, Mike's call), `src/shootgen.py:927` and its
    docstring (`_flatten_zeropage_scenes`, a function name, plus a reference
    to `prompts/shotlist_prompt_zeropage.txt` which does not exist), and
    `src/shootgen.py:1688` (user-visible `--help` text).
- **Covered, but the reason has lapsed:** `app/auth.py:155-156` and
  `app/mcp_auth.py:75` are allowlisted as "infrastructure that keeps its name
  until its own step"; the apps were deleted on 2026-10-15, so these are now
  history comments and the allowlist entry's reason should say so (or the
  `mcp_auth` docstring should name `api.phantra.ai`).
- The task file's list is accurate: every one of the nine files does still
  contain the string. `scripts/brand-grep.sh` over the whole tree is the
  running count; this table is only the nine files it named.

Suggested next step (not done overnight, nothing renamed): one small PR that
renames `_flatten_zeropage_scenes` -> `_flatten_scene_shots`, fixes the two
stale prompt-file references and the `--client` help text, rewords the three
history comments, and adds `ZeroPageFilms` to the rename allowlist with
"the Meta app's registered name" as the reason.
