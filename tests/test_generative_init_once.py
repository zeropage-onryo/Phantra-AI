"""A render must not run a schema init.

The same race tests/test_init_race.py is about, on the render path and
with no start in it. Every render adapter (fal, nano_banana, effects,
midjourney) opened with generative.init(dsn) -- before its cap check and
before its hold -- and ran it again for the shot row; the Assets wall's
record() and fal's receipt (Tracker.submitted) ran their own init the
same way. An init is not safe beside a copy of itself (db.run_init says
why): it takes CREATE INDEX's ShareLock on its table and then wants
own_table's UPDATE on it, so two at once each wait for the other and
Postgres ends one with

    psycopg.errors.DeadlockDetected: deadlock detected
    ... UPDATE shots SET account_id = $1 WHERE account_id IS NULL

Measured 2026-10-11 on a schema that already had the tables and one
seeded account, 6 of 6 rounds each:

- two generative.init(dsn) in two threads: one deadlocked;
- two stills at once through nano_banana.generate_from_prompt: one came
  back {"ok": False}, nothing charged, no still;
- two render_assets.record_best_effort() released together: one row
  never written (swallowed -- a paid output missing from the Assets wall);
- two fal_requests Tracker.submitted() released together: one job left
  with no receipt (logged -- a render nothing can reattach to).

generative.ensure, render_assets.ensure and fal_requests.ensure are the
fix: the init runs once per process and database, through db.run_init,
and a render is only the render.

THE LEDGER'S OWN INIT IS NOT THIS FILE'S. charge.Charge.take ran
ledger.init(dsn) on every hold until ledger.ensure (its own change, with
its own tests); on a tree without it two holds at once deadlock THERE,
one step after the ones tested here. So the renders below run with the
ledger made once, by its real init, and its per-call init stubbed: with
ledger.ensure the stub is never reached, and without it the stub is what
keeps this file about its own tables.
"""
import ast
import inspect
import textwrap
import threading

import pytest

from ops import render_queue
from src import (
    accounts,
    db,
    effects,
    fal,
    fal_requests,
    generative,
    ledger,
    midjourney,
    nano_banana,
    preprod,
    pricing,
    render_assets,
)

# Without the ensure()s every race below failed in its first round, every
# run; each round is a fresh schema (about a second to make), which is
# what keeps this low.
ROUNDS = 3

GRANTED = 100_000
STILL_MODEL = "gemini-2.5-flash-image"      # pinned: a .env may name Pro
CLIP_MODEL = "kling3-turbo-pro"
PROMPT = "a rider suits up in a cold garage and does not look back " * 2

# the tables a render writes, by the module whose init makes them
MADE_BY = {
    generative: ("shots", "generations"),
    render_assets: ("generated_assets",),
    fal_requests: ("fal_requests",),
}
MODULES = tuple(MADE_BY)
TABLES = tuple(t for tables in MADE_BY.values() for t in tables)

_LEDGER_INIT = ledger.init          # the real one, whatever a test stubs


def _race(*fns):
    """Run each of `fns` in its own thread, released together: what each
    returned (None where it raised), and the errors raised."""
    results, errors = [None] * len(fns), []
    barrier = threading.Barrier(len(fns))

    def run(i, fn):
        barrier.wait()
        try:
            results[i] = fn()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(fns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not any(t.is_alive() for t in threads), "a render never finished"
    return results, errors


def _seeded(dsn):
    """A schema with one account in it and none of the render tables:
    what a process no start ran in begins from on a new database. The
    account is what makes own_table's backfill run its UPDATE."""
    db.init_db(dsn)
    accounts.seed("race@example.com", dsn=dsn)
    with db.connect(dsn) as conn:
        return int(conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"])


def _made_elsewhere(dsn, *modules):
    """The modules' tables as ANOTHER process's start left them -- the
    web app's, seen from a CLI or a graph run. Each module's real init,
    which this process then forgets having run: the database is exactly
    what an init leaves and the process is one that never ran it. The
    tables being there is what turns two first inits into the deadlock
    (both take CREATE INDEX's ShareLock, each then waits on the other's
    UPDATE)."""
    for module in modules:
        module.init(dsn)
        getattr(module, "_ready", set()).discard(db.resolve_dsn(dsn))


def _has(dsn, *tables):
    with db.connect(dsn) as conn:
        return all(db.table_exists(conn, t) for t in tables)


def _count(dsn, table):
    with db.connect(dsn) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _schema_work(monkeypatch):
    """Every own_table on a render table from here on -- the UPDATE that
    deadlocks, and one per table per init. generative imports the
    function by name; the other two call it on db."""
    seen, real = [], db.own_table

    def own_table(conn, table):
        if table in TABLES:
            seen.append(table)
        real(conn, table)

    monkeypatch.setattr(db, "own_table", own_table)
    monkeypatch.setattr(generative, "own_table", own_table)
    return seen


# --------------------------------------------------------------------------
# a studio with nothing real around the tables
# --------------------------------------------------------------------------


def _fal_queue(url, payload=None):
    """fal's queue, answering at once: the receipt, COMPLETED, the clip."""
    if payload is not None:
        return {"status": fal.STATUS_QUEUED, "request_id": "req",
                "status_url": "https://queue.test/status",
                "response_url": "https://queue.test/result",
                "cancel_url": "https://queue.test/cancel"}
    if url.endswith("/status"):
        return {"status": "COMPLETED"}
    return {"video": {"url": "https://cdn.test/clip.mp4"}}


@pytest.fixture
def studio(monkeypatch):
    """The image model and fal's queue faked, no bucket, no RAG shelf.
    Everything that touches the render tables is real: the cap check, the
    shot and generations rows, the hold and its settle, fal's receipt and
    the Assets wall's row. Returns make(dsn, start=...) -> account id."""
    import src.storage as storage

    def image(prompt, out_path, **kw):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"\x89PNG")
        return out_path

    def download(url, out_path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"\x00" * 2048)

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.setattr(nano_banana, "generate_image", image)
    monkeypatch.setattr(fal, "_download", download)
    monkeypatch.setattr(fal, "_request", lambda *a, **k: pytest.fail("real HTTP"))
    monkeypatch.setattr(fal, "POLL_SECONDS", 0)
    monkeypatch.setattr(storage, "configured", lambda: False)
    # the wall's row is the subject; the shelf it also feeds is not
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 0, "error": None})

    def make(dsn, *, start):
        """One funded account on `dsn`. start=True is the web app: this
        process's start made the render tables. start=False is a CLI or a
        graph run: another process's did. start=None: nobody has."""
        account_id = _seeded(dsn)
        preprod.init(dsn)
        _LEDGER_INIT(dsn)
        # see the module docstring: the ledger's per-call init is not ours
        monkeypatch.setattr(ledger, "init", lambda dsn=None: None)
        ledger.grant(account_id, GRANTED, "purchase", dsn=dsn)
        if start:
            for module in MODULES:
                module.init(dsn)
        elif start is False:
            _made_elsewhere(dsn, *MODULES)
        return account_id

    return make


def _still(dsn, account_id, concept_id):
    """One Nano still. `concept_id` is what makes its file name its own:
    the stamp in it is second-resolution, so two stills with no concept
    made in the same second are one file (nano_banana says so)."""
    return nano_banana.generate_from_prompt(
        PROMPT, db_path=dsn, account_id=account_id, model=STILL_MODEL,
        concept_id=concept_id)


def _scene(dsn, account_id, title):
    return preprod.save_concept(
        {"title": title, "hook": "h", "logline": "l",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "KLING",
                    "prompt": PROMPT, "refs": ["/refs/seed.jpg"]}]}, dsn=dsn, account_id=account_id)


def _clip(dsn, account_id, concept_id):
    """One scene rendered through the Queue's own door."""
    return fal.generate_for_shot(
        concept_id, 1, db_path=dsn, model=CLIP_MODEL, http=_fal_queue,
        approved=True, account_id=account_id)


def _spent(dsn, account_id):
    return -sum(e["delta"] for e in ledger.entries(account_id, dsn)
                if e["kind"] != "grant")


def _both_made(results, errors, round_no):
    assert errors == [], f"round {round_no}: {errors!r}"
    assert [r["error"] for r in results] == [None, None], f"round {round_no}"
    assert all(r["ok"] for r in results)
    assert results[0]["generation_id"] != results[1]["generation_id"]


# --------------------------------------------------------------------------
# two renders at once
# --------------------------------------------------------------------------


def test_two_stills_at_once_are_both_made_and_both_charged(pg_factory, studio):
    """The failure itself: one of the two came back {"ok": False,
    "error": "deadlock detected ... UPDATE shots SET account_id"}, every
    round, before its hold -- nothing charged, and no still. Both are
    made now, each charged its own price, each on the wall."""
    price = pricing.still_credits(STILL_MODEL)
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = studio(dsn, start=False)
        stills, errors = _race(lambda: _still(dsn, account_id, 1),
                               lambda: _still(dsn, account_id, 2))
        _both_made(stills, errors, round_no)
        assert _spent(dsn, account_id) == 2 * price
        assert ledger.outstanding(account_id, dsn) == 0
        assert ledger.available(account_id, dsn) == GRANTED - 2 * price
        assert _count(dsn, "generations") == 2
        assert None not in [s["asset_id"] for s in stills]
        assert _count(dsn, "generated_assets") == 2


def test_two_stills_at_once_after_the_start_are_both_made(pg_factory, studio):
    """The web app's case: its start made the tables, so two stills at
    once are two stills and nothing else, round after round. (The
    per-call init deadlocked here too -- it ran whoever had made them.)"""
    price = pricing.still_credits(STILL_MODEL)
    dsn = pg_factory()
    account_id = studio(dsn, start=True)
    for round_no in range(ROUNDS):
        stills, errors = _race(lambda: _still(dsn, account_id, 2 * round_no + 1),
                               lambda: _still(dsn, account_id, 2 * round_no + 2))
        _both_made(stills, errors, round_no)
    assert _spent(dsn, account_id) == 2 * ROUNDS * price
    assert _count(dsn, "generations") == 2 * ROUNDS
    assert _count(dsn, "generated_assets") == 2 * ROUNDS


def test_two_clips_at_once_are_both_rendered_tracked_and_filed(pg_factory, studio):
    """Two scenes approved together, through fal.generate_for_shot: the
    same init, then fal's receipt and the wall's row -- each of which ran
    an init of its own."""
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = studio(dsn, start=False)
        scenes = [_scene(dsn, account_id, title) for title in ("Cold open", "Last light")]
        clips, errors = _race(lambda: _clip(dsn, account_id, scenes[0]),
                              lambda: _clip(dsn, account_id, scenes[1]))
        _both_made(clips, errors, round_no)
        assert ledger.outstanding(account_id, dsn) == 0
        assert _spent(dsn, account_id) > 0
        with db.connect(dsn) as conn:
            receipts = conn.execute(
                "SELECT outcome, generation_id FROM fal_requests "
                "WHERE account_id = %s ORDER BY id", (account_id,)).fetchall()
        assert [r["outcome"] for r in receipts] == ["rendered", "rendered"]
        assert {r["generation_id"] for r in receipts} == {c["generation_id"] for c in clips}
        assert _count(dsn, "generated_assets") == 2
        for scene_id in scenes:
            shot = preprod.get_concept(scene_id, dsn, account_id=account_id)["shots"][0]
            assert shot.get("media_url")


def test_a_still_beside_a_clip_are_both_made(pg_factory, studio):
    """Two adapters, one table: a still approved while a scene renders."""
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = studio(dsn, start=False)
        scene_id = _scene(dsn, account_id, "Cold open")
        made, errors = _race(lambda: _still(dsn, account_id, scene_id),
                             lambda: _clip(dsn, account_id, scene_id))
        _both_made(made, errors, round_no)
        assert ledger.outstanding(account_id, dsn) == 0
        assert _count(dsn, "generations") == 2
        assert _count(dsn, "generated_assets") == 2


def test_two_first_renders_in_a_fresh_schema_are_both_made(pg_factory, studio):
    """Nobody has made the tables: whichever render gets there makes them
    and the other waits. (Two CREATE TABLE IF NOT EXISTS at once is not a
    deadlock, it is a UniqueViolation on pg_type -- the same two inits,
    one statement earlier.)"""
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = studio(dsn, start=None)
        assert not _has(dsn, "generations")
        stills, errors = _race(lambda: _still(dsn, account_id, 1),
                               lambda: _still(dsn, account_id, 2))
        _both_made(stills, errors, round_no)
        assert _count(dsn, "generated_assets") == 2


# --------------------------------------------------------------------------
# a render is only the render
# --------------------------------------------------------------------------


def test_a_still_does_no_schema_work_after_the_start(pg, studio, monkeypatch):
    """The web app makes these tables at start, under db.run_init
    (app.main.init_tables). After that a still must be the still: no DDL
    and no backfill UPDATE on shots, generations or generated_assets, so
    there is nothing for two of them to deadlock on however they land.
    It ran the generations init twice and the wall's once."""
    account_id = studio(pg, start=True)
    seen = _schema_work(monkeypatch)
    still = _still(pg, account_id, 7)
    assert still["ok"], still["error"]
    assert seen == []
    assert _spent(pg, account_id) == pricing.still_credits(STILL_MODEL)
    assert still["asset_id"] is not None


def test_a_clip_does_no_schema_work_after_the_start(pg, studio, monkeypatch):
    """The same for a scene's render, which also files fal's receipt."""
    account_id = studio(pg, start=True)
    scene_id = _scene(pg, account_id, "Cold open")
    seen = _schema_work(monkeypatch)
    clip = _clip(pg, account_id, scene_id)
    assert clip["ok"], clip["error"]
    assert seen == []
    assert fal_requests.open_count(account_id, pg) == 0
    assert _count(pg, "fal_requests") == 1


def test_the_first_renders_make_each_table_once_and_only_once(pg, studio, monkeypatch):
    """No start made the tables here, so the first render does -- once
    per table, not once per render. The guarantee the per-call init gave,
    kept: a missing table would be UndefinedTable, not a still."""
    account_id = studio(pg, start=None)
    assert not _has(pg, *TABLES)
    seen = _schema_work(monkeypatch)
    for n in range(3):
        still = _still(pg, account_id, n + 1)
        assert still["ok"], still["error"]
    assert seen == ["shots", "generations", "generated_assets"]
    scene_id = _scene(pg, account_id, "Cold open")
    for _ in range(2):
        clip = _clip(pg, account_id, scene_id)
        assert clip["ok"], clip["error"]
    assert seen == ["shots", "generations", "generated_assets", "fal_requests"]
    assert _has(pg, *TABLES)


def test_tables_that_cannot_be_made_refuse_the_still_before_any_spend(pg, studio,
                                                                     monkeypatch):
    """ensure() sits where the init sat, inside the adapter's try: a log
    that cannot be made is {"ok": False} with the reason, before the hold
    and before the model, exactly as a failed init was."""
    account_id = studio(pg, start=None)
    drawn = []
    monkeypatch.setattr(nano_banana, "generate_image",
                        lambda *a, **k: drawn.append(1))

    def down(dsn=None):
        raise RuntimeError("no database for a moment")

    monkeypatch.setattr(generative, "init", down)
    still = _still(pg, account_id, 1)
    assert still["ok"] is False and "no database for a moment" in still["error"]
    assert drawn == [] and _spent(pg, account_id) == 0


# --------------------------------------------------------------------------
# the wall's row and fal's receipt, alone
# --------------------------------------------------------------------------


def _file(dsn, account_id, n):
    return render_assets.record_best_effort(
        generation_id=n, tool="nano", model=STILL_MODEL, media_kind="image",
        prompt=PROMPT, media_url=f"/renders/nano/{n}.png", dsn=dsn,
        account_id=account_id)


def test_two_renders_finishing_together_are_both_on_the_wall(pg_factory, monkeypatch):
    """record() ran render_assets.init on every call, and
    record_best_effort swallowed the deadlock: the still was made and
    charged, and one of the two never reached the Assets wall."""
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 0, "error": None})
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = _seeded(dsn)
        _made_elsewhere(dsn, render_assets)
        rows, errors = _race(lambda: _file(dsn, account_id, 1),
                             lambda: _file(dsn, account_id, 2))
        assert errors == [], f"round {round_no}: {errors!r}"
        assert None not in [r["id"] for r in rows], f"round {round_no}: {rows!r}"
        assert len(render_assets.list_all(dsn, account_id=account_id)) == 2


def test_two_repoints_at_once_both_land(pg_factory, monkeypatch):
    """update_media_url, the other writer that ran the init per call."""
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 0, "error": None})
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = _seeded(dsn)
        render_assets.init(dsn)
        ids = [_file(dsn, account_id, n)["id"] for n in (1, 2)]
        _made_elsewhere(dsn, render_assets)
        _, errors = _race(*[
            lambda i=i: render_assets.update_media_url(
                i, f"https://cdn.test/{i}.png", dsn, account_id=account_id)
            for i in ids])
        assert errors == [], f"round {round_no}: {errors!r}"
        urls = {a["media_url"] for a in render_assets.list_all(dsn, account_id=account_id)}
        assert urls == {f"https://cdn.test/{i}.png" for i in ids}


def _submit(dsn, account_id, n):
    tracker = fal_requests.Tracker(
        account_id=account_id, ref=f"c{n}-s1.mp4", hold_id=None, held=0,
        model=CLIP_MODEL, model_id="fal-ai/x", out_path=f"/renders/fal/c{n}-s1.mp4",
        context={"kind": "shot"}, dsn=dsn)
    tracker.submitted({"request_id": f"req-{n}",
                       "status_url": "https://queue.test/status",
                       "response_url": "https://queue.test/result"})
    return tracker


def test_two_submits_at_once_both_leave_a_receipt(pg_factory, capsys):
    """Tracker.submitted() ran fal_requests.init on every submit and
    logged the deadlock instead of raising it: fal was running the job
    and nothing here could reattach to it if the worker died."""
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        account_id = _seeded(dsn)
        _made_elsewhere(dsn, fal_requests)
        trackers, errors = _race(lambda: _submit(dsn, account_id, 1),
                                 lambda: _submit(dsn, account_id, 2))
        assert errors == [], f"round {round_no}: {errors!r}"
        assert [t.recorded for t in trackers] == [True, True], (
            f"round {round_no}: {capsys.readouterr().err}")
        assert fal_requests.open_count(account_id, dsn) == 2
        for n in (1, 2):
            assert fal_requests.get(f"c{n}-s1.mp4", account_id=account_id,
                                    dsn=dsn)["request_id"] == f"req-{n}"


def test_a_receipt_that_cannot_be_written_is_still_only_logged(pg, monkeypatch, capsys):
    """ensure() sits where the init sat, inside submitted()'s try: the
    job is already at fal, so bookkeeping that fails is said loudly and
    never raised."""
    account_id = _seeded(pg)

    def down(dsn=None):
        raise RuntimeError("no database for a moment")

    monkeypatch.setattr(fal_requests, "init", down)
    tracker = _submit(pg, account_id, 1)
    assert tracker.recorded is False
    assert "COULD NOT RECORD fal request req-1" in capsys.readouterr().err


# --------------------------------------------------------------------------
# ensure(), the same in all three modules
# --------------------------------------------------------------------------


@pytest.fixture(params=MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def module(request):
    return request.param


def test_two_inits_at_once_are_why(pg_factory, module):
    """Not the fix, the reason for it: a raw init() beside a copy of
    itself still deadlocks, which is why nothing on a render's path may
    call one. If this stops failing the inits became safe and ensure()
    is only a saving."""
    lost = 0
    for _ in range(ROUNDS):
        dsn = pg_factory()
        _seeded(dsn)
        module.init(dsn)
        _, errors = _race(lambda: module.init(dsn), lambda: module.init(dsn))
        lost += bool(errors)
    assert lost, "two inits side by side no longer deadlock"


def test_two_first_uses_at_once_make_the_tables_once(pg_factory, module):
    """ensure() beside itself, where another process made the tables: one
    thread runs the init, the other waits for it."""
    for round_no in range(ROUNDS):
        dsn = pg_factory()
        _seeded(dsn)
        _made_elsewhere(dsn, module)
        _, errors = _race(lambda: module.ensure(dsn), lambda: module.ensure(dsn))
        assert errors == [], f"round {round_no}: {errors!r}"


def test_first_use_still_makes_the_tables_in_each_database(pg, pg_factory, module):
    """The guarantee the per-call init gave, kept: a database this process
    has not made the tables in gets them on first use. Per database, so a
    second schema in the same process is not skipped because the first
    one is done."""
    for dsn in (pg, pg_factory()):
        db.init_db(dsn)
        assert not _has(dsn, *MADE_BY[module])
        module.ensure(dsn)
        assert _has(dsn, *MADE_BY[module])


def test_the_database_is_named_by_the_environment_too(pg, pg_factory, module,
                                                      monkeypatch):
    """dsn=None is DATABASE_URL, read per call (the web app, a CLI): the
    same rule, keyed by the database it resolves to."""
    for dsn in (pg, pg_factory()):
        db.init_db(dsn)
        monkeypatch.setenv("DATABASE_URL", dsn)
        module.ensure()
        assert _has(dsn, *MADE_BY[module])


def test_an_init_at_start_is_the_only_one(pg, module, monkeypatch):
    """init() records the database it finished against, which is what
    lets a render in the web app run none."""
    db.init_db(pg)
    module.init(pg)
    seen = _schema_work(monkeypatch)
    for _ in range(3):
        module.ensure(pg)
    assert seen == []


def test_a_first_init_that_failed_is_run_again(pg, module, monkeypatch):
    """Only an init that finished counts. One that raised is not
    remembered as done, or every later render would name a table that
    was never made."""
    db.init_db(pg)
    real, calls = module.init, []

    def flaky(dsn=None):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("no database for a moment")
        real(dsn)

    monkeypatch.setattr(module, "init", flaky)
    with pytest.raises(RuntimeError):
        module.ensure(pg)
    assert not _has(pg, *MADE_BY[module])
    module.ensure(pg)
    module.ensure(pg)
    assert len(calls) == 2 and _has(pg, *MADE_BY[module])


def test_the_first_use_takes_its_turn_with_a_start(pg, module, monkeypatch):
    """The first init goes through db.run_init, so it waits for another
    process's start (the lock every start takes) and runs again if
    Postgres still picks it as a deadlock's victim."""
    db.init_db(pg)
    through, real = [], db.run_init

    def run_init(steps, dsn=None, **kw):
        through.append(dsn)
        return real(steps, dsn, **kw)

    monkeypatch.setattr(db, "run_init", run_init)
    module.ensure(pg)
    module.ensure(pg)
    assert through == [pg] and _has(pg, *MADE_BY[module])


def test_an_init_stubbed_by_keyword_is_still_what_ensure_runs(pg, monkeypatch):
    """The adapters always called generative.init(**kwargs), so a test
    that stubs it as `lambda **k: None` (tests/test_element_sheet.py)
    must keep working: ensure() calls the init by keyword too."""
    seen = []
    monkeypatch.setattr(generative, "init", lambda **k: seen.append(k))
    generative.ensure(dsn=pg)
    generative.ensure()
    assert seen == [{"dsn": pg}, {"dsn": None}]


# --------------------------------------------------------------------------
# the tripwire
# --------------------------------------------------------------------------


def _calls(obj):
    """Every call in `obj`'s source, as written: "generative.ensure",
    "init", ... Parsed, so a comment that names the init is not a call."""
    names = set()
    for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(obj)))):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name):
            names.add(fn.id)
        elif isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
            names.add(f"{fn.value.id}.{fn.attr}")
    return names


RENDER_DOORS = (
    fal._shot_row_for_prompt, fal.generate_candidates, fal.generate_for_shot,
    fal.generate_from_prompt, fal.generate_image_from_prompt,
    nano_banana._shot_row_for_prompt, nano_banana.generate_from_prompt,
    effects.run, midjourney._shot_row_for_prompt,
    render_queue.import_clip,
)


def test_no_render_path_names_an_init():
    """A per-call init on any of these paths is this bug again, whatever
    else the function does."""
    for adapter in (fal, nano_banana, effects, midjourney):
        assert "generative.init" not in _calls(adapter), adapter.__name__
    for door in RENDER_DOORS:
        calls = _calls(door)
        assert "generative.init" not in calls, door.__qualname__
        assert "generative.ensure" in calls, door.__qualname__
    for writer in (render_assets.record, render_assets.update_media_url,
                   fal_requests.Tracker.submitted):
        calls = _calls(writer)
        assert "init" not in calls, writer.__qualname__
        assert "ensure" in calls, writer.__qualname__
