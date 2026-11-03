# Draft on Veo 3.1 Fast, redo on Veo 3.1

2026-11-03. Mike: "go ahead with the next cost cut" (the second half of Phase 2 in the
pricing plan, `docs/tasks/task-competitive-pricing.md`).

## Why Veo

Draft-then-finish (`src/drafts.py`, 2026-10-11) drafts at a model's cheapest FRAME and
finishes with a Topaz upscale. That already covers Seedance 2.5 (480p, now on Replicate at
about $0.10/s) and Wan 3.0. It could not cover Veo 3.1: one flat rate ($0.40/s at 720p and
1080p), so there is no cheaper frame. Veo 3.1 is also the dearest clip in the table and the
thinnest margin (1.15x since 2026-11-02). Every take a person throws away on it costs them
46 credits a second and leaves us about 6 cents.

Veo 3.1 Fast ($0.15/s, 1.5x) takes exactly the same inputs: lengths 4/6/8, 720p/1080p, the
same aspect ratios and negative prompt (`tests/test_drafts.py` pins that). A draft there costs
the person about 40% of a Veo 3.1 take and earns more per second than Veo 3.1 does.

Cross-family drafts (an LTX draft for a Seedance final) were left out on purpose: a take on
another model's family does not predict the final's look or motion, so it is not a draft.

## As built

- `fal.DRAFT_MODELS = {"veo3.1": "veo3.1-fast"}`, `fal.draft_model`, `fal.finish_model`. Only
  pairs that share every legal input go here.
- The catalogue (`providers._fal_models`) carries `draft_model` beside `draft`.
- The Render card (full card, not the chat's Approve-only card) shows "Draft first · Veo 3.1
  Fast · cheaper" for Veo 3.1. It only changes the pick (`withSiblingDraft`, keeps length and
  frame); the priced button reads "Draft · ...". The priced button is still the one click that
  spends.
- **Finishing is a re-render**, not an upscale: a different model cannot reproduce a take.
  `drafts.redo_of(concept)` lists the shots whose clip was made on a quick sibling;
  `GET /api/scenes/{id}/render` returns it as `scene.redo`. The card shows "Redo the draft on
  Veo 3.1 · priced next"; `POST /api/scenes/{id}/redo` (`drafts.clear_for_redo` ->
  `timeline.clear_clips`) takes those clips off their shots, free, and the card re-prices the
  scene on Veo 3.1. Only those shots are quoted and rendered (the loop skips shots that keep
  a clip). The drafts stay in the Library.
- `drafts.of_row` is unchanged: the Library and Renders never offer the upscale Finish on a
  Veo 3.1 Fast clip.
- The connector's `draft_first` workspace preference drafts Veo 3.1 on Veo 3.1 Fast too.

## Not done

- No UI click-through yet; the routes are covered by `tests/test_drafts.py`, the helpers by
  `web/tests/render-choice.test.mjs`.
- The chat's Approve-only card has no draft toggle (by design, 2026-10-23); a draft from chat
  is picking Veo 3.1 Fast on the settings line, which Vesper already proposes for first passes
  (`prompts/model_picks.txt`).
