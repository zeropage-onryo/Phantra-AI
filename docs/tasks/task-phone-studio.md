# The phone's studio (2026-10-26)

Mike compared phantra.ai and higgsfield.ai at phone size and asked for a simpler mobile studio "like
theirs". The design is the "Phantra Mobile Studio" canvas (nine phone boards); his answers on it: a
bottom bar of Home, Assets, a bigger Create button, **Effects**, Profile; a top bar with only the menu
(on the LEFT, his call) and the logo; the box resized for a phone; a signed-out send opens sign-up;
the Elements panel leak and the wrapping send button fixed; the phone homepage simplified.

## As built

Everything below applies under 720px only; the desktop is unchanged.

- **The chrome** (`components/studio/phone/phone-chrome.tsx`, `phone.css`): `PhoneTop` (menu + the website's owl lockup, 24px, the intro round once a session),
  `PhoneTabs` (Home `/studio`, Assets `/studio/assets`, Create `/studio/new`, Effects, Profile
  `/studio/me`), `PhoneMenu` (Projects, Video, Image, Elements, Brand kits, Calendar, Plugins,
  Settings). Drawn by `shell.tsx`; `studio.css`'s "THE PHONE, 2026-10-26" block hides the rail and
  the header there. Effects goes to `/studio/effects` when `effects_tab` is on, else to
  `/studio/new?open=effects` (the composer's gallery). The credit pill, search, the activity tray and
  New session are not on a phone's top bar; credits are on Profile. The floating assistant is not
  drawn on a phone (Create is Vesper's chat there).
- **Home** (`PhoneHome` in `components/studio/front/front.tsx`): the news as a swipeable row, four
  tools (Video, Image, Effects, Talking photo) and "Recreate in one tap" (the use cases; a tap fills
  the box and opens Create). On a phone `/studio` draws only this.
- **Create** (`/studio/new`, `(create)/new/page.tsx`): the compose page, a "home" in create-view's
  sense (a send moves to `/studio/chat`) with no front page. Greeting with Vesper and the first name,
  the starters as one row, the box at the bottom. The box's line on a phone is `+`, Image | Video,
  one model button and send (plus the still's credits when a send draws one); the rest of the line
  is folded into `PhoneModelSheet` (model, frame or shape, length). Nothing in the sheet prices.
- **Signed-out send**: `send()` opens `SignupSheet` before anything is asked of the server. The prompt
  is kept in localStorage for an hour and put back in the box (never sent) when the person lands
  signed in. Google and Discord go straight on through `/signin?provider=` (`app/main.py`, which
  stashes `next` first; a provider that is not configured shows the door as before).
- **Profile** (`/studio/me`, `components/studio/phone/profile.tsx`): avatar, plan, credits with Add
  credits, the settings sections, Help, Log out. Works on a desktop too, centred.
- **Fixes**: the element row under the box (`.row`) is not drawn on a phone (it ran on below Create
  as "No elements yet"); the box's line no longer wraps the send button; the Library's size slider
  is not drawn on a phone.
- **The public site**: the header's menu button is left of the logo on every public page (its sheet's
  close too, 44px). The homepage on a phone drops the starting points and the model strip, and its
  footer (`SiteFooter compact`) keeps Studio, Plans and Legal in two columns; the Tools and Models
  lists stay in the page for crawlers, hidden under 640px.

Tests: `web/tests/phone.test.mjs`, `front-page.test.mjs` (the compose page has no front page),
`tests/test_auth.py::test_signin_with_a_provider_goes_straight_on_and_keeps_next`.

Not done: the chat page (`/studio/chat`) keeps the 2026-10-23 "C2f" layout with the new box line;
the brain picker, the kit chip and Ask first / Auto are not in the phone's model sheet (their
defaults stand); the Assets page keeps its own header and chips.
