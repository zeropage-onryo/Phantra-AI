# Phantra AI

Plan, write and organise short video scenes from your own photos and clips, in a
conversation with Claude. Open your [Phantra](https://phantra.ai) projects, bring
your photos in as elements, write a scene as timed shots held to them, see what
it would cost in credits, and trim, reshape, join and share what you already
have, free.

**Nothing in this plugin renders, draws or spends credits.** A scene saved here
opens on its own page in the Phantra studio, where you see the price and press
Render yourself.

Documentation: https://phantra.ai/mcp/claude

## What's included

- **The Phantra connector**, a remote MCP server at
  `https://api.phantra.ai/mcp/claude`. You sign in with your Phantra account
  (OAuth); the tools read and write your own projects, scenes, elements and
  library, and nobody else's.
- **22 skills** that teach Claude the studio workflow. Claude loads
  `phantra-ai-use` before any write.

## Install

You need a Phantra account. Sign in once at https://phantra.ai: your workspace
is created on the first sign-in, with a one-time trial grant of credits. The
connector cannot create a workspace; until you have one it says where to sign
in.

**Claude (web, desktop, mobile):** add Phantra AI from the directory, open its
Connectors tab, connect, and approve the sign-in.

**Claude Code:**

```
/plugin marketplace add zeropage-onryo/phantra-claude-plugin
/plugin install phantra-ai@phantra
```

Then ask "What am I working on in Phantra?" to check the connection.

## Skills

| Group | Skills | What they cover |
|---|---|---|
| The work | `phantra-ai-use`, `start-a-project`, `ideas-and-projects`, `storyboard`, `write-scene`, `series-and-continuity`, `ad-variations` | a brief to ideas, a project, a beat list, timed-shot scenes, episodes and A/B variants |
| Look and pictures | `look-matching`, `brand-kit-from-my-work`, `product-shots`, `camera-moves`, `model-prompting`, `sound-plan` | what each photo is for, a brand kit from your own work, camera language, which model, the sound |
| Kinds of piece | `ad-formats`, `ugc-ad`, `explainer`, `hooks-and-first-seconds`, `client-treatment` | ad shapes, talk-to-camera ads, explainers, openings, a one-page pitch |
| Finishing | `edit-and-deliver`, `platform-delivery` | trims, joins, reshapes per platform, a download link |
| Credits | `price-and-hand-off`, `credits-and-limits` | the price of a scene, the studio link, your balance |

No skill invents testimonials, reviews, numbers or awards: claims come from you.

## Tools

32 tools. None of them renders, draws or spends credits.

| Tools | What they do |
|---|---|
| `projects`, `project`, `project_chat`, `create_project` | list, reopen (brief, look, scenes, references, renders, chat) and start projects; the same ones as in the studio |
| `elements`, `add_element`, `upload_link` | your characters, props and places; add a picture from an image address or product page; a one-time page to upload from your phone |
| `write_scene`, `duplicate_scene`, `scene` | save a scene with what each photo is for, copy one with changes, read one back |
| `quote`, `video_models`, `recommend_model` | a scene's price in credits with its studio link; the models; which one suits a job |
| `library`, `share_link` | your renders and uploads; a time-limited download link |
| `reformat`, `trim_clip`, `assemble_clips`, `job` | free edits on the studio's server, and their progress |
| `balance`, `credit_history`, `whoami`, `recent`, `search` | your credits, your workspace and plan, your latest work, search |
| `preferences`, `set_preferences`, `recipes`, `recipe`, `save_recipe` | your defaults and saved recipes |
| `what_works`, `score_caption`, `feedback` | what you kept and what reached an audience, a caption scored on your own posts, a note to us |

## Try it

1. "What am I working on?" → `projects`.
2. "A 10-second spot for a matte black water bottle on a wet gym floor, no
   people." → Claude asks a few questions and proposes three ideas.
3. "Here's the bottle." → `upload_link`: open the page on your phone, pick the
   photo, and it lands on a Bottle element.
4. "Write the scene." → timed shots in the chat, your edits, then `write_scene`.
5. "What would it cost?" → `quote`: the keyframes, each shot, your balance, and
   the scene's link. Open it and press Render; the price is shown again first.
6. "Square cut of the first second, and a link I can send." → `trim_clip`,
   `reformat`, `share_link`, all free.

## Data

The connector talks only to your Phantra account at `api.phantra.ai`, over HTTPS,
with the sign-in you approve. It sends what the tools need: the scene text
Claude writes with you, a project's name, brief and look, the ids of your
projects, scenes, renders and photos, and the words you give a tool (a search,
a note, a recipe, a caption, a preference). It does not send the conversation.

- `add_element` gives the studio one https address you name. The studio fetches
  it itself: an image up to 15 MB, or a product page, whose main picture is
  taken and whose stated facts (name, brand, colour, size) are kept in the
  element's notes.
- With `upload_link` the file goes from your device to the studio through the
  page the link opens, never through the chat.
- A `share_link` works for anyone holding it until it expires.

Your scenes, elements, uploads and projects stay under your account until you
remove them in the studio. Preferences, recipes and feedback are kept as dated
entries; ask Support to remove them. Nothing is deleted through the connector,
and every change except a scene rewrite makes a new item. Renders are made in
the studio and charged from your balance only after you approve the price there.
The plugin itself runs no code and stores nothing. See the
[privacy policy](https://phantra.ai/privacy) and [terms](https://phantra.ai/terms).

The connector cannot render, buy credits, change a plan, post anywhere or
remove your work. It allows over a hundred calls a minute per account; a `429`
carries `Retry-After`.

## Support

support@phantra.ai · https://phantra.ai/support (a person answers within 24-48
hours). Plugin bugs: [GitHub issues](https://github.com/zeropage-onryo/phantra-claude-plugin/issues).

MIT licensed.
