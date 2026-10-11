"""A hold must not run the ledger's schema init.

The same race tests/test_init_race.py is about, on the money path and
with no start in it. charge.Charge.take ran ledger.init(dsn) on every
hold -- every render approve, every charged still -- and the MCP `quote`
ran it on every quote. An init is not safe beside a copy of itself
(db.run_init says why): ledger.init takes CREATE INDEX's ShareLock on
credit_lots and credit_entries and then wants own_table's UPDATE on
them, so two at once each wait for the other and Postgres ends one with

    psycopg.errors.DeadlockDetected: deadlock detected

Measured 2026-10-11: two ledger.init(dsn) in two threads, on a schema
that already had the tables and one seeded account, deadlocked in 6 of
6 rounds. Two stills approved together, or a still beside a render, is
exactly that -- and the one that lost failed before its hold was taken.

ledger.ensure is the fix: the init runs once per process and database,
through db.run_init, and a hold is only the hold. The first two tests
are the race and the steady state; both fail without it.
"""
import inspect
import threading

import pytest

from src import accounts, charge, db, ledger, mcp_server, preprod

# Without ledger.ensure every race below failed in its first round, every
# run; each round is a fresh schema (about a second to make), which is
# what keeps this low.
ROUNDS = 3

USD = 0.5                               # one hold's estimate
GRANTED = 10_000


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
    assert not any(t.is_alive() for t in threads), "a hold never finished"
    return results, errors


def _seeded(dsn):
    """A schema with one account in it and NO ledger: what a process
    that never ran the web lifespan starts from on a new database. The
    account is what makes own_table's backfill run its UPDATE."""
    db.init_db(dsn)
    accounts.seed("race@example.com", dsn=dsn)
    with db.connect(dsn) as conn:
        account_id = conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"]
    return dsn, int(account_id)


def _made_elsewhere(dsn):
    """The same, with the ledger's tables already in the database but
    made by ANOTHER process -- the web app's start, seen from the stdio
    MCP server or a CLI. ledger.init's own statements on a bare
    connection, so this process has initialised nothing; the tables being
    there is what turns two first inits into the deadlock (both take
    CREATE INDEX's ShareLock, each then waits on the other's UPDATE).
    Funded, so a hold has something to take."""
    dsn, account_id = _seeded(dsn)
    with db.connect(dsn) as conn:
        conn.execute(ledger.SCHEMA)
        db.own_table(conn, "credit_lots")
        db.own_table(conn, "credit_entries")
        conn.execute(ledger.INDEXES)
        db.add_ledger_balance_trigger(conn)
    ledger.grant(account_id, GRANTED, "purchase", dsn=dsn)
    return dsn, account_id


@pytest.fixture
def seeded(pg_factory):
    return _seeded(pg_factory())


def _charge(dsn, account_id, ref):
    return charge.Charge(account_id, provider="fal", ref=ref, estimate_usd=USD, dsn=dsn)


def _ledger_schema_work(monkeypatch):
    """Every piece of ledger.init's schema work from here on: own_table
    asked to own either ledger table (the UPDATE that deadlocks), and the
    balance triggers."""
    seen, own, triggers = [], db.own_table, db.add_ledger_balance_trigger

    def own_table(conn, table):
        if table in ("credit_lots", "credit_entries"):
            seen.append(table)
        own(conn, table)

    def add_ledger_balance_trigger(conn):
        seen.append("triggers")
        return triggers(conn)

    monkeypatch.setattr(db, "own_table", own_table)
    monkeypatch.setattr(db, "add_ledger_balance_trigger", add_ledger_balance_trigger)
    return seen


ONE_INIT = ["credit_lots", "credit_entries", "triggers"]


def _has_ledger(dsn):
    with db.connect(dsn) as conn:
        return db.table_exists(conn, "credit_lots") and db.table_exists(conn, "credit_entries")


# --------------------------------------------------------------------------
# the hold
# --------------------------------------------------------------------------


def test_two_holds_at_once_are_both_taken(pg_factory):
    """The failure itself: one of the two died on DeadlockDetected, every
    round, before its hold was taken. Both are taken now, and the money
    is what two holds come to."""
    price = ledger.charge_credits(USD)
    for round_no in range(ROUNDS):
        dsn, account_id = _made_elsewhere(pg_factory())
        holds, errors = _race(lambda: _charge(dsn, account_id, "still-a.png").take(),
                              lambda: _charge(dsn, account_id, "still-b.png").take())
        assert errors == [], f"round {round_no}: {errors!r}"
        assert None not in holds and holds[0] != holds[1]
        assert ledger.outstanding(account_id, dsn) == 2 * price
        assert ledger.available(account_id, dsn) == GRANTED - 2 * price


def test_two_holds_at_once_after_the_start_are_both_taken(pg_factory):
    """The web app's case: its start made the ledger, so two holds at
    once are two holds and nothing else, round after round."""
    price = ledger.charge_credits(USD)
    dsn, account_id = _seeded(pg_factory())
    ledger.init(dsn)
    ledger.grant(account_id, GRANTED, "purchase", dsn=dsn)
    for round_no in range(ROUNDS):
        holds, errors = _race(
            lambda: _charge(dsn, account_id, f"render-{round_no}.mp4").take(),
            lambda: _charge(dsn, account_id, f"still-{round_no}.png").take())
        assert errors == [], f"round {round_no}: {errors!r}"
        assert None not in holds and holds[0] != holds[1]
    assert ledger.outstanding(account_id, dsn) == 2 * ROUNDS * price


def test_a_hold_does_no_schema_work_after_the_start(seeded, monkeypatch):
    """The web app makes the ledger at start, under db.run_init
    (app.main.init_tables). After that a hold must be the hold: no DDL
    and no backfill UPDATE, so there is nothing for two of them to
    deadlock on however they land. The whole sandwich, not only take()."""
    dsn, account_id = seeded
    ledger.init(dsn)
    ledger.grant(account_id, GRANTED, "purchase", dsn=dsn)
    seen = _ledger_schema_work(monkeypatch)
    price = ledger.charge_credits(USD)
    kept = _charge(dsn, account_id, "kept.mp4")
    assert kept.take() is not None
    kept.submitted()
    assert kept.settle() == price
    given_back = _charge(dsn, account_id, "failed.mp4")
    given_back.take()
    assert given_back.release("provider error") == price
    assert seen == []
    assert ledger.available(account_id, dsn) == GRANTED - price
    assert ledger.outstanding(account_id, dsn) == 0


def test_the_first_hold_makes_the_ledger_once_and_only_once(seeded, monkeypatch):
    """No start made the tables here, so the first hold does -- once, not
    once per hold. Refused for the empty balance, which is the ledger
    answering: a missing table would be UndefinedTable."""
    dsn, account_id = seeded
    assert not _has_ledger(dsn)
    seen = _ledger_schema_work(monkeypatch)
    for n in range(3):
        with pytest.raises(ledger.InsufficientCredit):
            _charge(dsn, account_id, f"first-{n}.png").take()
    assert seen == ONE_INIT
    assert _has_ledger(dsn)


def test_two_first_holds_in_a_fresh_schema_are_both_answered(pg_factory):
    """Nobody has made the tables: whichever hold gets there makes them
    and the other waits. (Two CREATE TABLE IF NOT EXISTS at once is not a
    deadlock, it is a UniqueViolation on pg_type -- the same two inits,
    one statement earlier.) Both are answered by the ledger."""
    for round_no in range(ROUNDS):
        dsn, account_id = _seeded(pg_factory())
        _, errors = _race(lambda: _charge(dsn, account_id, "a.png").take(),
                          lambda: _charge(dsn, account_id, "b.png").take())
        assert [type(e) for e in errors] == [ledger.InsufficientCredit] * 2, (
            f"round {round_no}: {errors!r}")


def test_a_ledger_that_cannot_be_made_refuses_the_hold(seeded, monkeypatch):
    """ensure() is outside any try in take(), as the init was: a ledger
    that cannot be made is no hold, and no hold is no submit."""
    dsn, account_id = seeded

    def down(dsn=None):
        raise RuntimeError("no database for a moment")

    monkeypatch.setattr(ledger, "init", down)
    c = _charge(dsn, account_id, "down.png")
    with pytest.raises(RuntimeError, match="no database"):
        c.take()
    assert c.hold_id is None and c.held == 0 and not c.billed


def test_the_unowned_pool_still_touches_no_ledger(seeded, monkeypatch):
    """A render with no account is nobody's bill: no hold, and (as
    before) not even the tables."""
    dsn, _ = seeded
    seen = _ledger_schema_work(monkeypatch)
    assert _charge(dsn, None, "pool.mp4").take() is None
    assert seen == [] and not _has_ledger(dsn)


# --------------------------------------------------------------------------
# ledger.ensure
# --------------------------------------------------------------------------


def test_first_use_still_makes_the_tables_in_each_database(pg, pg_factory):
    """The guarantee the per-call init gave, kept: a database this process
    has not made the ledger in gets it on first use. Per database, so a
    second schema in the same process is not skipped because the first
    one is done."""
    for dsn in (pg, pg_factory()):
        assert not _has_ledger(dsn)
        ledger.ensure(dsn)
        assert _has_ledger(dsn)
        assert ledger.available(None, dsn) == 0


def test_the_database_is_named_by_the_environment_too(pg, pg_factory, monkeypatch):
    """dsn=None is DATABASE_URL, read per call (the web app, a CLI): the
    same rule, keyed by the database it resolves to."""
    for dsn in (pg, pg_factory()):
        monkeypatch.setenv("DATABASE_URL", dsn)
        ledger.ensure()
        assert _has_ledger(dsn)


def test_an_init_at_start_is_the_only_one(pg, monkeypatch):
    """init() records the database it finished against, which is what
    lets a request in the web app run none."""
    ledger.init(pg)
    seen = _ledger_schema_work(monkeypatch)
    for _ in range(3):
        ledger.ensure(pg)
    assert seen == []


def test_a_first_init_that_failed_is_run_again(pg, monkeypatch):
    """Only an init that finished counts. One that raised is not
    remembered as done, or every later hold would name a table that was
    never made."""
    real, calls = ledger.init, []

    def flaky(dsn=None):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("no database for a moment")
        real(dsn)

    monkeypatch.setattr(ledger, "init", flaky)
    with pytest.raises(RuntimeError):
        ledger.ensure(pg)
    assert not _has_ledger(pg)
    ledger.ensure(pg)
    ledger.ensure(pg)
    assert len(calls) == 2 and _has_ledger(pg)


def test_the_first_use_takes_its_turn_with_a_start(pg, monkeypatch):
    """The first init goes through db.run_init, so it waits for another
    process's start (the lock every start takes) and runs again if
    Postgres still picks it as a deadlock's victim."""
    through = []
    real = db.run_init

    def run_init(steps, dsn=None, **kw):
        through.append(dsn)
        return real(steps, dsn, **kw)

    monkeypatch.setattr(db, "run_init", run_init)
    ledger.ensure(pg)
    ledger.ensure(pg)
    assert through == [pg] and _has_ledger(pg)


# --------------------------------------------------------------------------
# the MCP quote
# --------------------------------------------------------------------------


def _scene(dsn, account_id):
    preprod.init(dsn)
    return preprod.save_concept(
        {"title": "Cold open", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "KLING",
                    "desc": "Cold open", "prompt": "A courier crosses a wet street at night.",
                    "refs": ["/characters/sam/photo/face.jpg"]}]},
        brand="zeropage", prompt_template="T", dsn=dsn, account_id=account_id)


def test_two_quotes_at_once_both_answer(pg_factory, monkeypatch):
    """The other call site: `quote` ran the same init on every call, so
    two quotes at once -- or a quote beside a hold -- was the same
    deadlock."""
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    for round_no in range(ROUNDS):
        dsn, account_id = _made_elsewhere(pg_factory())
        scene_id = _scene(dsn, account_id)

        def quote():
            return mcp_server.quote_render(scene_id, dsn=dsn, account_id=account_id)

        quotes, errors = _race(quote, quote,
                               lambda: _charge(dsn, account_id, "beside.png").take())
        assert errors == [], f"round {round_no}: {errors!r}"
        assert quotes[0]["clip"]["credits"] > 0
        assert quotes[0]["clip"] == quotes[1]["clip"]


def test_a_quote_does_no_schema_work_after_the_start(seeded, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    dsn, account_id = seeded
    ledger.init(dsn)
    ledger.grant(account_id, GRANTED, "purchase", dsn=dsn)
    scene_id = _scene(dsn, account_id)
    seen = _ledger_schema_work(monkeypatch)
    out = mcp_server.quote_render(scene_id, dsn=dsn, account_id=account_id)
    assert seen == []
    assert out["balance"] == GRANTED and out["affordable"] is True


def test_the_first_quote_makes_the_ledger_on_a_bare_database(seeded, monkeypatch):
    """stdio on a fresh clone: no start made the ledger (the stdio
    server's own init does not), and the quote still reads a balance."""
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    dsn, account_id = seeded
    scene_id = _scene(dsn, account_id)
    seen = _ledger_schema_work(monkeypatch)
    for _ in range(2):
        out = mcp_server.quote_render(scene_id, dsn=dsn, account_id=account_id)
        assert out["balance"] == 0 and out["affordable"] is False
    assert seen == ONE_INIT


def test_neither_call_site_names_the_init():
    """The tripwire: a per-call ledger.init on either path is this bug
    again, whatever else the function does."""
    for fn in (charge.Charge.take, mcp_server.quote_render):
        source = inspect.getsource(fn)
        assert "ledger.init(" not in source, fn.__qualname__
        assert "ledger.ensure(" in source, fn.__qualname__
