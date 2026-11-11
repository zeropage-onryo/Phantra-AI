"""Write web/src/content/effects-catalog.json: the effects table as the
public /effects pages read it (app.api.public_effects_catalog).

    venv/bin/python -m ops.export_effects_catalog            # write it
    venv/bin/python -m ops.export_effects_catalog --check    # report only

Run it after adding or changing an effect, and commit the file;
tests/test_effects_catalog.py fails CI while it is stale. Touches no
database and no network: a projection of src/effects.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render() -> str:
    from app.api import public_effects_catalog
    return json.dumps(public_effects_catalog(), indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    from app.api import EFFECTS_CATALOG_PATH
    path = ROOT / EFFECTS_CATALOG_PATH
    text = render()
    current = path.read_text() if path.exists() else ""
    if "--check" in argv:
        print("effects-catalog.json is current" if current == text
              else "effects-catalog.json is STALE: run python -m ops.export_effects_catalog")
        return 0 if current == text else 1
    path.write_text(text)
    print(f"wrote {EFFECTS_CATALOG_PATH} ({len(json.loads(text)['items'])} effects)")
    return 0


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main(sys.argv[1:]))
