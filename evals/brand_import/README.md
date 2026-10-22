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

`golden_set.json` is the chat's answer key (`brandkit.zip`, `golden/golden_set.json`): 21 brands,
each with its official primary (none for Linear, ClickUp and Gygler), its fonts and the page each
value came from. CIEDE2000 is computed in `src/brand_import.py` (pure Python, checked against
Sharma's published pairs), so no scikit-image is needed.

## Runs

| Date | Extractor | Primary exact | Within ΔE 10 | Logo | Fonts | "high" exact |
|---|---|---|---|---|---|---|
| 2026-10-21 | the chat's own (`brandkit.zip`, its scorecard) | 12/18 | 12/18 | 19/20 | 7/9 | 10/12 |
| 2026-10-21 | first fresh one, before the port | 7/17 (Raycast timed out) | 7/17 | 16/21 | 4/8 | 4/6 |
| 2026-10-21 | ported scoring, async guard, 120 s limit (this branch) | 10/16 (Raycast timed out) | 11/16 | 19/21 | 7/9 | 9/11 |

- **Misses:** the six the chat's extractor also misses (GitHub, Stack Overflow, JetBrains,
  Framer, Android, Bun; the chat's notes say github.com, for one, shows its product colours, not
  the brand's).
- **Run-to-run variation:** Raycast was exact when scored alone and hit the 120 s limit in the
  full run. Vimeo came back ΔE 7.4 (exact in an earlier run): its hero video differs between
  loads.
