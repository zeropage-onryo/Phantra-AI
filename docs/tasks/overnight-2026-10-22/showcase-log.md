# Showcase slate -- spend log (group 12, 2026-10-22)

Account `phantra` (id 1), through the local `phantra-ai` studio MCP server. Hard cap 1,000 credits
(Mike, chat, 2026-10-22 00:27 ET). Every paid item is quoted first (a call without `quote_token`
spends nothing); an item runs only when running total + its quote <= 1,000.

Starting balance: 7527 credits (first quote, 2026-10-22 ~01:04 ET). Project: "Showcase 2026-10-22", id 4. Running total: 10
Final balance: (recorded at the end)

| time (ET) | item | tool | model | args summary | quoted | charged | result id | media URL | status |
|---|---|---|---|---|---|---|---|---|---|
| 01:05 | start frame for clip 1 (rooftop, 16:9) -- the studio connector's text-to-video is always 9:16 (`fal.DEFAULT_ASPECT`), so a 16:9 clip needs a 16:9 start frame; not a listed item in itself | generate_image | flux-pro1.1 | 16:9, project 4 | 10 | 10 | gen:160 | https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-20261022-050506.jpg | done |
