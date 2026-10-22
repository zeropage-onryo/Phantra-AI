"""
Credits everywhere (2026-10-08, part 2 of
docs/tasks/task-spend-holes-and-credits.md): a person in the studio sees
CREDITS, never the provider's dollars. Dollars stay on the operator's
pages (/costs, the Dev Studio) and on the marketing site's plan prices,
none of which are scanned here.

- the default renderer's state carries its clip's price in credits, by the
  same conversion pricing.display makes, so no client has to fall back to
  the dollar estimate
- no studio page, no Director component and not the legacy Queue formats a
  dollar figure: a guard over the source, because every dollar label that
  shipped was added by a page that had the number in hand and printed it.
  A Python test rather than a node one so CI runs it (CI runs no web tests).
"""
import re
from pathlib import Path

from app import api
from src import pricing, providers

ROOT = Path(__file__).resolve().parent.parent

# what is scanned: every studio page and component, the Director canvas, the
# shared price text, and the legacy /ui Queue
SCANNED = [
    *sorted((ROOT / "web/src/app/studio").rglob("*.ts*")),
    *sorted((ROOT / "web/src/components/studio").rglob("*.ts*")),
    *sorted((ROOT / "web/src/components/flows").rglob("*.ts*")),
    ROOT / "web/src/lib/render-choice.ts",
    ROOT / "app/static/phantra/queue.js",
]

# a dollar figure being built: "~$", "$${" (a literal $ before an
# interpolation), '$' + ..., or toFixed(2) on a line about usd / estimate
DOLLARS = [
    (re.compile(r"~\$"), "a '~$' label"),
    (re.compile(r"\$\$\{"), "a '$' before an interpolation"),
    (re.compile(r"""['"]\$['"]\s*\+"""), "'$' + a number"),
    (re.compile(r"(?i)(usd|estimate).*toFixed\(2\)|toFixed\(2\).*(usd|estimate)"),
     "toFixed(2) on a dollar estimate"),
]


def _code(line: str) -> bool:
    stripped = line.strip()
    return not stripped.startswith(("//", "*", "/*"))


def test_no_studio_surface_formats_dollars():
    assert all(p.exists() for p in SCANNED[-2:])
    found = []
    for path in SCANNED:
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if not _code(line):
                continue
            for pattern, what in DOLLARS:
                if pattern.search(line):
                    found.append(f"{path.relative_to(ROOT)}:{n}: {what}: {line.strip()[:120]}")
    assert not found, "the studio shows credits, never dollars:\n" + "\n".join(found)


def test_the_guard_would_have_caught_the_labels_it_replaced():
    """The lines this pass removed, as they were: each must trip the guard,
    or the guard is guarding nothing."""
    removed = [
        "? `est. $${Number(rw.estimate_usd).toFixed(2)}`",
        "tally.usd ? `~$${tally.usd.toFixed(2)}` : \"\",",
        ": usd === null || usd === undefined ? 'unpriced' : '~$' + usd.toFixed(2)}`;",
        "<b>{rw?.estimate_usd != null ? `$${Number(rw.estimate_usd).toFixed(2)}` : \"—\"}</b>",
    ]
    for line in removed:
        assert any(p.search(line) for p, _ in DOLLARS), line


# --- the settings area (2026-10-11, docs/tasks/task-settings-page.md) -------
# Settings shows the balance, the lots and the history, all in credits. ONE
# dollar figure is allowed in the whole studio: a plan's PRICE, on the Plan &
# credits section, printed the way the public /pricing page prints it (the
# catalog's `usd` formatter over `monthly_usd` / `yearly_usd`). The four
# patterns above already cover these files (they are under the scanned
# folders); this holds the exception to exactly that.

SETTINGS = [
    *sorted((ROOT / "web/src/components/studio/settings").rglob("*.ts*")),
    *sorted((ROOT / "web/src/app/studio/settings").rglob("*.ts*")),
]
USD_CALL = re.compile(r"(?<![\w.])usd\(")
PLAN_PRICE = re.compile(r"usd\((?:monthlyAt\(|[\w.]*\b(?:monthly_usd|yearly_usd)\b)")
USD_FIELD = re.compile(r"\b\w*_usd\b")
PLAN_PRICE_FIELDS = {"monthly_usd", "yearly_usd", "yearly_monthly_usd"}
DOLLAR_LITERAL = re.compile(r"\$\d")


def _settings_dollars(path: Path, lines) -> tuple[list[str], list[str]]:
    """(the plan-price calls found, everything else that names a dollar)."""
    prices, strays = [], []
    for n, line in enumerate(lines, 1):
        if not _code(line):
            continue
        where = f"{path.name}:{n}: {line.strip()[:120]}"
        for call in USD_CALL.finditer(line):
            if path.name == "plan.tsx" and PLAN_PRICE.match(line, call.start()):
                prices.append(where)
            else:
                strays.append(f"a dollar formatted outside a plan price: {where}")
        for field in USD_FIELD.findall(line):
            if field not in PLAN_PRICE_FIELDS:
                strays.append(f"a dollar field ({field}): {where}")
        if DOLLAR_LITERAL.search(line):
            strays.append(f"a dollar amount typed by hand: {where}")
    return prices, strays


def test_settings_prints_one_dollar_figure_a_plan_price():
    assert SETTINGS, "the settings area moved: point this guard at it"
    prices, strays = [], []
    for path in SETTINGS:
        found, bad = _settings_dollars(path, path.read_text().splitlines())
        prices += found
        strays += bad
    assert not strays, "settings shows credits; only a plan's price is in dollars:\n" + "\n".join(strays)
    # the guard is looking at the file that prints it
    assert prices, "no plan price found in settings/plan.tsx -- did the formatter change?"


def test_the_settings_guard_catches_what_it_is_for():
    plan, usage = Path("plan.tsx"), Path("usage.tsx")
    ok = ["<b>{usd(monthlyAt(p, at))}</b> a month", "`${usd(mine.yearly_usd)} a year`"]
    assert _settings_dollars(plan, ok) == ([f"plan.tsx:{n}: {line}" for n, line in enumerate(ok, 1)], [])
    for path, line in [
        (usage, "<td>{usd(entry.cost)}</td>"),                 # a dollar outside the plan section
        (plan, "<span>{usd(TOPUP.usd)}</span>"),               # a price that is not a plan's
        (plan, "<span>{row.cost_usd}</span>"),                 # the provider's cost
        (plan, "<p>Top up for $10</p>"),                       # typed by hand
    ]:
        assert _settings_dollars(path, [line])[1], line


def test_the_renderer_state_carries_its_clip_in_credits(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "k")
    state = api._render_state(None)
    pick = providers.check_render_choice()
    assert state["estimate_usd"] == pick["estimate_usd"]
    assert state["credits"] == pricing.credits_for(pricing.usd_micros(pick["estimate_usd"]))
    assert state["credits"] >= pricing.CREDIT_FLOOR
