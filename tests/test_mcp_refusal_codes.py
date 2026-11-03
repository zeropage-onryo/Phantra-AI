"""Every refusal a connector tool gives carries a code (QA 2026-11-02 K9,
change 17).

Until then every refusal -- the reference gate, a bad renderer, an unknown
id, a missing consent -- arrived as a plain tool error, a sentence and
nothing else, so a client could not tell `needs_reference` from an outage
without reading English. Now an error result carries
`structuredContent = {"error": {"code", "message"}}` beside the same
sentence, on all three servers; a crash is `server_error`.

These go through a real client session, because the code rides on the
result the SDK builds, not on the exception a direct `call_tool` raises.
"""
from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from src import mcp_server, preprod, projects
from src.failures import Refusal

SCENE = ("(0-3s) A rider in a red jacket crosses a wet street at dusk, neon in the "
         "puddles. (3-6s) She stops at the curb and looks back over her shoulder, "
         "rain on the lens, slow push in.")


@pytest.fixture
def tmp_db(pg):
    preprod.init(pg)
    return pg


def _call(server, name, args):
    async def go():
        async with Client(server) as c:
            return await c.call_tool(name, args)
    return asyncio.run(go())


def _error(result):
    assert result.is_error, result
    return (result.structured_content or {}).get("error")


def _servers(dsn):
    ok = lambda *a, **k: {}          # noqa: E731
    return {
        "studio": mcp_server.build_server(dsn=dsn),
        "render": mcp_server.build_server(dsn=dsn, listed=True, approve_render=ok,
                                          approve_keyframes=ok),
        "claude": mcp_server.build_server(dsn=dsn, listed="claude"),
    }


def test_a_refusal_is_still_a_value_error_with_its_sentence():
    """Every caller that catches ValueError, and every test that matches
    the sentence, keeps working."""
    r = Refusal("not_found", "no scene 7")
    assert isinstance(r, ValueError) and str(r) == "no scene 7" and r.code == "not_found"


def test_an_unknown_id_is_not_found_on_every_server(tmp_db):
    projects.init(tmp_db)
    for listing, server in _servers(tmp_db).items():
        err = _error(_call(server, "project", {"project_id": 999999}))
        assert err == {"code": "not_found", "message": err["message"]}, listing
        assert "no project 999999" in err["message"], listing


def test_the_reference_gate_is_needs_reference(tmp_db, monkeypatch):
    """A scene with no photograph cannot be priced: the gate is the one
    refusal a client most needs to branch on (`add_element`, then write
    the scene again)."""
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    sid = preprod.save_concept({"title": "QA", "shots": [{"n": 1, "prompt": SCENE,
                                                          "seconds": 6, "refs": []}]},
                               dsn=tmp_db, account_id=None)
    err = _error(_call(_servers(tmp_db)["render"], "quote", {"scene_id": sid}))
    assert err["code"] == "needs_reference"
    assert "add_element" in err["message"]


def test_a_tool_this_server_does_not_have_is_unknown_tool(tmp_db):
    err = _error(_call(_servers(tmp_db)["studio"], "quote", {"scene_id": 1}))
    assert err["code"] == "unknown_tool"


def test_the_sentence_is_unchanged_beside_the_code(tmp_db):
    projects.init(tmp_db)
    result = _call(_servers(tmp_db)["render"], "project", {"project_id": 999999})
    assert result.content[0].text == _error(result)["message"]


def test_bad_arguments_are_invalid_arguments(tmp_db):
    err = _error(_call(_servers(tmp_db)["render"], "project", {"project_id": "seven"}))
    assert err["code"] == "invalid_arguments"


def test_a_crash_is_server_error_and_says_nothing_of_the_server(tmp_db, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("password=hunter2 at db.internal")
    monkeypatch.setattr(mcp_server, "_project_or_refuse", boom)
    err = _error(_call(_servers(tmp_db)["render"], "project", {"project_id": 1}))
    assert err["code"] == "server_error"
    assert "hunter2" not in err["message"] and "db.internal" not in err["message"]


def test_each_kind_of_no_has_its_code():
    """`Refused` (this server does not do that at all) has its own code,
    so a client stops asking instead of fixing its arguments; a plain
    ValueError is still a caller error."""
    assert mcp_server.refusal_code(mcp_server.Refused("no")) == "not_available"
    assert mcp_server.refusal_code(ValueError("bad")) == "invalid_request"
    assert mcp_server.refusal_code(Refusal("needs_consent", "ask")) == "needs_consent"


def test_a_missing_consent_is_needs_consent():
    from src import dubbing, talking_photo
    for check in (dubbing.check_consent, talking_photo.check_consent):
        with pytest.raises(Refusal) as no:
            check(None)
        assert no.value.code == "needs_consent"
