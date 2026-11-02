"""The Claude facade (src/claude_client.py): Gemini's types in, Gemini's types out.

No network and no database: the SDK is a fake that records the request it was
sent and answers with canned messages.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace as NS

import pytest
from google.genai import types

from src import claude_client as cc
from src import gemini_utils, spend

SONNET = "claude-sonnet-5-5"


def message(*blocks, stop="end_turn", usage=None):
    return NS(content=list(blocks), stop_reason=stop, model=SONNET,
              usage=NS(**(usage or {"input_tokens": 100, "output_tokens": 50,
                                    "cache_read_input_tokens": 0,
                                    "cache_creation_input_tokens": 0})))


def text(t):
    return NS(type="text", text=t)


def tool_use(id_, name, **args):
    return NS(type="tool_use", id=id_, name=name, input=args)


class FakeStream:
    def __init__(self, final, deltas):
        self.final, self.text_stream = final, iter(deltas)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.final


class FakeSDK:
    def __init__(self, *answers, deltas=()):
        self.answers, self.sent, self.deltas = list(answers), [], deltas
        self.messages = self

    def create(self, **kw):
        self.sent.append(kw)
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    @contextmanager
    def stream(self, **kw):
        self.sent.append(kw)
        yield FakeStream(self.answers.pop(0), self.deltas)


def client(*answers, **kw):
    sdk = FakeSDK(*answers, **kw)
    return cc.ClaudeClient(sdk), sdk


def test_is_claude():
    assert cc.is_claude("claude-opus-5-5") and not cc.is_claude("gemini-3-flash")
    assert not cc.is_claude(None)


def test_text_round_trip_and_usage():
    c, sdk = client(message(text("hello"), usage={
        "input_tokens": 10, "output_tokens": 7, "cache_read_input_tokens": 90,
        "cache_creation_input_tokens": 5}))
    cfg = types.GenerateContentConfig(system_instruction="be brief")
    r = c.models.generate_content(model=SONNET, contents="hi", config=cfg)
    assert r.text == "hello"
    assert r.usage_metadata.prompt_token_count == 105      # includes the cache read
    assert r.usage_metadata.cached_content_token_count == 90
    assert r.usage_metadata.candidates_token_count == 7
    sent = sdk.sent[0]
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert sent["messages"] == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]


def test_tool_loop_matches_results_by_id_and_flags_errors():
    c, sdk = client(message(text("done")))
    call = types.Content(role="model", parts=[
        types.Part(function_call=types.FunctionCall(id="toolu_a", name="look", args={"q": 1})),
        types.Part(function_call=types.FunctionCall(id="toolu_b", name="peek", args={}))])
    back = types.Content(role="user", parts=[
        types.Part.from_function_response(name="peek", response={"result": "error: nope"}),
        types.Part.from_function_response(name="look", response={"result": "fine"})])
    c.models.generate_content(model=SONNET, contents=[
        types.Content(role="user", parts=[types.Part.from_text(text="go")]), call, back])
    msgs = sdk.sent[0]["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    results = {b["tool_use_id"]: b for b in msgs[2]["content"]}
    assert results["toolu_a"]["content"] == "fine" and "is_error" not in results["toolu_a"]
    assert results["toolu_b"]["is_error"] is True


def test_a_response_with_no_call_to_answer_is_refused():
    with pytest.raises(cc.ClaudeError):
        cc.to_messages([types.Content(role="user", parts=[
            types.Part.from_function_response(name="ghost", response={"result": "x"})])])


def test_tool_use_comes_back_as_a_function_call():
    c, _ = client(message(tool_use("toolu_1", "look", q="x")))
    r = c.models.generate_content(model=SONNET, contents="hi")
    fc = r.function_calls[0]
    assert (fc.id, fc.name, dict(fc.args)) == ("toolu_1", "look", {"q": "x"})


def test_thinking_round_trips_first_and_effort_is_adaptive():
    think = NS(type="thinking", thinking="hmm", signature="sig1")
    c, sdk = client(message(think, text("ok")))
    cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH))
    r = c.models.generate_content(model=SONNET, contents="hi", config=cfg)
    sent = sdk.sent[0]
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"]["effort"] == "high"
    assert "budget_tokens" not in str(sent)
    parts = r.candidates[0].content.parts
    assert parts[0].thought and parts[0].thought_signature == b"sig1"
    assert r.text == "ok"                                   # thinking is never the answer
    # handed back, it leads the assistant turn
    blocks = cc.to_messages([r.candidates[0].content])[0]["content"]
    assert blocks[0] == {"type": "thinking", "thinking": "hmm", "signature": "sig1"}


def test_json_schema_is_closed_and_unsupported_bounds_dropped():
    schema = {"type": "object", "properties": {
        "n": {"type": "integer", "minimum": 1, "maximum": 5},
        "xs": {"type": "array", "minItems": 3, "maxItems": 9, "items": {
            "type": "object", "properties": {"a": {"type": "string", "maxLength": 4}}}}}}
    out = cc.close_schema(schema)
    assert out["additionalProperties"] is False
    assert out["properties"]["xs"]["items"]["additionalProperties"] is False
    flat = str(out)
    for gone in ("minimum", "maximum", "maxItems", "maxLength", "minItems"):
        assert gone not in flat
    assert schema["properties"]["n"]["minimum"] == 1        # the input is not touched
    cfg = types.GenerateContentConfig(response_mime_type="application/json",
                                      response_json_schema=schema)
    req = cc.to_request(SONNET, "hi", cfg)
    assert req["output_config"]["format"]["type"] == "json_schema"


def test_tools_become_input_schemas():
    decl = types.FunctionDeclaration(name="look", description="d", parameters_json_schema={
        "type": "object", "properties": {"q": {"type": "string"}}})
    cfg = types.GenerateContentConfig(tools=[types.Tool(function_declarations=[decl])])
    tool = cc.to_request(SONNET, "hi", cfg)["tools"][0]
    assert tool["name"] == "look" and tool["input_schema"]["properties"]["q"]["type"] == "string"


def test_unreadable_image_is_said_not_sent():
    parts = [types.Part.from_bytes(data=b"x", mime_type="image/heic"),
             types.Part.from_bytes(data=b"x", mime_type="image/png")]
    blocks = cc.to_messages([types.Content(role="user", parts=parts)])[0]["content"]
    assert blocks[0]["type"] == "text" and "heic" in blocks[0]["text"]
    assert blocks[1]["type"] == "image" and blocks[1]["source"]["media_type"] == "image/png"


def test_same_role_turns_merge_with_results_first():
    merged = cc.to_messages([
        types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
            id="t1", name="f", args={}))]),
        types.Content(role="user", parts=[types.Part.from_text(text="extra")]),
        types.Content(role="user", parts=[types.Part.from_function_response(
            name="f", response={"result": "r"})])])
    user = merged[1]["content"]
    assert user[0]["type"] == "tool_result"


class Boom(Exception):
    def __init__(self, status, message="x", headers=None):
        super().__init__(message)
        self.status_code, self.message = status, message
        self.response = NS(headers=headers or {})


@pytest.mark.parametrize("status", [429, 500, 529])
def test_busy_api_reads_as_retriable_with_its_cooldown(status):
    err = cc.translate(Boom(status, "slow down", {"retry-after": "7"}))
    assert gemini_utils.is_retriable(err)
    assert gemini_utils.retry_delay(err, 0) == 9      # its own 7s, plus the 2s margin


def test_empty_balance_reads_as_depleted():
    err = cc.translate(Boom(400, "Your credit balance is too low to access the API"))
    assert gemini_utils.is_depleted(err) and not gemini_utils.is_retriable(err)


def test_no_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv(cc.KEY_ENV, raising=False)
    with pytest.raises(cc.ClaudeError, match="ANTHROPIC_API_KEY"):
        cc.ClaudeClient().models.generate_content(model=SONNET, contents="hi")
    assert not cc.available()


def test_tally_prices_each_call_and_nests_cleanly():
    c, _ = client(message(text("a")), message(text("b")))
    prices = spend.prices()[SONNET]
    with cc.tally() as bill:
        c.models.generate_content(model=SONNET, contents="1")
        c.models.generate_content(model=SONNET, contents="2")
    assert bill.calls == 2 and bill.unpriced == 0
    assert bill.usd == pytest.approx(2 * (100 * prices['input'] + 50 * prices['output']) / 1_000_000)
    c2, _ = client(message(text("c")))
    c2.models.generate_content(model=SONNET, contents="3")     # outside: not counted
    assert bill.calls == 2


def test_unknown_model_counts_as_unpriced():
    c, _ = client(message(text("a")))
    with cc.tally() as bill:
        c.models.generate_content(model="claude-mystery-9", contents="1")
    assert bill.calls == 1 and bill.unpriced == 1 and bill.usd == 0


def test_stream_yields_text_then_a_closing_chunk_with_the_rest():
    final = message(text("hello"), tool_use("t9", "look", q="x"))
    c, _ = client(final, deltas=["hel", "lo"])
    chunks = list(c.models.generate_content_stream(model=SONNET, contents="hi"))
    assert [ch.candidates[0].content.parts[0].text for ch in chunks[:2]] == ["hel", "lo"]
    last = chunks[-1]
    assert last.function_calls and last.function_calls[0].id == "t9"
    assert last.usage_metadata.prompt_token_count == 100
    assert all(p.text is None for p in last.candidates[0].content.parts)


def test_generate_with_retry_dispatches_a_claude_model_to_the_facade(monkeypatch):
    c, sdk = client(message(text("from claude")))
    monkeypatch.setattr(cc, "get", lambda: c)

    class Gemini:                                           # must never be touched
        class models:
            @staticmethod
            def generate_content(**kw):
                raise AssertionError("a claude model went to gemini")

    r = gemini_utils.generate_with_retry(Gemini, SONNET, "hi", fallbacks=[], stage="t", raw=True)
    assert r.text == "from claude" and sdk.sent
