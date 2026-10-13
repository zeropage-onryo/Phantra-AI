> Phantra was named Zero Page until 2026-10-13. This is a dated record and keeps the names of its day.

# Reviewer walk: /mcp/claude as zp-billing-test (2026-10-12)

Run by `ops/connector_walk.py walk claude`. Every answer below is the connector's own, with tokens and URL query strings redacted. PASS means the expectation held; CHECK means read it. A refusal is the connector's own sentence, never retried.

**70 of 72 expectations PASS.**

## Verdicts

| # | tool | expectation | verdict | detail |
|---|---|---|---|---|
| 1 | whoami | whoami names zp-billing-test | PASS | slug 'zp-billing-test', id 5 |
| 1 | whoami | the signed-in member and role are named | PASS | name 'Michael Massaad', role 'member' |
| 2 | preferences (as found) | the preferences as found, before anything is set | PASS | {"aspect": null, "seconds": null, "video_model": null, "image_model": null, "draft_first": null} |
| 3 | projects | projects lists 'Spring product spots' | PASS | Spring product spots |
| 4 | project | project opens with its title | PASS | title 'Spring product spots' |
| 5 | elements | elements lists at least two elements with photos | PASS | 4 element(s) |
| 5 | elements | an element named like 'Tonal' has a photo ref | PASS | Tonal One headphones |
| 6 | upload_link | upload_link returns an https /u/ address | PASS | https://api.zeropage.studio/u/… |
| 6 | upload_link | upload_link costs 0 credits | PASS | credits 0 |
| 7 | upload the icon to the one-time page, then open it again | the page says Saved | PASS | status 200 |
| 7 | upload the icon to the one-time page, then open it again | the page names an asset:<id> | PASS | asset:3 |
| 7 | upload the icon to the one-time page, then open it again | the page says Added to Reviewer check (prop) | PASS | Saved · Zero Page Studio ZP Saved Add a photo to the prop “Reviewer check” in your studio. Your file is in your studio. Filed as asset:3 Kind image Size 512 × 512 Added to Reviewer check (prop) Go bac |
| 7 | upload the icon to the one-time page, then open it again | the page shows a Size line | PASS |  |
| 7 | upload the icon to the one-time page, then open it again | the page shows no Length line for a picture (#284) | PASS |  |
| 7 | upload the icon to the one-time page, then open it again | opening the link again says already used | PASS | status 410: Upload link · Zero Page Studio ZP This link can't take a file this upload link was already used -- it saved asset:3. Ask the chat for a new one to upload anothe |
| 8 | elements (after the upload) | elements now lists the prop Reviewer check with a photo | PASS | 5 element(s); before: 4 |
| 9 | write_scene | write_scene answers a scene_id | PASS | 408 |
| 9 | write_scene | the answer carries the light role on the second photo | PASS | {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"} |
| 9 | write_scene | the scene is not a draft (it carries photos) | PASS |  |
| 10 | scene | scene shows two shots | PASS | 2 |
| 10 | scene | scene counts two reference photos | PASS | 2 |
| 10 | scene | scene answers the roles | PASS | {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"} |
| 10 | scene | scene is not rendered yet | PASS |  |
| 11 | quote | quote carries approve_url (the studio's Render card) | PASS | https://zeropage.studio/studio/scene/408 |
| 11 | quote | no signed tokens on the Claude listing's quote | PASS |  |
| 11 | quote | quote prices the keyframes | PASS |  |
| 11 | quote | quote shows the balance in credits | PASS | 501 |
| 11 | quote | no dollar key in the quote | PASS |  |
| 11 | quote | no preference applied before set_preferences | PASS | null |
| 12 | library | library lists items | PASS | 4 |
| 12 | library | the library holds a rendered clip | CHECK | None |
| 12 | library | the upload is in the library | PASS | asset:3 |
| 13 | reformat, trim_clip, assemble_clips, share_link: skipped | (recorded) | - | |
| 14 | balance | balance answers available credits | PASS | 501 |
| 14 | balance | no dollar key in balance | PASS |  |
| 15 | credit_history | credit_history has lines | PASS | 8 |
| 15 | credit_history | every line carries balance_after | PASS |  |
| 15 | credit_history | no dollar key in credit_history | PASS |  |
| 16 | recent | recent lists projects, scenes or renders | PASS | projects, scenes, renders |
| 17 | search | search finds the Tonal One prop | PASS |  |
| 17 | search | search finds the written scene | PASS | 408 |
| 18 | video_models | video_models lists the catalogue | PASS | 9 |
| 18 | video_models | wan3 carries a 480p draft frame | PASS | "480p" |
| 18 | video_models | no dollar key in video_models | PASS |  |
| 19 | recommend_model | a cheap test ranks LTX 2.3 first | PASS | ltx2.3 |
| 19 | recommend_model | no dollar key in recommend_model | PASS |  |
| 20 | recommend_model (25 s, sound) | 25 seconds leaves Seedance 2.5 only | PASS | seedance2.5 |
| 21 | preferences | preferences read the same as at the start (unset, or as a previous walk left them) | PASS | {"aspect": null, "seconds": null, "video_model": null, "image_model": null, "draft_first": null} |
| 21 | preferences | the choices are listed | PASS |  |
| 22 | set_preferences | set_preferences took seconds=12, wan3, draft_first | PASS |  |
| 23 | set_preferences video_model=sora | video_model=sora is refused with the list | PASS | Error executing tool set_preferences: video_model is one of ['kling3-turbo-pro', 'ltx2.3', 'ltx2.5', 'ltx2.5-fast', 'seedance2', 'seedance2-fast', 'seedance2.5', 'veo3.1', 'wan3'], got 'sora' |
| 24 | quote (after set_preferences) | quote applies the wan3 preference | PASS | {"provider": "fal", "model": "wan3", "frame": "480p", "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"} |
| 24 | quote (after set_preferences) | the draft frame 480p is applied | PASS |  |
| 25 | quote model=ltx2.3 | a named model carries no preference | PASS |  |
| 26 | duplicate_scene | duplicate_scene makes a new scene | PASS | 409 |
| 26 | duplicate_scene | it names copied_from | PASS | 400 |
| 26 | duplicate_scene | the copy carries no clip | PASS |  |
| 27 | duplicate_scene refs=[] | a copy with refs=[] is a draft (needs_reference) | PASS |  |
| 28 | feedback | feedback is saved | PASS |  |
| 29 | recipes | recipes lists the studio's shelf (single-shot among them) | PASS | 5 recipe(s); reviewer-check at version 0 |
| 30 | save_recipe | save_recipe answers version 1 | PASS | 1 |
| 31 | save_recipe (again) | save_recipe answers version 2 | PASS | 2 |
| 32 | recipe | recipe returns version 2 with the note that it is the person's own text | PASS | version 2 |
| 33 | recipe single-shot | recipe single-shot is the shelf's | PASS |  |
| 34 | what_works | what_works says enough_data false | PASS | False |
| 34 | what_works | what_works says nothing posted | PASS |  |
| 34 | what_works | no dollar key in what_works | PASS |  |
| 35 | score_caption | score_caption is neutral at 0.5 | PASS | 0.5 |
| 35 | score_caption | score_caption says enough_data false | PASS |  |
| 36 | project project_id=1 (another workspace's) | project 1 is refused as no project 1 | CHECK | {"id": 1, "title": "Spring product spots", "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce  |
| 37 | scene scene_id=375 (another workspace's) | scene 375 is refused as no scene 375 | PASS | Error executing tool scene: no scene 375 |
| 38 | balance (at the end) | the balance is what it was at the start | PASS | 501 -> 501 |
| 39 | set_preferences (back) | preferences set back to what the walk found (or the defaults): seconds=8, video_model=ltx2.3, draft_first=False | PASS |  |
| - | every answer | no dollar sign and no dollar-named key anywhere | PASS |  |

## Answers

### 1. whoami

args: `{}`

```json
{
  "workspace": {
    "id": 5,
    "name": "Billing test (Claude, 2026-09-30)",
    "slug": "zp-billing-test",
    "created_at": "2026-09-30T14:38:08"
  },
  "plan": null,
  "member": {
    "name": "Michael Massaad",
    "role": "member"
  },
  "signed_in_person": true,
  "studio_url": "https://zeropage.studio",
  "note": ""
}
```

### 2. preferences (as found)

args: `{}`

```json
{
  "aspect": null,
  "seconds": null,
  "video_model": null,
  "image_model": null,
  "draft_first": null,
  "set_at": null,
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

### 3. projects

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
      "scenes": 4,
      "rendered": 0,
      "archived": false,
      "updated_at": "2026-10-08T19:48:07.003522+00:00",
      "cover": null
    }
  ],
  "truncated": false
}
```

### 4. project

args: `{"project_id": 1}`

```json
{
  "id": 1,
  "title": "Spring product spots",
  "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no faces.",
  "look": "",
  "archived": false,
  "created_at": "2026-10-08T19:48:06.392097+00:00",
  "updated_at": "2026-10-08T19:48:07.003522+00:00",
  "learned": [],
  "scenes": [
    {
      "id": 401,
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/tonal-one-headphones/headphones.jpg",
      "page": null,
      "scenes": [
        400
      ]
    },
    {
      "ref": "/props/kumo-matcha/photo/matcha.jpg",
      "kind": "prop",
      "label": "matcha.jpg",
      "url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/kumo-matcha/matcha.jpg",
      "page": null,
      "scenes": [
        400
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

### 5. elements

args: `{}`

```json
{
  "count": 4,
  "elements": [
    {
      "kind": "prop",
      "name": "Fuego Dulce hot sauce",
      "description": "Invented hot sauce FUEGO DULCE, mango habanero: a tall bottle with a red cap and a flame label, flat lay with mango, habaneros, lime, garlic and coriander on teal.",
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
      "photos": [
        {
          "ref": "/props/kumo-matcha/photo/matcha.jpg",
          "label": "matcha.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Solene perfume",
      "description": "Invented fragrance brand SOLÈNE, 'Fig & Salt' eau de parfum: a clear square glass bottle with a brass cap and a cream label, styled on travertine plinths beside a split fig, cobalt background.",
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

### 6. upload_link

args: `{"purpose": "reference", "element_kind": "prop", "element_name": "Reviewer check"}`

```json
{
  "url": "https://api.zeropage.studio/u/…",
  "expires_in_s": 1800,
  "purpose": "reference",
  "element": {
    "kind": "prop",
    "name": "Reviewer check"
  },
  "takes": "jpg, png, webp or heic pictures; mp4 or mov clips",
  "credits": 0,
  "note": "Give the person this link to upload a photo for the prop “Reviewer check”. It is good for 30 minutes and for one file; the page says what was saved. Nothing is drawn and no credits are spent.",
  "next": "`elements` lists the photo once it is up; pass its `ref` in a scene's `refs`"
}
```

### 7. upload the icon to the one-time page, then open it again

args: `{"file": "zeropage-studio-icon-512.png"}`

```json
{
  "posted": {
    "status": 200,
    "text": "Saved · Zero Page Studio ZP Saved Add a photo to the prop “Reviewer check” in your studio. Your file is in your studio. Filed as asset:3 Kind image Size 512 × 512 Added to Reviewer check (prop) Go back to the chat and say the file is up. This link is used up; ask for a new one to send another file."
  },
  "again": {
    "status": 410,
    "text": "Upload link · Zero Page Studio ZP This link can't take a file this upload link was already used -- it saved asset:3. Ask the chat for a new one to upload another file. Go back to the chat and ask for a new upload link if you still want to send a file."
  }
}
```

### 8. elements (after the upload)

args: `{}`

```json
{
  "count": 5,
  "elements": [
    {
      "kind": "prop",
      "name": "Fuego Dulce hot sauce",
      "description": "Invented hot sauce FUEGO DULCE, mango habanero: a tall bottle with a red cap and a flame label, flat lay with mango, habaneros, lime, garlic and coriander on teal.",
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
      "photos": [
        {
          "ref": "/props/kumo-matcha/photo/matcha.jpg",
          "label": "matcha.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Reviewer check",
      "description": "",
      "photos": [
        {
          "ref": "/props/reviewer-check/photo/up-ef7a3c3e884c5085.jpg",
          "label": "up-ef7a3c3e884c5085.jpg"
        }
      ]
    },
    {
      "kind": "prop",
      "name": "Solene perfume",
      "description": "Invented fragrance brand SOLÈNE, 'Fig & Salt' eau de parfum: a clear square glass bottle with a brass cap and a cream label, styled on travertine plinths beside a split fig, cobalt background.",
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

### 9. write_scene

args: `{"prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only diegetic sound: the faint rustle of a sleeve, a chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a second pair of hands, any face.", "title": "Reviewer check: Tonal One push-in", "refs": ["/props/tonal-one-headphones/photo/headphones.jpg", "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg"], "roles": {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"}, "project_id": 1}`

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
  "keyframe": null,
  "clips": [],
  "rendered": false,
  "studio_url": "https://zeropage.studio/studio/scene/408",
  "next": "`quote` scene_id=408 for the price; the person approves the render in the studio at `studio_url`"
}
```

### 10. scene

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
  "keyframe": null,
  "clips": [],
  "rendered": false,
  "studio_url": "https://zeropage.studio/studio/scene/408"
}
```

### 11. quote

args: `{"scene_id": 408}`

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
    "credits": 174,
    "content_hash": "0834008347a11ce3",
    "renders": [
      {
        "part": 1,
        "seconds": 6,
        "credits": 87
      },
      {
        "part": 2,
        "seconds": 6,
        "credits": 87
      }
    ]
  },
  "balance": 501,
  "credits_needed": 194,
  "affordable": true,
  "approve_url": "https://zeropage.studio/studio/scene/408",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 12. library

args: `{}`

```json
{
  "count": 4,
  "items": [
    {
      "id": "asset:3",
      "kind": "image",
      "origin": "upload",
      "seconds": 600.0,
      "size_bytes": 23523,
      "frame": "512x512",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/cut/media/2e04a72858b31d19f502075c.jpg",
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
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145537.png",
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
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145453.png",
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
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145406.png",
      "created_at": "2026-09-30T14:54:45+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    }
  ],
  "note": ""
}
```

### 13. reformat, trim_clip, assemble_clips, share_link: skipped

args: `{}`

error: no rendered clip in the library to edit

### 14. balance

args: `{}`

```json
{
  "available": 501,
  "held": 0,
  "plan": null,
  "lots": [
    {
      "kind": "promo",
      "credits": 100,
      "remaining": 1,
      "granted_at": "2026-09-30T14:38:14.611391+00:00",
      "expires_at": "2026-11-30T14:38:14.611391+00:00"
    },
    {
      "kind": "adjustment",
      "credits": 500,
      "remaining": 500,
      "granted_at": "2026-10-08T19:30:29.460639+00:00",
      "expires_at": "2026-12-08T19:30:29.460639+00:00"
    }
  ],
  "scheduled": [],
  "charged": true,
  "note": "credits, never money; plans and top-ups are in the studio at https://zeropage.studio/pricing"
}
```

### 15. credit_history

args: `{}`

```json
{
  "items": [
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
      "label": "Trial credits",
      "link": null,
      "balance_after": 100
    }
  ],
  "next": null,
  "count": 8,
  "note": "credits only, newest first; pass `next` as `before` for the page after"
}
```

### 16. recent

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
      "updated_at": "2026-10-12T14:22:06.703957+00:00",
      "cover": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/tonal-one-headphones/headphones.jpg"
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
      "studio_url": "https://zeropage.studio/studio/scene/408"
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
      "studio_url": "https://zeropage.studio/studio/scene/401"
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
      "studio_url": "https://zeropage.studio/studio/scene/400"
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
      "studio_url": "https://zeropage.studio/studio/scene/399"
    },
    {
      "id": 398,
      "title": "Solene: fig and salt at golden hour",
      "summary": "A six-second perfume spot built on light, stone…",
      "status": "idea",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-08T19:45:43+00:00",
      "scene_id": 398,
      "project_id": 1,
      "studio_url": "https://zeropage.studio/studio/scene/398"
    }
  ],
  "renders": [
    {
      "id": "gen:95",
      "kind": "image",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145537.png",
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
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145453.png",
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
      "media_url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/renders/nano/c386-20260930-145406.png",
      "created_at": "2026-09-30T14:54:45+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    }
  ]
}
```

### 17. search

args: `{"q": "headphones"}`

```json
{
  "q": "headphones",
  "recent": false,
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
      "sub": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow pu…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://zeropage.studio/studio/scene/408"
    },
    {
      "scene_id": 400,
      "title": "Morning focus: Tonal One and Kumo",
      "sub": "…attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match th…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://zeropage.studio/studio/scene/400"
    }
  ],
  "elements": [
    {
      "kind": "product",
      "name": "Tonal One headphones",
      "sub": "Invented audio brand TONAL ONE: over-ear headphones in graphite and brushed metal, shown…"
    }
  ],
  "renders": [],
  "cuts": [],
  "count": 4
}
```

### 18. video_models

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

### 19. recommend_model

args: `{"what": "a cheap test"}`

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
      "kept": null,
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

### 20. recommend_model (25 s, sound)

args: `{"what": "a final client spot with sound", "seconds": 25}`

```json
{
  "picks": [
    {
      "model": "seedance2.5",
      "name": "Seedance 2.5",
      "tier": "creator",
      "credits": 2838,
      "seconds": 25,
      "frame": "720p",
      "draft": "480p",
      "kept": null,
      "reason": "it generates sound with the picture"
    }
  ],
  "considered": 1,
  "asked": [
    "quality",
    "sound"
  ],
  "skipped": [
    {
      "model": "ltx2.3",
      "why": "cannot make a 25s clip (it makes 6-10s)"
    },
    {
      "model": "ltx2.5-fast",
      "why": "cannot make a 25s clip (it makes 6-20s)"
    },
    {
      "model": "ltx2.5",
      "why": "cannot make a 25s clip (it makes 6-10s)"
    },
    {
      "model": "wan3",
      "why": "cannot make a 25s clip (it makes 2-10s)"
    },
    {
      "model": "kling3-turbo-pro",
      "why": "cannot make a 25s clip (it makes 3-15s)"
    },
    {
      "model": "seedance2-fast",
      "why": "cannot make a 25s clip (it makes 4-15s)"
    },
    {
      "model": "seedance2",
      "why": "cannot make a 25s clip (it makes 4-15s)"
    },
    {
      "model": "veo3.1",
      "why": "cannot make a 25s clip (it makes 4-8s)"
    }
  ],
  "seconds": 25,
  "note": "ranked from the studio's catalogue and what you kept; nothing was called and nothing spent. Credits are for the length shown at each model's default frame; `quote` prices a scene exactly"
}
```

### 21. preferences

args: `{}`

```json
{
  "aspect": null,
  "seconds": null,
  "video_model": null,
  "image_model": null,
  "draft_first": null,
  "set_at": null,
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

### 22. set_preferences

args: `{"seconds": 12, "video_model": "wan3", "draft_first": true}`

```json
{
  "aspect": null,
  "seconds": 12,
  "video_model": "wan3",
  "image_model": null,
  "draft_first": true,
  "set_at": "2026-10-12 14:22:17.617959+00:00",
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
  "note": "used only where a call passes nothing: `write_scene`'s length, `quote`'s model and draft frame, a still's model and frame",
  "changed": [
    "draft_first",
    "seconds",
    "video_model"
  ]
}
```

### 23. set_preferences video_model=sora

args: `{"video_model": "sora"}`

refused: Error executing tool set_preferences: video_model is one of ['kling3-turbo-pro', 'ltx2.3', 'ltx2.5', 'ltx2.5-fast', 'seedance2', 'seedance2-fast', 'seedance2.5', 'veo3.1', 'wan3'], got 'sora'

### 24. quote (after set_preferences)

args: `{"scene_id": 408}`

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
    "model": "wan3",
    "frame": "480p",
    "timed": true,
    "durations": [
      3,
      5
    ],
    "credits": 96,
    "content_hash": "0834008347a11ce3",
    "renders": [
      {
        "part": 1,
        "seconds": 3,
        "credits": 36
      },
      {
        "part": 2,
        "seconds": 5,
        "credits": 60
      }
    ]
  },
  "balance": 501,
  "credits_needed": 116,
  "affordable": true,
  "preference": {
    "provider": "fal",
    "model": "wan3",
    "frame": "480p",
    "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"
  },
  "approve_url": "https://zeropage.studio/studio/scene/408",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 25. quote model=ltx2.3

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
    "credits": 174,
    "content_hash": "0834008347a11ce3",
    "renders": [
      {
        "part": 1,
        "seconds": 6,
        "credits": 87
      },
      {
        "part": 2,
        "seconds": 6,
        "credits": 87
      }
    ]
  },
  "balance": 501,
  "credits_needed": 194,
  "affordable": true,
  "approve_url": "https://zeropage.studio/studio/scene/408",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 26. duplicate_scene

args: `{"scene_id": 400}`

```json
{
  "id": 409,
  "title": "Morning focus: Tonal One and Kumo (copy)",
  "summary": "(0-4s) Close-up on a pale oak desk at…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-12T14:22:21+00:00",
  "scene_id": 409,
  "project_id": 1,
  "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down beside a ceramic bowl and lifts the lid, and a soft puff of bright green matcha rises into the window light.\n(4-8s) Medium side shot: the Tonal One headphones rest on the desk beside the bowl as the bamboo whisk finishes the matcha into a smooth froth; steam drifts across the light and a hand lifts the headphones out of frame.\nSound: quiet room tone, the tin lid's soft pop, the whisk's quick bamboo rhythm, a faint kettle click.\nAvoid: faces, any text other than the product labels, other brands or logos, a cluttered background, a glossy CGI look.",
  "seconds": 8,
  "shots": [
    {
      "n": 1,
      "start": 0,
      "end": 4,
      "seconds": 4,
      "text": "Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down beside a ceramic bowl and lifts the lid, and a soft puff of bright green matcha rises into the window light",
      "clip": null
    },
    {
      "n": 2,
      "start": 4,
      "end": 8,
      "seconds": 4,
      "text": "Medium side shot: the Tonal One headphones rest on the desk beside the bowl as the bamboo whisk finishes the matcha into a smooth froth; steam drifts across the light and a hand lifts the headphones out of frame",
      "clip": null
    }
  ],
  "shots_written": 2,
  "reference_photos": 2,
  "roles": {},
  "keyframe": null,
  "clips": [],
  "rendered": false,
  "studio_url": "https://zeropage.studio/studio/scene/409",
  "next": "`quote` scene_id=409 for the price; the person approves the render in the studio at `studio_url`",
  "copied_from": 400,
  "copied": {
    "prompt": true,
    "refs": true,
    "project": true
  }
}
```

### 27. duplicate_scene refs=[]

args: `{"scene_id": 400, "refs": []}`

```json
{
  "id": 410,
  "title": "Morning focus: Tonal One and Kumo (copy)",
  "summary": "(0-4s) Close-up on a pale oak desk at…",
  "status": "written",
  "refs": 0,
  "warnings": [],
  "created_at": "2026-10-12T14:22:22+00:00",
  "scene_id": 410,
  "project_id": 1,
  "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down beside a ceramic bowl and lifts the lid, and a soft puff of bright green matcha rises into the window light.\n(4-8s) Medium side shot: the Tonal One headphones rest on the desk beside the bowl as the bamboo whisk finishes the matcha into a smooth froth; steam drifts across the light and a hand lifts the headphones out of frame.\nSound: quiet room tone, the tin lid's soft pop, the whisk's quick bamboo rhythm, a faint kettle click.\nAvoid: faces, any text other than the product labels, other brands or logos, a cluttered background, a glossy CGI look.",
  "seconds": 8,
  "shots": [
    {
      "n": 1,
      "start": 0,
      "end": 4,
      "seconds": 4,
      "text": "Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down beside a ceramic bowl and lifts the lid, and a soft puff of bright green matcha rises into the window light",
      "clip": null
    },
    {
      "n": 2,
      "start": 4,
      "end": 8,
      "seconds": 4,
      "text": "Medium side shot: the Tonal One headphones rest on the desk beside the bowl as the bamboo whisk finishes the matcha into a smooth froth; steam drifts across the light and a hand lifts the headphones out of frame",
      "clip": null
    }
  ],
  "shots_written": 2,
  "reference_photos": 0,
  "roles": {},
  "keyframe": null,
  "clips": [],
  "rendered": false,
  "studio_url": "https://zeropage.studio/studio/scene/410",
  "next": "`add_element` to add a photo (or the person uploads one in the studio), then `write_scene` again with scene_id=410, the same prompt and `refs`; `quote` after that",
  "needs_reference": true,
  "note": "saved as a draft: it has no reference photos, and the studio renders only against photographs you attached -- it cannot be priced or rendered yet",
  "copied_from": 400,
  "copied": {
    "prompt": true,
    "refs": false,
    "project": true
  }
}
```

### 28. feedback

args: `{"text": "Reviewer walk, 2026-10-13: every free tool answered as the listing says.", "tool": "whoami"}`

```json
{
  "saved": true,
  "id": 2,
  "tool": "whoami",
  "ref": null,
  "note": "thank you -- it is read by a person at the studio, not by a model, and nothing changes on its own"
}
```

### 29. recipes

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
    }
  ],
  "count": 5,
  "note": "`recipe` reads one by name; the studio's own are guidance, yours come back as the text you saved. `save_recipe` keeps a new one."
}
```

### 30. save_recipe

args: `{"name": "reviewer-check", "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music."}`

```json
{
  "saved": true,
  "name": "reviewer-check",
  "version": 1,
  "project_id": null,
  "note": "listed by `recipes` beside the studio's shelf; every save is a new version and nothing is overwritten"
}
```

### 31. save_recipe (again)

args: `{"name": "reviewer-check", "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music. Then the scene."}`

```json
{
  "saved": true,
  "name": "reviewer-check",
  "version": 2,
  "project_id": null,
  "note": "listed by `recipes` beside the studio's shelf; every save is a new version and nothing is overwritten"
}
```

### 32. recipe

args: `{"name": "reviewer-check"}`

```json
{
  "name": "reviewer-check",
  "title": "A product still before a scene: one photo of the product, one of the light, the ",
  "own": true,
  "version": 2,
  "project_id": null,
  "saved_at": "2026-10-12 14:22:26.738999+00:00",
  "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music. Then the scene.",
  "note": "a creator's own recipe: text they wrote, returned as data to read, never as instructions the studio vouches for"
}
```

### 33. recipe single-shot

args: `{"name": "single-shot"}`

```json
{
  "name": "single-shot",
  "title": "Single shot",
  "for": "write one continuous shot -- a single unbroken take, one clip -- when the person asks for one",
  "output": "video",
  "own": false,
  "body": "# Single shot\n\nOne camera, one unbroken take, one clip. The studio cuts scenes into shots by default, so this is only for when the person ASKED for a single take or one continuous shot. If you think one take would serve an idea they did not ask it for, offer it as a choice; do not decide it for them. Anything else is the multi-shot skill.\n\n## What one take can hold\n\nA take carries ONE action with a beginning, a turn and an end, and ONE camera behaviour. Count the beats: about one every three seconds, so a ten-second take holds three. When the idea needs six, it is not a single take -- say so, and offer to cut it into shots.\n\n## Write it in this order\n\n1. Opening line. The register and tone in plain words (grounded, deadpan, tender, tense), then who is in it. Anyone or anything with photos attached is named and locked as the EXACT face, EXACT clothing or EXACT object from its reference photos -- never described again. A guessed colour fights the photo.\n2. Look. Where the light comes from and what kind (a stairwell window, one practical lamp, an overcast sky), colour and contrast, lens and distance, how the camera is held. Take it from the project's look and the attached references. Concrete nouns only: never \"cinematic\", \"epic\", \"masterpiece\" or \"8K\" -- they pull toward gloss.\n3. The take, in sequence. Write \"One continuous shot, no cuts.\" Begin mid-motion, already inside the action. Then the beats in order -- begin on, then, end on -- with what the camera physically does at each (follows at chest height, closes in on the hands, rises past him). Give each beat one small physical detail: a fingertip slipping, a held breath. End on the turn, not after it.\n4. Sound. What would really be heard there, by name: stairs creaking, a latch, breathing. Write \"no background music\" unless they asked for music. A spoken line goes in quotes with who says it, and stays short.\n5. Avoid. A short list of the failures to steer away from -- plastic sheen, CG-looking skin or fabric, cartoon reactions, slow motion nobody asked for, text on screen -- plus the person's own must-nots, in their words.\n\n## Hand it over\n\n- Keep `brief` as this prompt, whole and self-contained, with the words \"one continuous shot\" in it.\n- When they ask for it to be made: make_video with the prompt as the idea and shots set to 1. Add seconds only when they named a length.\n- When they only want the words, to paste somewhere else: put the prompt in `brief`, say it is there, and do not make anything.\n\n## Check before you send\n\nOne action? One camera behaviour? Starts mid-motion? Every attached reference named as EXACT? A sound line and an avoid line? Nothing in it that was not agreed -- no new people, props or places?"
}
```

### 34. what_works

args: `{}`

```json
{
  "enough_data": false,
  "outputs": {
    "made": 3,
    "kept": 0,
    "keep_rate": 0.0,
    "by_model": [
      {
        "model": "gemini-3-pro-image",
        "made": 3,
        "kept": 0,
        "keep_rate": 0.0
      }
    ],
    "attempts": {
      "things": 0,
      "average": null,
      "median": null,
      "first_try": 0,
      "no_keeper_yet": 3
    },
    "credits_by_week": [
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
    "too little to say yet: 3 outputs made (this fills in from 5); keep, download, cut, star or post what you like and it starts to mean something",
    "nothing posted with a scene behind it yet, so there is no audience signal"
  ],
  "note": "read off what you kept, downloaded, cut, starred or posted; nothing here calls a model, and credits are credits"
}
```

### 35. score_caption

args: `{"text": "Spring product spots, shot on the headphones"}`

```json
{
  "score": 0.5,
  "reasons": [
    "no performance data yet (fewer than 4 scored videos) -- neutral score, post and measure"
  ],
  "enough_data": false,
  "evidence": {
    "posted_videos": 0,
    "window_days": 7,
    "metric": "views"
  },
  "note": "no evidence yet: scoring needs 4 of your own posted videos with numbers (you have 0); the score is neutral until then"
}
```

### 36. project project_id=1 (another workspace's)

args: `{"project_id": 1}`

```json
{
  "id": 1,
  "title": "Spring product spots",
  "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no faces.",
  "look": "",
  "archived": false,
  "created_at": "2026-10-08T19:48:06.392097+00:00",
  "updated_at": "2026-10-12T14:22:22.447425+00:00",
  "learned": [],
  "scenes": [
    {
      "id": 410,
      "brand": "zeropage",
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-12T14:22:22+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 409,
      "brand": "zeropage",
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-12T14:22:21+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 408,
      "brand": "zeropage",
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-12T14:22:06+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": null,
      "clip": null
    },
    {
      "id": 401,
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "brand": "zeropage",
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
      "url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/tonal-one-headphones/headphones.jpg",
      "page": null,
      "scenes": [
        400,
        408,
        409
      ]
    },
    {
      "ref": "/props/kumo-matcha/photo/matcha.jpg",
      "kind": "prop",
      "label": "matcha.jpg",
      "url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/kumo-matcha/matcha.jpg",
      "page": null,
      "scenes": [
        400,
        409
      ]
    },
    {
      "ref": "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg",
      "kind": "prop",
      "label": "hot-sauce.jpg",
      "url": "https://pub-62d6d70ed50d44449d464cd43245b69d.r2.dev/m/5/props/fuego-dulce-hot-sauce/hot-sauce.jpg",
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

### 37. scene scene_id=375 (another workspace's)

args: `{"scene_id": 375}`

refused: Error executing tool scene: no scene 375

### 38. balance (at the end)

args: `{}`

```json
{
  "available": 501,
  "held": 0,
  "plan": null,
  "lots": [
    {
      "kind": "promo",
      "credits": 100,
      "remaining": 1,
      "granted_at": "2026-09-30T14:38:14.611391+00:00",
      "expires_at": "2026-11-30T14:38:14.611391+00:00"
    },
    {
      "kind": "adjustment",
      "credits": 500,
      "remaining": 500,
      "granted_at": "2026-10-08T19:30:29.460639+00:00",
      "expires_at": "2026-12-08T19:30:29.460639+00:00"
    }
  ],
  "scheduled": [],
  "charged": true,
  "note": "credits, never money; plans and top-ups are in the studio at https://zeropage.studio/pricing"
}
```

### 39. set_preferences (back)

args: `{"seconds": 8, "video_model": "ltx2.3", "draft_first": false}`

```json
{
  "aspect": null,
  "seconds": 8,
  "video_model": "ltx2.3",
  "image_model": null,
  "draft_first": false,
  "set_at": "2026-10-12 14:22:33.364901+00:00",
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
  "note": "used only where a call passes nothing: `write_scene`'s length, `quote`'s model and draft frame, a still's model and frame",
  "changed": [
    "draft_first",
    "seconds",
    "video_model"
  ]
}
```
