# Reddit and LinkedIn, and the platform's own form (2026-10-22)

PR 4 of the distribution build, on `task-calendar.md` (PR 3). Two more providers in
`src/social/`, the per-post form a platform needs, and the operator's registration checklist.

## As built

- **`src/social/reddit.py`**: OAuth2 web app (`duration=permanent`, so the hour-long access
  token renews with the permanent refresh token), `User-Agent` on every call (Reddit refuses
  the default). A post is a LINK post to the subreddit named per post (`settings.subreddit`),
  the words as the title (300), optional `flair_id` / `nsfw` / `spoiler`. Reddit's own refusal
  (flair required, no links) comes back on the row in its words. `flairs()` reads a sub's post
  flairs for a later picker. Reddit's native video upload (media lease) is not built.
- **`src/social/linkedin.py`**: OpenID Connect + Share on LinkedIn (`w_member_social`), a
  member's profile only. The Posts API at `LINKEDIN_VERSION`: an image is initializeUpload ->
  PUT -> post, in one call; a video is initializeUpload -> PUT parts -> finalizeUpload, then
  PENDING until `GET /rest/videos/{urn}` says AVAILABLE, then the post (`post_finish`). The post
  urn comes from the `x-restli-id` header (`_request`, the one raw-response seam). Self-serve
  apps get no refresh token: at day 60 the card says Expired -> Reconnect.
- **A provider's `SETTINGS`** (`social.catalogue()` -> `settings`, `caption_max`, `feed`): the
  per-post form, declared once per platform (Reddit: subreddit / flair / NSFW; Instagram: story
  or reel; LinkedIn: who can see it). `components/studio/calendar/provider-fields.tsx` draws
  it in the drawer (one block per picked account) and in the Library's Post… panel; a required
  field empty disables the press, with the missing names on the button.
- **`posts.create_group(settings_by=)`** / `POST /api/posts/group {settings_by}`: one
  platform's form per connection, merged over the shared `settings`, checked in the dry run
  before any row is written.
- **`docs/ops/social-apps.md`**: every portal, field value, secret name and review, in the
  order the gates clear. X is pay-per-use now (about $0.015 a post, $0.20 with a link).

## Verified by running it

Against the dev database with four connections: the drawer drew LinkedIn's "in" mark and
Reddit's icon, the LinkedIn visibility select and the Reddit subreddit / flair / NSFW block;
Schedule stayed disabled with "Still needed: u/phantra: Subreddit" until the sub was typed,
then a press wrote two rows in one group with each platform's own settings. The providers'
HTTP is tested against recorded shapes (`tests/test_social_providers.py`); a real post waits on
Mike registering the apps.

## LinkedIn Pages (2026-10-23)

`src/social/linkedin_page.py`: a Company Page, on a SECOND LinkedIn app that carries only the
Community Management API (LinkedIn allows no other product beside it, so no OpenID sign-in;
the member is read off `organizationAcls`). Scopes `w_organization_social` +
`r_organization_admin`. The connect lists the Pages the member holds a posting role on (admin,
content admin, sponsored content poster); one finishes at once, several leave the row pending
on `page` and the settings card's picker says "Page". Posting is `linkedin.py`'s with the Page as
author and upload owner, always public. Programmatic refresh (a year) through
`linkedin.refresh_with`. One Page per member per workspace (the row's external_id is the
member). Off until `SOCIAL_LINKEDIN_PAGE_CLIENT_ID` / `_SECRET` are set, which waits on
LinkedIn approving the app. `linkedin.LINKEDIN_VERSION` moved 202506 -> 202609 the same day
(202506 had left LinkedIn's docs).

## X (2026-10-25)

`src/social/x.py`: a member's own account, OAuth 2.0 with PKCE (S256) on a confidential client,
scopes `tweet.read tweet.write users.read media.write offline.access`. The door gives a provider
only the signed, single-use state, so the PKCE verifier is an HMAC of it under the client secret,
derived again at the callback; nothing is stored between. Tokens last two hours and X rotates the
refresh token on every refresh, so `social_connections` now renews a LAPSED token that has a
refresh token on use (and lists it as connected, not Expired); a lapsed token with none is still
a reconnect. A post is `POST /2/tweets` (280 characters) with one media id from the v2 chunked
upload (initialize, 4 MB appends, finalize); a still posts at once, a video waits on
`processing_info` through `post_check`. A 4xx other than 429 is X's no (terminal), a 429/5xx goes
back for the worker's retry. Posting spends the developer account's prepaid credit
(docs/ops/social-apps.md). Off until `SOCIAL_X_CLIENT_ID` / `_SECRET` are set.

## Not built

- Reddit native video (kind=video with a media lease); the flair picker in the drawer
  (`reddit.flairs` exists, no route yet); subreddit search.
- A Reconnect reminder before day 60.
- TikTok on connections, YouTube, Facebook. X threads, polls and quote posts.
