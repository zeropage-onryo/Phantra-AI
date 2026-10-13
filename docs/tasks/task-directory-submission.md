# Task — get Zeropage Studio listed in the Claude and ChatGPT directories

**From:** a cloud session, 2026-10-11. **For:** Claude Code, in this repo on Mike's Mac.
**Mike's call:** list in BOTH directories at once, no idea board on either.
**Read first:** `docs/directory/TWO_LISTINGS.md` (what was built and why), then
`docs/directory/SUBMISSION.md` (the older status table; TWO_LISTINGS wins where they differ).

## State right now

- PR #221 (`claude/directory-two-listings`, rebuilt on main 2026-10-11) is OPEN, NOT merged. It adds:
  - `/mcp` = the ChatGPT listing (renders through `approve`).
  - `/mcp/claude` = the Claude listing (no render; `quote` hands back `approve_url`).
  - No board tools, no `save_chat` on either listing.
  - A new `scene` tool reads a scene back. (`write_scene` creating scenes and the board's removal landed on main first, in #226.)
  - `llms.txt` rewritten.
  - `ZEROPAGE_MCP_RESOURCE` set to `https://api.zeropage.studio/mcp`.
- `api.zeropage.studio` already answers (healthz 200), but it still publishes the fly.dev resource until #221 deploys.
- Fly secrets are unknown from the cloud session. `ZEROPAGE_MCP_HOSTS` is the one that matters.
- The test account `zp-billing-test` (account 5, `deals4michael@gmail.com`) exists and is populated, but its user has NO password yet.
- The plugin repo `zeropage-onryo/phantra-claude-plugin` still has skills that call the old board tools (`board`, `pick`, `capture`, `save_chat`).

## Rules for this task

- Mike's standing rule: **no renders, stills or any generation unless he says so in chat.**
  Every check below that would spend credits stops and asks first.
- Never print a secret. `fly secrets list` shows names only, which is fine.
- Steps marked **MIKE** are his to do (accounts, dashboards, legal answers). Prepare them, then stop and say what's needed.
- Branch for any code change; never commit to `main`.

## Steps

### 0. Before merging #221

- [x] `ZEROPAGE_MCP_HOSTS` no longer has to name `api.zeropage.studio`: since 2026-10-11
  `mcp_mount.allowed_hosts()` always adds the host of `ZEROPAGE_MCP_RESOURCE` (fly.toml).
  The secret's other hosts still count. If it is `*`, the check is off anyway.
- [ ] Also confirm `STUDIO_URL` is the studio's public origin (`https://zeropage.studio`).
  - Done when: `quote`'s `approve_url` will point at a page that opens.

### 1. Merge and deploy

- [ ] **MIKE** merges PR #221. The push to `main` deploys Fly.
- [ ] After deploy, verify by running, not reading:
  - `curl https://api.zeropage.studio/.well-known/oauth-protected-resource/mcp` → `resource` is `https://api.zeropage.studio/mcp`.
  - Same for `/mcp/claude` → `resource` ends in `/mcp/claude`.
  - `POST https://api.zeropage.studio/mcp/claude/` with no token → 401, and `WWW-Authenticate` names the `/mcp/claude` document.
  - With the operator token (`ZEROPAGE_MCP_TOKEN`, from `.env`), `tools/list` on each path:
    - `/mcp/` operator → full server.
    - `/mcp/claude/` → exactly 8 tools (no `approve`, no `job`).
  - Done when: all four answer as above. If any is a 421, step 0 was wrong.

### 2. Re-add Mike's own connector

- [ ] **MIKE** removes the fly.dev Zero Page connector in claude.ai (Customize → Connectors) and adds `https://api.zeropage.studio/mcp/claude`.
  - Done when: in a fresh chat, the tool list shows `scene` and no `board`.
- [ ] Walk the Claude flow in that chat, with no spend:
  - `elements` → `write_scene` (new scene with a title, one element photo ref) → `scene` → `quote`.
  - Open `approve_url` in the browser; it must land on the scene in the studio.
  - Done when: the scene's Render card shows the same price as the quote. Do NOT press Render unless Mike says so.

### 3. Fix the plugin repo

- [ ] Clone `zeropage-onryo/phantra-claude-plugin` and list every skill that names a removed tool:
  `grep -rn "board\|pick\|capture\|save_chat\|archive\|shoot" skills/`
- [ ] Rewrite those skills around the new flow:
  - Projects: `projects` → `create_project`.
  - Scenes: `elements` → `write_scene` → `scene` → `quote`.
  - Render: on the ChatGPT listing, `approve` after the person's yes; on Claude, the `approve_url`.
- [ ] Branch, commit and open a PR.
  - Done when: `grep` finds no removed tool name, and the README names both URLs.

### 4. Test account (both directories require one)

- [ ] **MIKE** sets a password for the `zp-billing-test` user in `/studio/settings` (signed in as that user).
- [ ] Check the account holds at least:
  - one element with real photos;
  - one project;
  - one written scene (`write_scene` through the connector is fine, it spends nothing).
- [ ] Give the account enough credits for a reviewer to run one cheap ChatGPT render (LTX 2.3, ~87 credits). Ask Mike before granting.
  - Done when: signing in as that user shows all of the above, and `quote` shows `affordable: true`.

### 5. Inspector pass (both checklists ask for it)

- [ ] `npx @modelcontextprotocol/inspector`, connect to each URL through OAuth as the test account.
- [ ] Call every tool once with valid input, and once with a bad id. Confirm:
  - every success returns data;
  - every refusal is a readable message, never "Internal Server Error".
- [ ] Note anything odd in `docs/directory/TWO_LISTINGS.md` under a new "Inspector, <date>" heading.
  - Done when: every listed tool on both servers has been called and the notes are written.

### 6. Listing materials

- [x] Public docs page: confirm `https://api.zeropage.studio/llms.txt` serves the new text.
  A `zeropage.studio/connector` page on the Vercel site would be better. Draft it in `web/`, and ask Mike before publishing.
  *(2026-10-11: `llms.txt` serves the new text, and `https://zeropage.studio/connector` is live: PR #245, merged on Mike's word.)*
- [x] Privacy policy URL and support email: find the live ones on zeropage.studio and list them in TWO_LISTINGS.md.
  If either is missing, stop and tell Mike.
  *(2026-10-11: both are live and listed under "Listing materials". Neither is missing, but the policy does not mention the connector; Mike has been told.)*
- [ ] Write the listing text for both, from the rules in TWO_LISTINGS.md:
  - name, tagline, description;
  - 3–5 example prompts for ChatGPT;
  - use cases for Claude.
  - The ChatGPT text must not mention prices, plans or upgrades.
  - Done when: the text is in TWO_LISTINGS.md for Mike to approve.

### 7. Submit

- [ ] **MIKE**, OpenAI:
  - verify the organization on platform.openai.com (Owner role);
  - pick a global (not EU) data-residency project;
  - submit `https://api.zeropage.studio/mcp` with the test credentials, the privacy URL, support contact and the example prompts.
- [ ] **MIKE**, Anthropic: submit `https://api.zeropage.studio/mcp/claude` through the MCP directory form.
  For the AI-media acknowledgment, answer that the connector writes and prices scenes and that rendering happens in the studio after the person approves it there.
- [ ] Record both submission dates and any review IDs in TWO_LISTINGS.md.

### 8. After submitting

- [ ] Watch for reviewer feedback. Fix on a branch, and re-run steps 1 and 5 for anything touched.
- [ ] Once listed, set `ZEROPAGE_CLAUDE_DIRECTORY_URL` (Fly secret) so the studio's "Connect to Claude" panel becomes one button.

## Done means

Both submissions are in, and:

- both URLs pass the Inspector as the test account;
- Mike's own connector works at the new address;
- the plugin repo no longer names a removed tool;
- TWO_LISTINGS.md records what was submitted and when.
