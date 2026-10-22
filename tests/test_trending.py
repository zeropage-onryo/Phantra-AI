"""Trending this week (src/trending.py; GET /api/trending), the Create
page's row of what an account used most over the last seven days.

Scoped to the caller's own account: another account's runs and scenes
never count, an older week's never count, and nothing here calls a
model or a provider. The answer carries no price.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import (
    accounts,
    db,
    effects,
    generative,
    outcomes,
    preprod,
    render_assets,
    trending,
)
from src.shot import Shot

WHO = {}


@pytest.fixture
def seeded(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    preprod.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    outcomes.init(pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": False, "chunks": 0, "error": "stubbed"})
    monkeypatch.setattr(render_assets, "drop_chunk", lambda *a, **k: None)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "t-user"})
    WHO["mine"] = accounts.upsert_account("t-mine", "Mine", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("t-theirs", "Theirs", "#fff", dsn=pg)
    return pg


def effect_run(pg, who, effect, n, *, kind="video"):
    """One effect attempt the way effects.run logs it: a generations row
    whose params name the effect, and its output on the wall."""
    shot = generative.add_shot(Shot(subject=f"{effect} {n}", action="as prompted"),
                               notes="test", dsn=pg, account_id=WHO[who])
    gen = generative.record_generation(
        shot, effects.LOG_TOOL, f"{effect} run {n}",
        params={"provider": "fal", "model": effect, "effect": effect, "options": {}},
        dsn=pg, account_id=WHO[who])
    asset = render_assets.record(
        generation_id=gen, tool=effects.LOG_TOOL, model=effect, media_kind=kind,
        prompt=f"{effect} run {n}", media_url=f"/renders/fal/fx-{effect}-{n}.mp4",
        dsn=pg, account_id=WHO[who])["id"]
    return gen, asset


def scene(pg, who, spark, title="Scene"):
    return preprod.save_concept({"title": title, "shots": [{"prompt": spark}]},
                                spark=spark, dsn=pg, account_id=WHO[who])


def age(pg, table, row_id, days, column="created_at"):
    stamp = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with db.connect(pg) as conn:
        conn.execute(f"UPDATE {table} SET {column} = %s WHERE id = %s", (stamp, row_id))  # noqa: S608


def test_the_week_counts_only_this_accounts_runs_scenes_and_events(seeded):
    pg = seeded
    _, kept_asset = effect_run(pg, "mine", "kling-effect", 1)
    effect_run(pg, "mine", "kling-effect", 2)
    effect_run(pg, "mine", "add-sound", 3)
    # a star keeps the first Kling output
    assert outcomes.record("star", asset_id=kept_asset, account_id=WHO["mine"], source="library", dsn=pg)
    # the other account ran the same effect four times: not this account's week
    for n in range(4, 8):
        effect_run(pg, "theirs", "kling-effect", n)
    # a run from ten days ago, and the scene it came with, fall outside the week
    old_gen, _ = effect_run(pg, "mine", "upscale", 9)
    age(pg, "generations", old_gen, 10)
    scene(pg, "mine", "A product ad for the headphones")
    scene(pg, "mine", "a product ad for the headphones  ")
    noir = scene(pg, "mine", "A noir short under one streetlight")
    old_scene = scene(pg, "mine", "An old brief")
    age(pg, "shoot_concepts", old_scene, 10)
    scene(pg, "theirs", "Their brief")

    week = trending.trending(account_id=WHO["mine"], dsn=pg)
    assert week["scope"] == "account" and week["days"] == 7
    assert [(e["effect"], e["runs"], e["kept"]) for e in week["effects"]] == [
        ("kling-effect", 2, 1), ("add-sound", 1, 0)]
    assert week["effects"][0]["label"] == "Kling effects"
    assert [(b["text"], b["count"]) for b in week["briefs"]] == [
        ("A product ad for the headphones", 2),
        ("A noir short under one streetlight", 1)]
    assert week["briefs"][1]["concept_id"] == noir
    assert week["events"] == {"kept": 1, "discarded": 0, "edited": 0}
    # nothing in the answer is a price
    assert "credits" not in str(week)

    theirs = trending.trending(account_id=WHO["theirs"], dsn=pg)
    assert [(e["effect"], e["runs"]) for e in theirs["effects"]] == [("kling-effect", 4)]
    assert [b["text"] for b in theirs["briefs"]] == ["Their brief"]


def test_an_empty_week_and_an_unreadable_store_are_empty_answers(seeded):
    pg = seeded
    empty = trending.trending(account_id=WHO["mine"], dsn=pg)
    assert empty["effects"] == [] and empty["briefs"] == []
    assert empty["events"] == {"kept": 0, "discarded": 0, "edited": 0}
    # never raises: a store that cannot be reached is the same empty shape
    down = trending.trending(account_id=WHO["mine"],
                             dsn="postgresql://nobody:nobody@127.0.0.1:1/nowhere")
    assert down["effects"] == [] and down["briefs"] == [] and down["scope"] == "account"


def test_the_window_is_lexical_on_the_tables_own_stamp():
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    assert trending.cutoff(7, now) == "2026-10-15T12:00:00+00:00"
    assert trending.brief_key("  A  Product\nad ") == "a product ad"


def test_the_route_answers_for_the_signed_in_account(seeded):
    pg = seeded
    effect_run(pg, "mine", "camera-move", 1)
    app.dependency_overrides[auth.current_account_id] = lambda: WHO["mine"]
    try:
        body = TestClient(app).get("/api/trending").json()
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)
    assert body["scope"] == "account"
    assert [e["effect"] for e in body["effects"]] == ["camera-move"]
