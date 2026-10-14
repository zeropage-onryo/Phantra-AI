"""The board-eval snapshot (ops/snapshot_board_evals.py, 2026-10-11).

Step 0 of docs/tasks/task-higgsfield-shape.md: the board's labels are
copied out before anything that reads them is removed. Each test names
the line it guards. Nothing here calls a model.
"""
import json

import pytest

from ops import snapshot_board_evals as snap
from src import accounts, autonomy, db, preprod, winners


@pytest.fixture
def store(pg, tmp_path):
    preprod.init(pg)
    autonomy.init(pg)
    winners.init(pg)
    seeded = accounts.seed("mike@example.com", dsn=pg)
    return {"dsn": pg, "account": seeded["accounts"][0], "tmp": tmp_path}


def scene(dsn, account, title):
    return preprod.save_concept(
        {"title": title, "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX", "desc": "d",
                    "prompt": "THE SECRET PROMPT", "refs": ["/refs/a.jpg"]}]},
             prompt_template="T", dsn=dsn, account_id=account)


def _setup(s):
    dsn, acct = s["dsn"], s["account"]
    ids = {name: scene(dsn, acct, name) for name in ("picked", "passed", "plain", "made")}
    preprod.set_picked(ids["picked"], True, dsn=dsn, account_id=acct)
    preprod.set_archived(ids["passed"], True, dsn=dsn, account_id=acct, reason="boring")
    preprod.mark_shot(ids["made"], True, dsn=dsn, account_id=acct)
    # a row nobody owns: the unowned pool gets its own file
    ids["unowned"] = scene(dsn, None, "unowned")
    with db.connect(dsn) as conn:
        for status in ("approved", "rejected", "held"):
            conn.execute(
                "INSERT INTO hold_queue (created_at, channel, status, concept_id, account_id) "
                "VALUES ('2026-10-01', 'zeropage', %s, %s, %s)", (status, ids["plain"], acct))
    autonomy.log_prompt_scores("run-1", [
        {"prompt": "p1", "score": 8, "pass": True, "reason": "fine", "dims": {"subject": 2}},
        {"prompt": "p2", "score": 4, "pass": False, "reason": "no camera"}], dsn=dsn)
    winners.add("ltx", "a keeper", note="picked on the board", video_ref="concept-1-shot-1",
                verdict="worked", dsn=dsn)
    winners.add("ltx", "a miss", note="passed on the board", video_ref="concept-2-shot-1",
                verdict="didnt_work", dsn=dsn)
    return ids


# guards: collect -- the label columns per account, graded holds only, the shared tables
def test_the_snapshot_holds_every_label_and_changes_nothing(store):
    ids = _setup(store)
    dsn, acct = store["dsn"], store["account"]
    snapshot = snap.collect(dsn)

    mine = next(a for a in snapshot["accounts"] if a["account_id"] == acct)
    by_id = {r["id"]: r for r in mine["concepts"]}
    assert set(by_id) == {ids[k] for k in ("picked", "passed", "plain", "made")}
    assert by_id[ids["picked"]]["picked_at"]
    assert by_id[ids["passed"]]["archived_at"] and by_id[ids["passed"]]["archive_reason"] == "boring"
    assert by_id[ids["made"]]["shot_done"] == 1
    # the labels, never the prompt: the row stays in the database
    assert "THE SECRET PROMPT" not in json.dumps(mine, default=str)
    assert sorted(h["status"] for h in mine["holds"]) == ["approved", "rejected"]
    assert set(mine["rates"]) == {"pick_rate", "shoot_rate", "reason_counts",
                                  "evaluator_agreement", "ungrounded_count"}
    assert isinstance(mine["rates"]["pick_rate"], dict)

    unowned = next(a for a in snapshot["accounts"] if a["account_id"] is None)
    assert [r["id"] for r in unowned["concepts"]] == [ids["unowned"]]

    shared = snapshot["shared"]
    assert [r["prompt"] for r in shared["prompt_scores"]] == ["p1", "p2"]
    assert {r["verdict"] for r in shared["winning_prompts"]} == {"worked", "didnt_work"}
    assert set(shared["rates"]) == {"prompt_gate_agreement", "first_try_pass_rate"}

    report = snap.counts(snapshot)
    row = next(a for a in report["accounts"] if a["account_id"] == acct)
    assert (row["concepts"], row["picked"], row["archived"], row["with_reason"],
            row["marked_shot"], row["graded_holds"]) == (4, 1, 1, 1, 1, 2)
    assert report["prompt_scores"] == 2
    assert report["winning_prompts"]["worked_pending"] == 1
    assert report["winning_prompts"]["avoid_pending"] == 1

    # read-only: every row is where it was
    assert len(preprod.list_concepts(limit=100, dsn=dsn, account_id=acct)) == 4
    with db.connect(dsn) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM hold_queue").fetchone()["n"] == 3
        assert conn.execute("SELECT COUNT(*) AS n FROM prompt_scores").fetchone()["n"] == 2


# guards: write -- one file per account, shared.json, the manifest, never overwritten
def test_the_write_saves_one_file_per_account_and_refuses_to_overwrite(store):
    _setup(store)
    out = store["tmp"] / "board-evals"
    files = snap.write(snap.collect(store["dsn"]), out, where="test:5432/db")
    names = sorted(p.name for p in files)
    assert names == sorted([f"account-{store['account']}-zeropage.json",
                            "account-unowned.json", "shared.json", "manifest.json"])
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["database"] == "test:5432/db"
    assert manifest["counts"]["prompt_scores"] == 2
    assert len(json.loads((out / "shared.json").read_text())["winning_prompts"]) == 2
    with pytest.raises(FileExistsError):
        snap.write(snap.collect(store["dsn"]), out)


# guards: main -- report by default, files only with --write, never a guessed database
def test_the_cli_reports_by_default_and_never_guesses_the_database(store, monkeypatch, capsys):
    _setup(store)
    out = store["tmp"] / "cli"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert snap.main(["--out", str(out), "--write"]) == 2
    assert "never guesses" in capsys.readouterr().err
    assert not out.exists()

    assert snap.main(["--dsn", store["dsn"], "--out", str(out)]) == 0
    assert "report only" in capsys.readouterr().out
    assert not out.exists()

    assert snap.main(["--dsn", store["dsn"], "--out", str(out), "--write"]) == 0
    assert (out / "manifest.json").exists()
    # a second write the same day is refused, the first one kept
    assert snap.main(["--dsn", store["dsn"], "--out", str(out), "--write"]) == 3


# guards: _rate -- a rate that cannot answer is written down, not fatal
def test_a_rate_that_fails_is_recorded_not_raised(store, monkeypatch):
    _setup(store)

    def boom(*a, **k):
        raise RuntimeError("no such column")
    monkeypatch.setattr(snap.preprod, "pick_rate", boom)
    mine = next(a for a in snap.collect(store["dsn"])["accounts"]
                if a["account_id"] == store["account"])
    assert mine["rates"]["pick_rate"].startswith("unavailable: RuntimeError")
    assert isinstance(mine["rates"]["shoot_rate"], dict)
