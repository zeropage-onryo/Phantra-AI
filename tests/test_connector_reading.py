"""
The reading tools on the listed servers (2026-10-11,
docs/tasks/task-connector-overnight.md PR 3): `balance`, `search`, `whoami`,
`recent`, `credit_history`, `video_models` (in credits) and
`recommend_model` (a pure ranking, src/model_pick.py).

What is guarded: every answer is this account's only and in credits only
(no dollar figure anywhere in a listed answer); the ranking is pure and
reads the words; nothing calls a model.
"""
import asyncio
import json

import pytest

from src import (
    accounts,
    billing,
    entities,
    generative,
    ledger,
    mcp_server,
    model_pick,
    outcomes,
    preprod,
    projects,
    render_assets,
    scout,
)
from src.cut import store as cut_store


def _no_dollars(value, path="answer"):
    """No key naming dollars and no dollar sign in a string, recursively."""
    if isinstance(value, dict):
        for k, v in value.items():
            assert "usd" not in str(k).lower() and "dollar" not in str(k).lower(), f"{path}.{k}"
            _no_dollars(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _no_dollars(v, f"{path}[{i}]")
    elif isinstance(value, str):
        assert "$" not in value, f"{path}: {value!r}"


@pytest.fixture
def world(pg, monkeypatch):
    for init in (preprod.init, scout.init, entities.init, generative.init, render_assets.init,
                 projects.init, cut_store.init, ledger.init, outcomes.init, billing.init):
        init(pg)
    seeded = accounts.seed("alice@example.com", dsn=pg)
    a = seeded["accounts"][0]
    alice = accounts.get_user_by_email("alice@example.com", dsn=pg)["id"]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    ledger.grant(a, 500, "promo", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    project = projects.create("Spring spots", "a brief for spring", pg, account_id=a)
    scene = preprod.save_concept(
        {"title": "Matcha pour", "hook": "", "logline": "a slow pour",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY", "desc": "d",
                    "prompt": "Ultra-realistic matcha being poured in slow light"}]}, dsn=pg, account_id=a)
    projects.tag_concepts([scene], project["id"], pg, account_id=a)
    row = render_assets.record(generation_id=9301, tool="fal", model="ltx2.3",
                               media_kind="video", prompt="the matcha pour clip",
                               media_url="/renders/fal/m.mp4", output_path=None,
                               account_id=a, dsn=pg, concept_id=scene)
    return {"dsn": pg, "a": a, "b": b, "alice": alice, "project": project["id"],
            "scene": scene, "render": f"gen:{row['id']}"}


# --------------------------------------------------------------------------
# balance
# --------------------------------------------------------------------------

def test_balance_is_this_accounts_credits_only(world):
    out = mcp_server.read_balance(dsn=world["dsn"], account_id=world["a"])
    assert out["available"] == 500 and out["held"] == 0 and out["plan"] is None
    assert out["charged"] is True and out["scheduled"] == []
    (lot,) = out["lots"]
    assert lot["kind"] == "promo" and lot["credits"] == 500 and lot["remaining"] == 500
    assert "studio" in out["note"]
    _no_dollars(out)
    bob = mcp_server.read_balance(dsn=world["dsn"], account_id=world["b"])
    assert bob["available"] == 0 and bob["lots"] == []


def test_balance_names_the_plan_in_credits_never_its_price(world, monkeypatch):
    monkeypatch.setattr(accounts, "plan_of", lambda account_id, dsn=None: "creator")
    out = mcp_server.read_balance(dsn=world["dsn"], account_id=world["a"])
    assert out["plan"] == {"key": "creator", "name": "Creator", "tier": "creator",
                           "credits_per_month": 3500}
    _no_dollars(out)


def test_a_listed_balance_names_no_purchase_page(world):
    """OpenAI's commerce rule (read 2026-10-12): a listed server's balance
    says where credits are added, never a link to a page that sells them."""
    import asyncio
    import json

    server = mcp_server.build_server(dsn=world["dsn"], listed=True, account_id=world["a"])
    result = asyncio.run(server.call_tool("balance", {}))
    payload = result.structuredContent if getattr(result, "structuredContent", None) else json.loads(
        next(c.text for c in result.content if getattr(c, "type", "") == "text"))
    assert payload["available"] == 500
    assert "studio" in payload["note"] and "http" not in payload["note"]
    _no_dollars(payload)


def test_balance_falls_back_to_the_ledger_when_the_plan_tables_cannot_answer(world, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("schema in flight")
    monkeypatch.setattr(billing, "balance", boom)
    out = mcp_server.read_balance(dsn=world["dsn"], account_id=world["a"])
    assert out["available"] == 500 and out["lots"][0]["remaining"] == 500
    assert out["plan"] is None


def test_no_workspace_is_refused(pg):
    ledger.init(pg)
    with pytest.raises(mcp_server.Refused, match="no workspace"):
        mcp_server.read_balance(dsn=pg, account_id=None)


# --------------------------------------------------------------------------
# search, recent, whoami, credit_history
# --------------------------------------------------------------------------

def test_search_finds_each_persons_own_work_with_the_ids_the_tools_take(world):
    out = mcp_server.search_studio("matcha", dsn=world["dsn"], account_id=world["a"])
    assert out["count"] >= 2 and not out["recent"]
    (scene,) = out["scenes"]
    assert scene["scene_id"] == world["scene"] and scene["project_title"] == "Spring spots"
    assert scene["studio_url"].endswith(f"/studio/scene/{world['scene']}")
    (render,) = out["renders"]
    assert render["id"] == world["render"] and render["kind"] == "video"
    spring = mcp_server.search_studio("spring", dsn=world["dsn"], account_id=world["a"])
    assert [p["id"] for p in spring["projects"]] == [world["project"]]
    assert mcp_server.search_studio("matcha", dsn=world["dsn"], account_id=world["b"])["count"] == 0
    recent = mcp_server.search_studio("", dsn=world["dsn"], account_id=world["a"])
    assert recent["recent"] and [p["id"] for p in recent["projects"]] == [world["project"]]
    nothing = mcp_server.search_studio("zzzz", dsn=world["dsn"], account_id=world["a"])
    assert nothing["count"] == 0 and "nothing matched" in nothing["note"]
    _no_dollars(out)


def test_recent_lists_projects_open_scenes_and_renders(world):
    out = mcp_server.recent(limit=5, dsn=world["dsn"], account_id=world["a"])
    assert [p["title"] for p in out["projects"]] == ["Spring spots"]
    (scene,) = out["scenes"]
    assert scene["scene_id"] == world["scene"] and scene["project_id"] == world["project"]
    assert "brand" not in scene and "spark" not in scene
    assert [r["id"] for r in out["renders"]] == [world["render"]]
    assert mcp_server.recent(dsn=world["dsn"], account_id=world["b"]) == \
        {"projects": [], "scenes": [], "renders": []}


def test_whoami_names_the_workspace_the_plan_and_the_person(world):
    token = mcp_server.CALLER_USER.set(world["alice"])
    try:
        out = mcp_server.whoami(dsn=world["dsn"], account_id=world["a"])
    finally:
        mcp_server.CALLER_USER.reset(token)
    assert out["workspace"]["id"] == world["a"] and out["workspace"]["slug"]
    assert out["plan"] is None and out["signed_in_person"]
    assert out["member"]["name"] == "Mike" and out["member"]["role"] == "owner"
    assert out["studio_url"].startswith("http")
    nobody = mcp_server.whoami(dsn=world["dsn"], account_id=world["a"])
    assert nobody["member"] is None and not nobody["signed_in_person"] and nobody["note"]
    _no_dollars(out)


def test_credit_history_pages_in_credits_newest_first(world):
    out = mcp_server.credit_history_page(dsn=world["dsn"], account_id=world["a"])
    (item,) = out["items"]
    assert item["kind"] == "grant" and item["credits"] == 500 and item["balance_after"] == 500
    assert out["next"] is None and out["count"] == 1
    _no_dollars(out)
    for bad in (0, -3, "x"):
        with pytest.raises(ValueError, match="before is an id"):
            mcp_server.credit_history_page(before=bad, dsn=world["dsn"], account_id=world["a"])
    assert mcp_server.credit_history_page(dsn=world["dsn"], account_id=world["b"])["items"] == []


# --------------------------------------------------------------------------
# the models: in credits, and a pure ranking
# --------------------------------------------------------------------------

def test_video_models_are_priced_in_credits_with_their_draft_frames(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    out = mcp_server.list_video_models_listed()
    _no_dollars(out)
    by = {m["id"]: m for m in out["models"]}
    assert out["default"] in by and out["available"]
    wan = by["wan3"]
    assert wan["draft"] == "480p" and wan["credits_by_frame"]["480p"] < wan["credits_by_frame"]["1080p"]
    assert all(isinstance(c, int) and c > 0 for m in out["models"] for c in m["credits_by_frame"].values())
    assert by["ltx2.3"]["draft"] is None


FAKE = [
    {"model": "cheap1", "name": "Cheap", "blurb": "Fast, cheap.", "tier": "standard",
     "min_seconds": 6, "max_seconds": 10, "draft": None},
    {"model": "sound1", "name": "Sound", "blurb": "Newest, with sound, up to 20 seconds.",
     "tier": "creator", "min_seconds": 6, "max_seconds": 20, "draft": None},
    {"model": "prem1", "name": "Premium", "blurb": "Top model, with sound. Premium only.",
     "tier": "premium", "min_seconds": 4, "max_seconds": 8, "draft": None},
    {"model": "draft1", "name": "Drafty", "blurb": "Open-weight realism.", "tier": "standard",
     "min_seconds": 2, "max_seconds": 10, "draft": "480p"},
]
PRICES = {"cheap1": 87, "sound1": 110, "prem1": 480, "draft1": 120}


def _price(model, seconds):
    return (PRICES[model], seconds or 5, "720p")


def test_the_ranking_is_pure_and_reads_the_words():
    cheap = model_pick.rank("a cheap test", catalogue=FAKE, price=_price)
    assert cheap["picks"][0]["model"] == "cheap1" and cheap["asked"] == ["cheap"]
    assert "cheapest" in cheap["picks"][0]["reason"] and cheap["picks"][0]["credits"] == 87
    sound = model_pick.rank("a spot with sound and dialogue", catalogue=FAKE, price=_price)
    assert sound["picks"][0]["model"] in ("sound1", "prem1")
    assert "sound" in sound["picks"][0]["reason"]
    final = model_pick.rank("the final client deliverable", catalogue=FAKE, price=_price)
    assert final["picks"][0]["model"] == "prem1" and "premium" in final["picks"][0]["reason"]
    long = model_pick.rank("a long take", seconds=18, catalogue=FAKE, price=_price)
    assert [p["model"] for p in long["picks"]] == ["sound1"]
    assert {s["model"] for s in long["skipped"]} == {"cheap1", "prem1", "draft1"}
    assert "cannot make a 18s clip" in long["skipped"][0]["why"]
    budget = model_pick.rank("anything", budget_credits=100, catalogue=FAKE, price=_price)
    assert {p["model"] for p in budget["picks"]} == {"cheap1"}
    assert any("over the budget" in s["why"] for s in budget["skipped"])
    drafty = model_pick.rank("", draft=True, catalogue=FAKE, price=_price)
    assert drafty["picks"][0]["model"] == "draft1" and "draft tier" in drafty["picks"][0]["reason"]
    kept = model_pick.rank("", catalogue=FAKE, price=_price,
                           kept={"sound1": (4, 4), "cheap1": (2, 0)}, default_model="cheap1")
    assert kept["picks"][0]["model"] == "sound1" and "kept 4 of the 4" in kept["picks"][0]["reason"]
    assert kept["picks"][1]["kept"] == {"made": 2, "kept": 0}          # too few to say
    assert all("_score" not in p for p in kept["picks"]) and len(kept["picks"]) <= model_pick.PICKS
    plain = model_pick.rank("", catalogue=FAKE, price=_price, default_model="cheap1")
    assert plain["picks"][0]["model"] == "cheap1" and plain["asked"] == []


def test_recommend_model_runs_off_the_real_catalogue_and_calls_nothing(world):
    out = mcp_server.recommend_model("a cheap test", dsn=world["dsn"], account_id=world["a"])
    assert out["picks"] and out["considered"] >= 5 and out["seconds"] == 5
    assert all(isinstance(p["credits"], int) for p in out["picks"])
    _no_dollars(out)
    long = mcp_server.recommend_model("a long take", seconds=25, dsn=world["dsn"],
                                      account_id=world["a"])
    assert {p["model"] for p in long["picks"]} == {"seedance2.5"}
    for bad in ({"seconds": 0}, {"seconds": "x"}, {"budget_credits": -1}):
        with pytest.raises(ValueError):
            mcp_server.recommend_model("x", dsn=world["dsn"], account_id=world["a"], **bad)
    # what the person kept on a model moves it up
    outcomes.record("star", asset_id=int(world["render"].split(":")[1]),
                    account_id=world["a"], source="test", dsn=world["dsn"])
    kept = mcp_server.recommend_model("a cheap test", dsn=world["dsn"], account_id=world["a"])
    ltx = next(p for p in kept["picks"] if p["model"] == "ltx2.3")
    assert ltx["kept"] == {"made": 1, "kept": 1}


# --------------------------------------------------------------------------
# the listings
# --------------------------------------------------------------------------

READS = ("balance", "search", "whoami", "recent", "credit_history", "video_models",
         "recommend_model")


def test_both_listings_offer_the_reading_tools_and_say_no_price(pg):
    pytest.importorskip("mcp")
    preprod.init(pg)
    scout.init(pg)
    for listed in (True, "claude"):
        server = mcp_server.build_server(dsn=pg, listed=listed,
                                         job_status=lambda i, account_id=None: None)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        for name in READS:
            assert name in tools, (listed, name)
            assert tools[name].annotations.read_only_hint is True
            assert "$" not in tools[name].description and "dollar" not in tools[name].description
        assert "credits" in tools["video_models"].description
    studio = {t.name for t in asyncio.run(mcp_server.build_server(dsn=pg).list_tools())}
    assert not (set(READS) - {"video_models"}) & studio


def test_a_listed_answer_carries_no_dollar_figure_anywhere(world, monkeypatch):
    pytest.importorskip("mcp")
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    server = mcp_server.build_server(dsn=world["dsn"], listed="claude", account_id=world["a"],
                                     job_status=lambda i, account_id=None: None)
    for name, args in (("balance", {}), ("search", {"q": "matcha"}), ("whoami", {}),
                       ("recent", {}), ("credit_history", {}), ("video_models", {}),
                       ("recommend_model", {"what": "a cheap test"})):
        res = asyncio.run(server.call_tool(name, args))
        payload = json.loads(res.content[0].text)
        _no_dollars(payload, name)
