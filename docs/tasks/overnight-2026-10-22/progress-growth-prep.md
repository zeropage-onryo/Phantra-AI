# Progress: group 7, growth prep (branch `claude/overnight-growth-prep`)

- [ ] Cost table: per effect and per model, provider cost vs credits charged, from `src/effects.py` and `fal.VIDEO_MODELS`
- [ ] Free-grant math: the largest signup grant that keeps the Founding 500 offer's worst case at the doc's ceiling, using real markups
- [ ] Ledger safety tests: concurrent holds can't double-spend one balance; a failed provider job refunds; a replayed Stripe webhook grants once
- [ ] Abuse check: how many accounts one person can farm free credits with; list the guards that exist and the ones missing
- [ ] Rename residue: for each file in "State right now" that contains "zeropage", say whether `rename-allowlist.txt` covers it
