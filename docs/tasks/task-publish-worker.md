# Posts and the publish worker (2026-10-22)

PR 2 of the distribution build, on top of `task-social-connections.md` (PR 1). A post is one
clip or still, going to one connected account, at one time; the worker is the clock that sends
it. The calendar that draws these rows is PR 3.

## What shipped

- **`src/posts.py`** -- the OWNED `posts` and `post_events` tables. A row names its connection
  (so provider, account and token follow), carries its source (`gen:<id>` / `asset:<id>`, with
  what the worker needs written down at creation), the caption, provider settings, `publish_at`
  and a state: `draft -> queued -> publishing -> published | error`, `cancelled`. `create` runs
  every check the worker would otherwise fail on at 3am while a person is watching: the
  connection is this account's and finished, the source is this account's, the caption fits the
  platform, the kind of media is one the platform takes. The person's moves (`set_date`,
  `set_state`, `update`, `remove`) never touch a row in `publishing`; only the worker lands a
  post.
- **`src/publish_worker.py`** -- one tick every 20s: claim the due rows with
  `FOR UPDATE SKIP LOCKED` (flipped to `publishing` under this worker's name in the same
  statement, so two workers never send one post), `post_start`; poll the pending rows on their
  own schedule, `post_check` then `post_finish`; mark a row a dead worker left in `publishing`
  with nothing pending as `error`, never re-sent on its own (the platform may already have it).
  A 5xx or no answer goes back to the queue with a backoff (five tries, then error); the
  platform's no (`PostFailed`) and a token that needs the person (`ConnectRefused`) are terminal
  at once, in plain words on the row. A landed post writes `release_id` / `release_url`, a
  `videos` row with the concept (the audience loop `preprod.posted_outcomes` joins and
  `src.refresh_metrics` reads back) and `outcomes.record("post")` on the render. Runs as a
  third supervisord program on Fly (`ops/fly/supervisord.conf`); `python -m src.publish_worker
  --once` is one tick.
- **The providers post.** `src/social/base.py` gained the contract (`PostResult`,
  `PostFailed`, `post_start` / `post_check` / `post_finish`, `check_post`, `CAPTION_MAX`).
  Discord: one message from the bot to the picked channel, the file attached when it fits an
  unboosted server's 10 MB, else linked (Discord draws the link as a player); completed in one
  call. Instagram: the container -> `status_code` poll -> `media_publish` -> permalink, three
  functions so the row sits pending between polls instead of a thread waiting a minute per
  post; a check after a finish answers completed, never publishes again.
- **`app/post_routes.py`** -- `/api/posts` (list by window and state, create, get with its log,
  patch, move, state, delete), each scoped to the caller's account.
- **"Post…" on a render** (`components/studio/post-panel.tsx`, in the Library viewer beside
  Make element and Effects): the connected account, the words, Now or Later, one button. With
  no account connected it says so and links Settings -> Connections.
- `db.PLATFORMS` names the seven platforms a `videos` row may carry.

## Decisions made here

1. **A Postgres loop, not Temporal.** The rows are the durable state; `SKIP LOCKED` is the
   claim. One Fly machine, one more supervisord line, no new service.
2. **A stuck row is an error, not a resend.** A worker that died between the platform's answer
   and the write may have posted; the person checks and presses Post again.
3. **The platform's no is never retried.** A refused post arriving five times is worse than one
   error with the reason on it.
4. **Creation checks, not worker checks.** What can be refused is refused while a person is
   there to read it.

## Not built, each its own step

- The calendar (PR 3): the week/month views over `GET /api/posts`, drag to move, the editor on
  a slot; the Renders page listing errors with Post again.
- TikTok through `posts` (today the TikTok review page still sends on its own, operator token).
- Provider settings forms (Instagram story vs reel, Discord embeds); comments / threads
  (`parent_post_id`); repeating posts.
- A metrics pull for Discord (there is none) and for Instagram through the person's own token
  (`src.refresh_metrics` reads the operator's).
- `src/scheduling.py` (the 2026-09 queue over the operator's env tokens) is superseded by
  `posts` and left in place until the TikTok lane moves over.
