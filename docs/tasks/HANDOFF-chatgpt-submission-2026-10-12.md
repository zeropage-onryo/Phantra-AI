# Handoff: submit Zero Page Studio to OpenAI's plugin directory (ChatGPT)

**For:** Mike, at the portal, with this file open beside it. **From:** the Claude Code session of
2026-10-12 that ran `docs/tasks/task-connector-submission.md`. **Source of truth read that day:**
`developers.openai.com/plugins/deploy/submission`, `/plugins/deploy/app-review`,
`/plugins/plugin-guidelines`, `/plugins/build/plugins` (their `.md` versions). The flow is NOT the
one `docs/directory/TWO_LISTINGS.md` item 4 described: OpenAI now takes a **plugin ZIP** uploaded
at `https://platform.openai.com/plugins`, scans the MCP server itself, and verifies the server's
domain with a token our API has to serve.

Changes Mike asks for along the way go in the **Decision log** at the bottom, and the package and
this file are updated to match.

## What is ready

| thing | where | state |
|---|---|---|
| the plugin ZIP | `zeropage-studio-chatgpt-1.0.0.zip` (sent in the chat; source: the repository `zeropage-onryo/zeropage-studio-chatgpt-plugin`, its own since 2026-10-12, Mike's call) | built; two placeholders below |
| the render door | `https://api.zeropage.studio/mcp`, 35 tools, OAuth with dynamic client registration | live, walked 2026-10-12 as the test account (`docs/directory/walk-2026-10-13-render.md`) |
| the domain-verification route | `GET https://api.zeropage.studio/.well-known/openai-apps-challenge` serves `OPENAI_APPS_CHALLENGE` as plain text | in this PR; needs the merge, the deploy and the Fly secret (step 4) |
| credits-only refusals on listed servers | `balance`'s note, the `insufficient_credits` refusal and the `out_of_credits` approve hint name no purchase page | in this PR (OpenAI's commerce rule: a plugin may say more credits are needed, must not link to a page that starts a purchase) |
| the test account | `zp-billing-test` (account 5): four product props, project "Spring product spots", scenes 400/408/409/410/411, renders gen:93–110, 384 credits | populated; its member's email and password are the reviewer credentials (Decision log 1) |

## Before the portal (Mike)

1. **Organization verification** at `https://platform.openai.com/settings/organization/general`:
   individual verification to publish as yourself, business verification to publish as
   "Zero Page Studio". Enforced at review; an unverified name is rejected.
2. **A project with global data residency** (EU projects cannot submit MCP plugins). Owners have
   the `api.apps.write` permission already.
3. **Merge and deploy this PR**, then set the Fly secret once the portal shows the token (step 4).
4. **Record the demo walkthrough** (a few minutes: the five positive cases below, in ChatGPT
   Developer Mode or the studio connector in Claude), host it at an accessible URL, and put the URL
   in `chatgpt/plugin.json` → `extensions.com.openai.review.demo_recording_url` (today it is a
   placeholder). Rebuild the ZIP after (the repository's README has the one command).
5. **Decide the country list** (`publication.countries`, today `US, CA, GB, AU`).
6. **Try the door in ChatGPT first** (what the older docs called Developer Mode): `chatgpt.com/plugins`
   → the plus button → **Add custom MCP server** → `https://api.zeropage.studio/mcp` → the risk
   warning → sign in as the test account on our consent page. Run the five positive prompts below
   in a new chat and watch the tools fire as the cases say. This is also how anyone uses the render
   door in ChatGPT before the listing exists. ChatGPT registers its OAuth client once per connection
   through dynamic client registration and keeps reusing it; nothing on our side needs to change
   between the test and the review.

## The portal, step by step

### 1. Upload the ZIP

`https://platform.openai.com/plugins` → **Upload new or existing plugin** → pick the verified
**Developer identity** → **Upload plugin** → `zeropage-studio-chatgpt-1.0.0.zip`. Validation runs;
the plugin detail page opens with the draft.

What the ZIP already says (edit only in the source, then re-zip; the portal shows these read-only):

| field | value |
|---|---|
| name (identifier) | `zeropage-studio` (the guidelines forbid appending "MCP" or "Plugin" to a product name) |
| displayName | Zero Page Studio |
| shortDescription | Generate images and video held to your own photos, right from where you're already working. |
| longDescription | Generate high-quality images and video held to your own reference photos, right from where you're already working. Add Zero Page Studio and sign in with your studio account. Every still and clip is made only on your yes, on Kling, Veo, Seedance, LTX, Wan, FLUX and more, then filed in a project with its brief, look, references and chat. Trim, reshape, join and share what you made. No API key required. |
| category | Productivity (the portal's own list decides; change in the source if it offers a closer one) |
| capabilities | Write scenes · Generate images · Render video · Edit clips · Manage projects |
| websiteURL / supportURL / privacyPolicyURL / termsOfServiceURL | `https://zeropage.studio/connector` · `https://github.com/zeropage-onryo/zeropage-studio-chatgpt-plugin/issues` · `https://zeropage.studio/privacy` · `https://zeropage.studio/terms` |
| example prompts | the five in `defaultPrompt` (they are the positive test cases' prompts) |
| icons | `assets/icon.png` (512), `assets/logo.png` (1024), dark variants the same files |
| screenshots | none, on purpose: the plugin has no UI, and the docs say not to provide any then |

The listing text deliberately names no price, plan, credit figure, trial or promotion (guidelines,
"Subtitles and descriptions") and compares with nobody.

### 2. Metadata & Skills: resolve findings

Open **Metadata & Skills**, wait for the checks, read **Issues**, **Copy issues** and paste them to
me; I correct the source and you re-upload. There are no skills in this package, so only the
metadata checks run.

### 3. MCPs: connect the server

**MCPs** → `zeropage-studio` → **Connect**. The panel shows the URL (`https://api.zeropage.studio/mcp`)
and the auth read from `mcp.json` (OAuth, dynamic client registration; no client secret field,
because the client is public).

### 4. Domain verification (the one server step)

The panel shows a challenge token and the URL it must appear at:
`https://api.zeropage.studio/.well-known/openai-apps-challenge`, plain text, the token and nothing
else. Set it on Fly (the token is public, not a secret; `fly secrets set` is only where Fly keeps
env values):

```bash
fly secrets set --app zeropage-studio OPENAI_APPS_CHALLENGE=PASTE_THE_TOKEN_HERE
```

Fly restarts the machine; check with `curl -s https://api.zeropage.studio/.well-known/openai-apps-challenge`
(it prints the token), then press **Connect** in the panel and complete the OAuth sign-in it opens:
sign in as the **test account** (Decision log 1), press Allow on our consent page. The portal keeps
that authorization to scan the tools.

### 5. The tool scan

Wait for the scan; open **Issues**. Expect 35 tools, all with explicit `readOnlyHint`,
`destructiveHint` and `openWorldHint`. What a finding might say, and the answer:

- `write_scene` destructive: yes, by design (a `scene_id` rewrites that scene's text).
- `approve` and `generate_image` destructive and open-world: they spend the account's own credits
  and reach the studio's render providers; the quote-then-token flow is the confirmation step.
- `add_element` open-world: it fetches one picture or product page the person names, https only.
- Response-minimization findings (timestamps, ids): answers carry `created_at` and the ids a
  person needs to name things (`scene_id`, `gen:<id>`, job ids). If the reviewer asks, the
  timestamps can be dropped from the listed answers; tell me which tool.

### 6. Review details

**Metadata & Skills → Review information → Review details.** The test cases, the demo URL,
`commerce: false` and the release notes are imported from the ZIP. Enter by hand, in the portal
only:

- **Reviewer credentials:** the test account's email and password (Decision log 1), login URL
  `https://zeropage.studio/signin`, and these sign-in instructions:

  > Sign in at https://zeropage.studio/signin with the email and password (no code, no second
  > factor). The workspace "Billing test" opens with its project, elements and renders already in
  > it. Then connect the plugin: the OAuth sign-in it opens takes the same email and password and
  > a consent page with Allow. Every render asks for a quote first and runs only on an explicit
  > yes (the second call with the quote's token); the account holds enough credits for the cases.

- The five positive cases (imported; here for reference):

| # | prompt | tools | expected |
|---|---|---|---|
| 1 | Open my project Spring product spots and show me its scenes. | projects, project | the project's brief, look, scenes 400 and 408 with status, their reference photos, the latest chat turns; nothing rendered |
| 2 | Write a two-shot scene of the Tonal One headphones on a desk in soft window light, about 8 seconds, and save it to Spring product spots. | elements, write_scene | a new scene in the project with the headphones' photo as a reference; `scene_id`, two shots, `reference_photos: 2`, `rendered: false`, the studio link; nothing spent |
| 3 | What would it cost to render scene 408? | quote | keyframes and clip priced in credits beside the balance, signed tokens, the note to wait for a yes; nothing spent |
| 4 | Draw a still of a pair of headphones on a slate desk in soft window light. Yes, go ahead at that price. | generate_image ×2, job | the first call quotes (model, credits, `quote_token`) and draws nothing; the second starts a job; `job` ends done with the image and its `gen:<id>`; the balance drops once by the quoted credits |
| 5 | Make a square copy of my latest clip and give me a download link. | library, reformat, job, share_link | the clip listed; a 1:1 copy as a new `gen:<id>` at no cost; an https download link for 24 hours; balance unchanged |

- The three negative cases (imported): "Buy me 500 more credits." (no commerce: the plugin says
  credits are added in the studio and starts nothing); "Delete scene 400 and all my renders."
  (no tool deletes; every edit is a new item); "Show me scene 375." (another workspace's: "no scene
  375").

**Save details.**

### 7. Submit for review

Select the draft → **Submit for review** → the policy attestations (read each; they are the
guidelines' sections: usage policies, privacy, commerce, originality) → submit. Review status is on
the Plugins page; decisions come by email. One review at a time per plugin; **Cancel Review** to
replace the package.

### 8. After approval

**Publish plugin** when you choose. After that, tool changes on the server are picked up by a daily
scan (or **Rescan**); only metadata and skills need a new ZIP. The MCP URL cannot be changed later
without support.

## Rules this package keeps (the guidelines, read 2026-10-12)

- **Commerce:** nothing is sold through the plugin; no plans displayed, no checkout or upgrade
  page linked; a refusal says more credits are needed and that they are added in the studio. The
  person may use the credits of their existing account. (The rule allows a link to a purely
  informational plans page; ours starts a checkout, so no link at all is the safe reading.)
- **Names and descriptions:** no "MCP" or "Plugin" appended; no pricing, subscriptions, trials,
  discounts, promotions or comparisons.
- **Tools:** one tool per operation, explicit boolean annotations, minimal inputs, no tool takes
  the conversation (`save_chat` is not on this door).
- **Test credentials:** a dedicated account with sample data, a login and password, no MFA, no
  emailed code.
- **No UI, no screenshots.**

## Decision log

1. **Reviewer credentials** (2026-10-12): Mike does not want his Gmail as the reviewer login. The
   plan: invite a reviewer mailbox into `zp-billing-test` (`python -m src.accounts invite EMAIL
   --brand zp-billing-test --join-existing --name Reviewer`, with `DATABASE_URL` exported), sign in
   once to claim it, set a password in Settings → Account, and use that pair. Until that email
   exists, the credentials are the current member's. **Status: waiting on the mailbox.**
2. **Listing copy** (2026-10-12): the Runway register ("Generate images and video … right from
   where you're already working … No API key required"), chosen by Mike; the credit words left out
   under the commerce rule.
3. **Package name** (2026-10-12): `zeropage-studio`; the Claude plugin at the repository root is
   `zeropage-studio-skills` (pull 5) so the two read apart on GitHub.
4. **Two repositories** (2026-10-12): the ChatGPT package lives in
   `zeropage-onryo/zeropage-studio-chatgpt-plugin` (public, MIT); the Claude plugin stays in
   `zeropage-onryo/zeropage-studio-plugin`. The Claude repo's pull 6 (a `chatgpt/` folder) was
   closed as superseded.
