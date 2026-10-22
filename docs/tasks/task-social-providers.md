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

## Not built

- Reddit native video (kind=video with a media lease); the flair picker in the drawer
  (`reddit.flairs` exists, no route yet); subreddit search.
- LinkedIn Company Pages (partner program); a Reconnect reminder before day 60.
- X, TikTok on connections, YouTube, Facebook.
