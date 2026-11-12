# 03 — Backend endpoint E2E, 2026-11-02

Run at `8ba89087` on branch `claude/qa-2026-11`, in-process (FastAPI `TestClient`) against a
throwaway Postgres schema `qa1102c` (dropped at the end, count 0), with providers faked at the
HTTP layer. A socket + psycopg guard blocked anything off this machine; every key was blank or a
local fake; no `*_SPEND_OK` / `PHANTRA_RENDER`. Script: `e2e_routes.py` (this folder); route dump:
`openapi.json` (287 paths). Written by the main session from Agent C's hand-back (the harness
refused the subagent's own Write); the route table below is Agent C's `table.md` verbatim.

Rerun:
`PYTHONPATH="$PWD:<scratch>/site" venv/bin/python docs/qa/2026-11-02/e2e_routes.py --schema qa1102c --json out.json --openapi docs/qa/2026-11-02/openapi.json`
(`<scratch>/site/sitecustomize.py` drops the venv's editable finder so the worktree's code runs,
not the main checkout's.) The final run exits 0 with E1–E6 listed as known failures.

## Summary

| | |
|---|---|
| Routes (method + path, 4 mounts, 11 hidden from the schema) | **332**: 151 read, 138 write, 43 spend |
| Checks | 1,657: **1,386 pass, 13 fail**, 258 notes/skips |
| Per route | 316 PASS, 11 FAIL, 2 NOTE, 3 static mounts not probed |
| 5xx | **0 × 500.** Every 5xx was a readable 503 "not configured here" |
| Bad input | 794 checks, 0 failures, 0 5xx; huge ids → 404 / 422 |
| Tenancy (path ids) | 109 of B's ids refused, 0 leaks of B's data, B's 51 owned tables unchanged |
| Ledger | **PASS** (below) |
| Jobs / SSE | **PASS** |
| Stripe webhook | **PASS**; billing tests 9 files, **190 passed in 208 s** |
| MCP auth | **PASS** (`/mcp`, `/mcp/claude` 401 with no / wrong bearer) |

**Classification.** read = GET or a mount. write = everything else that is not spend; quote,
menu and render-price paths are never spend. spend = the handler's source or its dependency tree
matches a provider, ledger or Stripe pattern. It errs wide: known over-matches are `cut/assemble`,
`cut/media`, `quick-edit`, `billing/webhook`, the voice-clone delete and `assets/backfill`.

**Seed.** Accounts A and B through the app's own routes, each with a user and 2,000 purchase
credits; a character, prop and location; a project and a scene held to a photo; a Library render
and a cut project; a brand kit, a workflow and a share; a Discord connection and a post; a
creative project, a job and a plugin token.

**Passes, in order:** unauth → tenancy (path ids) → tenancy with keys faked → bad input
(non-numeric id, id past int4/int8, no body, wrong types, 1 MB string, non-JSON) → authed as A →
model text with Gemini blank → tenancy (body ids) → plugin bearer → CSRF → quote tokens → ledger
(fal/Gemini faked) → jobs/SSE → Stripe → MCP → shared tables → destructive routes last.

## Findings

| # | Severity | Route(s) | Evidence | Cause / fix |
|---|---|---|---|---|
| E1 | **major (security)** | CSRF on cookie-authed `/api` writes | `POST /api/direct/image/run`, multipart, `Origin: evil.example`, no `X-Phantra-Model-Connection` → 200 `{"job_id":11,"credits":10,"charged":true}`, ledger hold then settle. `POST /api/assets/generated/1/share`, no body → 200 `{"shared":true,…}` (a render made public). urlencoded / text-plain JSON bodies got 422; the header-guarded `creative-guide` got 403. | `auth.issue_session` sets `SameSite=None; Secure` on https (`app/auth.py:243-256`, confirmed by the main session); no Origin check; the mutation header is enforced on 14 routes only. Fix: require the header or a same-site Origin on every non-GET `/api` route, or a Lax cookie on the studio origin. Not reproduced on live (needs a sign-in and a spend). |
| E2 | **major** | `/api/evals/golden`, `/api/evals/run` | `GET` → 200 listing the operator's rows; `POST` → 200; `DELETE /api/evals/golden/{id}` → 200, table 8 rows → 7. `POST /api/evals/run` runs on the operator's Gemini key behind only the Create gate. | Handlers (`app/api.py` ~7771-7830) check only `current_account_id` on a SHARED table. Fix: an operator check. |
| E3 | minor | `POST /api/concepts/{id}/refs`, `PUT …/shots/{n}/refs` | `{"refs":["/characters/qab-hero/photo/qaB.png"]}` (B's photo) → 200; A's `shots_json` then holds B's ref. `write_scene` refuses such refs; these routes don't. | Not verified on the R2 `tenant` rung, where A's resolver reads `m/<A>/` (likely no bytes leak there). |
| E4 | cosmetic | `GET/DELETE /api/assets/generated/{B's id}/share` | From A → 200 `{"shared":false,…}` instead of 404. No leak; B's share still 200 afterwards. | |
| E5 | minor | voice run | When filing fails (ffprobe can't read the file) the job says "Nothing was charged." while the ledger shows hold → settle (1,844 → 1,834). | `run_voice` says "made and paid for", and `failures.plain`'s `_OURS` pattern spares "was charged" but not "paid for" (`src/failures.py:34-41`). |
| E6 | minor | `POST /api/assets/locations` | `{"ok":true,"described":false,…}` but `GET /api/assets?scope=elements` lists only `character-1` and `prop-1`. | `_create_location` writes no `locations` row when the describe call fails. |
| E7 | cosmetic | social connection options/pick/posting-times; post PATCH/date/state | B's ids → 400 "No such … on this workspace" instead of 404. | |
| E8 | cosmetic | `POST /plugin/v1/signout` | No bearer → 200 `{"ok":true,"revoked":false}`. | |
| E9 | cosmetic | `/api/retrieve` | 503 "No API key was provided … ai.google.dev …" (Google SDK text reaches the person). | |
| E10 | cosmetic | `/api/brand-kits/import` | A 1 MB `url` reaches `getaddrinfo` (`refbin.public_host`) before a readable 400. | Length check first. |
| E11 | minor | live `api.phantra.ai/openapi.json`, `/docs`, `/redoc` | All 200 on production (openapi.json 246,931 bytes, 0.53 s). | The whole route map is public. |
| E12 | minor | `POST /api/projects`, `PATCH /api/projects/{id}` (title), `PATCH /api/assets/generated/{id}` (folder), `POST/PUT /api/workflows`, `…/shots/{n}/prompt` | A 1 MB string is stored. | No length caps. |

## Tenancy

- Path ids: 109 refused (6 of them as E7's 400s), 3 answered 200 (E4).
- 18 skipped: the id is the same for A and B (publish session, what's-new items and showcase,
  voice/golden/run/video ids), or `location_id` had no value (E6).
- Sheet, direct and refine routes: 503 with no key, then 404 with fake keys, and no provider was
  reached — ownership is checked before any provider call.
- Body ids:

| Request (A naming B's id in the body) | Answer |
|---|---|
| `cut/assemble` | 404 |
| `cut/projects` | 404 ×2 |
| `posts` | 400 ×2 |
| `quick-edit` | 400 |
| `effects/run` | job failed "no render 2", no hold, no submit |
| `effects/quote` | 200, price only |
| `brand-kit` | silently set to null |
| `assistant/project` | a new empty project for A |
| `refs` ×2 | **accepted (E3)** |

- Plugin bearer: B's scene, download and job → 404; no bearer → 401.

## Ledger (providers faked)

Every stubbed spend held credits before the provider call; success settled, failure released,
and the balance always ended at before − settled.

| Case | Credits | Balance |
|---|---|---|
| fal clip (scene approve, signed token) | 116 | 1,990 → 1,874 |
| FLUX still, Nano Banana still (direct, `expect_credits`) | 10 each | settled |
| voice (`expect_credits`) | 10 | settled |
| failure path (each) | held → released | unchanged |

Reconcile clean, 0 holds left open. Quote refusals held nothing (1,990 → 1,990): `missing_quote`,
`bad_signature`, `wrong_account`, `stale_content`, and 404 on B's scene. A price off by one →
409 `price_changed` with nothing held.

## Jobs / SSE, Stripe, MCP

- A backfill job reached `done`; B's job id → 404. `/api/jobs/stream` (uvicorn on 8031) sent
  `hello` and the job event within 0.13 s, released the subscriber within 0.2 s of hang-up, and
  answered 401 with no session.
- `/billing/webhook`: no, bad, wrong-secret and stale signatures all → 400, no grant. Checkout
  `{"item":"starter"}` → 503 `billing_unconfigured` (no Stripe key here, as intended).
- `/mcp`, `/mcp/claude` → 401 with no bearer or a wrong one.

## Model text with Gemini blank (all readable, none 500)

| Route | Answer |
|---|---|
| `creative-guide` | 400 |
| `act` | 400 |
| `draft-brief` | 503 |
| `scenes/run` | 400 |
| cut agent | 200 job |
| voiceover script | 200 job |
| product-from-link | 400 |
| `retrieve` | 503 (E9) |

Authed as A: 182 pass, 141 notes (readable 4xx, 8 state 409s, 15 readable 503s that need a key).
Network wall: 3 blocks, all expected public-host DNS checks (brand-kit import ×2,
product-from-link ×1).

## Live smoke (production, curl, no auth, ~16:50 UTC; seconds)

| URL | Status | Samples |
|---|---|---|
| `api.phantra.ai/healthz` | 200 | 0.257 / 0.156 / 0.229 |
| `phantra.ai/sitemap.xml` | 200 | 0.478 / 0.157 / 0.235 |
| `phantra.ai/robots.txt` | 200 | 0.174 / 0.306 / 0.141 |
| `api.phantra.ai/api/me` | 401 | 0.148 / 0.231 / 0.232 |
| `/v/<fake>` | 404 | 1.855 (cold) / 0.399 / 0.406 |
| `/public/share/<fake>` | 404 | 0.192 / 0.324 / 0.328 |

A real `/v/` share page was skipped: none is public, and minting one would be a live write.

## Not covered

Static mounts; Supabase and OAuth round trips; E3 on the R2 rung; E1 on live.

## Route table

| # | Method | Path | Class | In schema | Unauth | Own (A) | A asks B's id | Bad input pass/fail/note | Other passes | Result |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | GET | `/openapi.json` | read | no | 200 | 200 | - | - | - | PASS (E11) |
| 2 | GET | `/docs` | read | no | 200 | 200 | - | - | - | PASS (E11) |
| 3 | GET | `/docs/oauth2-redirect` | read | no | 200 | 200 | - | - | - | PASS |
| 4 | GET | `/redoc` | read | no | 200 | 200 | - | - | - | PASS (E11) |
| 5 | * | `/static` | read | no | - | - | - | - | - | not probed (mount) |
| 6 | * | `/renders` | read | no | - | - | - | - | - | not probed (mount) |
| 7 | * | `/refs` | read | no | - | - | - | - | - | not probed (mount) |
| 8 | * | `/mcp` | read | no | - | - | - | - | - | PASS (mcp phase: 401 without / with a wrong bearer) |
| 9 | GET | `/.well-known/oauth-protected-resource/mcp` | read | yes | 200 | 200 | - | - | - | PASS |
| 10 | GET | `/.well-known/oauth-protected-resource` | read | yes | 200 | 200 | - | - | - | PASS |
| 11 | GET | `/.well-known/oauth-protected-resource/mcp/claude` | read | yes | 200 | 200 | - | - | - | PASS |
| 12 | GET | `/.well-known/openai-apps-challenge` | read | yes | 404 | 404 | - | - | - | PASS |
| 13 | GET | `/api/creative-projects` | read | yes | 401 | 200 | - | - | - | PASS |
| 14 | GET | `/api/creative-projects/{project_id}` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 15 | POST | `/api/creative-projects` | write | yes | 401 | 200 | - | 4/0/0 | - | PASS |
| 16 | GET | `/api/model-connections` | read | yes | 401 | 200 | - | - | - | PASS |
| 17 | GET | `/api/model-connections/{provider}` | read | yes | 401 | 404 | - | - | - | PASS |
| 18 | POST | `/api/model-connections/{provider}/signin` | write | yes | 401 | 404 | - | 4/0/0 | - | PASS |
| 19 | POST | `/api/model-connections/{provider}/disconnect` | write | yes | 401 | 409 | - | - | - | PASS |
| 20 | GET | `/api/publish` | read | yes | 401 | 200 | - | - | - | PASS |
| 21 | POST | `/api/publish/prepare` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 22 | GET | `/api/publish/{session_id}` | read | yes | 401 | 404 | skip | - | - | PASS |
| 23 | POST | `/api/publish/{session_id}/submit` | write | yes | 401 | 400 | skip | 4/0/0 | - | PASS |
| 24 | POST | `/api/publish/{session_id}/cancel` | write | yes | 401 | 400 | skip | 4/0/0 | - | PASS |
| 25 | GET | `/api/social/providers` | read | yes | 401 | 200 | - | - | - | PASS |
| 26 | GET | `/api/social/connections` | read | yes | 401 | 200 | - | - | - | PASS |
| 27 | GET | `/api/social/connections/{connection_id}/options` | read | yes | 401 | 200 | 400 | 3/0/0 | - | PASS (E7) |
| 28 | POST | `/api/social/connections/{connection_id}/pick` | write | yes | 401 | 400 | 400 | 7/0/0 | - | PASS (E7) |
| 29 | GET | `/api/social/connections/{connection_id}/posting-times` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 30 | PUT | `/api/social/connections/{connection_id}/posting-times` | write | yes | 401 | 200 | 400 | 7/0/0 | - | PASS (E7) |
| 31 | DELETE | `/api/social/connections/{connection_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 32 | GET | `/api/posts` | read | yes | 401 | 200 | - | - | - | PASS |
| 33 | POST | `/api/posts` | write | yes | 401 | 400 | - | 4/0/0 | tenancy_body | PASS |
| 34 | POST | `/api/posts/group` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 35 | GET | `/api/posts/next-slot` | read | yes | 401 | 422 | - | - | - | PASS |
| 36 | GET | `/api/posts/free-slots` | read | yes | 401 | 422 | - | - | - | PASS |
| 37 | GET | `/api/posts/feed` | read | yes | 401 | 422 | - | - | - | PASS |
| 38 | GET | `/api/posts/{post_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 39 | PATCH | `/api/posts/{post_id}` | write | yes | 401 | 200 | 400 | 7/0/0 | - | PASS (E7) |
| 40 | PUT | `/api/posts/{post_id}/date` | write | yes | 401 | 200 | 400 | 7/0/0 | - | PASS (E7) |
| 41 | POST | `/api/posts/{post_id}/state` | write | yes | 401 | 400 | 400 | 7/0/0 | - | PASS (E7) |
| 42 | DELETE | `/api/posts/{post_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 43 | GET | `/api/whats-new` | read | yes | 401 | 200 | - | - | - | PASS |
| 44 | POST | `/api/whats-new/seen` | write | yes | 401 | 200 | - | 3/0/1 | tenancy_body | PASS |
| 45 | POST | `/api/whats-new/{item_id}/dismiss` | write | yes | 401 | 200 | skip | 0/0/4 | - | PASS |
| 46 | POST | `/api/whats-new/{item_id}/notify` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 47 | GET | `/api/whats-new/showcase` | read | yes | 401 | 404 | - | - | - | PASS |
| 48 | PUT | `/api/whats-new/showcase/{item_id}` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 49 | POST | `/api/whats-new/showcase/{item_id}/quote` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 50 | POST | `/api/whats-new/showcase/{item_id}/approve` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 51 | POST | `/api/whats-new/showcase/{item_id}/pick` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 52 | POST | `/api/whats-new/showcase/{item_id}/keep` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 53 | POST | `/api/whats-new/showcase/{item_id}/redo` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 54 | POST | `/api/whats-new/showcase/{item_id}/skip` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 55 | POST | `/api/whats-new/showcase/{item_id}/restore` | write | yes | 401 | 404 | skip | 4/0/0 | - | PASS |
| 56 | GET | `/api/capabilities` | read | yes | 401 | 200 | - | - | - | PASS |
| 57 | GET | `/api/scene-lengths` | read | yes | 401 | 200 | - | - | - | PASS |
| 58 | GET | `/api/skills` | read | yes | 401 | 200 | - | - | - | PASS |
| 59 | GET | `/api/studios/{studio_id}` | read | yes | 401 | 200 | - | - | - | PASS |
| 60 | POST | `/api/studios/product-from-link` | spend | yes | 401 | 400 | - | 4/0/0 | model_text | PASS |
| 61 | GET | `/api/studios/{studio_id}/insights` | read | yes | 401 | 200 | - | - | - | PASS |
| 62 | GET | `/api/brains` | read | yes | 401 | 200 | - | - | - | PASS |
| 63 | GET | `/api/image-models` | read | yes | 401 | 200 | - | - | - | PASS |
| 64 | GET | `/api/clip-models` | read | yes | 401 | 200 | - | - | - | PASS |
| 65 | GET | `/api/render-choices` | read | yes | 401 | 200 | - | - | - | PASS |
| 66 | GET | `/api/me` | read | yes | 401 | 200 | - | - | - | PASS |
| 67 | GET | `/api/account/members` | read | yes | 401 | 200 | - | - | - | PASS |
| 68 | GET | `/api/mcp/connection` | read | yes | 401 | 200 | - | - | - | PASS |
| 69 | PATCH | `/api/me` | write | yes | 401 | 200 | - | 4/0/0 | - | PASS |
| 70 | GET | `/api/me/security` | read | yes | 401 | 200 | - | - | - | PASS |
| 71 | POST | `/api/me/security/code` | write | yes | 401 | 503 | - | 0/0/4 | - | PASS |
| 72 | POST | `/api/me/password` | write | yes | 401 | 503 | - | 3/0/1 | - | PASS |
| 73 | POST | `/api/me/email` | write | yes | 401 | 503 | - | 3/0/1 | - | PASS |
| 74 | POST | `/api/creative-guide` | spend | yes | 401 | 400 | - | 4/0/0 | csrf, model_text | PASS |
| 75 | POST | `/api/creative-guide/act` | spend | yes | 401 | 400 | - | 4/0/0 | model_text | PASS |
| 76 | GET | `/api/assistant` | read | yes | 401 | 200 | - | - | - | PASS |
| 77 | PUT | `/api/assistant/persona` | write | yes | 401 | 200 | - | 3/0/1 | - | PASS |
| 78 | PUT | `/api/assistant/project` | write | yes | 401 | 400 | - | 4/0/0 | tenancy_body | PASS |
| 79 | DELETE | `/api/assistant/project` | write | yes | 401 | 200 | - | - | - | PASS |
| 80 | POST | `/api/assistant/project/new` | write | yes | 401 | 200 | - | 0/0/4 | - | PASS |
| 81 | POST | `/api/assistant/reference-verdicts` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 82 | GET | `/api/assistant/reference-agreement` | read | yes | 401 | 200 | - | - | - | PASS |
| 83 | GET | `/api/assets` | read | yes | 401 | 200 | - | - | - | PASS |
| 84 | GET | `/api/media` | read | yes | 401 | 200 | - | - | - | PASS |
| 85 | GET | `/api/assets/search` | read | yes | 401 | 200 | - | - | - | PASS |
| 86 | GET | `/api/search` | read | yes | 401 | 200 | - | - | - | PASS |
| 87 | GET | `/api/assets/generated/trash` | read | yes | 401 | 200 | - | - | - | PASS |
| 88 | GET | `/api/assets/generated/{asset_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 89 | GET | `/api/assets/generated/{asset_id}/download` | read | yes | 401 | 404 | 404 | 3/0/0 | - | PASS |
| 90 | GET | `/api/assets/{category}/{item_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 91 | POST | `/api/assets/locations` | write | yes | 401 | 400 | - | 4/0/0 | seed | FAIL E6 |
| 92 | POST | `/api/assets/characters` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 93 | POST | `/api/assets/props` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 94 | POST | `/api/assets/backfill` | spend | yes | 401 | 200 | - | 3/0/1 | jobs | PASS |
| 95 | DELETE | `/api/assets/characters/{character_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 96 | DELETE | `/api/assets/locations/{location_id}` | write | yes | skip | skip | skip | - | - | NOTE |
| 97 | DELETE | `/api/assets/props/{prop_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 98 | POST | `/api/assets/{plural}/{item_id}/sheet` | write | yes | 401 | 503 | 503/404 | 1/0/6 | - | PASS |
| 99 | PATCH | `/api/assets/generated/{asset_id}` | write | yes | 401 | 400 | 404 | 6/0/1 | - | PASS (E12) |
| 100 | DELETE | `/api/assets/generated/{asset_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 101 | GET | `/api/storage` | read | yes | 401 | 200 | - | - | - | PASS |
| 102 | DELETE | `/api/assets/generated/{asset_id}/forever` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 103 | POST | `/api/assets/generated/{asset_id}/restore` | write | yes | 401 | 404 | 404 | 7/0/0 | - | PASS |
| 104 | GET | `/api/assets/generated/{asset_id}/share` | read | yes | 401 | 200 | 200 | 1/0/2 | - | FAIL E4 |
| 105 | POST | `/api/assets/generated/{asset_id}/share` | write | yes | 401 | 200 | 404 | 3/0/4 | csrf | FAIL E1 |
| 106 | DELETE | `/api/assets/generated/{asset_id}/share` | write | yes | 401 | 200 | 200 | - | - | FAIL E4 |
| 107 | POST | `/api/retrieve` | write | yes | 401 | 503 | - | 3/0/1 | model_text | PASS (E9) |
| 108 | GET | `/api/pipeline/arrival` | read | yes | 401 | 200 | - | - | - | PASS |
| 109 | GET | `/api/pipeline/concepts` | read | yes | 401 | 200 | - | - | - | PASS |
| 110 | GET | `/api/ref-roles` | read | yes | 401 | 200 | - | - | - | PASS |
| 111 | POST | `/api/scenes/run` | spend | yes | 401 | 400 | - | 4/0/0 | model_text | PASS |
| 112 | GET | `/api/projects` | read | yes | 401 | 200 | - | - | - | PASS |
| 113 | POST | `/api/projects` | write | yes | 401 | 400 | - | 3/0/1 | csrf | PASS (E12) |
| 114 | POST | `/api/projects/draft-brief` | spend | yes | 401 | 503 | - | 3/0/1 | model_text | PASS |
| 115 | GET | `/api/projects/{project_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 116 | PATCH | `/api/projects/{project_id}` | write | yes | 401 | 200 | 404 | 6/0/1 | - | PASS (E12) |
| 117 | POST | `/api/projects/{project_id}/archive` | write | yes | 401 | 200 | 404 | - | csrf | PASS |
| 118 | POST | `/api/projects/{project_id}/forget` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 119 | GET | `/api/projects/{project_id}/standing` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 120 | GET | `/api/projects/{project_id}/scenes` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 121 | DELETE | `/api/projects/{project_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 122 | GET | `/api/projects/{project_id}/messages` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 123 | POST | `/api/concepts/{concept_id}/keyframes` | spend | yes | 401 | 503 | 404 | 4/0/3 | - | PASS |
| 124 | POST | `/api/scenes/{concept_id}/keyframes` | spend | yes | 401 | 503 | 404 | 4/0/3 | - | PASS |
| 125 | POST | `/api/concepts/{concept_id}/archive` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 126 | GET | `/api/queue/pending` | read | yes | 401 | 200 | - | - | - | PASS |
| 127 | GET | `/api/queue/count` | read | yes | 401 | 200 | - | - | - | PASS |
| 128 | GET | `/api/renders/unfinished` | read | yes | 401 | 200 | - | - | - | PASS |
| 129 | GET | `/api/queue/manual` | read | yes | 401 | 404 | - | - | - | PASS |
| 130 | POST | `/api/queue/manual/{concept_id}/clip` | write | yes | 401 | 404 | 404 | 7/0/0 | - | PASS |
| 131 | GET | `/api/scenes/{concept_id}/render` | read | yes | 401 | 200 | 404 | 3/0/0 | quote | PASS |
| 132 | GET | `/api/queue/{concept_id}/quote` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 133 | GET | `/api/scenes/{concept_id}/quote` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 134 | POST | `/api/queue/{concept_id}/approve` | spend | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 135 | POST | `/api/scenes/{concept_id}/approve` | spend | yes | 401 | 400 | 404 | 7/0/0 | csrf, ledger, quote | PASS |
| 136 | POST | `/api/queue/{concept_id}/reject` | write | yes | 401 | 200 | 404 | 3/0/4 | - | PASS |
| 137 | POST | `/api/queue/{concept_id}/shot` | write | yes | 401 | 200 | 404 | 6/0/1 | - | PASS |
| 138 | POST | `/api/concepts/{concept_id}/refs` | write | yes | 401 | 200 | 404 | 6/0/1 | tenancy_body | FAIL E3 |
| 139 | PUT | `/api/scenes/{concept_id}/hook` | write | yes | 401 | 422 | 404 | 7/0/0 | - | PASS |
| 140 | DELETE | `/api/scenes/{concept_id}/hook` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 141 | GET | `/api/concepts/{concept_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 142 | POST | `/api/concepts/{concept_id}/shots/{shot_n}/media` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 143 | POST | `/api/concepts/{concept_id}/direct` | spend | yes | 401 | 503 | 503/404 | 4/0/3 | - | PASS |
| 144 | POST | `/api/concepts/{concept_id}/shots/{shot_n}/refine` | spend | yes | 401 | 503 | 503/404 | 1/0/6 | - | PASS |
| 145 | POST | `/api/concepts/{concept_id}/shots/{shot_n}/generate` | write | yes | 401 | 503 | 404 | 3/0/4 | - | PASS |
| 146 | POST | `/api/refs/upload` | write | yes | 401 | 200 | - | 0/0/4 | - | PASS |
| 147 | POST | `/api/pipeline/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 148 | GET | `/api/effects` | read | yes | 401 | 200 | - | - | - | PASS |
| 149 | GET | `/api/side-by-side` | read | yes | 401 | 422 | - | - | - | PASS |
| 150 | POST | `/api/effects/quote` | write | yes | 401 | 200 | - | 4/0/0 | tenancy_body | PASS |
| 151 | POST | `/api/effects/run` | spend | yes | 401 | 400 | - | 4/0/0 | tenancy_body | PASS |
| 152 | GET | `/api/talking-photo` | read | yes | 401 | 200 | - | - | - | PASS |
| 153 | POST | `/api/talking-photo/voice/quote` | write | yes | 401 | 200 | - | 4/0/0 | - | PASS |
| 154 | POST | `/api/talking-photo/voice/run` | spend | yes | 401 | 400 | - | 4/0/0 | ledger | FAIL E5 |
| 155 | POST | `/api/talking-photo/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 156 | POST | `/api/talking-photo/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 157 | GET | `/api/dubbing` | read | yes | 401 | 200 | - | - | - | PASS |
| 158 | POST | `/api/dubbing/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 159 | POST | `/api/dubbing/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 160 | GET | `/api/voice` | read | yes | 401 | 200 | - | - | - | PASS |
| 161 | POST | `/api/voice/speak/quote` | write | yes | 401 | 422 | - | 4/0/0 | - | PASS |
| 162 | POST | `/api/voice/speak/run` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 163 | POST | `/api/voice/library/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 164 | POST | `/api/voice/library/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 165 | POST | `/api/voice/dialogue/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 166 | POST | `/api/voice/dialogue/run` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 167 | POST | `/api/voice/clone/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 168 | POST | `/api/voice/clone/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 169 | DELETE | `/api/voice/clones/{voice_id}` | spend | yes | 401 | 404 | skip | - | - | PASS |
| 170 | POST | `/api/quick-edit` | spend | yes | 401 | 400 | - | 4/0/0 | tenancy_body | PASS |
| 171 | GET | `/api/presets` | read | yes | 401 | 200 | - | - | - | PASS |
| 172 | GET | `/api/presets/counts` | read | yes | 401 | 200 | - | - | - | PASS |
| 173 | GET | `/api/trending` | read | yes | 401 | 200 | - | - | - | PASS |
| 174 | GET | `/api/director/landing` | read | yes | 401 | 200 | - | - | - | PASS |
| 175 | POST | `/api/generate/run` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 176 | GET | `/api/direct/video` | read | yes | 401 | 200 | - | - | - | PASS |
| 177 | POST | `/api/direct/video/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 178 | GET | `/api/direct/image` | read | yes | 401 | 200 | - | - | - | PASS |
| 179 | POST | `/api/direct/image/quote` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 180 | POST | `/api/direct/video/run` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 181 | POST | `/api/direct/image/run` | spend | yes | 401 | 400 | - | 4/0/0 | csrf, ledger | FAIL E1 |
| 182 | PUT | `/api/concepts/{concept_id}/shots/{shot_n}/graph` | spend | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 183 | GET | `/api/concepts/{concept_id}/shots/{shot_n}/graph` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 184 | DELETE | `/api/concepts/{concept_id}/graph` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 185 | POST | `/api/concepts/{concept_id}/shots/{shot_n}/prompt` | spend | yes | 401 | 200 | 404 | 6/0/1 | - | PASS (E12) |
| 186 | PUT | `/api/concepts/{concept_id}/shots/{shot_n}/refs` | write | yes | 401 | 400 | 404 | 7/0/0 | tenancy_body | FAIL E3 |
| 187 | POST | `/api/concepts/{concept_id}/shots/{shot_n}/reference` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 188 | POST | `/api/concepts/{concept_id}/approve` | spend | yes | 401 | 409 | 404 | 7/0/0 | - | PASS |
| 189 | POST | `/api/concepts/{concept_id}/deny` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 190 | GET | `/api/evals/golden` | read | yes | 401 | 200 | - | - | shared | FAIL E2 |
| 191 | POST | `/api/evals/golden` | write | yes | 401 | 400 | - | 4/0/0 | shared | FAIL E2 |
| 192 | DELETE | `/api/evals/golden/{golden_id}` | write | yes | 401 | 200 | skip | - | shared | FAIL E2 |
| 193 | GET | `/api/evals/runs` | read | yes | 401 | 200 | - | - | - | PASS (E2) |
| 194 | GET | `/api/evals/runs/{run_id}` | read | yes | 401 | 404 | skip | 3/0/0 | - | PASS (E2) |
| 195 | POST | `/api/evals/run` | spend | yes | 401 | 503 | - | 3/0/1 | - | PASS (E2) |
| 196 | GET | `/api/analytics/summary` | read | yes | 401 | 200 | - | - | - | PASS |
| 197 | GET | `/api/analytics/posts` | read | yes | 401 | 200 | - | - | - | PASS |
| 198 | GET | `/api/costs` | read | yes | 401 | 200 | - | - | - | PASS |
| 199 | GET | `/api/analytics/accounts` | read | yes | 401 | 200 | - | - | - | PASS |
| 200 | POST | `/api/videos/{video_id}/refresh` | write | yes | 401 | 404 | skip | 7/0/0 | - | PASS |
| 201 | GET | `/api/workflows` | read | yes | 401 | 200 | - | - | - | PASS |
| 202 | POST | `/api/workflows` | write | yes | 401 | 200 | - | 3/0/1 | - | PASS (E12) |
| 203 | POST | `/api/workflows/exec/ground` | spend | yes | 401 | 200 | - | 3/0/1 | - | PASS |
| 204 | POST | `/api/workflows/exec/enhance` | spend | yes | 401 | 503 | - | 3/0/1 | - | PASS |
| 205 | POST | `/api/workflows/exec/generate` | spend | yes | 401 | 503 | - | 3/0/1 | - | PASS |
| 206 | POST | `/api/workflows/exec/nano` | spend | yes | 401 | 503 | - | 3/0/1 | - | PASS |
| 207 | GET | `/api/workflows/{workflow_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 208 | PUT | `/api/workflows/{workflow_id}` | write | yes | 401 | 200 | 404 | 6/0/1 | - | PASS (E12) |
| 209 | DELETE | `/api/workflows/{workflow_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 210 | POST | `/api/workflows/{workflow_id}/run` | spend | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 211 | GET | `/api/jobs` | read | yes | 401 | 200 | - | - | jobs | PASS |
| 212 | GET | `/api/jobs/stream` | read | yes | - | - | - | - | sse | PASS |
| 213 | DELETE | `/api/jobs` | write | yes | 401 | 200 | - | - | - | PASS |
| 214 | GET | `/api/jobs/{job_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | jobs | PASS |
| 215 | POST | `/api/jobs/{job_id}/cancel` | write | yes | 401 | 200 | 404 | 3/0/4 | jobs | PASS |
| 216 | DELETE | `/api/jobs/{job_id}` | write | yes | 401 | 404 | 404 | - | jobs | PASS |
| 217 | POST | `/api/billing/checkout` | write | yes | 401 | 400 | - | 4/0/0 | stripe | PASS |
| 218 | POST | `/api/billing/portal` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 219 | GET | `/api/billing/balance` | read | yes | 401 | 200 | - | - | - | PASS |
| 220 | GET | `/api/billing/history` | read | yes | 401 | 200 | - | - | - | PASS |
| 221 | GET | `/api/affiliates/me` | read | yes | 401 | 200 | - | - | - | PASS |
| 222 | POST | `/api/affiliates/apply` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 223 | POST | `/api/affiliates/attribute` | write | yes | 401 | 200 | - | 3/0/1 | - | PASS |
| 224 | GET | `/api/cut/ready` | read | yes | 401 | 200 | - | - | - | PASS |
| 225 | POST | `/api/cut/motion-ad` | spend | yes | 401 | 200 | - | 4/0/0 | - | PASS |
| 226 | POST | `/api/cut/projects/{project_id}/motion-ad/beat` | spend | yes | 401 | 400 | 404 | 4/0/0 | - | PASS |
| 227 | POST | `/api/cut/assemble` | spend | yes | 401 | 409 | - | 4/0/0 | tenancy_body | PASS |
| 228 | POST | `/api/cut/media` | spend | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 229 | POST | `/api/cut/index` | spend | yes | 401 | 409 | - | 4/0/0 | - | PASS |
| 230 | GET | `/api/cut/search` | read | yes | 401 | 400 | - | - | - | PASS |
| 231 | GET | `/api/cut/projects` | read | yes | 401 | 200 | - | - | - | PASS |
| 232 | POST | `/api/cut/projects` | write | yes | 401 | 200 | - | 4/0/0 | tenancy_body | PASS |
| 233 | GET | `/api/cut/projects/{project_id}` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 234 | PATCH | `/api/cut/projects/{project_id}` | write | yes | 401 | 200 | 404 | 4/0/0 | - | PASS |
| 235 | DELETE | `/api/cut/projects/{project_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 236 | POST | `/api/cut/projects/{project_id}/restore` | write | yes | 401 | 404 | 404 | 4/0/0 | - | PASS |
| 237 | POST | `/api/cut/projects/{project_id}/ops` | write | yes | 401 | 422 | 404 | 4/0/0 | - | PASS |
| 238 | POST | `/api/cut/projects/{project_id}/undo` | write | yes | 401 | 409 | 404 | 4/0/0 | - | PASS |
| 239 | POST | `/api/cut/projects/{project_id}/redo` | write | yes | 401 | 409 | 404 | 4/0/0 | - | PASS |
| 240 | POST | `/api/cut/projects/{project_id}/rollback` | write | yes | 401 | 200 | 404 | 3/0/1 | - | PASS |
| 241 | GET | `/api/cut/media` | read | yes | 401 | 200 | - | - | - | PASS |
| 242 | GET | `/api/cut/projects/{project_id}/media` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 243 | GET | `/api/cut/media/{handle}/preview` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 244 | GET | `/api/cut/media/{handle}/transcript` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 245 | POST | `/api/cut/projects/{project_id}/export` | write | yes | 401 | 409 | 404 | 4/0/0 | - | PASS |
| 246 | GET | `/api/cut/projects/{project_id}/music` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 247 | POST | `/api/cut/projects/{project_id}/music/quote` | write | yes | 401 | 200 | 404 | 4/0/0 | - | PASS |
| 248 | POST | `/api/cut/projects/{project_id}/music/run` | spend | yes | 401 | 400 | 404 | 4/0/0 | - | PASS |
| 249 | GET | `/api/cut/projects/{project_id}/voiceover` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 250 | POST | `/api/cut/projects/{project_id}/voiceover/quote` | write | yes | 401 | 400 | 404 | 4/0/0 | - | PASS |
| 251 | POST | `/api/cut/projects/{project_id}/voiceover/run` | spend | yes | 401 | 400 | 404 | 4/0/0 | - | PASS |
| 252 | POST | `/api/cut/projects/{project_id}/voiceover/script` | spend | yes | 401 | 200 | 404 | 4/0/0 | model_text | PASS |
| 253 | GET | `/api/cut/projects/{project_id}/exports` | read | yes | 401 | 200 | 404 | - | - | PASS |
| 254 | POST | `/api/cut/projects/{project_id}/agent` | spend | yes | 401 | 200 | 404 | 4/0/0 | model_text | PASS |
| 255 | POST | `/api/cut/projects/{project_id}/agent/keep` | write | yes | 401 | 422 | 404 | 4/0/0 | - | PASS |
| 256 | POST | `/api/cut/projects/{project_id}/cleanup` | write | yes | 401 | 200 | 404 | 3/0/1 | - | PASS |
| 257 | POST | `/api/cut/projects/{project_id}/captions` | write | yes | 401 | 200 | 404 | 4/0/0 | - | PASS |
| 258 | POST | `/api/cut/projects/{project_id}/index` | spend | yes | 401 | 409 | 404 | 4/0/0 | - | PASS |
| 259 | GET | `/api/cut/{concept_id}/timeline` | read | yes | 401 | 404 | 404 | 3/0/0 | - | PASS |
| 260 | POST | `/api/cut/{concept_id}/rollback` | write | yes | 401 | 404 | 404 | 7/0/0 | - | PASS |
| 261 | GET | `/api/brand-kits` | read | yes | 401 | 200 | - | - | - | PASS |
| 262 | POST | `/api/brand-kits` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 263 | GET | `/api/brand-kits/{kit_id}` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 264 | PATCH | `/api/brand-kits/{kit_id}` | write | yes | 401 | 200 | 404 | 7/0/0 | - | PASS |
| 265 | POST | `/api/brand-kits/{kit_id}/duplicate` | write | yes | 401 | 200 | 404 | 3/0/4 | - | PASS |
| 266 | DELETE | `/api/brand-kits/{kit_id}` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 267 | POST | `/api/brand-kits/{kit_id}/restore` | write | yes | 401 | 200 | 404 | 3/0/4 | - | PASS |
| 268 | POST | `/api/brand-kits/{kit_id}/assets` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 269 | DELETE | `/api/brand-kits/{kit_id}/assets/{asset_id}` | write | yes | 401 | 404 | 404 | - | - | PASS |
| 270 | GET | `/api/brand-kits/{kit_id}/assets/{asset_id}/file` | read | yes | 401 | 404 | 404 | 3/0/0 | - | PASS |
| 271 | POST | `/api/brand-kits/{kit_id}/screens/preview` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 272 | POST | `/api/brand-kits/{kit_id}/screens` | write | yes | 401 | 400 | 404 | 7/0/0 | - | PASS |
| 273 | GET | `/api/brand-kits/{kit_id}/end-card.png` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 274 | POST | `/api/brand-kits/import` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS (E10) |
| 275 | PUT | `/api/projects/{project_id}/brand-kit` | write | yes | 401 | 200 | 404 | 6/0/1 | tenancy_body | PASS |
| 276 | GET | `/api/projects/{project_id}/brand-kit` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 277 | GET | `/api/scenes/{concept_id}/prompt-preview` | read | yes | 401 | 200 | 404 | 3/0/0 | - | PASS |
| 278 | GET | `/api/plugin/link` | read | yes | 401 | 422 | - | - | - | PASS |
| 279 | POST | `/api/plugin/link` | write | yes | 401 | 400 | - | 4/0/0 | - | PASS |
| 280 | GET | `/api/plugin/connections` | read | yes | 401 | 200 | - | - | - | PASS |
| 281 | POST | `/api/plugin/connections/{token_id}/revoke` | write | yes | 401 | 200 | 404 | - | - | PASS |
| 282 | POST | `/auth/email` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 283 | POST | `/auth/verify` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 284 | POST | `/auth/signup` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 285 | POST | `/auth/login` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 286 | POST | `/auth/forgot` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 287 | POST | `/auth/reset` | write | yes | 422 | 422 | - | 4/0/0 | - | PASS |
| 288 | POST | `/auth/logout` | write | yes | 200 | - | - | - | - | PASS |
| 289 | GET | `/auth/logout` | read | yes | 200 | - | - | - | - | PASS |
| 290 | GET | `/auth/handoff` | read | yes | 200 | 200 | - | - | - | PASS |
| 291 | GET | `/auth/confirm` | read | yes | 200 | 200 | - | - | - | PASS |
| 292 | GET | `/auth/google/login` | read | yes | 200 | 200 | - | - | - | PASS |
| 293 | GET | `/auth/discord/login` | read | yes | 200 | 200 | - | - | - | PASS |
| 294 | GET | `/auth/apple/login` | read | yes | 200 | 200 | - | - | - | PASS |
| 295 | GET | `/auth/callback` | read | yes | 200 | 200 | - | - | - | PASS |
| 296 | GET | `/auth/google/callback` | read | yes | 200 | 200 | - | - | - | PASS |
| 297 | GET | `/auth/discord/callback` | read | yes | 200 | 200 | - | - | - | PASS |
| 298 | GET | `/auth/social/{provider}/start` | read | yes | 200 | 404 | - | - | - | PASS |
| 299 | GET | `/auth/social/{provider}/callback` | read | yes | 404 | 404 | - | - | - | PASS |
| 300 | GET | `/oauth/consent` | read | yes | 400 | 400 | - | - | - | PASS |
| 301 | POST | `/oauth/consent` | write | yes | 400 | 400 | - | 4/0/0 | - | PASS |
| 302 | GET | `/u/{token}` | read | yes | 404 | 404 | - | - | - | PASS |
| 303 | POST | `/u/{token}` | write | yes | 404 | 404 | - | 4/0/0 | - | PASS |
| 304 | GET | `/public/share/{token}` | read | yes | 200 | 200 | - | - | - | PASS |
| 305 | GET | `/public/whats-new` | read | yes | 200 | 200 | - | - | - | PASS |
| 306 | POST | `/billing/webhook` | spend | yes | 400 | - | - | - | stripe | PASS |
| 307 | POST | `/plugin/v1/pair` | write | yes | 200 | 200 | - | 4/0/0 | - | PASS |
| 308 | POST | `/plugin/v1/pair/token` | write | yes | 400 | 400 | - | 4/0/0 | - | PASS |
| 309 | GET | `/plugin/v1/me` | read | yes | 401 | 200 | - | - | plugin | PASS |
| 310 | POST | `/plugin/v1/tools/{name}` | write | yes | 401 | 200 | - | - | plugin | PASS |
| 311 | POST | `/plugin/v1/upload` | write | yes | 401 | 400 | - | - | - | PASS |
| 312 | GET | `/plugin/v1/download/{ref}` | read | yes | 401 | 404 | - | - | plugin | PASS |
| 313 | GET | `/plugin/v1/scenes/{scene_id}/clips` | read | yes | 401 | 200 | - | - | plugin | PASS |
| 314 | GET | `/plugin/v1/looks` | read | yes | 401 | 200 | - | - | - | PASS |
| 315 | POST | `/plugin/v1/looks/run` | write | yes | 401 | 400 | - | - | - | PASS |
| 316 | GET | `/plugin/v1/jobs/{job_id}` | read | yes | 401 | 200 | - | - | plugin | PASS |
| 317 | POST | `/plugin/v1/signout` | write | yes | 200 | - | - | - | - | NOTE (E8) |
| 318 | GET | `/signin` | read | yes | 200 | 200 | - | - | - | PASS |
| 319 | GET | `/ui/accounts` | read | yes | 200 | 200 | - | - | - | PASS |
| 320 | GET | `/ui` | read | yes | 200 | 200 | - | - | - | PASS |
| 321 | GET | `/` | read | yes | 200 | 200 | - | - | - | PASS |
| 322 | GET | `/healthz` | read | no | 200 | 200 | - | - | - | PASS |
| 323 | GET | `/privacy` | read | yes | 200 | 200 | - | - | - | PASS |
| 324 | GET | `/favicon.ico` | read | no | 200 | 200 | - | - | - | PASS |
| 325 | GET | `/icon.png` | read | no | 200 | 200 | - | - | - | PASS |
| 326 | GET | `/robots.txt` | read | yes | 200 | 200 | - | - | - | PASS |
| 327 | GET | `/llms.txt` | read | yes | 200 | 200 | - | - | - | PASS |
| 328 | GET | `/sitemap.xml` | read | yes | 200 | 200 | - | - | - | PASS |
| 329 | POST | `/account/{slug}` | write | yes | 404 | 404 | - | - | - | PASS |
| 330 | GET | `/locations/{space}/photo/{filename}` | read | yes | 404 | 404 | - | - | - | PASS |
| 331 | GET | `/characters/{slug}/photo/{filename}` | read | yes | 200 | 200 | - | - | - | PASS |
| 332 | GET | `/props/{slug}/photo/{filename}` | read | yes | 404 | 404 | - | - | - | PASS |
