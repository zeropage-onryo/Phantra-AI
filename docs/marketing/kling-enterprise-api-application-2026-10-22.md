# Kling AI (Kuaishou) enterprise API application: Kling 4.0

**Draft, not sent. Mike to review.** 2026-10-22. Group 11 stretch of
`docs/tasks/task-overnight-2026-10-22.md`; it feeds `fal.SLOTS["kling4"]`
(branch `claude/overnight-vesper`), off until the official API opens.

## Where this goes

Kling's developer platform (`https://kling.ai/dev`) has three doors: API Documentation,
Pricing & Purchase (prepaid unit packages) and an "API Service Enterprise Plan" reached by
business inquiry. The portal is JavaScript-rendered and unreadable from here, so the headings
below are what third-party write-ups say it asks (company, use case, approval, then a key
with its own credit pool) plus the usual enterprise fields. Kling's 2026-10-15/19 launch
post lists API access for enterprise customers and developers as **coming soon** for 4.0, so
this asks to be in the first wave. `[MIKE: open kling.ai/dev signed in, match these headings
to the live form, drop what it does not ask.]`

## Applicant

- **Company:** Phantra AI, operator of phantra.ai `[MIKE: legal name, jurisdiction]`
- **Website:** https://phantra.ai; connector docs at https://phantra.ai/mcp
- **Contact:** support@phantra.ai `[MIKE: enterprise forms want a named signatory; the
  site's legal pages carry no personal name, so decide who signs]`
- **Region:** United States `[MIKE: confirm]`; servers on Fly.io (US), media on Cloudflare R2
- **Existing Kling account:** `[MIKE: global developer-portal id, if any]`

## What Phantra is

An AI production studio: a person brings an idea and their own photos, the studio writes a
scene as timed shots, prices it in credits, renders each shot on a dated table of video
models, then cuts and finishes it in a built-in editor. Nothing renders without a priced
approval and a credit-ledger hold before the provider call. Models reach the studio through
fal.ai today, plus a Claude/ChatGPT connector (MCP). Pre-launch, on a 500-user founding sprint.

## What Phantra does with Kling today

Through fal.ai (`src/fal.py` `VIDEO_MODELS`, re-checked 2026-09-26): **Kling v3 Turbo Pro**,
text-to-video and image-to-video, 3-15 s, 1080p, $0.14/s, the default for the `kling`
platform in every scene plan. Through `src/effects.py`: **Kling v1.6 Standard effects**, 98
templates on a still, 5 or 10 s, $0.056/s. A 5 s Kling clip costs 168 credits ($0.70
provider at a 2.4x markup). Kling is one of five video families offered (Kling, Veo,
Seedance, LTX, Wan).

## Why Kling 4.0 and how it is routed

The 4.0 slot exists in code, switched off (`PHANTRA_KLING_4`; endpoint ids and prices
`None`; never offered until both are filled from the official API, never via a reseller or
relay). Its routing rule: Kling 4.0 for **a single continuous shot of 15-30 s** and for
**reference-heavy scenes (3+ subject, product or place references)**, where 4.0's 30 s
single pass and Omni Reference matter most; everything else keeps its current model. Every
4.0 render still passes the priced card and the hold.

## Expected volume (estimates)

From `docs/stats/cost-per-effect-2026-10-22.md` and the sprint plan:

- Month one, worst case: 500 members, 310,000 granted credits, about $1,292 provider spend.
  If Kling 4.0 takes the single-take and reference-heavy share, estimated at 25-40% of video
  spend `[MIKE: today's Kling share from the generations table]`: roughly **$320-520/month,
  2,300-3,700 output seconds, 230-370 ten-second clips** at the published 3.0 Turbo API
  rate ($0.14/s).
- 500 paying Standard members (1,500 credits each): 750,000 credits, about $3,125 provider;
  the same share gives **$780-1,250/month, 5,600-8,900 seconds**.
- Concurrency: 5-20 jobs at peak, one shot at a time per scene.
- Months 3-6: `[MIKE: the growth number]`.

The smallest published prepaid package is $700 for 5,000 units, 180-day expiry, 20
concurrent tasks (third-party page, 2026-10-21; confirm on the portal). `[MIKE: a package,
or the enterprise plan with net terms]`

## Integration

Server-to-server from the Phantra API (Python), one adapter mirroring the fal one: create
task, persist the task id at submit, poll or take a callback, settle the hold against the
result. Inputs: prompt, 0-10 image references (character, product, place; the first
anchors), optional start frame and video references; outputs stored under the account's own
R2 key. No fine-tuning, no resale of raw access: Kling is a named model on the picker,
logged under its own name on every render.

## Content policy

Every render is tied to a signed-in account on a plan or trial with a ledger hold. Scenes are
held to the person's own photographs; prompts carry an avoid list; no political, sexual or
minor-depicting content; https://phantra.ai/terms and https://phantra.ai/privacy bind every
account. Phantra will follow Kling's content guidelines, disclosure rules and takedown
requests; outputs are labelled AI-made on the public site. `[MIKE: does Kling require its
own moderation call, or accept ours?]`

## What we need from the API

1. **Model id(s)** for Kling 4.0 (full and Flash): separate endpoints or a `model_name`.
2. **Per-second pricing** by resolution (720p / 1080p / 4K) and audio on/off.
3. **Legal durations** (3-30 s; enum or range) and the extension path toward 2 min.
4. **Aspect ratios** (16:9, 9:16, 1:1, 21:9) and resolution limits per ratio.
5. **Image and video references**: limits, subject binding, URL or hosted asset id.
6. **Callback (webhook) or polling**: a signed callback preferred; else status polling with
   retention long enough to survive a deploy.
7. **Rate and concurrency limits**, time-outs, and the refund rule for a failed task.
8. A **sandbox or test allowance** before paid traffic.

## Sources (read 2026-10-22)

- https://kling.ai/dev (three doors; body not readable without JavaScript)
- https://x.com/Kling_ai/status/2110747537187709424 (4.0 fully available; API coming soon)
- https://www.remio.ai/post/kling-4-0-release-goes-wide-but-mcp-and-cli-access-shift-the-real-contest
  (broad release 2026-10-19; enterprise/developer API forthcoming)
- https://www.toolcolumn.com/pricing/kling-ai-pricing (packages, concurrency; 2026-10-21)
- https://pixverse.ai/en/blog/kling-4-release-date (2026-10-13; Flash vs full specs)
- https://www.cometapi.com/kling-4-0-explaineds-guide/ (2026-10-16; 21:9, 15 references)
- https://anycap.ai/page/en-US/news/kling-ai-review-2026 (portal application steps; 410 on re-read)
