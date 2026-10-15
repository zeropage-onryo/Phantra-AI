"""
Insights on the listed servers (2026-10-11,
docs/tasks/task-connector-overnight.md PR 5): `what_works` and
`score_caption`.

What is guarded: both read one account's own outcomes and posts, say
plainly when there is too little to say, call no model, and carry no
dollar figure.
"""
import asyncio
import json

import pytest

from src import (
    accounts,
    db,
    entities,
    generative,
    ledger,
    mcp_server,
    outcomes,
    post_seo,
    preprod,
    projects,
    render_assets,
)


def _no_dollars(value, path="answer"):
    if isinstance(value, dict):
        for k, v in value.items():
            assert "usd" not in str(k).lower(), f"{path}.{k}"
            _no_dollars(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _no_dollars(v, f"{path}[{i}]")
    elif isinstance(value, str):
        assert "$" not in value, f"{path}: {value!r}"


@pytest.fixture
def world(pg, monkeypatch):
    db.init_db(pg)
    for init in (preprod.init, entities.init, generative.init, render_assets.init,
                 projects.init, ledger.init, outcomes.init):
        init(pg)
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})

    def render(acct, n, model="ltx2.3", concept_id=None):
        row = render_assets.record(generation_id=9400 + acct * 100 + n, tool="fal", model=model,
                                   media_kind="video", prompt=f"clip {n}",
                                   media_url=f"/renders/fal/{acct}-{n}.mp4", output_path=None,
                                   account_id=acct, dsn=pg, concept_id=concept_id)
        return int(row["id"])
    return {"dsn": pg, "a": a, "b": b, "render": render}


def test_with_nothing_made_what_works_says_so_and_calls_nothing(world):
    out = mcp_server.what_works(dsn=world["dsn"], account_id=world["a"])
    assert not out["enough_data"] and out["outputs"]["made"] == 0
    assert any("too little to say" in line for line in out["lines"])
    assert any("nothing posted" in line for line in out["lines"])
    assert out["presets"] == [] and out["posted"] == []
    _no_dollars(out)


def test_what_works_reads_each_accounts_own_keeps_presets_and_posts(world):
    ids = [world["render"](world["a"], n) for n in range(5)]
    world["render"](world["a"], 9, model="wan3")
    for i in ids[:2]:
        outcomes.record("star", asset_id=i, account_id=world["a"], source="test", dsn=world["dsn"])
    outcomes.record("delete", asset_id=ids[2], account_id=world["a"], source="test",
                    dsn=world["dsn"])
    # a scene written with a camera preset, rendered once; a video posted from it
    scene = preprod.save_concept(
        {"title": "Matcha pour", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY", "desc": "d",
                    "prompt": "a slow pour", "preset": "handheld-slow"}]}, dsn=world["dsn"], account_id=world["a"])
    world["render"](world["a"], 7, concept_id=scene)
    video = db.add_video("Matcha pour", "instagram", "2026-10-01", dsn=world["dsn"],
                         account_id=world["a"])
    with db.connect(world["dsn"]) as conn:
        conn.execute("UPDATE videos SET concept_id = %s WHERE id = %s", (scene, video))
    db.record_metrics(video, views=120, likes=9, dsn=world["dsn"], account_id=world["a"])
    world["render"](world["b"], 1)

    out = mcp_server.what_works(dsn=world["dsn"], account_id=world["a"])
    assert out["enough_data"] and out["outputs"]["made"] == 7 and out["outputs"]["kept"] == 2
    by = {m["model"]: m for m in out["outputs"]["by_model"]}
    assert by["ltx2.3"]["made"] == 6 and by["ltx2.3"]["kept"] == 2 and by["wan3"]["made"] == 1
    assert out["presets"] == [{"preset": "handheld-slow", "tried": 1, "kept": 0}]
    (post,) = out["posted"]
    assert post["scene_id"] == scene and post["views"] == 120 and post["likes"] == 9
    assert any("kept 2 of 7" in line for line in out["lines"])
    assert any("handheld-slow" in line for line in out["lines"])
    assert any("Matcha pour on instagram -- 120 views" in line for line in out["lines"])
    assert out["outputs"]["discards"][0]["deleted"] == 1
    _no_dollars(out)
    bob = mcp_server.what_works(dsn=world["dsn"], account_id=world["b"])
    assert bob["outputs"]["made"] == 1 and bob["posted"] == [] and not bob["enough_data"]


def test_score_caption_is_neutral_with_no_evidence_and_bounded(world):
    out = mcp_server.score_caption("A slow pour, side light, no music", dsn=world["dsn"],
                                   account_id=world["a"])
    assert out["score"] == 0.5 and not out["enough_data"]
    assert out["evidence"]["posted_videos"] == 0
    assert any("no performance data" in r for r in out["reasons"])
    assert "no evidence yet" in out["note"]
    _no_dollars(out)
    for bad, match in (("", "pass the caption"), ("x" * 2201, "at most 2200")):
        with pytest.raises(ValueError, match=match):
            mcp_server.score_caption(bad, dsn=world["dsn"], account_id=world["a"])


def test_score_caption_scores_against_the_accounts_own_winners(world, monkeypatch):
    from collections import Counter
    signals = {"sample": 6, "median": 100.0, "at_days": 7, "metric": "views",
               "winning_topics": Counter({"matcha": 3}), "losing_topics": Counter(),
               "winning_hooks": Counter(), "losing_hooks": Counter(),
               "winning_title_words": Counter({"pour": 3, "slow": 2})}
    seen = []
    monkeypatch.setattr(post_seo, "derive_signals",
                        lambda **kw: seen.append(kw) or signals)
    out = mcp_server.score_caption("A slow pour at dawn", dsn=world["dsn"],
                                   account_id=world["a"])
    assert seen[0]["account_id"] == world["a"]
    assert out["enough_data"] and out["score"] > 0.5
    assert any("shares words with winning titles" in r for r in out["reasons"])
    assert out["evidence"] == {"posted_videos": 6, "window_days": 7, "metric": "views"}


def test_both_listings_offer_the_insights_read_only_and_without_dollars(world):
    pytest.importorskip("mcp")
    for listed in (True, "claude"):
        server = mcp_server.build_server(dsn=world["dsn"], listed=listed, account_id=world["a"],
                                         job_status=lambda i, account_id=None: None)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        for name in ("what_works", "score_caption"):
            assert name in tools and tools[name].annotations.read_only_hint is True
            assert "$" not in tools[name].description
        for name, args in (("what_works", {}), ("score_caption", {"text": "a pour"})):
            res = asyncio.run(server.call_tool(name, args))
            _no_dollars(json.loads(res.content[0].text), name)
    studio = {t.name for t in asyncio.run(mcp_server.build_server(dsn=world["dsn"]).list_tools())}
    assert not {"what_works", "score_caption"} & studio
