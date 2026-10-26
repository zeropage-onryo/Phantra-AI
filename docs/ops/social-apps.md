# Registering the social apps (2026-10-22)

What Mike does, once, so that any user can connect their own accounts under Settings ->
Connections. One developer app per platform, its keys as Fly secrets, three platform reviews.
The code side is `docs/tasks/task-social-connections.md` (the connect flow),
`task-publish-worker.md` (the sending) and `task-calendar.md` (the page); this file is only the
portal clicks and the values to paste.

Companion: the project doc `social_platforms_the_eight_2026-10-22.md` (why each platform is
shaped the way it is). Prices and review rules below are as of 2026-10-22 and drift.

## Before any app: three things every portal asks for

1. **Public legal pages on phantra.ai**, linked from the site footer:
   - `https://phantra.ai/privacy`
   - `https://phantra.ai/terms`
   - `https://phantra.ai/data-deletion` -- a page that says how a person removes their data
     (Settings -> Connections -> Disconnect wipes the token at once; Settings -> Account deletes
     the account; or email). Meta refuses a submission without this URL.
2. **The redirect URL**, the same shape for every platform, HTTPS only, no trailing slash:

       https://api.phantra.ai/auth/social/<provider>/callback

   `<provider>` is the id in `src/social/`: `discord`, `instagram`, `facebook`, `tiktok`,
   `youtube`, `linkedin`, `reddit`, `x`. The platform compares it character for character with
   what the server sends (`app/social_routes.py: redirect_uri`), so `SOCIAL_REDIRECT_ORIGIN` on
   Fly must be exactly `https://api.phantra.ai`.
3. **The vault key.** `SOCIAL_TOKEN_SECRET`: any long random string (`openssl rand -hex 32`).
   Every stored token is encrypted under it; change it and everyone has to reconnect. Set it
   before the first connect, never rotate casually.

Fly secrets are set with one command per batch and the app restarts once:

    fly secrets set -a phantra-api SOCIAL_TOKEN_SECRET=... SOCIAL_REDIRECT_ORIGIN=https://api.phantra.ai

## The apps, fastest to unlock first

### Discord (no review) -- built

- Portal: https://discord.com/developers/applications -> New Application "Phantra".
- OAuth2 -> Redirects: add `https://api.phantra.ai/auth/social/discord/callback`.
- Bot -> Reset Token (copy it once; Discord never shows it again). Privileged intents: none.
- Secrets: `SOCIAL_DISCORD_CLIENT_ID` (OAuth2 -> Client ID), `SOCIAL_DISCORD_CLIENT_SECRET`
  (OAuth2 -> Client Secret), `SOCIAL_DISCORD_BOT_TOKEN`.
- What a user does: Connect -> picks a server they manage -> the bot joins -> they pick the
  channel. Limit: 10 MB attachment on an unboosted server; bigger clips go as a link.

### Instagram (Meta App Review + Business Verification) -- built, testers only until review

- Portal: https://developers.facebook.com/apps -> Create app -> use case "Manage everything on
  your Page" is NOT it; pick **"Other"** -> type **Business** -> name "Phantra".
- Add product **Instagram** -> "API setup with Instagram business login" (NOT the Facebook
  Login route; the connect screen Mike pressed on Postiz is this one).
- Instagram business login settings -> OAuth redirect URIs:
  `https://api.phantra.ai/auth/social/instagram/callback`. Deauthorize callback and Data
  deletion request URL: `https://phantra.ai/data-deletion` (both fields).
- App settings -> Basic: Privacy Policy URL, Terms of Service URL, App icon (1024x1024), Category
  "Business and pages", **Business Verification** (App settings -> Basic -> Verification):
  Phantra's legal name, address and one document. This is the slow part; start it today.
- Secrets: `SOCIAL_INSTAGRAM_APP_ID` (the *Instagram app id* shown under the Instagram product,
  not the parent app id), `SOCIAL_INSTAGRAM_APP_SECRET` (the Instagram app secret).
- Until review passes, only people added under App roles -> Instagram testers can connect
  (they accept the invite in Instagram -> Settings -> Apps and websites -> Tester invites).
- **App Review**: Use cases -> the Instagram use case -> Permissions ->
  `instagram_business_basic`, `instagram_business_content_publish`,
  `instagram_business_manage_comments`, `instagram_business_manage_insights` -> request
  Advanced Access for each, with a screen recording of: Settings -> Connections -> Connect
  Instagram -> the Meta consent screen -> back in the studio -> Library -> Post... -> the post
  on Instagram. Two to six weeks; Meta usually asks one round of questions.

### Reddit (no review) -- next PR

- Portal: https://www.reddit.com/prefs/apps -> "create another app..." -> type **web app**.
- name "Phantra", redirect uri `https://api.phantra.ai/auth/social/reddit/callback`,
  about url `https://phantra.ai`.
- Secrets: `SOCIAL_REDDIT_CLIENT_ID` (the string under the app name), `SOCIAL_REDDIT_CLIENT_SECRET`.
- Reddit's Data API terms: free tier is 100 requests a minute per client; commercial use
  nominally wants their approval form (https://support.reddithelp.com/hc/en-us/requests/new ->
  Data API). File it; nothing blocks posting meanwhile.

### LinkedIn (no review for a member's own posts) -- next PR

- Portal: https://www.linkedin.com/developers/apps -> Create app: name "Phantra", a LinkedIn
  **Page** to associate (create "Phantra" as a company page first if there is none; the app
  must be verified by a page admin, Settings -> Verify), logo, legal agreement.
- Auth -> Redirect URLs: `https://api.phantra.ai/auth/social/linkedin/callback`.
- Products -> request **"Share on LinkedIn"** and **"Sign In with LinkedIn using OpenID
  Connect"**. Both self-serve, granted in minutes. (Company-page posting is the "Community
  Management API", a partner application that takes weeks and is not guaranteed; skip it.)
- Secrets: `SOCIAL_LINKEDIN_CLIENT_ID`, `SOCIAL_LINKEDIN_CLIENT_SECRET`.
- Tokens last 60 days and self-serve apps get no refresh token: at day 60 the card says
  Expired and the person presses Reconnect. Expected, not a bug; a warning email before that
  is a later step.

### X (no review; paid per post) -- next PR

- Portal: https://developer.x.com -> sign up for a developer account (as of 2026 new accounts
  are **pay-per-use**: prepaid credits, about $0.015 per post created and $0.20 when the post
  carries a link, no monthly fee; the $200 Basic tier is closed to new signups). Phantra pays
  this, not the user; a clip post with no link is the cheap case.
- Project -> App "Phantra" -> User authentication settings: **OAuth 2.0**, type "Web App",
  permissions **Read and write**, callback `https://api.phantra.ai/auth/social/x/callback`,
  website `https://phantra.ai`.
- Secrets: `SOCIAL_X_CLIENT_ID`, `SOCIAL_X_CLIENT_SECRET` (the OAuth 2.0 pair, not the v1.1
  consumer keys).
- Load a few dollars of credit before the first post or every post is refused with a billing
  error.

### TikTok (app audit; unaudited = private posts, 5 users a day) -- provider exists, needs moving onto connections

- Portal: https://developers.tiktok.com/apps -> Connect an app: name "Phantra", category
  "Video editing", platform **Web**, website `https://phantra.ai`, Terms and Privacy URLs.
- Add products **Login Kit** and **Content Posting API** (turn on **Direct Post**).
- Redirect URI (both products): `https://api.phantra.ai/auth/social/tiktok/callback`.
- Scopes: `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.publish`,
  `video.upload`, `video.list`.
- Secrets: `SOCIAL_TIKTOK_CLIENT_KEY` (16 chars), `SOCIAL_TIKTOK_CLIENT_SECRET` (32 chars).
- Do NOT add a verified media domain: the provider uploads bytes (`FILE_UPLOAD`), which needs
  none. (The old env-token `tiktok.py` used `PULL_FROM_URL`, which did.)
- **Audit**: once the app posts for Mike's own account, submit for review from the app page.
  They want a screen recording showing the user choosing privacy/comment settings and pressing
  Post themselves (the review page already is that screen), the legal pages, and the app's
  description. Two to four weeks. Until then: posts are forced `SELF_ONLY` and five users can
  post per 24 h.

### YouTube / Shorts (Google verification) -- built

- Portal: https://console.cloud.google.com -> New project "Phantra" -> APIs & Services ->
  Enable **YouTube Data API v3**.
- OAuth consent screen (Google Auth Platform): External, app name "Phantra", support email,
  logo, app domain `phantra.ai`, authorised domain `phantra.ai`, privacy
  (`https://phantra.ai/privacy`) and terms (`https://phantra.ai/terms`). Data access (scopes):
  `https://www.googleapis.com/auth/youtube.upload` and
  `https://www.googleapis.com/auth/youtube.readonly`, nothing else.
- Clients -> Create client -> Web application -> Authorised redirect URI
  `https://api.phantra.ai/auth/social/youtube/callback`.
- Secrets: `SOCIAL_YOUTUBE_CLIENT_ID`, `SOCIAL_YOUTUBE_CLIENT_SECRET`.
- While "Testing": up to 100 test users (Audience -> Test users), and their refresh tokens
  expire after 7 days (the card then says Reconnect). **Publish** the app, then **submit for
  verification** (sensitive scopes: a demo video of the OAuth flow and the upload, the legal
  pages); until verified, people outside the test list see Google's "unverified app" warning.
- Quota (videos.insert reference, read 2026-10-26): an upload is 1 unit of a separate Video
  Uploads bucket, 100 a day per project, and unverified projects' uploads are no longer forced
  private. A quota extension is a form in the console when 100 a day is not enough.

### Facebook Pages (same Meta app as Instagram) -- later PR

- Same app: add product **Facebook Login for Business**; Valid OAuth Redirect URIs
  `https://api.phantra.ai/auth/social/facebook/callback`.
- App Review for `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
  `business_management`, on the same submission as Instagram if filed together.
- Secrets: the parent app's `SOCIAL_FACEBOOK_APP_ID` / `SOCIAL_FACEBOOK_APP_SECRET` (these are
  the *Facebook* app id/secret from App settings -> Basic, different from the Instagram ones).

## The three reviews, one week, in parallel

| Review | Needs | Typical wait | Meanwhile |
|---|---|---|---|
| Meta (Instagram, then Facebook) | legal pages incl. data deletion, Business Verification, a screen recording, a sentence per permission | 2-6 weeks | app-role testers only |
| TikTok | legal pages, a screen recording of the user pressing Post | 2-4 weeks | 5 users/day, private posts |
| Google (YouTube) | published consent screen, a YouTube demo video, legal pages | 1-2 weeks | 100 test users, 7-day tokens, 100 uploads/day per project |

Record ONE screen video of: sign in -> Settings -> Connections -> Connect <platform> -> the
platform's consent screen -> back in the studio -> Library -> Post... -> pick the account ->
words -> Post now -> the post live on the platform. Re-use it for all three with the platform
swapped. Keep the raw recording; reviewers ask for re-takes.

## After the keys are in

- `fly secrets set -a phantra-api <the pairs above>`; the app restarts.
- Settings -> Connections -> "Connect an account" tiles turn from greyed ("not set up on this
  server yet") to live as each pair lands; nothing else to deploy.
- Connect your own accounts first; the first real post through each is the smoke test the
  reviews want recorded anyway.
- Rotation: a leaked client secret is regenerated in the portal and re-set on Fly; users do not
  reconnect (their tokens are under `SOCIAL_TOKEN_SECRET`, not the app secret).
