# The render listing's half: /mcp as zp-billing-test (2026-10-12)

Run by `ops/connector_walk.py call render …`, one call at a time, right after the Claude listing's walk (`walk-2026-10-13-claude.md`), with the same sign-in. Every answer below is the connector's own, with tokens and URL query strings redacted and dollar-named keys left out where an answer carried one (said where it happened). The cap was 130 credits of account 5's 501; nothing was spent twice, every spend went through a quote and its single-use token.

**11 of 12 expectations PASS. Spent 117 credits: the still 10, scene 408's two keyframes 20, one LTX 2.3 shot 87 (on scene 411, a one-window copy of 408).**

## The plan against the cap

LTX 2.3 renders at 1080p for 87 credits per 6-second shot, and a timed window is fitted UP to the model's shortest length, so the two-window scene 408's clip is two shots, 174 credits: more than the cap leaves after the still and the keyframes (100). The task's own arithmetic (one still, two keyframes, one LTX 2.3 shot = 10 + 20 + 87 = 117) holds only for a ONE-shot clip, so the keyframes were approved on 408 as asked, and the clip on a free `duplicate_scene` copy of 408 with a single six-second window (scene 411, the same two photos and roles). The clip on 408 itself was skipped, and this file says so.

## Verdicts

| # | expectation | verdict | detail |
|---|---|---|---|
| 1 | generate_image with no token answers a quote with a quote_token and draws nothing | PASS | FLUX 1.1 Pro, 10 credits, balance 501 -> 491 |
| 2 | the same call with the token starts a job that ends done with a gen:<id> | PASS | job 1: gen:104, 10 credits, charged True |
| 3 | quote on scene 408 at LTX 2.3 prices two keyframes and a two-shot clip, tokens signed | PASS | keyframes 20, clip 174 ([87, 87]) |
| 4 | approve what=keyframes on 408 ends done; scene 408 then carries a keyframe | PASS | job 1: 20 credits, charged True; scene 408 keyframe True |
| 5 | the two-shot clip on 408 (174) is over the cap's remainder and was skipped | PASS | cap 130; after the still and the keyframes 100 remained; 174 > 100, not approved |
| 6 | duplicate_scene 408 with a one-window prompt makes scene 411 (free) with two photos | PASS | scene 411, 1 shot, 6 s |
| 7 | quote on 411 at LTX 2.3 prices one 6-second shot at 87 | PASS | 87 credits, frame 1080p |
| 8 | approve what=clip on 411 with the quote's token and the same renderer choice ends done; scene 411 is rendered | PASS | job 2: 87 credits, charged True; clip https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/fal/c4 |
| 9 | generate_image once more with the SAME first token answers already_used and charges nothing | PASS | This approval was already used -- it started job 1; poll `job` for it. Nothing new was started or charged. A new render  |
| 10 | credit_history shows one hold and one settle per spend | PASS | 4 holds, 4 settles on 2026-10-12: LTX 2.3 clip, 6s -87, Still · Nano Banana -10, Still · Nano Banana -10, Still · FLUX 1.1 Pro -10 |
| 11 | the balance dropped by exactly the quoted credits, at most 130 in total | PASS | 501 -> 384; spent 117 |
| 12 | no dollar-named key in any answer (the render listing prices in credits) | CHECK | 09-approve-clip-411.json: render.estimate_usd, quote.estimate_usd, quote.renders[0].estimate_usd |

The one CHECK: `approve what=clip` answered the Queue's own JSON, which carries the provider's estimate under dollar-named keys (`render`, `quote`, `quote.renders[0]`); `quote` on the same door drops them. The studio's rule is credits only on a listed server, so the approve answer wants the same `_credits_only` pass its quote already has. Recorded in `docs/tasks/task-connector-submission.md` "As run".

## Spends

| at (UTC) | what | credits | balance after |
|---|---|---|---|
| 2026-10-12T14:25:19 | settle: Still · FLUX 1.1 Pro | 0 | 491 |
| 2026-10-12T14:26:35 | settle: Still · Nano Banana | 0 | 481 |
| 2026-10-12T14:26:45 | settle: Still · Nano Banana | 0 | 471 |
| 2026-10-12T14:27:47 | settle: LTX 2.3 clip, 6s | 0 | 384 |
| 2026-10-12T14:25:08 | hold: Still · FLUX 1.1 Pro | -10 | 491 |
| 2026-10-12T14:26:30 | hold: Still · Nano Banana | -10 | 481 |
| 2026-10-12T14:26:37 | hold: Still · Nano Banana | -10 | 471 |
| 2026-10-12T14:26:49 | hold: LTX 2.3 clip, 6s | -87 | 384 |

## Answers

### 1. image_models

args: `{}`

```json
{
  "default": "flux-pro1.1",
  "available": true,
  "aspects": [
    "1:1",
    "4:5",
    "5:4",
    "3:4",
    "4:3",
    "2:3",
    "3:2",
    "9:16",
    "16:9",
    "21:9"
  ],
  "models": [
    {
      "id": "flux-pro1.1",
      "label": "FLUX 1.1 Pro",
      "note": "Sharp, fast, the default. Text-only (no reference input).",
      "references": false,
      "max_references": 0,
      "credits": 10
    },
    {
      "id": "flux2-pro",
      "label": "FLUX.2 Pro",
      "note": "FLUX's newest; takes up to 9 reference images.",
      "references": true,
      "max_references": 8,
      "credits": 10
    },
    {
      "id": "nano-banana-pro",
      "label": "Nano Banana Pro (fal)",
      "note": "Gemini's image model through fal; strong on references and text.",
      "references": true,
      "max_references": 8,
      "credits": 36
    },
    {
      "id": "seedream4.5",
      "label": "Seedream 4.5",
      "note": "ByteDance; photographic, about 4 megapixels, generates and edits with up to 10 references.",
      "references": true,
      "max_references": 10,
      "credits": 10
    },
    {
      "id": "gpt-image-2",
      "label": "GPT Image 2",
      "note": "OpenAI's image model; strong on text and instructions, takes up to 16 references.",
      "references": true,
      "max_references": 16,
      "credits": 13
    },
    {
      "id": "gpt-image-2.5-flare",
      "label": "GPT Image 2.5 Flare",
      "note": "OpenAI's fast default; text, layouts and edits, up to 16 references.",
      "references": true,
      "max_references": 16,
      "credits": 15
    },
    {
      "id": "gpt-image-2.5-sunburst",
      "label": "GPT Image 2.5 Sunburst",
      "note": "OpenAI's precision tier; fine detail and identity kept across edits, up to 16 references.",
      "references": true,
      "max_references": 16,
      "credits": 15
    },
    {
      "id": "ideogram4.5",
      "label": "Ideogram 4.5",
      "note": "Graphic, typographic, poster-like. Text-only.",
      "references": false,
      "max_references": 0,
      "credits": 15
    }
  ]
}
```

### 2. generate_image (no token: the quote)

args: `{"prompt": "A single pair of over-ear headphones on a slate desk in soft window light, product still, no text"}`

```json
{
  "ok": false,
  "needs_approval": true,
  "can_approve": true,
  "note": "Nothing was spent. This FLUX 1.1 Pro image costs 10 credits; the balance is 501 and would be 491 after it. Show the person what it is and the price in credits, and WAIT for a yes. Only then call again with the SAME arguments plus quote_token from this quote -- it is good for one hour, for exactly this request, and once.",
  "quote": {
    "model": "flux-pro1.1",
    "label": "FLUX 1.1 Pro",
    "aspect": null,
    "references": [],
    "credits": 10,
    "charged": true,
    "balance": 501,
    "balance_after": 491,
    "quote_token": "…",
    "expires_at": "2026-10-12T15:24:05+00:00"
  }
}
```

### 3. generate_image (with the quote's token)

args: `{"prompt": "A single pair of over-ear headphones on a slate desk in soft window light, product still, no text", "quote_token": "…"}`

```json
{
  "job_id": 1,
  "status": "running",
  "label": "image default",
  "note": "started; poll with the `job` tool",
  "quote": {
    "model": "flux-pro1.1",
    "label": "FLUX 1.1 Pro",
    "aspect": null,
    "references": [],
    "credits": 10,
    "charged": true,
    "balance": 501,
    "balance_after": 491
  }
}
```

### 4. job (the still)

args: `{"job_id": 1, "wait": 15}`

```json
{
  "id": 1,
  "kind": "mcp",
  "label": "image default",
  "status": "done",
  "progress": 1.0,
  "detail": "",
  "error": null,
  "ref_id": null,
  "cancellable": true,
  "started_at": "2026-10-12T14:25:08+00:00",
  "ended_at": "2026-10-12T14:25:21+00:00",
  "account_id": 5,
  "credits": 10,
  "credits_held": 0,
  "charged": true,
  "result": {
    "ok": true,
    "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/fal/flux-pro1.1-20261012-142508.jpg",
    "generation_id": 148,
    "references": 0,
    "asset_id": 104,
    "credits": 10,
    "error": null,
    "quote": {
      "model": "flux-pro1.1",
      "label": "FLUX 1.1 Pro",
      "aspect": null,
      "references": [],
      "credits": 10,
      "charged": true,
      "balance": 501,
      "balance_after": 491
    },
    "ref": "gen:104"
  }
}
```

### 5. quote scene_id=408 model=ltx2.3

args: `{"scene_id": 408, "model": "ltx2.3"}`

```json
{
  "scene_id": 408,
  "status": "written",
  "keyframes": {
    "stills": 2,
    "each": 10,
    "credits": 20
  },
  "clip": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 408,
    "provider": "fal",
    "model": "ltx2.3",
    "frame": "1080p",
    "timed": true,
    "durations": [
      6,
      6
    ],
    "signed": true,
    "credits": 174,
    "content_hash": "0834008347a11ce3",
    "renders": [
      {
        "part": 1,
        "seconds": 6,
        "credits": 87,
        "token": "…"
      },
      {
        "part": 2,
        "seconds": 6,
        "credits": 87,
        "token": "…"
      }
    ]
  },
  "balance": 491,
  "credits_needed": 194,
  "affordable": true,
  "note": "show the person this price and wait for a yes; tokens are valid for one hour -- pass them to `approve` with the same renderer choice"
}
```

### 6. duplicate_scene 408 with a one-window prompt (free)

args: `{"scene_id": 408, "prompt": "(0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. No background music. Only diegetic sound: a chair creak. Avoid: on-screen text, logos, hands, any face.", "seconds": 6}`

```json
{
  "id": 411,
  "title": "Reviewer check: Tonal One push-in (copy)",
  "summary": "(0-6s) Close on the Tonal One headphones resting…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-12T14:25:25+00:00",
  "scene_id": 411,
  "project_id": 1,
  "prompt": "(0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. No background music. Only diegetic sound: a chair creak. Avoid: on-screen text, logos, hands, any face.",
  "seconds": 6,
  "shots": [],
  "shots_written": 1,
  "reference_photos": 2,
  "roles": {
    "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"
  },
  "keyframe": null,
  "clips": [],
  "rendered": false,
  "studio_url": "https://phantra.ai/studio/scene/411",
  "next": "`quote` scene_id=411 for the price; show the person, and only on their yes call `approve`",
  "copied_from": 408,
  "copied": {
    "prompt": false,
    "refs": true,
    "project": true
  }
}
```

### 7. quote scene_id=411 model=ltx2.3

args: `{"scene_id": 411, "model": "ltx2.3"}`

```json
{
  "scene_id": 411,
  "status": "written",
  "keyframes": {
    "stills": 1,
    "each": 10,
    "credits": 10
  },
  "clip": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 411,
    "provider": "fal",
    "model": "ltx2.3",
    "frame": "1080p",
    "timed": false,
    "durations": [
      6
    ],
    "signed": true,
    "credits": 87,
    "content_hash": "cfac49ed53838c26",
    "renders": [
      {
        "part": null,
        "seconds": 6,
        "credits": 87,
        "token": "…"
      }
    ]
  },
  "balance": 491,
  "credits_needed": 97,
  "affordable": true,
  "note": "show the person this price and wait for a yes; tokens are valid for one hour -- pass them to `approve` with the same renderer choice"
}
```

### 8. approve scene_id=408 what=keyframes (with the quote's tokens)

args: `{"scene_id": 408, "what": "keyframes", "tokens": ["…", "…"]}`

```json
{
  "ok": true,
  "job_id": 1,
  "keyframes": {
    "stills": 2,
    "each": 10,
    "credits": 20
  },
  "note": "started; poll with the `job` tool"
}
```

### 9. job (the keyframes)

args: `{"job_id": 1, "wait": 15}`

```json
{
  "id": 1,
  "kind": "keyframe",
  "label": "keyframe · Reviewer check: Tonal One push-in",
  "status": "done",
  "progress": 1.0,
  "detail": "2 still(s)",
  "error": null,
  "ref_id": 408,
  "cancellable": false,
  "started_at": "2026-10-12T14:26:29+00:00",
  "ended_at": "2026-10-12T14:26:46+00:00",
  "account_id": 5,
  "credits": 20,
  "credits_held": 0,
  "charged": true
}
```

### 10. approve scene_id=411 what=clip (the quote's token, provider fal, model ltx2.3, frame 1080p, duration 6)

args: `{"scene_id": 411, "what": "clip", "tokens": ["…"], "provider": "fal", "model": "ltx2.3", "frame": "1080p", "duration": 6}`

(dollar-named keys left out of this file: render.estimate_usd, quote.estimate_usd, quote.renders[0].estimate_usd; see the verdicts)

```json
{
  "job_id": 2,
  "render": {
    "provider": "fal",
    "model": "ltx2.3",
    "duration": 6,
    "frame": "1080p"
  },
  "quote": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 411,
    "provider": "fal",
    "model": "ltx2.3",
    "frame": "1080p",
    "timed": false,
    "durations": [
      6
    ],
    "signed": true,
    "credits": 87,
    "content_hash": "cfac49ed53838c26",
    "renders": [
      {
        "part": null,
        "seconds": 6,
        "credits": 87,
        "token": "…"
      }
    ]
  },
  "note": "started; poll with the `job` tool"
}
```

### 11. job (the clip)

args: `{"job_id": 2, "wait": 15}`

Job ids restarted during this half: the API machine redeployed (PR #287 merged to main) between calls, and jobs live in memory; every job still ended done and landed on its scene.

```json
{
  "id": 2,
  "kind": "render",
  "label": "approved · Reviewer check: Tonal One push-in (copy) · fal.ai ltx2.3",
  "status": "done",
  "progress": 1.0,
  "detail": "clip attached",
  "error": null,
  "ref_id": 411,
  "cancellable": false,
  "started_at": "2026-10-12T14:26:49+00:00",
  "ended_at": "2026-10-12T14:27:52+00:00",
  "account_id": 5,
  "credits": 87,
  "credits_held": 0,
  "charged": true
}
```

### 12. generate_image once more, with the SAME first token

args: `{"prompt": "A single pair of over-ear headphones on a slate desk in soft window light, product still, no text", "quote_token": "…"}`

```json
{
  "job_id": 1,
  "status": "running",
  "label": "image default",
  "note": "This approval was already used -- it started job 1; poll `job` for it. Nothing new was started or charged. A new render needs a new quote and a new yes.",
  "already_used": true
}
```

### 13. scene scene_id=408

args: `{"scene_id": 408}`

```json
{
  "id": 408,
  "title": "Reviewer check: Tonal One push-in",
  "summary": "(0-3s) Close on the Tonal One headphones resting…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-12T14:22:06+00:00",
  "scene_id": 408,
  "project_id": 1,
  "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only diegetic sound: the faint rustle of a sleeve, a chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a second pair of hands, any face.",
  "seconds": 8,
  "shots": [
    {
      "n": 1,
      "start": 0,
      "end": 3,
      "seconds": 3,
      "text": "Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight",
      "clip": null
    },
    {
      "n": 2,
      "start": 3,
      "end": 8,
      "seconds": 5,
      "text": "Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband",
      "clip": null
    }
  ],
  "shots_written": 2,
  "reference_photos": 2,
  "roles": {
    "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"
  },
  "keyframe": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c408-20261012-142630.png",
  "clips": [],
  "rendered": false,
  "studio_url": "https://phantra.ai/studio/scene/408"
}
```

### 14. scene scene_id=411

args: `{"scene_id": 411}`

```json
{
  "id": 411,
  "title": "Reviewer check: Tonal One push-in (copy)",
  "summary": "(0-6s) Close on the Tonal One headphones resting…",
  "status": "rendered",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-12T14:25:25+00:00",
  "scene_id": 411,
  "project_id": 1,
  "prompt": "(0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. No background music. Only diegetic sound: a chair creak. Avoid: on-screen text, logos, hands, any face.",
  "seconds": 6,
  "shots": [],
  "shots_written": 1,
  "reference_photos": 2,
  "roles": {
    "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"
  },
  "keyframe": null,
  "clips": [
    "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/fal/c411-s1-20261012-142649.mp4"
  ],
  "rendered": true,
  "studio_url": "https://phantra.ai/studio/scene/411"
}
```

### 15. credit_history

args: `{"limit": 12}`

```json
{
  "items": [
    {
      "id": 63,
      "at": "2026-10-12T14:27:47.533805+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "LTX 2.3 clip, 6s",
      "group": "render",
      "label": "LTX 2.3",
      "link": {
        "kind": "scene",
        "id": 411,
        "title": "Reviewer check: Tonal One push-in (copy)"
      },
      "balance_after": 384
    },
    {
      "id": 62,
      "at": "2026-10-12T14:26:49.788770+00:00",
      "kind": "hold",
      "credits": -87,
      "what": "LTX 2.3 clip, 6s",
      "group": "render",
      "label": "LTX 2.3",
      "link": {
        "kind": "scene",
        "id": 411,
        "title": "Reviewer check: Tonal One push-in (copy)"
      },
      "balance_after": 384
    },
    {
      "id": 61,
      "at": "2026-10-12T14:26:45.808323+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · Nano Banana",
      "group": "still",
      "label": "Nano Banana",
      "link": {
        "kind": "scene",
        "id": 408,
        "title": "Reviewer check: Tonal One push-in"
      },
      "balance_after": 471
    },
    {
      "id": 60,
      "at": "2026-10-12T14:26:37.596664+00:00",
      "kind": "hold",
      "credits": -10,
      "what": "Still · Nano Banana",
      "group": "still",
      "label": "Nano Banana",
      "link": {
        "kind": "scene",
        "id": 408,
        "title": "Reviewer check: Tonal One push-in"
      },
      "balance_after": 471
    },
    {
      "id": 59,
      "at": "2026-10-12T14:26:35.828849+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · Nano Banana",
      "group": "still",
      "label": "Nano Banana",
      "link": {
        "kind": "scene",
        "id": 408,
        "title": "Reviewer check: Tonal One push-in"
      },
      "balance_after": 481
    },
    {
      "id": 58,
      "at": "2026-10-12T14:26:30.272616+00:00",
      "kind": "hold",
      "credits": -10,
      "what": "Still · Nano Banana",
      "group": "still",
      "label": "Nano Banana",
      "link": {
        "kind": "scene",
        "id": 408,
        "title": "Reviewer check: Tonal One push-in"
      },
      "balance_after": 481
    },
    {
      "id": 57,
      "at": "2026-10-12T14:25:19.094819+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · FLUX 1.1 Pro",
      "group": "still",
      "label": "FLUX 1.1 Pro",
      "link": {
        "kind": "render",
        "id": 104
      },
      "balance_after": 491
    },
    {
      "id": 56,
      "at": "2026-10-12T14:25:08.487279+00:00",
      "kind": "hold",
      "credits": -10,
      "what": "Still · FLUX 1.1 Pro",
      "group": "still",
      "label": "FLUX 1.1 Pro",
      "link": {
        "kind": "render",
        "id": 104
      },
      "balance_after": 491
    },
    {
      "id": 41,
      "at": "2026-10-08T19:30:30.120150+00:00",
      "kind": "grant",
      "credits": 500,
      "what": "Adjustment",
      "group": "grant",
      "label": "Adjustment",
      "link": null,
      "balance_after": 501
    },
    {
      "id": 23,
      "at": "2026-09-30T14:56:12.042926+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · Nano Banana Pro",
      "group": "still",
      "label": "Nano Banana Pro",
      "link": {
        "kind": "scene",
        "id": 386,
        "title": "[TEST] keyframe approve #2 (copy of #384)"
      },
      "balance_after": 1
    },
    {
      "id": 22,
      "at": "2026-09-30T14:55:41.423260+00:00",
      "kind": "hold",
      "credits": -33,
      "what": "Still · Nano Banana Pro",
      "group": "still",
      "label": "Nano Banana Pro",
      "link": {
        "kind": "scene",
        "id": 386,
        "title": "[TEST] keyframe approve #2 (copy of #384)"
      },
      "balance_after": 1
    },
    {
      "id": 21,
      "at": "2026-09-30T14:55:28.411505+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · Nano Banana Pro",
      "group": "still",
      "label": "Nano Banana Pro",
      "link": {
        "kind": "scene",
        "id": 386,
        "title": "[TEST] keyframe approve #2 (copy of #384)"
      },
      "balance_after": 34
    }
  ],
  "next": 21,
  "count": 12,
  "note": "credits only, newest first; pass `next` as `before` for the page after"
}
```

### 16. balance

args: `{}`

```json
{
  "available": 384,
  "held": 0,
  "plan": null,
  "lots": [
    {
      "kind": "promo",
      "credits": 100,
      "remaining": 0,
      "granted_at": "2026-09-30T14:38:14.611391+00:00",
      "expires_at": "2026-11-30T14:38:14.611391+00:00"
    },
    {
      "kind": "adjustment",
      "credits": 500,
      "remaining": 384,
      "granted_at": "2026-10-08T19:30:29.460639+00:00",
      "expires_at": "2026-12-08T19:30:29.460639+00:00"
    }
  ],
  "scheduled": [],
  "charged": true,
  "note": "credits, never money; plans and top-ups are in the studio at https://phantra.ai/pricing"
}
```
