"""ops/tokenize_old_renders.py: the pure pieces, and the rewrite against a
real (throwaway) schema. The bucket is a fake: tests never touch the network."""
import json

import pytest

from ops import tokenize_old_renders as tok
from src import db, render_names

OLD = "c12-s1-20261001-120000.png"
KEYS = [
    f"m/1/renders/nano/{OLD}",
    f"t/1/renders/nano/{OLD}",
    "m/1/renders/fal/wf-20261002-101010.mp4",
    f"m/1/renders/fal/c3-s1-20261003-000000-{'a' * 32}.mp4",          # already tokened
    f"m/1/renders/cut/media/{'b' * 24}.mp4",                          # content-addressed
    "m/shared/refs/abc.jpg",
    "m/1/characters/mara/IMG_1.JPG",
    f"m/2/renders/nano/{OLD}",                                         # same name, other account
]


def test_only_guessable_render_masters_are_chosen():
    names = [(o["account"], o["name"]) for o in tok.legacy_objects(KEYS)]
    assert (1, OLD) in names and (1, "wf-20261002-101010.mp4") in names
    assert all("a" * 32 not in n and "b" * 24 not in n for _a, n in names)
    assert not any("IMG_1" in n or "abc" in n for _a, n in names)


def test_a_name_shared_by_two_objects_is_set_aside():
    usable, ambiguous = tok.split_ambiguous(tok.legacy_objects(KEYS))
    assert [o["name"] for o in usable] == ["wf-20261002-101010.mp4"]
    assert {o["account"] for o in ambiguous} == {1, 2}


def test_the_new_name_keeps_the_readable_prefix_and_gains_the_token():
    fresh = tok.new_name(OLD)
    assert fresh.startswith("c12-s1-20261001-120000-") and fresh.endswith(".png")
    assert render_names.has_token(fresh)


def test_the_manifest_pairs_object_and_thumbnail():
    objs = [o for o in tok.legacy_objects(KEYS) if o["account"] == 1 and o["name"] == OLD]
    entry = tok.make_manifest(objs, set(KEYS))[0]
    assert entry["old_key"] == f"m/1/renders/nano/{OLD}"
    assert entry["new_key"] == f"m/1/renders/nano/{entry['new_name']}"
    assert entry["old_thumb"] == f"t/1/renders/nano/{OLD}"
    assert entry["new_thumb"] == f"t/1/renders/nano/{entry['new_name']}"
    assert entry["new_rel"] == f"nano/{entry['new_name']}"


def test_rewrite_swaps_whole_names_only():
    m = {OLD: "NEW.png"}
    assert tok.rewrite_text(f"/renders/nano/{OLD}", m) == "/renders/nano/NEW.png"
    assert tok.rewrite_text(f"https://x/m/1/renders/nano/{OLD}?v=1", m).endswith("NEW.png?v=1")
    assert tok.rewrite_text(f"x{OLD}", m) == f"x{OLD}"            # not the end of a longer name
    assert tok.rewrite_text(f"{OLD}.jpg", m) == "NEW.png.jpg"
    assert tok.rewrite_text("c12-s1-20261001-120000.png2", m) == "c12-s1-20261001-120000.png2"


@pytest.fixture
def table(pg):
    with db.connect(pg) as conn:
        conn.execute("CREATE TABLE t_rows (id serial primary key, a text, j jsonb, n int)")
        conn.execute("INSERT INTO t_rows (a, j, n) VALUES (%s, %s::jsonb, 1), "
                     "('nothing here', '{}'::jsonb, 2), (%s, '{}'::jsonb, 3)",
                     (f"/renders/nano/{OLD}", json.dumps({"clip": f"data/renders/nano/{OLD}", "k": 2}),
                      f"{OLD}-shaped but not it"))
    return pg


def test_scan_finds_every_column_and_rewrite_changes_a_row_once(table):
    with db.connect(table) as conn:
        rows = tok.scan(conn, {OLD})
        # the SQL filter is loose (it also catches the lookalike); the rewrite is exact
        assert [set(r["columns"]) for r in rows] == [{"a", "j"}, {"a"}]
        assert tok.apply_rewrite(conn, rows, {OLD: "NEW.png"}) == 1
    with db.connect(table) as conn:
        a, j = conn.execute("SELECT a, j FROM t_rows WHERE id = 1").fetchone()
        assert a == "/renders/nano/NEW.png" and j["clip"] == "data/renders/nano/NEW.png" and j["k"] == 2
        assert conn.execute("SELECT a FROM t_rows WHERE id = 3").fetchone()[0].startswith(OLD)


def test_revert_puts_the_old_name_back(table, tmp_path):
    entry = {"old_name": OLD, "new_name": "NEW.png"}
    (tmp_path / "m.json").write_text(json.dumps({"entries": [entry]}))
    with db.connect(table) as conn:
        tok.apply_rewrite(conn, tok.scan(conn, {OLD}), {OLD: "NEW.png"})
    assert tok.revert(tmp_path / "m.json", table) == 1
    with db.connect(table) as conn:
        assert conn.execute("SELECT a FROM t_rows WHERE id = 1").fetchone()[0] == f"/renders/nano/{OLD}"


def test_ledger_and_history_columns_are_never_rewritten():
    assert ("credit_entries", "ref") in tok.IDENTIFIER_COLUMNS
    assert ("generations", "params_json") in tok.IDENTIFIER_COLUMNS
    assert ("generations", "output_path") not in tok.IDENTIFIER_COLUMNS
