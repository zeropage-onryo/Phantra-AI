# Vesper vs invideo, Higgsfield and Runway — five briefs, 2026-10-24

The same five briefs went to each tool, word for word: 1 (bare still), 2 (vague ad), 8 (named
look), 9 (model question) and 13 (mood). Vesper's runs are from the audit's 0c harness
(`docs/qa/vesper-audit-2026-10-24/briefs_fast.json`, `briefs_reasoning.json`; brief 13 was not
in that set). The competitors' transcripts are word for word in `invideo.md`, `higgsfield.md`
and `runway.md`. LTX has no chat agent on its free plan (`ltx.md`). The rule everywhere was: tap
the first suggestion, or say "you decide", and stop at the first generate. Nothing was
rendered on any competitor.

Spend:

| Tool | Spent | Charged for |
|---|---|---|
| invideo | 37.3 credits | thinking turns (up to 9.1 for a turn) and one auto still |
| Higgsfield | 6.14 credits | the two GPT 6 Astra turns; Auto turns were free |
| Runway | 0 | chat is free |
| LTX | 0 | |

## Turns to the first priced card

| Brief | Vesper Fast | Vesper Reasoning | invideo | Higgsfield | Runway |
|---|---|---|---|---|---|
| 1 coffee cup | 1 (no questions) | 1 | 2 (a 4-question form; it then drew without asking, on "Always allow") | 1 | 1 (2 questions) |
| 2 "help me make an ad" | **never** (asks for a photo every turn) | **never** | 3 (a 5-question form, then "you decide") -> a timed script + a "Script go?" form | 1 (2 questions) -> a key-visual still | 1 (3 questions, from the **brand kit**) -> a priced motion-graphic plan |
| 8 Wong Kar-wai | 2, a draft scene (asked for a photo first) | 1, a scene | 1, a hero still | 1, a 160-credit Seedance video | 1, a hero still |
| 9 talking head | never named a model in 3 turns | 2 (Talking Photo card) | 1 answer (by starting point) | 1 answer (by starting point + a rule of thumb) | 1 answer (a pick from the person's Quality setting, + alternatives + a draft model) |
| 13 "3am…" | (not run) | (not run) | 1 form (3 questions) | 1 question (5 options) | 1 question (5 options, one of them the brand kit) |

## What every competitor does and Vesper does not

1. **A missing photo never blocks.** No competitor asked for a photo before making
   something.
   - invideo and Runway draw a **hero still first** and animate it. Runway gives the reason:
     "The central subject (the man) isn't pinned down, so I'll lock the look with a start
     frame first."
   - Higgsfield goes text-to-video, or makes a key visual for an ad.
   - Vesper asked "drop a photo" on every turn of brief 2 on both tiers, and first on brief 8
     Fast. That is our reference gate speaking through the brain, and it is the one dead end
     all three avoid.
2. **The approval card shows the prompt and the settings, and the prompt sent is the one
   shown.**
   - invideo: the full prompt in an **editable** box, the frame and the model as chips, and
     "Approve · 2.50 credits".
   - Runway: the prompt, then Aspect Ratio, Quality, Model and Credits.
   - Higgsfield: the prompt, then model · frame · length · resolution · quality on a video,
     but no frame on a still.
   - Vesper's step card shows a prompt that `/api/generate/run` then rewrites (audit 0b: 6 of
     6). This confirms rank 1. A card whose words differ from what runs is the one thing no
     competitor does.
3. **A model question is answered in one turn, by what the person starts from.** All three
   did it: from a photo / from a clip / generating it all; or one take vs a series vs a fixed
   voice. Each named a cheap model for drafts or a lipsync step, and offered next steps.
   Vesper Fast asked about the photo three times and never named a model.
4. **When the person defers, the agent decides and says what it locked** (invideo: "Locking it
   myself: brand is RISE, one confession line, clean-focus/no-crash claim, 9:16"). Vesper
   answers a deferral with another question.

## What only one or two do (worth taking)

- **The brand kit as default context** (Runway). "Help me make an ad" was answered from the
  account's Gygler kit: its audiences, palette, type, tagline and URL. Its questions were
  about the brand, not "what are you selling". An open brief's options included "Gygler
  on-brand piece". The kit was NOT put into the unrelated coffee still. Today Vesper sees a
  kit only through a project or the "Kit: none ▾" pick.
- **Deny asks why** (invideo). Six chips:
  - Prompt needs a clearer direction
  - Add or change the references first
  - Use a more suitable model for this
  - Adjust the settings before generating
  - This is not aligned with the brief
  - I want to revise it before generating

  That is a labelled discard signal at the cheapest moment. Our live data has 4 discard
  events in total (audit section 1), so this feeds the metric directly.
- **An ad is a script before it is a render** (invideo, Runway): a timed table (time ·
  visual · audio, or time · on-screen words), a word count and read time ("9 words. Estimated
  read: 4 seconds"), and ranked alternative hooks, all shown before any video spend.
- **Video prompts as shot lists with locks** (Higgsfield): timed shots with a size and an
  "Outgoing:" frame per cut, then Camera law / Grade / Audio, then counts and continuity
  locks ("Count of hard cuts: two… The same man, the same shirt, the same plastic bag in all
  three shots"). Our timed windows have the shape; the locks block is new.
- **Questions only when the brief is open.** All three asked 0 questions on brief 8 and 2-5
  on briefs 2 and 13. Asking style:
  - Higgsfield and Runway: one at a time, "1 of 3", numbered chips, Skip.
  - invideo: one form with every question at once, chips plus free text.

  Vesper's single question per turn with three chips is close enough; the conflict is in the
  instruction files (audit 0a), not the shape.

## What not to copy

- **Inventing a brand or a claim and saying nothing.** Higgsfield's ad still invented
  "VOLTAIC", "ZERO SUGAR" and "200MG CAFFEINE" and printed them on the can. invideo invented
  "RISE" but said so, and kept the claim "lifestyle only (no medical)".
- **A big render with no question and no draft.** Higgsfield proposed 160 credits for brief 8
  with no cheaper pass. Our draft-then-finish is the better rule.
- **The prompt and the card disagreeing.** Higgsfield's prompt said "1.85:1 framing" while
  the card said 16:9. That is the same kind of conflict as our 9:16-vs-4:5 (audit 0b), so
  frame-from-one-place stays in task 1.
- **Pricey thinking.** invideo charged 8-9 credits for some text-only turns. Our "model text
  is free on a plan" is a real advantage.

## Named look (brief 8), side by side

- Higgsfield, Runway and Vesper Reasoning all **dropped the director's name and wrote the
  craft** (step-printing, jade or emerald against sodium orange, anamorphic, neon haze).
  invideo kept the name and the films, and added the craft.
- Vesper Fast kept the name ("STYLE: Wong Kar-wai").
- Every tool agreed on the craft words. This is not where we lose.
