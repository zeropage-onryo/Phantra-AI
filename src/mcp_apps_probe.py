"""
The MCP Apps probe: does a UI panel actually render in the Claude client
this studio is used from? (2026-10-11, docs/tasks/task-mcp-studio-v2.md
step 3 + 4's gate.)

WHY A PROBE AND NOT THE VIEWER. The inline viewer and the upload drop zone
were not built, because MCP Apps could not be confirmed: the SDK supports
it (`mcp.server.apps`), Claude lists Desktop as a host, and yet open
reports (anthropics/claude-ai-mcp#165, modelcontextprotocol/ext-apps#671)
describe the capability negotiated, the resource read, and no panel -- a
local stdio server in Claude Desktop among them. It cannot be tested from
inside the Desktop app, whose restart ends the session doing the testing.
So this is the smallest thing that settles it, for Mike to run.

OFF unless `PHANTRA_MCP_APPS_PROBE=1` (the checkout's `.env` is enough:
the stdio entry point loads it). Off, the studio server is byte for byte
what it was: no extension is advertised and no tool is added. On, the
STUDIO surface (stdio) gains three diagnostics that are deliberately not
in TITLES / STUDIO_TOOLS -- they are a test rig, not part of the product:

- `ui_probe`        bound to a `ui://` view. If MCP Apps works, a panel
                    appears with the call.
- `ui_probe_ping`   visible to the VIEW only; the panel calls it through
                    the host, which is how the server learns the panel ran.
- `ui_probe_report` how far it got, from the server's side.

A BLANK PANEL STILL ANSWERS THE QUESTION, because the server records each
step the client takes and `ui_probe_report` reads them back in order:

1. advertised -- the client's `initialize` carried the extension
2. read       -- the host fetched the `ui://` resource
3. handshake  -- the view's script ran and `ui/initialize` was answered
4. result     -- the view was handed the tool's result
5. bridge     -- a `tools/call` from the view reached this server
(6. clicked   -- the person pressed the panel's button)

1 + 2 without 3 is the failure those reports describe: the host knows
about the view and never mounts it. Nothing at all is a client that does
not speak the extension.

THE VIEW follows the fixes people needed to get a panel on screen (the
checklist in ext-apps#671), because a probe that fails for its own reasons
would say "no" falsely: it is self-contained (no CDN -- the handshake is
written out by hand from the spec, 2026-01-26); `ui/notifications/
initialized` is sent whether or not the host's reply is recognised; the
`ui://` URI carries a content hash; `_meta.ui.resourceUri` rides on the
tool RESULT as well as the tool, in both spellings; the resource carries
`_meta.ui.csp` with empty lists. The view was run against the official
`AppBridge` host from @modelcontextprotocol/ext-apps before it was shipped
(see the task doc), so a "no" from a real client is the client's.

Nothing here spends, reads the board, or touches the database. The log is
in this process's memory and goes when the server stops.
"""
import hashlib
import os
import threading
import time
from typing import Any, Optional

ENV = "PHANTRA_MCP_APPS_PROBE"
PROTOCOL_VERSION = "2026-01-26"          # the MCP Apps spec the view speaks
TOOL = "ui_probe"
PING_TOOL = "ui_probe_ping"
REPORT_TOOL = "ui_probe_report"
STAGES = ("handshake", "handshake-timeout", "tool-input", "tool-result", "bridge", "button")

VIEW_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phantra · MCP Apps probe</title>
<style>
  :root { color-scheme: light dark; }
  html, body { margin: 0; padding: 0; background: transparent; }
  body { font: 14px/1.45 var(--font-sans, -apple-system, "Segoe UI", system-ui, sans-serif);
         color: var(--color-text-primary, light-dark(#171717, #f5f5f5)); }
  .card { margin: 0; padding: 14px 16px; border-radius: 12px;
          border: 1px solid light-dark(#d9d9d9, #3a3a3a);
          background: var(--color-background-secondary, light-dark(#fafafa, #1f1f1f)); }
  h1 { font-size: 15px; margin: 0 0 2px; }
  .sub { margin: 0 0 10px; opacity: .7; font-size: 12px; }
  ul { list-style: none; margin: 0 0 10px; padding: 0; }
  li { display: flex; gap: 8px; align-items: baseline; padding: 2px 0; }
  .mark { width: 1.2em; text-align: center; font-weight: 700; }
  .ok .mark { color: #1a9d55; } .no .mark { color: #d93025; } .wait .mark { opacity: .45; }
  .note { opacity: .7; font-size: 12px; }
  button { font: inherit; padding: 6px 12px; border-radius: 8px; cursor: pointer;
           border: 1px solid light-dark(#bdbdbd, #555); background: light-dark(#fff, #2a2a2a);
           color: inherit; }
  button:disabled { opacity: .5; cursor: default; }
  #verdict { font-weight: 600; margin: 8px 0 0; }
</style>
</head>
<body>
<div class="card" id="card">
  <h1>Phantra · MCP Apps probe</h1>
  <p class="sub">If you can read this, a panel rendered in this client.</p>
  <ul>
    <li id="s-loaded" class="ok"><span class="mark">&#10003;</span>
      <span>View loaded and its script is running</span></li>
    <li id="s-handshake" class="wait"><span class="mark">&middot;</span>
      <span>Handshake with the host <span class="note" id="n-handshake">(ui/initialize)</span></span></li>
    <li id="s-input" class="wait"><span class="mark">&middot;</span>
      <span>Tool input received <span class="note" id="n-input"></span></span></li>
    <li id="s-result" class="wait"><span class="mark">&middot;</span>
      <span>Tool result received <span class="note" id="n-result"></span></span></li>
    <li id="s-bridge" class="wait"><span class="mark">&middot;</span>
      <span>Server reached through the host <span class="note" id="n-bridge">(tools/call)</span></span></li>
  </ul>
  <button id="btn" disabled>Call the server from this panel</button>
  <span class="note" id="n-btn"></span>
  <p id="verdict"></p>
</div>
<script>
(function () {
  "use strict";
  var PROTOCOL = "__PROTOCOL__", PING = "__PING__";
  var nextId = 1, pending = {}, handshook = false, initializedSent = false, bridged = false;

  function el(id) { return document.getElementById(id); }
  function mark(id, state, note) {
    var li = el("s-" + id);
    li.className = state;
    li.querySelector(".mark").innerHTML =
      state === "ok" ? "&#10003;" : state === "no" ? "&#10007;" : "&middot;";
    if (note !== undefined) { var n = el("n-" + id); if (n) n.textContent = note; }
    reportSize();
  }
  function post(message) { window.parent.postMessage(message, "*"); }
  function request(method, params) {
    var id = nextId++;
    return new Promise(function (resolve, reject) {
      pending[id] = { resolve: resolve, reject: reject };
      post({ jsonrpc: "2.0", id: id, method: method, params: params });
    });
  }
  function notify(method, params) {
    var message = { jsonrpc: "2.0", method: method };
    if (params !== undefined) message.params = params;
    post(message);
  }
  function sendInitialized() {
    if (initializedSent) return;
    initializedSent = true;
    notify("ui/notifications/initialized");
    reportSize();
    // the CARD, not the document: the document is as tall as the frame
    if (window.ResizeObserver) new ResizeObserver(reportSize).observe(el("card"));
  }
  // Height only: the card fills whatever width the host gives it. Never
  // measured before the frame has a width (a view is often written into an
  // iframe that is not laid out yet), and never on an animation frame: a host
  // keeps the panel hidden until `initialized`, and a hidden frame gets none.
  var lastHeight = 0, sizeTries = 0;
  function reportSize() {
    if (!initializedSent) return;
    if (window.innerWidth < 120) {
      if (sizeTries++ < 60) setTimeout(reportSize, 50);
      return;
    }
    var h = Math.ceil(el("card").getBoundingClientRect().height) + 2;
    if (h === lastHeight) return;
    lastHeight = h;
    notify("ui/notifications/size-changed", { height: h });
  }
  // The host's theme and its style variables, when it sends them.
  function applyContext(context) {
    if (!context) return;
    var root = document.documentElement;
    if (context.theme === "light" || context.theme === "dark") root.style.colorScheme = context.theme;
    var vars = (context.styles || {}).variables || {};
    Object.keys(vars).forEach(function (name) {
      if (name.indexOf("--") === 0 && typeof vars[name] === "string") root.style.setProperty(name, vars[name]);
    });
    reportSize();
  }
  function ping(stage, detail) {
    return request("tools/call", { name: PING, arguments: { stage: stage, detail: detail || "" } })
      .then(function (result) {
        if (!bridged) { bridged = true; mark("bridge", "ok", "(tools/call answered)"); verdict(); }
        return result;
      });
  }
  function verdict() {
    var text = handshook && bridged
      ? "MCP Apps works here: the panel rendered, the host answered, and the server was reached."
      : handshook ? "The panel rendered and the host answered. Waiting on the server call..."
      : "";
    el("verdict").textContent = text;
    reportSize();
  }

  window.addEventListener("message", function (event) {
    if (event.source !== window.parent) return;
    var data = event.data;
    if (!data || data.jsonrpc !== "2.0") return;
    if (data.method === undefined) {                     // a response to one of ours
      var waiter = pending[data.id];
      if (!waiter) return;
      delete pending[data.id];
      if (data.error) waiter.reject(data.error); else waiter.resolve(data.result);
      return;
    }
    if (data.id !== undefined) {                         // a request from the host
      if (data.method === "ping" || data.method === "ui/resource-teardown") {
        post({ jsonrpc: "2.0", id: data.id, result: {} });
      } else {
        post({ jsonrpc: "2.0", id: data.id,
               error: { code: -32601, message: "Method not found: " + data.method } });
      }
      return;
    }
    if (data.method === "ui/notifications/tool-input") {
      mark("input", "ok", "(" + Object.keys((data.params || {}).arguments || {}).length + " arguments)");
      ping("tool-input").catch(function () {});
    } else if (data.method === "ui/notifications/host-context-changed") {
      applyContext(data.params);
    } else if (data.method === "ui/notifications/tool-result") {
      var content = ((data.params || {}).content || []);
      mark("result", "ok", "(" + content.length + " content block" + (content.length === 1 ? "" : "s") + ")");
      ping("tool-result").catch(function () {});
    }
  });

  el("btn").addEventListener("click", function () {
    el("n-btn").textContent = "calling...";
    ping("button", "pressed at " + new Date().toISOString())
      .then(function () { el("n-btn").textContent = "the server answered."; })
      .catch(function (e) { el("n-btn").textContent = "refused: " + ((e && e.message) || e); });
  });

  // The handshake, written out from the spec. `initialized` is sent whether
  // or not the reply is one we recognise: a host holds the frame hidden
  // until it lands, so waiting on a shape we do not know would be a deadlock.
  var answered = false;
  request("ui/initialize", {
    appInfo: { name: "phantra-mcp-apps-probe", version: "1" },
    appCapabilities: {},
    protocolVersion: PROTOCOL
  }).then(function (result) {
    answered = true; handshook = true;
    var host = (result && result.hostInfo) || {};
    var where = (host.name || "host") + (host.version ? " " + host.version : "");
    mark("handshake", "ok", "(" + where + ", " + ((result && result.protocolVersion) || "?") + ")");
    applyContext(result && result.hostContext);
    sendInitialized();
    el("btn").disabled = false;
    verdict();
    return ping("handshake", where + " / " + ((result && result.protocolVersion) || "") + " / " +
                (((result && result.hostContext) || {}).displayMode || ""));
  }).then(function () {
    return ping("bridge");
  }).catch(function (error) {
    if (!handshook) mark("handshake", "no", "(refused: " + ((error && error.message) || error) + ")");
    else mark("bridge", "no", "(tools/call refused: " + ((error && error.message) || error) + ")");
    sendInitialized();
  });
  setTimeout(function () {
    if (answered) return;
    mark("handshake", "no", "(no answer to ui/initialize after 1.5s)");
    sendInitialized();
    el("btn").disabled = false;
    ping("handshake-timeout").catch(function () {});
  }, 1500);
})();
</script>
</body>
</html>
""".replace("__PROTOCOL__", PROTOCOL_VERSION).replace("__PING__", PING_TOOL)


def view_uri() -> str:
    """`ui://phantra/probe-<hash>.html`. Hosts cache a view against its URI,
    so the hash of the HTML is in it: change the view and it is a new URI,
    never a stale copy."""
    return f"ui://phantra/probe-{hashlib.sha256(VIEW_HTML.encode()).hexdigest()[:10]}.html"


def enabled() -> bool:
    return (os.environ.get(ENV) or "").strip() == "1"


class Log:
    """What the client did, as this server saw it. In memory, one process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started = time.time()
        self.client: dict[str, Any] = {}
        self.reads: list[float] = []
        self.calls: list[float] = []
        self.pings: list[dict[str, Any]] = []

    def saw_client(self, info: dict[str, Any]) -> None:
        with self._lock:
            self.client = dict(info)

    def read(self) -> None:
        with self._lock:
            self.reads.append(time.time())

    def called(self) -> None:
        with self._lock:
            self.calls.append(time.time())

    def ping(self, stage: str, detail: str = "") -> None:
        with self._lock:
            self.pings.append({"stage": str(stage)[:40], "detail": str(detail)[:300],
                               "at": time.time()})

    def report(self) -> dict[str, Any]:
        with self._lock:
            stages = [p["stage"] for p in self.pings]
            host = next((p["detail"] for p in self.pings if p["stage"] == "handshake"), "")
            advertised = bool(self.client.get("advertised"))
            levels = {
                "advertised": advertised,
                "read": bool(self.reads),
                "handshake": "handshake" in stages,
                "result": "tool-result" in stages,
                "bridge": bool(stages),
                "clicked": "button" in stages,
            }
            since = self.calls[0] if self.calls else self.started
            return {"levels": levels, "summary": summary(levels, self.client, len(self.calls)),
                    "client": dict(self.client), "host": host,
                    "probe_calls": len(self.calls), "resource_reads": len(self.reads),
                    "view_reports": [{"stage": p["stage"], "detail": p["detail"],
                                      "seconds_after_probe": round(p["at"] - since, 1)}
                                     for p in self.pings],
                    "view": view_uri()}


def summary(levels: dict[str, bool], client: dict, calls: int) -> str:
    """One sentence for a person: what the levels add up to."""
    if not calls:
        return "ui_probe has not been called yet -- call it first, then ask for this report."
    who = " ".join(str(client.get(k) or "") for k in ("name", "version")).strip() or "this client"
    if levels["handshake"] and levels["bridge"]:
        tail = (" The button was pressed too." if levels["clicked"] else
                " Press the panel's button to prove a click reaches the server.")
        got = "" if levels["result"] else " (the tool's result was not handed to the view)"
        return (f"MCP Apps WORKS in {who}: the panel rendered, the host answered the handshake"
                f"{got} and the view reached this server.{tail}")
    if levels["bridge"]:
        return (f"The view RAN in {who} and reached this server, but the host never answered "
                "ui/initialize -- a panel may be showing, with the handshake line marked failed.")
    if levels["advertised"] and levels["read"]:
        return (f"{who} advertised MCP Apps and read the view, but the view never called back: "
                "the panel was not mounted (or its script never ran). This is the failure "
                "reported in claude-ai-mcp#165 / ext-apps#671 -- no inline viewer here yet.")
    if levels["read"]:
        return (f"{who} read the view without advertising MCP Apps, and the view never called "
                "back: no panel.")
    if levels["advertised"]:
        return (f"{who} advertised MCP Apps but never read the view: it did not try to render "
                "one for this tool.")
    return (f"{who} did not advertise MCP Apps and never read the view: this client does not "
            "render panels for this server.")


def _client_info(ctx) -> dict[str, Any]:
    """Who connected and what they said about the extension, off the session."""
    from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID, client_supports_apps
    info: dict[str, Any] = {"advertised": False}
    try:
        info["advertised"] = bool(client_supports_apps(ctx))
        caps = ctx.client_capabilities
        extensions = dict(getattr(caps, "extensions", None) or {})
        info["extensions"] = sorted(extensions)
        info["mime_types"] = list((extensions.get(EXTENSION_ID) or {}).get("mimeTypes") or [])
        info["wants"] = APP_MIME_TYPE
        params = getattr(ctx.request_context.session, "client_params", None)
        who = getattr(params, "client_info", None) or getattr(params, "clientInfo", None)
        info["name"] = getattr(who, "name", None)
        info["version"] = getattr(who, "version", None)
        info["protocol"] = getattr(params, "protocol_version", None)
    except Exception as e:          # noqa: BLE001 -- a probe reports what it can
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def build(log: Optional[Log] = None):
    """The Apps extension carrying the probe, and its log. Pass the result's
    first item to `MCPServer(extensions=[...])`, then `add_report_tool`."""
    from mcp.server.apps import APP_MIME_TYPE, Apps
    from mcp.server.mcpserver import Context
    from mcp.server.mcpserver.resources import FunctionResource
    from mcp.types import CallToolResult, TextContent, ToolAnnotations

    log = log or Log()
    uri = view_uri()
    apps = Apps()

    def read_view() -> str:
        log.read()
        return VIEW_HTML

    apps.add_resource(FunctionResource(
        uri=uri, name="phantra-mcp-apps-probe", title="Phantra · MCP Apps probe",
        description="A self-contained test panel: it reports whether it rendered.",
        mime_type=APP_MIME_TYPE,
        # empty lists, not absent: the view loads nothing from anywhere
        meta={"ui": {"csp": {"connectDomains": [], "resourceDomains": []}}},
        fn=read_view))

    @apps.tool(
        resource_uri=uri, name=TOOL, title="Test whether a panel renders (MCP Apps)",
        # the flat spelling older hosts read, beside the `ui` object the decorator stamps
        meta={"ui/resourceUri": uri},
        description=(
            "A diagnostic, not part of the studio: shows a small test panel if this client "
            "renders MCP Apps. Call it once, tell the person to look for a panel titled "
            "\"Phantra · MCP Apps probe\" and to press its button if it is there, then "
            f"call `{REPORT_TOOL}` to read how far the client got. Spends nothing."),
        annotations=ToolAnnotations(title="Test whether a panel renders (MCP Apps)",
                                    read_only_hint=True, destructive_hint=False,
                                    idempotent_hint=True, open_world_hint=False))
    def ui_probe(ctx: Context) -> CallToolResult:
        info = _client_info(ctx)
        log.saw_client(info)
        log.called()
        said = ("This client advertised MCP Apps" if info.get("advertised") else
                "This client did NOT advertise MCP Apps at connect")
        text = (f"{said}. If a panel titled \"Phantra · MCP Apps probe\" is showing with this "
                "message, MCP Apps renders here: ask the person what they see and to press its "
                f"button. Then call `{REPORT_TOOL}` -- it says how far the client got even if "
                "nothing appeared.")
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content={"view": uri, "client": info},
            # on the RESULT too, both spellings: some hosts read it only here
            _meta={"ui": {"resourceUri": uri}, "ui/resourceUri": uri})

    @apps.tool(
        resource_uri=uri, visibility=["app"], name=PING_TOOL,
        title="(the probe panel reports in)",
        description="Called by the probe's own panel through the host. Not for the model.",
        annotations=ToolAnnotations(title="(the probe panel reports in)", read_only_hint=True,
                                    destructive_hint=False, idempotent_hint=True,
                                    open_world_hint=False))
    def ui_probe_ping(stage: str, detail: str = "") -> str:
        log.ping(stage, detail)
        return "noted"

    return apps, log


def add_report_tool(server, log: Log) -> None:
    """`ui_probe_report`: a plain tool (no view), so it answers on any client."""
    from mcp.server.mcpserver import Context
    from mcp.types import ToolAnnotations

    @server.tool(name=REPORT_TOOL, title="Read the MCP Apps probe's result",
                 description=(
                     f"What the server saw after `{TOOL}`: whether the client advertised MCP "
                     "Apps, read the view, mounted it (the view calls back when its script "
                     "runs), handed it the tool result, and whether the panel's button was "
                     "pressed -- with a one-sentence verdict. Read-only."),
                 annotations=ToolAnnotations(title="Read the MCP Apps probe's result",
                                             read_only_hint=True, destructive_hint=False,
                                             idempotent_hint=True, open_world_hint=False))
    def ui_probe_report(ctx: Context) -> dict[str, Any]:
        log.saw_client(_client_info(ctx))
        return log.report()


__all__ = ["ENV", "TOOL", "PING_TOOL", "REPORT_TOOL", "VIEW_HTML", "PROTOCOL_VERSION", "Log",
           "enabled", "view_uri", "summary", "build", "add_report_tool"]
