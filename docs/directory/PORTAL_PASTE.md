# Portal paste sheet (2026-10-12)

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
| Server URL | `https://api.zeropage.studio/mcp/claude` |
| Connection type | Universal URL |

(`SUBMISSION.md` still shows `https://zeropage-studio.fly.dev/mcp` here; the Claude listing is
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
| Name | 100 | `Zero Page Studio` |
| One-liner | 200 | `Your AI video studio from a conversation: write a scene held to your own reference photos, see its price in credits, and render it only when you say yes.` |
| Description | 2,000 | the block below |
| Categories | 1–5 | Creative & Design; Productivity; Marketing (pick what the portal offers closest to video / creative) |
| Documentation URL | | `https://zeropage.studio/connector` |
| Privacy policy URL | | `https://zeropage.studio/privacy` |
| Terms | | `https://zeropage.studio/terms` |
| Support contact | | `https://github.com/zeropage-onryo/zeropage-studio-plugin/issues` |
| Icon | square PNG | `docs/directory/icon/zeropage-studio-icon-512.png` (or `zeropage-studio-icon-1024.png` if the portal asks for 1024) |
| Slug (permanent) | | `zeropage-studio` |

Description, paste as one block:

> Zero Page Studio is an AI video studio for creators and filmmakers.
> From a conversation, open your projects with their brief, look, scenes,
> reference images and chat history, or start a new one. Bring your own
> photos in: paste an image or product-page address, or get a one-time
> upload page for a picture or clip on your phone. Write a scene with
> Claude as timed shots and save it into a project; every scene is held to
> photographs of your own elements (a character, a product, a place), never
> to a name, and you can say what each photo is for. Ask what rendering
> would cost: the keyframes and the clip are priced in credits beside your
> balance, with a link to the scene's page in the studio where you approve
> it. Nothing is drawn, rendered or charged from the chat. Trim a clip,
> make a square or vertical copy, join clips and get a download link for
> free, on the studio's own server. Read your balance and where your
> credits went, which model suits a job, what you kept and what reached an
> audience, and keep your own recipes. Sign in once at zeropage.studio to
> create your workspace, then connect.

### Use cases (C30)

- Primary use cases, three lines: `Write a scene for a short or an ad into a project, held to
  my own product or character photos`; `Reopen a project with its brief, references and chat
  and carry on`; `Price and approve a render without leaving the chat`.
- What users need before they can connect: `A Zero Page Studio account (free sign-in; trial
  credits; a plan or credits for renders).`
- Reads data, writes data, or both: **both**.

### Company

Zero Page Studio, `https://zeropage.studio`. Primary contact: Mike's email for review updates
(the one on the GitHub account; not shown publicly).

### Authentication

`OAuth with dynamic client registration (Supabase OAuth 2.1 server, PKCE S256). No lazy auth:
every tool needs the account.`

### Data handling

Paste: `The API is our own (api.zeropage.studio). The connector calls no third-party API on the
person's behalf: add_element fetches the one picture or product page the person names (https
only), and share_link signs a time-limited download address off the studio's own storage
bucket. No personal health data. No sponsored content.`
(Corrected from `SUBMISSION.md`, whose line names `images_for` and the image-search lanes;
those are the studio surface's, not on either listed server.)

### Test & launch (C26, C28)

- Test credentials: email `deals4michael@gmail.com`; the password Mike set on 2026-10-12, typed
  here only.
- Setup instructions for the reviewer, paste as a numbered list:
  1. `The account is zp-billing-test, a real workspace already populated: four product elements
     with photos (Solene perfume, Tonal One headphones, Fuego Dulce hot sauce, Kumo matcha, all
     invented brands), the project "Spring product spots" with written scenes, three renders, a
     credit balance, and the prop "Reviewer check" with its photo, the scene "Reviewer check:
     Tonal One push-in" and the recipe "reviewer-check" left by our own reviewer walk.`
  2. `Sign in once at https://zeropage.studio with these credentials (the workspace exists; the
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
- "Tested every tool in Claude and the MCP Inspector": tick once `walk-2026-10-13-claude.md`
  and `screens/inspector-claude.json` are on `main` (they are the record).

### Compliance (C33): seven acknowledgments, each answered truthfully

1. Directory guidelines: read and followed.
2. First-party API: `The connector reaches only Zero Page Studio's own API. Its one outbound
   fetch is the picture or product page a person names in add_element; downloads are signed
   off the studio's own storage bucket.`
3. Financial transactions: `None. The connector cannot buy credits, change a plan or move money;
   quote shows a price in credits and links to the studio.`
4. AI media generation: `This listing (/mcp/claude) generates no images, video or audio. It
   writes scene text, prices a render in credits and returns the studio link where the person
   approves it; its free edits (trim, reformat, join) run ffmpeg on the studio's server over the
   person's own files.`
5. Prompt injection: `Tool descriptions describe the tools. A saved recipe, a product page's
   facts and a person's own text come back marked as data to read, never as instructions.`
6. Conversation data collection: `No tool takes the conversation (save_chat is not on this
   listing). feedback stores only the note a person asks to leave.`
7. Public documentation: `https://zeropage.studio/connector`, and the plugin README at
   `https://github.com/zeropage-onryo/zeropage-studio-plugin#readme`.

## 2. Anthropic: the plugin bundle

Submit new → Plugin bundle (P26).

| step | paste |
|---|---|
| Repository | `zeropage-onryo/zeropage-studio-plugin` (public) |
| Plugin path | the repository root |
| Branch or tag | `main` (v0.3.0, b1c6b93) |
| Validate | listing details come from `.claude-plugin/plugin.json` and `README.md` |
| Data handling | reads personal data: only the account's own projects, scenes, renders and chat text; sends data to services other than its declared connector: no; retention: the studio's, `https://zeropage.studio/privacy`; intended for people under 18: no |
| Compliance | contact email (Mike's); the four acknowledgments, truthfully |
| Review and submit | the GitHub push webhook (needs repo admin), else the scheduled check |

Then **pair** the plugin with the connector listing once both exist.

## 3. OpenAI: the render listing

`TWO_LISTINGS.md` "By hand" item 4: verify the organization on the OpenAI Platform (Owner
role); a global, not EU, data-residency project; no screenshots or CSP (no UI component).

| field | paste |
|---|---|
| MCP server URL | `https://api.zeropage.studio/mcp` (34 tools: the Claude set plus image_models, generate_image, approve) |
| Test credentials | email `deals4michael@gmail.com`; the password typed there only |
| Privacy policy URL | `https://zeropage.studio/privacy` |
| Support contact | `https://github.com/zeropage-onryo/zeropage-studio-plugin/issues` |
| Documentation | `https://zeropage.studio/connector` |
| Example prompts | `Open my project Spring product spots and show me its scenes`; `Write a two-shot scene of the Tonal One headphones on a desk in window light and save it to the project`; `What would it cost to render scene 400, and what is my balance?`; `Make a square copy of my latest clip and give me a download link`; `Which model should I use for a cheap test, and which for a 25-second spot with sound?` |
| Listing text | the Description block above, plus one sentence: `On this listing a still can be drawn and a priced render approved from the chat, after a quote and your yes.` The text names no price or plan; if the reviewer reads "priced in credits beside your balance" as a price, cut that clause (Mike's call). |

The steps the reviewer follows are the same as section 1's, plus: `image_models →
generate_image (a quote comes back; call it again with the quote_token to draw) → approve
what=keyframes, then what=clip, each with quote's tokens and a balance that covers one small
render`.

## 4. After publishing (Mike)

- Fly: set `ZEROPAGE_CLAUDE_DIRECTORY_URL` to the listing's `https://claude.ai/...` address, so the
  studio's "Connect to Claude" panel collapses to one button.
- Watch the connector dashboard; `directory@anthropic.com` / `mcp-review@anthropic.com` for a
  stuck submission.
- Optional: clear account 1's "Live check" leftovers in the studio (scenes 405/406/407, the prop
  "Live check 2026-10-12", recipe `live-check`).
