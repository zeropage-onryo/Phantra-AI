# 05 — One real end-to-end render (gated on Mike)

**Not run. Nothing was generated and no credit was spent for this step.**

The task makes this step optional and gated: ask Mike first, with the quote, and do nothing until
he says yes and names a credit cap. The question was put to him in the session on 2026-11-02
(about 16:20 UTC) with this estimate, and no answer had come when the reports were committed:

| Stage | Cheapest path | Credits (public table, `web/src/content/pricing.json`) |
|---|---|---|
| One still | the cheapest image model, one still | ≥ 10 (`credit_floor`) |
| One 5 s clip | Grok Imagine 1.5 Lite, 5 s | 26 |
| Final Cut join | the editor's Assemble | 0 (free) |
| **Estimate** | | **~40–70**, exact quote to be read from the card before any click |

Proposed cap: 100 credits on the review workspace (5, `zp-billing-test`, 343 available).

If Mike says yes, this file gets: stage timings (submit → job queued → provider done → R2 file →
Library shows it → Final Cut joined), credits before / quoted / after, and the media addresses.
If he says no, this file will say "skipped by Mike".
