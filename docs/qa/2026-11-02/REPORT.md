# QA + competitive review, 2026-11-02 — the report

Reports only: no product code was changed. Branch `claude/qa-2026-11` (off `origin/main`
`8ba89087`). Seven agents' files in this folder carry the evidence; every line below names the
file and finding id it comes from.

| File | What | Findings |
|---|---|---|
| [`00-baseline.md`](00-baseline.md) | live health, connector workspaces and credits, suite results | — |
| [`01-public-ui.md`](01-public-ui.md) | public site, 46 pages × 3 widths, axe, weight, consistency, critique | P1–P21: 0 blocker, 5 major, 10 minor, 6 cosmetic |
| [`02-studio-ui.md`](02-studio-ui.md) | studio signed in (throwaway DB), 33 routes × 3 widths, flows, timings | T1–T20: 0 blocker, 6 major, 9 minor, 5 cosmetic |
| [`03-backend-e2e.md`](03-backend-e2e.md) + [`e2e_routes.py`](e2e_routes.py) + [`openapi.json`](openapi.json) | 332 routes: auth, tenancy, bad input, ledger, jobs, Stripe | E1–E12: 2 major, 5 minor, 5 cosmetic; 0 × 500; ledger PASS |
| [`04-connector.md`](04-connector.md) | every tool on `/mcp/claude`, `/mcp`, stdio `phantra-ai`, quote-only | K1–K13: 2 major, 3 minor, 6 cosmetic, 2 info |
| [`05-live-render.md`](05-live-render.md) | the gated real render | **not run** (waiting on Mike) |
| [`06-competitors.md`](06-competitors.md) (+ `06a`, `06b`) | Phantra vs Higgsfield, Runway, LTX Studio, Krea, invideo, Magnific | F1–F6 for Phantra |

**Spend: zero.** No priced button was clicked, nothing was approved, no media was generated.
Credits before → after: workspace 5 (`/mcp/claude`) **343 → 343**, workspace 1 (`/mcp`, Mike's)
**8,133 → 8,133**, 0 held on both (00, 04); the throwaway studio account 500 → 500 (02); the
throwaway backend accounts only moved inside the stubbed ledger test, as designed (03).

**Suites on `8ba89087`** (00): ruff clean; web `node --test` 439/439, typecheck and build pass;
pytest — see `00-baseline.md` for the count.

## Top 10 issues (by severity, then by reach)

| # | Severity | Issue | Evidence |
|---|---|---|---|
| 1 | **major (security)** | **Cross-site request forgery on cookie-authed `/api` writes.** A form POST from another site carrying the session cookie spends credits (`POST /api/direct/image/run` → 200, 10 credits held and settled) and makes a render public (`POST /api/assets/generated/{id}/share` → 200). The session cookie is `SameSite=None; Secure` on https (`app/auth.py:243-256`, read by the main session), there is no Origin check, and the mutation header is enforced on 14 routes only. Not reproduced on live (that needs a sign-in and a spend). | 03 E1 |
| 2 | **major (security)** | **Any customer can read, add and delete the shared eval golden set**, and start `/api/evals/run` on the operator's Gemini key. DELETE took the table from 8 rows to 7. The handlers check only `current_account_id` on a shared table. Related: BACKLOG #12 recorded `/evals/run` as a shared-table route that "takes an owner anyway". | 03 E2 |
| 3 | **major (money)** | **Claude Desktop's studio server runs code 264 commits old** (the main checkout on `claude/sheet-gpt-image-25`, process up since 10-30): LTX 2.3 6 s 1080p quotes **87 credits there vs 116** on both live listings, and Grok is missing. An approve there holds the old price. | 04 K1 |
| 4 | **major** | **The chat's still card breaks two approved rules at once**: the one spending button is **white on yellow** (~1.2:1) and a card waiting for approval is framed in **red**; its price sits under the button, not on it. | 02 T1 (`still-step.css` 17, 43, 138-145, 156) |
| 5 | **major** | **The Render card names models by raw id + platform**, on the Approve button itself: "Approve · kling3-turbo-pro (kling) · … 105 cr", "ltx2.3 (ltx)", while the line above says "Kling 3 Turbo Pro". | 02 T2 (`src/providers.py:172`) |
| 6 | **major** | **The Create composer's "Which model renders" menu prints a price on every model** ("· 116 credits a clip"), against the rule "no prices in model pickers, price only on the button". The direct generators comply. | 02 T3 (`create-view.tsx:4073`) |
| 7 | **major** | **Page weight on phones**: the new Halloween try-on page moves **28.9 MB on load** (four spin MP4s eager, `make-hero.tsx:76`); `lena.mp4` is still 9.45 MB (talking-photo page 18.6 MB after a scroll, OmniHuman page 23.1 MB); `/` is 5.0 MB on load at 390 with a 2.5 s LCP, the slowest on the site and the slowest of four sites measured. | 01 P1, P2, P3; 06a §3 |
| 8 | **major** | **Provenance labels a visitor or customer reads as offered models**: the home reel still says **"Runway Gen-4 Turbo"** (and "Seedance 2 Fast"); the home model strip omits Kling 4.0 and Grok; the Library's provider filter shows **"Fal · 3"**, "Kling" for Kling 4.0 and **"Runway"**. | 01 P5–P8 (`hero-reel.ts:45,50`, `vesper-content.ts:220-231`); 02 T4 (`src/render_assets.py:116-137`) |
| 9 | **major (WCAG)** | **Keyboard focus is invisible** on the public header (1.04:1 pill, no outline, every page) and on the composer textarea (D7, still open); "New element" is still **white on yellow** because `.zps button { color: inherit }` beats `.elnew`. | 01 P4 (`site-header.tsx:66`); 02 T8, T5 |
| 10 | **major** | **`images_for` is dead** on the stdio server and on `origin/main`: every call fails with a message-less error; `ImageSearch.sources` is typed `list[Any]` but `imagesearch.sources()` returns a dict. | 04 K2 (`src/mcp_shapes.py:248`, `src/imagesearch.py:126`) |

Also major, outside the ten: **Elements has no phone layout** (752 px at a 390 viewport, open
since 10-22 D2; 02 T6); **price per clip vs rivals** (Seedance 2.5 ~$3.55 per 5 s on Phantra vs
~$0.54–2.0 elsewhere, with the caveats in 06; 06b F1).

Minor items worth fixing with the ten because they touch money or trust: a paid voice job that
fails after settling says **"Nothing was charged."** (03 E5); `quote` still prices a **removed
scene** and a single-beat scene's own length is ignored without a note (04 K3, K4); the Add-element
modal **pre-ticks a 15-credit sheet** and its Add button shows no price (02 T10); with the API down,
two studio pages show an outage as an **empty account** (02 T11).

## Re-checks of 2026-10-22

| 10-22 item | Now | Evidence |
|---|---|---|
| Connector #1 (Claude listing in ws 5) | unchanged, Mike's call | 04 |
| Connector #2 (burst refusals) | not reproduced for reads (32/32); writes untested | 04 |
| Connector #3 (removed scene priced) | open | 04 K4 |
| Connector #4 (fit-up hidden) | open, broader | 04 K3 |
| Connector #5, #6 | open | 04 K5, K6 |
| S1 Runway label, S2–S4 model names | open; S3 staler | 01 P5–P8 |
| S6 "Image" suffix, `/make` 404 | fixed | 01 |
| W1–W4 page weight | open; W2 worse; a new 28.9 MB page | 01 P1–P3, P13, P18 |
| M1 pricing swipe | open | 01 P9 |
| M2 blank hero | not reproduced | 01 |
| C1 kit applied unasked | half fixed: the "Kit:" chip shows; the brief still bakes the logo in while asking | 02 T9 |
| C2 assistant covers content | **fixed** (docked in the rail, 44×44) | 02 |
| C3 kit asset 404s | not reproduced locally; production not checked | 02 |
| C5 "Runway" filter | open, wider | 02 T4 |
| D2 Elements phone | open | 02 T6 |
| D5 creature covers content | mostly fixed; one small creature in the chat | 02 T12 |
| D6 Effects focus ring | **fixed** | 02 |
| D7 composer focus | open | 02 T8 |
| D8 white on yellow | `.elnew` open; `.cv2-cta` gone | 02 T5 |

## UI design changes

Mike's approved rules used as the bar: price only on the spending button, never in a picker;
renders named by model, never by platform; Marigold/yellow fills with black text; red only for
errors; owl + Phantra lettering on the phone top bar (met, 02). A change that would reverse a
recorded call is flagged.

### Desktop

| Page | Change | Shown working on | Evidence |
|---|---|---|---|
| Create chat, still card | Black text on the yellow Approve, price on the button, a neutral (not red) frame while waiting | Phantra's own direct generators ("Generate · 10 credits") | 02 T1; `flow-*` screenshots in `screens/studio/` |
| Render card | Display names from the catalogue ("Kling 3 Turbo Pro"), never `id (platform)`, in the menu, the closed picker and the Approve label | `/pricing` and the direct pickers already use display names | 02 T2 |
| Create composer, renderer menu | Drop "· N credits a clip"; the price stays on Render | the direct generators' pickers | 02 T3 |
| Public header, composer | A visible `:focus-visible` ring (2 px Marigold outline) | Effects tiles after D6's fix | 01 P4; 02 T8 |
| `/` | Relabel or drop the Runway clip; "Seedance 2.0 Fast"; strip from `pricing.json` so Kling 4.0 and Grok appear; lazy-load reel columns past the first | — | 01 P3, P5–P7 |
| Signed-out `/studio` | Don't land a visitor on a shell that 401s: either a sign-in sheet over the shell, or a **guest composer** that asks for an account on Send | Runway's guest workspace (`screens/competitors/runway/guest-app-1440.png`); Krea's signed-out tool pages | 01 P14; 06 |
| `/mcp` (and the connector listings) | Lead with "every spend is quoted and approved"; a recipe library of copyable prompts per client; add `/llms.txt` and an `/agents.md` | Runway `/mcp` (19 prompts), invideo `/agents.md`, Krea `llms.txt` | 06 (06a §5, 06b F2) |
| `/pricing` | Translate each plan's credits into outputs ("3,500 credits ≈ N clips of …"); a "which plan?" finder | Runway plan cards, Higgsfield / invideo finders | 06 |
| Effects tab | An outcome-named apps row on top of the model-named effects ("Product spin", "9 shots from one image", "Relight") | Higgsfield `/apps`, Krea `/apps` | 06 |
| Ad Studio | A "Generate in Claude / ChatGPT" door beside Start in Create | Krea Ad Studio (`screens/competitors/krea/ad-studio-1440.png`) | 06b F6 |
| Studio, any page | Say "can't reach the studio's server" on a proxy 5xx, never an empty board or "INTERNAL SERVER ERROR" | — | 02 T11 |
| Library filter | Model names from the catalogue; no "Fal", no "Runway" | — | 02 T4 |
| Home demo "Approve", Profile "Log out" | **Mike's call**: both are red fills. `vesper.css:37` says "red only on the one spend"; the brief for this QA says red is for errors only. One rule has to win. | — | 01 P17; 02 T19 |

### Mobile (390 px)

| Page | Change | Evidence |
|---|---|---|
| `/make/ai-halloween-costume-try-on` | Only the front fan card plays eagerly; re-encode the spins (1.2–1.7 MB/s today) | 01 P1 |
| `/make/photo-to-talking-video`, OmniHuman page | Re-encode `lena.mp4` (9.45 MB) and `mechanic.mp4` (5.37 MB) or ship a short preview | 01 P2 |
| `/` | Smaller phone renditions of the reel; LCP 2.5 s today | 01 P3 |
| `/pricing` | Stacked plan cards or a visible swipe cue; make the table focusable | 01 P9 (M1) |
| `/studio/elements` | A phone layout (single column) | 02 T6 (D2) |
| `/studio/renders` | Stack the house-only showcase block (page is 407 px wide) | 02 T7 |
| Phone menu | Add Voice (unreachable today) | 02 T15 |
| `/studio/new` | One creature per screen | 02 T20 |
| Public tap targets | ≥ 24 px for "Try now", "Learn more", "Start now", `/mcp` filters | 01 P11 |

## Code changes (write the failing test first)

| # | Change | File / route | Failing test to write first | Size |
|---|---|---|---|---|
| 1 | Refuse cross-site writes: require a same-site `Origin`/`Sec-Fetch-Site` (or the mutation header) on every non-GET `/api` route; consider `SameSite=Lax` now that the handoff makes the cookie first-party on phantra.ai | `app/main.py` middleware; `app/auth.py:243-256` | `POST /api/direct/image/run` and `/api/assets/generated/{id}/share` with `Origin: https://evil.example`, cookie, no header → 403, ledger unchanged (03 E1 reproduces it) | S |
| 2 | Operator-only eval golden set and `/evals/run` | `app/api.py` ~7771-7830 | a non-operator account → 403 on GET/POST/DELETE `/api/evals/golden` and POST `/api/evals/run` | S |
| 3 | Stop a stale studio server from pricing: refuse `quote`/`approve` when the process's `pricing_version` is older than the one the deployed API recorded (and update the Desktop checkout now) | `src/mcp_server.py`, `src/pricing.py`; ops: `ops/claude-desktop-mcp.json` | stub a newer recorded version → stdio `generate_video` quote refuses with "update the studio server" | S |
| 4 | Render card labels by display name | `src/providers.py:172` | `GET /api/scenes/{id}/render` → every `models[].label` equals the catalogue name and contains no "(" | S |
| 5 | No credits in the composer's renderer menu | `web/src/app/studio/(create)/create-view.tsx:4073` | node test on the menu's label builder: no "credit" in any label | S |
| 6 | Still card colours and price | `web/src/components/studio/still-step.css` | a node test that no rule pairs `background: var(--signal)` with a white `color`; the waiting state has no red | S |
| 7 | `.elnew` black text | `studio.css` (`.zps .elnew` or drop `color: inherit` from `.zps button`) | same CSS test as 6 | S |
| 8 | Library labels by model | `src/render_assets.py:116-137` `_label` | `_label` for a fal `flux2-pro` still → "FLUX.2 Pro", for `kling4` → "Kling 4.0", never "Fal" / "Runway" | S |
| 9 | `images_for` output shape | `src/mcp_shapes.py:248` | call `images_for` with `imagesearch` stubbed to its real return shape → validates | S |
| 10 | "Nothing was charged" only when nothing was | `src/failures.py:34-41` (`_OURS`) | a `run_voice` failure after settle → the job's message does not say "Nothing was charged" | S |
| 11 | `quote` refuses a removed scene; says when the length differs from the scene | `src/mcp_server.py` quote, `src/pricing.py` | `quote(<removed scene>)` → refusal; `quote(<4 s single-beat scene>, kling4)` carries the rendered length and a line | S |
| 12 | Scene refs from another account refused | `POST /api/concepts/{id}/refs`, `PUT …/shots/{n}/refs` | B's photo ref on A's scene → 403/422, as `write_scene` already does | S |
| 13 | A place whose describe call fails is still saved | `_create_location` (`app/api.py`) | describe stubbed to fail → `locations` row exists, listed in Elements | S |
| 14 | No sheet unless asked; price on Add | `_sheet_wanted` (`app/api.py:2585`); Add-element modal | `POST /api/assets/characters` without `sheet` → no sheet job | S |
| 15 | Hide `/docs`, `/redoc`, `/openapi.json` in production | `app/main.py` (`FastAPI(docs_url=…)` behind `DEV_TOOLS`) | with `DEV_TOOLS` unset → 404 | S |
| 16 | Length caps on titles, folders, prompts, workflow bodies | `/api/projects`, `/api/assets/generated/{id}`, `/api/workflows`, `…/shots/{n}/prompt` | a 1 MB title → 422 | S |
| 17 | Structured refusal codes on MCP tool errors | `src/mcp_server.py` | a reference-gate refusal carries `code: needs_reference` | M |
| 18 | Studio fetch wrapper: an outage is said as an outage | `web/src/lib/` fetch helpers | node test: a 502 from the proxy → "can't reach the server" state, not empty data | S |

Cosmetic, batch them: 03 E4, E7–E10; 04 K5–K8, K10, K11; 02 T16–T18; 01 P16, P19–P21.

## Next steps: from here to where Phantra could be

BACKLOG checked first; items already there are linked, not re-proposed.

### Now (this week: bugs and quick wins)

| Item | Why | Size |
|---|---|---|
| Code changes 1–2 (CSRF, evals gate) | security; both reproduce in `e2e_routes.py` | S |
| Update Claude Desktop's checkout + change 3 | it quotes old prices today (04 K1) | S |
| Changes 4–8 (labels, prices in pickers, white on yellow, red frame) | they break Mike's approved rules on the spend path | S |
| Changes 9–11 (`images_for`, "Nothing was charged", removed-scene quote) | a dead tool and two money messages that can be wrong | S |
| Page weight: re-encode the Halloween spins, `lena.mp4`, `mechanic.mp4`; front card eager only | 28.9 MB / 18.6 MB / 23.1 MB pages (01 P1–P2); the long-term answer is BACKLOG #16 (transcoding, renditions) | S |
| Home labels and model strip from `pricing.json` | open since 10-22 (01 P5–P7) | S |
| Focus rings (header, composer) | WCAG 2.4.7, open since 10-22 for the composer | S |
| Delete the QA rows in workspace 5 (10-22's and today's) | listed in `04-connector.md` | Mike |
| Confirm the Resolve `.pkg` on `/download` is meant to be public | 01 P15; the panels were to be "offered later" | Mike |

### Next (2–4 weeks: the gaps vs Higgsfield and the rest)

| Item | Why | Size |
|---|---|---|
| Guest composer on signed-out `/studio` (or a sign-in sheet) | the home CTAs land on a shell that 401s (01 P14); Runway and Krea let a visitor reach Generate first | M |
| Phone layouts: Elements, Renders' showcase block, Voice in the menu | 02 T6, T7, T15 (D2 open since 10-22) | M |
| `/mcp` as a recipe library; `/llms.txt` + `/agents.md`; "Generate in Claude" on Ad Studio; lead with quote-before-spend | Phantra's one feature none of the six has, said where agents and directories read (06) | S–M |
| Outcome-named apps row over the effects table | Higgsfield and Krea score 5 on effects, Phantra 3 (06) | M |
| Pricing page: credits → outputs per plan, a plan finder | Runway's cards; 06 | S |
| Credit economics review: Seedance per-clip price, 2-month expiry, one-time trial | 06b F1, F3, F4; **changes recorded decisions** (the one-time 100-credit trial, `PHANTRA_SIGNUP_CREDITS`; the 2-month expiry) — Mike's call | M |
| Structured MCP refusals (change 17) | an agent cannot tell a refusal from an outage (04 K9) | M |
| Nightly `e2e_routes.py` (in CI, not on Fly) | turns this pass into a regression check; **note**: CLAUDE.md says the IG token keeper is the only scheduled job — a CI nightly is a new scheduled job, Mike's call | S |
| Changes 12–16, 18 | hygiene found by the route pass | S each |

### Later (studios, mobile app)

| Item | Why | Size |
|---|---|---|
| Ad loop: ad-account data in → variants of winners → approved publish | Runway Ads (GA 10-27) and Higgsfield's ads tools sell the same buyer; Phantra has Ad Studio, kits, `outcomes` and the publish worker to build on (06); see BACKLOG #4 (analytics pull) and #28 (brand kits not built) | L |
| A small daily free allowance | Krea's 100 units/day vs a one-time 100 (06b F3); changes the trial decision | M |
| Media renditions and transcoding | BACKLOG #16 (parked by Mike 2026-09-08) is the real fix for P1–P3 | L |
| Music generation, a motion-control model | the catalogue rows where the six score 5 and Phantra 4 (06) | M |
| Editor on a phone / a mobile app | the editor has no phone layout by design today; Runway, Krea, invideo ship apps (06) | L |
| Jobs that survive a restart | BACKLOG #26 (parked) | M |

## Scorecard (06, 1–5 on 13 criteria, out of 65)

| | Phantra* | Higgsfield | Runway | LTX Studio | Krea | invideo AI | Magnific |
|---|---|---|---|---|---|---|---|
| Total | **52** | 44 | 52 | 39 | 52 | 51 | 44 / 50 (3 n/m) |
| Strongest | agent with priced approval, MCP, social publishing (5) | catalog, effects, MCP | agent, ads, MCP | first screen, page weight | catalog, effects, agent, ads, MCP | first screen, catalog, editor, agent, MCP | catalog, library, brand kit, MCP |
| Weakest | first screen, effects, mobile (3) | first screen, pricing, page weight, editor, publishing (2) | first screen, onboarding, effects (3) | onboarding, effects, agent (2), publishing (1) | page weight, publishing (1) | publishing (2) | publishing (1) |

\* Phantra self-scored by the main session from the agents' measurements; the six were scored
from outside, signed out (06).

## Needs Mike

1. Step 5 (one real render, ~40–70 credits on the review workspace, cap proposed 100): yes or no (05).
2. Which red rule wins: "red only on the one spend" (`vesper.css`) or "red only for errors" (01 P17, 02 T19).
3. The credit economics in 06 (Seedance price, expiry, trial shape) — each changes a recorded decision.
4. The Resolve installer live on `/download` (01 P15).
5. Delete the QA rows in workspace 5 (04).
6. Pick which changes above become task files. Nothing here is built until you say so.
