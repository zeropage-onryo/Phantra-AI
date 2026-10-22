# Reviewer record: /mcp (the ChatGPT door) as zp-billing-test (2026-10-16)

Run by `ops/connector_walk.py call render …`, free and read tools only, with the same sign-in as the Claude door walk. Nothing was spent: `generate_image` was called with no `quote_token`, which returns a price and draws nothing, and `approve`, `apply_effect` and every other spending call were left out. URL query strings are redacted.

The card (src/mcp_widget.py) is declared on exactly `quote`, `generate_image` and `job`; see `screens/inspector-render.json` (37 tools).

| # | tool | arguments | result |
|---|---|---|---|
| 1 | whoami | `{}` | answered |
| 2 | balance | `{}` | answered |
| 3 | credit_history | `{}` | answered |
| 4 | projects | `{}` | answered |
| 5 | project | `{"project_id": 1}` | answered |
| 6 | elements | `{}` | answered |
| 7 | library | `{}` | answered |
| 8 | recent | `{}` | answered |
| 9 | search | `{"query": "headphones"}` | answered |
| 10 | video_models | `{}` | answered |
| 11 | image_models | `{}` | answered |
| 12 | recommend_model | `{"what": "a cheap test of a short product clip"}` | answered |
| 13 | preferences | `{}` | answered |
| 14 | recipes | `{}` | answered |
| 15 | what_works | `{}` | answered |
| 16 | scene | `{"scene_id": 408}` | answered |
| 17 | quote | `{"scene_id": 408}` | answered |
| 18 | generate_image | `{"prompt": "A pair of headphones on a slate desk in soft window light.", "model": "", "aspect": ""}` | answered |
| 19 | scene | `{"scene_id": 375}` | refused (another workspace's scene: refusal expected) |

## Answers

### 1. whoami

args: `{}`

```json
{
  "workspace": {
    "id": 5,
    "name": "Phantra Review",
    "slug": "zp-billing-test",
    "created_at": "2026-09-30T14:38:08"
  },
  "plan": null,
  "member": {
    "name": "",
    "role": "member"
  },
  "signed_in_person": true,
  "studio_url": "https://phantra.ai",
  "note": ""
}
```

### 2. balance

args: `{}`

```json
{
  "available": 374,
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
      "remaining": 374,
      "granted_at": "2026-10-08T19:30:29.460639+00:00",
      "expires_at": "2026-12-08T19:30:29.460639+00:00"
    }
  ],
  "scheduled": [],
  "charged": true,
  "note": "credits, never money; credits are added in the Phantra studio"
}
```

### 3. credit_history

args: `{}`

```json
{
  "items": [
    {
      "id": 107,
      "at": "2026-10-16T18:44:30.048120+00:00",
      "kind": "settle",
      "credits": 0,
      "what": "Still · FLUX 1.1 Pro",
      "group": "still",
      "label": "FLUX 1.1 Pro",
      "link": null,
      "balance_after": 374
    },
    {
      "id": 106,
      "at": "2026-10-16T18:44:22.906786+00:00",
      "kind": "hold",
      "credits": -10,
      "what": "Still · FLUX 1.1 Pro",
      "group": "still",
      "label": "FLUX 1.1 Pro",
      "link": null,
      "balance_after": 374
    },
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
    },
    {
      "id": 20,
      "at": "2026-09-30T14:54:59.336088+00:00",
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
      "balance_after": 34
    },
    {
      "id": 19,
      "at": "2026-09-30T14:54:41.834292+00:00",
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
      "balance_after": 67
    },
    {
      "id": 18,
      "at": "2026-09-30T14:54:11.388208+00:00",
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
      "balance_after": 67
    },
    {
      "id": 17,
      "at": "2026-09-30T14:38:15.275282+00:00",
      "kind": "grant",
      "credits": 100,
      "what": "Trial credits",
      "group": "grant",
```

### 4. projects

args: `{}`

```json
{
  "count": 1,
  "projects": [
    {
      "id": 1,
      "title": "Spring product spots",
      "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no f",
      "has_look": false,
      "scenes": 5,
      "rendered": 0,
      "archived": false,
      "updated_at": "2026-10-16T18:40:07.618820+00:00",
      "cover": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png"
    }
  ],
  "truncated": false
}
```

### 5. project

args: `{"project_id": 1}`

```json
{
  "id": 1,
  "title": "Spring product spots",
  "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no faces.",
  "look": "",
  "archived": false,
  "created_at": "2026-10-08T19:48:06.392097+00:00",
  "updated_at": "2026-10-16T18:40:07.618820+00:00",
  "learned": [
    {
      "kind": "pick",
      "text": "PICKED “Reviewer check: Tonal One push-in (copy)” — (0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. No background music. Only diegetic sound: a chair creak. Avoid: on-screen text, logos, hands, any face.",
      "concept_id": 411,
      "at": "2026-10-12T14:26:49+00:00"
    }
  ],
  "scenes": [
    {
      "id": 408,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-12T14:22:06+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png",
      "clip": null
    },
    {
      "id": 401,
      "title": "Kumo: the whisk",
      "summary": "A slow-motion product moment for the matcha tin",
      "status": "idea",
      "is_scene": false,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:47+00:00",
      "prompt": "",
      "still": null,
      "clip": null
    },
    {
      "id": 400,
      "title": "Morning focus: Tonal One and Kumo",
      "summary": "A two-shot morning-ritual spot pairing the…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-08T19:45:45+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 399,
      "title": "Fuego Dulce: one drop too many",
      "summary": "A ten-second comedic hot sauce spot",
      "status": "render started",
      "is_scene": false,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:44+00:00",
      "prompt": "",
      "still": null,
      "clip": null
    },
    {
      "id": 398,
      "title": "Solene: fig and salt at golden hour",
      "summary": "A six-second perfume spot built on light, stone…",
      "status": "idea",
      "is_scene": false,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:43+00:00",
      "prompt": "",
      "still": null,
      "clip": null
    }
  ],
  "scenes_truncated": false,
  "references": [
    {
      "ref": "/props/tonal-one-headphones/photo/headphones.jpg",
      "kind": "prop",
      "label": "headphones.jpg",
      "url": "https://media.phantra.ai/m/5/props/tonal-one-headphones/headphones.jpg",
      "page": null,
      "scenes": [
        400,
        408
      ]
    },
    {
      "ref": "/props/kumo-matcha/photo/matcha.jpg",
      "kind": "prop",
      "label": "matcha.jpg",
      "url": "https://media.phantra.ai/m/5/props/kumo-matcha/matcha.jpg",
      "page": null,
      "scenes": [
        400
      ]
    },
    {
      "ref": "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg",
      "kind": "prop",
      "label": "hot-sauce.jpg",
      "url": "https://media.phantra.ai/m/5/props/fuego-dulce-hot-sauce/hot-sauce.jpg",
      "page": null,
      "scenes": [
        408
      ]
    }
  ],
  "references_truncated": false,
  "renders": [],
  "chat": [],
  "chat_has_more": false,
  "next": "a reference's `ref` or a render's `gen:<id>` goes wherever a tool takes a reference, and project_id=1 files new work under this project where a tool takes it; `save_chat` keeps this conversation with it; `project_chat` pages back through its history"
}
```

### 6. elements

args: `{}`

```json
{
  "count": 5,
  "elements": [
    {
      "kind": "prop",
      "name": "Fuego Dulce hot sauce",
      "description": "Invented hot sauce FUEGO DULCE, mango habanero: a tall bottle with a red cap and a flame label, flat lay with mango, habaneros, lime, garlic and coriander on teal.",
      "sheet": null,
      "use": [
        "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg"
      ],
      "photos": [
        {
          "ref": "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg",
          "label": "hot-sauce.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Kumo matcha",
      "description": "Invented tea brand KUMO, ceremonial matcha: a white tin with a sage label, the lid, bamboo scoop and whisk caught mid-air in a burst of green powder on lilac.",
      "sheet": null,
      "use": [
        "/props/kumo-matcha/photo/matcha.jpg"
      ],
      "photos": [
        {
          "ref": "/props/kumo-matcha/photo/matcha.jpg",
          "label": "matcha.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Phantra Icon",
      "description": "",
      "sheet": null,
      "use": [
        "/props/phantra-icon/photo/phantra-owl-180.png"
      ],
      "photos": [
        {
          "ref": "/props/phantra-icon/photo/phantra-owl-180.png",
          "label": "phantra-owl-180.png"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Solene perfume",
      "description": "Invented fragrance brand SOLÈNE, 'Fig & Salt' eau de parfum: a clear square glass bottle with a brass cap and a cream label, styled on travertine plinths beside a split fig, cobalt background.",
      "sheet": null,
      "use": [
        "/props/solene-perfume/photo/fragrance.jpg"
      ],
      "photos": [
        {
          "ref": "/props/solene-perfume/photo/fragrance.jpg",
          "label": "fragrance.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Tonal One headphones",
      "description": "Invented audio brand TONAL ONE: over-ear headphones in graphite and brushed metal, shown as an exploded view (drivers, board, battery, cushions) on a yellow background.",
      "sheet": null,
      "use": [
        "/props/tonal-one-headphones/photo/headphones.jpg"
      ],
      "photos": [
        {
          "ref": "/props/tonal-one-headphones/photo/headphones.jpg",
          "label": "headphones.jpg"
        }
      ]
    }
  ],
  "note": ""
}
```

### 7. library

args: `{}`

```json
{
  "count": 12,
  "items": [
    {
      "id": "asset:7",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 15260,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/media/26f904d4471bcd3bbbbaa2a0.jpg",
      "created_at": "2026-10-15T22:42:46+00:00",
      "filename": "26f904d4471bcd3bbbbaa2a0.jpg"
    },
    {
      "id": "asset:6",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 15260,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/media/26f904d4471bcd3bbbbaa2a0.jpg",
      "created_at": "2026-10-15T22:41:27+00:00",
      "filename": "26f904d4471bcd3bbbbaa2a0.jpg"
    },
    {
      "id": "asset:5",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 15260,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/media/26f904d4471bcd3bbbbaa2a0.jpg",
      "created_at": "2026-10-15T22:40:41+00:00",
      "filename": "26f904d4471bcd3bbbbaa2a0.jpg"
    },
    {
      "id": "asset:4",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 15260,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/media/26f904d4471bcd3bbbbaa2a0.jpg",
      "created_at": "2026-10-15T22:39:27+00:00",
      "filename": "26f904d4471bcd3bbbbaa2a0.jpg"
    },
    {
      "id": "gen:107",
      "kind": "video",
      "origin": "render",
      "seconds": 6.12,
      "size_bytes": 2875965,
      "frame": "1080x1920",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/fal/c411-s1-20261012-142649-bca45dcbb355cadbd85d05e7f089acb3.mp4",
      "created_at": "2026-10-12T14:27:51+00:00",
      "model": "ltx2.3",
      "prompt": "RENDER THE CHANGE, not the frame: open already mid-motion, end still moving, and"
    },
    {
      "id": "gen:106",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": {
        "id": 1,
        "title": "Spring product spots"
      },
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142637-dd0ad68da0a055c733abb62f00d44c20.png",
      "created_at": "2026-10-12T14:26:46+00:00",
      "model": "gemini-2.5-flash-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: No backgrou"
    },
    {
      "id": "gen:105",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": {
        "id": 1,
        "title": "Spring product spots"
      },
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png",
      "created_at": "2026-10-12T14:26:36+00:00",
      "model": "gemini-2.5-flash-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: No backgrou"
    },
    {
      "id": "gen:104",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/fal/flux-pro1.1-20261012-142508-79b7bb1c5991e8de0899c82dc28823aa.jpg",
      "created_at": "2026-10-12T14:25:19+00:00",
      "model": "flux-pro1.1",
      "prompt": "A single pair of over-ear headphones on a slate desk in soft window light, produ"
    },
    {
      "id": "asset:3",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 23523,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/media/2e04a72858b31d19f502075c.jpg",
      "created_at": "2026-10-12T14:21:58+00:00",
      "filename": "2e04a72858b31d19f502075c.jpg"
    },
    {
      "id": "gen:95",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145537-e83240c39c8a8c7ca2f497e147af88c1.png",
      "created_at": "2026-09-30T14:56:14+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    },
    {
      "id": "gen:94",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145453-beb0ad011ff5faa37f019703e770627f.png",
      "created_at": "2026-09-30T14:55:31+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    },
    {
      "id": "gen:93",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145406-d3d2a53719d60f5d220590bf65a5f0bb.png",
      "created_at": "2026-09-30T14:54:45+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    }
  ],
  "note": ""
}
```

### 8. recent

args: `{}`

```json
{
  "projects": [
    {
      "id": 1,
      "title": "Spring product spots",
      "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no f",
      "has_look": false,
      "scenes": 5,
      "rendered": 0,
      "archived": false,
      "updated_at": "2026-10-16T18:40:07.618820+00:00",
      "cover": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png"
    }
  ],
  "scenes": [
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
      "studio_url": "https://phantra.ai/studio/scene/408"
    },
    {
      "id": 401,
      "title": "Kumo: the whisk",
      "summary": "A slow-motion product moment for the matcha tin",
      "status": "idea",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:47+00:00",
      "scene_id": 401,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/401"
    },
    {
      "id": 400,
      "title": "Morning focus: Tonal One and Kumo",
      "summary": "A two-shot morning-ritual spot pairing the…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-08T19:45:45+00:00",
      "scene_id": 400,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/400"
    },
    {
      "id": 399,
      "title": "Fuego Dulce: one drop too many",
      "summary": "A ten-second comedic hot sauce spot",
      "status": "render started",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:44+00:00",
      "scene_id": 399,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/399"
    }
  ],
  "renders": [
    {
      "id": "gen:107",
      "kind": "video",
      "origin": "render",
      "seconds": 6.12,
      "size_bytes": 2875965,
      "frame": "1080x1920",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/fal/c411-s1-20261012-142649-bca45dcbb355cadbd85d05e7f089acb3.mp4",
      "created_at": "2026-10-12T14:27:51+00:00",
      "model": "ltx2.3",
      "prompt": "RENDER THE CHANGE, not the frame: open already mid-motion, end still moving, and"
    },
    {
      "id": "gen:106",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": {
        "id": 1,
        "title": "Spring product spots"
      },
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142637-dd0ad68da0a055c733abb62f00d44c20.png",
      "created_at": "2026-10-12T14:26:46+00:00",
      "model": "gemini-2.5-flash-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: No backgrou"
    },
    {
      "id": "gen:105",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": {
        "id": 1,
        "title": "Spring product spots"
      },
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png",
      "created_at": "2026-10-12T14:26:36+00:00",
      "model": "gemini-2.5-flash-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: No backgrou"
    },
    {
      "id": "gen:104",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/fal/flux-pro1.1-20261012-142508-79b7bb1c5991e8de0899c82dc28823aa.jpg",
      "created_at": "2026-10-12T14:25:19+00:00",
      "model": "flux-pro1.1",
      "prompt": "A single pair of over-ear headphones on a slate desk in soft window light, produ"
    },
    {
      "id": "gen:95",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145537-e83240c39c8a8c7ca2f497e147af88c1.png",
      "created_at": "2026-09-30T14:56:14+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    },
    {
      "id": "gen:94",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145453-beb0ad011ff5faa37f019703e770627f.png",
      "created_at": "2026-09-30T14:55:31+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    },
    {
      "id": "gen:93",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145406-d3d2a53719d60f5d220590bf65a5f0bb.png",
      "created_at": "2026-09-30T14:54:45+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    }
  ]
}
```

### 9. search

args: `{"query": "headphones"}`

```json
{
  "q": "",
  "recent": true,
  "projects": [
    {
      "id": 1,
      "title": "Spring product spots",
      "sub": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fueg…",
      "archived": false
    }
  ],
  "scenes": [
    {
      "scene_id": 408,
      "title": "Reviewer check: Tonal One push-in",
      "sub": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/408"
    },
    {
      "scene_id": 401,
      "title": "Kumo: the whisk",
      "sub": "A slow-motion product moment for the matcha tin.",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/401"
    },
    {
      "scene_id": 400,
      "title": "Morning focus: Tonal One and Kumo",
      "sub": "A two-shot morning-ritual spot pairing the headphones with the matcha.",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/400"
    },
    {
      "scene_id": 399,
      "title": "Fuego Dulce: one drop too many",
      "sub": "A ten-second comedic hot sauce spot.",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/399"
    }
  ],
  "elements": [],
  "renders": [],
  "cuts": [],
  "count": 5
}
```

### 10. video_models

args: `{}`

```json
{
  "default": "ltx2.3",
  "available": true,
  "models": [
    {
      "id": "kling3-turbo-pro",
      "platform": "kling",
      "seconds": {
        "kind": "range",
        "min": 3,
        "max": 15,
        "default": 5,
        "note": ""
      },
      "frame": {
        "kind": "fixed",
        "values": [
          "1080p"
        ],
        "default": "1080p",
        "note": "kling3-turbo-pro takes no resolution field -- it renders at 1080p"
      },
      "priced_seconds": 5,
      "credits_by_frame": {
        "1080p": 168
      },
      "draft": null,
      "verified": "2026-09-26"
    },
    {
      "id": "ltx2.3",
      "platform": "ltx",
      "seconds": {
        "kind": "choices",
        "values": [
          6,
          8,
          10
        ],
        "default": 6,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "1080p",
          "1440p",
          "2160p"
        ],
        "default": "1080p",
        "note": ""
      },
      "priced_seconds": 6,
      "credits_by_frame": {
        "1080p": 87,
        "1440p": 173,
        "2160p": 346
      },
      "draft": null,
      "verified": "2026-09-26"
    },
    {
      "id": "ltx2.5",
      "platform": "ltx",
      "seconds": {
        "kind": "choices",
        "values": [
          6,
          8,
          10
        ],
        "default": 6,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "720p",
          "1080p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 6,
      "credits_by_frame": {
        "720p": 173,
        "1080p": 245
      },
      "draft": null,
      "verified": "2026-10-08"
    },
    {
      "id": "ltx2.5-fast",
      "platform": "ltx",
      "seconds": {
        "kind": "choices",
        "values": [
          6,
          8,
          10,
          12,
          14,
          16,
          18,
          20
        ],
        "default": 6,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "720p",
          "1080p",
          "1440p",
          "2160p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 6,
      "credits_by_frame": {
        "720p": 130,
        "1080p": 188,
        "1440p": 274,
        "2160p": 432
      },
      "draft": null,
      "verified": "2026-10-08"
    },
    {
      "id": "seedance2",
      "platform": "seedance",
      "seconds": {
        "kind": "range",
        "min": 4,
        "max": 15,
        "default": 5,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "480p",
          "720p",
          "1080p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 5,
      "credits_by_frame": {
        "480p": 365,
        "720p": 365,
        "1080p": 819
      },
      "draft": null,
      "verified": "2026-09-26"
    },
    {
      "id": "seedance2-fast",
      "platform": "seedance",
      "seconds": {
        "kind": "range",
        "min": 4,
        "max": 15,
        "default": 5,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "480p",
          "720p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 5,
      "credits_by_frame": {
        "480p": 291,
        "720p": 291
      },
      "draft": null,
      "verified": "2026-09-26"
    },
    {
      "id": "seedance2.5",
      "platform": "seedance",
      "seconds": {
        "kind": "range",
        "min": 4,
        "max": 30,
        "default": 5,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "480p",
          "720p",
          "1080p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 5,
      "credits_by_frame": {
        "480p": 265,
        "720p": 568,
        "1080p": 1397
      },
      "draft": "480p",
      "verified": "2026-10-06"
    },
    {
      "id": "veo3.1",
      "platform": "veo",
      "seconds": {
        "kind": "choices",
        "values": [
          4,
          6,
          8
        ],
        "default": 6,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "720p",
          "1080p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 6,
      "credits_by_frame": {
        "720p": 576,
        "1080p": 576
      },
      "draft": null,
      "verified": "2026-09-26"
    },
    {
      "id": "wan3",
      "platform": "wan",
      "seconds": {
        "kind": "range",
        "min": 2,
        "max": 10,
        "default": 5,
        "note": ""
      },
      "frame": {
        "kind": "choices",
        "values": [
          "480p",
          "720p",
          "1080p"
        ],
        "default": "720p",
        "note": ""
      },
      "priced_seconds": 5,
      "credits_by_frame": {
        "480p": 60,
        "720p": 120,
        "1080p": 240
      },
      "draft": "480p",
      "verified": "2026-09-26"
    }
  ],
  "note": "credits for a short clip at each frame; `quote` prices a scene's exact length"
}
```

### 11. image_models

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

### 12. recommend_model

args: `{"what": "a cheap test of a short product clip"}`

```json
{
  "picks": [
    {
      "model": "ltx2.3",
      "name": "LTX 2.3",
      "tier": "standard",
      "credits": 87,
      "seconds": 6,
      "frame": "1080p",
      "draft": null,
      "kept": {
        "made": 1,
        "kept": 1
      },
      "reason": "87 credits for 6s is among the cheapest"
    },
    {
      "model": "wan3",
      "name": "Wan 3.0",
      "tier": "standard",
      "credits": 120,
      "seconds": 5,
      "frame": "720p",
      "draft": "480p",
      "kept": null,
      "reason": "120 credits for 5s is among the cheapest"
    },
    {
      "model": "ltx2.5-fast",
      "name": "LTX 2.5 Fast",
      "tier": "standard",
      "credits": 130,
      "seconds": 6,
      "frame": "720p",
      "draft": null,
      "kept": null,
      "reason": "130 credits for 6s is among the cheapest"
    }
  ],
  "considered": 9,
  "asked": [
    "cheap"
  ],
  "skipped": [],
  "seconds": 5,
  "note": "ranked from the studio's catalogue and what you kept; nothing was called and nothing spent. Credits are for the length shown at each model's default frame; `quote` prices a scene exactly"
}
```

### 13. preferences

args: `{}`

```json
{
  "aspect": null,
  "seconds": 8,
  "video_model": "ltx2.3",
  "image_model": null,
  "draft_first": false,
  "set_at": "2026-10-15 22:43:14.803632+00:00",
  "choices": {
    "aspect": [
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
    "seconds": [
      4,
      30
    ],
    "video_model": [
      "kling3-turbo-pro",
      "ltx2.3",
      "ltx2.5",
      "ltx2.5-fast",
      "seedance2",
      "seedance2-fast",
      "seedance2.5",
      "veo3.1",
      "wan3"
    ],
    "image_model": [
      "nano",
      "flux-pro1.1",
      "flux2-pro",
      "nano-banana-pro",
      "seedream4.5",
      "gpt-image-2",
      "gpt-image-2.5-flare",
      "gpt-image-2.5-sunburst",
      "ideogram4.5"
    ],
    "draft_first": [
      true,
      false
    ]
  },
  "note": "used only where a call passes nothing: `write_scene`'s length, `quote`'s model and draft frame, a still's model and frame"
}
```

### 14. recipes

args: `{}`

```json
{
  "recipes": [
    {
      "name": "character-sheet",
      "title": "Character sheet",
      "for": "save a person as a character and draw their reference sheet from real photos of them",
      "output": "image",
      "own": false
    },
    {
      "name": "single-shot",
      "title": "Single shot",
      "for": "write one continuous shot -- a single unbroken take, one clip -- when the person asks for one",
      "output": "video",
      "own": false
    },
    {
      "name": "multi-shot",
      "title": "Multi-shot scene",
      "for": "write a scene cut into timed shots, each one rendered as its own clip",
      "output": "video",
      "own": false
    },
    {
      "name": "product-still",
      "title": "Product still",
      "for": "draw a still of a real product from its own photos -- a packshot, a hero frame, or in use",
      "output": "image",
      "own": false
    },
    {
      "name": "mood-board",
      "title": "Mood board",
      "for": "gather real reference photos for a look, and write the look down in words a scene can use",
      "output": "image",
      "own": false
    },
    {
      "name": "reviewer-check",
      "title": "A product still before a scene: one photo of the product, one of the light, the ",
      "versions": 10,
      "project_id": null,
      "updated_at": "2026-10-15 22:43:11.645967+00:00",
      "own": true
    }
  ],
  "count": 6,
  "note": "`recipe` reads one by name; the studio's own are guidance, yours come back as the text you saved. `save_recipe` keeps a new one."
}
```

### 15. what_works

args: `{}`

```json
{
  "enough_data": true,
  "outputs": {
    "made": 20,
    "kept": 12,
    "keep_rate": 0.6,
    "by_model": [
      {
        "model": "trim",
        "made": 5,
        "kept": 4,
        "keep_rate": 0.8
      },
      {
        "model": "reformat",
        "made": 4,
        "kept": 4,
        "keep_rate": 1.0
      },
      {
        "model": "join",
        "made": 3,
        "kept": 3,
        "keep_rate": 1.0
      },
      {
        "model": "gemini-3-pro-image",
        "made": 3,
        "kept": 0,
        "keep_rate": 0.0
      },
      {
        "model": "flux-pro1.1",
        "made": 2,
        "kept": 0,
        "keep_rate": 0.0
      },
      {
        "model": "gemini-2.5-flash-image",
        "made": 2,
        "kept": 0,
        "keep_rate": 0.0
      },
      {
        "model": "ltx2.3",
        "made": 1,
        "kept": 1,
        "keep_rate": 1.0
      }
    ],
    "attempts": {
      "things": 11,
      "average": 1.09,
      "median": 1,
      "first_try": 10,
      "no_keeper_yet": 7
    },
    "credits_by_week": [
      {
        "week": "2026-10-12",
        "credits": 107,
        "made": 17,
        "kept": 12,
        "per_kept": 9
      },
      {
        "week": "2026-09-28",
        "credits": 0,
        "made": 3,
        "kept": 0,
        "per_kept": null
      }
    ],
    "discards": [
      {
        "week": "2026-10-12",
        "made": 17,
        "deleted": 0,
        "regenerated": 1
      },
      {
        "week": "2026-09-28",
        "made": 3,
        "deleted": 0,
        "regenerated": 0
      }
    ]
  },
  "presets": [],
  "posted": [],
  "lines": [
    "you kept 12 of 20 outputs (60%)",
    "on trim: kept 4 of 5",
    "on reformat: kept 4 of 4",
    "on join: kept 3 of 3",
    "a keeper takes 1.09 tries on average",
    "nothing posted with a scene behind it yet, so there is no audience signal"
  ],
  "note": "read off what you kept, downloaded, cut, starred or posted; nothing here calls a model, and credits are credits"
}
```

### 16. scene

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
  "keyframe": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png",
  "clips": [],
  "rendered": false,
  "studio_url": "https://phantra.ai/studio/scene/408"
}
```

### 17. quote

args: `{"scene_id": 408}`

```json
{
  "scene_id": 408,
  "status": "written",
  "keyframes": null,
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
        "token": "phq.…(redacted)"
      },
      {
        "part": 2,
        "seconds": 6,
        "credits": 87,
        "token": "phq.…(redacted)"
      }
    ]
  },
  "balance": 374,
  "credits_needed": 174,
  "affordable": true,
  "preference": {
    "provider": "fal",
    "model": "ltx2.3",
    "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"
  },
  "title": "Reviewer check: Tonal One push-in",
  "preview_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630-82d96eaad66ea0e40a9f6976bacc7322.png",
  "note": "show the person this price and wait for a yes; tokens are valid for one hour -- pass them to `approve` with the same renderer choice. A card with the price and balance is already on screen: reply in one short sentence, ask whether to go ahead, and do not list the numbers again."
}
```

### 18. generate_image

args: `{"prompt": "A pair of headphones on a slate desk in soft window light.", "model": "", "aspect": ""}`

```json
{
  "ok": false,
  "needs_approval": true,
  "can_approve": true,
  "note": "Nothing was spent. This FLUX 1.1 Pro image costs 10 credits; the balance is 374 and would be 364 after it. Show the person what it is and the price in credits, and WAIT for a yes. Only then call again with the SAME arguments plus quote_token from this quote -- it is good for one hour, for exactly this request, and once. A card with the price and balance is already on screen: reply in one short sentence, ask whether to go ahead, and do not list the numbers again.",
  "quote": {
    "model": "flux-pro1.1",
    "label": "FLUX 1.1 Pro",
    "aspect": null,
    "references": [],
    "credits": 10,
    "charged": true,
    "balance": 374,
    "balance_after": 364,
    "quote_token": "phq.…(redacted)",
    "expires_at": "2026-10-16T22:51:13+00:00"
  }
}
```

### 19. scene

args: `{"scene_id": 375}`

```json
{
  "refused": "Error executing tool scene: no scene 375"
}
```
