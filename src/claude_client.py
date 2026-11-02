"""A Gemini-shaped door onto the Anthropic Messages API (2026-11-02).

WHY THIS IS A FACADE AND NOT A SECOND CODE PATH. Every brain-driven caller in
this repo (the composer's Guide and its tool loop, the scene writer, the
timeline planner, voice-over, the motion ad, the cut agent) builds Gemini's own
types -- `types.Content`, `types.Part`, `types.FunctionDeclaration`,
`GenerateContentConfig` -- and reads Gemini's response (`.text`,
`.function_calls`, `.candidates[0].content`, `.usage_metadata`). Rewriting
each of them for a second SDK is how two copies of one loop drift apart.
`gemini_utils.generate_with_retry` already takes its `client` as an argument
and already treats a client as "something with `.models.generate_content`",
so a `claude-*` model id is answered by THIS object and nothing upstream
changes: the same retry loop, the same meter row, the same tool loop.

WHAT IT TRANSLATES.
- contents: text, inline images, a model turn's function calls and the next
  turn's function responses (matched to Anthropic's `tool_use` ids by order and
  name, because Gemini's function response carries no id).
- config: `system_instruction`, `tools` (FunctionDeclaration ->
  input_schema), `response_mime_type=application/json` + `response_json_schema`
  (-> `output_config.format`) and `thinking_config.thinking_level` (-> adaptive
  thinking at that effort; the manual `budget_tokens` form is a 400 on these
  models).
- the answer: a real `types.GenerateContentResponse`, so a caller cannot tell
  it from Gemini's. Thinking blocks ride as `thought` parts with their
  signature, because a tool loop must hand them back unmodified.
- usage: Anthropic's four counts onto Gemini's names (`prompt_token_count`
  INCLUDES the cache reads, as Google's does, so `spend.estimate_cost` prices
  the slice at the cached rate). Thinking is already inside `output_tokens`,
  so `thoughts_token_count` is left empty rather than counted twice.

WHAT IT DOES NOT DO. No silent fallback to Gemini (the brain's `fallbacks` is
empty; a failed Claude turn raises, the way the reasoning tier does). No
`temperature`. Interleaved thinking between two tool calls of ONE response is
handed back thinking-first (the order the API itself produces for a single
response with parallel tool calls).

THE TALLY. `tally()` is the turn's own bill: every call made inside it adds its
estimated provider USD, priced off `spend.prices()` from the usage the API
reported. It does not read the `llm_calls` row because that meter never raises
and may write nothing; the money path must not depend on it.
"""
from __future__ import annotations

import base64
import contextvars
import json
import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from google.genai import types

KEY_ENV = "ANTHROPIC_API_KEY"
MAX_TOKENS_ENV = "PHANTRA_CLAUDE_MAX_TOKENS"
DEFAULT_MAX_TOKENS = 16000
TIMEOUT_S = 180.0

# what the API accepts as a picture; anything else is said, not sent
IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")
# thinking_level -> the effort the adaptive form takes
EFFORT = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}
# HTTP statuses worth waiting out: rate limit, server errors, "overloaded" (529)
RETRIABLE_STATUS = (429, 500, 502, 503, 504, 529)


class ClaudeError(RuntimeError):
    """A failed call, worded so `gemini_utils.is_retriable` / `is_depleted`
    read it the way they read Google's: a busy or limited API says
    "UNAVAILABLE" (and "retry in Ns" when the API named a cooldown); an empty
    prepaid balance keeps Anthropic's own words, which are in
    `gemini_utils.DEPLETED_MARKERS`."""


def is_claude(model) -> bool:
    return str(model or "").startswith("claude-")


def available() -> bool:
    """Whether this install can call Claude at all (a key is set)."""
    return bool((os.environ.get(KEY_ENV) or "").strip())


# --- the turn's bill -------------------------------------------------------

_tally: contextvars.ContextVar[Optional["Tally"]] = contextvars.ContextVar(
    "claude_tally", default=None)


class Tally:
    """Provider USD spent on Claude inside one `tally()` block."""

    def __init__(self) -> None:
        self.usd = 0.0
        self.calls = 0
        self.unpriced = 0

    def add(self, model: str, usage: dict) -> None:
        from . import spend
        self.calls += 1
        cost = spend.estimate_cost(
            model,
            prompt_tokens=usage.get("prompt") or 0,
            output_tokens=usage.get("output") or 0,
            cached_tokens=usage.get("cached") or 0)
        if cost is None:
            self.unpriced += 1
        else:
            self.usd += float(cost)


@contextmanager
def tally() -> Iterator[Tally]:
    """Everything Claude costs inside the block, on the thread that opened it
    (a ContextVar does not cross into a thread someone else starts)."""
    mine = Tally()
    token = _tally.set(mine)
    try:
        yield mine
    finally:
        _tally.reset(token)


# --- schemas ---------------------------------------------------------------

# Keys Anthropic's structured output refuses (400). Gemini accepts them, and a
# pydantic model emits them for any bounded field.
_UNSUPPORTED = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "multipleOf", "minLength", "maxLength", "maxItems", "uniqueItems",
                "minProperties", "maxProperties")


def close_schema(schema: Any) -> Any:
    """A copy of a JSON schema the structured-output endpoint will take:
    every object closed (`additionalProperties: false`), the bounds it does
    not support dropped, `minItems` kept only at 0 or 1."""
    if isinstance(schema, list):
        return [close_schema(v) for v in schema]
    if not isinstance(schema, dict):
        return schema
    out = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED:
            continue
        if key == "minItems" and value not in (0, 1):
            continue
        out[key] = close_schema(value)
    if out.get("type") == "object" or "properties" in out:
        out["additionalProperties"] = False
    return out


def _schema_of(decl) -> dict:
    raw = getattr(decl, "parameters_json_schema", None)
    if isinstance(raw, dict) and raw:
        schema = dict(raw)
    elif getattr(decl, "parameters", None) is not None:
        schema = _lower_types(decl.parameters.model_dump(exclude_none=True, mode="json"))
    else:
        schema = {}
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return schema


def _lower_types(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: (v.lower() if k == "type" and isinstance(v, str) else _lower_types(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [_lower_types(v) for v in node]
    return node


# --- contents -> messages ---------------------------------------------------

def _text_of(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, types.Part):
        return value.text or ""
    if isinstance(value, types.Content):
        return "\n".join(p.text for p in value.parts or [] if p.text)
    if isinstance(value, (list, tuple)):
        return "\n".join(t for t in (_text_of(v) for v in value) if t)
    return str(value)


def _as_contents(contents) -> list:
    if isinstance(contents, str):
        return [types.Content(role="user", parts=[types.Part.from_text(text=contents)])]
    if isinstance(contents, types.Content):
        return [contents]
    out, loose = [], []

    def flush():
        if loose:
            out.append(types.Content(role="user", parts=list(loose)))
            loose.clear()

    for item in contents or []:
        if isinstance(item, types.Content):
            flush()
            out.append(item)
        elif isinstance(item, str):
            loose.append(types.Part.from_text(text=item))
        elif isinstance(item, types.Part):
            loose.append(item)
        else:
            raise ClaudeError(f"cannot send a {type(item).__name__} to Claude")
    flush()
    return out


def _result_text(response) -> str:
    if isinstance(response, dict) and set(response) == {"result"} \
            and isinstance(response["result"], str):
        return response["result"]
    return json.dumps(response, default=str)


def to_messages(contents) -> list[dict]:
    """Gemini `contents` -> Anthropic `messages`. Consecutive turns of one
    role are merged (the API wants them alternating), a user turn's tool
    results come first, and a model turn's thinking comes first."""
    messages: list[dict] = []
    pending: list[tuple[str, str]] = []      # (tool_use id, name) still owed a result

    for content in _as_contents(contents):
        assistant = content.role == "model"
        thinking, body, results = [], [], []
        if assistant:
            pending = []
        for part in content.parts or []:
            if part.function_call is not None:
                fc = part.function_call
                call_id = fc.id or f"toolu_{len(messages):03d}_{len(body):02d}"
                pending.append((call_id, fc.name))
                body.append({"type": "tool_use", "id": call_id, "name": fc.name,
                             "input": dict(fc.args or {})})
            elif part.function_response is not None:
                fr = part.function_response
                match = next((i for i, (cid, name) in enumerate(pending)
                              if (fr.id and cid == fr.id) or (not fr.id and name == fr.name)),
                             None)
                if match is None:
                    raise ClaudeError(f"a function response for {fr.name!r} answers no tool call")
                call_id, _ = pending.pop(match)
                text = _result_text(fr.response)
                block = {"type": "tool_result", "tool_use_id": call_id, "content": text}
                if text.startswith("error:"):
                    block["is_error"] = True
                results.append(block)
            elif part.inline_data is not None:
                blob = part.inline_data
                mime = (blob.mime_type or "").lower()
                if mime in IMAGE_TYPES and blob.data:
                    body.append({"type": "image", "source": {
                        "type": "base64", "media_type": mime,
                        "data": base64.standard_b64encode(blob.data).decode("ascii")}})
                else:
                    body.append({"type": "text", "text":
                                 f"[an image in a format Claude cannot read ({mime or 'unknown'}) "
                                 "was left out]"})
            elif part.thought:
                sig = (part.thought_signature or b"").decode("utf-8", "ignore")
                if part.text is None:
                    thinking.append({"type": "redacted_thinking", "data": sig})
                else:
                    thinking.append({"type": "thinking", "thinking": part.text, "signature": sig})
            elif part.text:
                if body and body[-1]["type"] == "text":
                    body[-1]["text"] += part.text          # streamed deltas arrive as many parts
                else:
                    body.append({"type": "text", "text": part.text})
        blocks = thinking + body if assistant else results + body
        if not blocks:
            continue
        role = "assistant" if assistant else "user"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"].extend(blocks)
            if role == "user":                              # results stay first after a merge
                messages[-1]["content"].sort(key=lambda b: b["type"] != "tool_result")
        else:
            messages.append({"role": role, "content": blocks})
    return messages


# --- config -> request ------------------------------------------------------

def to_request(model: str, contents, config=None) -> dict:
    kwargs: dict = {"model": model, "messages": to_messages(contents),
                    "max_tokens": _max_tokens(config)}
    system = _text_of(getattr(config, "system_instruction", None)).strip() if config else ""
    if system:
        # a breakpoint at the end of the system block caches the tools and the
        # instructions together: a tool loop sends them again every round
        kwargs["system"] = [{"type": "text", "text": system,
                             "cache_control": {"type": "ephemeral"}}]
    tools = []
    for tool in (getattr(config, "tools", None) or []):
        for decl in getattr(tool, "function_declarations", None) or []:
            tools.append({"name": decl.name, "description": decl.description or "",
                          "input_schema": _schema_of(decl)})
    if tools:
        kwargs["tools"] = tools
    output: dict = {}
    if config is not None and getattr(config, "response_mime_type", None) == "application/json":
        schema = getattr(config, "response_json_schema", None) or getattr(config, "response_schema", None)
        if isinstance(schema, type) and hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()
        if isinstance(schema, dict) and schema:
            output["format"] = {"type": "json_schema", "schema": close_schema(schema)}
    level = getattr(getattr(config, "thinking_config", None), "thinking_level", None)
    if level is not None:
        name = str(getattr(level, "name", level)).upper().rsplit(".", 1)[-1]
        if name in EFFORT:
            kwargs["thinking"] = {"type": "adaptive"}
            output["effort"] = EFFORT[name]
    if output:
        kwargs["output_config"] = output
    return kwargs


def _max_tokens(config) -> int:
    asked = getattr(config, "max_output_tokens", None) if config is not None else None
    if asked:
        return int(asked)
    try:
        return max(1024, int(os.environ.get(MAX_TOKENS_ENV) or DEFAULT_MAX_TOKENS))
    except ValueError:
        return DEFAULT_MAX_TOKENS


# --- message -> response ----------------------------------------------------

def _usage(message) -> dict:
    u = getattr(message, "usage", None)

    def n(name):
        try:
            return int(getattr(u, name, 0) or 0)
        except (TypeError, ValueError):
            return 0

    cached = n("cache_read_input_tokens")
    return {"prompt": n("input_tokens") + cached + n("cache_creation_input_tokens"),
            "output": n("output_tokens"), "cached": cached}


def _finish(message):
    reason = getattr(message, "stop_reason", None)
    if reason == "max_tokens":
        return types.FinishReason.MAX_TOKENS
    if reason == "refusal":
        return types.FinishReason.SAFETY
    return types.FinishReason.STOP


def from_message(message) -> types.GenerateContentResponse:
    parts = []
    for block in getattr(message, "content", None) or []:
        kind = getattr(block, "type", None)
        if kind == "text":
            parts.append(types.Part(text=block.text))
        elif kind == "thinking":
            parts.append(types.Part(text=block.thinking, thought=True,
                                    thought_signature=(block.signature or "").encode("utf-8")))
        elif kind == "redacted_thinking":
            parts.append(types.Part(thought=True, thought_signature=(block.data or "").encode("utf-8")))
        elif kind == "tool_use":
            parts.append(types.Part(function_call=types.FunctionCall(
                id=block.id, name=block.name, args=dict(block.input or {}))))
    usage = _usage(message)
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts),
                                    finish_reason=_finish(message))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=usage["prompt"], candidates_token_count=usage["output"],
            cached_content_token_count=usage["cached"] or None),
        model_version=getattr(message, "model", None))


# --- errors -----------------------------------------------------------------

def translate(exc: BaseException) -> ClaudeError:
    """An SDK exception -> a ClaudeError worded for gemini_utils' classifiers."""
    if isinstance(exc, ClaudeError):
        return exc
    status = getattr(exc, "status_code", None)
    detail = str(getattr(exc, "message", None) or exc)
    name = type(exc).__name__
    if status in RETRIABLE_STATUS or name in ("APIConnectionError", "APITimeoutError"):
        wait = ""
        headers = getattr(getattr(exc, "response", None), "headers", None)
        try:
            seconds = float(headers.get("retry-after")) if headers is not None else None
        except (TypeError, ValueError):
            seconds = None
        if seconds is not None:
            wait = f" (retry in {seconds:g}s)"
        return ClaudeError(f"UNAVAILABLE: Claude {status or name}: {detail}{wait}")
    return ClaudeError(f"Claude {status or name}: {detail}")


# --- the client -------------------------------------------------------------

class _Models:
    def __init__(self, owner: "ClaudeClient") -> None:
        self._owner = owner

    def generate_content(self, *, model, contents, config=None):
        sdk = self._owner.sdk()
        request = to_request(model, contents, config)
        try:
            message = sdk.messages.create(**request)
        except Exception as exc:                      # noqa: BLE001 -- reworded, not hidden
            raise translate(exc) from exc
        return self._owner.finish(model, message)

    def generate_content_stream(self, *, model, contents, config=None):
        """Text arrives as it is written; the closing chunk carries the rest
        (thinking, tool calls, usage), which is what `_streamed` expects."""
        sdk = self._owner.sdk()
        request = to_request(model, contents, config)
        try:
            with sdk.messages.stream(**request) as stream:
                for delta in stream.text_stream:
                    yield types.GenerateContentResponse(candidates=[types.Candidate(
                        content=types.Content(role="model",
                                              parts=[types.Part(text=delta)]))])
                message = stream.get_final_message()
        except Exception as exc:                      # noqa: BLE001
            raise translate(exc) from exc
        done = self._owner.finish(model, message)
        candidate = done.candidates[0]
        rest = [p for p in candidate.content.parts if not (p.text and not p.thought)]
        yield types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(role="model", parts=rest),
                                        finish_reason=candidate.finish_reason)],
            usage_metadata=done.usage_metadata, model_version=done.model_version)


class ClaudeClient:
    """`client.models.generate_content(...)`, answered by Claude."""

    def __init__(self, sdk=None) -> None:
        self._sdk = sdk
        self.models = _Models(self)

    def sdk(self):
        if self._sdk is None:
            key = (os.environ.get(KEY_ENV) or "").strip()
            if not key:
                raise ClaudeError(f"{KEY_ENV} is not set -- a Claude brain cannot answer")
            import anthropic
            # max_retries=0: gemini_utils.generate_with_retry is the ONE retry policy
            self._sdk = anthropic.Anthropic(api_key=key, max_retries=0, timeout=TIMEOUT_S)
        return self._sdk

    def finish(self, model, message):
        """Bill the call to the open tally, then shape the answer."""
        mine = _tally.get()
        if mine is not None:
            try:
                mine.add(model, _usage(message))
            except Exception:                         # noqa: BLE001 -- see Tally.add
                mine.unpriced += 1
        return from_message(message)


_client: Optional[ClaudeClient] = None


def get() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client

