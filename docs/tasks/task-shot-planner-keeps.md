# Task: the shot planner keeps what it was handed (2026-10-22)

Three studio bugs Mike reported on one food scene, fixed on branch
`claude/youthful-davinci-om2yy4`:

1. Rewriting a scene into timed shots dropped the photos that came from the Library
   (the dish and the chef were renders, not elements).
2. The shot planner threw away a voiceover line instead of keeping it or warning that
   it would not fit.
3. A scene could render with shots that had no photos at all, and nothing warned.

All three have one shape: the planner (`src/timeline.plan`, one model call on
`prompts/shot_timeline_prompt.txt`) is ASKED for something and nothing checked its
answer. `parse_response` already enforced the windows and the closed set of refs; it did
not notice a reference on no shot, a shot with no refs, or a sentence gone missing.

## As built

- **`timeline.caption(url, roles)`** is what the planner reads under a reference's number,
  in the list and under each picture. It was `shootgen.reference_label` alone, which is `""`
  for a render, so a still or a frame attached out of the Library was listed as a bare
  `[3]`. Now it is `ref_roles.label`: the role the person put on it, else the element's name
  and kind, else `RENDER_CAPTION` for a render, else "Reference photo attached to this
  scene:". `plan` and `ensure` take `roles` (the shot's `ref_roles`) for it.
- **`timeline.keep(result, scene, windows, refs, roles=)`** runs on every timeline, planned
  or split (`plan`, and the connector's `write_scene`, which splits with no model), and
  returns the warnings stored as `timeline["warnings"]`:
  - a reference that is not look-only (`ref_roles.LOOK_ONLY`) and sits on NO shot is put on
    every shot, in the scene's order (the fallback's own grounding for that one picture:
    under-grounding a shot costs the face), with "reference N (...) was on none of the
    planned shots -- it is now on every shot". `describe_ref` names it: the role, the
    element, "an earlier render from the Library", "an uploaded photo".
  - a shot left with no refs stays as planned (an empty hallway needs no portrait) and is
    said: "shot N (a-bs): no reference photos on this shot -- it renders from its words
    alone". The scene-level reference gate is unchanged; this is advice, never a refusal.
  - a voiceover line (`voice_lines`: "VO:", "V.O.:", "Voiceover (warm):", "Narrator:",
    "Narration:"; the quoted words, else to the end of the line or the next label) written
    in a window's own words is appended to that shot's prompt when the planner's prompt
    does not carry its words (`VOICEOVER, as written: "..."`); one written outside every
    window (the scene's) goes on the continuity, which `render_prompt` puts in front of
    every shot. A line longer than its seconds at `VOICE_WORDS_PER_SECOND` (2.5, the same
    pace `src/voiceover.py` budgets) is a warning either way: "the voiceover is N words,
    about Xs to say, and the window is Ys -- it will not fit".
- **`_TAIL` has a `voice` kind**: a voiceover label after the last window is the scene's
  tail, like the sound line, unless earlier beats carry their own (then it is the last
  shot's, as before).
- **The card prints them.** `_timeline_card` carries `warnings` (only off a CURRENT
  timeline, `timeline.warnings_of`; a stale one says nothing and is re-planned on read),
  `_concept_card` appends them to the scene's own `warnings` (the drawer's list), and the
  Render card lists them under its note (`render-card.tsx`), in the signal colour, not as a
  lock: Render stays pressable.
- **The prompt asks for the same**: every photograph of a person, product, dish, prop or
  place on at least one shot; a render caption is a subject, not a style note; a voiceover
  line stays in its shot word for word.
- Tests: `tests/test_timeline.py` ("what the planner must not lose") and the connector's
  `test_a_voiceover_that_will_not_fit_its_window_is_said_on_the_written_scene`.

## Not done, on purpose

- A part's refs still cannot be edited by hand; the keep rule is why a warning alone was
  not enough.
- `source_hash` does not include roles: changing a reference's role does not re-plan.
- A voiceover is NOT turned into audio here. Each shot is its own clip; the line reaches
  the video model's prompt (Veo and others can voice it) and the editor's voiceover (Audio
  tab) is still where a narrator is recorded over the cut.
