"""Vesper proposes brand kit edits; only the card's Apply makes them
(docs/tasks/task-brand-kit-import-and-chat.md step 6, src/kit_changes.py).

A valid change becomes a proposal with each field before and after; a value
the kit would refuse goes back to the model naming the field; the tool is
handed only to a turn in a project that picked a kit, for that kit only; and
Apply writes the caller's kit, never another account's. Nothing reaches a
network or a model.
"""
import json
import types as pytypes

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import (
    accounts,
    brand_kits,
    creative_guide,
    gemini_utils,
    guide_tools,
    kit_changes,
    preprod,
    projects,
)

client = TestClient(app)
GUARDED = {"x-phantra-model-connection": "1"}
SPEC = {"identity": {"tagline": "Get a Gyg, stay for good."},
        "palette": [{"hex": "#FF880B", "role": "primary", "name": "Gygler orange"},
                    {"hex": "#FAF0E4", "role": "background", "name": "Cream"}],
        "look": {"style": "Warm and clean.", "banned": ["neon"]}}


@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    brand_kits.init(pg)
    projects.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("kc-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("kc-theirs", "Theirs", "#fff", dsn=pg)
    kit = brand_kits.create("Gygler", SPEC, pg, account_id=mine)
    project = projects.create("Gygler explainer", "", pg, account_id=mine)
    project = projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    return {"pg": pg, "mine": mine, "theirs": theirs, "kit": kit, "project": project}


# ---------- the arithmetic ----------

def test_a_colour_and_a_list_change_show_before_and_after():
    kit = {"id": 7, "name": "Gygler", "spec": brand_kits.clean_spec(SPEC)}
    checked = kit_changes.check({"kit_id": 7, "changes": [
        {"field": "palette.background", "value": "#fcf4eb"},
        {"field": "look.banned", "value": "neon, cold blue light"},
        {"field": "palette.text", "value": "151515"}]}, kit)
    assert checked["kit_name"] == "Gygler"
    assert checked["diff"] == [
        {"field": "palette.background", "label": "Background colour", "kind": "colour",
         "before": "#FAF0E4", "after": "#FCF4EB"},
        {"field": "look.banned", "label": "Banned elements", "kind": "text",
         "before": "neon", "after": "neon, cold blue light"},
        {"field": "palette.text", "label": "Text colour", "kind": "colour",
         "before": "", "after": "#151515"}]
    after = kit_changes.apply(kit["spec"], checked["changes"])
    assert [s["hex"] for s in after["palette"]] == ["#FF880B", "#FCF4EB", "#151515"]
    assert after["identity"]["tagline"] == "Get a Gyg, stay for good."      # untouched


@pytest.mark.parametrize("change,field", [
    ({"field": "palette.background", "value": "cream"}, "palette.background"),
    ({"field": "identity.selling_points", "value": "\n".join(f"p{i}" for i in range(9))},
     "identity.selling_points"),
    ({"field": "look.style", "value": "x" * 1501}, "look.style"),
    ({"field": "identity.logo", "value": "new.png"}, "identity.logo"),
    ({"field": "voice.tone", "value": 3}, "voice.tone"),
])
def test_a_value_the_kit_would_refuse_names_its_field(change, field):
    kit = {"id": 7, "name": "Gygler", "spec": brand_kits.clean_spec(SPEC)}
    with pytest.raises(kit_changes.ChangeError) as e:
        kit_changes.check({"kit_id": 7, "changes": [change]}, kit)
    assert e.value.field == field


def test_only_the_threads_kit_can_be_changed():
    kit = {"id": 7, "name": "Gygler", "spec": brand_kits.clean_spec(SPEC)}
    with pytest.raises(kit_changes.ChangeError) as e:
        kit_changes.check({"kit_id": 8, "changes": [{"field": "voice.cta", "value": "x"}]}, kit)
    assert e.value.field == "kit_id"
    with pytest.raises(kit_changes.ChangeError):
        kit_changes.check({"kit_id": 7, "changes": [{"field": "voice.cta", "value": "x"}]}, None)
    with pytest.raises(guide_tools.Refused):
        guide_tools.check_args("propose_kit_change", {"kit_id": 7, "changes": []})


def test_the_tool_is_a_write_the_act_route_runs():
    assert guide_tools.is_write("propose_kit_change") and guide_tools.is_kit("propose_kit_change")
    assert not guide_tools.is_make("propose_kit_change")
    assert guide_tools.WRITE_LABELS["propose_kit_change"] == "Change the brand kit"


# ---------- a turn ----------

class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(role="model", parts=[]))]


def _turn(monkeypatch, responses, *, project, kit):
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    tools, run_tool = guide_tools.session(local=True, in_project=project is not None, kit=kit)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user",
                                               "content": "use #FCF4EB for the background"}]),
        client=object(), grounding={}, tools=tools, run_tool=run_tool, project=project)
    return reply, seen


def test_a_turn_ends_on_the_proposal_with_its_before_and_after(dbx, monkeypatch):
    k = dbx
    kid = k["kit"]["id"]
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("propose_kit_change", {"kit_id": kid, "changes": [
            {"field": "palette.background", "value": "#FCF4EB"}]})]),
    ], project=k["project"], kit=k["kit"])
    proposal = reply["proposal"]
    assert proposal["tool"] == "propose_kit_change" and proposal["label"] == "Change the brand kit"
    assert proposal["args"]["diff"] == [{"field": "palette.background",
                                         "label": "Background colour", "kind": "colour",
                                         "before": "#FAF0E4", "after": "#FCF4EB"}]
    assert reply["message"].startswith("Here is the change to Gygler (background colour)")
    config = seen[0][1]["config"]
    assert "BRAND KIT EDITS" in config.system_instruction
    offered = {d.name: d for t in config.tools for d in t.function_declarations}
    assert "propose_kit_change" in offered
    assert "#FAF0E4" in offered["propose_kit_change"].description
    # nothing changed: the card has not been pressed
    assert brand_kits.get(kid, k["pg"], account_id=k["mine"])["spec"]["palette"][1]["hex"] == "#FAF0E4"


def test_a_refused_value_goes_back_to_the_model_naming_the_field(dbx, monkeypatch):
    k = dbx
    kid = k["kit"]["id"]
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("propose_kit_change", {"kit_id": kid, "changes": [
            {"field": "palette.background", "value": "cream"}]})]),
        _Resp(calls=[("propose_kit_change", {"kit_id": kid, "changes": [
            {"field": "palette.background", "value": "#FCF4EB"}]})]),
    ], project=k["project"], kit=k["kit"])
    told = [p.function_response.response["result"] for c in seen[1][0]
            for p in (getattr(c, "parts", None) or []) if getattr(p, "function_response", None)]
    assert told and "palette.background" in told[0] and "not a #RRGGBB" in told[0]
    assert reply["proposal"]["args"]["diff"][0]["after"] == "#FCF4EB"


def test_no_kit_no_tool(dbx, monkeypatch):
    k = dbx
    bare = projects.create("No kit", "", k["pg"], account_id=k["mine"])
    answer = json.dumps({"message": "Sure.", "choices": [], "brief": ""})
    _reply, seen = _turn(monkeypatch, [_Resp(text=answer)], project=bare, kit=None)
    config = seen[0][1]["config"]
    offered = [d.name for t in config.tools for d in t.function_declarations]
    assert "propose_kit_change" not in offered
    assert "BRAND KIT EDITS" not in config.system_instruction
    assert "propose_kit_change" not in [s["name"] for s in guide_tools.session(local=True)[0]]


# ---------- the card's Apply ----------

@pytest.fixture
def as_mine(dbx, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    app.dependency_overrides[auth.current_account_id] = lambda: dbx["mine"]
    yield dbx
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _apply(k, **over):
    body = {"tool": "propose_kit_change", "project_id": k["project"]["id"],
            "args": {"kit_id": k["kit"]["id"], "changes": [
                {"field": "palette.background", "value": "#FCF4EB"},
                {"field": "identity.selling_points", "value": "Staff in 24 hours\nOne rate"}]},
            **over}
    return client.post("/api/creative-guide/act", headers=GUARDED, json=body)


def test_apply_changes_the_kit_and_returns_what_it_replaced(as_mine):
    k = as_mine
    r = _apply(k)
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["result"] == "Gygler: background colour, selling points changed"
    assert done["previous"]["palette"][1]["hex"] == "#FAF0E4"
    assert done["kit"]["spec"]["palette"][1]["hex"] == "#FCF4EB"
    kit = brand_kits.get(k["kit"]["id"], k["pg"], account_id=k["mine"])
    assert kit["spec"]["identity"]["selling_points"] == ["Staff in 24 hours", "One rate"]
    assert kit["spec"]["identity"]["tagline"] == "Get a Gyg, stay for good."
    # Undo is the kit page's own PATCH with the spec it replaced
    back = client.patch(f"/api/brand-kits/{k['kit']['id']}", json={"spec": done["previous"]})
    assert back.json()["spec"]["palette"][1]["hex"] == "#FAF0E4"


def test_apply_refuses_another_kit_another_project_and_a_bad_value(as_mine):
    k = as_mine
    before = brand_kits.get(k["kit"]["id"], k["pg"], account_id=k["mine"])["spec"]
    other = brand_kits.create("Other", {}, k["pg"], account_id=k["mine"])
    theirs = projects.create("Theirs", "", k["pg"], account_id=k["theirs"])
    for over in ({"args": {"kit_id": other["id"], "changes": [
                    {"field": "voice.cta", "value": "Go"}]}},
                 {"project_id": theirs["id"]},
                 {"project_id": None},
                 {"args": {"kit_id": k["kit"]["id"], "changes": [
                     {"field": "palette.primary", "value": "orange"}]}}):
        r = _apply(k, **over)
        assert r.status_code == 400 and r.json()["error"]["code"] == "refused", r.text
    assert brand_kits.get(k["kit"]["id"], k["pg"], account_id=k["mine"])["spec"] == before
    assert brand_kits.get(other["id"], k["pg"], account_id=k["mine"])["spec"]["voice"]["cta"] == ""
