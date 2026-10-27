# Halloween costumes: one-tap try-on (2026-10-27)

Mike: "Ai halloween costume try on ... I want this out by today posting on socials", then
"i want it to be easy and one click", then "can this be a section of the effects tab".

## What a person does

1. Add a photo. Tap a costume (twelve: vampire, witch, pirate, skeleton, zombie bride,
   werewolf, mummy, devil, angel, ghost, scarecrow, black cat). Approve: a still of them in it,
   face kept. 10 credits (the floor; a new account's sign-up credits cover several).
2. Under that still, tap **Make it a video**: the Costume Try-On recipe on the ORIGINAL photo,
   the same costume carried over. Approve: 168 credits for 5 s, 336 for 10 s, 1080p.

Every spend is still its own priced card and Approve; nothing runs on a tap.

## As built

- `src/costumes.py`: COSTUMES (id -> our own wording, generic costumes only), `prompt_for`,
  `describe` (a picked name -> the full description). `prompts/effects/costume_preview.txt`.
- `src/effects.py` row `costume-preview`: Nano Banana edit, one image, prompt "none", the
  costume a required option (refused if off the list); `build_body` pops it into the prompt.
  Always listed (no flag): it is a plain still.
- `src/effect_recipes.py` recipe `costume_try_on` (behind PHANTRA_EFFECT_RECIPES, on on Fly):
  one spin and back in the costume; a picked costume name is expanded by `costumes.describe`.
- `src/mcp_server.py`: the listed `edit_image` takes `costume` (a costume with words is refused).
- `prompts/creative_guide_effects.txt`: Vesper's HALLOWEEN COSTUMES rule.
- Studio: the composer's effect card draws `costume` as one tap per value
  (`CHIP_OPTIONS`, effect-step.tsx); `/studio?open=costume` opens the card (from the home it
  moves to `/studio/chat` first -- the talking-photo CTA had the same gap and now moves too);
  a card opened before a photo binds to the first one attached; "Make it a video"
  (lib/continue.ts, create-view continueOn). The Effects page has a **Halloween Costumes**
  section above the strip, every costume shown with or without an example (the one seasonal
  exception to Mike's 2026-10-25 rule), the tiles also under Holiday and under the seasonal
  Halloween tab of `task-halloween-neon-effects.md` (`HALLOWEEN_IDS`); the section sits under that
  task's neon sign and leaves with it (`halloweenOn()`, HALLOWEEN_UNTIL 2026-11-03); "Make it a video" on a
  costume result puts the recipe in the panel with the original photo and the costume.
- `/make/ai-halloween-costume-try-on`: CTA opens the costume card (`cta.open: "costume"`).
- Tests: `tests/test_costumes.py` (5), `tests/test_effect_recipes.py` (+1),
  `tests/test_mcp_add_element.py`, web `continue.test.mjs` / `effects-wall.test.mjs`.
- Ran it: API + studio in the cloud container (Postgres 16 + pgvector, seeded account, minted
  session, fake FAL_KEY), Playwright at 1440 and 390: the link opens the card, a dropped photo
  binds, Vampire prices at **10 credits**; the Effects page section shows the twelve, Witch +
  a photo reads **Approve · 10 credits**; `/api/effects/quote` for the video: 168 / 336.
  Approve was never clicked: nothing ran, nothing was spent.

## Not done

- Example stills / clips for the tiles and the page (Mike's yes; ~10 credits a still, 168 a clip).
- The Effects page itself is behind PHANTRA_EFFECTS_TAB; the composer path works without it.
