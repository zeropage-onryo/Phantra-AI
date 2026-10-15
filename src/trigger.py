#!/usr/bin/env python3
"""
The scheduled trigger -- fires a shadow run on a schedule instead of a
click. Build-order step 5: autonomous *creation*, posting still gated.

    venv/bin/python -m src.trigger                # tonight's spark, rotated
    venv/bin/python -m src.trigger --spark "..."  # explicit direction

The spark rotates through prompts/sparks.txt by day of year, so
consecutive nights get different directions with nobody typing. (The
`--scout` / `--research` flags went with the research scout, 2026-10-14.)
The run itself goes through the full content graph and -- with render/publish
stubbed -- always ends by saying why it stopped. Nothing keeps a log
of runs any more: the hold queue went 2026-10-14 (Mike's call).

Exit 0 with the run's outcome printed, exit 1 on anything unexpected.
Since 2026-09-07 a crash is also CLASSIFIED (`classify_error`): the
printed reason and the exit code say whether the failure was about this
concept or about the world, so a caller looping over sparks can stop
instead of running fifteen more runs into the same dead socket. Exit 2
is the systemic one. (The nightly walk that was that caller,
src/nightly.py, was deleted 2026-10-07, Mike's call.)
"""
import argparse
import socket
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPARKS_PATH = PROJECT_ROOT / "prompts" / "sparks.txt"


def load_sparks(path: Path = SPARKS_PATH) -> list:
    """Non-empty, non-comment lines. Missing file -> empty list, and the
    caller falls back to a generic spark rather than dying."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def pick_spark(sparks: list, day: int) -> str:
    """Deterministic rotation: same night, same spark -- a re-run after a
    crash produces the same direction, not a surprise second slate."""
    if not sparks:
        return "tonight's shadow slate"
    return sparks[day % len(sparks)]


# --------------------------------------------------------------------------
# what kind of failure this is
# --------------------------------------------------------------------------

SYSTEMIC = "systemic"
CONTENT = "content"

# The world is broken in a way the next run will hit too: the database is
# unreachable, the name does not resolve, the card is empty, the key is
# refused. Fifteen more attempts produce fifteen more copies of this.
_DNS_MARKERS = (
    "nodename nor servname",
    "name or service not known",
    "temporary failure in name resolution",
    "could not translate host name",
    "getaddrinfo failed",
    "connection refused",
    "connection reset by peer",
    "server closed the connection",
    "could not connect to server",
    "network is unreachable",
    "no route to host",
    "connection timed out",
)
_AUTH_MARKERS = (
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
    "unauthenticated",
    "permission_denied",
    "401 unauthorized",
    "403 forbidden",
    "password authentication failed",
)
# A failure about THIS concept, or about one unlucky transaction. The next
# spark is a different concept and deserves its own attempt.
_CONTENT_MARKERS = (
    "deadlock detected",
    "deadlock",
    "could not serialize access",
)


def classify_error(error) -> str:
    """SYSTEMIC (the world is broken) or CONTENT (this concept is).

    Order matters. A Postgres deadlock arrives as an OperationalError,
    the same class a dead socket does, so the content markers are read
    FIRST -- otherwise one unlucky transaction would look like a broken
    database. Everything unrecognised is CONTENT: erring that way costs
    one wasted run, and erring the other way stops a loop on an
    exception nobody has seen yet.
    """
    from . import gemini_utils  # pulls in google-genai; --help needn't

    text = str(error).lower()
    if any(marker in text for marker in _CONTENT_MARKERS):
        return CONTENT
    if gemini_utils.is_depleted(error):
        return SYSTEMIC
    if isinstance(error, (socket.gaierror, ConnectionError)):
        return SYSTEMIC
    if any(marker in text for marker in _DNS_MARKERS):
        return SYSTEMIC
    if any(marker in text for marker in _AUTH_MARKERS):
        return SYSTEMIC
    try:
        import psycopg
        if isinstance(error, psycopg.OperationalError):
            return SYSTEMIC
    except Exception:      # psycopg missing is not this function's problem
        pass
    return CONTENT


def run_once(spark: str, *, brain=None) -> dict:
    """One graph run, as a result dict instead of an exit code.

    The shape the CLI wraps: `ok`, the `held` reason a shadow run
    always has, and on a crash the `kind` (`SYSTEMIC` / `CONTENT`) that
    says whether another run is worth attempting.
    """
    # Imported here, not at module top: orchestrator pulls in the whole
    # generation stack, and `--help` on a cron box shouldn't need it.
    from . import orchestrator

    try:
        result = orchestrator.run(spark, brain=brain)
    except Exception as e:
        kind = classify_error(e)
        return {"ok": False, "kind": kind, "error": str(e), "spark": spark}

    return {
        "ok": True,
        "kind": None,
        "spark": result.get("spark") or spark,
        "held": result.get("held_reason"),
        "result": result,
    }


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Fire one shadow run through the content graph."
    )
    parser.add_argument("--spark", default=None,
                        help="explicit direction; default rotates prompts/sparks.txt")
    # None, not "fast": an unnamed tier is what lets PHANTRA_BRAIN
    # decide (orchestrator.brain_default). A walk is ten runs, so naming `reasoning`
    # here is a bill somebody chose.
    parser.add_argument("--brain", default=None,
                        help="model tier for the writer: fast (default) or reasoning")
    args = parser.parse_args(argv)

    spark = args.spark or pick_spark(load_sparks(), date.today().timetuple().tm_yday)

    outcome = run_once(spark, brain=args.brain)
    if not outcome["ok"]:
        print(f"trigger: run crashed ({outcome['kind']}): {outcome['error']}",
              file=sys.stderr)
        # 2 is the systemic one: a caller looping over sparks can tell
        # "this concept broke" from "the world is broken" without
        # parsing stderr.
        return 2 if outcome["kind"] == SYSTEMIC else 1

    result = outcome["result"]
    used = outcome["spark"]
    print(f"trigger: spark={used!r} "
          f"attempts={result.get('attempts')} "
          f"concept_id={result.get('concept_id')} "
          f"held={result.get('held_reason')!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
