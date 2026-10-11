"""
The MCP surface: the studio, reachable from Claude.

WHY AN ADAPTER AND NOT A STORE. Everything this project holds lives in its
own tables -- scenes in `shoot_concepts`, projects, elements, renders. A
second store synced against those would be the same mistake `asset_shelf`
exists to fix: two places holding one fact, drifting apart the first time a
write path forgets the other. So nothing here holds state. Every function
below is a thin call into the module that owns the rows.

TWO SERVERS, ONE MODULE (`build_server`):

- THE STUDIO SURFACE (`surface="studio"`, the default) is what
  `python -m src.mcp_server` serves -- what Claude Desktop launches -- and
  what the operator's static key reaches on the HTTP mount: images, video,
  effects and element sheets on fal, each one quoted first and spent only
  after the person says yes in chat (`approval_gate`: a price in credits and
  a signed token bound to the exact request, redeemed once --
  `start_approved`), plus projects and the lists a reference can name.
- THE LISTED SERVER (`listed=True`) is what a signed-in stranger reaches
  through the directory connector: their projects and elements, and the one
  path Claude writes a scene, prices it and -- on the person's yes --
  renders it (`write_scene`, `quote`, `approve`).

NO IDEA BOARD (2026-10-11, docs/tasks/task-higgsfield-shape.md, Mike's
call). From 2026-08-31 this module's first job was the board: read the
concepts, pick one, archive three, bank a direction for the night. There
was a third, "board" surface carrying those tools (`board`, `idea`,
`search`, `capture`, `pick`, `shoot`, `archive`, `stats`), the spark bank's
(`add_spark`, `tonight`, `sparks`, `images`, `reference`,
`imagine_reference`) and the two engine tools (`research`, `generate`).
The studio has no board any more -- a scene is made in a project and
rendered from the scene -- so that surface and those tools are gone. What
is left of the spark bank here is the plain functions `ops/bank.py` calls
(`bank_spark`, `bank_reference`); they are no longer tools.

TWO LAYERS, ON PURPOSE. The functions here are plain Python against a
database URL; the MCP wrapper around them is built lazily in
`build_server`. So the whole tool surface stays testable with no `mcp`
package installed, and a machine that never serves MCP does not grow an
import-time dependency on one -- the same degrade-don't-break rule the
rest of src/ follows.
"""
from __future__ import annotations

import contextvars
import os
import sys
from pathlib import Path
from typing import Any, Literal, Optional

# typing_extensions', NOT typing's: pydantic (which the SDK builds every
# tool's schema with) refuses `typing.TypedDict` on Python < 3.12, and the
# Fly image is 3.11 -- so `save_chat`'s argument type took the whole server
# down there (2026-10-08: /mcp unmounted after #165) while CI (3.12) and
# this Mac (3.13) passed. tests/test_mcp_server.py builds every surface
# under 3.11's rule.
from typing_extensions import TypedDict

from . import accounts, autonomy, db, imagesearch, outcomes, preprod, refbin, scout

# What a spark typed by a human scores. `scout.next_spark` serves the
# highest-scoring unused finding at or above SCORE_FLOOR (0.55), so a
# hand-banked spark has to outrank a crawled one. Read by ops/bank.py.
HUMAN_SPARK_SCORE = 1.0

# A list call returns cards, not whole rows: a scene prompt is ~1200
# characters and a project holds dozens.
LIST_LIMIT = 25

# --- what the directory publishes (2026-10-07) ------------------------------
#
# One constant per registered tool, in `build_server`'s order. These are
# what a STRANGER reads -- a creator who installed the connector from the
# directory and has none of this repo's vocabulary -- so they say what the
# tool does and when to call it, in the product's words (project, scene,
# element, reference image, the studio), and nothing about how it is run
# here. A test pins every registered tool to its row and screens the words.

DEFAULT_BRAND = "zeropage"

# What the LISTED server tells Claude about itself (the studio surface has
# its own, STUDIO_INSTRUCTIONS).
INSTRUCTIONS = (
    "Your studio: write a scene into a project and render it. You write the "
    "scene prompt in this chat; `elements` lists the person's own photos and "
    "`add_element` adds one from a picture they give you -- a scene can be "
    "priced and rendered once it is held to at least one of them. `write_scene` "
    "saves it, `quote` says what the keyframes and the clip would cost in "
    "credits, and `approve` renders -- only after the person has seen that "
    "price and said yes. `generate_image` draws a still, quoted first and "
    "drawn only on the same yes. Never approve on their behalf, and stop when "
    "a call is refused for credits. `projects` / `project` reopen their work "
    "with its brief, look, scenes, references and chat. Renders run in the "
    "background: poll `job`, or read `scene` for the clips."
)

# THE CLAUDE DIRECTORY'S LISTING (2026-10-11, Mike's call: list in BOTH the
# Claude and the ChatGPT directories). Anthropic's connector checklist refuses
# connectors that "generate images, video, or audio through AI models"; OpenAI's
# guidelines do not. So /mcp (LISTED_TOOLS, the ChatGPT listing) can `approve`,
# and /mcp/claude (CLAUDE_LISTED_TOOLS) prices the render and hands the person
# the scene's page in the studio, where its Render card is the approve. The
# spend itself never moved. docs/directory/TWO_LISTINGS.md.
CLAUDE_INSTRUCTIONS = (
    "Zeropage Studio: plan video scenes with your own photos, ready to render "
    "in the studio. You write the scene prompt in this chat; `elements` lists "
    "the person's own photos and `add_element` adds one from a picture they "
    "give you -- a scene can be priced and rendered once it is held to at "
    "least one of them. "
    "`write_scene` saves it, and `quote` says what rendering it would cost in "
    "credits and gives the studio link where the person approves the render -- "
    "nothing in this connector renders or spends credits. `projects` / "
    "`project` reopen their work with its brief, look, scenes, references and "
    "chat; `scene` shows where a scene stands and its clips."
)

TITLES = {
    "images_for": "Find reference images",
    "job": "Check a background job",
    "cancel_job": "Cancel a render, effect or sheet in progress",
    "assemble_clips": "Join clips into one video (no credits)",
    "import_file": "Import an image or clip from this computer",
    "prepare_post": "Prepare a post for the person to review and send",
    "edit_clip": "Edit a clip by instruction, a frame first (quoted, spends credits)",
    "elements": "List your elements (reference photos)",
    "add_element": "Add a picture as an element (no credits)",
    "write_scene": "Save a scene you wrote",
    "quote": "Price the keyframes and the clip",
    "approve": "Approve a priced render (spends credits)",
    "image_models": "List the image models",
    "video_models": "List the video models",
    "effects": "List the effects",
    "renders": "List your recent renders",
    "prompt_craft": "Get the studio's prompt guides",
    "generate_image": "Render an image (quoted first, spends credits)",
    "generate_video": "Render a video clip (quoted first, spends credits)",
    "apply_effect": "Apply an effect (quoted first, spends credits)",
    "element_sheet": "Draw an element's reference sheet (quoted first, spends credits)",
    "projects": "List your projects",
    "project": "Open one project",
    "project_chat": "Read a project's chat history",
    "create_project": "Create a project",
    "save_chat": "Save this chat into a project",
    "scene": "Read one scene and its renders",
}

_CAP = f"Returns at most `limit` rows (default {LIST_LIMIT}, maximum 100)"
# The chat approval every spending tool on the studio surface asks for,
# and the ids a render or an effect is pointed at -- said once, the same
# way in every description that needs them.
_APPROVAL = (
    "Two calls: the first (no `quote_token`) spends nothing and returns the "
    "quote -- exactly what will run, its price in credits, the balance and the "
    "balance after it, and a `quote_token`. Show the person and wait for a yes; "
    "only then call again with the SAME arguments plus that `quote_token`. A "
    "token is good for one hour, for exactly that request, and once: a changed "
    "argument is refused, and a repeated call returns the first job instead of "
    "charging again. A balance too short comes back as `refused: "
    "insufficient_credits` with `needs`, `available` and `upgrade_url` -- stop "
    "and tell the person, with that link."
)
_REFERENCE_IDS = (
    "References are ids, never URLs: `gen:<id>` (an image from `renders` or "
    "a project), `asset:<id>` (an image you brought in with `import_file`), a "
    "photo `ref` exactly as `elements` or `project` lists it, or "
    "`candidate:<id>` (an id `images_for` returned)."
)
_PROJECT_FILING = (
    "`project_id` (from `projects`) files the result under that project, so "
    "it is there when the project is opened again."
)
# `add_element`, said once for the three servers that word its `source`
# differently (each names only the ids its own tools hand out).
_ELEMENT_ARGS = (
    "`kind` is character, prop or location; `name` is what to call it, and a "
    "name you already have of that kind gains the picture instead of making "
    "a second element; `notes` says what it is in a few words."
)
_ELEMENT_URL = (
    "the https address of an image file the person gave you (jpg, png or "
    "webp, up to 15 MB -- the image itself, not the page it is on; never an "
    "address you guessed)"
)
_ELEMENT_RESULT = (
    "Returns the element with its photo `ref`s, as `elements` lists them. "
    "Nothing is drawn and no credits are spent: the picture is saved as it "
    "is and described in words for the studio."
)
# The listed servers have no `renders`, `import_file` or `images_for`, so
# their spending tool names only the ids they can hand out.
_LISTED_REFERENCE_IDS = (
    "References are ids, never URLs: a photo `ref` exactly as `elements` or "
    "`project` lists it, or `gen:<id>` (an image this tool made, or one "
    "`project` lists among a project's renders)."
)

DESCRIPTIONS = {
    "images_for": (
        "Search the web's open image sources for reference frames matching a "
        "description of the light and surfaces wanted (e.g. \"cold fluorescent "
        "on wet tile, overhead\"). Returns up to `limit` (default 6, maximum 12) "
        "candidates as ids with what each shows and its credit -- never URLs. "
        "Pass one as `candidate:<id>` to use it as a render reference. "
        "Read-only."
    ),
    "job": (
        "The status of a background job by id -- one this connector started "
        "(a render, an effect, an approval) or one you "
        "started in the studio: status, "
        "label, progress detail and the result or error when it finished. "
        "Jobs live in memory, so a server restart forgets them. Read-only."
    ),
    "cancel_job": (
        "Stop an image, clip, effect or sheet this connector started, by its "
        "`job_id`. What is given back depends on how far it got, and the reply "
        "says which: not yet sent to the renderer -- stopped, nothing charged; "
        "waiting in the renderer's queue -- removed, nothing charged; already "
        "rendering -- the renderer is asked to stop, and if it still finishes "
        "the result is kept and charged at the quoted price, otherwise nothing "
        "is charged; already finished or being saved -- too late, charged and "
        "kept. A sheet that is already being drawn finishes. Poll `job` to see "
        "how it ended (cancelled, or done). Only jobs this connector's render "
        "tools started can be cancelled here."
    ),
    "assemble_clips": (
        "Join clips from your Assets wall into ONE video, in the order given: "
        "`clips` are two to twenty `gen:<id>` videos from `renders` (the same id "
        "may repeat). `transition` is cut (the default) or crossfade "
        "(`crossfade_s`, 0.1-2 seconds, at most half the shortest clip). "
        "`music` is an optional bed under the clips' own sound -- an `asset:<id>` "
        "from `renders` with kind=audio (audio you uploaded in the editor), "
        "trimmed to the picture and lowered under the clips' sound. Clips of "
        "different shapes (9:16 beside 16:9) are refused unless `letterbox` is "
        "true, which fits them inside the first clip's frame with black bars. "
        f"{_PROJECT_FILING} Spends no credits: it runs on the studio's own "
        "server. Runs in the background: poll `job`; the result is a new "
        "`gen:<id>` on your Assets wall (usable as a source like any clip) and "
        "an editable cut in the studio's editor."
    ),
    "edit_clip": (
        "SPENDS CREDITS. Change something IN a clip by instruction (\"make the "
        "jacket red\", \"turn day to dusk\"), in two stages, each quoted and "
        "approved on its own. `source` is a clip (`gen:<id>` or an imported "
        "`asset:<id>`). Stage `frame` (the default) edits ONE frame of it as a "
        "still, for a few credits -- `at` is the second to take it from (0 = "
        "the first) -- and its quote also lists what the whole clip would cost "
        "on each model, or why a model cannot take this clip. Show the person "
        "that still and wait. Stage `video` then edits the whole clip and takes "
        "that still's `gen:<id>` as `frame`, with the SAME source and "
        "instruction; any other image is refused. `model` is kling-o1 (the "
        "default: clips of 3-10s and at least 720px, the approved frame steers "
        "it), kling-o1-pro, or flux-3 (far cheaper, mp4 under 15s, 720p out, "
        "follows the instruction only). `keep_audio` keeps the clip's sound "
        f"where the model can. {_APPROVAL} {_PROJECT_FILING} After each yes it "
        "runs in the background: poll `job`."
    ),
    "prepare_post": (
        "Draft a social post of one of your clips and get back a review link. "
        "Nothing is posted by this tool, and no tool here can post: the person "
        "opens `review_url` in the studio, sees the clip and the account it goes "
        "to, chooses who can see it, comments / Duet / Stitch and any "
        "commercial disclosure, and presses Post themselves. `source` is a video "
        "`gen:<id>` from `renders` or an imported `asset:<id>`. `platform` is "
        "tiktok (more platforms are coming). `caption` is a draft the person can "
        "edit on the page, up to 2200 characters. If `media_problem` is set the "
        "clip cannot be posted yet and the message says why; pass it on. Give "
        "the person the review link and stop -- do not tell them it was posted."
    ),
    "import_file": (
        "Bring an image or a clip from this computer into the studio, by its "
        "full path (e.g. ~/Downloads/can.jpg). Only files in your Downloads or "
        "Desktop folders, or the studio's own data folder, are read: images "
        "(jpg, png, webp) up to 100MB and clips (mp4, mov) up to 500MB, checked "
        "to be what they say they are. Returns an `asset:<id>`: an image is a "
        "reference for `generate_image`, `generate_video` (a start frame) or "
        "`apply_effect`; a clip is a source for a clip effect or a clip to "
        "`assemble_clips`. It also appears in the studio editor's media bin. "
        "Spends nothing."
    ),
    "elements": (
        "Your elements: the characters, props and places whose photos you "
        "uploaded in the studio or added with `add_element`, each with its "
        "photo refs. Pass a photo's "
        "`ref` wherever a tool asks for one of your photos (a scene's refs, "
        "or a reference for a render or an effect); refs from this list are "
        "the only ones taken. Read-only."
    ),
    "add_element": (
        "Add ONE picture to your elements -- the characters, props and places "
        f"a scene is held to. {_ELEMENT_ARGS} `source` is the picture: "
        f"{_ELEMENT_URL}, `gen:<id>` (an image from `renders` or a project) or "
        "`asset:<id>` (an image brought in with `import_file`). "
        f"{_ELEMENT_RESULT} A reference sheet is `element_sheet`, quoted on "
        "its own."
    ),
    "write_scene": (
        "Save a scene prompt you wrote as a scene, so it can be priced and "
        "rendered. `prompt` is the full scene (the studio's shape: an opening "
        "line naming the attached photos, a style block, timed beats like "
        "(0-4s) each one shot, diegetic sound, an avoid list); `seconds` is "
        "its total length (4-30); `refs` are photo refs from `elements` -- the "
        "first one anchors the render. A scene needs at least one before it "
        "can be priced or rendered: with none it is saved as a draft, and you "
        "add a photo (`add_element`) and call this again with its `scene_id` "
        "and `refs`. Timed "
        "beats become the shots. `title` names it (a few words). `project_id` "
        "(from `projects`) files it in that project; without one it is a "
        "scene on its own. Pass `scene_id` to rewrite a scene you saved "
        "before instead of making another. Returns the scene's id for `quote` "
        "and `approve`. Spends nothing."
    ),
    "quote": (
        "What rendering one of your scenes would cost, in credits: the "
        "keyframe stills still to draw and the clip (one render per timed "
        "shot), with a signed token per render that `approve` takes, plus "
        "your balance. `scene_id` is the id `write_scene` or `project` gave. "
        "Optional `provider`, `model`, `duration` (whole-scene only) and "
        "`frame` pick the renderer; the defaults are the studio's. "
        "Read-only; a quote is valid for one hour."
    ),
    "approve": (
        "SPENDS CREDITS. Approve a quoted render for one of your scenes "
        "(`scene_id`), only after the person has seen the price from `quote` "
        "and said yes: `what` is \"keyframes\" (draw the stills) or \"clip\" "
        "(render the shots); for a clip pass the `tokens` from `quote` and the "
        "same renderer choice. Credit is held before anything is submitted and "
        "released if the render fails. Starts a background job; poll it with "
        "`job`. Refused when the scene has no reference photos, the quote is "
        "stale, or the balance is short."
    ),
    "image_models": (
        "The image models `generate_image` can name: id, label, what each is "
        "good at, how many reference images it takes (`max_references`; 0 "
        "means it draws from the prompt alone) and its price per image in "
        "dollars at 1:1, plus the aspect ratios every model takes. The quote "
        "prices your exact aspect and references. Read-only; spends nothing."
    ),
    "video_models": (
        "The video models `generate_video` can name: id, the lengths in "
        "seconds and the resolutions each takes, and its price per second at "
        "each resolution. Read-only; spends nothing."
    ),
    "effects": (
        "The effects `apply_effect` can run -- image edits, one-click video "
        "templates on a still, named camera moves on a still, and clip "
        "finishing (upscale, smoother motion, added sound, re-framing to a new "
        "shape, background removal) -- with what each "
        "takes (an image or a clip, how many, whether it needs a prompt), its "
        "options and how it is priced. `category` narrows the list "
        "(image_edit, video_effect, camera, finish); long option lists are "
        "sampled, so pass `effect` for one effect's full lists. Read-only; "
        "spends nothing."
    ),
    "renders": (
        "Your recent renders, newest first, each as the `gen:<id>` that names "
        "it as a reference or an effect source, with its model and the start "
        "of its prompt. `kind` is image or video (omit for both); audio (the "
        "sound files you uploaded in the editor, as the `asset:<id>` that "
        "`assemble_clips` takes as music); or upload (every file you brought in "
        "with `import_file` or the editor, as `asset:<id>`). Returns at most "
        "`limit` rows (default 20, maximum 100). Read-only."
    ),
    "prompt_craft": (
        "The studio's own prompt-writing guides, for you to apply: nothing is "
        "written for you. `step` is refine (polish a video prompt for one "
        "model, with the studio's technique notes -- pass `model` from "
        "`video_models` or `image_models`, or a `tool` name), enhance (tighten "
        "a prompt without losing what it locks), still (a first-frame image "
        "prompt from a video shot) or beats (the moments a camera move passes "
        "through; `count` of them). Returns the instruction with your prompt "
        "filled in. Read-only."
    ),
    "generate_image": (
        "SPENDS CREDITS. Render one image from a prompt on a model you choose "
        f"(`image_models`; omit `model` for the default) and file it on your "
        f"Assets wall. {_APPROVAL} An unknown model, an aspect ratio it does not "
        "take or more references than it accepts is refused, never swapped. "
        f"{_REFERENCE_IDS} {_PROJECT_FILING} After the yes it runs in the "
        "background: poll `job`; the result carries `media_url` and `asset_id` "
        "(`gen:<asset_id>` names it from then on)."
    ),
    "generate_video": (
        "SPENDS CREDITS. Render one clip on a video model you choose "
        "(`video_models`; omit `model` for the default) and file it on your "
        f"Assets wall. {_APPROVAL} `seconds` and `frame` (the resolution) must "
        "be ones the model takes, or the call is refused with the legal set. "
        "`reference` is ONE start frame for image-to-video, by id (same ids as "
        "a render reference); omit it for text-to-video. "
        f"{_REFERENCE_IDS} {_PROJECT_FILING} After the yes it runs in the "
        "background: poll `job`; the result carries `media_url` and `asset_id`."
    ),
    "apply_effect": (
        "SPENDS CREDITS. Apply one effect from `effects` to sources named by "
        "id: for an image effect, images by the reference ids below; for a "
        "clip effect, a video `gen:<id>` from `renders` or an `asset:<id>` clip "
        "you imported (it is measured before it is priced). `options` takes the names and values `effects` lists, "
        "e.g. {\"effect_scene\": \"bullet_time_360\"}; anything else is refused "
        "with the legal set. `prompt` is required, optional or refused per "
        f"effect. {_APPROVAL} {_REFERENCE_IDS} {_PROJECT_FILING} After the yes "
        "it runs in the background: poll `job`; the result carries `media_url` "
        "and `asset_id`."
    ),
    "element_sheet": (
        "SPENDS CREDITS. Draw (or redraw) the reference sheet for one of your "
        "elements -- `kind` (character, prop or location) and its `name` as "
        "`elements` lists it -- from the element's real photos: front, "
        "three-quarter, profile, back and a close-up for a character, a "
        "turnaround for a prop, a set of plates for a location, with the face, "
        "wardrobe or object kept in every panel. The sheet is saved on the "
        "element in the studio (Elements) and listed after its real photos. A "
        "redraw replaces the current sheet; the quote says when it would. The "
        f"element needs at least one photo. {_APPROVAL} After the yes it runs in "
        "the background: poll `job`; the result carries the sheet's `ref` and "
        "`media_url`."
    ),
    "projects": (
        "Your projects, most recently touched first: id, name, the start of "
        "its brief, whether it carries a look, and how many scenes it holds "
        "(and how many are rendered). `include_archived` adds the "
        f"archived ones. {_CAP}. Read-only."
    ),
    "project": (
        "One project in full, by its id from `projects`: its brief and look, "
        "what it learned from the scenes rendered and edited in it, its scenes (status, "
        "the start of each scene prompt, its still or clip), every reference "
        "image those scenes used (each with its `ref`, what it shows and the "
        "page it came from; a render or an effect takes a `ref` as a "
        "reference), the renders made for it (`gen:<id>`), and the latest "
        "turns of its chat. Up to 50 scenes and 60 references, newest scenes "
        "first; `chat_turns` sets how many turns (default 12, maximum 40); "
        "page further back with `project_chat`. Read-only."
    ),
    "project_chat": (
        "A project's chat history: each turn's role, words and time, oldest "
        "first within the page. Returns the newest `limit` turns (default 40, "
        "maximum 200, and fewer when the turns are long); pass `before` (the "
        "oldest turn id you already hold) to page further back; `has_more` "
        "says whether older turns exist. Read-only."
    ),
    "create_project": (
        "Start a new project: a name, an optional brief (who it is for, what "
        "it must always have and never show) and an optional look (the style "
        "every prompt in it is held to). It appears on your projects board in "
        "the studio. `save_chat` keeps a conversation with it, and a tool that "
        "takes `project_id` (a render, an effect) files its result under it. "
        "Spends nothing."
    ),
    "save_chat": (
        "Save turns of this conversation into one of your projects' chat "
        "history (`project_id` from `projects`), so they are there when the "
        "project is reopened -- here, or in the studio, where the project's "
        "assistant picks the conversation up. `turns` are the person's "
        "messages and your replies, in order, each {role: user or assistant, "
        "content}; up to 100 turns and 200,000 characters per call. Turns the "
        "history already ends with are "
        "skipped, so re-sending the conversation from its start saves only "
        "what is new. Save when the person wants this conversation kept with "
        "the project. Spends nothing."
    ),
}

DESCRIPTIONS["scene"] = (
    "One of your scenes by its `scene_id` (from `write_scene` or `project`): "
    "its title, project, the scene prompt and timed shots, how many reference "
    "photos it renders against, where it stands, the clips rendered so far and "
    "a link to open it in the studio. Use it to check whether a render has "
    "landed. Read-only."
)

# The listed servers' wording where it differs from the studio's: no
# `save_chat` there (OpenAI refuses a tool that takes the conversation;
# Anthropic asks for no conversation data a tool does not need), and no
# render or effect tool for a `ref` to go to.
LISTED_DESCRIPTIONS = {
    "project": (
        "One project in full, by its id from `projects`: its brief and look, "
        "what it learned from the scenes rendered and edited in it, its scenes "
        "(status, the start of each scene prompt, its still or clip), the "
        "reference images those scenes used, the renders made for it, and the "
        "latest turns of its chat in the studio. Up to 50 scenes and 60 "
        "references, newest scenes first; `chat_turns` sets how many turns "
        "(default 12, maximum 40); page further back with `project_chat`. "
        "Read-only."
    ),
    "create_project": (
        "Start a new project: a name, an optional brief (who it is for, what it "
        "must always have and never show) and an optional look (the style every "
        "scene in it is held to). It appears on your projects board in the "
        "studio, and `write_scene` with its `project_id` files a scene under "
        "it. Spends nothing."
    ),
    "job": (
        "The status of a background job by id -- a render this connector "
        "started, or one you started in the studio: status, label, progress "
        "detail and the result or error when it finished. Jobs live in memory, "
        "so a server restart forgets them; a render still lands on its scene, "
        "so read `scene` if a job is gone. Read-only."
    ),
    "add_element": (
        "Add ONE picture to your elements -- the characters, props and places "
        f"a scene is held to. {_ELEMENT_ARGS} `source` is the picture: "
        f"{_ELEMENT_URL}, or `gen:<id>` -- an image `generate_image` made "
        f"here, or one `project` lists among a project's renders. "
        f"{_ELEMENT_RESULT}"
    ),
    "image_models": (
        "The image models `generate_image` can name: id, label, what each is "
        "good at, how many reference images it takes (`max_references`; 0 "
        "means it draws from the prompt alone) and its price per image in "
        "credits at 1:1, plus the aspect ratios every model takes. The quote "
        "prices your exact aspect and references. Read-only; spends nothing."
    ),
    "generate_image": (
        "SPENDS CREDITS. Render one image from a prompt on a model you choose "
        "(`image_models`; omit `model` for the default) and file it on your "
        f"Assets wall in the studio. {_APPROVAL} An unknown model, an aspect "
        "ratio it does not take or more references than it accepts is "
        f"refused, never swapped. {_LISTED_REFERENCE_IDS} {_PROJECT_FILING} "
        "After the yes it runs in the background: poll `job`; the result "
        "carries `media_url` and `asset_id`, and `add_element` takes "
        "`gen:<asset_id>` as its `source` to keep the image as a reference."
    ),
}

# The Claude listing's wording where it differs again: nothing there renders,
# so no description may point at `approve`, `job` or `generate_image`.
CLAUDE_DESCRIPTIONS = {
    "add_element": (
        "Add ONE picture to your elements -- the characters, props and places "
        f"a scene is held to. {_ELEMENT_ARGS} `source` is the picture: "
        f"{_ELEMENT_URL}, or `gen:<id>`, an image `project` lists among a "
        f"project's renders. {_ELEMENT_RESULT}"
    ),
    "write_scene": (
        "Save a scene prompt you wrote with the person as a scene, ready to "
        "render in the studio. `prompt` is the full scene (an opening line "
        "naming the attached photos, a style block, timed beats like (0-4s) "
        "each one shot, diegetic sound, an avoid list); `seconds` is its total "
        "length (4-30); `refs` are photo refs from `elements` -- the first one "
        "anchors the render. A scene needs at least one before it can be "
        "priced or rendered: with none it is saved as a draft, and you add a "
        "photo (`add_element`) and call this again with its `scene_id` and "
        "`refs`. Timed beats become "
        "the shots. `title` names it (a few words). `project_id` (from "
        "`projects`) files it in that project. Pass `scene_id` to rewrite a "
        "scene you saved before. Returns the scene's id and its studio link. "
        "Spends nothing."
    ),
    "quote": (
        "What rendering one of your scenes (`scene_id`, from `write_scene` or "
        "`project`) would cost in the studio, in credits -- the keyframe stills "
        "still to draw and the clip, one render per timed shot -- beside your "
        "balance, and `approve_url`, the scene's page in the studio where the "
        "person approves the render. Nothing here renders or spends. Optional "
        "`provider`, `model`, `duration` (whole-scene only) and `frame` price a "
        "different renderer. Read-only."
    ),
}

# What each tool DOES, for Claude's permission model: `read` (no change),
# `destructive` (cannot be undone -- here, spends money or crawls and
# writes), `idempotent` (the same call again changes nothing more),
# `open_world` (reaches beyond this server: the web, a provider).
HINTS = {
    "images_for":        {"read": True,  "destructive": False, "idempotent": True,  "open_world": True},
    "job":               {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "cancel_job":        {"read": False, "destructive": False, "idempotent": True,  "open_world": True},
    "assemble_clips":    {"read": False, "destructive": False, "idempotent": False, "open_world": False},
    "import_file":       {"read": False, "destructive": False, "idempotent": False, "open_world": False},
    "prepare_post":      {"read": False, "destructive": False, "idempotent": False, "open_world": False},
    "edit_clip":         {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "elements":          {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    # open world: `source` may be an https address, fetched from here
    "add_element":       {"read": False, "destructive": False, "idempotent": False, "open_world": True},
    # destructive: `scene_id` REPLACES a scene (OpenAI counts an overwrite
    # as destructive, undo or not)
    "write_scene":       {"read": False, "destructive": True,  "idempotent": False, "open_world": False},
    "quote":             {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "approve":           {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "image_models":      {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "video_models":      {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "effects":           {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "renders":           {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "prompt_craft":      {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "generate_image":    {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "generate_video":    {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "apply_effect":      {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "element_sheet":     {"read": False, "destructive": True,  "idempotent": False, "open_world": True},
    "projects":          {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "project":           {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "project_chat":      {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
    "create_project":    {"read": False, "destructive": False, "idempotent": False, "open_world": False},
    "save_chat":         {"read": False, "destructive": False, "idempotent": True,  "open_world": False},
    "scene":             {"read": True,  "destructive": False, "idempotent": True,  "open_world": False},
}

# THE LISTED SET (2026-10-07, Mike's call; cut to this on 2026-10-11). What
# a signed-in stranger is offered through the HTTP mount: their projects
# and their chat, their elements, and the path that writes a scene, prices
# it and renders it on their yes. Claude does the ideation in the chat, so
# nothing here calls a paid model until `approve`. `build_server(listed=True)`
# registers exactly these.
#
# The idea-board tools that led this list until 2026-10-11 -- `board`,
# `idea`, `search`, `capture`, `pick`, `shoot`, `archive`, `stats` -- are
# gone with the board (docs/tasks/task-higgsfield-shape.md): `write_scene`
# makes the scene itself now, in a project or on its own, and `approve`
# asks for no pick.
#
# `save_chat` left it on 2026-10-11 (OpenAI refuses a tool that takes the
# conversation) and `scene` joined it: the status a render leaves behind,
# which outlives the in-memory job.
#
# THREE MORE THE SAME DAY (Mike's calls, docs/tasks/task-connector-elements.md).
# A new person had no elements, `write_scene` took refs only from elements,
# and nothing here could add one: the connector could make nothing. So
# `add_element` files ONE picture as an element -- on both listings, since
# it draws nothing -- and `image_models` / `generate_image` join THIS
# listing only: a still, behind the studio surface's own signed single-use
# quote (`approval_gate`). In `build_server`'s registration order.
LISTED_TOOLS = ("projects", "project", "project_chat", "create_project",
                "elements", "add_element", "image_models", "generate_image",
                "write_scene", "scene", "quote", "approve", "job")
# The Claude directory's listing: the same minus what renders or draws (see
# CLAUDE_INSTRUCTIONS); with nothing started here there is no job to poll.
CLAUDE_LISTED_TOOLS = ("projects", "project", "project_chat", "create_project",
                       "elements", "add_element", "write_scene", "scene", "quote")
LISTINGS = ("render", "claude")

# THE STUDIO SURFACE (2026-10-07, Mike's call). What `python -m
# src.mcp_server` serves -- what Claude Desktop launches, and what the
# operator's static key reaches over HTTP: work with Claude on images,
# video and effects. The three spending tools are
# always on here, because they are the point of it; each is quoted first
# and runs only after the person's yes in chat (`approval_gate`), which is
# the gate -- not the engine flag. `build_server(surface="studio")`.
STUDIO_TOOLS = ("projects", "project", "project_chat", "create_project", "save_chat",
                "elements", "add_element", "images_for", "image_models", "video_models",
                "effects", "renders", "prompt_craft", "generate_image",
                "generate_video", "apply_effect", "element_sheet", "job",
                "cancel_job", "assemble_clips", "import_file", "edit_clip",
                "prepare_post")
SURFACE_ENV = "ZEROPAGE_MCP_SURFACE"
# One surface since 2026-10-11: "board" went with the idea board. The name
# and the tuple stay so `--surface` and the environment variable still
# parse -- anything that is not "studio" is read as "studio".
SURFACES = ("studio",)
STUDIO_INSTRUCTIONS = (
    "Your studio: make images and video, apply effects and draw element "
    "reference sheets with the studio's models, on the studio's credits. "
    "EVERY image, clip, effect and sheet is two calls: the first (no quote_token) "
    "spends nothing and returns a quote -- show the person what will run, its "
    "price in credits and their balance, and WAIT for a yes; only then call "
    "again with the same arguments plus the quote's quote_token, which works "
    "once. Never approve on the person's behalf, and stop when a call is "
    "refused for credits. `add_element` files a picture (an image address, a "
    "render or an import) as an element; it draws nothing and is free. "
    "Work can be filed into a project: `projects` lists them, "
    "`project` reopens one (its brief, look, scenes, the reference images it "
    "used and its chat), `create_project` starts one, `project_id` on a "
    "render files it there, and `save_chat` keeps this conversation with the "
    "project when the person wants it kept. References and sources are ids (gen:<id> from "
    "renders, a photo ref from elements or a project, candidate:<id> from "
    "images_for), never URLs. "
    "Renders run in the background: poll `job`. prompt_craft holds the "
    "studio's prompt-writing guides."
)

# Words a directory user does not have. The test screens every published
# description and title for them (case-insensitive).
INTERNAL_WORDS = (
    "nightly", "the night", "Mike", "Michael", "Higgsfield", "Runway", "venv",
    "/ui", "Dev Studio", "LangGraph", "Nano", "Midjourney", "Gemini",
    "antihero", "zeropage", "on the machine", "src.", "hold_queue",
)


class Refused(Exception):
    """A deliberate no, not a failure.

    Separate from ValueError because the two mean different things to a
    caller -- a ValueError says "you asked wrongly, ask again", a
    Refused says "this surface will not do that at all, stop asking" --
    and separate from a bare RuntimeError because the translation layer
    in build_server has to be able to tell a refusal it should relay
    from a crash it must not dress up as one.
    """


# --- shaping ---------------------------------------------------------------

def _status_of(concept: dict) -> str:
    """The one word a scene carries, off its own row: where it stands with
    being made. (Until 2026-10-11 this was the board's word -- open,
    picked, parked, archived, shot.)"""
    shot = (concept.get("shots") or [{}])[0] or {}
    if concept.get("archived"):
        return "removed"
    if shot.get("media_url"):
        return "rendered"
    if concept.get("shot_done"):
        return "made"
    if concept.get("picked"):
        # the approve stamps this before it spends: a render was started
        # and no clip has landed (it is running, or it failed)
        return "render started"
    return "written" if (shot.get("prompt") or "").strip() else "idea"


def _card(concept: dict) -> dict[str, Any]:
    """One scene as a list draws it: enough to recognise, not enough to
    read the prompt."""
    shot = (concept.get("shots") or [{}])[0]
    return {
        "id": concept["id"],
        "brand": concept["brand"],
        "title": concept["title"],
        "summary": preprod.concept_summary(
            concept.get("card_line") or "",
            concept.get("logline") or "",
            shot.get("prompt") or "",
        ),
        "status": _status_of(concept),
        "is_scene": concept.get("is_scene", False),
        "spark": concept.get("spark") or "",
        "refs": len(concept.get("refs") or []),
        "warnings": concept.get("warnings") or [],
        "created_at": concept["created_at"],
    }


# What a null `judge_overall` means, said on the card rather than left
# to be inferred. Two doors write concepts and only one of them scores
# anything -- and neither writes THAT column.
ORIGIN_NOTE = {
    "graph": "ran through the LangGraph: `gate` is its verdict",
    "studio": ("written in the studio or in chat -- never scored; a null judge "
               "means unscored, not scored badly"),
    "capture": "an idea only -- no scene prompt yet, nothing to score",
}


def _gate(concept: dict, dsn, account_id: Optional[int]) -> dict[str, Any]:
    """The verdict the graph actually reached on this concept, read from
    where the graph actually writes it.

    `judge_overall` on the row is the Dev Studio's TASTE judge -- a
    manual per-click tool that no automated path has ever called -- so
    reading it as "the graph scored this" is wrong in both directions:
    #167 read 7.0 because somebody clicked, and every graph row reads
    null however it scored. The prompt gate logs to `prompt_scores` by
    run_id and the run's outcome is the hold row's reason, and until
    2026-09-03 neither reached this surface, so an agent asked why #173
    was held (5/10, "too many sequential character actions") had
    nothing to say. Origin is derived from the hold row: a concept the
    graph wrote always has one (`_park` runs on every terminal edge),
    and one it did not write never does.
    """
    hold = autonomy.hold_for_concept(concept["id"], dsn=dsn, account_id=account_id)
    if hold is None:
        origin = "capture" if not concept.get("shots") else "studio"
        return {"origin": origin, "note": ORIGIN_NOTE[origin], "gate": None}
    run_id = (hold.get("payload") or {}).get("run_id") if isinstance(
        hold.get("payload"), dict) else None
    scores = autonomy.prompt_scores_for_run(run_id, dsn=dsn)
    latest = scores[-1] if scores else None
    return {
        "origin": "graph",
        "note": ORIGIN_NOTE["graph"],
        "gate": {
            "hold_id": hold["id"],
            "status": hold.get("status") or "held",
            "outcome": hold.get("reason") or "",
            "run_id": run_id or "",
            "score": latest["score"] if latest else None,
            "passed": latest["passed"] if latest else None,
            "reason": (latest.get("reason") or "") if latest else "",
            "scores": [{"score": x["score"], "passed": x["passed"],
                        "reason": x.get("reason") or ""} for x in scores],
        },
    }


def _check(value: str, allowed, label: str) -> str:
    if value not in allowed:
        raise ValueError(f"{label} must be one of {list(allowed)}, got {value!r}")
    return value


def _truncation(rows: list, limit: int, advice: str) -> dict[str, Any]:
    """The cap, said out loud (2026-10-07). A list that stops at `limit`
    with no word looks complete, and an agent that reads 25 rows as the
    whole list decides on a third of it. The scan reads ONE row past the
    cap so `truncated` is a fact, not a guess."""
    if len(rows) <= limit:
        return {"truncated": False}
    return {"truncated": True,
            "note": f"more than {limit} matched; {advice}"}


# --- who is calling ----------------------------------------------------------

PRICING_URL_ENV = "ZEROPAGE_PRICING_URL"
DEFAULT_PRICING_URL = "https://zeropage.studio/pricing"


def pricing_url() -> str:
    """Where an out-of-credits caller is sent (2026-10-11). Inside Claude the
    refusal is the upgrade prompt, so it carries a link rather than "top up
    in the studio". ZEROPAGE_PRICING_URL overrides it for another domain."""
    return (os.environ.get(PRICING_URL_ENV) or "").strip() or DEFAULT_PRICING_URL


CALLER_ACCOUNT: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "zeropage_mcp_caller_account", default=None)
"""The account a SIGNED-IN caller is acting as, for the length of one
HTTP request. Set by app/mcp_mount.py's guard once a Supabase access
token has been verified, and unset for every other caller.

It lives here, in src/, rather than in the app layer for the reason the
whole injection pattern exists: `src/` never imports `app/`, and
`_account` is the one place that decides whose rows a tool reads, so
the value has to be readable from here. Verified empirically rather than
assumed -- the streamable-HTTP transport in stateless mode runs a tool
body in a task that inherits the request's context, so a value set in
the ASGI wrapper reaches the tool. A stateful session would not
guarantee that, which is one more reason the mount is stateless."""


def _account(account_id: Optional[int], dsn) -> Optional[int]:
    """Which account an MCP call acts as.

    Three callers, in order of precedence:

    - An EXPLICIT `account_id`, which is how the Guide opens a server
      per signed-in request.
    - A caller the transport authenticated (`CALLER_ACCOUNT`) -- a person
      who signed in through the OAuth door. Their own account, never the
      operator's: the bootstrap fallback below is exactly the bug that
      would hand a stranger the operator's work, so it must not be
      reachable once somebody has identified themselves.
    - Nobody named, which is the static-token door: an agent on the
      operator's own machine holding `ZEROPAGE_MCP_TOKEN`, or a CLI. It
      acts as the bootstrap account -- the same call the CLIs make, for
      the same reason. After the tenancy backfill, acting as nobody means
      reading an empty database and reporting it as empty.
    """
    if account_id is not None:
        return account_id
    caller = CALLER_ACCOUNT.get()
    if caller is not None:
        return caller
    return accounts.resolve_account(dsn=dsn)


# --- Claude writes the scene, the studio renders it (2026-10-07) ------------
#
# Mike's call: the listed connector uses Claude for the ideation -- no
# Gemini Create, no research pass -- and the MCP for the render. So a
# scene prompt written in the chat is SAVED here, against the person's
# own element photographs (the reference gate's rule, unchanged), priced
# by the same pricing the studio's Render card shows, and approved through
# the same body that card's button posts to.
#
# Since 2026-10-11 (no idea board) `write_scene` MAKES the scene -- in a
# project, or on its own -- where it used to write onto an idea somebody
# had captured and picked; and nothing has to be picked before `approve`.

MIN_SCENE_WORDS = 15
WhatToApprove = Literal["keyframes", "clip"]


def _catalogue(dsn, account_id) -> list[dict]:
    """The account's elements with the photos that are ITS OWN.

    `asset_shelf.catalogue` reads the element folders on disk first, and
    those are named by slug alone -- one `characters/me/` for every
    account on the machine. Where the bucket is the per-account store
    (asset_shelf.bucket_is_store), a connector's caller is listed the
    photos under their own keys instead: a stranger who names a character
    "Me" must never be handed the ref of somebody else's. Every reader on
    this surface goes through here -- `elements`, the ref gate, a sheet,
    `add_element`'s answer -- so they cannot disagree about whose photo
    is whose. Elsewhere (one studio on one machine, no bucket) the folder
    is the store and the catalogue is returned as it is."""
    from . import asset_shelf
    items = asset_shelf.catalogue(dsn, account_id=account_id)
    if not asset_shelf.bucket_is_store(account_id):
        return items
    return [{**item, "photos": asset_shelf.r2_photo_urls(
                item["category"], asset_shelf.slugify(item["name"]), account_id)}
            for item in items]


def list_elements(dsn: Optional[str] = None,
                  account_id: Optional[int] = None) -> dict[str, Any]:
    """The account's characters, props and places with their photo refs --
    the only strings `write_scene` accepts as references."""
    from . import asset_shelf
    account_id = _account(account_id, dsn)
    items = _catalogue(dsn, account_id)
    out = [{"kind": item["category"], "name": item["name"],
            "description": (item.get("text") or "")[:300],
            "photos": [{"ref": asset_shelf.storable_ref(url), "label": _photo_label(url)}
                       for url in item.get("photos") or []]}
           for item in items]
    return {"count": len(out), "elements": out,
            "note": ("" if out else
                     "no elements yet -- `add_element` adds one from a picture "
                     "(an https image address), or upload photos of your "
                     "characters, products or places in the studio (Elements); a "
                     "scene renders only against photographs you attached")}


def _photo_label(url: str) -> str:
    from . import asset_shelf
    parsed = asset_shelf.parse_ref(url) or {}
    return parsed.get("filename") or url.rsplit("/", 1)[-1]


def _allowed_refs(dsn, account_id) -> dict[str, str]:
    """storable ref -> the catalogue's own URL string, for every photo the
    account owns. The gate on `write_scene`: a ref is accepted only when
    `elements` could have issued it, which refuses a typed URL, another
    account's photo and a guess alike -- the candidate_id rule."""
    from . import asset_shelf
    allowed: dict[str, str] = {}
    for item in _catalogue(dsn, account_id):
        for url in item.get("photos") or []:
            allowed[asset_shelf.storable_ref(url)] = url
            allowed[url] = url
    return allowed


def _check_prompt(prompt: str) -> str:
    text = " ".join((prompt or "").split())
    if len(text.split()) < MIN_SCENE_WORDS:
        raise ValueError(f"the scene prompt is too short ({len(text.split())} words; "
                         f"at least {MIN_SCENE_WORDS}) -- write the whole scene")
    if "{" in text and "}" in text:
        raise ValueError("the scene prompt still carries a {placeholder} -- fill it in")
    return (prompt or "").strip()


MAX_SCENE_TITLE = 120


def _brand_for(account_id: Optional[int], dsn) -> str:
    """The label a scene made here is filed under: the account's own slug
    when it is one of the two brand labels, else the default. A label
    only -- nothing reads a look or a rule off it (2026-10-04)."""
    slug = accounts.slug_of(account_id, dsn=dsn) if account_id is not None else None
    return slug if slug in preprod.BRANDS else DEFAULT_BRAND


def _scene_title(title: str, prompt: str) -> str:
    """The name a scene is listed under: the one given, else the first few
    words of the prompt -- a scene row needs one."""
    given = " ".join((title or "").split())
    if given:
        return given[:MAX_SCENE_TITLE]
    words = " ".join((prompt or "").split()).split(" ")[:7]
    return (" ".join(words).rstrip(".,;:") or "Untitled scene")[:MAX_SCENE_TITLE]


STUDIO_URL_ENV = "STUDIO_URL"
DEFAULT_STUDIO_URL = "https://zeropage.studio"


def studio_link(scene_id: int) -> str:
    """The scene's page in the studio (/studio/scene/<id>, which opens the
    project workspace when the scene is filed), where its Render card is the
    priced approve. STUDIO_URL is the studio's public origin -- app/auth
    reads the same variable; src/ cannot import it."""
    base = (os.environ.get(STUDIO_URL_ENV) or "").strip().rstrip("/") or DEFAULT_STUDIO_URL
    return f"{base}/studio/scene/{int(scene_id)}"


# What a card carries that a directory user was never shown: the label a
# scene is filed under here, the direction a crawl banked it from, and a
# flag that is always true for a scene written in chat.
OPERATOR_CARD_KEYS = ("brand", "spark", "is_scene")


def _scene_view(concept: dict, account_id: Optional[int]) -> dict[str, Any]:
    """A saved scene as `write_scene` and `scene` answer with it: the card,
    the prompt and its shots, the clips rendered so far, and the studio
    link. Only what a person needs to follow their scene -- no judge
    scores, no operator vocabulary (OpenAI's response-minimisation rule).

    The card is `_card`'s minus OPERATOR_CARD_KEYS: spread whole, it put
    `brand` and `spark` on every answer this docstring says has neither."""
    shot = (concept.get("shots") or [{}])[0] or {}
    parts = (shot.get("timeline") or {}).get("parts") or []
    clips = [p["media_url"] for p in parts if p.get("media_url")] or (
        [shot["media_url"]] if shot.get("media_url") else [])
    card = {k: v for k, v in _card(concept).items() if k not in OPERATOR_CARD_KEYS}
    return {**card,
            "scene_id": concept["id"],
            "project_id": concept.get("project_id"),
            "prompt": shot.get("prompt") or "",
            "seconds": shot.get("seconds"),
            "shots": [{"n": p.get("n"), "start": p.get("start"), "end": p.get("end"),
                       "seconds": p.get("seconds"), "text": p.get("text") or "",
                       "clip": p.get("media_url") or None}
                      for p in parts],
            "shots_written": len(parts) or 1,
            "reference_photos": len(shot.get("refs") or []),
            "keyframe": shot.get("reference_image") or None,
            "clips": clips,
            "rendered": bool(shot.get("media_url")),
            "studio_url": studio_link(concept["id"])}


def read_scene(scene_id: int, dsn: Optional[str] = None,
               account_id: Optional[int] = None) -> dict[str, Any]:
    """One of the caller's scenes -- the `scene` tool (2026-10-11): the
    status a render leaves behind, which outlives the in-memory job."""
    account_id = _account(account_id, dsn)
    concept = preprod.get_concept(int(scene_id), dsn=dsn, account_id=account_id)
    if concept is None:
        raise ValueError(f"no scene {scene_id}")
    out = _scene_view(concept, account_id)
    shot = (concept.get("shots") or [None])[0]
    if shot and (shot.get("prompt") or "").strip() and preprod.reference_gate(concept):
        out.update(_draft(concept["id"]))     # written, with no photo to render against
    return out


def write_scene(prompt: str, seconds: int = 10, refs=None, title: str = "",
                project_id: Optional[int] = None, scene_id: Optional[int] = None,
                dsn: Optional[str] = None,
                account_id: Optional[int] = None) -> dict[str, Any]:
    """Save a scene written in the chat: a NEW scene (in `project_id`, or
    on its own), or -- with `scene_id` -- a rewrite of one saved before.

    The shot is the one `shootgen.generate_scene_concept` writes (n=1,
    AI, the fal default tool, the prompt, its seconds, its refs), so
    every reader -- the workspace's list, the Render card, pricing, the
    render loop -- treats it as any other scene. Timed windows in the
    prompt become the timeline through `timeline.fallback`, the split
    with no model in it: the chat already wrote each window as one shot,
    and a planner call here would spend the money this door exists to
    save. `source` is stamped so `timeline.ensure` reads it as current and
    never re-plans.

    A SCENE WITH NO PHOTOGRAPHS IS SAVED AS A DRAFT (2026-10-11, Mike's
    call, docs/tasks/task-connector-elements.md D2). Until then this
    refused it, which threw the person's words away at the moment a new
    account -- no elements yet -- wrote its first scene. Now the row is
    made and the answer says plainly that it cannot be priced or rendered
    until it carries a photo (`needs_reference`, `note`, `next`). ONLY the
    write loosened: `quote` still refuses an ungrounded scene, and the
    approve bodies still ask `preprod.reference_gate` themselves, so
    nothing renders against no photograph from any door.

    Everything else that can refuse -- the prompt, a ref `elements` did
    not issue, a project or a scene that is not the caller's -- refuses
    before a row is made.

    UNTIL 2026-10-11 this took an `idea_id` and wrote onto an idea
    captured on the board; the board is gone
    (docs/tasks/task-higgsfield-shape.md), so it makes the row itself.
    """
    from . import projects, shootgen, timeline
    account_id = _account(account_id, dsn)
    prompt = _check_prompt(prompt)
    seconds = timeline.scene_seconds(seconds)

    existing = None
    if scene_id is not None:
        existing = preprod.get_concept(int(scene_id), dsn=dsn, account_id=account_id)
        if existing is None:
            raise ValueError(f"no scene {scene_id}")
    project = _project_arg(project_id)
    if project is not None:
        _project_or_refuse(project, dsn, account_id)

    wanted = [str(r).strip() for r in (refs or []) if str(r).strip()]
    allowed = _allowed_refs(dsn, account_id)
    picked: list[str] = []
    for ref in wanted:
        if ref not in allowed:
            raise ValueError(
                f"ref {ref!r} is not one of your elements' photos -- call "
                "`elements` and pass a `ref` from its list (URLs and guesses are refused)")
        stored = allowed[ref]
        if stored not in picked:
            picked.append(stored)

    name = _scene_title(title, prompt) if (title or existing is None) else existing["title"]
    shot: dict[str, Any] = {
        "n": 1, "type": "BROLL", "source": "AI",
        "tool": shootgen.DEFAULT_SCENE_TOOL,
        "desc": name,
        "prompt": prompt, "seconds": seconds, "refs": picked,
        "written_by": "chat",
    }
    # `refs` set explicitly: get_concept surfaces the OLD shot's refs at the
    # top level, and the gate reads that first (found on 2026-10-08, when
    # every write onto a row with no shot yet was refused as ungrounded
    # whatever photos were passed).
    ungrounded = preprod.reference_gate({**(existing or {}), "refs": picked, "shots": [shot]})

    windows = timeline.parse_windows(prompt)
    if len(windows) >= 2:
        split = timeline.fallback(prompt, windows, picked)
        total = sum(w["seconds"] for w in windows)
        shot["timeline"] = {"seconds": total, "planner": "split", "brain": None,
                            "source": timeline.source_hash(prompt, picked),
                            "continuity": split["continuity"], "parts": split["parts"]}
        shot["seconds"] = total

    note = ""
    if existing is None:
        sid = preprod.save_concept(
            {"title": name, "hook": "", "logline": "", "shots": [shot],
             "duration": f"{shot['seconds']}s"},
            brand=_brand_for(account_id, dsn), dsn=dsn, account_id=account_id)
    else:
        sid = existing["id"]
        previous = (existing.get("shots") or [{}])[0] or {}
        preprod.update_concept_shots(
            sid, {"shots": [shot], "duration": f"{shot['seconds']}s"},
            warnings=[], dsn=dsn, account_id=account_id)
        if previous.get("media_url") or previous.get("reference_image"):
            note = ("the scene's earlier version had renders attached; they stay on "
                    "the Assets wall but are no longer this scene's")
    if project is not None:
        projects.tag_concepts([sid], project, dsn, account_id=account_id)

    out = _scene_view(preprod.get_concept(sid, dsn=dsn, account_id=account_id), account_id)
    if note:
        out["note"] = note
    out["next"] = (f"`quote` scene_id={sid} for the price; show the person, and only "
                   "on their yes call `approve`")
    if ungrounded:
        out.update(_draft(sid))
        if note:
            out["note"] = f"{out['note']}. Also: {note}"
    return out


def _draft(scene_id: int) -> dict[str, Any]:
    """What a scene saved with no reference photos says about itself, on
    `write_scene` and on `scene`: it is kept, and it cannot be priced or
    rendered until it carries one."""
    return {
        "needs_reference": True,
        "note": ("saved as a draft: it has no reference photos, and the studio "
                 "renders only against photographs you attached -- it cannot be "
                 "priced or rendered yet"),
        "next": ("`add_element` to add a photo (or the person uploads one in the "
                 f"studio), then `write_scene` again with scene_id={int(scene_id)}, "
                 "the same prompt and `refs`; `quote` after that"),
    }


def _listed_clip(clip: Optional[dict], listing: str) -> Optional[dict]:
    """The clip quote as a listed server shows it: credits, never dollars
    (the studio prices in credits everywhere), and on the Claude listing no
    signed tokens -- there is no `approve` there for them to go to."""
    if clip is None:
        return None
    out = {k: v for k, v in clip.items() if k != "estimate_usd"}
    renders = [{k: v for k, v in r.items() if k != "estimate_usd"}
               for r in clip.get("renders") or []]
    if listing == "claude":
        out.pop("signed", None)
        renders = [{k: v for k, v in r.items() if k != "token"} for r in renders]
    out["renders"] = renders
    return out


def quote_render(scene_id: int, provider: Optional[str] = None, model: Optional[str] = None,
                 duration: Optional[int] = None, frame: Optional[str] = None,
                 dsn: Optional[str] = None,
                 account_id: Optional[int] = None,
                 listing: Optional[str] = None) -> dict[str, Any]:
    """The price of rendering a scene, as the studio's Render card prints
    it: pricing.display for the clip (one render per timed shot, a token
    per render when the server can sign) and scene_chain.keyframe_quote for
    the stills, beside the balance. Nothing is held or spent."""
    from . import ledger, pricing, scene_chain
    account_id = _account(account_id, dsn)
    concept = preprod.get_concept(int(scene_id), dsn=dsn, account_id=account_id)
    if concept is None:
        raise ValueError(f"no scene {scene_id}")
    shot = (concept.get("shots") or [None])[0]
    if not shot or not (shot.get("prompt") or "").strip():
        raise ValueError(f"scene {scene_id} has no scene prompt yet -- `write_scene` first")
    ungrounded = preprod.reference_gate(concept)
    if ungrounded:
        raise ValueError(
            f"{ungrounded} -- scene {scene_id} is a draft and cannot be priced or "
            "rendered yet. Add a photo with `add_element` (or the person uploads "
            f"one in the studio), then `write_scene` with scene_id={scene_id}, the "
            "same prompt and `refs` from `elements`")
    try:
        clip = pricing.display(account_id=account_id, shot=shot, shot_id=int(scene_id),
                               provider=provider, model=model, seconds=duration, frame=frame)
    except pricing.PricingRefused as e:
        if e.reason == "nothing_to_render":
            clip = None
        else:
            raise ValueError(str(e)) from e
    except ValueError as e:
        raise ValueError(f"bad renderer choice: {e}") from e
    keyframes = scene_chain.keyframe_quote(concept)
    exempt = bool(account_id is not None and accounts.is_credit_exempt(account_id, dsn=dsn))
    # the ledger's tables exist wherever the app booted; a bare database
    # (stdio on a fresh clone, a test schema) gets them here, idempotently
    ledger.init(dsn)
    balance = None if account_id is None else ledger.available(account_id, dsn=dsn)
    needed = (keyframes or {}).get("credits", 0) + ((clip or {}).get("credits") or 0)
    if listing in LISTINGS:
        out = {"scene_id": int(scene_id), "status": _status_of(concept),
               "keyframes": keyframes, "clip": _listed_clip(clip, listing),
               "balance": balance, "credits_needed": needed,
               "affordable": exempt or balance is None or balance >= needed}
        if exempt:
            out["charged"] = False
        if listing == "claude":
            out["approve_url"] = studio_link(int(scene_id))
            out["note"] = ("every shot already has a clip" if clip is None else
                           "the person approves this render in the studio at "
                           "`approve_url`, where the price is shown again before "
                           "anything is spent")
        else:
            out["note"] = ("every shot already has a clip" if clip is None else
                           "show the person this price and wait for a yes; tokens are "
                           "valid for one hour -- pass them to `approve` with the same "
                           "renderer choice" if (clip or {}).get("signed") else
                           "show the person this price and wait for a yes before `approve`")
        return out
    return {
        "scene_id": int(scene_id),
        "status": _status_of(concept),
        "keyframes": keyframes,
        "clip": clip,
        "balance": balance,
        "exempt": exempt,
        "credits_needed": needed,
        "affordable": exempt or balance is None or balance >= needed,
        "note": ("every shot already has a clip" if clip is None else
                 "tokens are valid for one hour; pass them to `approve` with the same "
                 "renderer choice" if (clip or {}).get("signed") else
                 "this server signs no quotes; `approve` takes the renderer choice alone"),
    }


# --- the studio surface: images, video and effects, quoted in chat ----------
#
# 2026-10-07, Mike's call: the MCP Claude Desktop launches is for making
# things WITH Claude -- images, clips, effects -- and every one of them is
# quoted first and spent only after a yes in chat. The functions below are
# that surface's; `build_server(surface="studio")` registers them and
# nothing else. They spend through the studio's own doors
# (fal.generate_image_from_prompt, fal.generate_from_prompt, effects.run),
# so the credit hold, the cap, the generations row and the Assets wall
# behave exactly as they do from the composer and a scene's Render card.

REFERENCE_IDS = ("gen:<id> (an image on your Assets wall -- see `renders`, or the "
                 "asset_id a render returned), asset:<id> (an image you imported -- "
                 "`import_file`), a photo `ref` exactly as `elements` or `project` "
                 "lists it, or candidate:<id> (an image `images_for` found)")


def _fetchable(raw: str, account_id: Optional[int]) -> Optional[str]:
    """A stored reference -> a URL fal's servers can fetch, or None. The
    stored string first (a public URL passes, a local file is uploaded),
    then the read-time mint (`fetch_url`) for a name whose bytes live only
    in the bucket."""
    from . import asset_shelf, fal
    for minted in (False, True):
        try:
            value = asset_shelf.fetch_url(raw, account_id) if minted else raw
        except Exception:
            continue
        url = fal.as_image_url(value, resolve_photo=asset_shelf.resolve_photo,
                               account_id=account_id)
        if url:
            return url
    return None


def resolve_references(refs, *, limit: int, who: str, dsn: Optional[str] = None,
                       account_id: Optional[int] = None) -> list[str]:
    """Reference IDS -> URLs a renderer can fetch, or ValueError.

    By id and never by URL, the rule `find_images` and `write_scene`
    already keep: an agent that is handed a URL field fabricates URLs.
    Three kinds are issued by this studio -- a render on the Assets wall,
    an element's photo (the `ref` `elements` lists, checked against
    `_allowed_refs` exactly as `write_scene` checks it), a search
    candidate -- and anything else is refused with the grammar. The
    model's own limit is enforced HERE, before any spend: past it the
    call is refused rather than the extras silently dropped, and a model
    that takes none refuses any. A reference that cannot be made fetchable
    (R2 off, a photo that is nowhere) is refused for the same reason: a
    render must not be paid for against a frame it never saw."""
    from . import render_assets
    refs = list(dict.fromkeys(str(r).strip() for r in (refs or []) if str(r).strip()))
    if not refs:
        return []
    if limit <= 0:
        raise ValueError(f"{who} takes no reference images")
    if len(refs) > limit:
        raise ValueError(f"{who} takes at most {limit} reference image"
                         f"{'s' if limit != 1 else ''}, got {len(refs)}")
    allowed = None
    urls = []
    for ref in refs:
        kind, _, rest = ref.partition(":")
        if kind == "gen" and rest.isdigit():
            row = render_assets.get(int(rest), dsn, account_id=account_id)
            if not row or row.get("deleted_at"):
                raise ValueError(f"no render {rest} on this account -- ids come from `renders`")
            if row.get("media_kind") != "image":
                raise ValueError(f"{ref} is a {row.get('media_kind')}; a reference "
                                 "must be an image")
            raw = row["media_url"]
        elif kind == "asset" and rest.isdigit():
            # a file the person brought in (import_file / the editor's bin),
            # 2026-10-09 -- this account's own, and only an image references
            from .cut import store as cut_store
            row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
            if not row:
                raise ValueError(f"no import {rest} on this account -- `import_file` "
                                 "returns the id")
            if row.get("kind") != "image":
                raise ValueError(f"{ref} is {row.get('kind')}; a reference must be an image")
            raw = row["media_url"]
        elif kind == "candidate" and rest:
            cand = imagesearch.get(rest, dsn=dsn)
            if cand is None or not cand.get("image_url"):
                raise ValueError(f"no candidate {rest!r} -- ids come from `images_for`")
            raw = cand["image_url"]
        else:
            if allowed is None:
                allowed = _allowed_refs(dsn, account_id)
                # ...and every photo a project's scenes were grounded on
                # (2026-10-08): reopening a project reuses what it used
                for row in _project_refs(dsn, account_id):
                    allowed.setdefault(row["ref"], row["ref"])
            if ref not in allowed:
                raise ValueError(f"{ref!r} is not a reference id. Use one of: "
                                 f"{REFERENCE_IDS}. URLs are never taken")
            raw = allowed[ref]
        url = _fetchable(raw, account_id)
        if not url:
            raise ValueError(f"{ref} cannot be made fetchable for the renderer "
                             "(its bytes are not in the studio's bucket)")
        urls.append(url)
    return urls


def _project_refs(dsn, account_id, project_id: Optional[int] = None) -> list[dict]:
    """The refs on the account's project scenes, or [] when they cannot be
    read -- a reference check fails CLOSED (the ref is refused as unknown),
    never open."""
    from . import projects
    try:
        return projects.scene_refs(dsn, account_id=account_id, project_id=project_id)
    except Exception:
        return []


# The provider each spending tool holds credit under (src/charge.py checks
# a quote's provider against the hold's): fal for images, clips and effects,
# the still adapter for an element's sheet.
SPEND_PROVIDERS = {"generate_image": "fal", "generate_video": "fal",
                   "apply_effect": "fal", "element_sheet": "nano", "edit_clip": "fal"}


def _project_arg(project_id) -> Optional[int]:
    """A project id as it is bound into a quote: an int, or None for none."""
    return None if project_id in (None, "", 0) else int(project_id)


def _balance(account_id: Optional[int], dsn) -> Optional[int]:
    """The account's spendable credits right now, or None when there is no
    account to read or it cannot be read. A yearly plan's month that is
    due is released first, as the hold itself does (src/charge.py): a dead
    cron must not make a quote say "top up" to somebody who paid."""
    from . import ledger
    if account_id is None:
        return None
    try:
        try:
            from . import billing
            billing.release_due(account_id, dsn=dsn)
        except Exception:
            pass
        return int(ledger.available(account_id, dsn=dsn))
    except Exception:
        return None


def _when(epoch: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")


def approval_gate(usd: float, quote_token: str, *, tool: str, args: dict, what: str,
                  account_id: Optional[int], dsn) -> tuple[Optional[dict], Any, dict]:
    """The chat approval every spending tool on the studio surface goes
    through (2026-10-07: images, video, effects and sheets all quote first;
    2026-10-08: in credits, with a signed single-use token).

    Returns (stop, approved, price). `price` is what the quote shows --
    `credits` (the one conversion every hold uses, ledger.charge_credits),
    whether this account is `charged` (an exempt one is not), the
    `balance` and the `balance_after`, and the provider's `usd` as detail.

    - No `quote_token`: `stop` is the quote, nothing spent, carrying a
      token signed over THIS tool and THESE normalized arguments
      (pricing.sign_studio). No signing secret: the quote, with no token
      and a note that nothing can be approved here.
    - A token: verified (signature, expiry, account, tool, arguments) and
      re-priced; any refusal raises ValueError with its code. `approved` is
      the verified pricing.StudioQuote, handed down so the hold is its
      credits exactly.
    - Either way, a balance short of the price is `stop` as a STRUCTURED
      refusal (`refused`, `needs`, `available`) rather than an exception:
      an agent that sees a tool error retries, and a retry cannot fix an
      empty balance.

    Single use is the caller's (`start_approved`), which claims the
    token before the job starts."""
    from . import ledger, pricing
    credits = ledger.charge_credits(usd)
    charged = account_id is not None and not ledger.credit_exempt(account_id, dsn=dsn)
    balance = _balance(account_id, dsn)
    price = {"usd": usd, "credits": credits, "charged": charged, "balance": balance,
             "balance_after": (None if balance is None
                               else balance - (credits if charged else 0))}
    short = charged and balance is not None and balance < credits
    refusal = {"ok": False, "refused": "insufficient_credits", "needs": credits,
               "available": balance,
               "upgrade_url": pricing_url(),
               "note": (f"Nothing was spent. {what} needs {credits} credits and the "
                        f"balance is {balance}. Tell the person to pick a plan or "
                        f"top up at {pricing_url()}; do not call again until they have.")}
    token = (quote_token or "").strip()
    if not token:
        if short:
            return refusal, None, price
        if not pricing.configured():
            price["quote_token"] = None
            return {"ok": False, "needs_approval": True, "can_approve": False,
                    "note": (f"Nothing was spent. {what} costs {credits} credits. It "
                             "cannot be approved from here: this installation has no "
                             f"quote-signing secret ({pricing.SIGNING_ENV} is not set), "
                             "so nothing can be spent through this connector until it "
                             "is. Tell the person; quoting still works.")}, None, price
        signed = pricing.studio_quote(account_id=account_id, tool=tool,
                                      provider=SPEND_PROVIDERS[tool], args=args, usd=usd)
        price.update(quote_token=pricing.sign_studio(signed),
                     expires_at=_when(signed.expires_at))
        cost = (f"costs {credits} credits" + (
            f"; the balance is {balance} and would be {balance - credits} after it"
            if balance is not None else "") if charged else
            f"prices at {credits} credits; this account is not charged for it")
        return {"ok": False, "needs_approval": True, "can_approve": True,
                "note": (f"Nothing was spent. {what} {cost}. Show the person what it "
                         "is and the price in credits, and WAIT for a yes. Only then "
                         "call again with the SAME arguments plus quote_token from "
                         "this quote -- it is good for one hour, for exactly this "
                         "request, and once.")}, None, price
    if not pricing.configured():
        raise Refused("nothing can be approved here: this installation has no "
                      f"quote-signing secret ({pricing.SIGNING_ENV} is not set)")
    try:
        approved = pricing.verify_studio(token, account_id=account_id, tool=tool, args=args)
    except pricing.QuoteRefused as e:
        raise ValueError(f"{e.reason}: {e}. Call again WITHOUT quote_token for a fresh "
                         "quote and ask the person again") from e
    if approved.credits != credits:
        raise ValueError("stale_content: the price changed since this quote. Call "
                         "again WITHOUT quote_token for a fresh quote and ask the "
                         "person again")
    if short:
        return refusal, None, price
    return None, approved, price


def start_approved(fn, args: dict, start) -> dict[str, Any]:
    """The approved half of a quoted spend, ONCE (2026-10-08).

    `fn(**args, dry_run=True)` runs every check -- the arguments, the
    token, the balance -- and spends nothing; a structured refusal comes
    straight back and leaves the token unspent. Then the token is CLAIMED
    (src/quote_redemptions.py) and only the winner calls `start()`, which
    starts the job (or, with no job registry, runs it inline). A second
    call with the same token is handed the first call's answer -- the same
    job -- and starts and charges nothing. A claim that cannot be recorded
    refuses: an approval nobody can prove was used once is not spent."""
    from . import quote_redemptions
    pre = fn(**args, dry_run=True)
    if not pre.get("ok"):
        return pre
    approved = pre["approved"]
    acct, dsn = args.get("account_id"), args.get("dsn")
    try:
        first = quote_redemptions.claim(approved.token_id, acct, tool=approved.tool,
                                        credits=approved.credits, dsn=dsn)
    except Exception as e:
        raise Refused(f"the approval could not be recorded ({type(e).__name__}), so "
                      "nothing was started or spent -- try the same call again") from e
    if first is not None:
        earlier = dict(first.get("response") or {})
        job = earlier.get("job_id")
        return {**earlier, "already_used": True,
                "note": ("This approval was already used" +
                         (f" -- it started job {job}; poll `job` for it" if job else
                          " (its first call is still starting it)") +
                         ". Nothing new was started or charged. A new render needs a "
                         "new quote and a new yes.")}
    try:
        out = start()
    except Exception:
        try:
            quote_redemptions.forget(approved.token_id, acct, dsn=dsn)
        except Exception:
            pass
        raise
    try:
        quote_redemptions.record(approved.token_id, acct, out, dsn=dsn)
    except Exception as e:      # the claim already stands: a repeat is still refused
        print(f"note: quote {approved.token_id} redeemed but its job was not recorded "
              f"({type(e).__name__}: {e})", file=sys.stderr)
    return {**out, "quote": pre["quote"]} if "quote" not in out else out


FINISHED = ("done", "failed", "cancelled")

# What a cancel gives back, said once and the same way to the person and in
# the tool's reply (2026-10-08). The money follows fal's own answer: fal
# bills only successful outputs (fal.ai/docs/documentation/model-apis/
# pricing), so a job that ends with no output is released, and one that
# finishes anyway is kept and charged at the quoted price.
CANCEL_OUTCOMES = (
    "How it ends depends on how far it got: not yet sent to the renderer -> "
    "stopped, nothing charged; waiting in the renderer's queue -> removed, "
    "nothing charged; already rendering -> the renderer is asked to stop, and "
    "if it finishes anyway the result is kept and charged at the quoted price, "
    "otherwise nothing is charged; finished or being saved -> too late, "
    "charged and kept. A sheet already being drawn finishes."
)


def _spent_line(snap: dict) -> str:
    credits = snap.get("credits")
    if not credits:
        return ""
    return (f" It cost {credits} credits." if snap.get("charged", True)
            else f" It would have cost {credits} credits; this account is not charged.")


def cancel_studio_job(job_id: int, *, job_status, cancel,
                      account_id: Optional[int]) -> dict[str, Any]:
    """Ask the job registry to stop one of this account's jobs, and say
    honestly what that will and will not give back.

    The registry only FLAGS a running job (app/jobs.cancel); the job's own
    worker acts on it where it still changes the money -- before the
    provider call (charge.Charge.submitted) and while fal has the job
    (fal._submit_and_wait, which asks fal's cancel URL and lets fal's
    answer decide). So the answer here is "requested", and `job` says how
    it ended. A job nobody made cancellable (not one of this connector's
    render tools) is reported as such, never pretended at."""
    snap = job_status(int(job_id), account_id=account_id)
    if snap is None:
        raise ValueError(f"no job {job_id} -- jobs live in memory and a restart "
                         "clears them")
    base = {"job_id": snap["id"], "label": snap.get("label")}
    if snap["status"] in FINISHED:
        return {**base, "status": snap["status"], "cancelled": snap["status"] == "cancelled",
                "note": (f"Job {snap['id']} already finished ({snap['status']}); there is "
                         "nothing to cancel." + _spent_line(snap))}
    if not snap.get("cancellable"):
        return {**base, "status": snap["status"], "cancelled": False,
                "note": ("This job cannot be cancelled from here: only the images, "
                         "clips, effects and sheets this connector starts can be. It "
                         "will finish on its own.")}
    after = cancel(int(job_id), account_id=account_id) or snap
    if after["status"] == "cancelled":
        return {**base, "status": "cancelled", "cancelled": True,
                "note": "Cancelled before it started: nothing was held or spent."}
    return {**base, "status": after["status"], "cancelled": False, "cancel_requested": True,
            "note": (f"Cancel requested. {CANCEL_OUTCOMES} Poll `job`: it ends as "
                     "`cancelled` (nothing charged) or `done` (it finished first: "
                     "charged, and the result is filed).")}


def _cancellable_body(fn, kwargs: dict):
    """A spending job's body (2026-10-08): the tool, then the truth about a
    cancel. When the person asked to stop and the work came back with
    nothing, the job ends `cancelled` with the adapter's own words (which
    say what was released); when it came back WITH a result, the cancel was
    too late and the result says so -- charged and kept."""
    from . import cancellation

    def body(job):
        out = fn(**kwargs)
        if cancellation.requested():
            if not (isinstance(out, dict) and out.get("ok")):
                raise cancellation.Cancelled(
                    (out or {}).get("error") or "cancelled -- nothing was charged",
                    result=out)
            out = {**out, "cancel_too_late": True,
                   "note": ("The cancel came too late: the renderer had already "
                            "finished it, so it was charged at the quoted price and "
                            "is filed like any render.")}
        return {"result": out}
    return body


CRAFT_STEPS = ("refine", "enhance", "still", "beats")
CraftStep = Literal[CRAFT_STEPS]
RenderKind = Literal["image", "video", "audio", "upload"]
JoinTransition = Literal["cut", "crossfade"]
PostPlatform = Literal["tiktok"]   # publish_review.PLATFORMS; more to come
EditStage = Literal["frame", "video"]


def get_prompt_craft(step: str, prompt: str, model: str = "", tool: str = "",
                     count: int = 2, dsn: Optional[str] = None,
                     account_id: Optional[int] = None) -> dict[str, Any]:
    """The studio's own prompt writers, handed to the CALLER to run.

    Each Gemini step in the studio is an instruction plus an input. This
    returns that instruction with the input filled in and runs no model,
    so Claude does the writing and then passes the result to
    `generate_image` / `generate_video`:

    - refine: polish a video prompt for one tool against the technique
      shelf (`ai_prompting`, the same retrieval `structure_prompt` uses,
      minus the CRAG grading call -- judge the references yourself)
    - enhance: the studio's identity-preserving prompt tightener
    - still: a motion-free first-frame prompt from a video shot
    - beats: the distinct moments a shot's move passes through

    Read-only; the only outside call is the embedding for the shelf lookup.
    """
    from . import fal, promptgen, rag, shootgen, workflows
    step = (step or "").strip().lower()
    if step not in CRAFT_STEPS:
        raise ValueError(f"step must be one of {list(CRAFT_STEPS)}, got {step!r}")
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("a prompt to work on is required")
    if step == "enhance":
        return {"step": step, "instruction": workflows._enhance_system_text(),
                "input": prompt,
                "how": "Apply the instruction to `input`; the result is the new prompt."}
    if step == "still":
        return {"step": step,
                "instruction": shootgen.STILL_RUBRIC + "\n\nVIDEO SHOT:\n" + prompt,
                "how": ("The rubric ends on a different tool's flags (--ar, --style); "
                        "drop them. Send the one-sentence frame to generate_image and "
                        "pick the shape with its `aspect` argument.")}
    if step == "beats":
        return {"step": step,
                "instruction": shootgen.BEAT_RUBRIC.format(count=max(2, int(count))) +
                               "\n\nVIDEO SHOT:\n" + prompt,
                "how": "Each beat becomes its own generate_image prompt."}
    model = (model or "").strip()
    label = (tool or "").strip()
    if model:
        if model in fal.VIDEO_MODELS:
            label = fal.model_spec(model)["platform"]
        elif model in fal.IMAGE_MODELS:
            label = fal.IMAGE_MODELS[model]["label"]
        else:
            raise ValueError(f"unknown model {model!r}; see video_models / image_models")
    if not label:
        raise ValueError("refine needs `model` (a video_models id) or `tool`")
    found = rag.retrieve_references(
        f"{label} prompting technique for photorealistic AI video generation",
        domain=promptgen.REFINE_DOMAIN,
        prefer_project=accounts.slug_of(_account(account_id, dsn)))
    refs = rag.format_references(found.get("references") or []) if found.get("ok") else ""
    return {"step": step, "tool": label,
            "instruction": promptgen.build_refine_prompt(prompt, label, refs),
            "references_found": len((found.get("references") or [])),
            "lookup_error": None if found.get("ok") else found.get("error"),
            "how": ("Rewrite per the instruction. Keep every (0-3s)-style window and "
                    "every identity lock / avoid-list line; if the rewrite is much "
                    "shorter than the original or has a placeholder, keep the original.")}


def list_image_models(credits: bool = False) -> dict[str, Any]:
    """The still models `generate_image` can name -- a PROJECTION of
    fal.IMAGE_MODELS (the rows the composer's picker and
    GET /api/image-models read), so this menu cannot drift from what the
    generator accepts. Spends nothing.

    `credits` is a listed server's (2026-10-11): each row's price as the
    credits a still at 1:1 is charged -- the conversion every hold uses --
    and no dollars, which a listing never shows."""
    from . import fal, ledger
    rows = [{**row, "max_references": fal.image_max_refs(row["id"])}
            for row in fal.image_options()]
    if credits:
        rows = [{**{k: v for k, v in row.items() if k != "usd"},
                 "credits": ledger.charge_credits(row["usd"])} for row in rows]
    return {"default": fal.DEFAULT_IMAGE_MODEL, "available": fal.has_key(),
            "aspects": list(fal.IMAGE_SIZES), "models": rows}


# What a listed server leaves off a spend's answer: dollars (a listing
# shows credits, as the studio does) and where the file sits on the
# server's own disk.
_LISTED_SPEND_DROPS = ("usd", "cost_usd", "estimate_usd", "path")


def _listed_spend(payload: dict, account_id: Optional[int]) -> dict[str, Any]:
    """A quoted spend's answer as the render listing gives it: the quote
    and the result in credits only, the image as an address a person can
    open, and the `gen:<id>` that names it from then on."""
    out = {k: v for k, v in payload.items() if k not in _LISTED_SPEND_DROPS}
    if isinstance(out.get("quote"), dict):
        out["quote"] = {k: v for k, v in out["quote"].items()
                        if k not in _LISTED_SPEND_DROPS}
    if out.get("media_url"):
        out["media_url"] = _view(out["media_url"], account_id)
    if out.get("asset_id") is not None:
        out["ref"] = f"gen:{out['asset_id']}"
    return out


def run_image(prompt: str, model: str = "", aspect: str = "",
              references: Optional[list] = None, quote_token: str = "",
              dsn: Optional[str] = None,
              account_id: Optional[int] = None,
              dry_run: bool = False,
              project_id: Optional[int] = None,
              listed: bool = False) -> dict[str, Any]:
    """One still on ONE chosen model, through fal.generate_image_from_prompt:
    the composer's own door, so the credit hold, the cap, the generations
    row and the Assets wall behave exactly as they do from Studio.

    Quoted first (2026-10-07): with no quote_token it returns the price in
    credits and a signed token and spends nothing; it renders only with that
    token, for exactly these arguments (`approval_gate`). The
    model, the aspect and the reference count are checked HERE and
    refused with the legal set, never clamped -- an agent that asked for
    one model and got another would file the wrong model's output as a
    comparison. A failed render comes back as ok=False with fal's reason
    (its hold already released), not as an exception: an agent that sees
    a tool error retries the identical call.

    `listed` is the render listing's door (2026-10-11, Mike's D1 in
    docs/tasks/task-connector-elements.md): the SAME gate, hold and
    single-use token, answered in credits only (`_listed_spend`). It is
    not part of what the token signs.
    """
    from . import fal
    shaped = (lambda out: _listed_spend(out, account_id)) if listed else (lambda out: out)
    prompt = " ".join((prompt or "").split())
    if not prompt:
        raise ValueError("an empty prompt renders nothing")
    model = (model or "").strip() or fal.DEFAULT_IMAGE_MODEL
    spec = fal.IMAGE_MODELS.get(model)
    if spec is None:
        raise ValueError(f"model must be one of {list(fal.IMAGE_MODEL_NAMES)}, got {model!r}")
    aspect = (aspect or "").strip()
    if aspect and aspect not in fal.IMAGE_SIZES:
        raise ValueError(f"aspect must be one of {list(fal.IMAGE_SIZES)}, got {aspect!r}")
    named = list(dict.fromkeys(str(r).strip() for r in references or [] if str(r).strip()))
    urls = resolve_references(named, limit=fal.image_max_refs(model), who=spec["label"],
                              dsn=dsn, account_id=account_id)
    usd = fal.image_usd(model, aspect or None, references=len(urls))
    quote = {"model": model, "label": spec["label"], "aspect": aspect or None,
             "references": named, "usd": usd,
             **_filed_under(project_id, dsn, account_id)}
    stop, approved, price = approval_gate(
        usd, quote_token, tool="generate_image", what=f"This {spec['label']} image",
        args={"prompt": prompt, "model": model, "aspect": aspect or None,
              "references": named, "project_id": _project_arg(project_id)},
        account_id=account_id, dsn=dsn)
    quote.update(price)
    if stop is not None:
        return shaped({**stop, "quote": quote})
    if dry_run:      # every refusal above, none of the spend: the job's pre-flight
        return shaped({"ok": True, "dry_run": True, "quote": quote, "approved": approved})
    outcomes.record_refs("ref_reuse", named, account_id=account_id, source="mcp", dsn=dsn)
    res = fal.generate_image_from_prompt(
        prompt, model=model, aspect=aspect or None, reference_urls=urls or None,
        approved=True, account_id=account_id, source="mcp", bank=True,
        project_id=project_id, quote=approved,
        **({"db_path": dsn} if dsn is not None else {}))
    return shaped({**res, "quote": quote})


ElementKind = Literal["character", "prop", "location"]


def _find_element(kind: str, name: str, dsn, account_id) -> dict:
    """One element by kind + name (case-insensitive), as `elements` lists
    it, or ValueError naming the ones that exist."""
    from . import element_sheet as sheets
    kind = (kind or "").strip().lower()
    if kind not in sheets.KINDS:
        raise ValueError(f"kind must be one of {list(sheets.KINDS)}, got {kind!r}")
    wanted = " ".join((name or "").split()).lower()
    items = [i for i in _catalogue(dsn, account_id) if i["category"] == kind]
    for item in items:
        if item["name"].strip().lower() == wanted:
            return item
    names = [i["name"] for i in items]
    raise ValueError(f"no {kind} named {name!r} -- `elements` lists them"
                     + (f" ({', '.join(names[:20])})" if names else
                        f"; there are no {kind}s yet"))


def run_element_sheet(kind: str, name: str, quote_token: str = "",
                      dsn: Optional[str] = None, account_id: Optional[int] = None,
                      dry_run: bool = False) -> dict[str, Any]:
    """Draw (or redraw) one element's reference sheet from its real photos
    (2026-10-08, Mike: "create an element sheet tool"), behind the same chat
    approval as every other spend on this surface.

    The drawing is the studio's own: `element_sheet.draw`, the code the
    Elements card's button and the create routes run, so the sheet comes out
    the same shape (five panels for a person, a turnaround for a prop, plates
    for a place) and lands where the studio keeps it -- `<element>/sheet.jpg`,
    mirrored to the bucket, listed after the real photos so `refs[0]` is never
    the drawing. The charge is the image adapter's own hold at the model's
    meter price, which is the price quoted here.

    A redraw REPLACES the current sheet, exactly as the studio's button does;
    the quote says so. Only the element's real photos are sent -- an earlier
    sheet is never grounded on.
    """
    import tempfile

    from . import asset_shelf, media
    from . import element_sheet as sheets
    account_id = _account(account_id, dsn)
    item = _find_element(kind, name, dsn, account_id)
    kind = item["category"]
    photos = [u for u in item.get("photos") or []
              if not sheets.is_sheet(u.rsplit("/", 1)[-1].split("?", 1)[0])]
    has_sheet = len(photos) < len(item.get("photos") or [])
    if not photos:
        raise ValueError(f"{item['name']} has no photos -- a sheet is drawn from real "
                         "photos; add one in the studio (Elements) first")
    if not sheets.available(account_id):
        raise Refused("element sheets are not available on this installation "
                      "(no image key is set)")
    usd = sheets.price_usd()
    quote = {"element": {"kind": kind, "name": item["name"]},
             "photos": min(len(photos), sheets.MAX_REFERENCES),
             "layout": {"character": "front, three-quarter, profile, back and a close-up",
                        "prop": "a turnaround",
                        "location": "a set of plates"}[kind],
             "replaces_sheet": has_sheet, "usd": usd}
    what = (f"Redrawing {item['name']}'s sheet (it replaces the current one)"
            if has_sheet else f"Drawing {item['name']}'s sheet")
    stop, approved, price = approval_gate(
        usd, quote_token, tool="element_sheet", what=what,
        # the photos it is drawn from and whether it replaces a sheet are
        # part of what was approved: a sheet drawn meanwhile turns a "draw"
        # into a "replace", which the person has not said yes to
        args={"kind": kind, "element": item["name"],
              "photos": [u.rsplit("/", 1)[-1].split("?", 1)[0] for u in photos],
              "replaces_sheet": has_sheet},
        account_id=account_id, dsn=dsn)
    quote.update(price)
    if stop is not None:
        return {**stop, "quote": quote}
    if dry_run:
        return {"ok": True, "dry_run": True, "quote": quote, "approved": approved}

    slug = asset_shelf.slugify(item["name"])
    out_dir = asset_shelf.PHOTO_DIRS[kind] / slug
    plural = {"character": "characters", "prop": "props", "location": "locations"}[kind]
    with tempfile.TemporaryDirectory() as tmp:
        files = sheets.photo_files(photos, Path(tmp), account_id)
        if not files:
            return {"ok": False, "quote": quote,
                    "error": "none of the element's photos could be read"}
        res = sheets.draw(kind, item["name"], files,
                          sheets.out_dir_for(out_dir, files, Path(tmp)),
                          notes=item.get("text") or "", account_id=account_id,
                          db_path=dsn, quote=approved)
        if not res["ok"]:
            return {"ok": False, "quote": quote, "error": res["error"]}
        # inside the scratch folder's life: the sheet may live only there
        media.mirror(res["path"], f"{plural}/{slug}/{res['path'].name}", account_id,
                     content_type="image/jpeg")
    ref = asset_shelf.storable_ref(asset_shelf.photo_url(kind, slug, res["path"].name))
    return {"ok": True, "quote": quote, "sheet": ref, "media_url": _view(ref, account_id),
            "generation_id": res.get("generation_id"),
            "note": (f"Saved as {item['name']}'s reference sheet in Elements. It is "
                     "listed after the real photos; scenes still anchor on a photo.")}


# --- a picture becomes an element (2026-10-11) ------------------------------
#
# docs/tasks/task-connector-elements.md. A scene is held to the person's own
# photographs, `write_scene` takes them only from `elements`, and until
# today nothing on the connector could ADD one -- so a new account, with no
# elements, could make nothing from a chat. `add_element` files ONE picture
# as an element through the Elements page's own create body (app/api.py
# `create_element`, injected: src/ never imports app/), so the picture is
# saved, mirrored, described and shelved exactly as an upload in the studio
# is. It draws nothing: a reference sheet is a still that costs credits and
# has its own quoted tool.
#
# `source` MAY BE A URL, which no other tool here takes -- references are
# ids because an agent handed a URL field invents URLs. This one is the
# door a picture comes IN by, and an invented address costs nothing but a
# refusal: it is fetched with every guard a stranger's address needs
# (refbin.fetch_public_image -- https at every hop, public hosts only, a
# size cap), decoded to prove it is a picture, and only then saved.

ELEMENT_KINDS = ("character", "prop", "location")
ELEMENT_NAME_MAX = 80
ELEMENT_NOTES_MAX = 600
# the bound every later reader of the photo assumes (element_sheet.PHOTO_BYTES_MAX,
# the vision description, a keyframe): 15 MB
ELEMENT_PHOTO_BYTES = 15 * 1024 * 1024
ELEMENT_SOURCES = ("the https address of an image file (jpg, png or webp), "
                   "gen:<id> (one of your renders) or asset:<id> (an image you "
                   "brought in)")


def _own_picture(handle: str, dsn, account_id) -> bytes:
    """The bytes behind one of the account's OWN images, named `gen:<id>`
    (a render on the Assets wall) or `asset:<id>` (an upload). Someone
    else's id is exactly as missing as one that never existed: both
    lookups are scoped. The file is read where the editor reads it
    (cut.sources: this disk first, else the bucket)."""
    import tempfile

    from . import render_assets
    from .cut import sources
    from .cut import store as cut_store
    kind, _, rest = handle.partition(":")
    if kind == "gen":
        row = render_assets.get(int(rest), dsn, account_id=account_id)
        if not row or row.get("deleted_at"):
            raise ValueError(f"no render {rest} on this account")
        what = row.get("media_kind")
    else:
        row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
        if not row:
            raise ValueError(f"no import {rest} on this account")
        what = row.get("kind")
    if what != "image":
        raise ValueError(f"{handle} is {what or 'not an image'}; an element's picture "
                         "must be an image")
    megabytes = ELEMENT_PHOTO_BYTES // (1024 * 1024)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            path = sources.file_for(handle, row, account_id, Path(tmp))
            size = path.stat().st_size
            if size > ELEMENT_PHOTO_BYTES:
                raise ValueError(f"{handle} is over {megabytes} MB")
            return path.read_bytes()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{handle}'s file could not be read") from e


def _picture(source: str, dsn, account_id) -> tuple[bytes, str]:
    """`source` -> (the picture's bytes, which kind of source it was), or
    ValueError saying why it was not taken."""
    source = (source or "").strip()
    if not source:
        raise ValueError(f"`source` is required -- ONE of: {ELEMENT_SOURCES}")
    kind, _, rest = source.partition(":")
    if kind in ("gen", "asset") and rest.isdigit():
        return _own_picture(source, dsn, account_id), kind
    if kind.lower() in ("http", "https"):
        try:
            return refbin.fetch_public_image(source, max_bytes=ELEMENT_PHOTO_BYTES), "url"
        except refbin.ImageRefused as e:
            raise ValueError(f"that picture was not added: {e}") from e
    raise ValueError(f"{source[:80]!r} is not a picture this takes. `source` is ONE "
                     f"of: {ELEMENT_SOURCES}")


def _element_as_listed(kind: str, slug: str, dsn, account_id) -> Optional[dict]:
    """One element in the shape `elements` lists it, found by kind and the
    name's slug (a place is stored under its slug), or None."""
    from . import asset_shelf
    for item in _catalogue(dsn, account_id):
        if item["category"] == kind and asset_shelf.slugify(item["name"]) == slug:
            return {"kind": kind, "name": item["name"],
                    "description": (item.get("text") or "")[:300],
                    "photos": [{"ref": asset_shelf.storable_ref(url),
                                "label": _photo_label(url)}
                               for url in item.get("photos") or []]}
    return None


def add_element(kind: str, name: str, source: str, notes: str = "", *,
                create_element=None, dsn: Optional[str] = None,
                account_id: Optional[int] = None) -> dict[str, Any]:
    """File ONE picture as an element (or onto one the account already
    has under that name), and answer with the element as `elements` lists
    it -- the new photo's `ref` is what `write_scene` takes.

    Every refusal comes before anything is saved, in the order a caller
    can fix them: the kind, the name, whether this account may create at
    all (the Elements page's own gate), the source -- a `gen:` / `asset:`
    that is not the caller's, an address that is not public https or not
    an image, a file over the size bound -- and last that the bytes
    really decode as a picture. What is saved is an upright JPEG under a
    content-hashed name, so the same picture added twice is one file.

    `create_element` is app/api.py's body behind an adapter
    (app/mcp_mount.connector_element): it draws no sheet and spends no
    credits, and raises ValueError / Refused with the page's own words.
    Without one (a bare test server) the tool says so rather than
    pretending."""
    import hashlib

    from . import asset_shelf
    account_id = _account(account_id, dsn)
    kind = (kind or "").strip().lower()
    if kind not in ELEMENT_KINDS:
        raise ValueError(f"kind must be one of {list(ELEMENT_KINDS)}, got {kind!r}")
    name = " ".join((name or "").split())
    slug = asset_shelf.slugify(name)
    if not slug:
        raise ValueError("a name is required (letters or numbers) -- what should "
                         "this element be called?")
    if len(name) > ELEMENT_NAME_MAX:
        raise ValueError(f"the name is too long ({len(name)} characters; at most "
                         f"{ELEMENT_NAME_MAX})")
    notes = " ".join((notes or "").split())[:ELEMENT_NOTES_MAX]
    if create_element is None:
        raise Refused("elements cannot be added through this server -- add them in "
                      "the studio (Elements)")
    _create_gate(account_id, dsn)        # the page's gate, before any fetch

    data, came_from = _picture(source, dsn, account_id)
    jpeg = refbin.to_jpeg(data)
    if not jpeg:
        raise ValueError("that picture was not added: it is not an image this can "
                         "read (jpg, png or webp)")
    filename = f"add-{hashlib.sha1(jpeg).hexdigest()[:16]}.jpg"
    made = create_element(kind, name, photo=(filename, jpeg), notes=notes,
                          account_id=account_id) or {}
    if came_from == "gen":      # a render that became a reference was kept
        outcomes.record_refs("element_from", [source.strip()], account_id=account_id,
                             source="mcp", dsn=dsn)

    element = _element_as_listed(kind, made.get("slug") or slug, dsn, account_id)
    photo = next((ph for ph in (element or {}).get("photos") or []
                  if ph["label"] == filename), None)
    out: dict[str, Any] = {"added": True, "kind": kind,
                           "name": (element or {}).get("name") or name,
                           "element": element, "photo": photo,
                           "described": bool(made.get("described")),
                           "credits": 0}
    if photo is None:
        out["note"] = ("the picture was saved, but it is not listed yet -- call "
                       "`elements` for its `ref`")
    else:
        out["note"] = (f"Added to {out['name']}. Nothing was drawn and no credits "
                       "were spent.")
        out["next"] = "pass the photo's `ref` as one of a scene's `refs`"
    return out


def list_video_models() -> dict[str, Any]:
    """The fal video models `generate_video` can name -- providers.
    models_for("fal"), the SAME projection the Queue's picker reads: id,
    platform, the legal lengths and resolutions, the per-second rate by
    resolution. Spends nothing."""
    from . import fal, providers
    return {"default": fal.DEFAULT_MODEL, "available": fal.has_key(),
            "models": providers.models_for("fal")}


def run_video(prompt: str, model: str = "", seconds: Optional[int] = None,
              frame: str = "", reference: str = "", quote_token: str = "",
              dsn: Optional[str] = None,
              account_id: Optional[int] = None,
              dry_run: bool = False,
              project_id: Optional[int] = None) -> dict[str, Any]:
    """One clip on ONE chosen fal model, behind a chat approval.

    Priced first by providers.check_render_choice -- the Queue's own
    check, which REFUSES a length or resolution the model does not take
    rather than clamping it. It renders only with the quote's signed token,
    which is bound to these exact arguments, so an agent that changes the
    model or length after the person said yes is refused, not charged.

    The render is fal.generate_from_prompt: the hold before the submit,
    the daily cap, the restart-survivable receipt, the generations row
    and the Assets wall. A signed-in caller (CALLER_ACCOUNT) is refused:
    the listed server never registers this tool, and a scene's signed
    quote (`write_scene` -> `quote` -> `approve`) is that caller's door.
    """
    from . import fal, providers
    if CALLER_ACCOUNT.get() is not None:
        raise Refused("video renders from this connector are the operator's key "
                      "only -- save the scene with `write_scene` and `approve` it")
    prompt = " ".join((prompt or "").split())
    if not prompt:
        raise ValueError("an empty prompt renders nothing")
    reference = (reference or "").strip()
    (start_frame,) = resolve_references(
        [reference] if reference else [], limit=1, who="a clip's start frame",
        dsn=dsn, account_id=account_id) or (None,)
    choice = providers.check_render_choice(
        "fal", (model or "").strip() or None, seconds, (frame or "").strip() or None)
    usd = round(float(choice["estimate_usd"]), 4)
    quote = {"model": choice["model"], "seconds": choice["duration"],
             "frame": choice["frame"], "usd": usd,
             "from_image": bool(start_frame),
             **({"reference": reference} if reference else {}),
             **_filed_under(project_id, dsn, account_id)}
    stop, approved, price = approval_gate(
        usd, quote_token, tool="generate_video", what="This clip",
        args={"prompt": prompt, "model": choice["model"], "seconds": choice["duration"],
              "frame": choice["frame"], "reference": reference or None,
              "project_id": _project_arg(project_id)},
        account_id=account_id, dsn=dsn)
    quote.update(price)
    if stop is not None:
        return {**stop, "quote": quote}
    if dry_run:      # every refusal above, none of the spend: the job's pre-flight
        return {"ok": True, "dry_run": True, "quote": quote, "approved": approved}
    if reference:
        outcomes.record_ref("ref_reuse", reference, account_id=account_id, source="mcp", dsn=dsn)
    res = fal.generate_from_prompt(
        prompt, reference_image=start_frame, model=choice["model"],
        duration=choice["duration"], resolution=choice["frame"],
        approved=True, account_id=account_id, source="mcp", bank=True,
        project_id=project_id, quote=approved,
        **({"db_path": dsn} if dsn is not None else {}))
    return {**res, "quote": quote}


IMPORT_DIRS_ENV = "ZEROPAGE_IMPORT_DIRS"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def import_roots() -> list[Path]:
    """The folders `import_file` may read (2026-10-09, task-mcp-studio-v2
    step 3+4): ZEROPAGE_IMPORT_DIRS (os.pathsep-separated) when set, else
    ~/Downloads, ~/Desktop and this checkout's data/. Resolved, so a
    symlinked folder is compared by where it really is."""
    raw = (os.environ.get(IMPORT_DIRS_ENV) or "").strip()
    named = ([d for d in raw.split(os.pathsep) if d.strip()] if raw else
             ["~/Downloads", "~/Desktop", str(PROJECT_ROOT / "data")])
    out = []
    for d in named:
        try:
            out.append(Path(d.strip()).expanduser().resolve())
        except (OSError, RuntimeError):
            continue
    return out


def _import_types() -> dict[str, str]:
    """Images, and mp4/mov clips -- what a reference, an effect source or a
    join takes. Not audio, not webm: the task's list, kept narrow."""
    from .cut import uploads
    return {**uploads.IMAGE_TYPES, ".mp4": "video/mp4", ".mov": "video/quicktime"}


def run_prepare_post(source: str, platform: str = "tiktok", caption: str = "",
                     dsn: Optional[str] = None,
                     account_id: Optional[int] = None) -> dict[str, Any]:
    """Draft a post and return its review link (2026-10-11,
    src/publish_review.py). This is the ONLY publishing call on the MCP
    surface, and it sends nothing: the person answers the platform's
    questions and presses Post on the studio's review page, which is a
    signed-in request no MCP tool can make (tests/test_publish_review.py)."""
    from . import publish_review
    return publish_review.prepare(source, platform=platform, caption=caption,
                                  account_id=_account(account_id, dsn),
                                  created_via="mcp", dsn=dsn)


def run_import_file(path: str, dsn: Optional[str] = None,
                    account_id: Optional[int] = None) -> dict[str, Any]:
    """A file on THIS machine -> an `asset:<id>` (2026-10-09, step 3+4's
    fallback: the studio surface runs over stdio on the person's own Mac,
    and Claude Desktop cannot hand an MCP tool a file).

    Refused unless the path, with every symlink resolved, sits inside one
    of `import_roots()` -- so `~/Downloads/../.ssh/key` and a link out of
    Downloads both fail -- and its extension is an image or mp4/mov, its
    size under the editor's caps and its content what the extension says
    (src/cut/uploads.save probes it). Filed by the editor's own upload body,
    so it is in the bin, mirrored to the bucket and owned by the account.
    Never for a signed-in caller: a connector over the network must not
    read the server's disk."""
    from .cut import render, uploads
    if CALLER_ACCOUNT.get() is not None:
        raise Refused("import_file reads files on the computer running the studio's "
                      "own server; it is not offered over a connector")
    raw = (path or "").strip()
    if not raw:
        raise ValueError("give the file's full path, e.g. ~/Downloads/can.jpg")
    given = Path(raw).expanduser()
    if not given.is_absolute():
        raise ValueError(f"{raw!r} is not a full path -- e.g. ~/Downloads/can.jpg")
    roots = import_roots()
    try:
        real = given.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(f"there is no file at {raw}") from None
    if not any(real == r or r in real.parents for r in roots):
        raise ValueError(f"{raw} is outside the folders the studio may read: "
                         + ", ".join(str(r) for r in roots))
    if not real.is_file():
        raise ValueError(f"{raw} is not a file")
    types = _import_types()
    if real.suffix.lower() not in types:
        raise ValueError(f"only images ({', '.join(sorted(uploads.IMAGE_TYPES))}) and "
                         ".mp4 / .mov clips can be imported, not {real.suffix or 'that'}")
    size, cap = real.stat().st_size, uploads.cap_for(uploads.kind_of(real.suffix))
    if size > cap:
        raise ValueError(f"{real.name} is {size // uploads.MB}MB; the limit is "
                         f"{cap // uploads.MB}MB")
    try:
        saved = uploads.save(real.read_bytes(), real.name, account_id=account_id,
                             media_dir=render.CUT_DIR / "media", types=types, dsn=dsn)
    except uploads.UploadRefused as e:
        raise ValueError(f"{real.name}: {e}") from e
    info, kind = saved["info"], saved["kind"]
    use = ("a reference (generate_image, generate_video's start frame, an image effect)"
           if kind == "image" else "a clip effect's source or a clip to assemble_clips")
    return {"ok": True, "id": saved["handle"], "kind": kind, "filename": real.name,
            "seconds": None if kind == "image" else info.get("seconds"),
            "width": info.get("width"), "height": info.get("height"),
            "size_bytes": saved["size"],
            "note": f"Imported as {saved['handle']} -- use it as {use}. It is also in "
                    "the editor's media bin. Nothing was spent."}


def run_assemble_clips(clips: Optional[list] = None, transition: str = "cut",
                       crossfade_s: float = 0.5, music: str = "", letterbox: bool = False,
                       title: str = "", project_id: Optional[int] = None,
                       dsn: Optional[str] = None, account_id: Optional[int] = None,
                       dry_run: bool = False) -> dict[str, Any]:
    """Join `gen:<id>` clips into one video (2026-10-09, task-mcp-studio-v2
    step 2a): src/cut/join.py's plan -- every refusal, before anything is
    written -- then its join, which saves a scratch cut, renders it on this
    server and files the MP4 on the Assets wall. Spends nothing, so there
    is no quote: the result says so instead of quoting zero. A render that
    fails comes back as ok=False with the reason, never as a tool error the
    agent would retry identically."""
    from .cut import join, render, sources
    filed = _filed_under(project_id, dsn, account_id)
    try:
        planned = join.plan(list(clips or []), account_id=account_id, transition=transition,
                            crossfade_s=crossfade_s, music=(music or "").strip() or None,
                            letterbox=bool(letterbox), dsn=dsn)
    except join.JoinRefused as e:
        raise ValueError(str(e)) from e
    plan = {"clips": planned["handles"], "seconds": planned["seconds"],
            "canvas": planned["canvas"], "transition": planned["transition"],
            "crossfade_s": (round(planned["crossfade_frames"] / planned["fps"], 3)
                            if planned["crossfade_frames"] else None),
            "music": planned["music"], "letterboxed": planned["letterboxed"],
            "notes": planned["notes"], "credits": 0, **filed}
    if dry_run:
        return {"ok": True, "dry_run": True, "plan": plan}
    try:
        res = join.join(planned, account_id=account_id, title=title,
                        project_id=_project_arg(project_id), dsn=dsn)
    except (render.RenderError, sources.SourceError, ValueError) as e:
        return {"ok": False, "error": str(e), "plan": plan, "note": join.FREE_NOTE}
    return {**res, "plan": plan}


def list_effects(effect: str = "", category: str = "") -> dict[str, Any]:
    """The effects `apply_effect` can name -- a projection of
    effects.EFFECTS, so it cannot list one run_effect would refuse.
    Spends nothing."""
    from . import effects, fal
    return {"available": fal.has_key(), "categories": list(effects.CATEGORIES),
            "effects": effects.catalogue(effect=effect, category=category)}


def _clip_row(ref: str, dsn, account_id) -> dict:
    """A clip source by id -> its row ({media_url, output_path}): a `gen:<id>`
    video on the Assets wall, or an `asset:<id>` clip the person imported
    (2026-10-09). URLs are never taken."""
    from . import render_assets
    from .cut import store as cut_store
    kind, _, rest = ref.partition(":")
    if kind == "asset" and rest.isdigit():
        row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
        if not row:
            raise ValueError(f"no import {rest} on this account -- `import_file` returns the id")
        if row.get("kind") != "video":
            raise ValueError(f"{ref} is {row.get('kind')}; this takes a clip")
        return row
    if kind != "gen" or not rest.isdigit():
        raise ValueError(f"{ref!r}: a clip source is gen:<asset id> -- a video on "
                         "the Assets wall (see `renders`) -- or an asset:<id> you "
                         "imported. URLs are never taken")
    row = render_assets.get(int(rest), dsn, account_id=account_id)
    if not row or row.get("deleted_at"):
        raise ValueError(f"no render {rest} on this account -- ids come from `renders`")
    if row.get("media_kind") != "video":
        raise ValueError(f"{ref} is a {row.get('media_kind')}; this effect takes a clip")
    return row


def _video_sources(refs: list[str], dsn, account_id) -> tuple[list[str], dict]:
    """Clip sources by id (`_clip_row`) -> (fetchable URLs, probe of the
    first). A clip has no element or search id, and URLs are never taken."""
    from . import effects
    urls, probe = [], None
    for ref in refs:
        row = _clip_row(ref, dsn, account_id)
        local = row.get("output_path") or ""
        if probe is None:
            target = local if local and Path(local).is_file() else row["media_url"]
            probe = effects.probe_video(target)
        url = effects.fetchable_video(row["media_url"], local, account_id=account_id)
        if not url:
            raise ValueError(f"{ref} cannot be made fetchable for the renderer (its "
                             "file is not in the studio's bucket)")
        urls.append(url)
    return urls, probe


def run_effect(effect: str, sources: Optional[list] = None, prompt: str = "",
               options: Optional[dict] = None, quote_token: str = "",
               dsn: Optional[str] = None, account_id: Optional[int] = None,
               dry_run: bool = False,
               project_id: Optional[int] = None) -> dict[str, Any]:
    """Apply ONE effect (`effects` lists them) to sources named by id,
    behind the same chat approval as a clip: quoted with no quote_token,
    run only with that quote's token. Every check -- the effect,
    its options, the number and kind of sources, the prompt rule, the
    clip's measured length -- runs before the quote, so the price shown is
    the price of exactly the call that will run."""
    from . import effects
    row = effects.spec(effect)
    effect = effect.strip()
    opts = effects.check_options(effect, options)
    prompt = effects.check_prompt(effect, prompt)
    named = list(dict.fromkeys(str(r).strip() for r in sources or [] if str(r).strip()))
    effects.check_sources(effect, len(named), opts)
    probe = None
    if row["takes"] == "video":
        urls, probe = _video_sources(named, dsn, account_id)
    else:
        urls = resolve_references(named, limit=row["sources"][1], who=row["label"],
                                  dsn=dsn, account_id=account_id)
    usd = effects.quote_usd(effect, opts, probe)
    quote = {"effect": effect, "label": row["label"], "options": opts,
             "sources": named, "output": row["output"], "usd": usd,
             **({"source_clip": probe} if probe else {}),
             **_filed_under(project_id, dsn, account_id)}
    stop, approved, price = approval_gate(
        usd, quote_token, tool="apply_effect", what=f"This {row['label']} pass",
        args={"effect": effect, "options": opts, "sources": named, "prompt": prompt,
              "project_id": _project_arg(project_id)},
        account_id=account_id, dsn=dsn)
    quote.update(price)
    if stop is not None:
        return {**stop, "quote": quote}
    if dry_run:
        return {"ok": True, "dry_run": True, "quote": quote, "approved": approved}
    res = effects.run(effect, urls, prompt, opts, usd=usd, sources=named, probe=probe,
                      account_id=account_id, db_path=dsn, source="mcp",
                      project_id=project_id, quote=approved)
    return {**res, "quote": quote}


def _uploads(cap: int, dsn, account_id, *, kinds: tuple) -> dict[str, Any]:
    """The files this account brought in -- `import_file` or the editor's
    bin -- as `asset:<id>` (2026-10-09): `kinds` ("audio",) is what
    assemble_clips takes as music. They live in cut_media, not on the Assets
    wall -- a file somebody brought in is not a render."""
    from .cut import store
    out = []
    try:
        rows = store.media_bin(account_id=account_id, dsn=dsn)
    except Exception:
        rows = []
    for r in rows:
        if r.get("origin") != "upload" or r.get("kind") not in kinds:
            continue
        out.append({"id": f"asset:{r['id']}", "kind": r.get("kind"), "model": None,
                    "provider": None, "prompt": r.get("filename") or "",
                    "seconds": r.get("seconds"), "media_url": _view(r.get("media_url"), account_id),
                    "created_at": str(r.get("created_at") or "")})
        if len(out) >= cap:
            break
    return {"count": len(out), "renders": out,
            "note": "" if out else (
                "no audio uploaded yet -- add a music file in the studio's editor (Timeline)"
                if kinds == ("audio",) else
                "nothing imported yet -- `import_file` brings in an image or a clip")}


def _clip_file(row: dict, account_id) -> tuple[str, str, Optional[int]]:
    """A clip row -> (what ffmpeg/ffprobe can open, its suffix, its size in
    bytes when the file is on this disk)."""
    local = row.get("output_path") or ""
    if local and Path(local).is_file():
        return local, Path(local).suffix.lower(), Path(local).stat().st_size
    url = _view(row.get("media_url"), account_id) or ""
    return url, Path(url.split("?", 1)[0]).suffix.lower(), None


def _approved_frame(frame: str, source: str, instruction: str, dsn, account_id) -> dict:
    """The still stage 1 made, or ValueError. The video stage takes ONLY a
    frame this tool edited from this clip with this instruction -- so the
    dear half cannot be bought without the cheap half having been made to
    look at, and a frame of another clip cannot stand in for it."""
    from . import render_assets
    kind, _, rest = (frame or "").strip().partition(":")
    if kind != "gen" or not rest.isdigit():
        raise ValueError("stage=\"video\" needs `frame`: the gen:<id> of the edited frame "
                         "you showed the person -- run stage=\"frame\" first")
    row = render_assets.get(int(rest), dsn, account_id=account_id)
    if not row or row.get("deleted_at") or row.get("media_kind") != "image":
        raise ValueError(f"no edited frame {frame} on this account -- stage=\"frame\" makes one")
    made = (row.get("metadata") or {}).get("edit_clip") or {}
    if made.get("stage") != "frame":
        raise ValueError(f"{frame} is not a frame this tool edited -- stage=\"frame\" makes "
                         "the one to approve")
    if made.get("source") != source:
        raise ValueError(f"{frame} was made from {made.get('source')}, not {source} -- a "
                         "frame only stands for its own clip")
    if made.get("instruction") != instruction:
        raise ValueError(f"{frame} was made with a different instruction ({made.get('instruction')!r}). "
                         "Use that instruction exactly, or make a new frame for this one")
    return row


def run_edit_clip(source: str, instruction: str, stage: str = "frame", frame: str = "",
                  model: str = "", at: float = 0.0, keep_audio: bool = True,
                  quote_token: str = "", dsn: Optional[str] = None,
                  account_id: Optional[int] = None, dry_run: bool = False,
                  project_id: Optional[int] = None) -> dict[str, Any]:
    """Edit a clip by instruction, a frame first (2026-10-10,
    task-mcp-studio-v2 step 2c; src/clip_edit.py has the models and why).

    `stage="frame"`: one frame of the clip, pulled here with ffmpeg and
    edited as a still (clip_edit.FRAME_EFFECT) -- quote 1. Its quote lists
    what the video stage would cost on every model for THIS clip, so the
    whole price is known before the first credit. `stage="video"`: the
    whole clip on one model -- quote 2 -- and only with the gen:<id> of a
    frame stage 1 made from this clip with this instruction
    (`_approved_frame`). Both go through `approval_gate`; every check runs
    before either quote."""
    from . import clip_edit, effects, fal
    stage = (stage or "frame").strip().lower()
    if stage not in clip_edit.STAGES:
        raise ValueError(f"stage must be one of {list(clip_edit.STAGES)}, got {stage!r}")
    source = (source or "").strip()
    instruction = clip_edit.normal(instruction)
    row = _clip_row(source, dsn, account_id)
    target, suffix, size = _clip_file(row, account_id)
    filed = _filed_under(project_id, dsn, account_id)

    if stage == "frame":
        probe = effects.probe_video(target)
        try:
            at = float(at or 0)
        except (TypeError, ValueError):
            raise ValueError(f"`at` is a number of seconds into the clip, got {at!r}") from None
        if not 0 <= at < probe["seconds"]:
            raise ValueError(f"`at` must be inside the clip (0 to {probe['seconds']:g}s), "
                             f"got {at:g}")
        usd = clip_edit.frame_usd()
        still = effects.spec(clip_edit.FRAME_EFFECT)
        from . import ledger
        then = [{**o, **({"credits": ledger.charge_credits(o["usd"])} if "usd" in o else {})}
                for o in clip_edit.options_for(probe, suffix=suffix, size_bytes=size)]
        quote = {"stage": "frame", "source": source, "instruction": instruction, "at": at,
                 "frame_model": still["label"], "usd": usd, "source_clip": probe,
                 "then": then, **filed}
        stop, approved, price = approval_gate(
            usd, quote_token, tool="edit_clip", what="Editing one frame of this clip",
            args={"stage": "frame", "source": source, "instruction": instruction, "at": at,
                  "project_id": _project_arg(project_id)},
            account_id=account_id, dsn=dsn)
        quote.update(price)
        if stop is not None:
            return {**stop, "quote": quote}
        if dry_run:
            return {"ok": True, "dry_run": True, "quote": quote, "approved": approved}
        import tempfile
        try:
            with tempfile.TemporaryDirectory(prefix="zpf-frame-") as tmp:
                shot = clip_edit.extract_frame(target, at, Path(tmp) / "frame.jpg")
                frame_url = fal.as_image_url(shot.read_bytes(), account_id=account_id)
        except ValueError as e:
            return {"ok": False, "error": str(e), "quote": quote}
        if not frame_url:
            return {"ok": False, "quote": quote,
                    "error": "the frame could not be made fetchable for the renderer "
                             "(the studio's bucket is not configured)"}
        res = effects.run(
            clip_edit.FRAME_EFFECT, [frame_url], clip_edit.frame_prompt(instruction),
            effects.check_options(clip_edit.FRAME_EFFECT, {}), usd=usd, sources=[source],
            account_id=account_id, db_path=dsn, source="mcp", project_id=project_id,
            quote=approved,
            extra={"edit_clip": {"stage": "frame", "source": source,
                                 "instruction": instruction, "at": at}})
        if res.get("ok") and res.get("asset_id"):
            made = f"gen:{res['asset_id']}"
            res = {**res, "frame": made,
                   "next": (f"Show the person this edited frame ({made}). If they approve it, "
                            f"call edit_clip again with stage=\"video\", frame=\"{made}\" and "
                            "the same source and instruction; that call quotes the whole clip.")}
        return {**res, "quote": quote}

    model = (model or "").strip() or clip_edit.DEFAULT_MODEL
    m = clip_edit.spec(model)
    _approved_frame(frame, source, instruction, dsn, account_id)
    frame = frame.strip()
    urls, probe = _video_sources([source], dsn, account_id)
    clip_edit.check_clip(model, probe, suffix=suffix, size_bytes=size)
    frame_url = None
    if m["frame"]:
        (frame_url,) = resolve_references([frame], limit=1, who=m["label"], dsn=dsn,
                                          account_id=account_id)
    usd = clip_edit.video_usd(model, probe)
    quote = {"stage": "video", "source": source, "instruction": instruction, "frame": frame,
             "model": model, "label": m["label"], "frame_steers": bool(m["frame"]),
             **({"keep_audio": bool(keep_audio)} if m["audio"] else {}),
             "usd": usd, "source_clip": probe, **filed}
    stop, approved, price = approval_gate(
        usd, quote_token, tool="edit_clip", what=f"Editing this clip on {m['label']}",
        args={"stage": "video", "source": source, "instruction": instruction, "frame": frame,
              "model": model, "keep_audio": bool(keep_audio) if m["audio"] else None,
              "project_id": _project_arg(project_id)},
        account_id=account_id, dsn=dsn)
    quote.update(price)
    if stop is not None:
        return {**stop, "quote": quote}
    if dry_run:
        return {"ok": True, "dry_run": True, "quote": quote, "approved": approved}
    res = effects.run(
        f"edit-{model}", urls, instruction, {}, usd=usd, sources=[source, frame], probe=probe,
        account_id=account_id, db_path=dsn, source="mcp", project_id=project_id,
        quote=approved, row={"label": m["label"], "output": "video"},
        endpoint_body=clip_edit.video_body(model, urls[0], instruction, frame_url=frame_url,
                                           keep_audio=keep_audio),
        extra={"edit_clip": {"stage": "video", "source": source, "frame": frame,
                             "instruction": instruction, "model": model}})
    return {**res, "quote": quote}


def list_renders(kind: Optional[str] = None, limit: int = 20, dsn: Optional[str] = None,
                 account_id: Optional[int] = None) -> dict[str, Any]:
    """This account's recent renders on the Assets wall, newest first, as
    the `gen:<id>` a reference or an effect source names. Read-only."""
    from . import media, render_assets
    kind = (kind or "").strip()
    if kind and kind not in ("image", "video", "audio", "upload"):
        raise ValueError("kind is image, video, audio, upload or empty for images and videos")
    cap = max(1, min(int(limit or 20), 100))
    account_id = _account(account_id, dsn)
    if kind in ("audio", "upload"):
        return _uploads(cap, dsn, account_id,
                        kinds=("audio",) if kind == "audio" else ("image", "video", "audio"))
    out = []
    for r in render_assets.list_all(dsn, account_id=account_id):
        if kind and r.get("media_kind") != kind:
            continue
        url = r.get("media_url") or ""
        try:                      # what a viewer can open, minted on read
            url = media.url_for(url, account_id) if url else url
        except Exception:
            pass
        out.append({"id": f"gen:{r['id']}", "kind": r.get("media_kind"),
                    "model": r.get("model"), "provider": r.get("provider"),
                    "prompt": (r.get("prompt") or "")[:160],
                    "media_url": url,
                    "created_at": str(r.get("created_at") or "")})
        if len(out) >= cap:
            break
    return {"count": len(out), "renders": out,
            "note": "" if out else "no renders yet -- generate_image makes the first"}


# --- projects: make one, reopen one (2026-10-08) -----------------------------
#
# Mike's ask: make projects from Claude, revisit the ones made in the
# studio, and pull the reference images and the chat a project already
# has. All of it reads and writes `src/projects.py` -- the SAME rows the
# studio's projects board and workspace draw -- so a project started here
# is on the board, and one started there opens here with its history.

CHAT_PREVIEW = 12        # turns `project` carries; `project_chat` pages the rest
CHAT_PREVIEW_MAX = 40
CHAT_EXCERPT = 1500      # characters of one turn in the preview
PROJECT_REFS_MAX = 60    # reference images listed on `project`
PROJECT_RENDERS_MAX = 50
PROJECT_MEMORY = 20      # newest lessons shown
PROJECT_SCENES_MAX = 50  # newest scenes shown on `project`
CHAT_PAGE_CHARS = 200_000  # words one `project_chat` page carries at most


def _project_or_refuse(project_id, dsn, account_id) -> dict:
    """The caller's project, or ValueError -- someone else's id reads
    exactly like one that does not exist."""
    from . import projects
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        raise ValueError(f"project_id must be a number from `projects`, got {project_id!r}")
    found = projects.get(pid, dsn, account_id=account_id)
    if not found:
        raise ValueError(f"no project {pid} -- ids come from `projects`")
    return found


def _filed_under(project_id, dsn, account_id) -> dict:
    """The quote's `project` entry, checked before any price is shown, or
    nothing when no project was named."""
    if project_id in (None, "", 0):
        return {}
    found = _project_or_refuse(project_id, dsn, account_id)
    return {"project": {"id": found["id"], "title": found["title"]}}


def _view(url: Optional[str], account_id) -> Optional[str]:
    """A stored media string as something a person can open, minted on read."""
    from . import media
    if not url:
        return None
    try:
        return media.url_for(str(url), account_id)
    except Exception:
        return str(url)


def _turn(message: dict, excerpt: Optional[int] = None) -> dict[str, Any]:
    content = message.get("content") or ""
    out = {"id": message["id"], "role": message["role"],
           "at": message.get("created_at"),
           "content": content if excerpt is None else content[:excerpt]}
    if excerpt is not None and len(content) > excerpt:
        out["truncated"] = True
    extras = dict(message.get("tool_calls") or {}) if isinstance(
        message.get("tool_calls"), dict) else {}
    if extras.get("via"):
        out["via"] = extras.pop("via")           # saved from here, not the studio
    if extras:
        out["carried"] = sorted(extras)          # what the studio drew beside it
    return out


def list_project_cards(include_archived: bool = False, limit: int = LIST_LIMIT,
                       dsn: Optional[str] = None,
                       account_id: Optional[int] = None) -> dict[str, Any]:
    """The account's projects, newest-touched first -- the projects board."""
    from . import projects
    account_id = _account(account_id, dsn)
    cap = max(1, min(int(limit or LIST_LIMIT), 100))
    rows = projects.list_projects(dsn, account_id=account_id,
                                  include_archived=bool(include_archived))
    cards = [{"id": p["id"], "title": p["title"],
              "brief": " ".join((p.get("brief") or "").split())[:200],
              "has_look": bool((p.get("look") or "").strip()),
              "scenes": int(p.get("concepts") or 0),
              "rendered": int(p.get("rendered") or 0),
              "archived": bool(p.get("archived")),
              "updated_at": p.get("updated_at"),
              "cover": _view(p.get("cover"), account_id)}
             for p in rows[:cap]]
    return {"count": len(cards), "projects": cards,
            **_truncation(rows, cap, "raise `limit`"),
            **({} if cards else {"note": "no projects yet -- `create_project` starts one"})}


def get_project(project_id: int, chat_turns: int = CHAT_PREVIEW,
                dsn: Optional[str] = None,
                account_id: Optional[int] = None) -> dict[str, Any]:
    """One project as a person reopening it needs it: the brief and look,
    what it learned, its scenes, the reference images they used (as refs
    the render tools take back), its renders and the latest chat."""
    from . import asset_shelf, projects, render_assets
    account_id = _account(account_id, dsn)
    project = _project_or_refuse(project_id, dsn, account_id)
    pid = project["id"]

    concepts = preprod.list_concepts(limit=200, dsn=dsn, account_id=account_id,
                                     project_id=pid)
    scenes = []
    for c in concepts[:PROJECT_SCENES_MAX]:
        shot = (c.get("shots") or [{}])[0] or {}
        scenes.append({**_card(c),
                       "prompt": (shot.get("prompt") or "")[:400],
                       "still": _view(shot.get("reference_image"), account_id),
                       "clip": _view(shot.get("media_url"), account_id)})

    refs = _project_refs(dsn, account_id, pid)
    sources = scout.sources_for_refs(
        [r["ref"].split("?", 1)[0].rsplit("/", 1)[-1] for r in refs], dsn=dsn)
    references = []
    for r in refs[:PROJECT_REFS_MAX]:
        parsed = asset_shelf.parse_ref(r["ref"]) or {}
        src = sources.get(r["ref"].split("?", 1)[0].rsplit("/", 1)[-1]) or {}
        page = src.get("source_url") or ""
        references.append({
            "ref": r["ref"], "kind": parsed.get("kind") or "",
            "label": src.get("title") or parsed.get("filename")
            or r["ref"].rsplit("/", 1)[-1],
            "url": _view(r["ref"], account_id),
            "page": page if page.startswith(("http://", "https://")) else None,
            "scenes": r["concept_ids"]})

    in_scenes = {c["id"] for c in concepts}
    renders = []
    for row in render_assets.list_all(dsn, account_id=account_id):
        meta = row.get("metadata") or {}
        if row.get("concept_id") not in in_scenes and meta.get("project_id") != pid:
            continue
        renders.append({"id": f"gen:{row['id']}", "kind": row.get("media_kind"),
                        "model": row.get("model"),
                        "prompt": (row.get("prompt") or "")[:160],
                        "scene": row.get("concept_id"),
                        "media_url": _view(row.get("media_url"), account_id)})
        if len(renders) >= PROJECT_RENDERS_MAX:
            break

    turns = max(0, min(int(chat_turns if chat_turns is not None else CHAT_PREVIEW),
                       CHAT_PREVIEW_MAX))
    chat = (projects.messages(pid, dsn, account_id=account_id, limit=turns)
            if turns else {"items": [], "has_more": bool(
                projects.messages(pid, dsn, account_id=account_id, limit=1)["items"])})

    return {"id": pid, "title": project["title"],
            "brief": project.get("brief") or "",
            "look": project.get("look") or "",
            "archived": bool(project.get("archived")),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at"),
            "learned": (project.get("memory") or [])[-PROJECT_MEMORY:],
            "scenes": scenes,
            "scenes_truncated": len(concepts) > PROJECT_SCENES_MAX,
            "references": references,
            "references_truncated": len(refs) > PROJECT_REFS_MAX,
            "renders": renders,
            "chat": [_turn(m, CHAT_EXCERPT) for m in chat["items"]],
            "chat_has_more": bool(chat["has_more"]),
            "next": ("a reference's `ref` or a render's `gen:<id>` goes wherever "
                     f"a tool takes a reference, and project_id={pid} files new "
                     "work under this project where a tool takes it; "
                     "`save_chat` keeps this conversation with it; "
                     "`project_chat` pages back through its history")}


def project_history(project_id: int, before: Optional[int] = None,
                    limit: int = 40, dsn: Optional[str] = None,
                    account_id: Optional[int] = None) -> dict[str, Any]:
    """The project's chat, a page at a time, full turns."""
    from . import projects
    account_id = _account(account_id, dsn)
    project = _project_or_refuse(project_id, dsn, account_id)
    page = projects.messages(project["id"], dsn, account_id=account_id,
                             limit=max(1, min(int(limit or 40), 200)),
                             before=int(before) if before is not None else None)
    # newest first until the page is full: a reply a client can still
    # carry, the oldest turns of an over-long page left for the next one
    kept, size = [], 0
    for m in reversed(page["items"]):
        size += len(m.get("content") or "")
        if kept and size > CHAT_PAGE_CHARS:
            break
        kept.append(m)
    items = [_turn(m) for m in reversed(kept)]
    more = bool(page["has_more"]) or len(kept) < len(page["items"])
    return {"project_id": project["id"], "title": project["title"],
            "count": len(items), "turns": items, "has_more": more,
            **({"next_before": items[0]["id"]} if more and items else {}),
            **({} if items else {"note": "no chat in this project yet"})}


class ChatTurn(TypedDict):
    """One turn `save_chat` files: who said it and what was said."""
    role: Literal["user", "assistant"]
    content: str


def save_project_chat(project_id: int, turns: Optional[list] = None,
                      dsn: Optional[str] = None,
                      account_id: Optional[int] = None) -> dict[str, Any]:
    """This conversation into the project's history (2026-10-08, Mike's
    ask), marked `via: mcp`, de-duplicated against the history's tail by
    `projects.append_turns`. Spends nothing; a person's own project only."""
    from . import projects
    account_id = _account(account_id, dsn)
    project = _project_or_refuse(project_id, dsn, account_id)
    if not turns:
        raise ValueError("no turns to save -- pass the conversation as "
                         "[{role: user|assistant, content}]")
    done = projects.append_turns(project["id"], [dict(t) for t in turns], dsn,
                                 account_id=account_id, via="mcp")
    return {"project_id": project["id"], "title": project["title"], **done,
            "note": ("saved; reopening the project here or in the studio shows it"
                     if done["saved"] else "nothing new to save -- the history "
                     "already ends with these turns")}


def make_project(title: str, brief: str = "", look: str = "",
                 dsn: Optional[str] = None,
                 account_id: Optional[int] = None) -> dict[str, Any]:
    """A new project on the account's projects board. Spends nothing."""
    from . import projects
    account_id = _account(account_id, dsn)
    title = " ".join((title or "").split())
    if not title:
        raise ValueError("a project needs a name")
    if len((look or "").strip()) > projects.LOOK_MAX:
        raise ValueError(f"the look is at most {projects.LOOK_MAX} characters")
    made = projects.create(title, brief, dsn, account_id=account_id, look=look)
    return {"id": made["id"], "title": made["title"], "brief": made.get("brief") or "",
            "look": made.get("look") or "",
            "next": (f"project_id={made['id']} files work under it where a tool "
                     "takes one; `save_chat` keeps this conversation with it")}


# --- the spark bank: plain functions, no longer tools ----------------------
#
# `add_spark`, `tonight`, `sparks`, `images`, `reference` and
# `imagine_reference` were tools on the board surface until 2026-10-11.
# The functions stay because `ops/bank.py` banks through `bank_spark` and
# `bank_reference`, and because whether the spark bank and the scout go
# altogether is step 9 of docs/tasks/task-higgsfield-shape.md -- Mike's
# call, not made yet. `find_images` is still a tool (`images_for`, on the
# studio surface).

def bank_spark(
    brand: str,
    spark: str,
    rationale: str = "",
    evidence: str = "",
    score: float = HUMAN_SPARK_SCORE,
    dsn: Optional[str] = None,
) -> dict[str, Any]:
    """Hand the nightly run a direction, in the scout's own bank.

    Banked rather than written to prompts/sparks.txt because the bank is
    what `--scout` actually reads, and because a banked finding is
    claimed exactly once (`mark_used`) -- so a spark typed twice by
    accident cannot fire two of the night's 16 runs.

    A colliding spark is reported, not refused. `_spark_key` exists to
    stop the CRAWL rediscovering its own findings; a person retyping a
    direction usually means it.
    """
    _check(brand, scout.BRANDS, "brand")
    spark = " ".join((spark or "").split())
    if not spark:
        raise ValueError("spark is empty")

    key = scout._spark_key(spark)
    clashes = [
        row["id"]
        for row in scout.list_findings(brand=brand, dsn=dsn)
        if row.get("spark_key") == key
    ]
    finding_id = scout.record(
        brand,
        {"spark": spark, "rationale": rationale, "evidence": evidence,
         "sources": [], "score": float(score)},
        lanes="human",
        dsn=dsn,
    )
    return {"id": finding_id, "brand": brand, "spark": spark,
            "score": float(score), "lanes": "human",
            "duplicate_of": clashes,
            "serves_next": float(score) >= scout.SCORE_FLOOR}


def next_spark(brand: str, dsn: Optional[str] = None) -> dict[str, Any]:
    """What tonight's `--scout` run would take: the highest-scoring
    unused finding at or above the floor. None means it falls back to
    the `prompts/sparks.txt` rotation, which is the healthy degraded
    path, not an error."""
    _check(brand, scout.BRANDS, "brand")
    row = scout.next_spark(brand, dsn=dsn)
    if row is None:
        return {"brand": brand, "spark": None,
                "note": f"nothing unused at or above the {scout.SCORE_FLOOR} "
                        "floor -- tonight falls back to sparks.txt"}
    return {"brand": brand, "id": row["id"], "spark": row["spark"],
            "score": row.get("score"), "rationale": row.get("rationale") or "",
            "evidence": row.get("evidence") or "", "lanes": row.get("lanes") or ""}


def list_sparks(brand: Optional[str] = None, unused_only: bool = True,
                limit: int = 20, dsn: Optional[str] = None) -> dict[str, Any]:
    """The scout's bank, highest-scoring first."""
    if brand:
        _check(brand, scout.BRANDS, "brand")
    rows = scout.list_findings(brand=brand, unused_only=unused_only,
                               limit=max(1, min(int(limit), 100)), dsn=dsn)
    return {
        "brand": brand or "all",
        "unused_only": unused_only,
        "count": len(rows),
        "sparks": [
            {"id": r["id"], "brand": r["brand"], "spark": r["spark"],
             "score": r.get("score"), "lanes": r.get("lanes") or "",
             "used_at": r.get("used_at"),
             "rationale": r.get("rationale") or ""}
            for r in rows
        ],
    }


# --- the research bin ------------------------------------------------------

def _reachable(url: str) -> bool:
    """Does this page actually exist? A HEAD, five seconds, fail-open on
    anything that is not a definite 4xx.

    Fail-open because the job here is catching FABRICATION, not policing
    the web: a timeout or a bot-wall is not evidence the page is fake,
    and refusing on one would make the bank hostage to a flaky network.
    A 404 is evidence.
    """
    import requests
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        if resp.status_code == 405:              # HEAD not allowed; try GET
            resp = requests.get(url, timeout=5, stream=True)
        return not (400 <= resp.status_code < 500)
    except Exception:
        return True


def _store_local(path_str: str) -> Optional[str]:
    """A frame off his own disk into the bin, through refbin's own
    normalisation so it is addressed exactly like every other reference
    and resolves through the same reader."""
    try:
        data = Path(path_str).read_bytes()
    except OSError:
        return None
    jpeg = refbin.to_jpeg(data)
    return refbin.save(jpeg) if jpeg else None


def find_images(
    query: str,
    brand: str = "",
    limit: int = 6,
    dsn: Optional[str] = None,
) -> dict[str, Any]:
    """Look for reference images, and hand back ids -- never URLs.

    THE OMITTED FIELD IS THE FEATURE. On 2026-09-02 an agent with no
    image search banked eleven references by writing stock URLs from
    memory; the CDNs served *something* for every guess, so a sunny tree
    was banked as "bark texture" and six of the source pages 404. It was
    not lying, it was recalling -- and no prompt fixes recall.

    So the candidate keeps the URL and the caller only ever holds an
    `id`. There is no address here to invent, and `bank_reference`
    accepts an id that this function issued or nothing at all.
    """
    found = imagesearch.search(query, brand=brand or None,
                               limit=max(1, min(int(limit), 12)), dsn=dsn)
    live = imagesearch.sources()
    return {
        "query": " ".join((query or "").split()),
        "sources": live,
        "count": len(found),
        # "no lane is configured" and "nothing matched" are different
        # problems with the same empty list, and the second one wasted
        # two days when the scout bin was silently unfillable.
        "note": ("" if found else
                 ("no image source is configured — Openverse is off "
                  "(OPENVERSE_LANE=0) and no GOOGLE_CSE_ID / REDDIT_CLIENT_ID / "
                  "UNSPLASH_ACCESS_KEY / PEXELS_API_KEY is set"
                  if not imagesearch.any_web(live)
                  else "nothing matched; try plainer words for the light and "
                       "the surfaces rather than the story")),
        "images": [{"id": c["id"], "shows": c.get("title") or "(no description)",
                    "source": c["source"], "credit": c.get("credit") or ""}
                   for c in found],
    }


def bank_reference(
    finding_id: int,
    image_url: str = "",
    source_url: str = "",
    title: str = "",
    candidate_id: str = "",
    dsn: Optional[str] = None,
) -> dict[str, Any]:
    """Put ONE reference image behind a banked spark.

    The gap this closes: bank_spark hands the nightly run a direction
    but no photographs, and the only thing that ever wrote to the bin
    was the crawl -- so on a night the crawl found no images (or failed
    on DNS, which is what happened 2026-09-01) an agent could give the
    graph an idea and not one frame to render it against.

    THE FETCH HAPPENS HERE, SERVER-SIDE, ON PURPOSE. The caller hands
    over a URL, not bytes: refbin.fetch is what enforces the public-host
    guard, the 8MB cap, the JPEG normalisation and the content-addressed
    /refs/<sha>.jpg name. An agent chose this URL after reading some
    page, which makes it exactly the input those guards exist for --
    passing bytes straight through would put the decision in the
    client's hands and the request on this machine's network.

    `source_url` is REQUIRED, not decoration. These are other people's
    frames held as mood reference, and an unattributed one in front of
    somebody about to spend a render is the wrong affordance --
    spark_images returns it on every tile for the same reason.

    Capped at MAX_BIN_IMAGES per pass, same as the crawl: a bin bigger
    than one generation carries has a tail that can never be used.

    TWO WAYS IN, AND ONLY ONE OF THEM IS FOR AGENTS.

    `candidate_id` redeems something `find_images` served: the URL and
    the attribution come out of the row WE wrote, so neither can be
    invented. That is the path the research agent takes.

    A bare `image_url` is the composer's path -- a photo Michael dragged
    on, where a person vouched for it. Left open for that reason, but it
    now has to survive `_reachable(source_url)`: on 2026-09-02 six of
    eleven agent-banked references cited Unsplash pages that 404, and
    nothing had ever resolved one. A HEAD request would have caught
    every one.
    """
    # strict: a database that could not be asked must not come back as
    # "this spark does not exist" -- the agent's only move on that answer
    # is to give up on the images, which is what happened on 2026-09-07.
    try:
        finding = scout.get_finding(int(finding_id), dsn=dsn, strict=True)
    except scout.Unreadable as e:
        raise Refused(str(e)) from e
    if finding is None:
        raise ValueError(f"no finding {finding_id}")

    local_path = ""
    if candidate_id:
        candidate = imagesearch.get(candidate_id, dsn=dsn)
        if candidate is None:
            # An id nobody issued is what a guess looks like now, and it
            # has to say so rather than falling through to a fetch.
            raise ValueError(
                f"no candidate {candidate_id!r} — ids come from find_images "
                f"and cannot be composed; search again and pick one")
        image_url = candidate["image_url"]
        source_url = candidate["source_url"]
        title = title or candidate.get("title") or ""
        if candidate["source"] == "frames":
            # His own footage never leaves this machine, so there is no
            # URL to fetch and no host to guard -- the "url" is a path.
            local_path, image_url = candidate["image_url"], ""
    elif not (image_url or "").strip():
        raise ValueError("give either a candidate_id from find_images or an "
                         "image_url")

    if not (source_url or "").strip():
        raise ValueError("source_url is required — an unattributed reference "
                         "is the wrong thing to put in front of a spend")
    if not candidate_id and not _reachable(source_url):
        raise ValueError(f"source_url {source_url!r} does not resolve — an "
                         f"attribution nobody can check is worse than none")


    # The fetch-and-bank tail is scout's, shared with the automatic
    # backstop (`scout.illustrate`). Everything above this line is what
    # is specific to an AGENT asking: the id has to have been issued, and
    # the attribution has to resolve.
    result = scout.bank_candidate(
        finding,
        {"image_url": local_path or image_url,
         "source_url": source_url, "title": title,
         "source": "frames" if local_path else "", "lane": "agent"},
        dsn=dsn)
    result.setdefault("finding_id", finding["id"])
    return result


def spark_images(finding_id: int, dsn: Optional[str] = None) -> dict[str, Any]:
    """The reference images the scout downloaded on the pass this spark
    came out of.

    The scout already fetched and normalised these into data/refs during
    its pass, addressed as `/refs/<sha>.jpg` -- the same URL shape a
    composer upload gets, which is why they can ride the existing path
    into a keyframe with no new route. Nothing is downloaded here;
    this reads the bank.

    `source_url` is returned on every tile and is not optional
    decoration: these are other people's frames held as mood reference,
    and an unattributed one in front of somebody about to spend a render
    is the wrong affordance.
    """
    if scout.get_finding(int(finding_id), dsn=dsn) is None:
        raise ValueError(f"no finding {finding_id}")
    rows = scout.bin_for_finding(int(finding_id), dsn=dsn)
    return {
        "finding_id": int(finding_id),
        "count": len(rows),
        "images": [
            {"url": r["url"], "source_url": r.get("source_url") or "",
             "title": r.get("title") or "", "lane": r.get("lane") or "",
             "metric": r.get("metric") or ""}
            for r in rows
        ],
    }


# --- the engine: plain functions, no longer tools --------------------------
#
# `research` (a scout pass) and `generate` (one run of the graph, ending
# parked) were tools on the board surface under ZEROPAGE_MCP_ENGINE=1 until
# 2026-10-11. With that surface gone nothing registers them: the scout runs
# from `python -m src.scout run` and the graph from `python -m src.trigger`,
# by hand. The functions and the flag's name stay until step 9 of
# docs/tasks/task-higgsfield-shape.md decides the scout's fate; the flag no
# longer turns anything on.

ENGINE_ENV = "ZEROPAGE_MCP_ENGINE"
# Every lane the scout can dispatch -- ITS list, never a copy: this one had
# drifted (still naming `feeds` as a default, missing `pinterest`) and, as
# the tool's default, ran Instagram for every caller. The default is now
# scout.default_lanes(<the caller's account>).
LANES = scout.KNOWN_LANES


def engine_enabled() -> bool:
    return os.environ.get(ENGINE_ENV) == "1"


def _create_gate(account_id: Optional[int], dsn=None) -> None:
    """research and generate spend Gemini money for their caller, so they
    ask the same question Studio's Create does (charge.create_refusal,
    2026-09-29): an account with no plan and no credit balance is Refused
    -- a deliberate no, so an agent stops rather than retrying. The
    operator's key resolves to an exempt account and is never refused."""
    from . import charge
    reason = charge.create_refusal(_account(account_id, dsn), dsn=dsn)
    if reason:
        raise Refused(reason)


def run_research(brand: str, count: int = 4, lanes=None,
                 dsn: Optional[str] = None,
                 account_id: Optional[int] = None) -> dict[str, Any]:
    """One full scout pass: crawl the lanes, digest to scored sparks,
    bank them, and stash the images behind them.

    Returns the banked findings rather than the crawl. The digest step
    exists precisely so raw crawl text never reaches a generator, and
    handing it to an agent instead would just move that mistake one
    layer out.
    """
    _check(brand, scout.BRANDS, "brand")
    _create_gate(account_id, dsn)
    lanes = tuple(lanes) if lanes else scout.default_lanes(_account(account_id, dsn), dsn=dsn)
    unknown = [lane for lane in lanes if lane not in LANES]
    if unknown:
        raise ValueError(f"unknown lanes {unknown}; known: {list(LANES)}")

    result = scout.scout(brand=brand, count=max(1, min(int(count), 8)),
                         lanes=lanes, dsn=dsn, account_id=_account(account_id, dsn))
    return {
        "ok": result["ok"],
        "brand": brand,
        "signals": result.get("signals", 0),
        "images": len(result.get("bin") or []),
        # Errors are returned, never swallowed: a crawl that quietly
        # finds nothing looks exactly like a healthy one, which is the
        # failure mode that hid the dead launchd job for eleven nights.
        "errors": result.get("errors") or [],
        "findings": [
            {"id": f.get("id"), "spark": f.get("spark"),
             "score": f.get("score"), "rationale": f.get("rationale") or ""}
            for f in result.get("findings") or []
        ],
    }


def resolve_finding(spark: str, brand: str, finding_id: Optional[int] = None,
                    dsn: Optional[str] = None) -> tuple[str, str, Optional[dict]]:
    """Which banked finding, if any, a generate call is running FROM --
    and therefore whose reference images ride along.

    The server decides, the same way /api/scenes/run decides for the
    composer: a client-side id is exactly what goes stale. Three cases.
    An explicit `finding_id` with no spark runs that finding's spark. An
    explicit id WITH a spark must be that finding's spark (on
    `_spark_key`, so fixed capitals still match) -- a reworded direction
    anchored on a stranger's thumbnail is not the caller's direction, and
    rather than silently drop the photos the way the composer does, this
    door says so, because an agent can act on a message and a person
    can see a tile. No id: the spark text is looked up, so `add_spark`
    -> `reference` -> `generate(spark)` finds its own photographs
    without the agent having to carry an id between calls.

    Returns (spark, brand, finding-or-None). Never spends.
    """
    spark = " ".join((spark or "").split())
    finding = None
    if finding_id is not None:
        try:
            finding = scout.get_finding(int(finding_id), dsn=dsn, strict=True)
        except scout.Unreadable as e:
            raise Refused(str(e)) from e
        if finding is None:
            raise ValueError(f"no finding {finding_id}")
        if spark and not scout.claims(finding["id"], spark, dsn=dsn):
            raise ValueError(
                f"spark {spark!r} is not finding {finding['id']}'s spark "
                f"({finding['spark']!r}). Run the finding's own spark, or omit "
                "finding_id to run a direction of your own -- its references "
                "belong to the direction they were banked behind.")
        spark = spark or " ".join((finding.get("spark") or "").split())
        brand = brand or finding["brand"]
        if brand != finding["brand"]:
            raise ValueError(f"finding {finding['id']} was banked for "
                             f"{finding['brand']!r}, not {brand!r}")
    elif spark and brand:
        finding = scout.find_by_spark(brand, spark, dsn=dsn)
    return spark, brand, finding


def run_graph(spark: str = "", brand: str = "", goal: str = "",
              channel: str = "", finding_id: Optional[int] = None,
              account_id: Optional[int] = None,
) -> dict[str, Any]:
    """One pass through the LangGraph content graph: ground, generate,
    evaluate, retry, score the prompt, keyframe if it clears the gate,
    and park in the Queue.

    Parking IS the terminal state, and that is the point -- the graph
    ends at the spend gate rather than through it, so an agent can drive
    concept generation end to end without being able to buy anything.

    THE REFERENCES COME FROM THE SPARK'S BIN (2026-09-03). This call
    used to take a spark string and nothing else, and `orchestrator.run`
    with an explicit spark never reads the bin (the scout node acts only
    when asked to CHOOSE the direction) -- so an agent could bank six
    photographs behind a spark with `reference` and then generate from
    that spark with none of them. Now `resolve_finding` names the
    finding, its bin becomes `reference_photos`, and the id rides the
    run so `planner` claims the finding and the hold card says where
    the idea came from. Same rule as the composer: the photos behind a
    direction ride with THAT direction, never a reworded one.

    Refuses outright when ZEROPAGE_RENDER=1. That flag turns
    `generate_render` from a dry stub into real Veo spend, and the one
    thing this surface must never be is the caller that trips it.

    `finding_id` closes a gap the composer already closed for itself
    (`/api/scenes/run`'s `scout_finding_id`): a spark run straight
    through here -- Mike pasting a banked spark's text into `generate`,
    or an agent firing on one it read from `sparks`/`tonight` -- never
    claimed the bank row, because `orchestrator.planner` only stamps
    `used_at` when its OWN `scout` node pulled the finding
    (state["scout"]=True, the nightly path only). A finding that sits
    unused at its original score is what the next `next_spark` call, or
    tonight's batch, hands back out as a "new" direction -- the same
    idea generated twice. Same guard as the composer's: `scout.claims()`
    checks the text still matches this finding (a stale id is not
    silently trusted), and the claim lands only once a concept actually
    exists, so a run that errored or held burns nothing.
    """
    account_id = _account(account_id, None)      # None: DATABASE_URL, read at call time
    if os.environ.get("ZEROPAGE_RENDER") == "1":
        raise Refused(
            "refusing: ZEROPAGE_RENDER=1 makes the graph spend render "
            "credit, and this surface is not allowed to be what trips "
            "it. Run the graph on the machine, or unset the flag."
        )
    _create_gate(account_id)
    # DATABASE_URL read at CALL time, like _account above: a default bound
    # at import is the path the process started with, not the one a
    # test (or a later reconfiguration) points the module at.
    spark, brand, finding = resolve_finding(spark, brand, finding_id)
    _check(brand, preprod.BRANDS, "brand")
    if not spark:
        raise ValueError("spark is empty")
    photos = [b["url"] for b in scout.bin_for_finding(finding["id"])
              if b.get("url")] if finding else []

    from . import orchestrator

    state = orchestrator.run(goal or spark, brand=brand, spark=spark,
                             channel=channel or brand, account_id=account_id,
                             reference_photos=photos,
                             scout_finding_id=finding["id"] if finding else None)
    concept_id = state.get("concept_id")
    claimed = bool(finding_id) and scout.claims(finding_id, spark)
    if claimed and concept_id:
        scout.mark_used(finding_id, run_id=f"concept:{concept_id}")
    out = {
        "concept_id": concept_id,
        "brand": brand,
        "spark": spark,
        "finding_id": finding["id"] if finding else None,
        "reference_photos": photos,
        "attempts": state.get("attempts"),
        "held_reason": state.get("held_reason") or "",
        "parked_reason": state.get("parked_reason") or "",
        "finding_claimed": bool(claimed and concept_id),
        "keyframes": [
            {"n": k.get("n"), "ok": k.get("ok"), "url": k.get("url") or "",
             "error": k.get("error") or ""}
            for k in state.get("keyframes") or []
        ],
        "prompt_scores": [
            {"score": p.get("score"), "pass": p.get("pass"),
             "reason": p.get("reason") or ""}
            for p in state.get("prompt_scores") or []
        ],
        "error": state.get("error"),
    }
    if concept_id:
        concept = preprod.get_concept(concept_id, account_id=account_id)
        out["idea"] = _card(concept)
        # The verdict rides back with the run rather than waiting for a
        # second call: a held run's whole point is the reason it held.
        out["idea"].update(_gate(concept, None, account_id))
    return out


# --- the server ------------------------------------------------------------

# Written against the INSTALLED mcp SDK, 2.1.1 (2026-08-31). v2 renamed
# FastMCP to MCPServer and moved `stateless_http` from the constructor
# onto `streamable_http_app()`; code written for mcp 1.x imports a
# module that no longer exists. requirements.txt pins mcp>=2 for that
# reason -- verify this import on a major bump, the same rule veo.py
# carries for google-genai.

def _structured(name: str, fn):
    """The studio surface's registration of a tool (2026-10-09,
    task-mcp-studio-v2 step 7): the same function, answering with a
    CallToolResult -- a short human line as text and the payload as
    structuredContent -- and declaring `Annotated[CallToolResult,
    mcp_shapes.SHAPES[name]]`, from which the SDK publishes the tool's
    outputSchema and against which it validates every answer.

    A wrapper with its own `__signature__` (the arguments exactly as the
    tool declares them, evaluated; only the return type swapped) rather
    than a second copy of every tool, so a typed tool cannot drift from
    the function it wraps."""
    import inspect
    from typing import Annotated

    from mcp.types import CallToolResult

    from . import mcp_shapes
    sig = inspect.signature(fn, eval_str=True)

    def typed(**kwargs):
        out = fn(**kwargs)
        return mcp_shapes.result(name, out) if isinstance(out, dict) else out

    typed.__name__ = typed.__qualname__ = fn.__name__
    typed.__doc__ = fn.__doc__
    typed.__signature__ = sig.replace(
        return_annotation=Annotated[CallToolResult, mcp_shapes.SHAPES[name]])
    return typed


def build_server(dsn: Optional[str] = None, name: str = "zeropage-studio",
                 start_job=None, job_status=None, account_id: Optional[int] = None,
                 engine: Optional[bool] = None, listed=False,
                 approve_render=None, approve_keyframes=None,
                 surface: str = "studio", cancel_job=None,
                 local_files: bool = True, create_element=None):
    """Wrap the functions above as an MCP server -- one of two.

    `surface="studio"` (the default, and the only surface) is what Claude
    Desktop launches and what the operator's static key reaches over HTTP:
    STUDIO_TOOLS -- the models, the elements and renders a reference can
    name, a prompt helper, projects, and the spending doors (image, video,
    effect, sheet, clip edit), each quoted in chat and run only after a
    yes. Every answer is typed (`_structured`).

    `listed=True` registers LISTED_TOOLS instead -- what a signed-in
    stranger reaches through the directory listing: projects, elements,
    write_scene / quote / approve, and ONE of the studio's spending doors,
    `generate_image` (2026-10-11), behind the same quote. `listed="claude"`
    is the Claude directory's set: nothing that renders or draws.
    The mount builds one of each and routes by door.

    `create_element` is app/api.py's element-create body behind the
    mount's adapter (app/mcp_mount.connector_element), injected for the
    reason the approve bodies are. `add_element` is registered either way
    and says so when a server was built without one.

    There was a third, "board" surface until 2026-10-11
    (docs/tasks/task-higgsfield-shape.md): the idea board's tools, the
    spark bank's and the two engine tools. It is gone, and `surface`
    refuses any name but "studio".

    `approve_render` / `approve_keyframes` are app/api.py's priced approve
    bodies, injected like `start_job` because src/ never imports app/.
    The `approve` tool registers only when both are given; a listed server
    without them (a test) has `quote` and no way to spend.

    `account_id` is whose rows this server reads. None keeps the
    transport's answer (`_account`: a signed-in caller's own account, else
    the bootstrap account behind the operator's key).

    `engine` is accepted and ignored: it gated the board surface's
    spending and engine tools, and callers still pass it.

    `local_files=False` leaves `import_file` off the studio surface. That
    tool reads the disk of the machine the server runs on, which is the
    person's own computer over stdio and the web server's over HTTP -- so
    the HTTP mount builds without it, as it always was unreachable there.

    `mcp` is imported lazily so it stays an optional dependency: the
    tool surface is testable, and the pipeline runs, on a machine that
    never installed it.

    `start_job`/`job_status` are the app-layer capability src/ cannot
    reach -- `app/jobs.py` is a thread registry that belongs to the web
    process -- so they are INJECTED as callables, the same way
    `scene_chain` takes the two capabilities it needs from app/. Without
    them a spending tool still registers, but runs inline; that is fine
    for a CLI or a test and wrong for HTTP, where a render would sit on
    an open request until something times out.

    Each tool is registered explicitly rather than in a loop, because the
    SDK publishes a tool's signature to the model -- and a loop would
    publish `dsn` as an argument, which is a database chosen by a remote
    caller.
    """
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations

    def _t(fn, *args, **kwargs):
        """Call a tool function, translating its ValueErrors.

        The SDK draws a deliberate line: a ToolError's message reaches
        the model, and every other exception is a crash whose text stays
        on the server as "Error executing tool <name>". Every ValueError
        raised above is a CALLER error -- an unknown id, a ref nobody
        issued, an empty prompt -- and the message is the whole
        useful part of it. Without this translation an agent cannot tell
        "you passed a bad id" from "the server is broken", and its only
        recovery from either is to retry the identical call.
        """
        try:
            return fn(*args, **kwargs)
        except (ValueError, Refused) as exc:
            raise ToolError(str(exc)) from exc

    # --- what a stranger reads (2026-10-07, the directory listing) ------
    #
    # Every title, description and annotation comes from the constants
    # above (TITLES / DESCRIPTIONS / HINTS), never from a docstring: the
    # SDK reads a docstring at registration, so a docstring written for
    # the operator's agent ("the nightly", "the Dev Studio", a venv
    # command) is what a directory user would have been handed. The test
    # pins each registered tool to its constant and screens the
    # vocabulary. The functions' own docstrings stay as the operator's
    # notes, which is what they always were.
    def _ann(name: str) -> ToolAnnotations:
        hints = HINTS[name]
        return ToolAnnotations(title=TITLES[name], read_only_hint=hints["read"],
                               destructive_hint=hints["destructive"],
                               idempotent_hint=hints["idempotent"],
                               open_world_hint=hints["open_world"])

    if surface not in SURFACES:
        raise ValueError(f"surface must be one of {SURFACES}, got {surface!r} "
                         "(the board surface was removed on 2026-10-11)")
    # the servers: a listed one (the render listing, or the Claude
    # directory's -- `listed="claude"`, 2026-10-11), or the studio
    listing = ("render" if listed is True else listed) if listed else None
    if listing is not None and listing not in LISTINGS:
        raise ValueError(f"listed must be True or one of {LISTINGS}, got {listed!r}")
    studio = listing is None
    offered = {None: STUDIO_TOOLS, "render": LISTED_TOOLS,
               "claude": CLAUDE_LISTED_TOOLS}[listing]

    def _describe(name: str) -> str:
        if listing == "claude" and name in CLAUDE_DESCRIPTIONS:
            return CLAUDE_DESCRIPTIONS[name]
        if listing and name in LISTED_DESCRIPTIONS:
            return LISTED_DESCRIPTIONS[name]
        return DESCRIPTIONS[name]

    def _reg(name: str):
        if name not in offered:
            return lambda fn: fn          # not on this server
        register = server.tool(name=name, title=TITLES[name],
                               description=_describe(name), annotations=_ann(name))
        if not studio:
            return register               # the listed server: plain dicts, as always

        def typed(fn):                    # the studio: typed results (step 7)
            register(_structured(name, fn))
            return fn
        return typed

    # The MCP Apps probe (2026-10-11): OFF unless ZEROPAGE_MCP_APPS_PROBE=1, and
    # the studio surface only. On, the server advertises the UI extension and
    # carries three diagnostics that say whether a panel renders in the client
    # -- src/mcp_apps_probe.py. Off, nothing below differs by a byte.
    probe = None
    # stdio only (`local_files`): since 2026-10-11 the operator's HTTP key
    # reaches this same surface, and a diagnostic for a desktop client has
    # no business on a network door
    if studio and local_files:
        from . import mcp_apps_probe
        if mcp_apps_probe.enabled():
            probe = mcp_apps_probe.build()
    server = MCPServer(name, instructions=(STUDIO_INSTRUCTIONS if studio else
                                           CLAUDE_INSTRUCTIONS if listing == "claude"
                                           else INSTRUCTIONS),
                       **({"extensions": [probe[0]]} if probe else {}))
    if probe:
        mcp_apps_probe.add_report_tool(server, probe[1])

    def _run(fn, *args, **kwargs):
        """A tool that takes minutes goes through the job registry when
        one was injected, and returns a job id instead of a result. The
        job is the caller's (resolved here, in the request).
        `_cancellable` (the spending tools) makes it one `cancel_job` can
        stop."""
        label = kwargs.pop("_label", fn.__name__)
        cancellable = kwargs.pop("_cancellable", False)
        if start_job is None:
            return _t(fn, *args, **kwargs)
        if cancellable:
            job = start_job("mcp", label, _cancellable_body(fn, kwargs), cancellable=True,
                            account_id=_account(account_id, dsn))
        else:
            job = start_job("mcp", label, lambda job: {"result": fn(*args, **kwargs)},
                            account_id=_account(account_id, dsn))
        return {"job_id": job["id"], "status": job["status"], "label": label,
                "note": ("started; poll with the `job` tool"
                         + ("; `cancel_job` stops it"
                            if cancellable and "cancel_job" in offered else ""))}

    @_reg("images_for")
    def images_for(query: str, brand: str = "", limit: int = 6) -> dict:
        return _t(find_images, query, brand=brand, limit=limit, dsn=dsn)

    @_reg("projects")
    def projects_tool(include_archived: bool = False, limit: int = LIST_LIMIT) -> dict:
        return _t(list_project_cards, include_archived=include_archived, limit=limit,
                  dsn=dsn, account_id=account_id)

    @_reg("project")
    def project_tool(project_id: int, chat_turns: int = CHAT_PREVIEW) -> dict:
        return _t(get_project, project_id, chat_turns=chat_turns, dsn=dsn,
                  account_id=account_id)

    @_reg("project_chat")
    def project_chat(project_id: int, before: Optional[int] = None,
                     limit: int = 40) -> dict:
        return _t(project_history, project_id, before=before, limit=limit, dsn=dsn,
                  account_id=account_id)

    @_reg("create_project")
    def create_project(title: str, brief: str = "", look: str = "") -> dict:
        return _t(make_project, title, brief=brief, look=look, dsn=dsn,
                  account_id=account_id)

    @_reg("save_chat")
    def save_chat(project_id: int, turns: list[ChatTurn]) -> dict:
        return _t(save_project_chat, project_id, turns=turns, dsn=dsn,
                  account_id=account_id)

    @_reg("elements")
    def elements() -> dict:
        return _t(list_elements, dsn=dsn, account_id=account_id)

    @_reg("add_element")
    def add_element_tool(kind: ElementKind, name: str, source: str,
                         notes: str = "") -> dict:
        return _t(add_element, kind, name, source, notes=notes,
                  create_element=create_element, dsn=dsn, account_id=account_id)

    @_reg("image_models")
    def image_models() -> dict:
        return _t(list_image_models, credits=not studio)

    @_reg("video_models")
    def video_models() -> dict:
        return _t(list_video_models)

    @_reg("effects")
    def effects(effect: str = "", category: str = "") -> dict:
        return _t(list_effects, effect=effect, category=category)

    @_reg("renders")
    def renders(kind: Optional[RenderKind] = None, limit: int = 20) -> dict:
        return _t(list_renders, kind=kind, limit=limit, dsn=dsn, account_id=account_id)

    @_reg("prompt_craft")
    def prompt_craft(step: CraftStep, prompt: str, model: str = "", tool: str = "",
                     count: int = 2) -> dict:
        return _t(get_prompt_craft, step, prompt, model=model, tool=tool,
                  count=count, dsn=dsn, account_id=account_id)

    # The spending doors: the studio surface's. Each answers a
    # call with no quote_token with the quote, inline and free; an approved
    # call is checked once more here -- so a stale token, a bad id or a
    # short balance is answered now, not inside a job the agent has to poll
    # for -- then its token is claimed and it runs as a job, once
    # (start_approved).
    def _quoted(fn, label: str, **args):
        args.update(dsn=dsn, account_id=_account(account_id, dsn))
        if not (args.get("quote_token") or "").strip():
            return _t(fn, **args)                 # a quote: instant, free
        return _t(start_approved, fn, args,
                  lambda: _run(fn, **args, _label=label, _cancellable=True))

    # A still is the ONE of them the render listing has too (2026-10-11,
    # Mike's call): the same function through the same gate, answered in
    # credits only. Never the Claude listing -- `_reg` leaves it off there.
    @_reg("generate_image")
    def generate_image(prompt: str, model: str = "", aspect: str = "",
                       references: Optional[list[str]] = None,
                       quote_token: str = "",
                       project_id: Optional[int] = None) -> dict:
        return _quoted(run_image, f"image {model or 'default'}", prompt=prompt,
                       model=model, aspect=aspect, references=references,
                       quote_token=quote_token, project_id=project_id,
                       **({} if studio else {"listed": True}))

    if studio:
        @_reg("generate_video")
        def generate_video(prompt: str, model: str = "", seconds: Optional[int] = None,
                           frame: str = "", reference: str = "",
                           quote_token: str = "",
                           project_id: Optional[int] = None) -> dict:
            return _quoted(run_video, f"video {model or 'default'}", prompt=prompt,
                           model=model, seconds=seconds, frame=frame,
                           reference=reference, quote_token=quote_token,
                           project_id=project_id)

        @_reg("apply_effect")
        def apply_effect(effect: str, sources: Optional[list[str]] = None,
                         prompt: str = "", options: Optional[dict] = None,
                         quote_token: str = "",
                         project_id: Optional[int] = None) -> dict:
            return _quoted(run_effect, f"effect {effect}", effect=effect,
                           sources=sources, prompt=prompt, options=options,
                           quote_token=quote_token, project_id=project_id)

        @_reg("element_sheet")
        def element_sheet(kind: ElementKind, name: str, quote_token: str = "") -> dict:
            return _quoted(run_element_sheet, f"sheet {name}", kind=kind, name=name,
                           quote_token=quote_token)

        @_reg("edit_clip")
        def edit_clip(source: str, instruction: str, stage: EditStage = "frame",
                      frame: str = "", model: str = "", at: float = 0.0,
                      keep_audio: bool = True, quote_token: str = "",
                      project_id: Optional[int] = None) -> dict:
            return _quoted(run_edit_clip, f"edit {stage} {source}", source=source,
                           instruction=instruction, stage=stage, frame=frame, model=model,
                           at=at, keep_audio=keep_audio, quote_token=quote_token,
                           project_id=project_id)

        # Joining clips spends nothing, so there is no quote; it is checked
        # here, in the request (a refusal is a caller error, not a failed
        # job to poll for), then rendered as a job.
        @_reg("assemble_clips")
        def assemble_clips(clips: list[str], transition: JoinTransition = "cut",
                           crossfade_s: float = 0.5, music: str = "",
                           letterbox: bool = False, title: str = "",
                           project_id: Optional[int] = None) -> dict:
            args = dict(clips=clips, transition=transition, crossfade_s=crossfade_s,
                        music=music, letterbox=letterbox, title=title,
                        project_id=project_id, dsn=dsn, account_id=_account(account_id, dsn))
            plan = _t(run_assemble_clips, **args, dry_run=True)["plan"]
            out = _run(run_assemble_clips, **args, _label=f"join {len(plan['clips'])} clips")
            if "job_id" not in out:
                return out                    # no registry: it ran inline
            return {**out, "plan": plan,
                    "note": (f"Joining {len(plan['clips'])} clips (about {plan['seconds']:g}s). "
                             "It runs on the studio's server -- no credits are spent. Poll "
                             "`job`: the result is a gen:<id> on your Assets wall.")}

    # Reading this machine's disk: the STUDIO surface over stdio only -- the
    # person's own computer. Never the listed server, and never the HTTP
    # mount (`local_files=False`), where "this machine" is the web server.
    if studio and local_files:
        @_reg("import_file")
        def import_file(path: str) -> dict:
            return _t(run_import_file, path, dsn=dsn, account_id=_account(account_id, dsn))

    # Posting: a DRAFT and a review link, never a post. The press of Post is
    # the person's, on the studio page (src/publish_review.submit). Safe on
    # every surface that is not listed: it writes a draft row and nothing else.
    @_reg("prepare_post")
    def prepare_post(source: str, platform: PostPlatform = "tiktok",
                     caption: str = "") -> dict:
        return _t(run_prepare_post, source, platform=platform, caption=caption,
                  dsn=dsn, account_id=account_id)

    @_reg("write_scene")
    def write_scene_tool(prompt: str, seconds: int = 10,
                         refs: Optional[list[str]] = None, title: str = "",
                         project_id: Optional[int] = None,
                         scene_id: Optional[int] = None) -> dict:
        out = _t(write_scene, prompt, seconds=seconds, refs=refs, title=title,
                 project_id=project_id, scene_id=scene_id,
                 dsn=dsn, account_id=account_id)
        if listing == "claude" and not out.get("needs_reference"):
            out["next"] = (f"`quote` scene_id={out['scene_id']} for the price; the "
                           "person approves the render in the studio at `studio_url`")
        return out

    @_reg("scene")
    def scene(scene_id: int) -> dict:
        return _t(read_scene, scene_id, dsn=dsn, account_id=account_id)

    @_reg("quote")
    def quote(scene_id: int, provider: Optional[str] = None, model: Optional[str] = None,
              duration: Optional[int] = None, frame: Optional[str] = None) -> dict:
        return _t(quote_render, scene_id, provider=provider, model=model,
                  duration=duration, frame=frame, dsn=dsn, account_id=account_id,
                  listing=listing)

    if approve_render is not None and approve_keyframes is not None:
        @_reg("approve")
        def approve(scene_id: int, what: WhatToApprove = "clip",
                    tokens: Optional[list[str]] = None, provider: Optional[str] = None,
                    model: Optional[str] = None, duration: Optional[int] = None,
                    frame: Optional[str] = None) -> dict:
            from .approvals import ApproveRefused
            acting = _account(account_id, dsn)
            try:
                if what == "keyframes":
                    out = approve_keyframes(int(scene_id), acting)
                else:
                    out = approve_render(int(scene_id), acting, {
                        "provider": provider, "model": model, "duration": duration,
                        "frame": frame, "tokens": [t for t in (tokens or []) if t]})
            except ApproveRefused as e:
                hint = (" -- call `quote` and pass its tokens"
                        if e.code in ("missing_quote", "expired", "stale_content",
                                      "wrong_render", "bad_signature") else
                        f" -- pick a plan or top up at {pricing_url()}"
                        if e.code == "out_of_credits" else "")
                raise ToolError(f"{e.code}: {e.message}{hint}") from e
            out = dict(out)
            out.setdefault("note", "started; poll with the `job` tool")
            return out

    if job_status is not None:
        @_reg("job")
        def job(job_id: int) -> dict:
            snap = job_status(int(job_id), account_id=_account(account_id, dsn))
            if snap is None:
                # only a listed server has `scene`: the studio surface is told
                # what it always was, not to read a tool it does not have
                raise ToolError(
                    f"no job {job_id} -- jobs live in memory and a restart "
                    "clears them; "
                    + ("a render still lands on its scene, so read `scene` "
                       "before starting anything again" if listing else
                       "start the work again if it was yours"))
            return snap

    # Stopping a render (2026-10-08, task-mcp-studio-v2 step 6): wherever the
    # spending tools are, and only with a registry to ask -- never listed.
    if cancel_job is not None and job_status is not None and studio:
        @_reg("cancel_job")
        def cancel_job_tool(job_id: int) -> dict:
            return _t(cancel_studio_job, job_id, job_status=job_status, cancel=cancel_job,
                      account_id=_account(account_id, dsn))

    return server


# --- stdio ------------------------------------------------------------------
#
# TWO TRANSPORTS, TWO CALLERS, AND THE DEFAULT IS THE SAFE ONE.
#
# The HTTP mount (app/mcp_mount.py) exists for a caller that is not on
# this machine: a signed-in person through the directory connector (the
# listed server), or the operator's own key (the studio surface).
#
# stdio costs no public endpoint. Claude Desktop LAUNCHES this process
# itself, talks to it down a pipe, and there is no port, no token on the
# internet, and nothing to leave running. It serves the studio surface.

# THE DROPPED COPY (2026-10-11). Claude Desktop starts this process, ends
# its stdin within a millisecond and starts another two seconds later,
# which is the one it keeps. The first was not killed: it ran the whole
# table setup -- 15s against the live database -- before the transport
# read EOF, and since the setups take turns (db.run_init) the kept copy
# sat behind it and answered `initialize` in ~30s instead of ~17. A
# process whose stdin has already been hung up, with nothing left to
# read, has nobody to serve; it should leave before it connects.
#
# The check must not CONSUME anything. mcp 2.x serves the wire from its
# own duplicate of fd 0 (mcp/server/stdio.py, _claim_fd), not through
# sys.stdin, so one byte read or peeked here is a request the kept copy
# never sees. poll() only looks. Measured on macOS, where Node hands a
# child a socketpair and a shell hands it a pipe:
#
#   the other end closed, nothing written   POLLHUP, 0 bytes   -> leave
#   open, nothing written yet               nothing            -> serve
#   open, a request already written         POLLIN,  n bytes   -> serve
#   a request written, THEN closed          POLLHUP, n bytes   -> serve it
#
# Everything else -- a terminal, /dev/null (POLLNVAL on macOS), a file,
# no poll() on the platform, any error at all -- reads as "serve". A wrong
# exit is worse than the slow start this fixes: the desktop would show
# "Server disconnected".

def hung_up(fd: int) -> bool:
    """True only when the other end of `fd` has gone AND nothing is left
    to read on it. Reads nothing; never raises."""
    try:
        import array
        import fcntl
        import select
        import termios

        poller = select.poll()
        poller.register(fd, select.POLLIN)
        events = poller.poll(0)
        if not events:
            return False
        flags = events[0][1]
        if flags & select.POLLNVAL or not flags & select.POLLHUP:
            return False
        pending = array.array("i", [0])
        fcntl.ioctl(fd, termios.FIONREAD, pending)
        return pending[0] == 0
    except Exception:           # no poll() here, not a descriptor, anything
        return False


def stdin_dropped() -> bool:
    """Whether whoever launched this process has already let go of it.

    Only when sys.stdin really is fd 0 -- the one case in which the
    transport reads fd 0. Anything else (stdin replaced by a test runner
    or an embedder, no stdin at all) is not this function's to judge."""
    try:
        if sys.stdin is None or sys.stdin.buffer.fileno() != 0:
            return False
    except Exception:
        return False
    return hung_up(0)


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="The Zero Page studio as an MCP server (images, video and "
                    "effects, quoted and approved in chat).")
    parser.add_argument("--db", default=None,
                        help="database URL (default: DATABASE_URL)")
    parser.add_argument("--engine", action="store_true",
                        help="accepted and ignored: it turned on the board "
                             "surface's engine tools, which went on 2026-10-11")
    parser.add_argument("--surface", default=None,
                        help="accepted for old configs: the only surface is "
                             "studio, and any other name (the removed `board`) "
                             "serves it too, with a note on stderr")
    args = parser.parse_args(argv)

    # .env is loaded HERE rather than at import: Claude Desktop launches
    # this with a bare environment -- no shell profile, no cwd it would
    # find -- so GEMINI_API_KEY and the rest have to be read off disk or
    # every engine tool fails with a missing key it cannot explain.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    dsn = args.db or None
    from . import entities, generative, projects, publish_review, quote_redemptions, render_assets, watermark
    from .cut import store as cut_store

    def init_tables():
        # Tables the tools read must exist before the first call: a desktop
        # that launches this on a fresh clone would otherwise answer its
        # first call with "no such table" instead of an empty list.
        db.init_db(dsn)
        preprod.init(dsn)
        scout.init(dsn)
        # ...and the ones `elements` and every reference check read (the
        # characters / props tables) and `renders` lists. Without these a
        # fresh database answered a photo ref with "Error executing tool"
        # rather than "not one of your photos" (found running the studio
        # surface over stdio, 2026-10-08).
        entities.init(dsn)
        render_assets.init(dsn)
        outcomes.init(dsn)            # what is done with an output made here
        projects.init(dsn)            # after preprod.init: it ALTERs shoot_concepts
        quote_redemptions.init(dsn)   # an approved quote is spent once
        publish_review.init(dsn)      # prepare_post writes a draft here
        watermark.init(dsn)           # a free render's clean original is found here
        # ...and what import_file and assemble_clips write (2026-10-09): the
        # editor's uploads, cut projects and versions, and the generations log a
        # joined clip's wall entry stands on. Found by running them over stdio
        # against a fresh database, where both crashed on a missing table.
        generative.init(dsn)
        cut_store.init(dsn)

    # Nobody to serve: leave before connecting (see THE DROPPED COPY).
    if stdin_dropped():
        print("note: stdin was already closed with nothing to read, so there "
              "is nobody to serve; exiting without touching the database",
              file=sys.stderr)
        return 0

    # One start at a time (2026-10-10). Claude Desktop launches this
    # process twice within seconds on every start and drops the first, and
    # two of these inits side by side deadlock in Postgres -- eleven
    # starts died that way, "Server disconnected", before anyone read the
    # desktop's log. db.run_init serializes them and runs the block again
    # if it is still picked as a deadlock's victim.
    db.run_init(init_tables, dsn)

    # The job registry, injected here for the same reason app/mcp_mount.py
    # injects it: a render takes minutes, and a tool call that blocks that
    # long is a tool call the desktop times out. With it, an approved
    # render hands back a job id and `job` polls it.
    #
    # This is the ONE place src/ reaches into app/, and it is deliberate:
    # the rule exists so the LIBRARY layer stays importable without the
    # web app, and `main` is a process entry point, not a module anything
    # imports. app/jobs.py is stdlib-only (asyncio, threading, datetime)
    # -- importing it pulls in no FastAPI and costs nothing. The
    # alternative was a second job registry living in src/, and one
    # registry with an odd import beats two implementations that drift.
    try:
        from app import jobs
        start_job, job_status, cancel_job = jobs.start, jobs.get, jobs.cancel
    except Exception as exc:                    # surfaced, never silent
        print(f"note: no job registry ({type(exc).__name__}: {exc}) -- renders "
              "will run inline and may time out", file=sys.stderr)
        start_job = job_status = cancel_job = None

    # `add_element` runs the Elements page's own create body, which lives in
    # app/api.py. Reached on the FIRST call rather than imported here: that
    # module pulls the whole web app in, and a desktop that never adds an
    # element should not pay for it at every start. That body writes to the
    # process's own database (it takes no `dsn`, like every route), so a
    # server started on another one with --db refuses rather than file an
    # element where this server would never read it back.
    def create_element(*a, **kw):
        if dsn and db.resolve_dsn(dsn) != db.resolve_dsn():
            raise Refused("elements are added to the studio's own database; this "
                          "server was started on another one (--db)")
        from app import api, mcp_mount
        return mcp_mount.connector_element(api.create_element)(*a, **kw)

    # THE STUDIO SURFACE, whatever was asked (2026-10-11): it is the only
    # one. An old config that still says `--surface board` (or the env var)
    # gets the studio and a line saying why, never a dead start.
    asked = (args.surface or os.environ.get(SURFACE_ENV, "")).strip()
    if asked and asked not in SURFACES:
        print(f"note: surface {asked!r} is gone (the idea board was removed on "
              "2026-10-11) -- serving the studio surface", file=sys.stderr)
    build_server(dsn=dsn, start_job=start_job, job_status=job_status,
                 cancel_job=cancel_job, surface="studio",
                 create_element=create_element).run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
