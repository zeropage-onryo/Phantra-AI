# 05 — One real end-to-end render (run on Mike's yes, cap 100)

**Run on 2026-11-02, 17:16–17:25 UTC, on Mike's "Yes, cap 100".** It spent **28 credits** of
the 100 cap on the review workspace (5, "Phantra Review", `zp-billing-test`). Every charge
settled at exactly the price shown on the button, and no hold or fal request is left open.

## How it was run

- **The studio UI, driven by headless Playwright.** A local Next dev server
  (`review1102.localhost:3041`) proxied to a local API (`127.0.0.1:8041`) running this branch's
  code (`8ba89087`, no `src/`/`app/` edits) against the **live** database and the live
  `phantra-media` bucket. Sign-in was a handoff token for review@phantra.ai, whose home
  workspace is 5; the script checked that before every click. One local API only (C6), started
  with `FAL_RECOVER=0 PHANTRA_AUTOPILOT=0 DEV_TOOLS=0`.
- **Spend guard.** The API process wrapped `fal._submit_and_wait`. It let exactly two submits
  through, once each: `fal-ai/flux-2-pro`, and `xai/grok-imagine-video/v1.5/lite/image-to-video`
  only at 480p for 5 s. Gemini stills (`nano_banana`), talking photo and `effects.run` were
  blocked outright. The API log shows the two allowed submits and nothing refused.
- **The Final Cut join** went through the Claude listing's connector, `assemble_clips` on
  `/mcp/claude` (workspace 5, production Fly, free). It joined the new clip with gen:107, an
  earlier clip already in workspace 5, because the tool needs at least two clips.
- The scripts and the raw stage log (`timeline.jsonl`) are in the session scratchpad, not
  committed. The screenshots are in [`screens/live/`](screens/live/).

## Credits

| | Available | Held | Source |
|---|---|---|---|
| Before | **343** | 0 | `GET /api/me` credits block, 17:16:56 |
| Still: button and quote | 10 | | "Generate · 10 credits" (FLUX.2 Pro, `1-image-priced-1440.png`) |
| After the still | 333 | 0 | 17:18:36 |
| Clip: button and quote | 18 | | "Generate · 18 credits" (Grok Imagine 1.5 Lite, 5s, 480p, `3-video-priced-1440.png`) |
| Join | 0 | | connector plan `"credits": 0` |
| **After** | **315** | 0 | studio 17:24:37, connector `balance` 17:23 (adjustment lot 500 → 315 left) |

The live `credit_entries` for account 5 on 2026-11-02 (read only):

| id | delta | kind | ref | generation |
|---|---|---|---|---|
| 500 | −10 | hold | `fal-flux2-pro-20261102-171705-…-323431.jpg` | — |
| 501 | 0 | settle | same | 376 |
| 502 | −18 | hold | `wf-20261102-172022-f767….mp4` | — |
| 503 | 0 | settle | same | 377 |

Each settle has a delta of 0, so the amount taken equals the hold, which equals the price on the
button. Quoted 10 + 18 + 0 = 28; spent 343 − 315 = 28. **PASS.**
`fal_requests`: row 90 (grok1.5-lite, held 18) is resolved `rendered` at 17:20:50. The database
has 0 unresolved `fal_requests`.

## Stage timings (UTC)

### 1. Still: FLUX.2 Pro, `/studio/image`

| Stage | Time | From click |
|---|---|---|
| Priced button visible | 17:17:04.07 | — |
| Click Generate | 17:17:04.20 | 0 |
| Job queued (`POST /api/direct/image/run` 200, job 1, `charged: true`) | 17:17:04.96 | 0.8 s |
| Ledger hold written | 17:17:06.20 | 2.0 s |
| fal submit stamped | 17:17:06.45 | 2.3 s |
| Settle written | 17:17:19.62 | 15.4 s |
| R2 file (`Last-Modified`) | 17:17:20 | ~16 s |
| Library row (`generated_assets` gen:302) | 17:17:21 | ~17 s |
| Job `ended_at` | 17:17:25 | ~21 s |
| Studio shows the still (`2-image-done-1440.png`) | 17:17:27.6 | 23.4 s |

### 2. Clip: Grok Imagine 1.5 Lite, 5s, 480p, start frame = the still, `/studio/video`

| Stage | Time | From click |
|---|---|---|
| Click Generate | 17:20:15.34 | 0 |
| Job queued (job 2, 18 credits, `charged: true`) | 17:20:19.38 | **4.0 s** |
| Ledger hold written | 17:20:23.56 | 8.2 s |
| fal submit (receipt persisted, `fal_requests` 90) | 17:20:24.20 | 8.9 s |
| Settle written | 17:20:49.89 | 34.6 s |
| fal request resolved | 17:20:50.25 | 34.9 s |
| R2 file (`Last-Modified`) | 17:20:52 | ~37 s |
| Library row (gen:303) | 17:20:53 | ~38 s |
| Job done, seen by the studio | 17:20:57.69 | **42.4 s** |

The provider ran for about 26 s (submit to settle). About 9 s passed between the click and the
fal submit. Most of it was before the job was queued (4.0 s for the multipart run, which carries
the start frame, against 0.8 s for the still) and between the queue and the hold (4.2 s). These
are single measurements on a shared Mac talking to Supabase across the Atlantic, so treat them
as a lead to profile, not a finding.

### 3. Final Cut join: connector `assemble_clips` (gen:303 + gen:107, cut, 9:16)

| Stage | Time | From call |
|---|---|---|
| `assemble_clips` called | 17:22:32.4 | 0 |
| Job started (production) | 17:22:36 | ~3.6 s |
| R2 file | 17:22:48 | ~16 s |
| Job done (`job` with wait=15, one poll) | 17:22:50 | ~18 s |

The result is gen:304 (generation 378), 11.13 s, 416×736, and an editable cut project
`8a570f0b-…` "QA 2026-11-02 final cut" v1. Credits: 0.

### 4. Library

`/studio/assets` drew all three new items under "November 2, 2026" 2.8 s after navigation
(`4-library-1440.png`). Each carries the trial watermark (red dot + "Phantra", bottom-right),
which is expected: workspace 5 has no plan.

## Media

| Item | Ref | Address | HTTP (`curl -I`) |
|---|---|---|---|
| Still | gen:302 | `https://media.phantra.ai/m/5/renders/fal/flux2-pro-20261102-171705-a26a41533dcaf1e1f407b1d6459c5017.jpg` | 200, image/jpeg, 114,156 B |
| Clip | gen:303 | `https://media.phantra.ai/m/5/renders/fal/wf-20261102-172022-f767cbd35e2f39a41789aa7d5a97a9f8.mp4` | 200, video/mp4, 381,574 B |
| Final Cut | gen:304 | `https://media.phantra.ai/m/5/renders/cut/cut-8a570f0b-c153-466c-a99d-e75e11ebbf8d-v1-66-cd65e54e35783a749247a0a1fe44619b.mp4` | 200, 1,040,217 B |

Python's `urllib` gets **403** from the same addresses; `curl` gets 200. This is the known
bot-blocking on the public host, not a missing file.

## What the live run showed

- **L1 (confirms 02 T4 on production data, minor).** The FLUX.2 still was filed as
  `asset_name` **"Fal image"**, `provider` **"Fal"** (`model_label` is "FLUX.2 Pro"). The clip from
  the same session is named correctly: "Grok Imagine 1.5 Lite video", provider
  "Grok Imagine 1.5 Lite". The Library's provider filter reads
  `Fal · 5 | Grok Imagine 1.5 Lite · 1 | Joined clips · 3 | LTX 2.3 · 1 | Nano Banana · 2 |
  Nano Banana Pro · 3`. Stills on fal's image table are named by the transport; clips are named
  by the model. The fix and its test are in REPORT.md (T4).
- **L2 (known, BACKLOG #26).** The still's fal call left **no `fal_requests` row**.
  `fal.generate_image` calls `_submit_and_wait` without a tracker (`src/fal.py:1663-1696`), while
  the clip's receipt was persisted (row 90). A deploy during a still therefore leaves a submitted
  hold that only `ledger.reap`, run by hand, releases. This is already written down as BACKLOG
  #26. It is noted here because this run shows it on live rows.
- **L3 (measurement).** It took 42 s from click to a watchable 5 s clip and 23 s for a still;
  joining two clips took 18 s. About 9 s of the clip's time came before the provider was called
  (see above).
- The local API and Next logs have no 5xx responses and no tracebacks, and the guard refused
  nothing. Browser console output was not captured.
