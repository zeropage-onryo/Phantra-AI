# Task: Seedance 2.5 on Replicate (2026-11-02)

Mike, 2026-11-02: "go ahead with the replicate adapter". Phase 2 of the plan in the project doc
**Phantra Pricing vs Competitors — Cost-Cutting Plan**. Stacked on
`claude/seedance-people-routing` (#552), itself on `claude/competitive-pricing` (#547).
**Nothing here is live until Mike merges, sets the token on Fly and deploys.**

## Why

fal charges exactly 2x ByteDance's per-token price for Seedance ($21.40 vs $10.70 per million
tokens on 2.5). ByteDance's own API (BytePlus ModelArk) does not sign up US accounts. Replicate
resells it at ByteDance's rate, read off replicate.com/bytedance/seedance-2.5 on 2026-11-02:

| Seedance 2.5 | fal | Replicate | Credits, 5 s (1.4x) |
|---|---|---|---|
| 480p | $0.2205/s | **$0.1028/s** | 155 -> **72** |
| 720p | $0.4730/s | **$0.2312/s** | 332 -> **162** |
| 1080p | $1.164/s | not offered | 815 (stays on fal) |

Seedance 2.5 refuses a real person's photo on both hosts (`task-seedance-people.md`), so the
move loses nothing on faces.

## As built

- `fal.VIDEO_MODELS["seedance2.5"]["hosts"]["replicate"]`: the Replicate model and its two rates.
- `fal.host_for(model, resolution)`: "replicate" when the row has a rate for that tier and
  `PHANTRA_REPLICATE` is not "0", else "fal". Key-free and deterministic, so the card, the
  quote, the hold, `pricing.json` and the render agree. `price_per_second` prices that host.
- `fal.generate_video`: no `REPLICATE_API_TOKEN` is a refusal BEFORE the hold (never a quiet
  fall back to fal at twice the price shown). Otherwise the same body (`build_body`), the same
  hold, the same `fal_requests` receipt (model_id `replicate:bytedance/seedance-2.5`), and
  fal's own `_submit_and_wait` with `submit_url` = Replicate's predictions URL and
  `http` = `replicate.queue_http()`.
- `src/replicate.py`: `to_input` (fal body -> Replicate input: `@ImageN` -> `[ImageN]`,
  `image_url` -> `image` with `aspect_ratio: "adaptive"`, `image_urls` -> `reference_images`, an
  integer duration, unknown keys dropped), `as_fal` (a prediction in fal's queue shapes:
  IN_PROGRESS / COMPLETED, `error` + `error_type`, `{"video": {"url"}}`), `queue_http` (POST
  submit, GET read, fal's CANCEL sentinel posts the cancel URL).
- `fal_requests._recover_one`: a `replicate:` receipt is read through `replicate.queue_http`;
  every other step of the sweep is shared.
- `failures.plain`: Replicate's "flagged as sensitive" reads as a declined prompt.
- `PRICING_VERSION` `2026-11-02-fal-v6`; `pricing.json` regenerated (Seedance 2.5: 162).
- Tests: `tests/test_replicate.py` (host choice, price, translation, shapes, an end-to-end
  render through a fake Replicate, no token, a refusal, a cancel, the sweep).

## Before deploying

- `fly secrets set REPLICATE_API_TOKEN=r8_... -a phantra-api` (the token Mike made on
  2026-11-02, in his `.env`). Without it every 480p / 720p Seedance 2.5 render refuses.
- Replicate is prepaid: keep a balance there, or renders fail with 402 "insufficient credit".

## Open

- Seedance 2.0 / 2.0 Fast on Replicate: rates not read yet; add a `hosts` entry when they are.
- A live 720p render on Replicate with a non-person reference, to check the bill matches
  $0.2312/s and the look matches fal (Mike's approval; about $1.16).
