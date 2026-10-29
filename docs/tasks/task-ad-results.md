# Task: ad results and A/B versions

Mike, 2026-10-29, after reading Runway's "Runway Ads is now available" email: build the two
missing pieces of a Runway-Ads-style loop on top of the Ad Studio. (1) Variants: several
versions of one ad, each changing one thing, proposed as one plan. (2) Results: what each ad
did once it ran, read back from the person's own ad account, so Vesper writes the next ad from
what won. Runway's pitch is an agent that "knows your campaign results"; this is the cheapest
honest version of that.

## The join: the ad code

Every Library output has an **ad code**, `PH<generated_assets.id>` (`ad_results.code_for`,
`web/src/lib/ad-results.ts adCode`; `tests/test_ad_results.py` holds the prefix equal on both
sides). The Library viewer shows it under Details with Copy. The person puts it in the ad's
NAME in Meta or TikTok Ads Manager (or its URL parameters, `utm_content=PH4821`). An imported
row whose name carries a code of THIS account's render is tied to it; a code of somebody
else's matches nothing; a row with no code is kept and listed as unmatched.

## Results: `src/ad_results.py`

- **Import** (`POST /api/ad-results/import`, multipart `file`, `mutation_header`): the ad-level
  report exported as **CSV** (an .xlsx is refused with "export as CSV": there is no spreadsheet
  reader in requirements, and both ads managers export CSV). `parse` matches headers loosely
  (lower case, a trailing currency like "(USD)" taken off and kept as the currency) against
  `FIELDS`: Meta's "Ad name", "Amount spent (USD)", "Reporting starts/ends", "Results", "Link
  clicks", "Purchases conversion value"; TikTok's "Ad name", "Ad ID", "Cost", "Clicks
  (destination)", "Conversions", "Date"; a plain CSV with the same words works too. Needs an ad
  name and a spend column, or it is refused before anything is written. The totals row (no ad
  name) is skipped and counted. A decimal comma ("40,00") is read as one.
- **Kept once per ad and window**: OWNED `ad_results`, unique on (account, platform, ad id or
  name, start, end), upserted. The same export twice changes nothing; a later window adds.
  Money is stored in the export's own currency and never converted. It is the person's own ad
  spend, not a Phantra price: the studio still shows credits for what Phantra charges.
- **An ad that ran is a keep**: the first import that shows spend on a render writes
  `outcomes.record("ad_run")` (new in `outcomes.KEPT`), with `teach=False` so an import makes
  no model call.
- **Undo**: `DELETE /api/ad-results/imports/{id}` takes one import's rows back out.
- **Read**: `GET /api/ad-results` (`summary`): every ad summed over its windows, with its code,
  render, scene, variant, spend, results, cost per result, CTR and return on spend; the tests;
  the last imports. Never raises.

## Versions: `make_plan` `variant` / `test`

- A plan's **scene** step may carry `variant` (the one thing this version changes, 60 chars)
  and the plan a `test` (what the versions test, 120). Labels only: nothing is priced or run
  differently, and a clip still waits for its own button. Two versions with one label refuse
  the plan; a `variant` on any other step is dropped; a `test` with no versions is dropped.
- The studio's plan runner sends `variant`, `variant_group` (the plan's id) and `variant_test`
  with the scene step's `POST /api/scenes/run`; the route files each written scene in OWNED
  `ad_variants` (`record_variant`, never raises). The card shows "Testing: …" and each
  version's label.
- `prompts/studios/ads_turn.txt` tells the Ad Studio brain to answer "variants / A/B / a few
  hooks" with one plan of 2-4 scene steps, each the same ad with ONE thing changed, and to tell
  the person once where the ad code goes.
- **Verdicts** (`tests`): cost per result decides, only between versions in one currency with
  results; "too early" until the best has `MIN_RESULTS` (5).

## The brain and the connector

- Every Ad Studio turn (a workspace with the add-on) is told the account's best costs per
  result and its tests' verdicts (`studios.results_note` -> `ad_results.note`), so the next ad
  builds on what won. Outside the Ad Studio, nothing.
- `what_works` on the connector carries `ads` and `ad_tests` and says them in `lines`.

## The page

`components/studio/ads/ad-results-panel.tsx` ("05 Results" under the four steps): how it
works in two sentences, a drop zone, the import's one-line outcome and the unmatched names,
one card per test with its verdict, a table (ad, spent, results, per result, CTR, return; it
scrolls inside its own box on a phone), and the last report with Remove. Open to every account
(their own data, nothing spends); the brain reads it only inside the add-on.

## Verified

- `tests/test_ad_results.py` (17): codes, parsing both exports, refusals, the import's scoping
  and idempotence, the `ad_run` keep, undo, variants as a test, verdict rules, plan labels, the
  brain's note, the routes (guard, scope, refusals) and the scenes route filing a version.
  `tests/test_make_plan.py` spec test updated for `variant`.
- `web/tests/ad-results.test.mjs` (6), the whole node suite, `npm run typecheck`.
- Clicked through on a local API + `next dev`: dropped a Meta export on `/studio/ads`, two
  rows matched their renders, the third listed as unmatched, the test card called "Hook: the
  spill" the winner at 10.00 vs 24.00 per result, Remove took the report back out; at 390px
  the page does not scroll sideways (the table scrolls in its box).

## Open (Mike)

- The Meta and TikTok Ads APIs (a direct pull instead of a CSV) wait until a paying client
  needs them: each is an app review.
- Next from the earlier list: a client review page (approve and comment on a batch), and an
  ad-policy pass in `render_qc` (platform rules, not just product fidelity).
