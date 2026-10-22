# Showcase slate -- spend log (group 12, 2026-10-22)

Account `phantra` (id 1), through the local `phantra-ai` studio MCP server. Hard cap 1,000 credits
(Mike, chat, 2026-10-22 00:27 ET). Every paid item is quoted first (a call without `quote_token`
spends nothing); an item runs only when running total + its quote <= 1,000.

Starting balance: 7527 credits (first quote, 2026-10-22 ~01:04 ET). Project: "Showcase 2026-10-22", id 4. Running total: 542 (six source clips done: 522 + two 16:9 start frames 20)
Final balance: (recorded at the end)

| time (ET) | item | tool | model | args summary | quoted | charged | result id | media URL | status |
|---|---|---|---|---|---|---|---|---|---|
| 01:05 | start frame for clip 1 (rooftop, 16:9) -- the studio connector's text-to-video is always 9:16 (`fal.DEFAULT_ASPECT`), so a 16:9 clip needs a 16:9 start frame; not a listed item in itself | generate_image | flux-pro1.1 | 16:9, project 4 | 10 | 10 | gen:160 | https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-20261022-050506.jpg | done |
| 01:06 | clip 2: woman under a streetlight, wet sidewalk, night, 9:16 | generate_video | ltx2.3 | 6s 1080p, text-to-video, project 4 | 87 | 87 | gen:161 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-050516.mp4 | done |
| 01:08 | clip 1: friend walking across a rooftop at sunset, 16:9 | generate_video | ltx2.3 | 6s 1080p, image-to-video from gen:160, project 4 | 87 | 87 | gen:162 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-050657.mp4 | done |
| 01:08 | clip 3: friends at a dim house party laughing into the camera, 9:16 | generate_video | ltx2.3 | 6s 1080p, text-to-video, project 4 | 87 | 87 | gen:163 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-050720.mp4 | done |
| 01:08 | start frame for clip 5 (coastal road, 16:9) -- same reason as clip 1's | generate_image | flux-pro1.1 | 16:9, project 4 | 10 | 10 | gen:164 | https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-20261022-050824.jpg | done |
| 01:09 | clip 4: barber spins the chair to reveal a fresh fade, 9:16 | generate_video | ltx2.3 | 6s 1080p, text-to-video, project 4 | 87 | 87 | gen:165 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-050824.mp4 | done |
| 01:11 | clip 5: cyclist on a coastal road, wide, 16:9 | generate_video | ltx2.3 | 6s 1080p, image-to-video from gen:164, project 4 | 87 | 87 | gen:167 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-051004.mp4 | done |
| 01:11 | clip 6: candle maker pouring wax into jars, 9:16 | generate_video | ltx2.3 | 6s 1080p, text-to-video, project 4 | 87 | 87 | gen:166 | https://media.phantra.ai/m/1/renders/fal/wf-20261022-050959.mp4 | done |
| 01:12 | stills batch 1 (dancer 4:5, headphones 1:1, three 16:9 heroes) | generate_image | seedream4.5 / flux-pro1.1 | project 4 | 10 each (50) | 0 | -- | -- | REFUSED before submit: "daily cap: 6/6 images generated today (FAL_DAILY_CAP to raise)". Holds released; balance 6985 confirmed by a free quote. The session's MCP server runs from the main checkout (commit 6a9d8d57), whose older src/fal.py defaults FAL_DAILY_CAP to 6 (main: 200); the counter is this account's fal VIDEO rows since UTC midnight, and images and effects check the same count. |
| 01:15 | 4K Smooth: Topaz upscale x2 + 60 fps on clip 5 | apply_effect | upscale | gen:167, {upscale_factor: 2, target_fps: 60} | 236 | 0 | -- | -- | HELD, not run: fits the cap (542 + 236 = 778) but would leave 222, less than the 246 the cap-blocked stills (130) + Bullet Time (68) + Product Orbit (48) need if the server's daily cap is lifted tonight; the parent's order puts the stills first, so this is the parent's call. (Also now blocked by the daily cap below.) |
| 01:16 | Sound Pass: MMAudio on clip 6 | apply_effect | add-sound | gen:166, prompt "wax pouring into glass jars, quiet studio ambience" | 10 | 0 | -- | -- | FAILED before any fal call: Supabase pooler "max clients reached in session mode (pool_size: 15)" (other sessions on this Mac hold the pool). No retry (the rule allows retries for source clips only, and the daily cap below closes the door anyway). |
| 01:16 | Generative Reframe: Luma Ray 2 Flash, clip 5 to 9:16 | apply_effect | reframe | gen:167, {aspect_ratio: "9:16"} | 89 | 0 | -- | -- | REFUSED before submit: "daily cap: 6/6 images generated today" -- the effects door reads the same count on this server. |
