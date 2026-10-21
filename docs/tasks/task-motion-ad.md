# A motion ad from a brief: the AI places the graphics

Status: **BUILT 2026-10-20**, on Mike's "build the AI does the placing part".

## What it is

The Gygler reference is a motion-graphics ad, not footage: big type over flat brand colours, one
huge faint word behind each line, product screens on cards, a label now and then, and the logo at
the end. The editor's graphics track (`docs/tasks/task-motion-graphics.md`) can draw all of that,
but only by hand. **Make a motion ad** (the Edit page, beside "Start from scratch") does the
placing:

1. **The person** writes a brief, picks a project (its brand kit is the look), a length (10-60s), a
   shape, and up to 8 product screenshots for cards.
2. **The brain writes the script** (`src/cut/motion_ad.write_beats`, `prompts/motion_ad_prompt.txt`).
   It is ONE structured Gemini call, stage `motion_ad`, free on a plan and behind the Create gate.
   It returns a title and 3-15 beats, each with:
   - a headline
   - a big word
   - which screenshot it shows, and its caption
   - a label
   - which brand colour it sits on (background or primary)
   - its seconds
3. **Code checks it** (`clean`). Every fix is a warning, never a refusal:
   - the beats are fitted to the length
   - over-long text is shortened
   - a screenshot that isn't attached is dropped
   - empty beats are left out
   - **any number on screen that the brief and the brand never give is flagged** ("check it is
     true")
4. **Code places it** (`layout`, pure):
   - **V1:** one flat-colour still per beat. `backgrounds` draws them with Pillow and files them in
     the bin, content-addressed.
   - **Graphics tracks:** G1 the big words, G2 the headlines (to the left when a card is on the
     right), G3 the cards (sliding in), G4 the labels, each timed inside its beat.
   - **Type colour:** always reads on its background (`ink_on`: the brand primary where it reads,
     else the brand colour that stands out most). A label on a primary beat gets the other colour
     as its pill.
5. **It is saved as a new cut** (`make`), filed under the studio project with the new
   `cut_projects.studio_project_id`, so the kit's captions and end card reach its export.
   `brand_kits.for_cut` is the one resolver: the scene's project, else this. Version 1 is
   authored `agent`, "motion ad: N beats".

Nothing renders and no credits are spent. The person opens the cut in the editor to keep, change
or throw away.

## Routes

`POST /api/cut/motion-ad` `{brief, project_id?, seconds, aspect, cards: [handles]}` starts a job,
which ends with `{cut_id, title, beats, warnings, brand_kit}`. It refuses:
- someone else's project (404)
- a card that isn't one of the caller's stills (400 `not_a_still`)
- a length off 8-60s (422)
- an account the Create gate refuses (402, before any job)

## The walk

On a throwaway schema, with the bucket and every renderer key blanked:
1. **Stubbed brain:** the dialog made a 21.9-second "Meet Gygler" cut: six beats, the talent card
   twice, two labels, the end card at export.
2. **The real brain**, once, on Mike's word (one Gemini text call on the local key): it wrote a
   clean five-beat script with no fixes needed, which was exported and looked at.
3. **What the real call showed:** it **invented "4.9 Stars" and "$26 / hr"**. The prompt now
   forbids facts the brief or the brand don't give, and the code flags any number that slips
   through. Not re-run after the fix; the tests cover it.

## Not built

- **Music:** the audio layer isn't built.
- **Generated product screens:** cards show only the person's own stills.
- **Footage beats mixed in:** a final cut from #392 under the graphics.
- **Graphics from the connector:** no MCP change was made.
- **A "regenerate one beat" button:** today the person edits a beat in the Inspector, or makes the
  ad again.
