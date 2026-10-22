# Social connections: a person's own accounts, connected to their workspace (2026-10-22)

Mike, 2026-10-22: TikTok, YouTube (and Shorts), Facebook, Instagram, LinkedIn, Reddit and
Discord, all connectable per account, all on one calendar. This is PR 1 of that build: the
connections layer, with Discord and Instagram as the first two providers. The review that
shaped it is in the project docs (`postiz_review_and_phantra_scheduling_plan_2026-10-22.md`,
`social_platforms_the_eight_2026-10-22.md`): Postiz's `Integration` row and `SocialProvider`
interface, in this repo's shape, and no Temporal.

## What shipped

- **`src/social_connections.py`** -- the OWNED `social_connections` table (one row per channel:
  provider, the platform's own id, display name / handle / avatar, the token Fernet-encrypted,
  expiry, scopes, `meta_json`, a `pending` in-between step, `refresh_needed`, soft delete).
  `save` upserts a live channel in place; `remove` soft-deletes and WIPES the token; `token_for`
  is the one reader (newest finished connection, renewed inside seven days of expiry, marked
  for reconnect when a renewal fails or the token lapsed). `ensure(dsn)` is the per-process
  init for processes no start made the table in. The vault key is `SOCIAL_TOKEN_SECRET`, else
  `SESSION_SECRET`; with neither set explicitly a connect is refused, because a generated
  secret would strand every token at the next deploy.
- **`src/social/`** -- the providers. `base.py` holds the shared types (`Connected`, `Renewed`,
  `ConnectRefused`) and the one HTTP function each module wraps as its own `_http`, the seam
  tests patch. `discord.py`: the combined "add the bot to a server" + `identify` grant, the
  server named in the token response, `PENDING_STEP = "channel"` with `options` (text and
  announcement channels, read with the bot's token) and `pick`. The BOT token
  (`SOCIAL_DISCORD_BOT_TOKEN`) is what will post; the person's token is kept only so the row
  says who connected it. `instagram.py`: Instagram Business Login, exactly the four scopes the
  consent screen shows, the short-lived token exchanged for a 60-day one, renewal through
  `refresh_access_token`, and a grant without `instagram_business_content_publish` REFUSED
  rather than stored.
- **`app/social_routes.py`** -- `GET /auth/social/{provider}/start` (this origin's session ->
  the platform; signed out here -> `/signin?next=<settings page>`) and
  `GET /auth/social/{provider}/callback` (the platform -> a row -> the settings page with
  `?connected=`, `?error=` or `?pick=`). The `state` is signed under the session secret with its
  own salt, ten minutes, and carries the workspace, the person and a nonce that must also be
  in this origin's starlette session, so a start URL from one browser cannot finish in another.
  `/api/social/providers`, `/connections`, `/connections/{id}/options`, `/pick`, `DELETE` are the
  settings page's, each scoped to the caller's account.
- **`publish_review.token_for`** asks the connections first; the operator's env token answers
  only when the account has no connection of its own, only for TikTok, only for
  `PUBLISH_OPERATOR_ACCOUNT`. A connection that needs reconnecting is said so, never papered
  over with the operator's token.
- **Settings -> Connections** (`web/src/components/studio/settings/social-accounts.tsx`): the
  connected accounts (avatar, the platform's own name for it, a status word: Connected / Pick a
  channel / Reconnect / Expired), the Discord channel picker inline on its row, a two-click
  Disconnect, and one tile per provider this server has keys for (a provider with no keys is
  shown greyed as "not set up on this server yet"). Connect is a top-level navigation to the
  API origin (`AUTH_ORIGIN`), the way sign-in goes.
- `.env.example` documents every variable; `tests/test_social_connections.py` holds the vault,
  the scoping, the state checks, the partial-grant refusal, renewal, the Discord pick and the
  `token_for` precedence.

## Decisions made here

1. **The callback is on the API origin, and the connect button navigates there.** A platform
   redirects to ONE registered URL and it has to be the server holding the app secret. The
   studio's proxy would have set the nonce cookie on the wrong origin, so the start route is
   reached by navigation, not fetch.
2. **Tokens are sealed on the row, not in a separate table.** The deleted BYOK `account_keys`
   envelope, back, under its own secret.
3. **Discord is a server + a channel, and the bot posts.** One grant, then a pick; the person's
   own token never posts.
4. **A grant that cannot publish is refused.** The Instagram toggle the person can switch off.
5. **Disconnect wipes the token at once** and keeps the row as history; reconnecting is a new row.

## Not built, each its own step

- Posting through a connection (the publish worker and the `posts` model), scheduling and the
  calendar -- PR 2 and 3 of the plan.
- TikTok, YouTube, Facebook, LinkedIn and Reddit providers (the order and each one's review is
  in `social_platforms_the_eight_2026-10-22.md`). TikTok's provider should switch
  `src/tiktok.py` to `FILE_UPLOAD`, which removes the media-domain verification.
- A daily token-refresh pass (today a token renews on the read that needs it).
- Listing the servers a person admins before the Discord grant (today Discord's own screen
  picks the server).
- Registering the developer apps and filing the reviews: Mike's, on each platform's console.
