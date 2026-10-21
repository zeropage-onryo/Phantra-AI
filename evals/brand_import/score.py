"""Score src/brand_import.py against websites with known brand colours.

BY HAND ONLY: it opens real websites, so it never runs in CI or in the test
suite. From the repo root:

    venv/bin/python -m evals.brand_import.score [--golden evals/brand_import/golden_set.json]

For each site: the primary is EXACT when ΔE <= 2 from the official one, the
logo counts when one was captured, and the fonts count when every listed
family was found. It also reports how often a "high" confidence primary was
right, which is what the kit page's chips promise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src import brand_import

HERE = Path(__file__).resolve().parent


def score(sites: list[dict], out=sys.stdout) -> dict:
    exact = logos = fonts_ok = high = high_right = 0
    for site in sites:
        try:
            kit = brand_import.extract(url=site["url"])
        except Exception as e:                       # one site failing is a row, not the run
            print(f"{site['url']}: FAILED ({type(e).__name__}: {e})", file=out)
            continue
        palette = {s["role"]: s["hex"] for s in kit["spec"]["palette"]}
        got = palette.get("primary", "")
        right = bool(got) and brand_import.delta_e(
            brand_import.rgb_of(got), brand_import.rgb_of(site["primary"])) <= 2
        sure = kit["spec"].get("import", {}).get("roles", {}).get("primary", {}).get("confidence")
        exact += right
        if sure == "high":
            high += 1
            high_right += right
        has_logo = any(f["role"].startswith("logo") for f in kit["files"])
        logos += has_logo == bool(site.get("logo", True))
        wanted = {f.lower() for f in site.get("fonts") or []}
        found = {f.lower() for f in kit["fonts"].values()}
        fonts_ok += wanted <= found
        print(f"{site['url']}: primary {got or '-'} vs {site['primary']} "
              f"{'EXACT' if right else 'miss'} ({sure}); logo {'yes' if has_logo else 'no'}; "
              f"fonts {sorted(found)}", file=out)
    n = len(sites)
    result = {"sites": n, "primary_exact": exact, "logo": logos, "fonts": fonts_ok,
              "high_confidence": high, "high_confidence_right": high_right}
    print(f"\nprimary exact {exact}/{n} · logo {logos}/{n} · fonts {fonts_ok}/{n} · "
          f"'high' right {high_right}/{high}", file=out)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--golden", default=str(HERE / "golden_set.json"))
    args = ap.parse_args(argv)
    sites = json.loads(Path(args.golden).read_text())["sites"]
    score(sites)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
