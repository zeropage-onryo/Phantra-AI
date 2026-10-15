"""The brand columns' way out (ops/brand_removal_schema.py, 2026-10-13).

Run against a throwaway schema shaped like the live one before step 6:
NOT NULL brand columns with values, the two dead tables, the index and a
Library row carrying an old brand name as its project.
"""
import json

import pytest

from ops import brand_removal_schema as schema
from src import db

OLD = schema.PROJECT_LABELS[0]


@pytest.fixture
def live_shape(pg):
    with db.connect(pg) as conn:
        conn.execute("""
            CREATE TABLE shoot_concepts (id BIGINT PRIMARY KEY, brand TEXT NOT NULL,
                uncanny_overall DOUBLE PRECISION, uncanny_passed INTEGER, uncanny_reason TEXT,
                title TEXT);
            CREATE TABLE scout_findings (id BIGINT PRIMARY KEY, brand TEXT NOT NULL, used_at TEXT);
            CREATE INDEX idx_scout_brand_used ON scout_findings (brand, used_at);
            CREATE TABLE hold_queue (id BIGINT PRIMARY KEY, channel TEXT NOT NULL);
            CREATE TABLE channels (name TEXT PRIMARY KEY);
            CREATE TABLE inspiration_accounts (id BIGINT PRIMARY KEY, handle TEXT);
            CREATE TABLE generated_assets (id BIGINT PRIMARY KEY, project TEXT);
        """)
        conn.execute("INSERT INTO shoot_concepts VALUES (1, %s, 9, 1, 'ok', 'a scene')", (OLD,))
        conn.execute("INSERT INTO scout_findings VALUES (1, %s, NULL)", (OLD,))
        conn.execute("INSERT INTO hold_queue VALUES (1, 'studio')")
        conn.execute("INSERT INTO channels VALUES ('one'), ('two')")
        conn.execute("INSERT INTO inspiration_accounts VALUES (1, 'someone')")
        conn.execute("INSERT INTO generated_assets VALUES (1, %s), (2, 'a client job'), (3, NULL)",
                     (OLD,))
    return pg


def _cols(dsn, table):
    with db.connect(dsn) as conn:
        return {r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = "
            "current_schema() AND table_name = %s", (table,)).fetchall()}


def test_the_report_counts_and_changes_nothing(live_shape):
    report = schema.scan(live_shape)
    by = {(c["table"], c["column"]): c for c in report["columns"]}
    assert by[("shoot_concepts", "brand")] == {
        "table": "shoot_concepts", "column": "brand", "not_null": True, "rows_with_a_value": 1}
    assert ("workflows", "brand") not in by            # a table this schema lacks is skipped
    assert {t["table"]: t["rows"] for t in report["tables"]} == {
        "channels": 2, "inspiration_accounts": 1, "hold_queue": 1}
    assert report["indexes"] == ["idx_scout_brand_used"]
    assert report["generated_assets_project_labels"] == 1
    assert "brand" in _cols(live_shape, "shoot_concepts")


def test_loosen_only_drops_not_null_and_is_rerunnable(live_shape):
    assert sorted(schema.loosen(live_shape)) == [
        "scout_findings.brand", "shoot_concepts.brand"]
    with db.connect(live_shape) as conn:
        conn.execute("INSERT INTO shoot_concepts (id, title) VALUES (2, 'no label')")
    assert schema.loosen(live_shape) == []
    assert "brand" in _cols(live_shape, "shoot_concepts")


def test_drop_after_a_backup_removes_everything_and_keeps_other_projects(live_shape, tmp_path):
    written = schema.backup(live_shape, tmp_path)
    assert written["shoot_concepts.columns"] == 1 and written["channels"] == 2
    saved = json.loads((tmp_path / "generated_assets.project.json").read_text())
    assert saved == [{"id": 1, "project": OLD}]
    lines = schema.drop(live_shape)
    assert "generated_assets.project -> NULL on 1 row(s)" in lines
    assert _cols(live_shape, "shoot_concepts") == {"id", "title"}
    assert _cols(live_shape, "hold_queue") == set()
    assert _cols(live_shape, "channels") == set()
    with db.connect(live_shape) as conn:
        projects = [r["project"] for r in conn.execute(
            "SELECT project FROM generated_assets ORDER BY id").fetchall()]
    assert projects == [None, "a client job", None]       # only the old brand name went
    assert schema.drop(live_shape) == ["generated_assets.project -> NULL on 0 row(s)"]


def test_the_command_refuses_unsafe_combinations(live_shape, capsys):
    assert schema.main(["--dsn", live_shape, "--drop"]) == 2
    assert schema.main(["--dsn", live_shape, "--loosen", "--drop", "--backup", "x"]) == 2
    assert schema.main(["--dsn", live_shape]) == 0
    assert "report only" in capsys.readouterr().out
    assert "brand" in _cols(live_shape, "shoot_concepts")
