# Task — Bots: the Discord bot and the read-only Reddit listener

**Moved 2026-10-22** (Mike: "these bots need to be separate from main"). The code (`bots/`)
and this task file's full "As built", "Not verified" and "MIKE (later)" notes now live in
**`zeropage-onryo/phantra-growth`**, with their history. That repo is the place for anything
that lives out on other platforms to bring people in: the Discord bot, the Reddit listener,
later a Devvit app and growth agents.

Why they could leave cleanly: neither bot imports `src/` or `app/`, nothing here imports them,
they had their own requirements and venv, and CI here never ran their tests. They are clients
of this API over HTTP, as the plugins are.

What stays here:
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` in `.env.example`: the reference-image lane
  (`src/imagesearch.py`) reads them. The listener can use the same Reddit "script" app, set on
  its own host.
- **The bot's door (2026-10-26, settled):** not a new key on `/api` but a third kind of plugin
  token on the panels' door (`app/plugin_api.py`, `src/plugin_tokens.py` client `discord-bot`,
  label "Discord bot"). The bot pairs like a panel (a code approved at /studio/link by a member
  of the workspace it should file into), holds a revocable `php_` token (Settings ->
  Connections; dead after 90 idle days), and reaches ONLY `/plugin/v1/me`, `/upload`, `/looks`,
  `/looks/run` and `/jobs/{id}`: every `/tools/*` call and `/scenes/*` is 403 `not_for_bots`, so
  a leaked bot token can make free looks in that workspace and nothing else. `/looks/run`
  refuses (402 `not_free`) any row that is not free with 0 credits, and runs a free one through
  `api.start_effect_job`, the studio card's own job body. Tests: `tests/test_plugin_bot.py`,
  including a real upload -> Noir -> poll round trip through ffmpeg.
- So the API contract the bot codes to is those five routes. A change to any of them breaks the
  bot without failing a test here; phantra-growth's fake API answers in their shapes.

Found in the move: the Discord bot crashed on start (`from __future__ import annotations` in
`bot.py` hid `discord` from the annotations discord.py evaluates). Its wiring test always
skipped here because discord.py was never in this venv; it runs in phantra-growth's CI, and the
fix is there.

The overnight records (`task-overnight-2026-10-22.md`, `report-overnight-2026-10-22.md`,
`overnight-2026-10-22/progress-bots.md`) still say `bots/...`; they describe that night as it
was and are not rewritten.
