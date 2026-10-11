"""The outcome-event backfill (ops/backfill_output_events.py).

What had already happened before events were recorded is read back from
the rows that prove it, and nothing is invented. Each test names the line
it guards. Nothing here calls a model.
"""
import hashlib
import json

import pytest

from ops import backfill_output_events as backfill
from src import accounts, db, generative, outcomes, render_assets
from src.cut import store as cut_store

WHO = {}


@pytest.fixture
def store(pg, monkeypatch):
    accounts.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    cut_store.init(pg)
    outcomes.init(pg)
    WHO["mine"] = accounts.upsert_account("b-mine", "Mine", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("b-theirs", "Theirs", "#fff", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": False, "chunks": 0, "error": "stubbed"})
    monkeypatch.setattr(render_assets, "drop_chunk", lambda *a, **k: None)
    return pg


def render(dsn, n, who="mine", kind="video", path=None):
    return render_assets.record(
        generation_id=n, tool="wan", model="wan3", media_kind=kind, prompt=f"prompt {n}",
        media_url=f"/renders/fal/r-{n}.mp4", output_path=path, dsn=dsn,
        account_id=WHO[who])["id"]


def version(dsn, project, n, handles, who="mine", exported=None):
    doc = {"fps": 24, "size": [720, 1280], "duration": 0, "markers": [],
           "tracks": [{"id": "V1", "kind": "video",
                       "clips": [{"id": f"c{i}", "media": h} for i, h in enumerate(handles)]}]}
    with db.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO timelines (created_at, project_id, version, doc, author, op_summary, "
            "export_url, account_id) VALUES (%s, %s, %s, %s::jsonb, 'user', 'test', %s, %s)",
            (f"2026-10-0{n}T10:00:00+00:00", project, n, json.dumps(doc), exported, WHO[who]))


def rows(dsn, who="mine"):
    with db.connect(dsn) as conn:
        return sorted((int(r["asset_id"]), r["event"], r["at"]) for r in conn.execute(
            "SELECT asset_id, event, at FROM output_events "
            "WHERE account_id IS NOT DISTINCT FROM %s", (WHO[who],)))


# guards: plan -- a cut's outputs once per cut at first appearance, exports, stars and deletes
def test_the_rows_that_prove_an_event_become_events(store):
    a, b, c = render(store, 1), render(store, 2), render(store, 3)
    theirs = render(store, 4, "theirs")
    version(store, "cut:x", 1, [f"gen:{a}", "asset:9"])
    version(store, "cut:x", 2, [f"gen:{a}", f"gen:{b}", f"gen:{theirs}"], exported="/renders/cut/x.mp4")
    render_assets.organize(c, dsn=store, account_id=WHO["mine"], starred=True)
    render_assets.soft_delete(c, dsn=store, account_id=WHO["mine"])

    planned = backfill.pending(store)
    kinds = sorted((r["asset_id"], r["event"]) for r in planned)
    assert kinds == [(a, "cut_add"), (a, "export"), (b, "cut_add"), (b, "export"),
                     (c, "delete"), (c, "star")]
    # another account's output on this account's timeline is nobody's event
    assert all(r["asset_id"] != theirs for r in planned)
    assert rows(store) == []                          # a report writes nothing

    assert backfill.apply(planned, store) == 6
    got = rows(store)
    assert (a, "cut_add", "2026-10-01T10:00:00+00:00") in got    # dated at first appearance
    assert (b, "cut_add", "2026-10-02T10:00:00+00:00") in got
    with db.connect(store) as conn:
        kept = {int(r["id"]): r["kept"] for r in conn.execute(
            "SELECT id, kept FROM generations WHERE account_id IS NOT DISTINCT FROM %s",
            (WHO["mine"],))}
    assert kept == {}                                 # these test renders have no attempt rows
    # run again: nothing new, nothing doubled
    assert backfill.pending(store) == []
    assert len(rows(store)) == 6


# guards: _element_matches -- only a photo that is byte-for-byte a render this machine holds
def test_an_element_photo_is_matched_to_its_render_by_its_bytes(store, tmp_path):
    data = b"\x89PNG the very same bytes"
    still = tmp_path / "data" / "renders" / "nano" / "s.png"
    still.parent.mkdir(parents=True)
    still.write_bytes(data)
    asset = render(store, 1, kind="image", path=str(still))
    render(store, 2, kind="image", path=str(tmp_path / "missing.png"))
    folder = tmp_path / "props" / "the-can"
    folder.mkdir(parents=True)
    (folder / f"gen-{hashlib.sha1(data).hexdigest()[:16]}.png").write_bytes(data)
    (folder / "gen-0000000000000000.png").write_bytes(b"something else")
    (folder / "upload.jpg").write_bytes(b"an upload")

    found = [r for r in backfill.pending(store, root=tmp_path) if r["event"] == "element_from"]
    assert [(r["asset_id"], r["account_id"]) for r in found] == [(asset, WHO["mine"])]
    assert found[0]["meta"]["photo"].startswith("props/the-can/gen-")


# guards: main -- report by default, never a guessed database
def test_the_cli_reports_by_default_and_never_guesses_the_database(store, monkeypatch, capsys):
    a = render(store, 1)
    render_assets.soft_delete(a, dsn=store, account_id=WHO["mine"])
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert backfill.main(["--write"]) == 2
    assert "never guesses" in capsys.readouterr().err
    assert backfill.main(["--dsn", store]) == 0
    assert "report only" in capsys.readouterr().out and rows(store) == []
    assert backfill.main(["--dsn", store, "--write"]) == 0
    assert [(r[0], r[1]) for r in rows(store)] == [(a, "delete")]
    assert backfill.main(["--dsn", store, "--write"]) == 0
    assert "nothing to record" in capsys.readouterr().out


# guards: apply's teach=False -- history is counted; nothing is taught and no model is called
def test_a_backfill_teaches_nothing(store, monkeypatch):
    from src import preprod, winners
    preprod.init(store)
    winners.init(store)
    accounts.set_prompt_edits_teach("b-mine", True, dsn=store)       # an account that DOES teach
    monkeypatch.setattr(winners, "ingest_to_rag",
                        lambda *a, **k: pytest.fail("the backfill embedded a prompt"))
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                    "prompt": "the scene prompt", "refs": ["/refs/a.jpg"]}]},
        brand="zeropage", dsn=store, account_id=WHO["mine"])
    shot = generative.add_shot(__import__("src.shot", fromlist=["Shot"]).Shot(
        subject="s", action="a"), dsn=store, account_id=WHO["mine"])
    gen = generative.record_generation(shot, "wan", "p", {}, None, 0.5, dsn=store,
                                       account_id=WHO["mine"])
    asset = render_assets.record(
        generation_id=gen, tool="wan", model="wan3", media_kind="video", prompt="p",
        media_url="/renders/fal/k.mp4", concept_id=cid, shot_n=1, dsn=store,
        account_id=WHO["mine"])["id"]
    render_assets.organize(asset, dsn=store, account_id=WHO["mine"], starred=True)

    assert backfill.apply(backfill.pending(store), store) == 1
    assert [(r[0], r[1]) for r in rows(store)] == [(asset, "star")]
    assert winners.recorded(outcomes.pair_ref(cid, 1), dsn=store) == []   # nothing filed
    with db.connect(store) as conn:                                       # but it IS kept
        assert conn.execute("SELECT kept FROM generations WHERE id = %s "
                            "AND account_id IS NOT DISTINCT FROM %s",
                            (gen, WHO["mine"])).fetchone()["kept"] == 1
    # the same event recorded as it happens DOES teach: the flag is the difference
    monkeypatch.setattr(winners, "ingest_to_rag", lambda *a, **k: {"ok": True, "error": None})
    outcomes.record("download", asset_id=asset, account_id=WHO["mine"], dsn=store)
    assert len(winners.recorded(outcomes.pair_ref(cid, 1), dsn=store)) == 1
