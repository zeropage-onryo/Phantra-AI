"""A studio server on an old checkout refuses to price (QA 2026-11-02, K1).

Claude Desktop's stdio server ran code 264 commits old against the live
database and quoted LTX 2.3 6 s 1080p at 87 credits beside the site's 116,
with the same PRICING_VERSION. The deployed API now records the public
catalog's fingerprint (`pricing.record_live`) and `approval_gate` -- the
one door every spending tool on the studio surface goes through -- refuses
both the quote and the approve when this process's table is not that one.
"""
from __future__ import annotations

import json

from src import mcp_server, pricing, settings

ARGS = {"prompt": "a can on a table", "model": "flux2-pro"}


def _gate(dsn):
    return mcp_server.approval_gate(0.04, "", tool="generate_image", args=ARGS,
                                    what="This image", account_id=None, dsn=dsn)


def _record(dsn, fingerprint):
    settings.init(dsn)
    from src import db
    with db.connect(dsn) as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES (%s, %s)",
                     (pricing.LIVE_KEY, json.dumps({"fingerprint": fingerprint,
                                                    "at": "2026-11-02T17:00:00+00:00"})))


def test_the_fingerprint_moves_with_a_price(monkeypatch):
    before = pricing.table_fingerprint()
    assert before == pricing.table_fingerprint()
    monkeypatch.setattr(pricing, "CREDIT_FLOOR", pricing.CREDIT_FLOOR + 1)
    assert pricing.table_fingerprint() != before


def test_record_live_round_trips(pg):
    settings.init(pg)
    record = pricing.record_live(pg)
    assert record["fingerprint"] == pricing.table_fingerprint()
    assert record["version"] == pricing.PRICING_VERSION
    assert pricing.live_drift(pg) is None
    assert pricing.record_live(pg)["fingerprint"] == record["fingerprint"]   # an upsert


def test_an_old_table_refuses_the_quote(pg):
    _record(pg, "0123456789abcdef")
    drift = pricing.live_drift(pg)
    assert drift and "Nothing was spent" in drift and "restart Claude Desktop" in drift
    stop, approved, price = _gate(pg)
    assert stop["refused"] == "stale_prices"
    assert approved is None
    assert price["credits"] is None          # no stale number reaches the card


def test_nothing_recorded_or_check_off_passes(pg, monkeypatch):
    settings.init(pg)
    assert pricing.live_drift(pg) is None
    _record(pg, "0123456789abcdef")
    monkeypatch.setenv(pricing.PRICE_CHECK_ENV, "0")
    assert pricing.live_drift(pg) is None


def test_the_api_records_only_on_fly(monkeypatch):
    import inspect

    import app.main as app_main
    src = inspect.getsource(app_main.lifespan)
    assert "FLY_APP_NAME" in src and "pricing.record_live()" in src
