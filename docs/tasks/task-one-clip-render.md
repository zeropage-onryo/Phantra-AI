# One clip, cuts inside (2026-10-26)

Mike: "its also seperating the shots instead of combining them into one". Asked which he
wanted, he picked "One clip, cuts inside". Scene 453 (Gygler, 15s, three shots) had rendered
as three Grok clips, each made without seeing the other two, then joined. None of the three
was sent the scene's photos, because no keyframes had been drawn and Grok was called
text-to-video.

## The rule

`timeline.renders_as_one(shot, axis)` is the one place this is decided. A timed scene renders
as ONE generation when:

- its prompt has windows,
- no shot has a clip of its own yet (a scene that was split partway keeps resuming the split,
  so nothing is paid for twice), and
- its length (the last window's end) is at most the model's longest render.

Otherwise it splits, one clip a shot, as before. `PHANTRA_ONE_CLIP=0` turns the rule off.

## As built

- **Pricing** (`pricing._one_clip`, from `estimate_scene`): one `Estimate` with `part=None`,
  `one_clip=True`. Its length is the scene's, rounded UP to a length the model takes, and it
  includes the per-picture price where the model charges one (Grok, $0.01 a picture). Grok
  takes references only at 480p or 720p, so a one-clip render on Grok at 1080p is REFUSED
  (`references_resolution`), never quietly sent without the photos. `display` adds
  `one_clip` and `references`, keeps `timed` False, and issues one token.
- **The render** (`approve_render` -> `fal.generate_for_shot(one_clip=True)`): `timeline.ensure`
  plans the shots first, which is free. Then the scene's refs, in order and capped at the model's
  `ref_max`, go out through `as_image_url` on the REF2V endpoint. A photo that cannot be fetched
  is dropped and is not named in the prompt. A model with no REF2V row is sent no photos and is
  anchored on the first shot's still, or on the scene's own.
- **The prompt** (`timeline.one_clip_prompt`) is built from these parts:
  - the length and the shot count, with "cut hard";
  - `CONTINUITY`;
  - `PICTURES`, one line per tag, each giving the element's name and what the picture is for;
  - `THE WHOLE SCENE`, the scene's words outside its windows: its style, sound and avoid list;
  - each shot as `SHOT n (a-bs) [tags]: …` / `CUT TO SHOT n …`.

  The planner's `[k]` numbers are rewritten into the model's own tags. The prompt then passes
  through `for_render`, `prompts_for` and the kit's `dress`, as every target does.
- **The row** records `one_clip: true` and `references: n`. The clip attaches to the shot.
- **The studio**:
  - The Render card's button reads "Render · 3 shots, one clip · N cr", and the line under it
    says the scene renders as one clip held to your photos.
  - The chat's turn shows the one clip as "One clip · 3 shots inside", and the Final cut join is
    skipped because there is nothing to join.
- **The connector**: the `quote` description now says which of the two renders applies.

## Checked

- `tests/test_one_clip.py` covers the rule, the prompt, the price (Seedance, LTX, Grok) and
  what the adapter sends.
- `tests/test_timeline.py` has a new test that approves a whole scene as one clip.
- The tests of the per-shot split now pass `shot_by_shot`.
- Scene 453, rebuilt from the live row with its clips stripped (nothing was sent to fal):
  - Seedance 2, 15s with 3 photos: 1,093 cr.
  - Kling 4: 566 cr.
  - Grok 1.5: 512 cr.
  - Grok 1.5 Lite, which has no reference endpoint, so no photos: 108 cr.

## Not done

- **No live render yet.** It waits on Mike's yes.
- **Grok 1.5 Lite has no reference endpoint.** Scene 453's model, `grok1.5-lite`, therefore
  still renders it without the photos: as one clip, but unheld.
- **The landing pages still say "each shot renders as its own clip".** Wan, Kling and the AI
  video generator pages say so and need a copy pass. `/faq` is updated.
- **There is no "split it anyway" choice on the card.**
