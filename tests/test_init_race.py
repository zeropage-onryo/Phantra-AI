"""Two starts must not deadlock each other's schema init.

Found 2026-10-10 in ~/Library/Logs/Claude/mcp-server-zeropage.log: Claude
Desktop launches the stdio MCP server twice within seconds, both run the
whole init against one database, and (eleven times since 2026-09-05) one
of them died on

    UPDATE creative_projects SET account_id = %s WHERE account_id IS NULL
    psycopg.errors.DeadlockDetected: deadlock detected

A module's init holds a ShareLock on its table (CREATE INDEX IF NOT
EXISTS takes one even when the index exists) and then wants a
RowExclusiveLock or an AccessExclusiveLock on it; two of them at once
each wait for the other. db.run_init is the fix; the first test here is
the race itself, driven through the real entry point, and it fails every
round without it.
"""
import inspect
import threading
import time

import psycopg
import pytest

from src import accounts, billing, db, ledger, mcp_server

# Without db.run_init every round of every race below deadlocked on the
# day (10 of 10 through the whole init, 6 of 6 for each of sixteen
# modules alone), so a handful of rounds is already a certain failure;
# the whole init is ~0.7s a start, which is what keeps ENTRY_ROUNDS low.
ENTRY_ROUNDS = 4
ROUNDS = 10
# A balance read is eight connections, and the request-path race below
# failed in round one of every run before its fix.
READ_ROUNDS = 4


@pytest.fixture
def owned(pg):
    """A schema with an account in it -- what makes own_table's backfill
    run its UPDATE, the exact statement in the desktop's log. (With no
    account the same race deadlocks one statement later, on the ALTER.)"""
    accounts.seed("race@example.com", dsn=pg)
    return pg


def _race(fn, n=2):
    """Run `fn` in `n` threads released together; the errors raised."""
    errors = []
    barrier = threading.Barrier(n)

    def run():
        barrier.wait()
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001  (SystemExit included)
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not any(t.is_alive() for t in threads), "a start never finished"
    return errors


def test_two_desktop_starts_do_not_deadlock(owned, monkeypatch):
    """The stdio entry point itself, twice at once, as the desktop
    launches it. Everything but the transport is real."""

    class FakeServer:
        def run(self, transport):
            pass

    monkeypatch.setattr(mcp_server, "build_server", lambda **kw: FakeServer())
    for round_no in range(ENTRY_ROUNDS):
        errors = _race(lambda: mcp_server.main(["--db", owned]))
        assert errors == [], f"round {round_no}: {errors!r}"


def test_four_starts_many_times(owned, monkeypatch):
    """Two desktop entries, each launched twice, is four at once. The
    module in the log, and one whose init ALTERs after its index."""
    from src import creative_projects, render_assets

    monkeypatch.setattr(db, "INIT_LOCK_POLL_S", 0.02)   # three of them queue

    def steps():
        creative_projects.init(owned)
        render_assets.init(owned)

    for round_no in range(ROUNDS):
        errors = _race(lambda: db.run_init(steps, owned), n=4)
        assert errors == [], f"round {round_no}: {errors!r}"


def test_a_start_survives_a_real_deadlock(owned, monkeypatch):
    """The backstop, against Postgres itself: something that never takes
    the init lock (a CLI's own init, a request in flight) holds the
    ShareLock and queues for the write first, so THIS start is the one
    Postgres refuses -- the log's failure, staged step by step. It must
    run its init again and finish, not die."""
    from src import creative_projects

    monkeypatch.setattr(db, "INIT_RETRY_PAUSE_S", 0.05)
    other = psycopg.connect(owned)
    watcher = psycopg.connect(owned, autocommit=True)
    holding, queued = threading.Event(), threading.Event()
    real_own_table, attempts, outcome = db.own_table, [], []

    def own_table(conn, table):
        # By here the start's CREATE INDEX holds its ShareLock too.
        attempts.append(1)
        if len(attempts) == 1:
            holding.set()
            assert queued.wait(20)
        real_own_table(conn, table)

    monkeypatch.setattr(db, "own_table", own_table)

    def start():
        try:
            outcome.append(db.run_init(lambda: creative_projects.init(owned), owned))
        except Exception as exc:  # noqa: BLE001
            outcome.append(exc)

    def write():
        other.execute("UPDATE creative_projects SET account_id = account_id "
                      "WHERE account_id IS NULL")

    try:
        other.execute("LOCK TABLE creative_projects IN SHARE MODE")
        starter = threading.Thread(target=start)
        starter.start()
        assert holding.wait(20)
        writer = threading.Thread(target=write)
        writer.start()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:      # until the write is queued
            if watcher.execute(
                    "SELECT count(*) FROM pg_locks WHERE NOT granted "
                    "AND relation = 'creative_projects'::regclass").fetchone()[0]:
                break
            time.sleep(0.02)
        queued.set()
        writer.join(timeout=20)     # granted once the start is rolled back
        other.commit()
        starter.join(timeout=20)
    finally:
        queued.set()
        other.close()
        watcher.close()
    assert outcome == [None], outcome
    assert len(attempts) == 2       # refused once, then run again


def test_a_second_start_waits_for_the_first(pg):
    ran = threading.Event()
    with db.init_lock(pg) as held:
        assert held
        waiter = threading.Thread(target=lambda: db.run_init(ran.set, pg))
        waiter.start()
        assert not ran.wait(0.6), "the second start ran while the first held the lock"
    assert ran.wait(10), "the second start never ran after the lock was released"
    waiter.join(timeout=10)


def test_a_hung_holder_cannot_block_a_start(pg, capsys):
    ran = []
    with db.init_lock(pg) as held:
        assert held
        began = time.monotonic()
        db.run_init(lambda: ran.append(1), pg, wait=0.4)
        waited = time.monotonic() - began
    assert ran == [1]
    assert 0.4 <= waited < 15      # bounded, not prompt: the suite shares its machine
    assert "starting without it" in capsys.readouterr().err


def test_a_lock_that_cannot_be_asked_for_is_not_a_dead_start(pg, monkeypatch, capsys):
    """The lock is an extra connection; losing it must cost a line on
    stderr and nothing else."""
    def refuse(*a, **kw):
        raise psycopg.OperationalError("no connection for the lock")

    monkeypatch.setattr(db.psycopg, "connect", refuse)
    assert db.run_init(lambda: "done", pg) == "done"
    assert "could not take the schema-init lock" in capsys.readouterr().err


def test_the_lock_connection_prepares_nothing(pg, monkeypatch):
    """Behind a transaction pooler (the live database's) a prepared
    statement lives on ONE server connection and the next poll may land
    on another. psycopg prepares a statement it has run five times, so a
    one-second wait would lose the lock to an error -- and no database on
    this machine can show it. This pins the switch that prevents it."""
    seen = {}
    real = db.psycopg.connect

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(db.psycopg, "connect", spy)
    with db.init_lock(pg) as held:
        assert held
    assert seen["prepare_threshold"] is None


def test_the_lock_is_released_when_the_init_fails(pg):
    def steps():
        raise RuntimeError("init broke")

    with pytest.raises(RuntimeError):
        db.run_init(steps, pg)
    with db.init_lock(pg, wait=0) as held:
        assert held


def test_the_lock_is_per_schema(pg, pg_factory):
    """Two schemas in one database (every test, and every session sharing
    the throwaway) must not wait on each other."""
    other = pg_factory()
    with db.init_lock(pg) as held:
        assert held
        with db.init_lock(other, wait=0) as also:
            assert also
        with db.init_lock(pg, wait=0) as again:
            assert not again


def test_a_deadlocked_init_is_run_again(pg, monkeypatch, capsys):
    monkeypatch.setattr(db, "INIT_RETRY_PAUSE_S", 0)
    calls = []

    def steps():
        calls.append(1)
        if len(calls) == 1:
            raise psycopg.errors.DeadlockDetected("deadlock detected")
        return "ok"

    assert db.run_init(steps, pg) == "ok"
    assert len(calls) == 2
    assert "running it again" in capsys.readouterr().err


def test_a_deadlock_every_time_is_raised(pg, monkeypatch):
    monkeypatch.setattr(db, "INIT_RETRY_PAUSE_S", 0)
    calls = []

    def steps():
        calls.append(1)
        raise psycopg.errors.DeadlockDetected("deadlock detected")

    with pytest.raises(psycopg.errors.DeadlockDetected):
        db.run_init(steps, pg)
    assert len(calls) == db.INIT_ATTEMPTS


def test_any_other_error_is_raised_once(pg):
    calls = []

    def steps():
        calls.append(1)
        raise ValueError("not a deadlock")

    with pytest.raises(ValueError):
        db.run_init(steps, pg)
    assert calls == [1]


def test_the_web_app_inits_through_the_same_lock():
    """A desktop start during a web boot is the same race. The lifespan
    is not entered by the suite, so this reads it: no init() may be
    called from it except through db.run_init."""
    import app.main as app_main

    source = inspect.getsource(app_main.lifespan)
    assert "db.run_init(init_tables)" in source
    assert ".init(" not in source and "init_db(" not in source
    assert "db.init_db()" in inspect.getsource(app_main.init_tables)


# --------------------------------------------------------------------------
# the same race with no start in it: a request path (2026-10-11)
# --------------------------------------------------------------------------
# billing.release_due ran billing.init() on every call and billing.balance
# calls it on every read, so two balance reads at once were two schema
# inits at once: one GET /api/billing/balance died on DeadlockDetected in
# own_table's UPDATE on credit_schedules. The studio's header reads the
# balance whenever a job ends, so two at once is ordinary. No start is
# involved, which is why db.run_init around the lifespan never saw it.
# The init is once per process and database now (billing._ensure).


@pytest.fixture
def ledgered(owned):
    """An account and the ledger, and NOT billing's own table: what
    tests/test_billing.py's fixture makes, and what a process that never
    ran the web lifespan starts from on a new database."""
    ledger.init(owned)
    with db.connect(owned) as conn:
        account_id = conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"]
    return owned, int(account_id)


@pytest.fixture
def made_elsewhere(ledgered):
    """The same, with billing's table already in the database but made by
    ANOTHER process -- the stdio MCP server or the release CLI against a
    database the web app set up. This process has run no billing init, so
    its first reads still have one to run, and the table being there is
    what turns two of them into the deadlock in the traceback (both take
    CREATE INDEX's ShareLock, each then waits on the other for the
    UPDATE)."""
    dsn, account_id = ledgered
    with db.connect(dsn) as conn:
        conn.execute(billing.SCHEMA)
        db.own_table(conn, "credit_schedules")
    return dsn, account_id


def _schedule_table_inits(monkeypatch):
    """Every time own_table is asked to own billing's table from here on
    -- the UPDATE in the traceback."""
    seen, real = [], db.own_table

    def own_table(conn, table):
        if table == "credit_schedules":
            seen.append(table)
        real(conn, table)

    monkeypatch.setattr(db, "own_table", own_table)
    return seen


def _two_reads(dsn, account_id):
    answers = []
    errors = _race(lambda: answers.append(billing.balance(account_id, dsn=dsn)))
    return answers, errors


def test_two_balance_reads_at_once_both_answer(made_elsewhere):
    """The failure itself: DeadlockDetected, every round, before the fix."""
    dsn, account_id = made_elsewhere
    for round_no in range(READ_ROUNDS):
        answers, errors = _two_reads(dsn, account_id)
        assert errors == [], f"round {round_no}: {errors!r}"
        assert len(answers) == 2 and answers[0] == answers[1]
        assert {"available", "outstanding", "lots", "schedules"} <= set(answers[0])


def test_two_first_reads_in_a_fresh_schema_both_answer(ledgered):
    """Nobody has made the table: whichever read gets there makes it and
    the other waits. (Two CREATE TABLE IF NOT EXISTS at once is not a
    deadlock, it is a UniqueViolation on pg_class -- the same two inits,
    one statement earlier.)"""
    dsn, account_id = ledgered
    for round_no in range(READ_ROUNDS):
        answers, errors = _two_reads(dsn, account_id)
        assert errors == [], f"round {round_no}: {errors!r}"
        assert len(answers) == 2 and answers[0] == answers[1]


def test_four_reads_and_a_hold_path_release_at_once(made_elsewhere):
    """A balance read beside charge.Charge.take's and the MCP quote's own
    call: release_due is the function all three share."""
    dsn, account_id = made_elsewhere
    calls = [lambda: billing.balance(account_id, dsn=dsn),
             lambda: billing.release_due(account_id, dsn=dsn)]
    for round_no in range(READ_ROUNDS):
        turn = iter(calls * 2)
        lock = threading.Lock()

        def one():
            with lock:
                fn = next(turn)
            fn()

        errors = _race(one, n=4)
        assert errors == [], f"round {round_no}: {errors!r}"


def test_a_balance_read_does_no_schema_work_after_the_start(ledgered, monkeypatch):
    """The web app makes the table at start, under db.run_init
    (app.main.init_tables). After that a read must be reads: no DDL and
    no backfill UPDATE, so there is nothing for two of them to deadlock
    on however they land."""
    dsn, account_id = ledgered
    billing.init(dsn)
    seen = _schedule_table_inits(monkeypatch)
    billing.balance(account_id, dsn=dsn)
    billing.release_due(account_id, dsn=dsn)
    assert billing.schedules(account_id, dsn=dsn) == []
    assert seen == []


def test_the_first_use_inits_once_and_only_once(ledgered, monkeypatch):
    """No start made the table here, so the first call does -- once, for
    every billing function, not once each and not once per call."""
    dsn, account_id = ledgered
    seen = _schedule_table_inits(monkeypatch)
    for _ in range(3):
        billing.balance(account_id, dsn=dsn)
    assert billing.cancel_schedules(account_id, dsn=dsn) == 0
    assert seen == ["credit_schedules"]


def test_first_use_still_makes_the_table_in_each_database(pg, pg_factory):
    """The guarantee the per-call init gave, kept: a database this process
    has not made the table in gets it on first use. Per database, so a
    second schema in the same process is not skipped because the first
    one is done."""
    for dsn in (pg, pg_factory()):
        with db.connect(dsn) as conn:
            assert not db.table_exists(conn, "credit_schedules")
        assert billing.release_due(None, dsn=dsn) == 0
        with db.connect(dsn) as conn:
            assert db.table_exists(conn, "credit_schedules")


def test_the_database_is_named_by_the_environment_too(pg, pg_factory, monkeypatch):
    """dsn=None is DATABASE_URL, read per call (the web app, the CLI):
    the same rule, keyed by the database it resolves to."""
    for dsn in (pg, pg_factory()):
        monkeypatch.setenv("DATABASE_URL", dsn)
        assert billing.release_due() == 0
        with db.connect(dsn) as conn:
            assert db.table_exists(conn, "credit_schedules")


def test_a_first_init_that_failed_is_run_again(pg, monkeypatch):
    """Only an init that finished counts. One that raised is not
    remembered as done, or every later read would query a table that was
    never made."""
    real, calls = billing.init, []

    def flaky(dsn=None):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("no database for a moment")
        real(dsn)

    monkeypatch.setattr(billing, "init", flaky)
    with pytest.raises(RuntimeError):
        billing.release_due(None, dsn=pg)
    assert billing.release_due(None, dsn=pg) == 0
    assert billing.release_due(None, dsn=pg) == 0
    assert len(calls) == 2
