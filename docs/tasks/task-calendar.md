# The calendar (2026-10-22)

PR 3 of the distribution build, on top of `task-publish-worker.md` (PR 2) and
`task-social-connections.md` (PR 1). The page that draws `posts`: where a post is, what state it
is in, and the one place a person moves, finishes or re-sends one. Nothing on it spends credits.

The design was settled on a canvas first (the "Phantra Publish Calendar" design artifact, Mike,
2026-10-22): the Postiz shape -- one calendar, one editor over it, provider settings folded
away -- plus six things taken from elsewhere, each named below with where it came from.

## As built

- **`/studio/calendar`** (`web/src/app/studio/calendar/`, `components/studio/calendar/`), a new
  rail entry and header tab beside Library and Timeline, found by ⌘K. Four views over
  `GET /api/posts`:
  - **Week**: 7 columns, 8 AM-8 PM drawn (the rest on scroll), past days hatched, today tinted
    with a "now" line. A card is the render's poster, the platform's own mark, the words, and
    its state. Drag a card to another hour -> `PUT /api/posts/{id}/date` (one toast, Undo puts it
    back). A sent post does not move.
  - **Month**: day cells with up to three chips and "+n more".
  - **List**: grouped by day with Upcoming / Needs you / Sent / Drafts; the refused row carries
    the platform's words and **Post again**.
  - **Feed** (Later's visual planner): one account's grid as it will look once the queue lands --
    upcoming tiles over the account's real recent posts (`GET /api/posts/feed?connection_id=`,
    the provider's `recent_media`, read at most once a day per connection and cached on the
    row). Drag two tiles to swap their dates. Offered for Instagram, TikTok, YouTube, X; a
    platform with no feed (Discord) is not offered.
- **The drawer** (`post-drawer.tsx`): opens on a card, a free slot, "New post", or a drop from the
  Library strip. Accounts are picked by clicking their avatars (Postiz: one clip to several
  accounts; each pick is its own `posts` row, one `group_id`; `POST /api/posts/group`). The
  preview is drawn in the platform's shape (Planable): an Instagram story / reel frame, a
  Discord message, a YouTube short. "When" defaults to the account's **next free slot**
  (Typefully) with Now and Pick a time beside it. The send button is split: Schedule, or Post now
  under its caret. A refused post shows the platform's reason, the log, Post again and Cancel.
- **Posting times** (Settings -> Connections, per account): weekday x slot, stored on the
  connection (`social_connections.meta_json.posting_times`, `GET/PUT
  /api/social/connections/{id}/posting-times`). The week draws them as dashed empty slots; the
  drawer's default reads `GET /api/posts/next-slot?connection_id=`. The worker never reads
  them: a post goes out at its own `publish_at`, which is what a slot fills in.
- **The Library strip** (Buffer's ideas column): unposted renders beside the week; drag one onto
  a day and the drawer opens with that render and time filled in. The Library's "Post…" door
  stays as it is.
- **"Needs you" on the Renders page**: refused posts (`GET /api/posts?state=error`) above the
  jobs, each with its reason and Post again.
- **State glyphs** (Linear): one ring, five fills -- hollow queued, half sending, full published,
  barred refused, dashed draft -- so a state reads without a legend and survives fading.
- **Platform marks**: the platforms' own glyphs from `simple-icons` (CC0), in their brand colours
  (TikTok and X are black marks and stay bone on the dark ground). LinkedIn is not in that set
  and gets a text mark until its provider lands with LinkedIn's own kit.
- **Keyboard** (Cron): `T` today, `←`/`→` week, `W` `M` `L` `F` views, `N` new post, `Enter`
  open, `Backspace` cancel a queued post (asks), `?` the list. Nothing on a keystroke sends.
- **X** joins the platform list (`db.PLATFORMS`, the calendar's chips and picks). Its provider is
  not in this PR; see below.

## Verified by running it (2026-10-22)

Against the dev database with two connections (Instagram, Discord), posting times on both and
posts in every state: the week, month, list and feed drew; the refused post's drawer showed the
platform's words, the log, Post again and Cancel; New post opened the picker, the avatar picks,
the next free slot (`Thu 6:30 PM` read from the connection) and the split send; a render dragged
from the strip onto Friday opened the drawer at that hour and Schedule wrote two rows in one
group; a card dragged to Saturday moved with an Undo toast; the feed read Instagram through the
stored token (which Instagram refused, so the note said so and the grid drew our own rows);
Settings -> Connections edited the times; the Renders page showed the strip. Two posts at one
hour share the column (lanes). Known: the floating assistant creature sits over the right-hand
columns on a 1440px window and takes the pointer there; that is the shell's, not the calendar's.

## Decisions made here

1. **The calendar is a reader with three writes**: move (`date`), state (`queued` /
   `cancelled`), and the drawer's create / patch. Every other door into `posts` already exists.
2. **One row per account, one group per press.** A fan-out to three accounts is three rows that
   can each fail on their own; the calendar shows three cards, the drawer shows the group.
3. **Posting times live on the connection, not in a table.** They are a preference of one
   account, read by the page and the drawer only.
4. **The feed's "published" tiles are the account's real feed**, read through the person's own
   token, once a day, cached under `meta_json._feed_cache` (keys that start with `_` never
   reach a page). Without the provider's `recent_media` the feed shows only our own posts.
5. **No library of drag-and-drop.** HTML5 drag events on the cards and the strip; the drop
   computes the hour from the pointer and calls the same route a click would.

## Not built, each its own step

- The X provider (OAuth 2.0 PKCE, chunked media upload, 280 characters, the paid API tier is a
  Phantra cost); TikTok through `posts`; YouTube, Facebook, LinkedIn, Reddit.
- Best-time heatmap under the week (Metricool) once the metrics pull reads a person's own token.
- Repeat posts as ghost cards (`repeat_days` on `posts`).
- Comments / threads (`parent_post_id`); a `/post` command in Create and `prepare_post` on the
  connector writing a draft row.
- Phone layout: the calendar is the editor's shape (no bottom-bar entry); List is the view that
  works narrow.
