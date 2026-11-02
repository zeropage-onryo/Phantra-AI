# Task: Seedance and real people (2026-11-02)

Mike, 2026-11-02, after the host test: "do option 1" -- route scenes with a real person
away from Seedance before building the cheaper Seedance host.

## What the test found

Mike's own headshot (`characters/michael/07-headshot-frontal-neutral.jpg`) as a Seedance 2.5
reference, 5 s, 720p, 9:16, the same request on two hosts:

| Host | Answer | Charged |
|---|---|---|
| fal (`bytedance/seedance-2.5/reference-to-video`) | 422 `content_policy_violation`: "may contain likenesses of real people or other private information that cannot be processed", reason `partner_validation_failed` | nothing |
| Replicate (`bytedance/seedance-2.5`) | failed in 3 s: "The input or output was flagged as sensitive. (E005)" | nothing (no output seconds) |

The refusal is ByteDance's, on every host. BytePlus ModelArk (ByteDance's own API) is not open
to US sign-ups. Seven of the eight refused renders in the 2026-10-27 audit were content-filter
blocks, most likely this. Not yet tested: a real person as Seedance's FIRST FRAME (image-to-
video) rather than a reference, and Kling 4.0 / Veo 3.1 with the same photo (each a paid
render if it works).

## As built

- `src/people_refs.py`: `REFUSE_REAL_PEOPLE` (the three Seedance rows), `FOR_PEOPLE`
  (`kling4`, `veo3.1`), `holds_person` (a `subject` role or a character element's photo,
  through `asset_shelf.parse_ref`), `note_for(model, shot)` and `card_fields(shot)`.
- **Advice, never a lock.** `GET /api/scenes/{id}/render` carries `holds_person`,
  `people_refusers` and `people_note`; the Render card shows the note under its reason line
  when the picked model is one of the refusers. `/quote` adds `people_note` for its pick. A
  drawn creature held as a character still renders on Seedance; the note says "if".
- `failures.plain`: the refusal reads "won't take a photo of a real person as a reference.
  Render this shot on Kling 4.0 or Veo 3.1 instead", not "reword it".
- `prompts/model_picks.txt`: a real person from their own photos goes to `kling4` or `veo3.1`,
  never a Seedance model; several pictures, one long take and "the best a clip can look" say the
  same.
- Tests: `tests/test_people_refs.py`.

## Open

- The Replicate adapter for Seedance (non-people shots, about half fal's price at 480p/720p;
  no 1080p there).
- Test Kling 4.0 and Veo 3.1 with a real person's photo before calling them the people models
  in copy (about $0.79 and $2.40 for 5-6 s at 720p).
- The direct Video page (`src/direct.py`) takes uploads with no role, so it cannot tell a person
  in advance; its refusal now reads as above.
