# Group 12 progress -- showcase (branch `claude/overnight-showcase`)

Copy of the group's checkboxes from `docs/tasks/task-overnight-2026-10-22.md`, ticked as each lands.
The spend log is `showcase-log.md` beside this file.

- [x] Source clips -- 6 clips, LTX 2.3, 6s, 1080p
- [x] Free looks on those clips (0 credits) -- real module after the looks branch landed 01:26; fallback first
- [ ] Stills -- BLOCKED: 0 of 13 drawn. The session's MCP server (main checkout, older src/fal.py, FAL_DAILY_CAP default 6) refused every still after the six clips: "daily cap: 6/6". Each quoted at 10 credits (130 total); no retry, no other door (parent's call). The two 16:9 start frames (gen:160, gen:164) are the only stills made.
- [ ] Paid effects -- 0 of 5 run. Bullet Time (68) and Product Orbit (48): no source still (cap). 4K Smooth: quoted 236, HELD for Mike (ordering vs the stills' budget). Sound Pass: quoted 10, failed on the Supabase pooler before any fal call. Reframe: quoted 89, refused by the same daily cap.
- [x] Wire into the pages -- `web/public/showcase/manifest.json` v2 (six look entries with before/after/poster, `cards` mapping, `sources`, `pending` list for the 20 cap-blocked keys). Checked on a local three-way merge (effects-tab + create-page + looks, throwaway branch): /studio/effects lists Free · 6 and the Film Grade card plays the manifest clip on hover (docs/qa/screens-2026-10-22/showcase-effects.png, -grid.png); /studio is the current composer because the create_v2 web half was not built yet (showcase-create.png).
