# 04 — Connector / MCP walk, quote-only (Agent D), 2026-11-02

Walk window 16:17:43 → 16:24:42 UTC, from this Claude Code session's three MCP connections.
No render, still, effect, voice, sheet or talking photo ran. No `approve` was called on any
surface, no `quote_token` was ever passed back. Signed quote tokens returned by the quotes are
redacted here (they are one-hour capability tokens on Mike's account).

**Credits: workspace 5 343 → 343 (0 held → 0 held); workspace 1 8,133 → 8,133 (0 → 0).**
Both match the 16:13 baselines in `00-baseline.md`. The stdio server has no `balance` tool; every
one of its quotes reported `balance: 8133` and its account's balance (workspace 1) was 8,133 at
the end. `credit_history` on both workspaces shows no entry after 2026-10-30 (ws1 newest id 498,
ws5 newest id 136), so nothing was held or settled.

Latency: no call took noticeably long. Each batch of 4–16 calls came back within one turn
(burst 1 of 16 calls: started 16:20:25, next timestamp 16:20:43 including my own turn time).
Per-call timings were not measured individually; "fast" below means "answered with its batch,
a few seconds at most".

"Structured?" column: **J** = a JSON body (ok shape or a refusal object); **E** = a plain MCP tool
error, `Error executing tool <name>: <message>` (a clear sentence but no code field);
**E0** = a tool error with no message at all.

## Surface 1: `/mcp/claude` (Claude listing, `60190b15-…`), workspace 5 "Phantra Review"

`whoami`: workspace 5 `zp-billing-test`, role member, plan null, member name `""`.

| Tool | Args | Result | Structured? | Latency | Notes |
|---|---|---|---|---|---|
| `balance` (start) | — | 343 / 0 held, plan null, lots promo 100 (0 left) + adjustment 500 (343 left) | J | fast | baseline matches |
| `whoami` | — | ws 5 "Phantra Review" | J | fast | #1 unchanged |
| `elements` | — | 6 props, incl. the 10-22 QA prop (still there) | J | fast | |
| `projects` | `include_archived=true` | 2: project 3 (10-22 QA, not deleted), project 1 | J | fast | |
| `project` | `project_id=1, chat_turns=3` | brief, 8 scenes, 3 refs, 3 renders, empty chat | J | fast | scene 399 still `render started` since 10-08 |
| `project_chat` | `project_id=1, limit=3` | 0 turns, "no chat in this project yet" | J | fast | |
| `scene` | `scene_id=411` | status `removed`, `shots: []`, `shots_written: 1`, 2 refs, 1 clip | J | fast | |
| `library` | `limit=15` | 15 items | J | fast | #6 unchanged |
| `recent` | `limit=5` | 2 projects, 5 scenes, 5 renders | J | fast | |
| `search` | `q="QA"` | project 3, scenes 433/434, the QA prop, the 10-22 cut | J | fast | 10-22 test rows still present |
| `credit_history` | `limit=5` | holds/settles for gen:147/149/150, `next: 132` | J | fast | |
| `video_models` | — | 12 models, default `ltx2.3` (grok1.5, grok1.5-lite, kling4 new since 10-22) | J | fast | ltx2.3 6 s 1080p now 116 cr (87 on 10-22, pricing `2026-10-27-fal-v4`) |
| `recommend_model` | `what="a cheap test", seconds=5` | grok1.5-lite 26, wan3 75, kling3-turbo-pro 105; 3 LTX skipped | J | fast | |
| `preferences` | — | seconds 8, video_model ltx2.3 | J | fast | |
| `recipes` | — | 11 studio + 2 own (incl. `qa-2026-10-22-test`) | J | fast | |
| `recipe` | `name=single-shot` | full body | J | fast | K7: body tells the model to call `make_video` / fill `brief` |
| `what_works` | — | 25 made / 14 kept | J | fast | |
| `score_caption` | short caption | 0.5 neutral, 0 posted videos | J | fast | |
| `open_in_studio` | video, 9:16, project 1 | `…/studio?spark=…&kind=video&frame=720%3A1280&project=1` | J | fast | nothing made |
| `open_in_studio` | image, `source=gen:150` | `…&kind=image&on=gen%3A150` | J | fast | |
| `job` | `job_id=999999` | "no job 999999 -- jobs live in memory…" | E | fast | correct |
| `trim_clip` | `gen:107, 2→99` | "the range ends at 99s, past the end of gen:107 (6.10s long)" | E | fast | correct; library says 6.12 s |
| `assemble_clips` | `[gen:107]` | "name at least 2 clips to join (gen:<id> from `renders`)" | E | fast | K7: `renders` is not on this listing (10-22 cosmetic, unfixed) |
| `reformat` | `gen:999999, 1:1` | "no render 999999 on this account -- `library` lists them" | E | fast | no row |
| `create_project` | "QA 2026-11-02 connector walk (delete me)" | project **8** | J | fast | WRITE (listed below); `next` names `save_chat` (K7) |
| `write_scene` | 4 s, one `(0-4s)` beat, project 8, no refs | scene **464**, `needs_reference: true`, `status: "written"` | J | fast | WRITE; K8 status says written while note says draft |
| `quote` | `scene_id=464` (draft) | "no reference photos attached -- scene 464 is a draft…" | E | fast | reference gate holds |
| `write_scene` | `scene_id=464`, refs=[Tonal One photo] | rewritten, refs 1 | J | fast | same row |
| `quote` | `464` (default) | ltx2.3 1080p `durations:[6]` 116 + keyframes up to 2×10 = 136 | J | fast | #4 / K3 |
| `quote` | `464, model=ltx2.3` | same, 6 s | J | fast | K3 |
| `quote` | `464, ltx2.3, frame=720p` | "ltx2.3 does not render resolution '720p' -- one of ['1080p','1440p','2160p']" | E | fast | refuse-never-clamp holds |
| `quote` | `464, model=sora9` | "fal.ai has no model 'sora9' -- one of [12 ids]" | E | fast | |
| `quote` | `464, model=kling4` | `durations:[5]`, 118 | J | fast | K3: kling4 takes 3-30 s, scene is 4 s |
| `quote` | `464, kling4, duration=4` | `durations:[4]`, 95 | J | fast | 4 s IS legal |
| `quote` | `464, seedance2-fast, 480p` | `durations:[5]`, 87 | J | fast | K3: takes 4-15 s |
| `quote` | `464, wan3, 480p` | `durations:[5]`, 38 | J | fast | K3: takes 2-10 s |
| `quote` | `scene_id=999999` | "no scene 999999" | E | fast | |
| `quote` | `411` (removed) | priced 136, `status: "removed"`, `approve_url` …/scene/411 | J | fast | #3 / K4 |
| `quote` | `433` (10-22 4 s scene) | ltx2.3 `durations:[6]` 116 | J | fast | #4 |
| `quote` | `433, ltx2.3, duration=5` | "ltx2.3 does not render duration 5 -- one of [6, 8, 10]" | E | fast | |
| `quote` | `433, wan3, 480p, duration=4` | 30 (48 on 10-22) | J | fast | re-priced since 10-22 |
| `quote` | `431` (two beats, 8 s) | ltx2.3 `one_clip: true`, `durations:[8]`, 154 + 20 | J | fast | a timed scene uses its own length |
| `scene` | `431` | 2 shots 0-4 / 4-8 | J | fast | |
| `duplicate_scene` | `scene_id=999999` | "no scene 999999" | E | fast | no row |
| `save_recipe` | `name=single-shot` | "'single-shot' is the studio's own recipe -- pick another name" | E | fast | no row |
| `add_element` | `source=gen:999999` | "no render 999999 on this account" | E | fast | no row |
| `add_element` | `source=http://127.0.0.1/x.jpg` | "the picture's address must start with https://" | E | fast | no row |
| `set_preferences` | `seconds=8` (current value) | ok, `"changed": ["seconds"]` | J | fast | WRITE; #5 / K5 |
| `set_preferences` | `video_model=sora9` | "video_model is one of [...], got 'sora9'" | E | fast | no write |
| `share_link` | `gen:107, hours=1` | presigned R2 URL, `phantra-ltx-107.mp4`, expires 17:20:18 UTC | J | fast | once; URL not reproduced here |
| `upload_link` | `purpose=reference` | one-time `https://api.phantra.ai/u/<token>`, 1800 s | J | fast | once; not opened; K10 |
| `feedback` | QA note, `tool=quote`, `ref=464` | saved, id **8** | J | fast | WRITE |
| `balance` (end) | — | 343 / 0 held | J | fast | **matches** |

Burst sets (below) also exercised `whoami`, `recent`, `library` (incl. `kind=video`), `projects`,
`search`, `preferences`, `recipes`, `credit_history`, `what_works`, `scene`, `project` (8),
`project_chat`, `recommend_model`, `recipe` (ad), `score_caption` a second time.

Not called on this listing: `reformat` / `trim_clip` / `assemble_clips` success paths (each would
make a new library row; 10-22 exercised the reformat job, and the refusals above prove the
validation), `job` on a real id (no job started), `add_element` success (10-22 did it).

## Surface 2: `/mcp` (ChatGPT listing, `71f4353e-…`), workspace 1 "Phantra AI" (Mike's)

`whoami`: workspace 1 `phantra`, role owner, member "Mike", plan null. Reads only, plus
refusal-only calls. **Every write and every run tool was left uncalled**; the permission
classifier also denied the first quote-only `generate_image` and a refusal-only
`assemble_clips`, and after that no further run or write tool was tried here.

| Tool | Args | Result | Structured? | Latency | Notes |
|---|---|---|---|---|---|
| `balance` (start) | — | 8,133 / 0 held, plan null, 7 lots | J | fast | baseline matches |
| `whoami` | — | ws 1, owner Mike | J | fast | |
| `elements` | — | 6 (Michael, Street drummer (AI), 4 Gygler / check props) | J | fast | carries `display_note` for ChatGPT |
| `projects` | `limit=5` | 2 (7 Halloween try-on, 6 Gygler test) | J | fast | |
| `recent` | `limit=3` | projects 7/6, scenes 454/453/451, renders gen:280-278 | J | fast | |
| `library` | `limit=8` | gen:273-280 | J | fast | K6: Kling clips gen:276-280 report `seconds/size/frame/aspect: null` |
| `project` | `6, chat_turns=2` | look, 4 scenes, 5 refs, 4 renders (incl. Final cut gen:241) | J | fast | |
| `project_chat` | `6, limit=2` | 0 turns | J | fast | |
| `scene` | `453` | rendered, 3 shots 5/3/7 s, 3 clips | J | fast | |
| `search` | `q=Gygler` | 2 projects, 2 scenes, 2 elements, 2 renders, 2 cuts | J | fast | |
| `credit_history` | `limit=4` | LTX 2.3 6 s holds −116, settles; newest id 498 (10-30) | J | fast | K11: `link: null` on these renders |
| `image_models` | — | 8 models, default flux-pro1.1, credits per image | J | fast | K8: flux2-pro note "up to 9" vs `max_references: 8` |
| `video_models` | — | 12 models, same as `/mcp/claude` | J | fast | |
| `preferences` | — | seconds 10, ltx2.3 | J | fast | |
| `recommend_model` | cheap, 4 s, budget 60 | grok1.5-lite 21, wan3 60; 10 skipped with reasons | J | fast | |
| `what_works` | — | 250 made / 46 kept; 1 posted (scene 375, 257 views) | J | fast | `gen4_turbo` row still counted (C5 from 10-22) |
| `recipes` / `recipe` | `product-still` | 11 + 1 own; full body | J | fast | K7: body names `find_references`, `make_image` |
| `score_caption` | short caption | 0.5, `enough_data: true`, `reasons: []`, 6 posted | J | fast | |
| `job` | `999999` | "no job 999999 …" | E | fast | |
| `quote` | `scene_id=454` (3 shots, 15 s) | keyframes 3×10 = 30 + ltx2.3 parts 6/6/8 s = 386 → 416, signed tokens | J | fast | K3: windows 5/3/7 s billed as 20 s, no line; tokens NOT used |
| `quote` | `451` (no refs) | "no reference photos attached -- scene 451 is a draft…" | E | fast | gate holds |
| `quote` | `411` (ws 5's scene) | "no scene 411" | E | fast | tenancy holds |
| `trim_clip` | `gen:280, 2→999` | "the range ends at 999s, past the end of gen:280 (5.03s long)" | E | fast | refusal, no row |
| `reformat` | `gen:107` (ws 5's render) | "no render 107 on this account" | E | fast | tenancy holds |
| `duplicate_scene` | `464` (ws 5's scene) | "no scene 464" | E | fast | tenancy holds |
| `generate_image` | quote-only (no token), flux-pro1.1 | **not run: denied by the Claude Code permission classifier** | — | — | |
| `assemble_clips` | `[gen:280]` (refusal check) | **not run: denied by the classifier** ("Modify Shared Resources") | — | — | |
| `balance` (end) | — | 8,133 / 0 held | J | fast | **matches** |

Not called on this listing (Mike's live account): `approve`; `edit_image`, `remove_background`,
`animate_still`, `camera_move`, `upscale_clip`, `add_sound`, `reframe_clip` (each description does
promise the first call only quotes, but after the classifier refused `generate_image`'s quote I
did not try the rest); `add_element`, `create_project`, `write_scene`, `feedback`,
`set_preferences`, `save_recipe` (writes); `share_link`, `upload_link` (once each was spent on
ws 5).

## Surface 3: stdio `phantra-ai` (Claude Desktop's studio server), acts in workspace 1

The process answering this session: PID 76937 / 77003, `venv/bin/python -m src.mcp_server`
from the MAIN checkout, started **Fri Oct 30 18:06 2026**. See K1.

| Tool | Args | Result | Structured? | Latency | Notes |
|---|---|---|---|---|---|
| `projects` | `limit=5` | same 2 projects as ws 1 | J | fast | |
| `elements` | — | same 6 as ws 1 | J | fast | |
| `renders` | `limit=5` | gen:276-280 | J | fast | K8: field `provider` holds "Kling 3 Turbo Pro" |
| `project` | `7, chat_turns=0` | look, 0 scenes, 25 renders | J | fast | |
| `project_chat` | `6, limit=2` | 0 turns | J | fast | |
| `video_models` | — | **10 models: no grok1.5 / grok1.5-lite**; USD per second; ltx2.3 1080p $0.06/s, verified 2026-09-26 | J | fast | K1 |
| `image_models` | — | 8 models in USD (description says dollars) | J | fast | |
| `effects` | `category=finish` | 6 finish effects with options and USD pricing | J | fast | |
| `prompt_craft` | `refine`, ltx2.3 | instruction with 5 guide excerpts | J | fast | the LTX guide excerpt says "do not include timestamps" while the appended rule says keep every `(0-3s)` window: contradictory instructions to the model (cosmetic) |
| `images_for` | `query=…, limit=2` | **`Error executing tool images_for`, no message** | E0 | fast | K2 |
| `images_for` | retry, `limit=1` | same | E0 | fast | K2 |
| `job` | `999999` | "no job 999999 …" | E | fast | |
| `cancel_job` | `999999` | "no job 999999 -- jobs live in memory…" | E | fast | |
| `generate_video` | 1st call, ltx2.3 6 s 1080p, no token | quote: **87 credits**, usd 0.36, `pv 2026-09-26-fal-v3`, balance 8133 → 8046, `state: quote` | J | fast | no job id; K1: remote listings price the same clip 116 |
| `generate_image` | 1st call, flux-pro1.1 1:1 | quote 10 credits, `state: quote` | J | fast | no job id |
| `apply_effect` | 1st call, `upscale` on gen:280 | quote 97 credits (5.042 s source measured) | J | fast | no job id |
| `element_sheet` | 1st call, Street drummer (AI) | quote 15 credits, `replaces_sheet: false` | J | fast | no job id |
| `voice_preview` | 1st call, 87-char script | quote 10 credits, ElevenLabs v3 / Rachel | J | fast | no job id |
| `edit_clip` | 1st call, stage frame on gen:280 | quote 10 credits; lists kling-o1 153, kling-o1-pro 204, flux-3 37 for the clip stage | J | fast | no job id |
| `talking_photo` | 1st call, `audio=asset:999999`, no consent | "`consent` must be true…" | E | fast | refused before pricing (K13) |
| `dub_clip` | 1st call, gen:280 → es, no consent | "`consent` must be true…" | E | fast | refused before pricing (K13) |
| `ui_probe` | — | view `ui://phantra/probe-955e130200.html`; client advertised `io.modelcontextprotocol/ui` | J | fast | |
| `ui_probe_report` | — | advertised true, **read false**, handshake/result/bridge/clicked false: "advertised MCP Apps but never read the view" | J | fast | K12 |
| `import_file` | `/etc/hosts` (refusal check) | **not run: denied by the classifier** | — | — | |

Every quote-first call answered `ok: false, needs_approval: true, state: "quote"` with "Nothing was
spent", carried no job id, and showed balance 8,133; the account ended at 8,133.

Not called: `add_element`, `create_project`, `save_chat`, `assemble_clips`, `prepare_post`
(writes on Mike's account), every second call with a `quote_token`.

## Burst test (`/mcp/claude`, 10-22 issue #2)

| Burst | Calls in one message | Successes | Transport refusals ("rate-limiting" / "isn't responding") |
|---|---|---|---|
| 1 (16:20:25) | 16 reads: balance, whoami, recent, library, video_models, elements, projects, search, preferences, recipes, credit_history, what_works, scene, project_chat, recommend_model, recipe | **16** | **0** |
| 2 (16:20:43) | 16 reads: balance ×2, whoami ×2, recent, library ×2, video_models, elements, projects, search, scene, project, credit_history, score_caption, preferences | **16** | **0** |

32 of 32 reads answered. Not reproduced. Caveat: 10-22's failures were five WRITES and one read
in a mixed burst; this pass sent reads only (the brief keeps writes on the live database to a
minimum), so a write-heavy burst is still untested.

## Re-check of the 10-22 connector issues

| # | 10-22 issue | 2026-11-02 | Evidence |
|---|---|---|---|
| 1 | Claude listing acts in ws 5, not Mike's ws 1 | **Unchanged** (Mike's call). The ChatGPT listing in this session acts in ws 1 as owner | `whoami` on each listing |
| 2 | Burst of 16 → 5 rate-limited, 1 "isn't responding" | **Not reproduced** for reads: 32/32 ok in two bursts | burst table |
| 3 | `quote` prices a removed scene | **Still open.** Scene 411 (`status: removed`) priced 136 credits with `approve_url`; the response now carries `"status": "removed"` but no refusal and no line | `quote(411)` |
| 4 | 4 s scene on ltx2.3 priced at 6 s with no note | **Still open, and broader** (K3): a single-beat scene's own `seconds` is not used at all; every model prices its DEFAULT length (kling4 5 s, wan3 5 s, seedance2-fast 5 s, ltx2.3 6 s) although three of them take 4 s. A timed scene's windows are fitted up silently too (scene 454: 5/3/7 s → 6/6/8 s) | `quote(464)` ×5, `quote(454)` |
| 5 | `set_preferences` to the current value says `changed` | **Still open**: `seconds=8` → `"changed": ["seconds"]`, new `set_at` | `set_preferences(seconds=8)` |
| 6 | `library` nulls on renders, 600 s on still uploads | **Still open**, on both listings: ws 5 gen:147-159 nulls, `asset:3-7` (512×512 jpg) `seconds: 600.0`; ws 1 Kling clips gen:276-280 nulls (trim says gen:280 is 5.03 s) | `library` on both |

## Findings

| Id | Severity | Surface | Finding | Evidence |
|---|---|---|---|---|
| K1 | **major** | stdio `phantra-ai` (Claude Desktop) | The studio server Desktop launches runs stale code. It is started from the main checkout, which is on `claude/sheet-gpt-image-25` at `37f56282` (2026-10-26), **264 commits behind `origin/main`**; the process has been up since 2026-10-30 18:06. Effects seen: `video_models` lists 10 models (no `grok1.5`, `grok1.5-lite`); ltx2.3 is priced at $0.06/s (`pricing_version 2026-09-26-fal-v3`), so a 6 s 1080p clip quotes **87 credits on Desktop vs 116 on `/mcp` and `/mcp/claude`** (`2026-10-27-fal-v4`, $0.08/s in `origin/main` `src/fal.py:213`); Seedance draft frames show `null`. An approve on Desktop would hold the old price. Ops, Mike's call: update that checkout (or point `ops/claude-desktop-mcp.json` at one that tracks main) and restart Desktop | `ps` (PIDs 76937/77003, lstart Oct 30 18:06); `git -C <main> rev-list --count HEAD..origin/main` = 264; `grep prices` in both checkouts; `generate_video` quote vs `quote(464, ltx2.3)` |
| K2 | **major** | stdio `images_for` (also on `origin/main`) | `images_for` always fails with a message-less `Error executing tool images_for`. The Desktop log shows a pydantic `ValidationError` on the tool's output: `ImageSearch.sources` is declared `list[Any]` (`src/mcp_shapes.py:248`) but `find_images` returns `imagesearch.sources()`, a **dict** (`src/imagesearch.py:126`). Both are the same on `origin/main`. The tool is dead, and an agent cannot tell it from an outage | 2 of 2 calls; `~/Library/Logs/Claude/mcp-server-phantra-ai.log` lines 1284-1357 |
| K3 | minor | `quote` on `/mcp/claude` and `/mcp` | 10-22 #4, root cause: for a scene with one beat (`timed: false`), the quote ignores the scene's `seconds` and prices the model's default length (`pricing.estimate`: "a whole scene renders at the model's default length"). Scene 464 is 4 s: kling4 → 5 s 118 cr (95 at 4 s), wan3 480p → 5 s 38, seedance2-fast 480p → 5 s 87, ltx2.3 → 6 s 116; nothing in the answer says the length differs from the scene. Timed scenes fit each window up silently (scene 454: 15 s billed as 20 s of clip, 386 cr) | quotes above |
| K4 | minor | `quote` | 10-22 #3 unchanged: a `removed` scene is priced and given an `approve_url` | `quote(411)` |
| K5 | cosmetic | `set_preferences` | 10-22 #5 unchanged | above |
| K6 | cosmetic | `library` (both listings) | 10-22 #6 unchanged, also on ws 1's Kling clips | above |
| K7 | cosmetic | `/mcp/claude` hints and recipes | Text names tools this listing does not have: `assemble_clips` refusal "from `renders`" (unfixed since 10-22); `create_project` / `project` `next` "`save_chat` keeps this conversation" (stdio only); the recipes are the studio brain's and say `make_video`, `make_image`, `find_references`, "keep `brief`" | quoted responses |
| K8 | cosmetic | labels, all surfaces | `search` lists elements as kind `product`, `elements` says `prop`; `search` shows render model "Fal" for gen:150 (flux2-pro) on ws 5 but "Grok Imagine 1.5 Lite" on ws 1; stdio `renders` puts a model label in `provider`; `image_models` flux2-pro note "up to 9 reference images" vs `max_references: 8`; `preferences.image_model` offers `nano`, which `image_models` does not list; `write_scene` returns `status: "written"` for a draft whose note says "saved as a draft"; `trim_clip` says gen:107 is 6.10 s, `library` 6.12 s | responses above |
| K9 | minor | all three surfaces | Every refusal (reference gate, bad renderer, unknown id, consent, studio recipe name) is a plain MCP tool error, `Error executing tool <name>: <sentence>`, with no code field. The sentences are clear, and credit refusals are documented as structured, but a client cannot branch on, e.g., `needs_reference` vs `bad_renderer` vs an outage | every E row |
| K10 | cosmetic | `upload_link` | The one-time URL's token is a signed but readable payload carrying the account id and the signed-in user's UUID (base64 JSON before the signature). Not a secret leak; worth knowing since the link is handed to people | `upload_link` response (token not reproduced) |
| K11 | cosmetic | `credit_history` ws 1 | The 2026-10-30 LTX 2.3 holds/settles (ids 495-498) carry `link: null`, so the entry cannot be traced to its render | `credit_history(limit=4)` |
| K12 | info | stdio `ui_probe` | This client (`local-agent-mode-phantra-ai 1.0.0`, protocol 2025-11-25) advertises MCP Apps but never read the view (`read: false`). The ChatGPT app UI cannot be verified from this session; the probe only reports on the calling client | `ui_probe_report` |
| K13 | info | stdio `talking_photo`, `dub_clip` | Without `consent: true` both refuse before quoting, so a model cannot show a price before asking for consent. Consistent with "never set it on their behalf"; noted because every other spend tool quotes first | refusals above |

Smaller notes (no id): ws 5 project 1 scene 399 still reads `render started` (since 2026-10-08);
`prompt_craft`'s LTX excerpt says to drop timestamps while its appended rule says keep every
window; the 10-22 test rows in ws 5 were never deleted (project 3, scenes 433/434, the QA prop,
recipe `qa-2026-10-22-test`, gen:159).

## Rows written (all workspace 5 `zp-billing-test`, for Mike to delete)

- project **8** "QA 2026-11-02 connector walk (delete me)"
- scene **464** "QA 2026-11-02 test scene (delete me)" (in project 8; refs = Tonal One photo)
- feedback note id **8** ("QA 2026-11-02 connector walk (delete me): …", tool `quote`, ref 464)
- one `set_preferences` entry (seconds 8 → 8, `set_at` 2026-11-02 16:20:08; no effective change)
- a 1-hour share link for `gen:107` (expired 17:20 UTC) and a 30-minute upload link (unused); both expire on their own

Nothing was written in workspace 1. The stdio quotes wrote no rows that their answers show (no
job, no asset); their single-use quote tokens expire at ~17:23 UTC unused.
