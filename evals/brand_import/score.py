"""Score src/brand_import.py against websites with known brand colours.

BY HAND ONLY: it opens real websites, so it never runs in CI or in the test
suite. From the repo root:

    venv/bin/python -m evals.brand_import.score [--golden evals/brand_import/golden_set.json] [--only NAME ...]

`golden_set.json` is the chat's answer key (2026-10-21, brandkit.zip): each
brand's website, its official primary (null where none is published), its
fonts and where they came from. A primary is EXACT at CIEDE2000 <= 2 and a
PASS at <= 10, the chat's own thresholds. A logo counts when one was
captured; fonts when a listed family was found. It also reports how often a
"high" confidence primary was exact, which is what the kit page's chips
promise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from src import brand_import

HERE = Path(__file__).resolve().parent


ciede2000 = brand_import.ciede2000


def same_font(a: str, b: str) -> bool:
    """The chat's loose match: 'Circular Std Book' is 'Circular', and
    'DB Sharp Grotesk (proprietary, ...)' is 'Sharp Grotesk'."""
    def strip(n):
        return brand_import.font_norm(re.sub(r"\(.*?\)", "", n or ""))
    x, y = strip(a), strip(b)
    return bool(x and y) and (x == y or f" {y} " in f" {x} " or f" {x} " in f" {y} ")


def _sites(raw) -> list[dict]:
    if isinstance(raw, dict):
        raw = raw.get("sites") or []
    return [{"name": s.get("name") or s.get("url"), "url": s.get("website") or s.get("url"),
             "primary": s.get("primary"), "fonts": s.get("fonts") or []} for s in raw]


def score(sites: list[dict], out=sys.stdout) -> dict:
    scored = exact = passed = logos = fonts_ok = fonts_n = high = high_right = 0
    rows = []
    for site in sites:
        try:
            kit = brand_import.extract(url=site["url"])
        except Exception as e:                       # one site failing is a row, not the run
            print(f"{site['name']:<15} FAILED ({type(e).__name__}: {str(e)[:120]})", file=out)
            rows.append({"name": site["name"], "failed": str(e)[:200]})
            continue
        palette = {s["role"]: s["hex"] for s in kit["spec"]["palette"]}
        got = palette.get("primary", "")
        sure = kit["spec"].get("import", {}).get("roles", {}).get("primary", {}).get("confidence")
        de = None
        if site["primary"] and got:
            scored += 1
            de = ciede2000(brand_import.rgb_of(got), brand_import.rgb_of(site["primary"]))
            exact += de <= 2
            passed += de <= 10
            if sure == "high":
                high += 1
                high_right += de <= 2
        has_logo = any(f["role"].startswith("logo") for f in kit["files"])
        logos += has_logo
        wanted = site["fonts"]
        found = sorted(set(kit["fonts"].values()))
        if wanted:
            fonts_n += 1
            fonts_ok += any(same_font(w, f) for w in wanted for f in found)
        mark = "" if de is None else ("EXACT" if de <= 2 else "pass" if de <= 10 else "miss")
        print(f"{site['name']:<15} {got or '-':<8} vs {site['primary'] or '(none)':<8} "
              f"{'' if de is None else f'ΔE {de:5.1f}':<9} {mark:<5} {sure or '':<6} "
              f"logo {'yes' if has_logo else 'no ':<3} fonts {sorted(found)}", file=out)
        rows.append({"name": site["name"], "primary": got, "official": site["primary"],
                     "delta_e": de, "confidence": sure, "logo": has_logo,
                     "fonts": sorted(found)})
    result = {"primaries_scored": scored, "primary_exact": exact, "primary_pass": passed,
              "logo": logos, "sites": len(sites), "fonts": fonts_ok, "fonts_scored": fonts_n,
              "high_confidence": high, "high_confidence_right": high_right, "rows": rows}
    print(f"\nprimary exact {exact}/{scored} (pass {passed}/{scored}) · logo {logos}/{len(sites)}"
          f" · fonts {fonts_ok}/{fonts_n} · 'high' exact {high_right}/{high}", file=out)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--golden", default=str(HERE / "golden_set.json"))
    ap.add_argument("--only", nargs="*", help="score only these brand names")
    ap.add_argument("--json", help="write the rows here too")
    args = ap.parse_args(argv)
    sites = _sites(json.loads(Path(args.golden).read_text()))
    if args.only:
        wanted = {n.lower() for n in args.only}
        sites = [s for s in sites if (s["name"] or "").lower() in wanted]
    result = score(sites)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
