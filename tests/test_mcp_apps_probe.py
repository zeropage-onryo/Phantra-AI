"""
The MCP Apps probe (2026-10-11, src/mcp_apps_probe.py): one flag-gated
diagnostic that says whether the Claude client a person uses renders a UI
panel for this server.

What is guarded here is the half a test CAN guard: that the probe is off
unless asked for and never on a served surface; that, on, the wire carries
everything a host needs to mount the view (the capability, the tool's and
the result's `_meta` in both spellings, the resource's mime and CSP); that
the view is self-contained; and that the report reads the client's steps
back correctly, including the failure it was built to recognise --
advertised, read, never mounted. That the view really completes the
handshake was run by hand against the official AppBridge host (the task
doc has the record); a browser is not something this suite has.
"""

import asyncio
import hashlib
import json
import re

import pytest
from mcp import Client
from mcp.client.extension import advertise
from mcp.types import Implementation

from src import mcp_apps_probe as probe
from src import mcp_server

NOWHERE = "postgresql://127.0.0.1:1/none"       # the probe never opens the database
UI = "io.modelcontextprotocol/ui"
MIME = "text/html;profile=mcp-app"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(probe.ENV, "1")


def _studio():
    return mcp_server.build_server(dsn=NOWHERE, surface="studio")


def _client(server, *, apps=True, name="Claude", version="1.2.3"):
    ext = [advertise(UI, {"mimeTypes": [MIME]})] if apps else None
    return Client(server, client_info=Implementation(name=name, version=version), extensions=ext)


def _run(coro):
    return asyncio.run(coro)


def _names(server):
    return {t.name for t in _run(server.list_tools())}


# --------------------------------------------------------------------------
# off unless asked for, and only ever on the studio (stdio) surface
# --------------------------------------------------------------------------

def test_off_by_default_the_studio_server_is_unchanged():
    assert not probe.enabled()
    server = _studio()

    async def go():
        async with _client(server) as c:
            caps = c.server_capabilities.model_dump(exclude_none=True, by_alias=True)
            return caps.get("extensions"), (await c.list_resources()).resources

    extensions, resources = _run(go())
    assert extensions is None and resources == []
    assert not {n for n in _names(server) if n.startswith("ui_")}


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "on", " 2 "])
def test_only_a_literal_1_turns_it_on(monkeypatch, value):
    monkeypatch.setenv(probe.ENV, value)
    assert not probe.enabled()


def test_on_it_adds_three_tools_and_nothing_to_the_product(on):
    added = {probe.TOOL, probe.PING_TOOL, probe.REPORT_TOOL}
    assert added <= _names(_studio())
    # a test rig, not a studio tool: never in the published tables
    assert not added & set(mcp_server.STUDIO_TOOLS)
    assert not added & set(mcp_server.TITLES)
    assert not added & set(mcp_server.LISTED_TOOLS)


def test_the_flag_never_reaches_a_served_surface(on, pg, monkeypatch):
    """What the HTTP mount serves: the studio surface without local files
    to the operator's key (it was the board until 2026-10-11, when the
    board went), and the listed server to anybody signed in. A flag in one
    person's `.env` must not put a diagnostic on either -- the probe is
    for the desktop's own pipe."""
    from src import preprod, scout
    preprod.init(pg)
    scout.init(pg)
    monkeypatch.setenv(mcp_server.ENGINE_ENV, "1")
    for kw in ({"surface": "studio", "local_files": False}, {"listed": True}):
        server = mcp_server.build_server(dsn=pg, **kw)
        assert not {n for n in _names(server) if n.startswith("ui_")}, kw
        assert _run(server.list_resources()) == []


# --------------------------------------------------------------------------
# on: everything a host needs to mount the view is on the wire
# --------------------------------------------------------------------------

def test_the_wire_carries_what_a_host_needs(on):
    uri = probe.view_uri()

    async def go():
        async with _client(_studio()) as c:
            caps = c.server_capabilities.model_dump(exclude_none=True, by_alias=True)
            tools = {t.name: t for t in (await c.list_tools()).tools}
            called = await c.call_tool(probe.TOOL, {})
            read = await c.read_resource(uri)
            listed = (await c.list_resources()).resources
            return caps, tools, called, read, listed

    caps, tools, called, read, listed = _run(go())
    # 1. the server declares the extension at initialize
    assert UI in caps["extensions"]
    # 2. the tool names its view, in the nested spelling and the flat one
    assert tools[probe.TOOL].meta["ui"]["resourceUri"] == uri
    assert tools[probe.TOOL].meta["ui/resourceUri"] == uri
    # ...the view's own tool is for the view, not the model
    assert tools[probe.PING_TOOL].meta["ui"]["visibility"] == ["app"]
    # ...and the report is a plain tool: it must answer on a client with no panels
    assert tools[probe.REPORT_TOOL].meta is None
    # 3. the RESULT names the view too, both spellings (some hosts read it only here)
    assert called.meta["ui"]["resourceUri"] == uri and called.meta["ui/resourceUri"] == uri
    assert "advertised MCP Apps" in called.content[0].text and not called.is_error
    assert called.structured_content["client"]["advertised"] is True
    # 4. the resource: the app mime type, and a CSP with EMPTY lists (not absent)
    (item,) = read.contents
    assert item.mime_type == MIME and item.text == probe.VIEW_HTML
    assert item.meta == {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}}}
    assert [str(r.uri) for r in listed] == [uri] and listed[0].mime_type == MIME


def test_the_uri_carries_the_views_hash():
    """Hosts cache a view against its URI: a changed view must be a new one."""
    digest = hashlib.sha256(probe.VIEW_HTML.encode()).hexdigest()[:10]
    assert probe.view_uri() == f"ui://zeropage/probe-{digest}.html"


def test_the_view_is_self_contained_and_speaks_the_handshake():
    html = probe.VIEW_HTML
    # nothing is fetched: no CDN, no module import, no external anything --
    # the declared CSP has empty lists, so one remote URL would be a blank panel
    assert not re.search(r"https?://", html)
    assert not re.search(r"<script[^>]+src=|<link\b|@import|\bimport\s*\(|<img\b|url\(", html)
    assert 'type="module"' not in html
    # the handshake, as the spec names it
    for needle in ('"ui/initialize"', '"ui/notifications/initialized"',
                   '"ui/notifications/size-changed"', '"ui/notifications/tool-input"',
                   '"ui/notifications/tool-result"', '"tools/call"',
                   "appInfo", "appCapabilities", "protocolVersion",
                   f'"{probe.PROTOCOL_VERSION}"', f'"{probe.PING_TOOL}"'):
        assert needle in html, needle
    # the placeholders were filled, and only messages from the host are heard
    assert "__PROTOCOL__" not in html and "__PING__" not in html
    assert "event.source !== window.parent" in html
    # `initialized` is sent even when the host's answer never comes
    assert "handshake-timeout" in html and "setTimeout" in html


# --------------------------------------------------------------------------
# the report: how far the client got
# --------------------------------------------------------------------------

async def _levels(steps, *, apps=True):
    async with _client(_studio(), apps=apps) as c:
        for step in steps:
            if step == "call":
                await c.call_tool(probe.TOOL, {})
            elif step == "read":
                await c.read_resource(probe.view_uri())
            else:
                await c.call_tool(probe.PING_TOOL, {"stage": step, "detail": "Claude 1 / x / inline"})
        res = await c.call_tool(probe.REPORT_TOOL, {})
        return json.loads(res.content[0].text)


def test_before_the_probe_is_called_the_report_says_so(on):
    out = _run(_levels([]))
    assert out["summary"].startswith("ui_probe has not been called yet")
    assert out["levels"]["advertised"] is True          # known from the report's own call
    assert out["probe_calls"] == 0 and out["view"] == probe.view_uri()


def test_a_client_without_the_extension(on):
    out = _run(_levels(["call"], apps=False))
    assert out["levels"] == {"advertised": False, "read": False, "handshake": False,
                             "result": False, "bridge": False, "clicked": False}
    assert "did not advertise MCP Apps" in out["summary"] and "Claude 1.2.3" in out["summary"]
    assert out["client"]["extensions"] == []


def test_advertised_and_read_but_never_mounted_is_named(on):
    """The failure the probe exists to catch: the host knows about the view
    and no panel ever runs."""
    out = _run(_levels(["call", "read"]))
    assert out["levels"]["advertised"] and out["levels"]["read"]
    assert not out["levels"]["handshake"] and not out["levels"]["bridge"]
    assert "never called back" in out["summary"] and "claude-ai-mcp#165" in out["summary"]
    assert out["resource_reads"] == 1 and out["view_reports"] == []


def test_advertised_but_never_read(on):
    out = _run(_levels(["call"]))
    assert "never read the view" in out["summary"]


def test_a_view_that_ran_without_a_handshake(on):
    out = _run(_levels(["call", "read", "handshake-timeout", "tool-result"]))
    assert out["levels"]["bridge"] and out["levels"]["result"] and not out["levels"]["handshake"]
    assert "never answered ui/initialize" in out["summary"]


def test_the_whole_way_and_the_button(on):
    out = _run(_levels(["call", "read", "handshake", "tool-input", "tool-result", "bridge"]))
    assert all(out["levels"][k] for k in ("advertised", "read", "handshake", "result", "bridge"))
    assert not out["levels"]["clicked"]
    assert out["summary"].startswith("MCP Apps WORKS in Claude 1.2.3")
    assert "Press the panel's button" in out["summary"]
    assert out["host"] == "Claude 1 / x / inline"
    assert [v["stage"] for v in out["view_reports"]] == ["handshake", "tool-input",
                                                         "tool-result", "bridge"]
    out = _run(_levels(["call", "read", "handshake", "tool-result", "button"]))
    assert out["levels"]["clicked"] and "The button was pressed too." in out["summary"]


def test_each_server_has_its_own_log(on):
    """Claude Desktop starts the stdio server twice; one process's steps
    must never be read as another's."""
    _, a = probe.build()
    _, b = probe.build()
    a.called()
    a.ping("handshake")
    assert a.report()["levels"]["bridge"] and not b.report()["levels"]["bridge"]
    assert b.report()["probe_calls"] == 0


def test_a_ping_is_bounded():
    log = probe.Log()
    log.ping("x" * 500, "y" * 5000)
    (seen,) = log.report()["view_reports"]
    assert len(seen["stage"]) == 40 and len(seen["detail"]) == 300
