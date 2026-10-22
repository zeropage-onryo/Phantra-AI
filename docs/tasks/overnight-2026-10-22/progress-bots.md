# Progress: bots (group 8), 2026-10-22

Ticked here, never in the task file.

- [x] Discord bot scaffold at `bots/discord/` (discord.py): `/look` with an attached clip and a dropdown of the free looks, `/makeitpro`; results post as the clip in a thread with "Open in Phantra"; per-server tracking link; clip limits 15s / 100 MB; per-user daily cap. Public installable app, calls the API, free looks only, no DMs except the one welcome on join. Done when `pytest bots/discord -q` passes against mocked Discord and API clients; no token in the repo.
- [x] Reddit listener at `bots/reddit_listener/` (PRAW, read-only): six subreddits, intent phrases, alerts to email or a Discord webhook; never posts or comments. Done when tests pass with recorded fixtures and a test asserts no write method on the Reddit client is ever called.
