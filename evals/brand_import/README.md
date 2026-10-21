# Brand import eval (by hand)

Scores `src/brand_import.py`, the "New kit from a website" import, against websites whose brand
colours are known. **It opens real websites, so it never runs in CI or in `tests/`.** Run it on a
machine with Playwright's Chromium installed (`venv/bin/python -m playwright install --only-shell
chromium`):

```bash
venv/bin/python -m evals.brand_import.score
venv/bin/python -m evals.brand_import.score --golden path/to/golden_set.json
```

Each site's primary is **exact** when it is within ΔE 2 of the official one. A logo counts when
one was captured, and fonts count when every listed family was found. It also reports how often
a "high" confidence primary was right, because that is what the kit page's chips promise.

`golden_set.json` holds only sites whose primary comes from the brand itself (guidelines or the
client). The 18-site set scored in the 2026-10-21 chat (`brandkit.zip`, `golden/golden_set.json`,
reported there as 12/18 primaries exact, 19/20 logos, 7/9 fonts) was never in this repo; drop it
in here when it is in hand and record the run below.

## Runs

| Date | Golden set | Primary exact | Logo | Fonts | "high" right |
|---|---|---|---|---|---|
| 2026-10-21 | gygler.com only (1 site) | 1/1 (#FF880B) | 1/1 | 1/1 (Urbanist) | 1/1 |

The extractor here was written fresh on 2026-10-21 from the task file's description. The chat's
extractor (`brandkit.zip`) was not available, so the chat's scores do not carry over to it.
