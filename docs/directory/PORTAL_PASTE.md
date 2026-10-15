# Portal paste sheet (2026-10-12, updated 2026-10-15)

> **2026-10-15 (directory-review fixes):** the Claude listing is described by what the
> connector does -- plan, write, organise, price and edit scenes from the person's own photos
> and clips -- and not as an "AI image and video generator", because Anthropic's Software
> Directory Policy (4B) and its connector review criteria refuse software that uses AI models
> to generate images, video or audio. Renders are approved and made in the Phantra studio,
> never through `/mcp/claude`. Its documentation URL is now `https://phantra.ai/mcp/claude`,
> a page that documents only that address and its 32 tools. The packages to submit are the
> Claude plugin **0.6.0** and the ChatGPT plugin **1.3.0** (both on their
> `claude/directory-review-fixes` branches until merged). The test account is
> `review@phantra.ai`.

Every field the portals ask for, in the order their forms ask, so each submission is paste and
click. The listing text is `SUBMISSION.md`'s "The portal fields" word for word; the addresses
are `TWO_LISTINGS.md`'s (which wins where the two disagree); where an older line in
`SUBMISSION.md` no longer describes the listed server, the correction is marked. Field names
and limits are `REQUIREMENTS.md`'s (C27, C28, C30, C33, P26).

**Nothing here is a credential.** The test account's password is Mike's to type into the
portal's test-credentials field, and nowhere else; this file carries its email only.

## 1. Anthropic: the MCP connector

`https://claude.ai/directory/manage` → Submit new → MCP connector.

### Connection

| field | paste |
|---|---|
| Server URL | `https://api.phantra.ai/mcp/claude` |
| Connection type | Universal URL |

(The Claude listing is
the `/mcp/claude` door on the API domain, `TWO_LISTINGS.md` "The two servers".)

### Tools

Sync from the server. 32 tools, each with a title and hints (`docs/directory/screens/inspector-claude.json`
is the listing the Inspector read). Read-only: projects, project, project_chat, elements,
video_models, scene, quote, job, library, share_link, balance, search, whoami, recent,
credit_history, recommend_model, preferences, recipes, recipe, what_works, score_caption.
Write, none destructive: create_project, add_element, upload_link, duplicate_scene, reformat,
trim_clip, assemble_clips, feedback, set_preferences, save_recipe; write_scene is marked
destructive because a `scene_id` replaces that scene's text. Nothing on this door renders,
draws or spends credits.

### Listing

| field | limit | paste |
|---|---|---|
| Name | 100 | `Phantra AI` |
| One-liner | 200 | `Plan, write, organise, price and edit short video scenes from your own photos and clips in a conversation. Renders are approved and made in the Phantra studio, never in the chat.` |
| Description | 2,000 | the block below |
| Categories | 1–5 | Creative & Design; Productivity; Marketing (pick what the portal offers closest to video / creative) |
| Documentation URL | | `https://phantra.ai/mcp/claude` (the Claude connector's own page: this address and its 32 tools only) |
| Privacy policy URL | | `https://phantra.ai/privacy` |
| Terms | | `https://phantra.ai/terms` |
| Support contact | | `support@phantra.ai` |
| Icon | square PNG | `docs/directory/icon/phantra-icon-512.png` (512×512, with a 1024×1024 master beside it; no dark variant) |
| Slug (permanent) | | `phantra-ai` |

Description, paste as one block:

> Phantra AI connects Claude to your Phantra workspace so you can plan short
> video scenes in a conversation. Open your projects with their brief, look,
> scenes, reference photos and chat history, or start a new one. Bring your
> own photos and clips in: paste an image or product-page address, or get a
> one-time upload page for a file on your phone. Write a scene with Claude as
> timed shots and save it into a project; every scene is held to photographs
> of your own elements (a character, a product, a place), and you can say
> what each photo is for. Ask what a scene would cost: the connector prices
> it in credits beside your balance and returns a link to the scene's page in
> the Phantra studio. Renders are approved and made there, by you; the
> connector itself draws, renders and spends nothing. Trim a clip, make a
> square or vertical copy, join clips and get a download link, free, on the
> studio's own server. Read your balance and where your credits went, which
> model suits a job, what you kept and what reached an audience, and keep
> your own recipes. Sign in once at phantra.ai to create your workspace, then
> connect.

### Use cases (C30)

- Primary use cases, three lines: `Plan a short ad or video as timed scenes in a project,
  held to my own product or character photos`; `Reopen a project with its brief, references
  and chat and carry on`; `Price a scene in credits and get the link to approve its render in
  the Phantra studio`.
- What users need before they can connect: `A Phantra account (free sign-in with trial
  credits; renders are approved and paid for in credits in the Phantra studio).`
- Reads data, writes data, or both: **both**.

### Company

Phantra, `https://phantra.ai`. Primary contact: Mike's email for review updates
(the one on the GitHub account; not shown publicly).

### Authentication

`OAuth with dynamic client registration (Supabase OAuth 2.1 server, PKCE S256). No lazy auth:
every tool needs the account.`

### Data handling

Paste: `The API is our own (api.phantra.ai). The connector calls no third-party API on the
person's behalf: add_element fetches the one picture or product page the person names (https
only), and share_link signs a time-limited download address off the studio's own storage
bucket. No personal health data. No sponsored content.`
(Corrected from `SUBMISSION.md`, whose line names `images_for` and the image-search lanes;
those are the studio surface's, not on either listed server.)

### Test & launch (C26, C28)

- Test credentials: email `review@phantra.ai` (the reviewer login on the populated
  workspace, created 2026-10-15); its password is typed into this field only and is written
  nowhere else.
- Setup instructions for the reviewer, paste as a numbered list:
  1. `The account is Phantra Review, a real workspace already populated: four product elements
     with photos (Solene perfume, Tonal One headphones, Fuego Dulce hot sauce, Kumo matcha, all
     invented brands), the project "Spring product spots" with written scenes, three renders, a
     credit balance, and the prop "Reviewer check" with its photo, the scene "Reviewer check:
     Tonal One push-in" and the recipe "reviewer-check" left by our own reviewer walk.`
  2. `Sign in once at https://phantra.ai with these credentials (the workspace exists; the
     first sign-in only links your session), then add the connector and approve the consent page
     it shows.`
  3. `In a chat: projects → project (Spring product spots) → elements → upload_link (open the
     page it returns, pick a photo, see it saved as an asset:<id> and onto the named element) →
     write_scene (a prompt of timed shots, refs from elements, roles for one of them,
     project_id from projects) → scene → quote (its approve_url is the scene's page in the
     studio; nothing renders from the chat) → library → reformat (a render to 1:1) → job (with
     wait=15, until done) → share_link.`
  4. `Then the reads: balance, credit_history, whoami, recent, search, video_models,
     recommend_model, what_works, score_caption, preferences; and the writes: set_preferences,
     duplicate_scene, save_recipe / recipes / recipe, feedback.`
  5. `What it cannot do: read another account's work (a foreign project or scene id answers
     "no project N" / "no scene N"), buy credits or change a plan, post anywhere, delete or
     overwrite anything (every edit is a new item; rewriting a scene replaces its text), or
     render or draw.`
- "Tested every tool in Claude and the MCP Inspector": yes -- `walk-2026-10-13-claude.md`,
  `walk-2026-10-13-render.md` and `screens/inspector-*.json` are the record (2026-10-12).

### Compliance (C33): seven acknowledgments, each answered truthfully

1. Directory guidelines: read and followed.
2. First-party API: `The connector reaches only Phantra's own API. Its one outbound
   fetch is the picture or product page a person names in add_element; downloads are signed
   off the studio's own storage bucket.`
3. Financial transactions: `None. The connector cannot buy credits, change a plan or move money;
   quote shows a price in credits and links to the studio.`
4. AI media generation: `This connector (/mcp/claude) generates no images, video or audio and
   has no tool that does. It plans and writes scene text, organises projects and the person's
   own photos and clips, prices a render in credits and returns approve_url, the scene's page
   in the Phantra studio, where the person approves the render outside the chat. Its free
   edits (trim, reformat, join) run ffmpeg on the studio's server over the person's own
   files.`
5. Prompt injection: `Tool descriptions describe the tools. A saved recipe, a product page's
   facts and a person's own text come back marked as data to read, never as instructions.`
6. Conversation data collection: `No tool takes the conversation (save_chat is not on this
   listing). feedback stores only the note a person asks to leave.`
7. Public documentation: `https://phantra.ai/mcp/claude`, and the plugin README at
   `https://github.com/zeropage-onryo/phantra-claude-plugin#readme`.

## 2. Anthropic: the plugin bundle

Submit new → Plugin bundle (P26).

| step | paste |
|---|---|
| Repository | `zeropage-onryo/phantra-claude-plugin` (public) |
| Plugin path | the repository root |
| Branch or tag | `main` at 59ee928 (v0.6.0, merged 2026-10-15) |
| Validate | listing details come from `.claude-plugin/plugin.json` and `README.md` |
| Data handling | reads personal data: only the account's own projects, scenes, renders and chat text; sends data to services other than its declared connector: no; retention: the studio's, `https://phantra.ai/privacy`; intended for people under 18: no |
| Compliance | contact email (Mike's); the four acknowledgments, truthfully |
| Review and submit | the GitHub push webhook (needs repo admin), else the scheduled check |

Then **pair** the plugin with the connector listing once both exist.

## 3. OpenAI: the render listing

**Superseded on 2026-10-12 by `docs/tasks/HANDOFF-chatgpt-submission-2026-10-12.md`:** OpenAI now
takes a plugin ZIP at `platform.openai.com/plugins` (source: `zeropage-onryo/phantra-chatgpt-plugin`),
verifies the server's domain with a token and asks for review cases and a demo recording. The
fields below are kept for the words; the handoff is the procedure.

| field | paste |
|---|---|
| MCP server URL | `https://api.phantra.ai/mcp` (37 tools: the Claude set plus image_models, generate_image, approve, effects and apply_effect) |
| Test credentials | email `review@phantra.ai`; the password typed there only |
| Privacy policy URL | `https://phantra.ai/privacy` |
| Support contact | `https://phantra.ai/support` |
| Documentation | `https://phantra.ai/mcp` |
| Example prompts | `Open my project Spring product spots and show me its scenes`; `Write a two-shot scene of the Tonal One headphones on a desk in window light and save it to the project`; `What would it cost to render scene 400, and what is my balance?`; `Make a square copy of my latest clip and give me a download link`; `Which model should I use for a cheap test, and which for a 25-second spot with sound?` |
| Listing text | the ChatGPT plugin's own listing (`plugin.json` `extensions.com.openai.interface`, phantra-chatgpt-plugin 1.3.0), not the Claude Description block above, which says the connector renders nothing and is true only of `/mcp/claude`. The text names no price or plan. |
| Package | `phantra-chatgpt-plugin` 1.3.0 (branch `claude/directory-review-fixes` until merged); `python3 scripts/check.py` prints ok |

The steps the reviewer follows are the same as section 1's, plus: `image_models →
generate_image (a quote comes back; call it again with the quote_token to draw) → approve
what=keyframes, then what=clip, each with quote's tokens and a balance that covers one small
render`, and `effects → library (for a gen:<id>) → apply_effect (a quote comes back; call it
again with the quote_token to run it)`.

## 4. After publishing (Mike)

- Fly: set `PHANTRA_CLAUDE_DIRECTORY_URL` to the listing's `https://claude.ai/...` address, so the
  studio's "Connect to Claude" panel collapses to one button.
- Watch the connector dashboard; `directory@anthropic.com` / `mcp-review@anthropic.com` for a
  stuck submission.
- Optional: clear account 1's "Live check" leftovers in the studio (scenes 405/406/407, the prop
  "Live check 2026-10-12", recipe `live-check`).
