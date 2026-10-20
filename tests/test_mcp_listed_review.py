"""
The directory review's findings on the two LISTED servers (2026-10-15):
`/mcp` (LISTED_TOOLS, the ChatGPT listing) and `/mcp/claude`
(CLAUDE_LISTED_TOOLS).

- B4: neither listing sells anything. OpenAI's plugin guidelines allow a
  plugin to say a feature needs more credits, never to show plans or link to
  a checkout, upgrade or purchase page -- so no `/pricing`, `checkout`,
  `upgrade_url` or `$` in a description, the instructions, or an answer
  about running short.
- S4: every argument of every listed tool has a description in its schema.
- S5: `share_link` and `upload_link` are not reads of a closed world.
- S9: a bad argument is a plain sentence, an unknown scene says "scene",
  and `initialize` reports a version.
"""
import asyncio
import json
import re

import pytest

from src import accounts, charge, ledger, mcp_server, preprod

pytest.importorskip("mcp")

LISTINGS = (True, "claude")
SELLING = re.compile(r"(?i)/pricing|checkout|upgrade_url|\$|top up|top-up|subscribe|"
                     r"pick a plan|https?://")
FACE = "/characters/sam/photo/face.jpg"
SCENE = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact face. "
         "Style: soft window light, true colour, a 35mm frame at chest height. "
         "(0-4s) Sam lifts the lid of a dented biscuit tin and freezes. "
         "(4-10s) Hard cut to the hallway: Sam backs away from the open door. "
         "No background music. Only diegetic sound: the tin lid.")


def _no_selling(value, path="answer"):
    if isinstance(value, dict):
        for k, v in value.items():
            assert not SELLING.search(str(k)), f"{path}.{k}"
            _no_selling(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _no_selling(v, f"{path}[{i}]")
    elif isinstance(value, str):
        assert not SELLING.search(value), f"{path}: {value!r}"


def _payload(result):
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    return json.loads(next(c.text for c in result.content if getattr(c, "type", "") == "text"))


def _server(dsn, listed, **kw):
    ok = lambda *a, **k: {}          # noqa: E731
    kw.setdefault("approve_render", ok)
    kw.setdefault("approve_keyframes", ok)
    kw.setdefault("job_status", lambda job_id, account_id=None: None)
    return mcp_server.build_server(dsn=dsn, listed=listed, **kw)


@pytest.fixture
def world(pg, monkeypatch):
    from src import asset_shelf, billing, entities, projects

    for init in (preprod.init, entities.init, projects.init, ledger.init, billing.init):
        init(pg)
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "a tired courier",
                          "photos": [FACE]}])
    return {"dsn": pg, "a": a}


# --------------------------------------------------------------------------
# the counts: nothing was added or dropped by the review's fixes
# --------------------------------------------------------------------------

def test_the_two_listings_still_offer_exactly_their_tools(tmp_path):
    dsn = str(tmp_path / "unused.db")
    for listed, expected in ((True, mcp_server.LISTED_TOOLS),
                             ("claude", mcp_server.CLAUDE_LISTED_TOOLS)):
        names = [t.name for t in asyncio.run(_server(dsn, listed).list_tools())]
        assert set(names) == set(expected), listed
    assert len(mcp_server.LISTED_TOOLS) == 42 and len(mcp_server.CLAUDE_LISTED_TOOLS) == 32


# --------------------------------------------------------------------------
# S4: every argument is described
# --------------------------------------------------------------------------

def test_every_argument_of_every_listed_tool_has_a_description(tmp_path):
    dsn = str(tmp_path / "unused.db")
    for listed in LISTINGS:
        for tool in asyncio.run(_server(dsn, listed).list_tools()):
            for arg, schema in (tool.input_schema.get("properties") or {}).items():
                said = (schema.get("description") or "").strip()
                assert said, f"{listed}: {tool.name}.{arg} has no description"
                assert len(said) <= 300, f"{tool.name}.{arg}: keep it short"
                low = said.lower()
                for word in mcp_server.INTERNAL_WORDS:
                    assert word.lower() not in low, f"{tool.name}.{arg}: {word!r}"
                assert "$" not in said and "dollar" not in low and "usd" not in low, \
                    f"{tool.name}.{arg}: credits only"


# --------------------------------------------------------------------------
# B4: nothing on a listed server sells
# --------------------------------------------------------------------------

def test_no_listed_description_title_or_instruction_sells(tmp_path):
    dsn = str(tmp_path / "unused.db")
    for listed in LISTINGS:
        server = _server(dsn, listed)
        _no_selling(server.instructions, f"{listed} instructions")
        for tool in asyncio.run(server.list_tools()):
            _no_selling(tool.title, f"{tool.name}.title")
            _no_selling(tool.description, f"{tool.name}.description")
            _no_selling(tool.input_schema, f"{tool.name}.inputSchema")


def test_a_listed_balance_names_no_page_and_no_price(world, monkeypatch):
    monkeypatch.setattr(accounts, "plan_of", lambda account_id, dsn=None: "creator")
    ledger.grant(world["a"], 120, "promo", dsn=world["dsn"])
    for listed in LISTINGS:
        server = _server(world["dsn"], listed, account_id=world["a"])
        out = _payload(asyncio.run(server.call_tool("balance", {})))
        assert out["available"] == 120 and out["plan"]["name"] == "Creator"
        assert out["note"] == mcp_server.LISTED_CREDITS_NOTE
        _no_selling(out)


def test_a_listed_still_the_balance_cannot_cover_names_no_page(world, monkeypatch):
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-secret-for-quotes")
    monkeypatch.setattr(mcp_server, "_balance", lambda account_id, dsn: 3)
    server = _server(world["dsn"], True, account_id=world["a"])
    out = _payload(asyncio.run(server.call_tool(
        "generate_image", {"prompt": "a can", "model": "seedream4.5", "aspect": "1:1"})))
    assert out["refused"] == "insufficient_credits" and out["available"] == 3
    assert mcp_server.CREDITS_ADDED_IN_STUDIO in out["note"]
    _no_selling(out)


def test_a_listed_approve_out_of_credits_and_unknown_scene_say_it_plainly(world):
    from mcp.server.mcpserver.exceptions import ToolError

    from src.approvals import ApproveRefused

    short = charge.refusal(ledger.InsufficientCredit(1, 40, 3), "this scene")
    assert "top up" in short                  # the studio's own sentence, as it is

    def render(concept_id, account_id, body):
        if concept_id == 999:
            raise ApproveRefused(404, "not_found", "no such concept")
        raise ApproveRefused(402, "out_of_credits", short)

    server = _server(world["dsn"], True, account_id=world["a"],
                     approve_render=render, approve_keyframes=lambda *a: {})
    with pytest.raises(ToolError) as refused:
        asyncio.run(server.call_tool("approve", {"scene_id": 1, "tokens": ["phq.x.y"]}))
    said = str(refused.value)
    assert "needs 40" in said and mcp_server.CREDITS_ADDED_IN_STUDIO in said
    _no_selling(said)
    with pytest.raises(ToolError) as missing:
        asyncio.run(server.call_tool("approve", {"scene_id": 999}))
    assert "no scene 999" in str(missing.value) and "concept" not in str(missing.value)


def test_a_listed_quote_on_a_short_balance_names_no_page(world):
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=world["dsn"],
                                 account_id=world["a"])["scene_id"]
    for listed in LISTINGS:
        server = _server(world["dsn"], listed, account_id=world["a"])
        out = _payload(asyncio.run(server.call_tool("quote", {"scene_id": sid})))
        assert out["affordable"] is False and out["balance"] == 0
        # the Claude listing's `approve_url` is the scene's own page in the
        # studio, not a purchase page: screened apart from the rest
        approve_url = out.pop("approve_url", None)
        assert approve_url is None or "/pricing" not in approve_url
        _no_selling(out)


def test_the_studios_own_refusals_are_reworded_for_a_listed_server():
    for text in (charge.CREATE_REFUSAL, charge.TRIAL_THINKING_REFUSAL,
                 charge.refusal(ledger.InsufficientCredit(1, 9, 1), "this still"),
                 f"x -- pick a plan or top up at {mcp_server.DEFAULT_PRICING_URL}"):
        said = mcp_server.listed_text(text)
        assert mcp_server.CREDITS_ADDED_IN_STUDIO in said, said
        _no_selling(said)
    assert mcp_server.listed_text("no scene 4") == "no scene 4"


def test_the_studio_surface_keeps_its_link(monkeypatch):
    monkeypatch.delenv(mcp_server.PRICING_URL_ENV, raising=False)
    from src import ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "credit_exempt", lambda a, dsn=None: False)
    monkeypatch.setattr(mcp_server, "_balance", lambda a, dsn: 1)
    stop, _, _ = mcp_server.approval_gate(5.0, "", tool="generate_image", args={},
                                          what="This image", account_id=7, dsn=None)
    assert stop["upgrade_url"] == mcp_server.DEFAULT_PRICING_URL


# --------------------------------------------------------------------------
# S5: the hints
# --------------------------------------------------------------------------

def test_a_link_minting_tool_is_not_a_closed_world_read():
    h = mcp_server.HINTS
    assert h["share_link"] == {"read": False, "destructive": False, "idempotent": False,
                               "open_world": True}
    assert h["upload_link"]["open_world"] is True and h["upload_link"]["read"] is False
    for name in ("set_preferences", "save_recipe", "feedback", "duplicate_scene"):
        assert h[name]["read"] is False, name
    assert mcp_server.TITLES["elements"] == "List your elements"


# --------------------------------------------------------------------------
# S9: errors and the version
# --------------------------------------------------------------------------

@pytest.mark.parametrize("tool, args, needle", [
    ("add_element", {"kind": "monster", "name": "x", "source": "gen:1"},
     "`kind` must be one of 'character', 'prop' or 'location'"),
    ("scene", {"scene_id": "abc"}, "`scene_id` must be a whole number"),
    ("scene", {}, "`scene_id` is required"),
    ("reformat", {"ref": "gen:1", "aspect": "3:2"}, "`aspect` must be one of"),
])
def test_a_bad_argument_is_a_plain_sentence(tmp_path, tool, args, needle):
    from mcp.server.mcpserver.exceptions import ToolError

    for listed in LISTINGS:
        server = _server(str(tmp_path / "unused.db"), listed)
        with pytest.raises(ToolError) as bad:
            asyncio.run(server.call_tool(tool, args))
        said = str(bad.value)
        assert needle in said and "Nothing was spent" in said, said
        for raw in ("Arguments", "type=", "pydantic", "validation error", "http"):
            assert raw not in said, (raw, said)


def test_the_server_reports_a_version(tmp_path):
    for listed in LISTINGS:
        server = _server(str(tmp_path / "unused.db"), listed)
        options = server._lowlevel_server.create_initialization_options()
        assert options.server_version and options.server_version == mcp_server.SERVER_VERSION
