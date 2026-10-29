# The scene hook (2026-10-29)

Mike asked: "how do i incorporate these effects as hooks in my ai videos". The answer: the
Final cut (ffmpeg, free) can open on a short effect clip drawn from the scene's first frame,
then hard-cut into shot 1.

## As built

- **Where the hook is stored**: on the first shot, as
  `shot["hook"] = {"asset": "gen:<id>", "seconds": 2}`. It sits outside the shot's prompt
  and refs, so `pricing.content_hash` ignores it and no quote goes stale
  (`tests/test_cut_assemble.py::test_the_hook_is_outside_the_quote_hash`).
- **Routes** (both free):
  - `PUT /api/scenes/{id}/hook {asset, seconds}`. The clip must be a video in this
    account's Library and not deleted. `seconds` must be 0.5 to 5; anything outside that is
    refused, not clamped.
  - `DELETE /api/scenes/{id}/hook`. The clip stays in the Library.
  - Both rewrite only the first shot, and keep the scene's warnings, duration and `ai`.
- **Assemble** (`src/cut/assemble.py`):
  - `hook_of(concept)` reads the hook.
  - `plan()` puts the hook first when its row belongs to this account. Otherwise it adds a
    note and the cut goes on without it.
  - `build_doc` trims the hook to `seconds`. The frame size comes from the scene's own first
    clip, never from the hook.
  - The job result carries `hook: true`.
- **Studio**:
  - Under a finished Final cut, an "Add a hook" outline pill opens the effects gallery on
    the Animate tab. The gallery is bound to the scene's first keyframe, or its first
    reference when there is no keyframe (`lib/final-cut.ts hookStill`).
  - The pick is an ordinary priced card, and that card is the only spend.
    `EffectState.hookFor` carries the scene.
  - When the effect's clip lands, `create-view` sets the hook and joins the cut again. Both
    steps are free.
  - The line under the cut then reads "Final cut · hook + N shots", followed by
    "Change the hook" and "Remove the hook".
- **The assistant's prompt**: `prompts/creative_guide_effects.txt` tells the assistant to
  point the person at "Add a hook" instead of calling apply_effect, and to offer it at most
  once, after a Final cut lands.

## Verified

- **Backend**: all 41 tests in `tests/test_cut_assemble.py` pass. One of them is a real
  ffmpeg join that opens on a 1.5s hook, for 13.5s in total.
- **Studio**: clicked through on the local stack. The quote, run, job, hook and assemble
  routes were stubbed, so nothing reached fal.
  - The card was bound to "the scene's first frame", and Approve ran it.
  - `PUT hook {"asset":"gen:55","seconds":2}` and `POST /cut/assemble` then fired, and the
    line under the cut changed.

## Not done

- The studio always sets a 2s hook; only the route accepts other lengths (0.5 to 5s).
- The gallery opens on the Animate tab. The recipe effects (Window Grab and the rest) appear
  there only where `PHANTRA_EFFECT_RECIPES=1`, which Fly has.
