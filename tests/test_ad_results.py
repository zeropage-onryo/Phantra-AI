"""
Ad results and ad variants (2026-10-29, docs/tasks/task-ad-results.md).

What is guarded:
- an ad report exported from Meta or TikTok as CSV is read, kept once per
  ad and window (importing it twice changes nothing), and a file that is
  not one is refused with a reason before anything is written
- the ad code in an ad's name finds its render, and only THIS account's:
  somebody else's code matches nothing
- an ad that ran is a kept output (outcomes "ad_run"), once
- versions of one ad from a plan read back as a test, and a winner is only
  called with enough results, in one currency
- the brain inside the Ad Studio is told the numbers; outside it, nothing
- the routes are scoped to the caller and guarded like every other write
- the code format is the same on both sides of the wire
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, ad_results, db, make_plan, outcomes, render_assets, studios

ROOT = Path(__file__).resolve().parent.parent

PURCHASE = "actions:offsite_conversion.fb_pixel_purchase"
META_CSV = "\n".join([
    "Reporting starts,Reporting ends,Campaign name,Ad set name,Ad name,Results,Result indicator,"
    "Impressions,Link clicks,Amount spent (USD),Purchases conversion value",
    f'2026-10-01,2026-10-14,Fall,Broad,Spill hook PH{{a}},12,{PURCHASE},"10,400",210,120.00,480.00',
    f'2026-10-01,2026-10-14,Fall,Broad,Price hook PH{{b}},4,{PURCHASE},"9,800",150,"96.00",130.00',
    f"2026-10-01,2026-10-14,Fall,Broad,Old creative no code,1,{PURCHASE},2000,20,30.00,",
    # the totals row Ads Manager adds: no ad name
    ",,,,,17,,22200,380,246.00,610.00",
    "",
])

TIKTOK_CSV = """Ad name,Ad ID,Ad group name,Date,Cost,Impressions,Clicks (destination),Conversions
UGC PH-{a},1790001,Group 1,2026-10-20,"40,00",5000,90,8
"""


@pytest.fixture
def world(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    accounts.seed("mike@example.com", dsn=pg)
    b = accounts.upsert_account("someone-else", "Else", "#000000", dsn=pg)
    render_assets.init(pg)
    outcomes.init(pg)
    ad_results.init(pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    with db.connect(pg) as conn:
        a = int(conn.execute("SELECT id FROM accounts WHERE slug = 'phantra'").fetchone()["id"])

    def render(acct, n, concept_id=None):
        row = render_assets.record(generation_id=7000 + acct * 100 + n, tool="fal", model="kling",
                                   media_kind="video", prompt=f"clip {n}",
                                   media_url=f"/renders/fal/{acct}-{n}.mp4", output_path=None,
                                   account_id=acct, dsn=pg, concept_id=concept_id)
        return int(row["id"])
    return {"dsn": pg, "a": a, "b": b, "render": render}


# --- the code -----------------------------------------------------------------

def test_codes_are_read_back_from_names_and_url_parameters():
    assert ad_results.code_for(4821) == "PH4821"
    assert ad_results.codes_in("Spill hook PH4821") == [4821]
    assert ad_results.codes_in("ph-12 / utm_content=PH13", "PH12") == [12, 13]
    # never inside a longer word or a longer number
    assert ad_results.codes_in("GRAPH12", "PH1234567890", "alpha", "") == []


def test_the_web_writes_the_code_the_server_reads():
    ts = (ROOT / "web/src/lib/ad-results.ts").read_text()
    m = re.search(r'AD_CODE_PREFIX = "([A-Z]+)"', ts)
    assert m and m.group(1) == ad_results.CODE_PREFIX


# --- reading an export --------------------------------------------------------

def test_a_meta_export_is_read_with_its_currency_and_skips_the_totals_row():
    parsed = ad_results.parse(META_CSV.format(a=1, b=2).encode())
    assert parsed["platform"] == "meta"
    assert parsed["currency"] == "USD"
    assert parsed["skipped"] == 1
    first = parsed["rows"][0]
    assert first["impressions"] == 10400 and first["clicks"] == 210
    assert first["spend"] == 120.0 and first["results"] == 12 and first["revenue"] == 480.0
    assert first["codes"] == [1]
    assert parsed["rows"][2]["revenue"] is None


def test_a_tiktok_export_and_a_decimal_comma_are_read():
    parsed = ad_results.parse(TIKTOK_CSV.format(a=5).encode())
    assert parsed["platform"] == "tiktok"
    row = parsed["rows"][0]
    assert row["spend"] == 40.0 and row["results"] == 8 and row["ad_key"] == "1790001"
    assert row["period_start"] == row["period_end"] == "2026-10-20"


@pytest.mark.parametrize("data, says", [
    (b"", "empty"),
    (b"PK\x03\x04rest", "CSV"),
    (b"Campaign name,Impressions\nFall,100\n", "Ad name"),
    (b"Ad name,Impressions\nx,100\n", "Amount spent"),
])
def test_a_file_that_is_not_an_ad_report_is_refused_with_a_reason(data, says):
    with pytest.raises(ad_results.ImportRefused) as e:
        ad_results.parse(data)
    assert says in str(e.value)


# --- importing ----------------------------------------------------------------

def test_an_import_matches_this_accounts_renders_only_and_is_idempotent(world):
    pg, a, b = world["dsn"], world["a"], world["b"]
    mine = world["render"](a, 1, concept_id=11)
    theirs = world["render"](b, 1)
    data = META_CSV.format(a=mine, b=theirs).encode()
    got = ad_results.import_csv(data, account_id=a, filename="fall.csv", dsn=pg)
    assert got["added"] == 3 and got["updated"] == 0 and got["matched"] == 1
    assert "Price hook PH%d" % theirs in got["unmatched"]
    again = ad_results.import_csv(data, account_id=a, dsn=pg)
    assert again["added"] == 0 and again["updated"] == 3
    with db.connect(pg) as conn:
        assert conn.execute("SELECT count(*) AS n FROM ad_results").fetchone()["n"] == 3
        kept = conn.execute("SELECT asset_id FROM output_events WHERE event = 'ad_run'").fetchall()
    # an ad that ran is a keep, written once, and never for somebody else's render
    assert [r["asset_id"] for r in kept] == [mine]
    # the other account sees nothing of it
    assert ad_results.summary(account_id=b, dsn=pg)["ads"] == []
    s = ad_results.summary(account_id=a, dsn=pg)
    spill = next(x for x in s["ads"] if x["asset_id"] == mine)
    assert spill["code"] == f"PH{mine}" and spill["concept_id"] == 11
    assert spill["cpa"] == 10.0 and spill["roas"] == 4.0 and spill["ctr"] == round(210 / 10400, 4)
    assert s["unmatched"] == 2


def test_deleting_an_import_takes_its_rows_back_out(world):
    pg, a = world["dsn"], world["a"]
    got = ad_results.import_csv(TIKTOK_CSV.format(a=1).encode(), account_id=a, dsn=pg)
    assert ad_results.delete_import(got["import_id"], account_id=world["b"], dsn=pg) == 0
    assert ad_results.delete_import(got["import_id"], account_id=a, dsn=pg) == 1
    assert ad_results.summary(account_id=a, dsn=pg)["ads"] == []


# --- variants -------------------------------------------------------------------

def test_versions_of_one_ad_read_back_as_a_test_with_a_winner(world):
    pg, a = world["dsn"], world["a"]
    spill = world["render"](a, 1, concept_id=21)
    price = world["render"](a, 2, concept_id=22)
    assert ad_results.record_variant(21, account_id=a, group_id="plan-1", label="Hook: the spill",
                                     test="which opening stops the scroll", dsn=pg)
    assert ad_results.record_variant(22, account_id=a, group_id="plan-1", label="Hook: price first",
                                     dsn=pg)
    assert not ad_results.record_variant(23, account_id=a, group_id="", label="x", dsn=pg)
    ad_results.import_csv(META_CSV.format(a=spill, b=price).encode(), account_id=a, dsn=pg)
    [t] = ad_results.summary(account_id=a, dsn=pg)["tests"]
    assert t["test"] == "which opening stops the scroll"
    assert t["winner"] == f"PH{spill}" and "Hook: the spill wins" in t["verdict"]
    assert [x["variant"] for x in t["ads"]] == ["Hook: the spill", "Hook: price first"]


def test_no_winner_is_called_too_early_or_across_currencies():
    def ad(code, cpa, results, currency="USD"):
        return {"group_id": "g", "test": None, "variant": code, "code": code, "cpa": cpa,
                "results": results, "spend": (cpa or 0) * results, "currency": currency}
    early = ad_results.tests([ad("A", 5.0, 2), ad("B", 9.0, 3)])
    assert early[0]["winner"] is None and "too early" in early[0]["verdict"]
    mixed = ad_results.tests([ad("A", 5.0, 20), ad("B", 9.0, 20, "EUR")])
    assert mixed[0]["winner"] is None and "currencies" in mixed[0]["verdict"]
    lone = ad_results.tests([ad("A", 5.0, 20)])
    assert lone[0]["winner"] is None


def test_a_plan_keeps_each_versions_label_and_its_test(monkeypatch):
    plan = make_plan.check({"test": "which hook", "steps": [
        {"do": "scene", "prompt": "the ad, spill hook", "variant": "Hook: the spill"},
        {"do": "scene", "prompt": "the ad, price hook", "variant": "Hook: price first"},
        {"do": "render", "scene": 1, "variant": "ignored on a render"},
    ]})
    assert plan["test"] == "which hook"
    assert [s.get("variant") for s in plan["steps"]] == ["Hook: the spill", "Hook: price first", None]
    # no versions, no test
    plain = make_plan.check({"test": "which hook", "steps": [
        {"do": "scene", "prompt": "one"}, {"do": "scene", "prompt": "two"}]})
    assert "test" not in plain


def test_two_versions_with_one_label_are_refused():
    from src import guide_tools
    with pytest.raises(guide_tools.Refused):
        make_plan.check({"steps": [
            {"do": "scene", "prompt": "a", "variant": "Hook A"},
            {"do": "scene", "prompt": "b", "variant": "hook a"}]})


# --- the brain ------------------------------------------------------------------

def test_the_ad_studio_turn_is_told_the_numbers_and_nothing_else_is(world):
    pg, a = world["dsn"], world["a"]
    assert studios.results_note({"id": "ads"}, a) == ""        # nothing imported yet
    spill = world["render"](a, 1)
    ad_results.import_csv(META_CSV.format(a=spill, b=999999).encode(), account_id=a, dsn=pg)
    note = studios.results_note({"id": "ads", "format": "ugc"}, a)
    assert f"PH{spill}" in note and "10.00 USD each" in note and "return 4.00x" in note
    assert "$" not in note
    assert studios.results_note(None, a) == ""
    assert studios.results_note({"id": "ads"}, None) == ""


# --- the routes -----------------------------------------------------------------

@pytest.fixture
def signed_in(world, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "m@example.com"})
    app.dependency_overrides[auth.current_account_id] = lambda: world["a"]
    yield world
    app.dependency_overrides.pop(auth.current_account_id, None)


GUARDED = {"X-Phantra-Model-Connection": "1"}


def test_the_import_route_is_guarded_scoped_and_says_why_it_refuses(signed_in):
    client = TestClient(app)
    mine = signed_in["render"](signed_in["a"], 1)
    files = {"file": ("ads.csv", TIKTOK_CSV.format(a=mine).encode(), "text/csv")}
    assert client.post("/api/ad-results/import", files=files).status_code == 403
    r = client.post("/api/ad-results/import", files=files, headers=GUARDED)
    assert r.status_code == 200, r.text
    assert r.json()["matched"] == 1 and r.json()["platform"] == "tiktok"
    bad = client.post("/api/ad-results/import", headers=GUARDED,
                      files={"file": ("x.xlsx", b"PK\x03\x04", "application/octet-stream")})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "bad_export"
    none = client.post("/api/ad-results/import", headers=GUARDED, data={"x": "1"})
    assert none.status_code == 400 and none.json()["error"]["code"] == "no_file"
    summary = client.get("/api/ad-results").json()
    assert summary["ads"][0]["code"] == f"PH{mine}"
    gone = client.delete(f"/api/ad-results/imports/{r.json()['import_id']}", headers=GUARDED)
    assert gone.json() == {"deleted": 1}


def test_a_plans_version_is_filed_on_the_scene_it_writes(signed_in, monkeypatch):
    import time

    from src import charge, scene_chain
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key=None: object())
    monkeypatch.setattr(scene_chain, "run", lambda idea, **kw: {"scenes": [{"concept_id": 77}],
                                                               "notes": []})
    client = TestClient(app)

    def wait(job_id):
        deadline = time.time() + 10
        while time.time() < deadline:
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in ("done", "failed"):
                return job
            time.sleep(0.05)
        raise AssertionError("the job never finished")

    r = client.post("/api/scenes/run", data={
        "idea": "the ad, spill hook", "variant": "Hook: the spill", "variant_group": "plan-9",
        "variant_test": "which hook"})
    assert wait(r.json()["job_id"])["status"] == "done"
    # a scene written with no variant is no version
    r = client.post("/api/scenes/run", data={"idea": "another"})
    assert wait(r.json()["job_id"])["status"] == "done"
    with db.connect(signed_in["dsn"]) as conn:
        rows = conn.execute("SELECT account_id, concept_id, group_id, label, test "
                            "FROM ad_variants").fetchall()
    assert [dict(r) for r in rows] == [{"account_id": signed_in["a"], "concept_id": 77,
                                        "group_id": "plan-9", "label": "Hook: the spill",
                                        "test": "which hook"}]
