"""The brand-era data clear (ops/brand_removal_clear.py, 2026-10-13).

Nothing here calls a model.
"""
import json

import pytest

from ops import brand_removal_clear as clear
from src import accounts, autonomy, db, preprod, render_assets, scout, workflows


@pytest.fixture
def store(pg, monkeypatch, tmp_path):
    preprod.init(pg)
    autonomy.init(pg)
    workflows.init(pg)
    scout.init(pg)
    render_assets.init(pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 0, "error": None})
    mine = accounts.seed("mike@example.com", dsn=pg)["accounts"][0]
    theirs = accounts.upsert_account("someone-else", "Someone Else", dsn=pg)
    return {"dsn": pg, "mine": mine, "theirs": theirs, "tmp": tmp_path}


def scene(dsn, account, title, **shot):
    return preprod.save_concept(
        {"title": title, "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX", "desc": "d",
                    "prompt": "p", "refs": ["/refs/a.jpg"], **shot}]},
        brand="zeropage", prompt_template="T", dsn=dsn, account_id=account)


def _setup(s):
    dsn, mine = s["dsn"], s["mine"]
    ids = {
        "plain": scene(dsn, mine, "plain"),
        "canvas": scene(dsn, mine, "plain with a canvas and a hold"),
        "picked": scene(dsn, mine, "picked, never rendered"),
        "rendered": scene(dsn, mine, "rendered", media_url="https://r2/clip.mp4"),
        "part": scene(dsn, mine, "one part rendered",
                      timeline={"parts": [{"n": 1, "media_url": "https://r2/p1.mp4"}]}),
        "asset": scene(dsn, mine, "has a Library item"),
        "theirs": scene(dsn, s["theirs"], "another account's"),
    }
    preprod.set_picked(ids["picked"], True, dsn=dsn, account_id=mine)
    render_assets.record(generation_id=1, tool="fal", model="ltx", media_kind="image", prompt="p",
                         media_url="https://r2/still.png", concept_id=ids["asset"], dsn=dsn,
                         account_id=mine)
    workflows.save_shot_graph(ids["canvas"], 1, {"nodes": []}, dsn=dsn, account_id=mine)
    workflows.save_shot_graph(ids["rendered"], 1, {"nodes": []}, dsn=dsn, account_id=mine)
    with db.connect(dsn) as conn:
        for cid in (ids["canvas"], None):
            conn.execute("INSERT INTO hold_queue (created_at, channel, concept_id, account_id) "
                         "VALUES ('2026-09-01', 'zeropage', %s, %s)", (cid, mine))
        conn.execute("INSERT INTO hold_queue (created_at, channel, account_id) "
                     "VALUES ('2026-09-01', 'zeropage', %s)", (s["theirs"],))
        conn.execute("INSERT INTO scout_findings (created_at, brand, spark, spark_key) "
                     "VALUES ('2026-09-01', 'zeropage', 'a spark', 'k1')")
        conn.execute("INSERT INTO scout_bin (created_at, pass_id, brand, url) "
                     "VALUES ('2026-09-01', 'p1', 'zeropage', '/refs/a.jpg')")
    return ids


def _count(dsn, table, where="TRUE"):
    with db.connect(dsn) as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table} WHERE {where}").fetchone()["n"]


def test_the_report_keeps_rendered_and_linked_scenes_and_changes_nothing(store):
    ids = _setup(store)
    plan = clear.scan(store["dsn"], account_id=store["mine"])
    assert sorted(plan["delete"]) == sorted([ids["plain"], ids["canvas"], ids["picked"]])
    assert plan["keep"] == {ids["rendered"]: ["rendered"], ids["part"]: ["rendered"],
                            ids["asset"]: ["points from a Library item"]}
    assert plan["counts"] == {"shoot_concepts": 3, "workflows": 1, "hold_queue": 2,
                              "prompt_scores": 0, "scout_findings": 1, "scout_bin": 1}
    assert plan["other_accounts"] == {store["theirs"]: 1}
    assert plan["unknown_columns"] == []
    assert _count(store["dsn"], "shoot_concepts") == 7


def test_keep_picked_and_keep_by_id(store):
    ids = _setup(store)
    plan = clear.scan(store["dsn"], account_id=store["mine"], keep_ids=(ids["plain"],),
                      keep_picked=True)
    assert plan["delete"] == [ids["canvas"]]
    assert plan["keep"][ids["picked"]] == ["picked"]
    assert plan["keep"][ids["plain"]] == ["kept by id"]


def test_the_backup_is_read_back_and_the_clear_matches_the_report(store):
    ids = _setup(store)
    dsn, mine = store["dsn"], store["mine"]
    plan = clear.scan(dsn, account_id=mine)
    out = store["tmp"] / "backup"
    written = clear.backup(dsn, account_id=mine, plan=plan, out=out)
    assert written["shoot_concepts"] == 3 and written["shoot_concepts_all_of_account"] == 6
    saved = json.loads((out / "shoot_concepts.json").read_text())
    assert sorted(r["id"] for r in saved) == sorted(plan["delete"])
    assert json.loads((out / "scout_bin.json").read_text())[0]["url"] == "/refs/a.jpg"

    assert clear.clear(dsn, account_id=mine, plan=plan) == plan["counts"]
    left = {c["id"] for c in preprod.list_concepts(limit=100, dsn=dsn, account_id=mine)}
    assert left == {ids["rendered"], ids["part"], ids["asset"]}
    # another account's scene and hold, the kept scene's canvas and the Library row stay
    assert _count(dsn, "shoot_concepts", f"account_id = {store['theirs']}") == 1
    assert _count(dsn, "hold_queue") == 1
    assert _count(dsn, "workflows") == 1
    assert len(render_assets.list_all(dsn=dsn, account_id=mine)) == 1
    assert _count(dsn, "scout_findings") == 0 and _count(dsn, "scout_bin") == 0
    # a second run finds nothing to do
    again = clear.scan(dsn, account_id=mine)
    assert again["delete"] == [] and set(again["counts"].values()) == {0}
    assert clear.clear(dsn, account_id=mine, plan=again) == again["counts"]


def test_a_count_that_moved_since_the_report_rolls_everything_back(store):
    _setup(store)
    dsn, mine = store["dsn"], store["mine"]
    plan = clear.scan(dsn, account_id=mine)
    with db.connect(dsn) as conn:
        conn.execute("INSERT INTO scout_bin (created_at, pass_id, brand, url) "
                     "VALUES ('2026-09-02', 'p2', 'zeropage', '/refs/b.jpg')")
    with pytest.raises(RuntimeError, match="rolled back"):
        clear.clear(dsn, account_id=mine, plan=plan)
    assert _count(dsn, "shoot_concepts") == 7 and _count(dsn, "hold_queue") == 3
    assert _count(dsn, "scout_findings") == 1


def test_the_command_refuses_a_write_with_no_backup_and_an_unknown_account(store, capsys):
    _setup(store)
    assert clear.main(["--account", "zeropage", "--dsn", store["dsn"], "--write"]) == 2
    assert clear.main(["--account", "nobody", "--dsn", store["dsn"]]) == 2
    assert clear.main(["--account", "zeropage", "--dsn", store["dsn"]]) == 0
    assert "report only" in capsys.readouterr().out
    assert _count(store["dsn"], "shoot_concepts") == 7
