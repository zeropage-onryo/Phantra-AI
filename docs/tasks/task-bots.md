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
- The API contract the Discord bot codes to: `GET /api/effects`, `/api/effects/quote`,
  `/api/effects/run` with `expect_credits`, `/api/jobs/<id>`, `POST /api/cut/media`. A change to
  any of these breaks the bot without failing a test here; phantra-growth's fake API answers in
  their shapes.
- The open API decision: the bot's identity is a minted `phantra_session` cookie today; a
  service-key bearer door on `/api` bound to one workspace is the right fix, and it is built
  here when it is built.

Found in the move: the Discord bot crashed on start (`from __future__ import annotations` in
`bot.py` hid `discord` from the annotations discord.py evaluates). Its wiring test always
skipped here because discord.py was never in this venv; it runs in phantra-growth's CI, and the
fix is there.

The overnight records (`task-overnight-2026-10-22.md`, `report-overnight-2026-10-22.md`,
`overnight-2026-10-22/progress-bots.md`) still say `bots/...`; they describe that night as it
was and are not rewritten.
