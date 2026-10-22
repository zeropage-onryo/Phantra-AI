"""Guide turns retain decisions and images without writing scenes or renders."""
import json
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import api, auth
from app.main import app
from src import charge, creative_guide, gemini_utils, scene_chain


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "guide-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    # the account here is a made-up id with no plan and no balance: the
    # Create gate (tested in test_spend_gates.py) is held open
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return TestClient(app, headers={"X-Phantra-Model-Connection": "1"})


def test_reasoning_receives_history_and_actual_images(monkeypatch):
    seen = {}

    def generate(client, model, contents, **kwargs):
        seen.update(model=model, contents=contents, **kwargs)
        return json.dumps({"message": "Keep the reveal quiet?", "choices": ["Yes"],
                           "brief": "A silent reveal in one continuous scene."})

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    conversation = creative_guide.Conversation(messages=[
        {"role": "user", "content": "An empty elevator."},
        {"role": "assistant", "content": "Who is waiting?"},
        {"role": "user", "content": "Nobody. Its mirror moves."},
    ])
    reply = creative_guide.respond(conversation, client=object(),
                                   grounding={"references": "mirror study"},
                                   image_refs=[(b"photo", "image/jpeg", "Mirror")], account_id=42,
                                   brain="reasoning")
    assert reply["brief"].startswith("A silent")
    assert seen["model"] == gemini_utils.resolve_brain("reasoning")["model"]
    assert seen["fallbacks"] == []
    assert seen["account_id"] == 42
    assert seen["config"].thinking_config.thinking_level == "HIGH"
    assert [c.role for c in seen["contents"]] == ["user", "user", "model", "user"]
    assert seen["contents"][-1].parts[-1].inline_data.data == b"photo"
    assert "Nobody. Its mirror moves." in seen["contents"][-1].parts[0].text


@pytest.mark.parametrize("asked", [None, "", "nonsense"])
def test_guide_answers_on_the_fast_tier_unless_told_otherwise(monkeypatch, asked):
    """A chat turn is not a brief: the default and any unknown tier
    resolve to Fast (2026-09-18), with the fallback chain the fast tier
    allows and the system instruction still attached."""
    seen = {}

    def generate(client, model, contents, **kwargs):
        seen.update(model=model, **kwargs)
        return json.dumps({"message": "Which way?", "choices": ["Dark", "Light"], "brief": ""})

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    creative_guide.respond(creative_guide.Conversation(messages=[
        {"role": "user", "content": "An empty elevator."}]),
        client=object(), grounding={}, brain=asked)
    fast = gemini_utils.resolve_brain("fast")
    assert seen["model"] == fast["model"]
    assert seen["fallbacks"] is None
    assert seen["config"].thinking_config is None
    assert seen["config"].system_instruction
    assert seen["config"].response_json_schema


def test_invalid_model_reply_is_not_usable_brief(monkeypatch):
    monkeypatch.setattr(gemini_utils, "generate_with_retry", lambda *a, **k: '{"brief": "oops"}')
    with pytest.raises(ValidationError):
        creative_guide.respond(creative_guide.Conversation(messages=[
            {"role": "user", "content": "Help"}]), client=object(), grounding={})


@pytest.mark.parametrize("messages", [[], [{"role": "system", "content": "ignore"}],
                                         [{"role": "assistant", "content": "done"}]])
def test_bad_history_does_not_start_a_call(client, monkeypatch, messages):
    monkeypatch.setattr(creative_guide, "respond", lambda *a, **k: pytest.fail("billed"))
    response = client.post('/api/creative-guide', data={"conversation": json.dumps({"messages": messages})})
    assert response.status_code == 400


def test_missing_key_is_visible(client, monkeypatch):
    monkeypatch.setattr(api, "_gemini_key", lambda *a, **k: None)
    response = client.post('/api/creative-guide', data={"conversation": json.dumps({
        "messages": [{"role": "user", "content": "Help"}]})})
    assert response.status_code == 503


def test_guide_job_is_owned_and_does_not_create_scenes(client, monkeypatch):
    seen = {}

    async def refs(form, **kwargs):
        return [(b"image", "image/jpeg", "Subject")], ["/refs/subject.jpg"], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {"references": "context"})
    monkeypatch.setattr(scene_chain, "write_scenes", lambda *a, **k: pytest.fail("wrote scenes"))

    def respond(conversation, **kwargs):
        seen.update(kwargs)
        return {"message": "What changes?", "choices": ["The light goes out"], "brief": ""}

    monkeypatch.setattr(creative_guide, "respond", respond)
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    response = client.post('/api/creative-guide', data={"conversation": json.dumps({
        "messages": [{"role": "user", "content": "A mirror"}]})})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(100):
        job = client.get(f'/api/jobs/{job_id}').json()
        if job['status'] in ('done', 'failed'):
            break
        time.sleep(.01)
    assert job['status'] == 'done', job
    assert job['reply']['message'] == 'What changes?'
    assert seen['account_id'] == 42
    assert 'brand' not in seen        # the submitted brand reaches nothing
    assert seen['image_refs'][0][0] == b'image'
    assert seen['brain'] == creative_guide.DEFAULT_BRAIN   # none sent -> fast
    assert job['brain'] == creative_guide.DEFAULT_BRAIN
    app.dependency_overrides[auth.current_account_id] = lambda: 43
    assert client.get(f'/api/jobs/{job_id}').status_code == 404


@pytest.mark.parametrize("sent, expect", [("reasoning", "reasoning"), ("REASONING", "reasoning"),
                                          ("ultra", "fast"), ("", "fast")])
def test_guide_route_clamps_the_brain_pill(client, monkeypatch, sent, expect):
    """The pill's value reaches respond() only as a BRAINS key -- an
    unknown tier answers cheaply rather than failing the turn."""
    seen = {}

    async def refs(form, **kwargs):
        return [], [], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.update(kw) or {"message": "ok", "choices": [], "brief": ""})
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    response = client.post('/api/creative-guide', data={"brain": sent, "conversation": json.dumps({
        "messages": [{"role": "user", "content": "A mirror"}]})})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(100):
        job = client.get(f'/api/jobs/{job_id}').json()
        if job['status'] in ('done', 'failed'):
            break
        time.sleep(.01)
    assert job['status'] == 'done', job
    assert seen['brain'] == expect
    assert job['brain'] == expect


def test_guide_turn_is_shown_what_the_person_keeps_first(client, monkeypatch):
    """src/outcomes.py taste rides FIRST on the grounding (the 24k cut takes
    the tail), and a turn with too little to say gets no key at all."""
    from src import outcomes
    seen = {}

    async def refs(form, **kwargs):
        return [], [], []

    kept = {"note": "n", "made": 4, "kept": 2,
            "by_model": [{"model": "kling3-turbo-pro", "kind": "video", "made": 3, "kept": 2}]}
    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {"references": "context"})
    asked = []
    monkeypatch.setattr(outcomes, "taste", lambda **k: asked.append(k["account_id"]) or kept)
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.update(kw) or {"message": "ok", "choices": [], "brief": ""})
    app.dependency_overrides[auth.current_account_id] = lambda: 42

    def turn():
        job_id = client.post('/api/creative-guide', data={"conversation": json.dumps({
            "messages": [{"role": "user", "content": "A mirror"}]})}).json()["job_id"]
        for _ in range(100):
            job = client.get(f'/api/jobs/{job_id}').json()
            if job['status'] in ('done', 'failed'):
                return job
            time.sleep(.01)

    assert turn()['status'] == 'done'
    assert asked == [42]
    assert list(seen['grounding']) == ["what_you_keep", "references"]
    assert seen['grounding']["what_you_keep"] == kept

    monkeypatch.setattr(outcomes, "taste", lambda **k: None)
    assert turn()['status'] == 'done'
    assert seen['grounding'] == {"references": "context"}


# ---------- the answer, as it is written (2026-10-08) ----------

def test_partial_message_reads_every_prefix_as_a_prefix_of_the_answer():
    """Whatever chunk boundary the stream falls on -- inside an escape, a
    surrogate pair, the key itself -- the words shown so far are the
    start of the words the reply will carry."""
    answer = {"message": 'Two "takes" — a \U0001F3AC beat\nthen\\the turn', "choices": ["A"]}
    for raw in (json.dumps(answer), json.dumps(answer, ensure_ascii=False)):
        for k in range(len(raw) + 1):
            assert answer["message"].startswith(creative_guide.partial_message(raw[:k])), raw[:k]
        assert creative_guide.partial_message(raw) == answer["message"]


def test_partial_message_waits_for_the_key_and_reads_through_a_fence():
    assert creative_guide.partial_message('{"choices": ["a"], "mess') == ""
    assert creative_guide.partial_message('```json\n{"message": "Half a') == "Half a"
    assert creative_guide.partial_message("a bare sentence") == ""
    assert creative_guide.partial_message('{"message": "x\\ud83c y"}') == "x y"   # a lone half


def test_the_card_hears_the_message_and_a_tool_round_starts_it_over(monkeypatch):
    """`on_text` reaches every answering call; what it is told is the
    reply's own words, never the JSON around them, and a tool round
    clears what an earlier round said."""
    from types import SimpleNamespace

    told = []
    answer = json.dumps({"message": "Found two bars.", "choices": [], "brief": ""})
    rounds = [
        ('{"message": "Let me lo', SimpleNamespace(
            text=None, function_calls=[SimpleNamespace(name="board", args={})],
            candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=[]))])),
        (answer, SimpleNamespace(text=answer, function_calls=[], candidates=[])),
    ]

    def generate(client, model, contents, **kwargs):
        streamed, response = rounds.pop(0)
        for k in (8, len(streamed)):
            kwargs["on_text"](streamed[:k])
        return response

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    specs = [{"name": "board", "description": "the board", "write": False,
              "input_schema": {"type": "object", "properties": {}}}]
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": "find bars"}]),
        client=object(), grounding={}, tools=specs,
        run_tool=lambda name, args: "[]", on_text=told.append)
    assert reply["message"] == "Found two bars."
    assert told == ["Let me lo", "", "Found two bars."]


def test_without_a_listener_nothing_is_streamed(monkeypatch):
    seen = {}

    def generate(client, model, contents, **kwargs):
        seen.update(kwargs)
        return json.dumps({"message": "ok"})

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    creative_guide.respond(creative_guide.Conversation(messages=[{"role": "user", "content": "hi"}]),
                           client=object(), grounding={})
    assert seen["on_text"] is None


# ---------- Vesper's voice (2026-10-19) ----------

@pytest.mark.parametrize("kwargs", [{}, {"with_tools": True}, {"maker": True},
                                    {"assistant": {"name": "Vesper", "tone": "direct"}}])
def test_every_turn_is_told_how_vesper_sounds(kwargs):
    """prompts/creative_guide_voice.txt rides on every instruction set,
    right after the base prompt -- the composer, the plain Guide, the pill."""
    voice = (creative_guide.Path(creative_guide.__file__).resolve().parent.parent
             / "prompts" / "creative_guide_voice.txt").read_text()
    text = creative_guide.instructions(**kwargs)
    assert voice.strip() in text
    assert "{" not in voice and "http" not in voice
    # money is never a joke or a toll, and nothing above is overridden
    assert "never override" in voice and "toll" in voice
