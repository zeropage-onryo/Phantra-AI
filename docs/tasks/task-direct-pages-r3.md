# Task: Image, Video and Brand kit pages, r3 (the design-canvas picks)

**From:** Mike, 2026-10-26: "can you do a resign for image, video, and brand kit pages", ten
directions per page on the design canvas, then: "i like 5 for image but panel on the left side.
for video 2 is good. for brand kit i like 1 and 4 when you go inside it. … make sure we are
thinking about all parts, including ui of reference images, renders, drop downs, buttons, etc".
**Branch:** `claude/studio-pages-r3`. **No flag**: a restyle of live pages over the same routes.
**Design canvas:** the "Phantra studio pages — directions" artifact (the old Effects canvas):
rows "Image / Video / Brand kit pages · 10 directions", then "Picked · every state" (18 boards:
a Parts sheet, five Image states, five Video states, seven Brand screens). Those boards are the spec.

## The rule the parts follow (the Parts board)

- **A yellow fill is the one button that spends**, and it always carries the server's price
  (`Generate · 189 credits`). Faded until there is a prompt and a price; "pricing…" while the
  server is asked; a spinner with "Starting…" once clicked.
- **A white fill confirms without spending**: Add (the picture picker), Read the site, Make the
  kit, Save. Everything else is an outline pill or a round icon button.
- Yellow also marks what is PICKED (a tab, a shape, a model's check), never an action.
- Menus are one card everywhere: a raised dark card, 18px radius, rows with a name, a one-line
  note and the price in mono on the right, a check on the pick; they open downward from a panel
  and upward from the dock; Esc and a press outside close them.

## Image (`/studio/image`, "Image 05", panel on the left)

`components/studio/direct-generator.tsx`, `.dgi` in `direct-generator.css`.
- **Panel** (left): the model dropdown, the prompt with its count, the references tray (64px
  thumbs with a remove button, Upload and Library tiles, "2 of 12" or "not sent" on a text-only
  model, whose pictures fade with NOT SENT and a line before the click), shape pills drawn as
  their frames, the Generate pill. Dropping a file anywhere on the page lights the panel.
- **Stage** (middle): the still being looked at, drawn, or not made. On a first visit, the
  starters (a tap fills the prompt; nothing runs). While drawing: the first reference blurred
  behind, the held credits, Cancel while the job says it can be cancelled. Done: the model, frame
  and credits as chips, then Reuse settings, Animate (Video with it as the start frame), Use in
  Create, Open in Library, Download. Failed: "Not made" with the reason, Add credits when that is
  why, and Use these settings, which only refills the panel (the spend is still Generate).
- **History** (right): this visit's makes with their state, then the Library's newest stills; a
  click puts one on the stage, nothing navigates.

## Video (`/studio/video`, "Video 02", theatre + dock)

`.dgv`. The theatre is the same Stage; the strip on the right is the same History in 9:16.
The **dock** under the theatre holds the pictures (START tag on one start frame, `@Image1…` tags
on references, which drop into the prompt at the caret when tapped), the prompt (as long as the
model takes, counted), and chips that open upward: Model (all models with price, longest take and
how many pictures), Length, Resolution, Frame (shape pills; "Frame follows the picture" with a
start frame), the Start frame / Reference switch for one picture on a reference model, and
Generate. `keptLine` still says when a model change moved a length or a frame.

## One state under both (what did not change, and what did)

Unchanged: the menus (`GET /api/direct/{image,video}`), the server's quote for exactly the pick on
screen, the run carrying `expect_credits`, a 409 re-pricing with "Nothing ran", the remembered
pick, `?model=`, `?prompt=`, `?start=`. Changed: the quote is now kept with the pick it was asked
for (`priced.key`), so nothing calls setState inside an effect (the two lint errors main had are
gone); a 409 bumps a nonce to ask again. The link's prompt and start frame are read once into the
initial state. New: the **picture picker** (Library stills and Elements photos, pick several,
Add N; `getElementPhotos`), **Reuse settings** (`lib/direct.ts reuseOf`: the prompt, and the
model only when this page's menu still has it), **Cancel** (`cancelJob`, only while the job
says `cancellable`), the starters (`STARTERS`), `modelBadges`, `refsCountLine`.
The assistant's creature is drawn at 150px on these two full-height pages and sits at the foot of
the history column, which keeps room for it (the shell's `.view::after` clearance would have been
a second grid row).

## Brand kits (`/studio/brand`, "Brand 01"; `/studio/brand/<id>`, "Brand 04")

`app/studio/brand/brand.css` (bk-), both pages.
- **Library**: a hero with "Brand kits" and the website reader as one bar (Read the site, the job's
  step while it reads, then a link to the new kit), then big cards: the kit's background with its
  logo (or its name in its heading font), the palette, "Aa" in the kit's own font with the font
  names, the name and how many projects use it. Hover or focus shows the Use menu
  (`UseKitMenu`, which now takes `buttonClassName` and `label`), Duplicate and Delete (Undo, as
  before). Blank kit is the last tile and opens a name box in place.
- **One kit**: the bar (back, the name edited in place, how many projects use it, Use this kit,
  Duplicate, Delete, then Save as a white pill only while there are changes, else a quiet
  "Saved"), then tabs (Identity, Visual, Look, Voice, Sound, Products & characters), one section
  per tab, the preview column beside them as before. The tab is kept in the address (`#look`). A
  problem that holds Save puts a dot on its tab (`brand-kit.ts tabOfProblem`) and the line above
  the form. Every field, file slot and rule on the page is the one it had; only the frame changed.

## As built (2026-10-26)

- Tests: `web/tests/direct-r3.test.mjs` (4), `web/tests/brand-kit-tabs.test.mjs` (2). All 373 web
  tests, typecheck, eslint on the changed files and `next build`: clean. No Python changed.
- **Ran it** on the local stack (API on a throwaway Postgres, `next dev` proxying): every state on
  the boards was clicked through in Chromium, 1440x1000 and 390x844 (no sideways scroll). The
  Library reads and the RUN were stubbed in the browser (local files, a fake job), so Generate was
  pressed without reaching the server: running, Cancel offered, done, failed, 409 untouched. The
  quotes were the real local server's (Kling 4.0 5s 720p: 189; 10s: 377; Veo 3.1 6s: 576).
  Two local test kits were made in the throwaway database; the website reader was stubbed.
