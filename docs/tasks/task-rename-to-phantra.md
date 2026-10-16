# Task — Rename Zero Page to Phantra, everywhere, in priority order

**From:** claude.ai chat, 2026-10-13 (rename scope + this list). **For:** Claude Code, in this repo on Mike's Mac.
**Mike's call:**
- The product is now **Phantra**. Domain **phantra.ai** (bought 2026-10-13). Instagram handle already changed.
- The brand name in copy is **"Phantra"** (not "Phantra AI", not "Phantra Studio"): page titles read `"<Page> — Phantra"`, the wordmark reads `phantra`.
- Logo: **text wordmark only for now.** The red/white "ZP" mark is retired; no new mark until Mike supplies one. Do NOT generate a logo or any image.
- Wipe every trace of zeropage / Zero Page / ZPF / ZP, user-facing first, internal last.
- **There are no users yet** (Mike, 2026-10-13). So: no transition period — no second accepted OAuth audience, no old-cookie fallback, no old-env-var fallback, no user announcement. Rename things outright.
- **Start fresh on storage and the API app:** a NEW R2 bucket that keeps ONLY the `m/`, `t/` and `site/` prefixes from the old one (most of those are the UI's pictures and videos); `renders/`, `props/`, `soul-training/` are left behind. A NEW Fly app replaces `zeropage-studio`. Old bucket and old apps are deleted only after the new ones are verified.
- zeropage.studio stays owned and 308-redirects to phantra.ai page-for-page for at least a year (search engines).
**Read first:** `CLAUDE.md` (Commands, "MEDIA IS MULTI-TENANT", the MCP and sign-in sections), `docs/tasks/task-remove-brand-labels.md`, `ops/r2-setup.md`.

## State right now (checked 2026-10-13 ~13:50 ET; R2 lines updated 14:40 ET)
- Repo: `main` at `0982e70` (PR #293). The main checkout is on `claude/element-sheet-is-the-element` with 8 uncommitted files from another session — leave them alone (see Step 0).
- Footprint: 416 tracked files, ~3,000 matches for `zero[ _.-]?page|zpf|ZPF|\bZP\b`. By area (files / lines): tests 129/1172, docs 78/691 (+84 in CLAUDE.md), src 48/265, web 67/192, app 38/150, ops+root+.github+.claude ~50/~290.
- **DNS:** phantra.ai's nameservers are Cloudflare (`iris` / `yoxall.ns.cloudflare.com`, registry updated ~12:55 ET), zone in Mike's Cloudflare account (the same account as the R2 bucket). `phantra.ai` → Vercel, 200; `www.phantra.ai` → 308 to apex; both records DNS-only. Cloudflare Email Routing records (MX/SPF/DKIM) are on the apex; routing rules were being set up by Mike. Imported wildcard `*.phantra.ai` A records were sending `api`/`media` to Vercel (TLS failure) — Mike is deleting them.
- **Email sending:** Supabase sends auth mail through **Resend** (`smtp.resend.com`). phantra.ai not yet verified in Resend as of this writing.
- Live old stack: `https://zeropage.studio` 200, `https://api.zeropage.studio/healthz` 200.
- Hosts in code: zeropage.studio (167), api.zeropage.studio (94), zeropage-studio.fly.dev (76), zpf-web.vercel.app (27), zeropage-web.fly.dev (8), media.zeropage.studio (7), reply@/noreply@/support@zeropage.studio.
- 44 `ZEROPAGE_*` env vars (`git grep -ohE '\bZEROPAGE_[A-Z0-9_]+' | sort -u`), read directly with `os.environ.get` in many modules.
- Cookies/salts: session cookie `zp_session`; itsdangerous salts `zp-session`, `zp-handoff`, `zp-upload`; ~35 `zpf.*` / `zp.*` / `zp-*` localStorage keys in `web/src` and `app/static`.
- MCP server name `build_server(name="zeropage-studio")` (`src/mcp_server.py` ~4706), instructions open "Zeropage Studio:". OAuth audience = `ZEROPAGE_MCP_RESOURCE` (`https://api.zeropage.studio/mcp`).
- **R2 today:** bucket `zeropageclips` (729.5 MB, public access on), top-level prefixes `m/`, `t/`, `site/`, `renders/`, `props/`, `soul-training/`. Env names `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE_URL` (on the Mac the base is the bucket's `pub-….r2.dev` address; Fly's value unknown). `ops/r2-setup.md`'s `zeropage-media` is only an example name.
- **Fly today:** apps `zeropage-studio` (the API; volume `zeropage_data` mounted at `/app/data`; Stripe webhook points at `https://zeropage-studio.fly.dev/billing/webhook`; deployed by `.github/workflows/fly-deploy.yml`) and `zeropage-web` (scaled to zero, unused since the site moved to Vercel). Fly secret VALUES cannot be read back — only names (`fly secrets list`).
- Data: account slug `zeropage` (`src/accounts.py` seed, `RESERVED_SLUGS`), brand values `"zeropage"` on rows (scoped for removal in `docs/tasks/task-remove-brand-labels.md`). Media keys are by account ID (`m/1/...`), not slug.
- Plugin repos (public, `can_push` true):
  - **Claude:** `zeropage-onryo/zeropage-studio-plugin` (27 files, ~50 hits): `.claude-plugin/plugin.json`, `.mcp.json` (server key `zeropage-studio` → `https://api.zeropage.studio/mcp/claude`), README, skill folder `skills/zeropage-use/`, one-line mentions in 22 SKILL.md files, LICENSE. Main repo references it as `../zeropage-studio-plugin` (4×) and by URL (11×).
  - **ChatGPT:** `zeropage-onryo/zeropage-studio-chatgpt-plugin` (43 files, ~70 hits): `plugin.json` (name, homepage/websiteURL, repository, supportURL, privacy/terms, demo URL), `mcp.json` (→ `https://api.zeropage.studio/mcp`), README, `skills/setup`, `skills/zeropage-use/`, `scripts/mcp-tools.txt`, zip name `zeropage-studio-chatgpt-1.0.0.zip`, `assets/icon*.png` / `logo*.png` (likely the ZP mark).
  - Submission state unknown: check `docs/directory/TWO_LISTINGS.md`. Anthropic's listing slug is **permanent once published** (`docs/directory/REQUIREMENTS.md` C27).
- Other old repos: `zpf-web` (public), `zpf-web-5t` (private), `Zero-Page-Film-Studio` (public). `Voice-bot` is unrelated.
- Legal copy: privacy page says "operated by Michael Massaad, trading as Zero Page Films".
- `CLAUDE.md` is stale in one spot: `langgraph.json` registers the graph as `orchestrator`, not `zeropage`.

## Rules for this task
- Branch from `origin/main` (`claude/rename-phantra-<phase>`); never commit to `main`. One PR per phase. Mike merges.
- No renders, stills, effects or any generation. Screenshots of pages are fine.
- Never print a secret value; refer to secrets by name only. Moving a secret from `.env` to Fly is done by piping, never by echoing it.
- **Never blind find-and-replace.** `zeropage` is also a DB name, an account slug, column values, env var names, app and bucket names. Change each class in its own phase.
- Nothing is deleted (bucket, Fly app, rows) until its replacement is verified working, and never without Mike's yes in chat.
- Anything that migrates live data, changes Fly secrets, or touches Stripe/Supabase/Cloudflare live config: report first, then **ask Mike** before acting.
- Run `venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`, and `cd web && npm test && npm run build` before each PR. Verify user-facing changes in a browser.

---

## What is left for Mike (2026-10-15)

Everything a visitor, an email or the connectors see says Phantra, the brand labels are gone and
account 1 is `phantra`. What remains is dashboards and deletions, each Mike's:

1. [x] **Cloudflare Email Routing** for `support@phantra.ai` (checked 2026-10-15: phantra.ai's MX records are Cloudflare's three routes and its one SPF record includes Cloudflare's; a test mail to support@ is still the real proof).
2. [ ] **Stripe dashboard:** business name, statement descriptor, support email, Checkout branding.
3. [ ] **Google Cloud OAuth consent screen:** app name Phantra, phantra.ai links, no ZP logo.
4. [x] **Old Fly apps:** deleted (checked 2026-10-15: `fly apps list` shows `phantra-api` only).
5. [ ] **Old R2 bucket `zeropageclips`:** its 67 objects left behind (`renders/`, `soul-training/`,
   `props/`) were never copied; decide whether any is wanted, then delete the bucket and revoke its
   old API token (Cloudflare).
6. [ ] **Old public repos** (checked 2026-10-15): `zpf-web` is now `phantra-web` (public); `zpf-web-5t` is private; **`Zero-Page-Film-Studio` is still public and not archived** -- archive, make private or delete.
7. [ ] **Handles and legal:** claim `phantra` handles; fictitious-name filing; the privacy page's
   trading line.
8. [ ] **Icon** for the ChatGPT plugin and the directory listings.

## MIKE — now (no code needed)
- [x] Vercel: `phantra.ai` + `www.phantra.ai` added; www → 308 to apex. (done 12:03 ET)
- [x] DNS moved to Cloudflare, records DNS-only. (nameservers switched ~12:55 ET)
- [x] Deleted the two `*.phantra.ai` A records (verified 14:40 ET).
- [x] Wait for Cloudflare to show the zone **Active** (Overview → "Check nameservers now"). (verified 2026-10-14: Cloudflare serves the zone)
- [ ] **Email Routing:** Destination addresses → add `mikemassaad@gmail.com` → click the verify link; Routing rules → create `support` → send to that Gmail. Catch-all off.
  - Done when: a mail from another account to support@phantra.ai lands in Gmail.
- [x] **Resend:** Domains → add `phantra.ai`; put its records (on `send.phantra.ai` and `resend._domainkey`) in Cloudflare DNS, DNS-only; add `_dmarc` TXT `v=DMARC1; p=none; rua=mailto:support@phantra.ai`; Verify. Never a second `v=spf1` on the apex. (verified 2026-10-14: DKIM on `resend._domainkey`, `_dmarc` live, a real reset email passes DKIM and DMARC)
- [x] **Google Search Console:** add Domain property `phantra.ai` (TXT in Cloudflare). No Change of Address yet. (verified 2026-10-14)
- [x] **New R2 bucket `phantra-media`** created; token `phantra-migration` (Object Read & Write on BOTH buckets) is in `.env` as `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`. Fly still has the OLD key pair. `media.phantra.ai` is connected to `phantra-media` (verified: `https://media.phantra.ai/site/mascot/v1/128/ferryman-storm-own-awake.webp` → 200 image/webp).
- [x] **Copy done (2026-10-13 14:40 ET, from claude.ai via the Mac):** server-side copy of `m/` (431 objs, 519.2 MB), `t/` (249, 6.4 MB), `site/` (1,499, 68.1 MB) = 2,179 objects / 593.6 MB into `phantra-media`; verified 0 missing, 0 size mismatches, 0 extras; content types preserved. Left behind in `zeropageclips` (untouched, still 2,246 objects): `renders/` (56, 121.2 MB), `soul-training/` (8, 14.5 MB), `props/` (3, 0.1 MB).
- [ ] **Handles:** claim `phantra` / `phantra.ai` on TikTok, YouTube, X, Threads, LinkedIn page, Discord, Reddit; re-claim the freed `@zeropagefilms` (Instagram) and `@zeropage` (TikTok) with placeholders.
- [ ] **Legal (not legal advice — confirm):** Florida Sunbiz fictitious name "Phantra"; USPTO search for "Phantra". Tell Claude the trading line for the privacy page.
- [ ] **Stripe dashboard:** public business name `Phantra`, statement descriptor (e.g. `PHANTRA.AI`), support email `support@phantra.ai`, Checkout/portal branding (no ZP mark).
- [x] **Discord developer portal:** rename the OAuth app to Phantra, remove the ZP icon. (verified 2026-10-14: Discord's public app record reads "Phantra AI", no icon)
- [ ] **Hold** the Claude and ChatGPT directory submissions until Phase 4 is done.
- [ ] **Decide the old repos:** `zpf-web` and `Zero-Page-Film-Studio` are public with the old name — make private/archive, or delete.
- [ ] **New icon:** supply a Phantra image for the ChatGPT plugin's `assets/` and the directory icon.

## MIKE — on Phase 2 day
- [x] **Supabase → Auth → URL Configuration:** Site URL `https://phantra.ai`; redirect URLs `https://phantra.ai/**`, `https://api.phantra.ai/**` (remove the zeropage ones once Phase 2 is verified). Auth → SMTP: sender `reply@phantra.ai`, name `Phantra` (Claude can apply templates via `ops/supabase_auth_email.py` with `SUPABASE_ACCESS_TOKEN`; the URL fields are yours). (verified 2026-10-14: a reset email came from Phantra <reply.ai> and its link landed on phantra.ai)
- [ ] **Google Cloud → OAuth consent screen:** app name `Phantra`, homepage/privacy/terms → phantra.ai, authorized domain `phantra.ai`, ZP logo removed. Redirect URIs (Supabase) don't change.
- [ ] **Optional:** Supabase custom domain add-on (`auth.phantra.ai`) so Google's sign-in screen shows your domain. Paid.

---

## Steps for Claude

### 0. Set up
- [ ] Do NOT switch branches in the main checkout (another session's uncommitted work). Use a worktree: `git fetch origin && git worktree add ../phantra-rename -b claude/rename-phantra-1-copy origin/main`; do every phase there, new branch per phase off `origin/main`.
- [ ] Phase 1 needs nothing from Mike — start it now. Before Phase 2, check `https://phantra.ai` resolves and the zone is Active; if not, open the Phase 1 PR and tell Mike. Mike may hold the Phase 1 merge so the name and domain switch the same day.
- [ ] Add `scripts/brand-grep.sh`: `git grep -nIiE 'zero[ _.-]?page|\bzpf\b|\bzp\b|zeropage'` minus the lines in `docs/tasks/rename-allowlist.txt` (start empty; each later phase adds only what it deliberately keeps, with a reason).
  - Done when: it prints the current count (~3,000) and exits 0.

### 1. User-facing copy and brand (no infra dependency)
- [ ] **Web metadata:** `web/src/app/layout.tsx` (TITLE, template `"%s — Phantra"`, siteName), `web/src/lib/page-meta.ts`, `web/src/app/opengraph-image.tsx`, `web/src/landing-pages/og.tsx`, `route.tsx`, `pages.ts`, all 22 `web/src/landing-pages/entries/*`.
- [ ] **Wordmark:** `web/src/components/wordmark.tsx` → text `phantra`, aria-label "Phantra home". Remove the ZP image mark from header, footer, favicon and OG. A plain letter "P" SVG favicon only if Mike approves it in chat; otherwise the browser default. Delete `web/public/brand/zp_*` once unreferenced.
- [ ] **Pages and components:** every "Zero Page" / "Zeropage" / "ZPF" string in `web/src` (38 files incl. privacy, terms, faq, connector, page.tsx, hero-reel, hero-nimbus, cta-section, site-footer, legal-page, plan-cards, the studio header "Zero Page Studio", flow-workspace, elements page, connect-claude, mentions). Privacy/terms trading line: Mike's answer, else "Michael Massaad, trading as Phantra", flagged in the PR.
- [ ] **Legacy FastAPI pages:** `app/templates/` (signin, landing, privacy, oauth_consent, upload, base, zpf, _rail, accounts, dev_studio, dev pages), brand labels in `app/main.py` (`"Zero Page Films"`) and `app/static/zpf/analytics.js`.
- [ ] **SEO surface:** `app/seo.py` (robots, llms.txt, JSON-LD), web sitemap/robots.
- [ ] **MCP identity:** `build_server(name=...)` → `"phantra"`; STUDIO/LISTED instructions, `TITLES` / `DESCRIPTIONS` / `LISTED_DESCRIPTIONS` → Phantra; update the wording-screen test.
- [ ] **Download file names:** `app/api.py` ~1688 and `src/mcp_server.py` ~2690 (`zeropage-<label>-<id>.<ext>`), `app/main.py` ~1047 (`zeropage-<what>.<fmt>`), and any cut-export names → `phantra-…`.
  - Done when: a Library download and a connector `share_link` save `phantra-….mp4|png`.
- [ ] **Stripe products:** `ops/stripe_setup.py` names → `f"Phantra {name}"`, ledger description. Don't run against live Stripe — ask Mike.
- [ ] **Email templates:** `docs/SUPABASE_EMAIL_TEMPLATES.md`, `ops/supabase_auth_email.py` → Phantra, `reply@phantra.ai`.
- [ ] **Pricing export:** re-run `python -m src.pricing export` if `web/src/content/pricing.json` carries the name.
- [ ] **Directory listing copy:** `docs/directory/PORTAL_PASTE.md`, `SUBMISSION.md`, `TWO_LISTINGS.md`.
- [ ] Update the tests that assert these strings.
- Done when: `scripts/brand-grep.sh -- web/src app/templates app/seo.py` finds no display-name hits; build passes; landing, /pricing, /faq, /privacy, /terms, /connector, /signin and the studio header show "Phantra" at desktop and 390px.

### 2. Domains, config and the new bucket (needs the zone Active)
Branch `claude/rename-phantra-2-domains`.
- [ ] **Code defaults** → phantra.ai: `web/src/lib/site-url.ts`, `web/next.config.ts`, `web/.env.example`, `.env.example`, `fly.toml` (`DIRECTOR_FRONTEND_URL`, `ZEROPAGE_MCP_RESOURCE` → `https://api.phantra.ai/mcp`), `ops/stripe_setup.py` return URL, support email (`web/src/lib/site.ts`), `app/seo.py`, `ops/register-claude-desktop.command`, `ops/claude-desktop-mcp.json`, `web/README.md`, `START_SERVER.md`. No old-host fallbacks (no users).
- [ ] **Redirects:** `web/next.config.ts` `redirects()` — host-matched permanent redirects `zeropage.studio` / `www.zeropage.studio` `/:path*` → `https://phantra.ai/:path*` (query kept). Or Mike sets it per domain in Vercel (308). Either way, verify with curl after deploy.
- [ ] **api.phantra.ai on the CURRENT app for now:** `fly certs add api.phantra.ai -a zeropage-studio` (skip if Mike already did); Mike adds CNAME `api` → `zeropage-studio.fly.dev`, DNS-only; `fly certs check` until ready. (Phase 7 moves it to the new app.)
- [ ] **Fly env (ask Mike first):** `FRONTEND_ORIGINS=https://phantra.ai`, `STUDIO_URL=https://phantra.ai` (the ORIGIN only: with `/studio` on it, a sign-in with no return address lands on `/studio/studio`, a 404 -- found 2026-10-13), `ZEROPAGE_MCP_RESOURCE=https://api.phantra.ai/mcp`, `ZEROPAGE_UPLOAD_ORIGIN`, `ZEROPAGE_SIGNUP_URL`, `ZEROPAGE_PRICING_URL`, `BILLING_RETURN_URL` → phantra.ai values.
- [ ] **Vercel env:** `NEXT_PUBLIC_SITE_URL=https://phantra.ai`, `NEXT_PUBLIC_AUTH_ORIGIN` / `API_UPSTREAM=https://api.phantra.ai`. Redeploy.
- [x] **New bucket — copy:** DONE (see the MIKE section). Do not re-copy. If new files were written to `zeropageclips` under `m/`/`t/`/`site/` after 2026-10-13 14:40 ET (any studio use before the switch below), copy just those before switching (compare listings by key+size).
- [x] `media.phantra.ai` connected to `phantra-media` (done by Mike, verified 200).
- [ ] **Switch the app to the new bucket:** `R2_BUCKET=phantra-media`, `R2_PUBLIC_BASE_URL=https://media.phantra.ai` in `.env` and Fly secrets (ask Mike first); update hard-coded media hosts (`web/src/content/landing-media.ts`, `web/next.config.ts` image domains, CSP). Remove old bases (`pub-….r2.dev`, `media.zeropage.studio`) from any allow-lists in code.
- [ ] **Stored addresses (live DB):** read-only report of rows whose text holds the old bases (`pub-62d6d70e….r2.dev`, `media.zeropage.studio`) or a key outside `m/`/`t/`/`site/` (`renders/…`, `props/…`, `soul-training/…`) — `shoot_concepts.shots_json`, `generated_assets`, `cut_media`, `timelines.export_url`, `videos`, element photo lists. Then, with Mike's yes: rewrite old-base URLs for kept prefixes to `https://media.phantra.ai/<key>`; soft-delete (`deleted_at`) wall rows whose only file was left behind; list anything else for Mike.
- [ ] **Supabase email:** `python -m ops.supabase_auth_email report`, `apply --templates --dry-run`, ask Mike, apply.
- [ ] **Stripe:** in the Stripe dashboard (MIKE), point the webhook endpoint at `https://api.phantra.ai/billing/webhook`; if Stripe issues a new signing secret, Mike sets it on Fly by name (`STRIPE_WEBHOOK_SECRET`).
- Done when: phantra.ai, /pricing, /studio load; `curl -sI https://zeropage.studio/faq` → 308 to `https://phantra.ai/faq`; `curl https://api.phantra.ai/healthz` 200; `/.well-known/oauth-protected-resource` on api.phantra.ai names `https://api.phantra.ai/mcp`; Google, Discord and email sign-in complete on phantra.ai in a browser; a reset email arrives from reply@phantra.ai saying Phantra; the Library shows images from `media.phantra.ai`; a Stripe test checkout returns to phantra.ai.

### 3. MIKE checkpoint
- [x] Mike merges Phases 1–2 and does the Phase-2-day dashboard steps. Search Console → zeropage.studio → **Change of Address** → phantra.ai; submit `https://phantra.ai/sitemap.xml`. (verified 2026-10-14: the zeropage.studio property says "currently moving to phantra.ai"; `https://phantra.ai/sitemap.xml` submitted, read Success, 29 pages)

### 4. Plugin repos and listing assets
#### 4a. The two plugin repos (after Phase 2 is live)
- [x] **Check submission state first:** `docs/directory/TWO_LISTINGS.md`. If either listing is submitted or published, stop and tell Mike.
- [x] **MIKE renames in GitHub:** `zeropage-studio-plugin` → `phantra-claude-plugin`, `zeropage-studio-chatgpt-plugin` → `phantra-chatgpt-plugin`. Then `git remote set-url` in each clone and rename local folders (`../zeropage-studio-plugin` → `../phantra-claude-plugin`).
- [x] **Claude plugin** (`phantra-claude-plugin`): `.claude-plugin/plugin.json` name `phantra`, Phantra copy, homepage `https://phantra.ai`, repository URL, version bump; `.mcp.json` key `phantra` → `https://api.phantra.ai/mcp/claude`; `git mv skills/zeropage-use skills/phantra-use` + frontmatter + references; README, SKILL.md mentions, LICENSE holder (Mike's trading name).
- [x] **ChatGPT plugin** (`phantra-chatgpt-plugin`): `plugin.json` name `phantra`, author/homepage/websiteURL → phantra.ai (`/mcp` if that page exists, else `/connector`), repository + supportURL → new repo, privacy/terms → phantra.ai, demo URL → `https://phantra.ai/connector#demo-TO-RECORD`, version bump; `mcp.json` key `phantra` → `https://api.phantra.ai/mcp`; `skills/phantra-use` rename + references; `skills/setup`; `scripts/mcp-tools.txt`; zip name `phantra-chatgpt-<version>.zip`; replace `assets/icon*.png` / `logo*.png` with Mike's image (no generation; don't ship the ZP mark); run `python scripts/check.py`.
- [x] **Main repo:** replace the plugin URLs/paths in `docs/directory/*`, `docs/tasks/*`, `CLAUDE.md`.
- [ ] **Verify:** Claude Code `/plugin` install from the renamed repo → server `phantra`, tools listed, `phantra-use` loads; ChatGPT developer mode → add `https://api.phantra.ai/mcp`, connects, lists tools. No generate/approve calls.
  - Done when: `git grep -niE 'zero[ _.-]?page|zpf'` in both plugin repos is empty and both installs work.
- [ ] **Old repos:** apply Mike's decision on `zpf-web`, `Zero-Page-Film-Studio`, `zpf-web-5t`.
- As done 2026-10-13: both repos renamed and their rename PRs merged (Claude plugin v0.4.0, ChatGPT plugin v1.1.0); local folders are `../phantra-claude-plugin` and `../phantra-chatgpt-plugin`. Still open: the ChatGPT plugin's `assets/` are the old ZP mark (needs Mike's image); the Claude plugin's PR #5 (name it `phantra-skills`?) is Mike's call; the install checks below.
#### 4b. Listing assets
- [x] Remove `docs/directory/icon/zeropage-studio-icon-*.png` (Mike supplies the new icon); retake `docs/directory/screens` against the renamed live site.

### 5. Internal identifiers (straight rename — no fallbacks)
Branch `claude/rename-phantra-5-internal`.
- [ ] **Env vars:** rename all 44 `ZEROPAGE_*` → `PHANTRA_*` in code, `.env.example`, `fly.toml`, CI, docs, tests. Then (ask Mike) rename them in `.env` and on Fly (set the new names from the current values by piping `.env`, unset the old) and deploy.
- [ ] **Session cookie:** `zp_session` → `phantra_session`; salts `zp-session` / `zp-handoff` / `zp-upload` → `phantra-…`. Everyone (Mike) signs in again once — fine with no users. Note in the PR that open handoff/upload links break at deploy.
- [ ] **localStorage keys:** `zpf.*` / `zp.*` / `zp-*` → `phantra.*` (no migration needed; Mike's browser just loses its saved UI prefs once).
- [ ] **Static/template names:** `app/static/zpf/` → `app/static/studio/`, `zpf.html` → `studio.html`, `zpf-` CSS prefixes not shared with `web/`, `PHANTRA_API_BASE` → `PHANTRA_API_BASE`.
- [ ] **Containers/CI:** `docker-compose.yml` and `.github/workflows/ci.yml` db/user `zeropage` → `phantra`; `Dockerfile` `/etc/cron.d/phantra`, supervisor `zeropage.conf` → `phantra`.
- [ ] **Local DB default:** `postgresql://localhost/zeropage` → `phantra` (`rag.DEFAULT_DB_URL`, `db.DEFAULT_DSN`); ask Mike before `ALTER DATABASE zeropage RENAME TO phantra` on his Mac.
- [x] **Claude Desktop / Code:** MCP entry `zeropage` → `phantra` in `ops/claude-desktop-mcp.json` and the register script (removing the old entry); `.claude/skills/zp-*` → `phantra-*`; `docs/CLAUDE_MODS.md`. (2026-10-14: the entry is `phantra-ai`, Mike's call, PR #317; Desktop re-registered and checked)
- [ ] **Python package:** `pyproject.toml` name `video-pipeline` → `phantra`; `pip install -e .`.
- [ ] **Tests:** update the ~1,170 lines carrying the name.
- Done when: pytest + ruff + web tests green; a Fly deploy with only `PHANTRA_*` serves; sign-in works with the new cookie.

### 6. Data labels and account slug (live data — report first, ask Mike before every write)
- [x] **Brand labels:** don't rename `"zeropage"` brand values; run `docs/tasks/task-remove-brand-labels.md` instead. (DONE 2026-10-15: the labels, columns and tables are gone.) If not now, report remaining counts and allowlist them.
- [x] **Account slug:** (RUN on live 2026-10-15 on Mike's yes: `phantra` / "Phantra AI", 224 RAG rows moved) `ops/rename_account_slug.py --from zeropage --to phantra [--write]`: `accounts.slug`, `RESERVED_SLUGS`, seed, `rag_documents.project`, `channels` / `hold_queue.channel`, `brand` cookie handling. Media keys are by account id — nothing in R2 moves.
- Done when: `select slug from accounts` shows `phantra`; Mike signs in to his workspace; `/api/me` shows it; tests green.

### 7. New Fly app (replaces `zeropage-studio`)
Branch `claude/rename-phantra-7-fly`. Do this after Phase 5 (so the app boots on `PHANTRA_*`).
- [ ] `fly secrets list -a zeropage-studio` → the list of NAMES. Compare with `.env`; give Mike the names that `.env` doesn't have (he must supply those values — Fly can't show them).
- [ ] `fly apps create phantra-api` (if taken, ask Mike for a name); `fly volumes create phantra_data -a phantra-api -r <same region as zeropage_data> -s <same size>`.
- [ ] `fly.toml`: `app = 'phantra-api'`, mount `source = 'phantra_data'`. Set secrets on `phantra-api` from `.env` by piping (never echo), plus Mike's extras.
- [ ] **Copy the volume data:** from the old machine, `fly ssh console -a zeropage-studio -C "tar czf /tmp/data.tgz -C /app data"`, `fly ssh sftp get /tmp/data.tgz`, then put and extract it on a `phantra-api` machine (`fly ssh sftp shell` → put; `tar xzf -C /app`). Report the file counts before and after.
- [ ] `fly deploy -a phantra-api`; `curl https://phantra-api.fly.dev/healthz` → 200.
- [ ] `fly certs add api.phantra.ai -a phantra-api`; **MIKE** changes the `api` CNAME to `phantra-api.fly.dev` (DNS-only); `fly certs check` ready; `curl https://api.phantra.ai/healthz` 200 from the new app (`fly logs -a phantra-api` shows the hit).
- [ ] **Deploy pipeline:** `.github/workflows/fly-deploy.yml` → `-a phantra-api`; **MIKE** creates a deploy token for `phantra-api` (`fly tokens create deploy -a phantra-api`) and replaces the `FLY_API_TOKEN` repo secret.
- [ ] Re-run Phase 2's "Done when" checks against the new app (sign-in, reset email, Library, Stripe test checkout, connector install).
- [x] After a week of working: **ask Mike**, then `fly apps destroy zeropage-web` and `fly apps destroy zeropage-studio`; Mike deletes the old `zeropageclips` bucket (Cloudflare → R2 → delete) and revokes its old API token. (done early on Mike's word, 2026-10-15: both Fly apps destroyed after checking api.phantra.ai is served by `phantra-api`, the Stripe webhook is `https://api.phantra.ai/billing/webhook` and the volume counts (old 244 files / 181 MB, new 255 / 183 MB); Mike deleted the `zeropageclips` bucket (R2 answers NoSuchBucket) and the `api.zeropage.studio` CNAME)

### 8. Other infrastructure names (Mike's call each)
- [ ] **GitHub org** `zeropage-onryo` → e.g. `phantra-ai` (MIKE). Then fix the Vercel git link, the deploy workflow, `git remote set-url` in the main repo and both plugin clones, plugin `repository` / `supportURL`, doc links. (2026-10-14: `zeropage-onryo` is a personal ACCOUNT, not an org, and keeps its name for now; the main repo is `Phantra-AI`, the plugin repos keep `phantra-claude-plugin` / `phantra-chatgpt-plugin`, Mike's call) (2026-10-14: `zeropage-onryo` is a personal ACCOUNT, not an org, and keeps its name for now; the main repo is `Phantra-AI` and the plugin repos keep `phantra-claude-plugin` / `phantra-chatgpt-plugin`, Mike's call)
- [x] **Vercel project** `zpf-web` → `phantra-web` (MIKE); nothing may point at `zpf-web.vercel.app`. (2026-10-14: the project is `phantra-web`)

### 9. Docs, repo folder, final sweep
- [ ] **Rewrite `CLAUDE.md` to describe the product as it is now** (Mike, 2026-10-13: "update the claude.md file to what the current AI production studio is, I believe it's out of date"). Not a find-and-replace: the Overview still opens "An AI pre-production studio for Zero Page Films (a one-person brand)" and most of Architecture is dated history (the idea board, the nightly walk, Runway/Higgsfield/Veo renderers, brands, the vanilla `/ui`) that later blocks say no longer applies. Write a current Overview (Phantra: an AI production studio — Create, projects, the Render card, Library, the editor, the connector on `/mcp` and `/mcp/claude`, credits and plans), keep Commands and the conventions that still hold, move superseded history to `docs/HISTORY.md` with one pointer line, and fix "Where the project stands" from the live database. Show Mike the outline before rewriting.
- [ ] **Living docs:** `CLAUDE.md` (also fix the `langgraph.json` note, and describe the new bucket/app names), `README.md`, `START_SERVER.md`, `ops/r2-setup.md`, ARCHITECTURE, BILLING, RUNBOOK, BACKLOG, ROLLOUT, directory docs.
- [ ] **Dated history docs** (`docs/tasks/HANDOFF-*`, dated task docs, `claude/*.md`): default is one header line, "Phantra was named Zero Page until 2026-10-13."; ask Mike if he wants them rewritten.
- [ ] **Repo folder:** turn `rename-to-zeropage-studio.command` into `rename-to-phantra.command` (NEW_NAME="Phantra"), delete the old one; Mike runs it.
- [ ] Run `scripts/brand-grep.sh`.
- Done when: it prints only allowlisted lines, each with a reason (the zeropage.studio redirect rule, dated history headers).

## Done means
- A visitor, a signed-in user, an email, a Stripe receipt, the Google/Discord sign-in screens and the Claude/ChatGPT connectors all say **Phantra** at **phantra.ai**; no ZP mark anywhere.
- zeropage.studio URLs 308 to the same page on phantra.ai.
- Media is served from the `phantra-media` bucket at `media.phantra.ai`, holding only `m/`, `t/`, `site/`; the API runs on the `phantra-api` Fly app; the old bucket and apps are deleted.
- Code, config, env vars, cookies, storage keys, tests and living docs carry no zeropage name; `scripts/brand-grep.sh` matches only the allowlist.
- Tests, ruff, web build and CI green; Search Console Change of Address submitted; directory submissions can go ahead.
