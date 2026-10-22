"""
Shared test setup.

The guard below exists because this has now bitten four times: a test
monkeypatches one generator function, the route is changed to call a
different one, the patch silently misses, and the test makes a real
billed API call while still passing. Nothing failed -- the only signal
was the suite getting slower.

So: no test may reach the network. Anything that wants to talk to
Gemini or YouTube has to patch the function it actually calls, and
gets a loud, immediate failure naming the offender if it doesn't.

`output_roots_in_tmp` below is the same idea for the OTHER thing a test
can do to a real machine: write to it. See its docstring.
"""
import importlib
import os
import socket
from pathlib import Path

import pytest

# The suite runs in the dev posture: the dev-console pages only register
# when DEV_TOOLS=1 (app/main.py), and the page tests hit them. CI has no
# .env, so pin it here -- conftest imports before any test module pulls
# in app.main. The public posture has its own tests (test_dev_tools.py),
# which reload app.main under DEV_TOOLS=0.
os.environ["DEV_TOOLS"] = "1"
# Open sign-up (a first sign-in gets its own workspace) is the shipped
# posture since 2026-09-24, but most of the suite signs fresh users in and
# asserts the invite-only gate's 403. Pinned off here, like DEV_TOOLS
# above; tests/test_open_signup.py turns it on per test.
os.environ["PHANTRA_OPEN_SIGNUP"] = "0"

# The reference rule (2026-09-08): in production a spark with no pictures
# behind it does not get written from at all -- `orchestrator.planner`
# holds the run. Pinned OFF here, deliberately, and for one reason: every
# graph test in this suite was written to exercise something else (the
# retry edge, the prompt gate, the keyframe, tenancy) and hands the graph
# a bare spark, so leaving it on would turn eighty-odd unrelated tests
# into assertions about reference images. The rule has its own tests,
# which turn it ON explicitly -- tests/test_reference_rule.py -- the same
# arrangement PHANTRA_GATES uses, where the default is what the suite
# runs under and the other mode is pinned per test.
os.environ["PHANTRA_REQUIRE_REFS"] = "0"

# The checkpointer is OFF for the suite, the same way DEV_TOOLS and the
# reference rule above are pinned: a posture, chosen here, so the suite
# runs one way and not two.
#
# It cannot be on. The saver opens its OWN connection on the configured
# DSN and caches it for the process, while `pg` gives every test a
# private schema and drops it afterwards -- so the first test to run the
# graph creates the checkpoint tables inside a throwaway schema, and
# every test after it queries a schema that no longer exists
# ("relation \"checkpoints\" does not exist"). Nothing about that is a
# bug in the checkpointer; it is two different ideas of which database
# this is.
#
# The logic itself is covered without a database, in
# tests/test_orchestrator.py -- fails-soft, the off switch, and what
# resume does with the account on the checkpoint.
os.environ["PHANTRA_CHECKPOINT"] = "0"

# The MCP Apps probe (src/mcp_apps_probe.py) is OFF for the suite. It is a
# flag a person sets in their own `.env` to test their Claude client, and
# app.main's load_dotenv would carry it in here, where it adds three tools
# to the studio surface every tool-set test counts.
# tests/test_mcp_apps_probe.py turns it on per test.
os.environ["PHANTRA_MCP_APPS_PROBE"] = "0"

# The Starlette session cookie is NOT Secure in the suite: the test client
# talks to http://testserver and would never send a Secure cookie back,
# and .env's https SITE_URL (load_dotenv at app.main import) would
# otherwise turn it on (app/security_headers.session_https_only).
os.environ["PHANTRA_SESSION_HTTPS_ONLY"] = "0"

# THE SUITE'S DATABASE IS THE THROWAWAY, AND NOTHING ELSE (2026-09-28).
# app.main calls load_dotenv() at import, and load_dotenv searches PARENT
# directories -- so a worktree under .claude/worktrees/ picks up the main
# checkout's .env, whose DATABASE_URL is the LIVE Supabase database. Any
# code path under test that called db.connect(None) then read production:
# test_element_sheet drew a still for account 1 with no db_path and the
# credit charge read the live ledger (no write, only because account 1 is
# credit_exempt). CI never saw it because CI has no .env.
#
# Set here, BEFORE app.main is imported, because load_dotenv never
# overrides a variable that is already set. RAG_DATABASE_URL too: it
# outranks DATABASE_URL in rag.connect, and the same .env sets it. A test
# that points either at its own pg schema still does so with setenv.
# `no_live_database` below is the backstop for anything that slips past.
TEST_DSN = os.environ.get("TEST_DATABASE_URL") or "postgresql://phantra:phantra@localhost:5432/phantra"
os.environ["DATABASE_URL"] = TEST_DSN
os.environ["RAG_DATABASE_URL"] = TEST_DSN
os.environ.pop("SUPABASE_RAG_DATABASE_URL", None)


class LiveDatabaseInTest(RuntimeError):
    pass


def _install_no_live_database() -> None:
    """Refuse, at connect time, any Postgres that is not on this machine.

    no_network below cannot do this: libpq opens its socket below Python's
    socket module. So the wall goes on psycopg itself -- both doors, since
    `psycopg.connect` is a bound method captured at import and the pool
    calls `Connection.connect` on the class. Local hosts are allowed
    (throwaway schemas, and the tests that point at a dead 127.0.0.1:1 on
    purpose), plus whatever host TEST_DSN names, so a CI service container
    reached by name still works. Anything else -- the Supabase pooler --
    fails the test loudly instead of reading or writing production.

    Installed once for the process, not per test: it is a wall, not a
    fixture a test could forget, and a test that wraps psycopg.connect
    (test_queue_pending_scaling) wraps the guarded one."""
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    allowed = {"", "localhost", "127.0.0.1", "::1"}
    allowed |= {h for h in (conninfo_to_dict(TEST_DSN).get("host") or "").split(",")}

    def check(conninfo, kwargs):
        params = conninfo_to_dict(conninfo or "", **{
            k: kwargs[k] for k in ("host", "hostaddr") if kwargs.get(k)})
        hosts = str(params.get("hostaddr") or params.get("host")
                    or os.environ.get("PGHOST") or "")
        for host in hosts.split(","):
            if host.strip() not in allowed and not host.startswith("/"):
                raise LiveDatabaseInTest(
                    f"a test tried to connect to Postgres at {host!r}, which is "
                    f"not the throwaway ({TEST_DSN!r}). Something resolved a DSN "
                    "from the environment instead of the test's own pg schema.")

    sync_connect = psycopg.Connection.connect.__func__
    async_connect = psycopg.AsyncConnection.connect.__func__

    def guarded(cls, conninfo="", **kwargs):
        check(conninfo, kwargs)
        return sync_connect(cls, conninfo, **kwargs)

    async def guarded_async(cls, conninfo="", **kwargs):
        check(conninfo, kwargs)
        return await async_connect(cls, conninfo, **kwargs)

    psycopg.Connection.connect = classmethod(guarded)
    psycopg.AsyncConnection.connect = classmethod(guarded_async)
    psycopg.connect = psycopg.Connection.connect


_install_no_live_database()


from app.main import app as _APP_AT_IMPORT  # noqa: E402  (see account_scope)
from src.imagesearch import LANE_ENV as IMAGE_LANE_ENV  # noqa: E402  (see POSTURE_ENV)

# Modules that are ABOUT the reference rule turn it back on for
# themselves. Keeping the list here rather than a fixture in each file is
# deliberate: the rule grew from two directions on the same day and the
# thing that would actually go wrong is a third enforcement point landing
# with its tests written under the suite default, passing, and testing
# nothing. A module named for the rule is opted in by being named.
REFS_RULE_MODULES = {"test_reference_gate", "test_reference_rule"}


@pytest.fixture(autouse=True)
def _refs_rule(request, monkeypatch):
    """PHANTRA_REQUIRE_REFS on for the rule's own tests, off elsewhere.

    A test whose NAME says it is about an ungrounded scene opts in too --
    those live in files that are mostly about something else (the queue,
    the board), and splitting them out would separate them from the
    fixtures they share."""
    module = request.module.__name__.rsplit(".", 1)[-1]
    if module in REFS_RULE_MODULES or "ungrounded" in request.node.name:
        monkeypatch.setenv("PHANTRA_REQUIRE_REFS", "1")


class NetworkUseInTest(RuntimeError):
    pass


# THE SUITE RUNS AS CI RUNS IT (2026-09-08). Everything below is a
# DEPLOYMENT POSTURE that lives in .env on Mike's machine and nowhere in
# CI, so a suite that inherits it is two different suites -- eleven
# orchestrator tests fail on his Mac and pass on GitHub, and the one that
# actually mattered (a reference photo's canonical URL) silently swapped
# what a dozen assertions were checking without either run saying which
# it got. A test that is ABOUT one of these sets it itself; monkeypatch
# unwinds these deletes in order, so a setenv inside a test still wins.
#
# A fixture and not a module-level pop, because app.main calls
# load_dotenv() at import and would put every one of them straight back.
R2_ENV = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
          "R2_BUCKET", "R2_PUBLIC_BASE_URL")

POSTURE_ENV = R2_ENV + (
    "PHANTRA_KEYFRAME",         # the night's stills, off since 2026-09-08
    "PHANTRA_UNCANNY",          # the on-brand judge, off on his machine
    "PHANTRA_SCENE_SECONDS",    # the scene length the writers fill (timeline.py)
    "LANGSMITH_TRACING",         # tracing is a live POST; the guard fails it
    "QUOTE_SIGNING_SECRET",      # quotes sign only where a test says so
    "STRIPE_SECRET_KEY",         # billing is configured only where a test says so
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_STARTER", "STRIPE_PRICE_CREATOR", "STRIPE_PRICE_STUDIO", "STRIPE_PRICE_TOPUP",
    "STRIPE_PRICE_STARTER_YEAR", "STRIPE_PRICE_CREATOR_YEAR", "STRIPE_PRICE_STUDIO_YEAR",
    "BILLING_RETURN_URL",
    # the Instagram credentials: the nightly preflight checks them live, so
    # a suite that inherited .env's would call Meta from a test
    "IG_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_GRAPH_TOKEN", "FB_GRAPH_TOKEN",
    "IG_USER_ID", "INSTAGRAM_USER_ID", "IG_BUSINESS_ID", "IG_RESEARCH_APP_ID",
) + IMAGE_LANE_ENV  # every image-search lane's key (src/imagesearch.py owns the list)


@pytest.fixture(autouse=True)
def r2_off(monkeypatch):
    """Shipped defaults, not this machine's .env."""
    for name in POSTURE_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    def blocked(*args, **kwargs):
        raise NetworkUseInTest(
            f"{request.node.nodeid} tried to open a network connection. "
            "A real API call in a test usually means a monkeypatch is "
            "patching a function the code under test no longer calls."
        )

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture(autouse=True)
def stdin_is_open(monkeypatch):
    """The stdio MCP server's main() leaves at once when its stdin has
    already been hung up (src/mcp_server.py, THE DROPPED COPY). Whether
    the TEST RUNNER's fd 0 is a hung-up pipe is a fact about how the
    suite was launched -- a CI step, a background job, `-s` -- and not
    about the code, so no test asks the real one: main() serves unless a
    test says otherwise. tests/test_mcp_dropped_copy.py checks the real
    thing on descriptors it makes and in real processes."""
    from src import mcp_server

    monkeypatch.setattr(mcp_server, "stdin_dropped", lambda: False)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Every module-level path that names somewhere this project WRITES on the
# real machine: (module, attribute, where it lives under the project root).
# The last field is what makes the redirect faithful -- RENDER_DIR has to
# stay *inside* RENDERS_ROOT or `_local_render_bytes`'s containment check
# refuses the very file the test just wrote.
#
# A test that drives a render patches the HTTP layer, not the output path,
# and the fake downloader writes 2048 zero bytes because that is what
# passes the size QC. Nothing about that is wrong -- but with RENDER_DIR
# still pointing at data/renders/higgsfield/, every one of those stubs
# landed in the owner's real render directory, named wf-<stamp>.mp4 like
# any real clip and indistinguishable from one in a listing or in the
# Queue. Twenty had accumulated there before anyone noticed.
OUTPUT_ROOTS = (
    ("src.fal", "RENDERS_ROOT", "data/renders"),
    ("src.fal", "RENDER_DIR", "data/renders/fal"),
    ("src.storage_quota", "RENDERS_ROOT", "data/renders"),
    ("src.nano_banana", "RENDER_DIR", "data/renders/nano"),
    ("src.orchestrator", "GENERATED_ROOT", "footage/generated"),
    ("src.autopilot", "GENERATED_DIR", "footage/generated"),
    ("src.autopilot", "KILL_SWITCH_PATH", "data/autopilot.off"),
    # the refreshed Instagram token (BACKLOG #4): token_store_path() reads
    # this constant per call unless IG_TOKEN_STORE says otherwise
    ("src.instagram", "TOKEN_STORE", "data/ig_token.json"),
    ("src.refbin", "REFS_DIR", "data/refs"),
    # the free looks' generated assets and their outputs (src/looks.py, 2026-10-22)
    ("src.looks", "ASSETS_DIR", "data/looks"),
    ("src.looks", "RENDER_DIR", "data/renders/looks"),
    # a brand kit's logos, fonts and references (src/brand_kits.py, 2026-10-20)
    ("src.brand_kits", "FILES_DIR", "data/brandkits"),
    # A personal model login is a folder of session files. Registered for
    # the same reason as the rest: the first test that connects one would
    # otherwise write a real credential store into data/.
    ("src.personal_models", "SESSIONS_ROOT", "data/model_sessions"),
    ("src.promote_winners", "QUEUE_PATH", "data/promotion_queue.json"),
    ("src.db", "DB_PATH", "data/pipeline.db"),
    ("app.main", "RENDERS_DIR", "data/renders"),
    ("app.main", "UPLOAD_REFS_DIR", "data/refs"),
    ("app.main", "THUMB_DIR", "data/thumbs"),
    ("app.api", "UPLOAD_REFS_DIR", "data/refs"),
    ("ops.render_queue", "RENDERS_ROOT", "data/renders"),
    ("ops.render_queue", "MANUAL_RENDER_DIR", "data/renders/manual"),
    ("ops.billing_walkthrough", "SEEN_FILE", "data/billing_walk_relayed.json"),
    # the connector walk client's OAuth session (ops/connector_walk.py,
    # 2026-10-12): a test that signed in through a fake door must not leave
    # a token file in the real data/
    ("ops.connector_walk", "SESSION_DIR", "data/connector_walk"),
    # the old-render tokenizer (ops/tokenize_old_renders.py, 2026-10-16): the
    # local renders it renames and the backup it writes before touching a row
    ("ops.tokenize_old_renders", "LOCAL_RENDERS", "data/renders"),
    ("ops.tokenize_old_renders", "BACKUPS", "data/backups"),
    # the cut (src/cut/, 2026-09-26): where a handle's local file is looked
    # for, where the MP4 lands, and where uploaded music/VO is kept
    ("src.cut.sources", "RENDERS_DIR", "data/renders"),
    ("src.cut.render", "CUT_DIR", "data/renders/cut"),
    ("app.cut_routes", "MEDIA_DIR", "data/renders/cut/media"),
    # the editor's browser previews (src/cut/preview.py, 2026-09-28)
    ("src.cut.preview", "PREVIEW_DIR", "data/renders/cut/preview"),
)


@pytest.fixture(autouse=True)
def output_roots_in_tmp(tmp_path, monkeypatch):
    """No test writes into the real data/ or footage/ tree.

    Autouse on purpose, and the reason is the whole point: the tests that
    littered data/renders/higgsfield/ with 2048-byte stubs were not tests
    that got the redirect wrong, they were tests that never thought about
    output paths at all. An opt-in fixture is exactly the thing they would
    not have opted into. So the default is tmp_path and a module has to be
    *registered* (OUTPUT_ROOTS above) rather than remembered.

    A test that already points one of these at its own tmp dir keeps
    working: it patches the same attribute afterwards, so its value wins,
    and monkeypatch unwinds both in order.

    tests/test_output_roots.py is the other half -- it fails if a new
    output root appears that nobody added here.
    """
    root = tmp_path / "project"
    for name in ("data", "footage"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for module_name, attr, relative in OUTPUT_ROOTS:
        module = importlib.import_module(module_name)
        monkeypatch.setattr(module, attr, root / relative, raising=True)
    return root


@pytest.fixture(autouse=True)
def no_spend_context():
    """The LLM meter's attribution is a contextvar (src/spend.py). A test
    that drives the orchestrator or binds one must not leave it set for
    the next test in the same worker."""
    from src import spend
    token = spend._context.set(None)
    yield
    try:
        spend._context.reset(token)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def account_scope():
    """Give every route an account to act as.

    Routes take `account_id: int = Depends(auth.current_account_id)`, and
    FastAPI captures that callable when the route is registered -- so
    monkeypatching the module attribute the way these tests patch
    `auth.current_user` does nothing. `dependency_overrides` is the
    supported seam.

    None is the unowned pool: rows that carry no account_id, which is
    exactly what a fixture database with no seeded accounts holds. So
    every test that was never about ownership keeps asserting what it
    always did. A test that IS about isolation seeds real accounts and
    sets its own override -- see tests/test_tenancy.py.
    """
    import app.main as app_main
    from app import auth

    # Both app objects, and they really can be two. test_dev_tools.py does
    # `importlib.reload(app_main)` to exercise the DEV_TOOLS=0 posture,
    # which builds a NEW FastAPI instance and rebinds app.main.app -- while
    # every other test module still holds the original from its
    # module-level `from app.main import app`. Override only the current
    # one and those modules' requests resolve the real dependency, which
    # then trips over a stubbed account dict that has no "id". That failure
    # only appears when the two files land in the same xdist worker, which
    # is why it looked like flakiness.
    targets = {id(_APP_AT_IMPORT): _APP_AT_IMPORT, id(app_main.app): app_main.app}
    for target in targets.values():
        target.dependency_overrides[auth.current_account_id] = lambda: None
        target.dependency_overrides[auth.dev_account_id] = lambda: None
    yield
    for target in targets.values():
        target.dependency_overrides.pop(auth.current_account_id, None)
        target.dependency_overrides.pop(auth.dev_account_id, None)


class CreateGateInTest(RuntimeError):
    pass


def _shared_schema(dsn: str) -> bool:
    """True when `dsn` is the throwaway itself rather than a private schema
    on it: TEST_DSN with no search_path of a test's own. That is the one
    place every test, and every earlier run on the machine, writes to."""
    from psycopg.conninfo import conninfo_to_dict

    try:
        return conninfo_to_dict(dsn) == conninfo_to_dict(TEST_DSN)
    except Exception:
        return False


@pytest.fixture(autouse=True)
def create_gate_reads_its_own_schema(monkeypatch, request):
    """The Create gate is never answered from the shared schema.

    `charge.create_refusal_code` fails OPEN on a read error, by design: a
    flaky read must not take the composer down. The routes call it with no
    dsn (`app/api._create_gate`, `app/cut_routes._create_gate`), so in a
    test that never pointed DATABASE_URL at its own `pg` schema the read
    lands in the throwaway's public schema -- and what that holds is a fact
    about the machine, not the code. A fresh CI Postgres has no
    `credit_entries`: the read errors, the gate opens, the route runs. A dev
    machine's public schema has the ledger tables (anything run there with
    no dsn of its own makes them: app startup, a charge's `ledger.init`), so
    a made-up account id reads as "no plan, no balance" and the route
    answers 402. tests/test_result_refs.py stubbed `charge.create_refusal`,
    the MCP tools' wrapper, after the routes had moved to
    `create_refusal_code`: 14 passed on a fresh database and 3 failed on a
    laptop's, from the same commit (2026-10-11).

    no_network's shape, for the same class of bug -- a patch that silently
    misses. A test whose route asks the gate about a real account id either
    stubs the function its code path calls, or seeds that account in `pg`
    and points the route at it. Anything else fails here, by name, the same
    way on both machines.

    Deliberately NOT "hold the gate open unless a test opts in": that makes
    the real function unreachable by default, so every test that walks a
    route with a seeded account in its own schema (the gate's own, the
    billing ones, the charges) would stop running it unless somebody
    remembered a marker -- the REFS_RULE_MODULES worry above. Here the real
    function runs wherever its answer is the test's own doing: an explicit
    dsn, DATABASE_URL set to a `pg` schema, or a dead address a test points
    at on purpose. `account_id` None is the unowned pool and never read.

    `charge.create_refusal` calls this by name, so the MCP path
    (`mcp_server._create_gate`) is covered by the same wrapper.
    """
    from src import charge, db

    real = charge.create_refusal_code

    def guarded(account_id, *, dsn=None):
        if account_id is not None and _shared_schema(db.resolve_dsn(dsn)):
            raise CreateGateInTest(
                f"{request.node.nodeid} asked the Create gate about account "
                f"{account_id!r} with no database of its own, so the answer "
                "would come from the throwaway's public schema: allowed on a "
                "fresh CI Postgres, 402 on a machine that has run the suite "
                "before. Stub the function the code under test calls "
                "(charge.create_refusal_code for app/api and app/cut_routes; "
                "charge.create_refusal for src/mcp_server), or seed the "
                "account in the `pg` schema and "
                "monkeypatch.setenv('DATABASE_URL', pg)."
            )
        return real(account_id, dsn=dsn)

    monkeypatch.setattr(charge, "create_refusal_code", guarded)


# ---------------------------------------------------------------------------
# the throwaway Postgres (docs/tasks/task-postgres-migration.md)
# ---------------------------------------------------------------------------

# Where the port's tests run: TEST_DSN, defined at the top of this file.
# Never read off DATABASE_URL: that is the live database in any real .env,
# and this fixture creates and drops schemas. The default is the
# docker-compose box, which is also the throwaway on Mike's machine (a
# role+database of that name on Postgres.app, 2026-09-03).


@pytest.fixture
def pg():
    """A connection URL onto a fresh, private schema, torn down after.

    Isolation is the schema, carried in the URL itself (`options=-c
    search_path=...`), so the code under test needs no notion of "which
    schema" -- CREATE TABLE IF NOT EXISTS, to_regclass() and
    information_schema all resolve on search_path -- and tests can run in
    parallel against one database. Every id sequence starts at 1 in a
    new schema, which is what the `run_id == 1` assertions rely on.
    """
    import uuid

    import psycopg
    from psycopg.conninfo import make_conninfo

    from src import db

    schema = f"t_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(TEST_DSN, autocommit=True)
    except psycopg.OperationalError as e:  # pragma: no cover - environment
        pytest.fail(
            f"no throwaway Postgres at {TEST_DSN!r} ({e}). Start it "
            "(`docker compose up -d`) or point TEST_DATABASE_URL at one."
        )
    admin.execute(f"CREATE SCHEMA {schema}")
    dsn = make_conninfo(TEST_DSN, options=f"-c search_path={schema}")
    try:
        db.init_db(dsn)
        yield dsn
    finally:
        admin.execute(f"DROP SCHEMA {schema} CASCADE")
        admin.close()


@pytest.fixture
def pg_factory():
    """More throwaway schemas on demand, for a test that needs a SECOND
    database beside `pg` -- an empty one to prove a read degrades, a
    fresh one to prove a seed. Each call is a new schema with NOTHING in
    it (not even db.init_db), torn down with the test."""
    import uuid

    import psycopg
    from psycopg.conninfo import make_conninfo

    admin = psycopg.connect(TEST_DSN, autocommit=True)
    made: list[str] = []

    def make() -> str:
        schema = f"t_{uuid.uuid4().hex[:12]}"
        admin.execute(f"CREATE SCHEMA {schema}")
        made.append(schema)
        return make_conninfo(TEST_DSN, options=f"-c search_path={schema}")

    try:
        yield make
    finally:
        for schema in made:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")
        admin.close()


def seed_two(email, dsn):
    """accounts.seed makes ONE account (2026-09-28). Tests about a person
    who belongs to TWO -- the
    tenancy fence, per-account ledgers and caps -- make the second one here
    explicitly, rather than relying on the setup command to."""
    from src import accounts

    seeded = accounts.seed(email, dsn=dsn)
    second = accounts.upsert_account("second-studio", "Second Studio", "#d64550", dsn=dsn)
    accounts.add_member(second, seeded["user_id"], dsn=dsn)
    return {**seeded, "accounts": [*seeded["accounts"], second]}

