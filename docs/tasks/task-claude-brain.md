# Claude as a priced brain (2026-11-02)

Mike: "add the claude brain as an option and you can choose two models like Higgsfield, it's
priced. Then we will work on the generality."

## As built

- **Two rows in the picker**: `gemini_utils.BRAINS["claude-sonnet"]` (Claude Sonnet 5.5) and
  `["claude-opus"]` (Claude Opus 5.5, thinking HIGH). Shown only when `PHANTRA_CLAUDE_BRAINS=1`
  and `ANTHROPIC_API_KEY` is set (`brain_available`); otherwise a Claude pick resolves to the
  default brain. No silent fallback to Gemini from a failed Claude turn: it raises, like Reasoning.
- **A facade, not a second code path** (`src/claude_client.py`): `generate_with_retry` hands a
  `claude-*` model to a client that takes Gemini's types and returns a real
  `GenerateContentResponse`, so the Guide's tool loop, the scene writer and the planner are
  unchanged. Tool-use ids ride in `FunctionCall.id`; thinking rides as `thought` parts with its
  signature; structured output goes through `output_config.format` (schema closed, bounds
  dropped); thinking is adaptive + effort. The SDK's own retries are off (`max_retries=0`).
- **Priced** (`src/text_charge.py`): the picker prints "about N credits a message, never more
  than 40 / 80". The route holds the ceiling BEFORE the job (402 `out_of_credits` on a short
  balance), `claude_client.tally()` adds up what the turn cost, and the job settles to
  `pricing.text_credits(usd)` (markup 2.4, floor 1 credit, never above the ceiling) or releases
  the whole hold on a failure. A call whose usage could not be priced is charged the ceiling.
  The result carries `spent`. Wired into `/api/creative-guide` and `/scenes/run` in `app/api.py`.
  A personal model connection (the person's own plan) never takes a hold.
- **Stale holds**: a chat turn leaves no row to find and never stamps `submitted`, and nothing
  schedules `ledger.reap`, so `ledger.release_stale_holds("text", 15 min, account_id=)` runs at
  the start of the account's next priced turn.
- **Prices** in `spend.DEFAULT_PRICES` (Sonnet 5.5 $2/$10, Opus 5.5 $4/$20 per million, cache
  reads at a tenth); override with `SPEND_PRICES_JSON`.

## Mike's to move

The model pair, the ceilings (`text_charge.CEILING_CREDITS`) and the markup on text.

## Not done / next

- The studio's credit pill does not refresh after a priced turn (the response carries `spent`).
- Other stages that call a brain (voice-over, motion ad, cut agent) still use the default brain;
  only the Guide and the scene writer take the picker.
- Tests: `test_claude_client.py`, `test_text_charge.py`, `test_claude_brain_route.py`. The two
  `test_tenancy` table tests need pgvector (not in the cloud container).
- The generality phase (skills, memory, connectors, switchable LLM) has not started.
