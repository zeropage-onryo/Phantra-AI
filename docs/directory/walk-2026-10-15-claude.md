# Reviewer walk: /mcp/claude as zp-billing-test (2026-10-15)

Run by `ops/connector_walk.py walk claude`. Every answer below is the connector's own, with tokens and URL query strings redacted. PASS means the expectation held; CHECK means read it. A refusal is the connector's own sentence, never retried.

**87 of 87 expectations PASS.**

## Verdicts

| # | tool | expectation | verdict | detail |
|---|---|---|---|---|
| 1 | whoami | whoami names zp-billing-test | PASS | slug 'zp-billing-test', id 5 |
| 1 | whoami | the signed-in member and role are named | PASS | name '', role 'member' |
| 2 | preferences (as found) | the preferences as found, before anything is set | PASS | {"aspect": null, "seconds": 8, "video_model": "ltx2.3", "image_model": null, "draft_first": false} |
| 3 | projects | projects lists 'Spring product spots' | PASS | Spring product spots |
| 4 | project | project opens with its title | PASS | title 'Spring product spots' |
| 5 | elements | elements lists at least two elements with photos | PASS | 5 element(s) |
| 5 | elements | an element named like 'Tonal' has a photo ref | PASS | Tonal One headphones |
| 6 | upload_link | upload_link returns an https /u/ address | PASS | https://api.phantra.ai/u/… |
| 6 | upload_link | upload_link costs 0 credits | PASS | credits 0 |
| 7 | upload the icon to the one-time page, then open it again | the page says Saved | PASS | status 200 |
| 7 | upload the icon to the one-time page, then open it again | the page names an asset:<id> | PASS | asset:7 |
| 7 | upload the icon to the one-time page, then open it again | the page says Added to Reviewer check (prop) | PASS | Saved · Phantra Saved Add a photo to the prop “Reviewer check” in your studio. Your file is in your studio. Filed as asset:7 Kind image Size 512 × 512 Added to Reviewer check (prop) Go back to the cha |
| 7 | upload the icon to the one-time page, then open it again | the page shows a Size line | PASS |  |
| 7 | upload the icon to the one-time page, then open it again | the page shows no Length line for a picture (#284) | PASS |  |
| 7 | upload the icon to the one-time page, then open it again | opening the link again says already used | PASS | status 410: Upload link · Phantra This link can't take a file this upload link was already used -- it saved asset:7. Ask the chat for a new one to upload another file. Go b |
| 8 | elements (after the upload) | elements now lists the prop Reviewer check with a photo | PASS | 5 element(s); before: 5 |
| 9 | write_scene | write_scene answers a scene_id | PASS | 421 |
| 9 | write_scene | the answer carries the light role on the second photo | PASS | {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"} |
| 9 | write_scene | the scene is not a draft (it carries photos) | PASS |  |
| 10 | scene | scene shows two shots | PASS | 2 |
| 10 | scene | scene counts two reference photos | PASS | 2 |
| 10 | scene | scene answers the roles | PASS | {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"} |
| 10 | scene | scene is not rendered yet | PASS |  |
| 11 | quote | quote carries approve_url (the studio's Render card) | PASS | https://phantra.ai/studio/scene/421 |
| 11 | quote | no signed tokens on the Claude listing's quote | PASS |  |
| 11 | quote | quote prices the keyframes | PASS |  |
| 11 | quote | quote shows the balance in credits | PASS | 384 |
| 11 | quote | no dollar key in the quote | PASS |  |
| 11 | quote | quote applies the preference already set (ltx2.3) | PASS | {"provider": "fal", "model": "ltx2.3", "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"} |
| 12 | library | library lists items | PASS | 20 |
| 12 | library | the library holds a rendered clip | PASS | gen:121 |
| 12 | library | the upload is in the library | PASS | asset:7 |
| 13 | reformat | reformat starts a job | PASS | 10 |
| 13 | reformat | reformat costs 0 credits | PASS |  |
| 14 | job (the reformat) | the job ends done | PASS | status 'done' after 1 poll(s) |
| 14 | job (the reformat) | the job names its new gen:<id> | PASS | gen:124 |
| 14 | job (the reformat) | nothing charged | PASS | credits None |
| 15 | trim_clip | trim_clip starts a job | PASS | 11 |
| 16 | job (the trim) | the job ends done | PASS | status 'done' after 1 poll(s) |
| 16 | job (the trim) | the job names its new gen:<id> | PASS | gen:125 |
| 16 | job (the trim) | nothing charged | PASS | credits None |
| 17 | assemble_clips | assemble_clips starts a job | PASS | 12 |
| 18 | job (the join) | the job ends done | PASS | status 'done' after 1 poll(s) |
| 18 | job (the join) | the job names its new gen:<id> | PASS | gen:126 |
| 18 | job (the join) | nothing charged | PASS | credits None |
| 19 | share_link | share_link is an https address | PASS | https://cb326ee64a106f7c8e48dacda39d1b24.r2.cloudflarestorage.com/phantra-media/m/5/renders/cut/cut-f4a77450-2357-4a8b-8b93-d808a5fecbf2-v1-38-ace5000f5d245932109e208efb056dd0.mp4?… |
| 19 | share_link | the link lasts 24 hours | PASS | 24 |
| 20 | share_link hours=200 | hours=200 is refused (1 to 168) | PASS | Error executing tool share_link: hours is 1 to 168 (seven days), got 200 |
| 21 | balance | balance answers available credits | PASS | 384 |
| 21 | balance | no dollar key in balance | PASS |  |
| 22 | credit_history | credit_history has lines | PASS | 16 |
| 22 | credit_history | every line carries balance_after | PASS |  |
| 22 | credit_history | no dollar key in credit_history | PASS |  |
| 23 | recent | recent lists projects, scenes or renders | PASS | projects, scenes, renders |
| 24 | search | search finds the Tonal One prop | PASS |  |
| 24 | search | search finds the written scene | PASS | 421 |
| 25 | video_models | video_models lists the catalogue | PASS | 9 |
| 25 | video_models | wan3 carries a 480p draft frame | PASS | "480p" |
| 25 | video_models | no dollar key in video_models | PASS |  |
| 26 | recommend_model | a cheap test ranks LTX 2.3 first | PASS | ltx2.3 |
| 26 | recommend_model | no dollar key in recommend_model | PASS |  |
| 27 | recommend_model (25 s, sound) | 25 seconds leaves Seedance 2.5 only | PASS | seedance2.5 |
| 28 | preferences | preferences read the same as at the start (unset, or as a previous walk left them) | PASS | {"aspect": null, "seconds": 8, "video_model": "ltx2.3", "image_model": null, "draft_first": false} |
| 28 | preferences | the choices are listed | PASS |  |
| 29 | set_preferences | set_preferences took seconds=12, wan3, draft_first | PASS |  |
| 30 | set_preferences video_model=sora | video_model=sora is refused with the list | PASS | Error executing tool set_preferences: video_model is one of ['kling3-turbo-pro', 'ltx2.3', 'ltx2.5', 'ltx2.5-fast', 'seedance2', 'seedance2-fast', 'seedance2.5', 'veo3.1', 'wan3'], got 'sora' |
| 31 | quote (after set_preferences) | quote applies the wan3 preference | PASS | {"provider": "fal", "model": "wan3", "frame": "480p", "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"} |
| 31 | quote (after set_preferences) | the draft frame 480p is applied | PASS |  |
| 32 | quote model=ltx2.3 | a named model carries no preference | PASS |  |
| 33 | duplicate_scene | duplicate_scene makes a new scene | PASS | 422 |
| 33 | duplicate_scene | it names copied_from | PASS | 400 |
| 33 | duplicate_scene | the copy carries no clip | PASS |  |
| 34 | duplicate_scene refs=[] | a copy with refs=[] is a draft (needs_reference) | PASS |  |
| 35 | feedback | feedback is saved | PASS |  |
| 36 | recipes | recipes lists the studio's shelf (single-shot among them) | PASS | 6 recipe(s); reviewer-check at version 8 |
| 37 | save_recipe | save_recipe answers version 9 | PASS | 9 |
| 38 | save_recipe (again) | save_recipe answers version 10 | PASS | 10 |
| 39 | recipe | recipe returns version 10 with the note that it is the person's own text | PASS | version 10 |
| 40 | recipe single-shot | recipe single-shot is the shelf's | PASS |  |
| 41 | what_works | what_works says whether there is enough data | PASS | True |
| 41 | what_works | no dollar key in what_works | PASS |  |
| 42 | score_caption | score_caption is neutral at 0.5 | PASS | 0.5 |
| 42 | score_caption | score_caption says enough_data false | PASS |  |
| 43 | project project_id=999999 (absent) | a project that does not exist is refused as no project 999999 | PASS | Error executing tool project: no project 999999 -- ids come from `projects` |
| 44 | scene scene_id=375 (another workspace's) | scene 375 is refused as no scene 375 | PASS | Error executing tool scene: no scene 375 |
| 45 | balance (at the end) | the balance is what it was at the start | PASS | 384 -> 384 |
| 46 | set_preferences (back) | preferences set back to what the walk found (or the defaults): seconds=8, video_model=ltx2.3, draft_first=False | PASS |  |
| - | every answer | no dollar sign and no dollar-named key anywhere | PASS |  |

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

### 2. preferences (as found)

args: `{}`

```json
{
  "aspect": null,
  "seconds": 8,
  "video_model": "ltx2.3",
  "image_model": null,
  "draft_first": false,
  "set_at": "2026-10-15 22:41:54.705987+00:00",
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
      "scenes": 17,
      "rendered": 1,
      "archived": false,
      "updated_at": "2026-10-15T22:41:50.068346+00:00",
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
  "updated_at": "2026-10-15T22:41:50.068346+00:00",
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
      "id": 420,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:41:50+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 419,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:49+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 418,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:29+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": null,
      "clip": null
    },
    {
      "id": 417,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:41:00+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 416,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:00+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 415,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:40:45+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": null,
      "clip": null
    },
    {
      "id": 414,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:39:48+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 413,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:39:48+00:00",
      "prompt": "Use the attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match their exact shapes, colours and labels. Style: clean modern product film, soft morning daylight from a side window, warm butter-yellow and pale lilac palette, shallow depth of field, gentle film grain, vertical 9:16.\n(0-4s) Close-up on a pale oak desk at sunrise: a hand sets the Kumo tin down besid",
      "still": null,
      "clip": null
    },
    {
      "id": 412,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:39:30+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": null,
      "clip": null
    },
    {
      "id": 411,
      "title": "Reviewer check: Tonal One push-in (copy)",
      "summary": "(0-6s) Close on the Tonal One headphones resting…",
      "status": "rendered",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-12T14:25:25+00:00",
      "prompt": "(0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. No background music. Only diegetic sound: a chair creak. Avoid: on-screen text, logos, hands, any face.",
      "still": null,
      "clip": "https://media.phantra.ai/m/5/renders/fal/c411-s1-20261012-142649.mp4"
    },
    {
      "id": 410,
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
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "is_scene": true,
      "spark": "",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-12T14:22:06+00:00",
      "prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only dieget",
      "still": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630.png",
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
        408,
        409,
        411,
        412,
        413,
        415,
        416,
        418,
        419
      ]
    },
    {
      "ref": "/props/kumo-matcha/photo/matcha.jpg",
      "kind": "prop",
      "label": "matcha.jpg",
      "url": "https://media.phantra.ai/m/5/props/kumo-matcha/matcha.jpg",
      "page": null,
      "scenes": [
        400,
        409,
        413,
        416,
        419
      ]
    },
    {
      "ref": "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg",
      "kind": "prop",
      "label": "hot-sauce.jpg",
      "url": "https://media.phantra.ai/m/5/props/fuego-dulce-hot-sauce/hot-sauce.jpg",
      "page": null,
      "scenes": [
        408,
        411,
        412,
        415,
        418
      ]
    }
  ],
  "references_truncated": false,
  "renders": [
    {
      "id": "gen:107",
      "kind": "video",
      "model": "ltx2.3",
      "prompt": "RENDER THE CHANGE, not the frame: open already mid-motion, end still moving, and move the camera only with the subject.\n\n(0-6s) Close on the Tonal One headphone",
      "scene": 411,
      "media_url": "https://media.phantra.ai/m/5/renders/fal/c411-s1-20261012-142649.mp4"
    }
  ],
  "chat": [],
  "chat_has_more": false,
  "next": "a reference's `ref` or a render's `gen:<id>` goes wherever a tool takes a reference, and project_id=1 files new work under this project where a tool takes it; `save_chat` keeps this conversation with it; `project_chat` pages back through its history"
}
```

### 5. elements

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
      "name": "Reviewer check",
      "description": "",
      "sheet": null,
      "use": [
        "/props/reviewer-check/photo/up-ef7a3c3e884c5085.jpg",
        "/props/reviewer-check/photo/up-f4731d97adb70aee.jpg"
      ],
      "photos": [
        {
          "ref": "/props/reviewer-check/photo/up-ef7a3c3e884c5085.jpg",
          "label": "up-ef7a3c3e884c5085.jpg"
        },
        {
          "ref": "/props/reviewer-check/photo/up-f4731d97adb70aee.jpg",
          "label": "up-f4731d97adb70aee.jpg"
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

### 6. upload_link

args: `{"purpose": "reference", "element_kind": "prop", "element_name": "Reviewer check"}`

```json
{
  "url": "https://api.phantra.ai/u/…",
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

args: `{"file": "icon512.png"}`

```json
{
  "posted": {
    "status": 200,
    "text": "Saved · Phantra Saved Add a photo to the prop “Reviewer check” in your studio. Your file is in your studio. Filed as asset:7 Kind image Size 512 × 512 Added to Reviewer check (prop) Go back to the chat and say the file is up. This link is used up; ask for a new one to send another file."
  },
  "again": {
    "status": 410,
    "text": "Upload link · Phantra This link can't take a file this upload link was already used -- it saved asset:7. Ask the chat for a new one to upload another file. Go back to the chat and ask for a new upload link if you still want to send a file."
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
      "name": "Reviewer check",
      "description": "",
      "sheet": null,
      "use": [
        "/props/reviewer-check/photo/up-ef7a3c3e884c5085.jpg",
        "/props/reviewer-check/photo/up-f4731d97adb70aee.jpg"
      ],
      "photos": [
        {
          "ref": "/props/reviewer-check/photo/up-ef7a3c3e884c5085.jpg",
          "label": "up-ef7a3c3e884c5085.jpg"
        },
        {
          "ref": "/props/reviewer-check/photo/up-f4731d97adb70aee.jpg",
          "label": "up-f4731d97adb70aee.jpg"
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

### 9. write_scene

args: `{"prompt": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow push in as dust drifts through the beam, the brushed metal of the earcup catching a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones and turns them once, the room falling out of focus behind, the same window light raking the headband. No background music. Only diegetic sound: the faint rustle of a sleeve, a chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a second pair of hands, any face.", "title": "Reviewer check: Tonal One push-in", "refs": ["/props/tonal-one-headphones/photo/headphones.jpg", "/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg"], "roles": {"/props/fuego-dulce-hot-sauce/photo/hot-sauce.jpg": "light"}, "project_id": 1}`

```json
{
  "id": 421,
  "title": "Reviewer check: Tonal One push-in",
  "summary": "(0-3s) Close on the Tonal One headphones resting…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-15T22:42:48+00:00",
  "scene_id": 421,
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
  "studio_url": "https://phantra.ai/studio/scene/421",
  "next": "`quote` scene_id=421 for the price; the person approves the render in the studio at `studio_url`"
}
```

### 10. scene

args: `{"scene_id": 421}`

```json
{
  "id": 421,
  "title": "Reviewer check: Tonal One push-in",
  "summary": "(0-3s) Close on the Tonal One headphones resting…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-15T22:42:48+00:00",
  "scene_id": 421,
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
  "studio_url": "https://phantra.ai/studio/scene/421"
}
```

### 11. quote

args: `{"scene_id": 421}`

```json
{
  "scene_id": 421,
  "status": "written",
  "keyframes": {
    "stills": 2,
    "each": 10,
    "credits": 20
  },
  "clip": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 421,
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
  "balance": 384,
  "credits_needed": 194,
  "affordable": true,
  "preference": {
    "provider": "fal",
    "model": "ltx2.3",
    "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"
  },
  "approve_url": "https://phantra.ai/studio/scene/421",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 12. library

args: `{}`

```json
{
  "count": 20,
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
      "id": "gen:122",
      "kind": "video",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-a8ab2d97-a9ae-4618-95ea-c69c08043e16-v1-35-7a44de821152575652b380873c379dd9.mp4",
      "created_at": "2026-10-15T22:41:42+00:00",
      "model": "join",
      "prompt": "Joined 2 clips: gen:120, gen:121"
    },
    {
      "id": "gen:121",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 257177,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-3e2d173b-a9b2-419a-b790-d52ed2ef9c90-v1-34-831cb761957d502a539c57d5251ce7f6.mp4",
      "created_at": "2026-10-15T22:41:37+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:115 to 0-1s"
    },
    {
      "id": "gen:120",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 204701,
      "frame": "720x1280",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-95e52a33-b167-4800-8743-c817ed08a960-v1-33-759b880b5ed2ded87121058f46006984.mp4",
      "created_at": "2026-10-15T22:41:33+00:00",
      "model": "reformat",
      "prompt": "Reformatted gen:115 to 9:16 (crop)"
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
      "id": "gen:117",
      "kind": "video",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-d33bfa08-b7aa-4f88-9c2b-2e0e62238349-v1-32-351837e44a7ef68b1e4135e54cc8610b.mp4",
      "created_at": "2026-10-15T22:40:52+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:115 to 0-1s"
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
      "id": "gen:115",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 268966,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-9d01d156-3a5f-44cc-824b-bf7c0cf2dd97-v1-31-43533e5d9a0f1180554e667cc456d363.mp4",
      "created_at": "2026-10-15T22:39:38+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:110 to 0-1s"
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
      "id": "gen:110",
      "kind": "video",
      "origin": "render",
      "seconds": 7.1,
      "size_bytes": 1915060,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-806c4b18-72f5-4a47-8e78-246c51b49b06-v1-29.mp4",
      "created_at": "2026-10-12T14:30:19+00:00",
      "model": "join",
      "prompt": "Joined 2 clips: gen:108, gen:109"
    },
    {
      "id": "gen:109",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 421678,
      "frame": "1080x1920",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-0b347985-6587-420f-848e-da904d9d87cd-v1-28.mp4",
      "created_at": "2026-10-12T14:30:06+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:107 to 0-1s"
    },
    {
      "id": "gen:108",
      "kind": "video",
      "origin": "render",
      "seconds": 6.1,
      "size_bytes": 1788697,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-a46972c1-fde0-430c-922c-b83c1d971f7c-v1-27.mp4",
      "created_at": "2026-10-12T14:29:59+00:00",
      "model": "reformat",
      "prompt": "Reformatted gen:107 to 1:1 (crop)"
    },
    {
      "id": "gen:107",
      "kind": "video",
      "origin": "render",
      "seconds": 6.12,
      "size_bytes": 2875965,
      "frame": "1080x1920",
      "aspect": "9:16",
      "project": {
        "id": 1,
        "title": "Spring product spots"
      },
      "media_url": "https://media.phantra.ai/m/5/renders/fal/c411-s1-20261012-142649.mp4",
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
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142637.png",
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
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c408-20261012-142630.png",
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
      "media_url": "https://media.phantra.ai/m/5/renders/fal/flux-pro1.1-20261012-142508.jpg",
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
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145537.png",
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
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145453.png",
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
      "media_url": "https://media.phantra.ai/m/5/renders/nano/c386-20260930-145406.png",
      "created_at": "2026-09-30T14:54:45+00:00",
      "model": "gemini-3-pro-image",
      "prompt": "CONTINUITY -- the same scene as every other shot, keep it identical: Male subjec"
    }
  ],
  "note": ""
}
```

### 13. reformat

args: `{"ref": "gen:121", "aspect": "9:16", "fit": "crop", "title": "Reviewer check 9:16"}`

```json
{
  "job_id": 10,
  "status": "running",
  "label": "reformat gen:121 to 9:16",
  "note": "Making gen:121 as 9:16 (crop). It runs on the studio's server -- no credits are spent. Poll `job`: the result is a gen:<id> in your library.",
  "plan": {
    "source": "gen:121",
    "aspect": "9:16",
    "fit": "crop",
    "size": [
      720,
      1280
    ],
    "still": false,
    "crop": {
      "left": 0.2188,
      "right": 0.2188,
      "top": 0.0,
      "bottom": 0.0
    },
    "source_size": [
      1080,
      1080
    ],
    "seconds": 1.0,
    "credits": 0
  }
}
```

### 14. job (the reformat)

args: `{"job_id": 10, "wait": 15}`
polls: 1

```json
{
  "id": 10,
  "kind": "mcp",
  "label": "reformat gen:121 to 9:16",
  "status": "done",
  "progress": 1.0,
  "detail": "",
  "error": null,
  "ref_id": null,
  "cancellable": false,
  "started_at": "2026-10-15T22:42:50+00:00",
  "ended_at": "2026-10-15T22:42:52+00:00",
  "account_id": 5,
  "result": {
    "ok": true,
    "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-0d399971-d7da-406a-8b76-64dadd0817e1-v1-36-9443bbdaa796f555db58d5cd8eb56375.mp4",
    "asset_id": 124,
    "ref": "gen:124",
    "generation_id": 168,
    "media_kind": "video",
    "seconds": 1.0,
    "size": [
      720,
      1280
    ],
    "cut_project": {
      "id": "0d399971-d7da-406a-8b76-64dadd0817e1",
      "title": "Reviewer check 9:16",
      "version": 1
    },
    "notes": [],
    "credits": 0,
    "note": "Made on the studio's server with ffmpeg -- no credits were spent.",
    "plan": {
      "source": "gen:121",
      "aspect": "9:16",
      "fit": "crop",
      "size": [
        720,
        1280
      ],
      "still": false,
      "crop": {
        "left": 0.2188,
        "right": 0.2188,
        "top": 0.0,
        "bottom": 0.0
      },
      "source_size": [
        1080,
        1080
      ],
      "seconds": 1.0,
      "credits": 0
    }
  }
}
```

### 15. trim_clip

args: `{"ref": "gen:121", "start": 0, "end": 1, "title": "Reviewer check first second"}`

```json
{
  "job_id": 11,
  "status": "running",
  "label": "trim gen:121",
  "note": "Trimming gen:121 to 0-1s. It runs on the studio's server -- no credits are spent. Poll `job`: the result is a gen:<id> in your library.",
  "plan": {
    "source": "gen:121",
    "start": 0.0,
    "end": 1.0,
    "seconds": 1.0,
    "size": [
      1080,
      1080
    ],
    "credits": 0
  }
}
```

### 16. job (the trim)

args: `{"job_id": 11, "wait": 15}`
polls: 1

```json
{
  "id": 11,
  "kind": "mcp",
  "label": "trim gen:121",
  "status": "done",
  "progress": 1.0,
  "detail": "",
  "error": null,
  "ref_id": null,
  "cancellable": false,
  "started_at": "2026-10-15T22:42:53+00:00",
  "ended_at": "2026-10-15T22:42:57+00:00",
  "account_id": 5,
  "result": {
    "ok": true,
    "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-5fbe275b-a4c2-4308-80d5-a7879ec2b3f3-v1-37-58929135ab891d40f7c54dfa08e01d13.mp4",
    "asset_id": 125,
    "ref": "gen:125",
    "generation_id": 169,
    "media_kind": "video",
    "seconds": 1.0,
    "size": [
      1080,
      1080
    ],
    "cut_project": {
      "id": "5fbe275b-a4c2-4308-80d5-a7879ec2b3f3",
      "title": "Reviewer check first second",
      "version": 1
    },
    "notes": [],
    "credits": 0,
    "note": "Made on the studio's server with ffmpeg -- no credits were spent.",
    "plan": {
      "source": "gen:121",
      "start": 0.0,
      "end": 1.0,
      "seconds": 1.0,
      "size": [
        1080,
        1080
      ],
      "credits": 0
    }
  }
}
```

### 17. assemble_clips

args: `{"clips": ["gen:124", "gen:125"], "letterbox": true, "title": "Reviewer check joined"}`

```json
{
  "job_id": 12,
  "status": "running",
  "label": "join 2 clips",
  "note": "Joining 2 clips (about 2s). It runs on the studio's server -- no credits are spent. Poll `job`: the result is a gen:<id> in your library.",
  "plan": {
    "clips": [
      "gen:124",
      "gen:125"
    ],
    "seconds": 2.0,
    "canvas": {
      "width": 720,
      "height": 1280,
      "aspect": "9:16"
    },
    "transition": "cut",
    "crossfade_s": null,
    "music": null,
    "letterboxed": [
      "gen:125"
    ],
    "notes": [],
    "credits": 0
  }
}
```

### 18. job (the join)

args: `{"job_id": 12, "wait": 15}`
polls: 1

```json
{
  "id": 12,
  "kind": "mcp",
  "label": "join 2 clips",
  "status": "done",
  "progress": 1.0,
  "detail": "",
  "error": null,
  "ref_id": null,
  "cancellable": false,
  "started_at": "2026-10-15T22:42:57+00:00",
  "ended_at": "2026-10-15T22:43:01+00:00",
  "account_id": 5,
  "result": {
    "ok": true,
    "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-f4a77450-2357-4a8b-8b93-d808a5fecbf2-v1-38-ace5000f5d245932109e208efb056dd0.mp4",
    "asset_id": 126,
    "ref": "gen:126",
    "generation_id": 170,
    "media_kind": "video",
    "seconds": 2.0,
    "canvas": {
      "width": 720,
      "height": 1280,
      "aspect": "9:16"
    },
    "cut_project": {
      "id": "f4a77450-2357-4a8b-8b93-d808a5fecbf2",
      "title": "Reviewer check joined",
      "version": 1
    },
    "notes": [],
    "credits": 0,
    "note": "Joined on the studio's server with ffmpeg -- no credits were spent.",
    "plan": {
      "clips": [
        "gen:124",
        "gen:125"
      ],
      "seconds": 2.0,
      "canvas": {
        "width": 720,
        "height": 1280,
        "aspect": "9:16"
      },
      "transition": "cut",
      "crossfade_s": null,
      "music": null,
      "letterboxed": [
        "gen:125"
      ],
      "notes": [],
      "credits": 0
    }
  }
}
```

### 19. share_link

args: `{"ref": "gen:126"}`

```json
{
  "ref": "gen:126",
  "kind": "video",
  "url": "https://cb326ee64a106f7c8e48dacda39d1b24.r2.cloudflarestorage.com/phantra-media/m/5/renders/cut/cut-f4a77450-2357-4a8b-8b93-d808a5fecbf2-v1-38-ace5000f5d245932109e208efb056dd0.mp4?…",
  "filename": "phantra-cut-126.mp4",
  "hours": 24,
  "expires_at": "2026-10-16T22:43:02.003984+00:00",
  "note": "a link that downloads the file; anyone holding it can open it until it expires"
}
```

### 20. share_link hours=200

args: `{"ref": "gen:126", "hours": 200}`

refused: Error executing tool share_link: hours is 1 to 168 (seven days), got 200

### 21. balance

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
  "note": "credits, never money; credits are added in the Phantra studio"
}
```

### 22. credit_history

args: `{}`

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
  "count": 16,
  "note": "credits only, newest first; pass `next` as `before` for the page after"
}
```

### 23. recent

args: `{}`

```json
{
  "projects": [
    {
      "id": 1,
      "title": "Spring product spots",
      "brief": "Four short vertical spots for invented brands: Solene perfume, Tonal One headphones, Fuego Dulce hot sauce and Kumo matcha. One product hero per spot, clean studio or window light, hands welcome, no f",
      "has_look": false,
      "scenes": 18,
      "rendered": 1,
      "archived": false,
      "updated_at": "2026-10-15T22:42:48.474215+00:00",
      "cover": "https://media.phantra.ai/m/5/props/tonal-one-headphones/headphones.jpg"
    }
  ],
  "scenes": [
    {
      "id": 421,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:42:48+00:00",
      "scene_id": 421,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/421"
    },
    {
      "id": 420,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:41:50+00:00",
      "scene_id": 420,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/420"
    },
    {
      "id": 419,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:49+00:00",
      "scene_id": 419,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/419"
    },
    {
      "id": 418,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:29+00:00",
      "scene_id": 418,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/418"
    },
    {
      "id": 417,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:41:00+00:00",
      "scene_id": 417,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/417"
    },
    {
      "id": 416,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:41:00+00:00",
      "scene_id": 416,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/416"
    },
    {
      "id": 415,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:40:45+00:00",
      "scene_id": 415,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/415"
    },
    {
      "id": 414,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 0,
      "warnings": [],
      "created_at": "2026-10-15T22:39:48+00:00",
      "scene_id": 414,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/414"
    },
    {
      "id": 413,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "summary": "(0-4s) Close-up on a pale oak desk at…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:39:48+00:00",
      "scene_id": 413,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/413"
    },
    {
      "id": 412,
      "title": "Reviewer check: Tonal One push-in",
      "summary": "(0-3s) Close on the Tonal One headphones resting…",
      "status": "written",
      "refs": 2,
      "warnings": [],
      "created_at": "2026-10-15T22:39:30+00:00",
      "scene_id": 412,
      "project_id": 1,
      "studio_url": "https://phantra.ai/studio/scene/412"
    }
  ],
  "renders": [
    {
      "id": "gen:126",
      "kind": "video",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-f4a77450-2357-4a8b-8b93-d808a5fecbf2-v1-38-ace5000f5d245932109e208efb056dd0.mp4",
      "created_at": "2026-10-15T22:43:00+00:00",
      "model": "join",
      "prompt": "Joined 2 clips: gen:124, gen:125"
    },
    {
      "id": "gen:125",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 254361,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-5fbe275b-a4c2-4308-80d5-a7879ec2b3f3-v1-37-58929135ab891d40f7c54dfa08e01d13.mp4",
      "created_at": "2026-10-15T22:42:56+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:121 to 0-1s"
    },
    {
      "id": "gen:124",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 203900,
      "frame": "720x1280",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-0d399971-d7da-406a-8b76-64dadd0817e1-v1-36-9443bbdaa796f555db58d5cd8eb56375.mp4",
      "created_at": "2026-10-15T22:42:52+00:00",
      "model": "reformat",
      "prompt": "Reformatted gen:121 to 9:16 (crop)"
    },
    {
      "id": "gen:122",
      "kind": "video",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-a8ab2d97-a9ae-4618-95ea-c69c08043e16-v1-35-7a44de821152575652b380873c379dd9.mp4",
      "created_at": "2026-10-15T22:41:42+00:00",
      "model": "join",
      "prompt": "Joined 2 clips: gen:120, gen:121"
    },
    {
      "id": "gen:121",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 257177,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-3e2d173b-a9b2-419a-b790-d52ed2ef9c90-v1-34-831cb761957d502a539c57d5251ce7f6.mp4",
      "created_at": "2026-10-15T22:41:37+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:115 to 0-1s"
    },
    {
      "id": "gen:120",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 204701,
      "frame": "720x1280",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-95e52a33-b167-4800-8743-c817ed08a960-v1-33-759b880b5ed2ded87121058f46006984.mp4",
      "created_at": "2026-10-15T22:41:33+00:00",
      "model": "reformat",
      "prompt": "Reformatted gen:115 to 9:16 (crop)"
    },
    {
      "id": "gen:117",
      "kind": "video",
      "origin": "render",
      "seconds": null,
      "size_bytes": null,
      "frame": null,
      "aspect": null,
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-d33bfa08-b7aa-4f88-9c2b-2e0e62238349-v1-32-351837e44a7ef68b1e4135e54cc8610b.mp4",
      "created_at": "2026-10-15T22:40:52+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:115 to 0-1s"
    },
    {
      "id": "gen:115",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 268966,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-9d01d156-3a5f-44cc-824b-bf7c0cf2dd97-v1-31-43533e5d9a0f1180554e667cc456d363.mp4",
      "created_at": "2026-10-15T22:39:38+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:110 to 0-1s"
    },
    {
      "id": "gen:110",
      "kind": "video",
      "origin": "render",
      "seconds": 7.1,
      "size_bytes": 1915060,
      "frame": "1080x1080",
      "aspect": "1:1",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-806c4b18-72f5-4a47-8e78-246c51b49b06-v1-29.mp4",
      "created_at": "2026-10-12T14:30:19+00:00",
      "model": "join",
      "prompt": "Joined 2 clips: gen:108, gen:109"
    },
    {
      "id": "gen:109",
      "kind": "video",
      "origin": "render",
      "seconds": 1.0,
      "size_bytes": 421678,
      "frame": "1080x1920",
      "aspect": "9:16",
      "project": null,
      "media_url": "https://media.phantra.ai/m/5/renders/cut/cut-0b347985-6587-420f-848e-da904d9d87cd-v1-28.mp4",
      "created_at": "2026-10-12T14:30:06+00:00",
      "model": "trim",
      "prompt": "Trimmed gen:107 to 0-1s"
    }
  ]
}
```

### 24. search

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
      "scene_id": 421,
      "title": "Reviewer check: Tonal One push-in",
      "sub": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow pu…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/421"
    },
    {
      "scene_id": 420,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "sub": "…attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match th…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/420"
    },
    {
      "scene_id": 419,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "sub": "…attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match th…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/419"
    },
    {
      "scene_id": 418,
      "title": "Reviewer check: Tonal One push-in",
      "sub": "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow pu…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/418"
    },
    {
      "scene_id": 417,
      "title": "Morning focus: Tonal One and Kumo (copy)",
      "sub": "…attached photos: the Tonal One headphones (photo 1) and the Kumo matcha tin (photo 2); match th…",
      "project_id": 1,
      "project_title": "Spring product spots",
      "rendered": false,
      "archived": false,
      "studio_url": "https://phantra.ai/studio/scene/417"
    }
  ],
  "elements": [
    {
      "kind": "product",
      "name": "Tonal One headphones",
      "sub": "Invented audio brand TONAL ONE: over-ear headphones in graphite and brushed metal, shown…"
    }
  ],
  "renders": [
    {
      "id": "gen:107",
      "kind": "video",
      "model": "LTX 2.3",
      "sub": "…. (0-6s) Close on the Tonal One headphones resting on a slate desk in soft window light; a slow…"
    },
    {
      "id": "gen:106",
      "kind": "image",
      "model": "Nano Banana",
      "sub": "…of a sleeve, a chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a sec…"
    },
    {
      "id": "gen:105",
      "kind": "image",
      "model": "Nano Banana",
      "sub": "…of a sleeve, a chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a sec…"
    },
    {
      "id": "gen:104",
      "kind": "image",
      "model": "Fal",
      "sub": "A single pair of over-ear headphones on a slate desk in soft window light, product still, no tex…"
    }
  ],
  "cuts": [],
  "count": 11
}
```

### 25. video_models

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

### 26. recommend_model

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

### 27. recommend_model (25 s, sound)

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

### 28. preferences

args: `{}`

```json
{
  "aspect": null,
  "seconds": 8,
  "video_model": "ltx2.3",
  "image_model": null,
  "draft_first": false,
  "set_at": "2026-10-15 22:41:54.705987+00:00",
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

### 29. set_preferences

args: `{"seconds": 12, "video_model": "wan3", "draft_first": true}`

```json
{
  "aspect": null,
  "seconds": 12,
  "video_model": "wan3",
  "image_model": null,
  "draft_first": true,
  "set_at": "2026-10-15 22:43:07.060732+00:00",
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

### 30. set_preferences video_model=sora

args: `{"video_model": "sora"}`

refused: Error executing tool set_preferences: video_model is one of ['kling3-turbo-pro', 'ltx2.3', 'ltx2.5', 'ltx2.5-fast', 'seedance2', 'seedance2-fast', 'seedance2.5', 'veo3.1', 'wan3'], got 'sora'

### 31. quote (after set_preferences)

args: `{"scene_id": 421}`

```json
{
  "scene_id": 421,
  "status": "written",
  "keyframes": {
    "stills": 2,
    "each": 10,
    "credits": 20
  },
  "clip": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 421,
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
  "balance": 384,
  "credits_needed": 116,
  "affordable": true,
  "preference": {
    "provider": "fal",
    "model": "wan3",
    "frame": "480p",
    "note": "your workspace's default renderer (`preferences`); name the same choice where the render is approved"
  },
  "approve_url": "https://phantra.ai/studio/scene/421",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 32. quote model=ltx2.3

args: `{"scene_id": 421, "model": "ltx2.3"}`

```json
{
  "scene_id": 421,
  "status": "written",
  "keyframes": {
    "stills": 2,
    "each": 10,
    "credits": 20
  },
  "clip": {
    "pricing_version": "2026-09-26-fal-v3",
    "shot_id": 421,
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
  "balance": 384,
  "credits_needed": 194,
  "affordable": true,
  "approve_url": "https://phantra.ai/studio/scene/421",
  "note": "the person approves this render in the studio at `approve_url`, where the price is shown again before anything is spent"
}
```

### 33. duplicate_scene

args: `{"scene_id": 400}`

```json
{
  "id": 422,
  "title": "Morning focus: Tonal One and Kumo (copy)",
  "summary": "(0-4s) Close-up on a pale oak desk at…",
  "status": "written",
  "refs": 2,
  "warnings": [],
  "created_at": "2026-10-15T22:43:08+00:00",
  "scene_id": 422,
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
  "studio_url": "https://phantra.ai/studio/scene/422",
  "next": "`quote` scene_id=422 for the price; the person approves the render in the studio at `studio_url`",
  "copied_from": 400,
  "copied": {
    "prompt": true,
    "refs": true,
    "project": true
  }
}
```

### 34. duplicate_scene refs=[]

args: `{"scene_id": 400, "refs": []}`

```json
{
  "id": 423,
  "title": "Morning focus: Tonal One and Kumo (copy)",
  "summary": "(0-4s) Close-up on a pale oak desk at…",
  "status": "written",
  "refs": 0,
  "warnings": [],
  "created_at": "2026-10-15T22:43:09+00:00",
  "scene_id": 423,
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
  "studio_url": "https://phantra.ai/studio/scene/423",
  "next": "`add_element` to add a photo (or the person uploads one in the studio), then `write_scene` again with scene_id=423, the same prompt and `refs`; `quote` after that",
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

### 35. feedback

args: `{"text": "Reviewer walk, 2026-10-13: every free tool answered as the listing says.", "tool": "whoami"}`

```json
{
  "saved": true,
  "id": 6,
  "tool": "whoami",
  "ref": null,
  "note": "thank you -- it is read by a person at the studio, not by a model, and nothing changes on its own"
}
```

### 36. recipes

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
      "versions": 8,
      "project_id": null,
      "updated_at": "2026-10-15 22:41:51.534824+00:00",
      "own": true
    }
  ],
  "count": 6,
  "note": "`recipe` reads one by name; the studio's own are guidance, yours come back as the text you saved. `save_recipe` keeps a new one."
}
```

### 37. save_recipe

args: `{"name": "reviewer-check", "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music."}`

```json
{
  "saved": true,
  "name": "reviewer-check",
  "version": 9,
  "project_id": null,
  "note": "listed by `recipes` beside the studio's shelf; every save is a new version and nothing is overwritten"
}
```

### 38. save_recipe (again)

args: `{"name": "reviewer-check", "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music. Then the scene."}`

```json
{
  "saved": true,
  "name": "reviewer-check",
  "version": 10,
  "project_id": null,
  "note": "listed by `recipes` beside the studio's shelf; every save is a new version and nothing is overwritten"
}
```

### 39. recipe

args: `{"name": "reviewer-check"}`

```json
{
  "name": "reviewer-check",
  "title": "A product still before a scene: one photo of the product, one of the light, the ",
  "own": true,
  "version": 10,
  "project_id": null,
  "saved_at": "2026-10-15 22:43:11.645967+00:00",
  "body": "A product still before a scene: one photo of the product, one of the light, the product's photo first, a single push-in, no music. Then the scene.",
  "note": "a creator's own recipe: text they wrote, returned as data to read, never as instructions the studio vouches for"
}
```

### 40. recipe single-shot

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

### 41. what_works

args: `{}`

```json
{
  "enough_data": true,
  "outputs": {
    "made": 18,
    "kept": 11,
    "keep_rate": 0.611,
    "by_model": [
      {
        "model": "trim",
        "made": 5,
        "kept": 4,
        "keep_rate": 0.8
      },
      {
        "model": "reformat",
        "made": 3,
        "kept": 3,
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
        "model": "gemini-2.5-flash-image",
        "made": 2,
        "kept": 0,
        "keep_rate": 0.0
      },
      {
        "model": "flux-pro1.1",
        "made": 1,
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
      "no_keeper_yet": 6
    },
    "credits_by_week": [
      {
        "week": "2026-10-12",
        "credits": 97,
        "made": 15,
        "kept": 11,
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
        "made": 15,
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
    "you kept 11 of 18 outputs (61%)",
    "on trim: kept 4 of 5",
    "on reformat: kept 3 of 3",
    "on join: kept 3 of 3",
    "a keeper takes 1.09 tries on average",
    "nothing posted with a scene behind it yet, so there is no audience signal"
  ],
  "note": "read off what you kept, downloaded, cut, starred or posted; nothing here calls a model, and credits are credits"
}
```

### 42. score_caption

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

### 43. project project_id=999999 (absent)

args: `{"project_id": 999999}`

refused: Error executing tool project: no project 999999 -- ids come from `projects`

### 44. scene scene_id=375 (another workspace's)

args: `{"scene_id": 375}`

refused: Error executing tool scene: no scene 375

### 45. balance (at the end)

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
  "note": "credits, never money; credits are added in the Phantra studio"
}
```

### 46. set_preferences (back)

args: `{"seconds": 8, "video_model": "ltx2.3", "draft_first": false}`

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
  "note": "used only where a call passes nothing: `write_scene`'s length, `quote`'s model and draft frame, a still's model and frame",
  "changed": [
    "draft_first",
    "seconds",
    "video_model"
  ]
}
```
