# 00 — Baseline, 2026-11-02

Branch `claude/qa-2026-11` off `origin/main` at `8ba89087` (Merge #534). Worktree
`.claude/worktrees/phantra-qa-competitive-8903e3`; the main checkout (`claude/sheet-gpt-image-25`,
Mike's uncommitted work in `app/`, `src/`, `CLAUDE.md`) was not touched.

## Live health (2026-11-02 16:13 UTC, curl from this Mac)

| URL | Status | Time |
|---|---|---|
| `https://api.phantra.ai/healthz` | 200 | 0.37 s |
| `https://phantra.ai/` | 200 | 0.39 s |
| `https://phantra.ai/studio` | 200 | 0.31 s |
| `https://api.phantra.ai/mcp` (no auth) | 401 | 0.15 s (expected) |
| `https://api.phantra.ai/mcp/claude` (no auth) | 401 | 0.15 s (expected) |
| `https://api.phantra.ai/api/me` (signed out) | 401 | 0.20 s (expected) |

## Connector workspaces and credits (before any agent ran)

| Listing | MCP connection | Workspace | Role | Plan | Available | Held |
|---|---|---|---|---|---|---|
| `/mcp/claude` (Claude listing, never renders) | `60190b15-…` | **5** "Phantra Review" (`zp-billing-test`) | member | none | **343** | 0 |
| `/mcp` (ChatGPT listing, CAN render) | `71f4353e-…` | **1** "Phantra AI" (`phantra`) — Mike's own | owner | none | **8,133** | 0 |
| stdio `phantra-ai` (studio server) | local | the bootstrap account (no `whoami` tool on this surface) | — | — | read in 04 | — |

Note for the agents and the report: the ChatGPT listing in this session acts **in Mike's own
workspace 1** and exposes `approve`, `generate_image` and every effect run tool. Agent D calls it
quote-only and reads; nothing that runs.

Credits after every agent finished: see the end of this file.

## Suites

Run once on `8ba89087`. Python: serial, exactly as CI (`python -m pytest tests/ -q`), with
`PYTHONPATH=<worktree>` and a plugin that drops the venv's editable finder (the venv's editable
install otherwise imports `src`/`app` from the main checkout, which holds Mike's uncommitted
edits). Web: a separate detached worktree of `origin/main` so the build's `.next` cannot collide
with Agent B's dev server.

(Results filled in below when the runs finish.)
