"""
Tests for src/autonomy.py -- the kill switch, the prompt gate's log and
the standing corrections. Against a throwaway Postgres schema.
"""
import pytest

from src import autonomy, db


@pytest.fixture
def tmp_db(pg):
    path = pg
    autonomy.init(path)
    return path


def _grade(dsn, run_id, verdict):
    """A human verdict on a run's scores, as the retired hold grading
    wrote it (2026-10-14: nothing writes one any more; the rows already
    graded are what prompt_gate_agreement still reads)."""
    with db.connect(dsn) as conn:
        conn.execute("UPDATE prompt_scores SET human_verdict = %s WHERE run_id = %s",
                     (verdict, run_id))


# ---------- no channels (2026-10-13), no hold queue (2026-10-14) ----------

def test_there_is_no_channels_table_and_no_hold_queue(tmp_db):
    """The two rows named for the two brands, their autonomy levels, rate
    caps and targets are gone, and so is the queue a run used to park in:
    nothing can promote a run to post, and nothing keeps a run to grade."""
    with db.connect(tmp_db) as conn:
        tables = {r["table_name"] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema()").fetchall()}
    assert not {"channels", "hold_queue"} & tables
    assert autonomy.AUTONOMY == "shadow"
    for gone in ("get_channel", "set_autonomy", "list_channels", "set_targets",
                 "channel_targets", "posts_today", "to_hold", "list_hold", "get_hold",
                 "hold_for_concept", "gates_for_concepts", "resolve_hold",
                 "record_hold_posts", "evaluator_agreement", "set_prompt_verdicts",
                 "HOLD_CHANNEL", "DEFAULT_POST_TARGETS"):
        assert not hasattr(autonomy, gone)


# ---------- kill switch ----------

def test_kill_switch_round_trip(tmp_db, monkeypatch):
    monkeypatch.delenv("PHANTRA_KILL", raising=False)
    assert autonomy.killed(dsn=tmp_db) is False
    autonomy.kill("bad night", dsn=tmp_db)
    assert autonomy.killed(dsn=tmp_db) is True
    autonomy.unkill(dsn=tmp_db)
    assert autonomy.killed(dsn=tmp_db) is False


def test_kill_switch_env_var_needs_no_db_write(tmp_db, monkeypatch):
    monkeypatch.setenv("PHANTRA_KILL", "1")
    assert autonomy.killed(dsn=tmp_db) is True


# ---------- the prompt gate's numbers ----------

def test_prompt_scores_round_trip(tmp_db):
    autonomy.log_prompt_scores("run1", [
        {"prompt": "good one", "score": 9, "pass": True, "reason": "", "dims": {"camera": 2}},
        {"prompt": "weak one", "score": 3, "pass": False, "reason": "no light", "dims": {}},
    ], dsn=tmp_db)

    assert autonomy.first_try_pass_rate(dsn=tmp_db) == {
        "total": 2, "passed": 1, "rate": 0.5}


def test_prompt_gate_agreement_separates_the_two_error_costs(tmp_db):
    # gate passed, you rejected -> the expensive error (credit burned)
    autonomy.log_prompt_scores("r1", [
        {"prompt": "a", "score": 9, "pass": True, "reason": "", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r1", "reject")
    # gate held, you'd post -> the cheap error (manual approval)
    autonomy.log_prompt_scores("r2", [
        {"prompt": "b", "score": 3, "pass": False, "reason": "x", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r2", "post")
    # two agreements
    autonomy.log_prompt_scores("r3", [
        {"prompt": "c", "score": 9, "pass": True, "reason": "", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r3", "post")
    autonomy.log_prompt_scores("r4", [
        {"prompt": "d", "score": 2, "pass": False, "reason": "y", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r4", "reject")

    result = autonomy.prompt_gate_agreement(dsn=tmp_db)
    assert result["graded"] == 4
    assert result["agreement"] == 0.5
    assert result["passed_but_rejected"] == 1
    assert result["held_but_posted"] == 1


def test_a_judge_that_never_answered_is_not_counted_against_the_gate(tmp_db):
    """A Gemini 503 is not evidence about the judge's taste.

    The fail-closed path returns score 0 with empty dims, which is the
    same shape as a real negative verdict, and it used to be written to
    prompt_scores as passed = 0 -- so every API wobble moved the one
    number that says whether the gate can be trusted, using rows where
    the gate had no opinion at all. Genuine passed = 0 rows still count,
    deliberately: see orchestrator._gate_advisory on why the scores
    themselves are never massaged.
    """
    # a real verdict you agreed with
    autonomy.log_prompt_scores("r1", [
        {"prompt": "a", "score": 9, "pass": True, "reason": "", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r1", "post")
    # a real verdict you disagreed with -- still counts
    autonomy.log_prompt_scores("r2", [
        {"prompt": "b", "score": 2, "pass": False, "reason": "thin", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r2", "post")
    # the judge fell over; the run was graded anyway
    autonomy.log_prompt_scores("r3", [
        {"prompt": "c", "score": 0, "pass": False, "unreadable": True,
         "reason": "judge unreadable (503) — failed closed", "dims": {}}], dsn=tmp_db)
    _grade(tmp_db, "r3", "post")

    result = autonomy.prompt_gate_agreement(dsn=tmp_db)
    assert result["graded"] == 2, "the outage row is not a graded verdict"
    assert result["agreement"] == 0.5, "one agreement, one real disagreement"
    assert result["held_but_posted"] == 1, "and only the real one is a miss"
    # the descriptive rate leaves it out too -- it is not a gate decision
    assert autonomy.first_try_pass_rate(dsn=tmp_db)["total"] == 2


# ---------- corrections ----------

def test_corrections_round_trip(tmp_db):
    cid = autonomy.add_correction("less neon, more silence", dsn=tmp_db)
    [pending] = autonomy.pending_corrections(dsn=tmp_db)
    assert pending["id"] == cid
    autonomy.consume_correction(cid, dsn=tmp_db)
    assert autonomy.pending_corrections(dsn=tmp_db) == []


def test_the_readers_answer_nothing_on_a_database_with_no_graph_history(pg):
    fresh = pg                             # db.init_db only: no autonomy.init yet
    assert autonomy.prompt_scores_for_run("r", dsn=fresh) == []


def test_prompt_scores_for_run_keeps_the_order_the_gate_scored_in(tmp_db):
    autonomy.log_prompt_scores("r", [
        {"prompt": "a", "score": 3, "pass": False, "reason": "thin",
         "dims": {"subject": 1}},
        {"prompt": "b", "score": 8, "pass": True, "reason": "", "dims": {}},
    ], dsn=tmp_db)
    rows = autonomy.prompt_scores_for_run("r", dsn=tmp_db)
    assert [(r["score"], r["passed"]) for r in rows] == [(3, False), (8, True)]
    assert rows[0]["dims"] == {"subject": 1}
    assert autonomy.prompt_scores_for_run(None, dsn=tmp_db) == []
    assert autonomy.prompt_scores_for_run("nope", dsn=tmp_db) == []


# ---------- post targets: validated, because a typo posts nowhere ----------

def test_an_unroutable_target_is_refused():
    """autopilot._post_dispatch routes on exactly these names."""
    assert autonomy.validate_targets("instagram, YouTube,tiktok,instagram") == [
        "instagram", "youtube", "tiktok"]
    with pytest.raises(ValueError, match="instgram"):
        autonomy.validate_targets("instgram")
