# Camera move and Lens on the Video page

2026-11-03, Mike: "are you going to be able to wire in the camera move option and lens
options, also verify if thats only for select models". Board 12 of the Image & Video design
canvas is the look; this is version A (preset moves). Version B, a path you draw, comes later.

## What was verified (each model's fal schema, 2026-11-03)

- **LTX 2.5 Fast and Pro** have a camera setting, `camera_motion`: `dolly_in`, `dolly_out`,
  `dolly_left`, `dolly_right`, `jib_up`, `jib_down`, `static`, `focus_shift`.
- **No other clip model** (LTX 2.3, Kling 4.0, Kling 3 Turbo, Seedance 2.5 / 2.0, Veo 3.1,
  Wan 3, Grok 1.5) has a camera field. They follow camera WORDS; each vendor's guide says where
  (`prompts/models/*.md`).
- **No clip model has a lens setting.** Lens is words, written as what the lens does to the
  picture (Veo's guide names lens by effect).
- **Seedance 2.5 and 2.0 reference-to-video take video references** (`video_urls`, @Video1..;
  2.5 up to 10 clips, 30.2 s in all; 2.0 up to 3, 2-15 s, 480-720p). Luma's Seedance guide
  uses "Use @Video1 as the camera movement reference". Kling 4.0 takes `video_urls` too, but
  its page does not say it follows a reference's camera, so it is not listed.
- Mike declined Higgsfield DoP's presets (2026-11-03): the moves are Phantra's own.

## As built

- `prompts/camera.json`: 12 moves (words, the LTX value where there is one, `clip` = the R2 key
  of Mike's own reference clip, null until he shoots it), focal lengths, apertures, looks, the
  pairs that contradict (rack focus + f/11, dolly zoom + macro), and where each model family
  takes the camera line (lead: Veo, Seedance; tail: LTX, Kling, Wan, Grok).
- `src/camera.py`: `mode` (exact / clip / guided), `dress` (the prompt with the lines placed,
  the `camera_motion`, the `video_refs`), `menu_for`, `catalogue`. Off-table picks and
  contradicting pairs are REFUSED.
- `fal.build_body` / `generate_video` / `generate_from_prompt` take `camera_motion` (refused off
  a row's `camera_motions`) and `reference_videos` (REF2V `video_field`; a start frame and
  references are still either/or). Video references render on fal only: `generate_video`
  refuses one on Replicate before any hold, and `replicate.to_input` refuses one too
  (Replicate's Seedance price is "with no video input").
- `GET /api/direct/video` carries `camera` (the cards) and, per model, `camera` (its exact moves,
  the moves a clip can carry and at which resolutions). `POST /api/direct/video/run` takes
  `camera_move`, `lens_focal`, `lens_aperture`, `lens_look` (`direct.dress_video`); a dressed
  prompt past the model's cap is refused, never cut. The quote does not change: words and
  LTX's setting cost nothing.
- The page (`lib/camera.ts`, `direct-generator.tsx`): Camera and Lens chips in the Video dock,
  each move labelled Exact / Guided / Reference clip for the model on screen; what will be added
  shows as chips under the prompt, each removable. A pick that contradicts another clears it
  and says why.

## Open

- **Reference clips.** Mike shoots the 12 moves (5-6 s, 720p, plain subject); they go to R2
  under `site/camera/<id>.mp4` and their keys into `prompts/camera.json`. Then ONE quoted test
  render on the lowest settings (Seedance with the clip against Seedance with words, same
  still), approved by Mike, settles two things before `PHANTRA_CAMERA_CLIPS=1`: whether the
  move carries without the clip's look, and whether a video reference changes fal's price
  (the quote does not count it today).
- Hover previews of each move in the menu (board 12 has them; the dock list does not yet).
- The draw-a-path editor (version B).
- The connector and the Create brain do not offer these cards yet.
