"""The card ChatGPT draws for a price or a finished render (2026-10-16).

WHY. On the ChatGPT listing a quote and a finished still came back as text
and ChatGPT filled the gap itself: a blank thumbnail on the render-cost card,
and above a finished still, a stock photo from some other website labelled
with that website's name. Our own image sat behind a link. A reviewer
watching the demo would reasonably take the stock photo for the render.

THE FIX is the open MCP Apps standard, which ChatGPT implements
(developers.openai.com/plugins/build/chatgpt-ui): the tool names a `ui://`
view, the view is served as `text/html;profile=mcp-app`, runs in an iframe,
and is handed the tool's `structuredContent`. The view draws OUR image, from
the one host the resource's CSP declares (`resourceDomains`), and nothing
else: no script, style or font from anywhere, and no connect domains.

WHAT IT DRAWS, from whichever of these the result carries:
  * a still or clip      `media_url` (a finished job, or an approved `generate_image`)
  * a scene's keyframe   `preview_url` (added to `quote` on the render listing)
  * a price              `quote.credits` or `credits_needed`, the balance and
                         what is left after
and one line of status. It has NO buttons: a price is approved in the chat, in
words, exactly as before (CLAUDE.md: nothing spends without a price the person
saw). It only makes what is already true visible.

ONLY THREE TOOLS carry it -- `quote`, `generate_image` and `job` -- on the
render listing alone (never the Claude listing, which draws nothing, and never
the studio). A tool without it behaves as it did.

The view follows src/mcp_apps_probe.py's, which was run against the official
host bridge before it shipped: the handshake is written out from the spec,
`initialized` is sent whether or not the reply is recognised, the URI carries
a content hash so a host never serves a stale copy, and the tool's own text
stays useful where no card renders.
"""
from __future__ import annotations

import hashlib
from typing import Any

PROTOCOL_VERSION = "2026-01-26"
DEFAULT_MEDIA_HOST = "https://media.phantra.ai"
# the render listing's tools that carry the card
TOOLS = ("quote", "generate_image", "job")

VIEW_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phantra</title>
<style>
  :root { color-scheme: light dark; }
  html, body { margin: 0; padding: 0; background: transparent; }
  body { font: 14px/1.45 var(--font-sans, -apple-system, "Segoe UI", system-ui, sans-serif);
         color: var(--color-text-primary, light-dark(#171717, #f5f5f5)); }
  .card { overflow: hidden; border-radius: 12px;
          border: 1px solid var(--color-border-primary, light-dark(#e0e0e0, #3a3a3a));
          background: var(--color-background-primary, light-dark(#fff, #212121)); }
  .media { display: block; width: 100%; max-height: 360px; object-fit: contain;
           background: light-dark(#f3f3f3, #181818); }
  .body { padding: 12px 14px 14px; }
  .head { display: flex; gap: 8px; align-items: center; justify-content: space-between; }
  .title { font-weight: 600; font-size: 15px; margin: 0; }
  .badge { font-size: 12px; padding: 2px 8px; border-radius: 999px; white-space: nowrap;
           background: light-dark(#f1f1f1, #303030);
           color: var(--color-text-secondary, light-dark(#555, #bbb)); }
  .badge.ok { background: light-dark(#e6f4ea, #16301f); color: light-dark(#137333, #7ddc99); }
  .badge.warn { background: light-dark(#fdeccf, #3a2c12); color: light-dark(#8a5a00, #ffcf70); }
  .badge.bad { background: light-dark(#fde7e7, #3a1a1a); color: light-dark(#b3261e, #ff9a93); }
  .sub { margin: 2px 0 0; font-size: 12px; color: var(--color-text-secondary, light-dark(#666, #aaa)); }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  td { padding: 4px 0; }
  td + td { text-align: right; font-variant-numeric: tabular-nums; }
  tr.total td { font-weight: 600; border-top: 1px solid var(--color-border-primary, light-dark(#e0e0e0, #3a3a3a)); }
  .note { margin: 10px 0 0; font-size: 12px; color: var(--color-text-secondary, light-dark(#666, #aaa)); }
  .slim { padding: 10px 14px; font-size: 13px; color: var(--color-text-secondary, light-dark(#666, #aaa)); }
</style>
</head>
<body>
<div class="card" id="card"></div>
<script>
(function () {
  "use strict";
  var PROTOCOL = "__PROTOCOL__";
  var nextId = 1, pending = {}, initializedSent = false, lastHeight = 0, tries = 0;
  var card = document.getElementById("card");

  function post(message) { window.parent.postMessage(message, "*"); }
  function request(method, params) {
    var id = nextId++;
    return new Promise(function (resolve, reject) {
      pending[id] = { resolve: resolve, reject: reject };
      post({ jsonrpc: "2.0", id: id, method: method, params: params });
    });
  }
  function notify(method, params) {
    var m = { jsonrpc: "2.0", method: method };
    if (params !== undefined) m.params = params;
    post(m);
  }
  function reportSize() {
    if (!initializedSent) return;
    if (window.innerWidth < 120) { if (tries++ < 60) setTimeout(reportSize, 50); return; }
    var h = Math.ceil(card.getBoundingClientRect().height) + 2;
    if (h === lastHeight) return;
    lastHeight = h;
    notify("ui/notifications/size-changed", { height: h });
  }
  function sendInitialized() {
    if (initializedSent) return;
    initializedSent = true;
    notify("ui/notifications/initialized");
    reportSize();
    if (window.ResizeObserver) new ResizeObserver(reportSize).observe(card);
  }
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

  // ---- drawing: every value is text, every address is checked ----
  function num(v) { return typeof v === "number" && isFinite(v) ? v : null; }
  function credits(n) { return n === null ? "" : n.toLocaleString() + " credit" + (n === 1 ? "" : "s"); }
  function safeUrl(u) {
    if (typeof u !== "string") return null;
    try { var x = new URL(u); return x.protocol === "https:" ? x.href : null; } catch (e) { return null; }
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function row(table, label, value, cls) {
    var tr = el("tr", cls || "");
    tr.appendChild(el("td", "", label));
    tr.appendChild(el("td", "", value));
    table.appendChild(tr);
  }
  function isVideo(url, kind) { return kind === "video" || /\\.(mp4|webm|mov)(\\?|$)/i.test(url || ""); }

  function render(sc) {
    card.textContent = "";
    if (!sc || typeof sc !== "object") return;
    var r = (sc.result && typeof sc.result === "object") ? sc.result : null;
    var quote = (sc.quote && typeof sc.quote === "object") ? sc.quote
              : (r && r.quote && typeof r.quote === "object") ? r.quote : null;
    var status = sc.status || (r && r.status) || "";
    var running = status === "running" || status === "queued" || status === "pending";
    var failed = status === "failed" || status === "error" || status === "cancelled";
    var mediaUrl = safeUrl(sc.media_url || (r && r.media_url) || sc.preview_url);
    var mediaKind = sc.media_kind || (r && r.media_kind) || "";

    if (running) {                                  // a poll: stay out of the way
      card.appendChild(el("div", "slim", "Phantra is still working on it\\u2026"));
      reportSize();
      return;
    }
    if (mediaUrl) {
      var m;
      if (isVideo(mediaUrl, mediaKind) && (sc.media_url || (r && r.media_url))) {
        m = document.createElement("video");
        m.controls = true; m.playsInline = true; m.preload = "metadata";
      } else {
        m = document.createElement("img");
        m.alt = "Image from Phantra";
        m.loading = "eager";
      }
      m.className = "media";
      m.src = mediaUrl;
      m.addEventListener("load", reportSize);
      m.addEventListener("loadedmetadata", reportSize);
      m.addEventListener("error", function () { m.style.display = "none"; reportSize(); });
      card.appendChild(m);
    }

    var body = el("div", "body");
    var head = el("div", "head");
    var title = sc.title || (quote && (quote.label || quote.model)) ||
                (sc.scene_id ? "Scene " + sc.scene_id : sc.label || "Phantra");
    head.appendChild(el("p", "title", String(title)));
    var badge = null;
    if (failed) badge = ["Didn\\u2019t finish", "bad"];
    else if (sc.refused === "insufficient_credits") badge = ["Not enough credits", "bad"];
    else if (sc.needs_approval) badge = ["Waiting for your yes", "warn"];
    else if (sc.affordable === false) badge = ["Over your balance", "bad"];
    else if (sc.affordable === true && sc.credits_needed) badge = ["Within your balance", "ok"];
    else if (status === "done" || status === "completed" || (mediaUrl && sc.media_url)) badge = ["Done", "ok"];
    if (badge) head.appendChild(el("span", "badge " + badge[1], badge[0]));
    body.appendChild(head);
    if (sc.scene_id && sc.status && typeof sc.status === "string" && !r) {
      body.appendChild(el("p", "sub", "Scene " + sc.scene_id + " \\u00b7 " + sc.status.replace(/_/g, " ")));
    }

    var table = el("table");
    var done = !!(sc.media_url || (r && r.media_url)) && !sc.needs_approval;
    var price = quote ? num(quote.credits) : num(sc.credits_needed);
    var kf = sc.keyframes && num(sc.keyframes.credits);
    var clip = sc.clip && num(sc.clip.credits);
    var balance = quote ? num(quote.balance) : num(sc.balance);
    var after = quote ? num(quote.balance_after) : (balance !== null && price !== null ? balance - price : null);
    if (sc.refused === "insufficient_credits") {
      if (num(sc.needs) !== null) row(table, "Needs", credits(num(sc.needs)));
      if (num(sc.available) !== null) row(table, "You have", credits(num(sc.available)));
    } else if (done && quote && quote.charged && price !== null) {
      row(table, "Credits used", credits(price), "total");
      if (after !== null) row(table, "Balance now", credits(after));
    } else {
      if (kf) row(table, "Keyframe stills", credits(kf));
      if (clip) row(table, "Video clip", credits(clip));
      var priceLabel = quote && quote.charged === false ? "Price (not charged)" : "Price";
      if (price !== null) row(table, priceLabel, credits(price), "total");
      if (balance !== null) row(table, "Balance", credits(balance));
      if (after !== null && (sc.needs_approval || sc.scene_id)) row(table, "After this", credits(after));
    }
    if (table.firstChild) body.appendChild(table);

    var note = null;
    if (sc.needs_approval && sc.can_approve !== false) note = "Nothing is spent until you say yes in the chat.";
    else if (sc.scene_id && sc.credits_needed) note = "A quote only. Nothing is spent until you say yes in the chat.";
    if (note) body.appendChild(el("p", "note", note));
    card.appendChild(body);
    reportSize();
  }

  window.addEventListener("message", function (event) {
    if (event.source !== window.parent) return;
    var data = event.data;
    if (!data || data.jsonrpc !== "2.0") return;
    if (data.method === undefined) {                       // a reply to one of ours
      var w = pending[data.id];
      if (!w) return;
      delete pending[data.id];
      if (data.error) w.reject(data.error); else w.resolve(data.result);
      return;
    }
    if (data.id !== undefined) {                           // a request from the host
      if (data.method === "ping" || data.method === "ui/resource-teardown") {
        post({ jsonrpc: "2.0", id: data.id, result: {} });
      } else {
        post({ jsonrpc: "2.0", id: data.id, error: { code: -32601, message: "Method not found: " + data.method } });
      }
      return;
    }
    if (data.method === "ui/notifications/tool-result") {
      var p = data.params || {};
      render(p.structuredContent);
    } else if (data.method === "ui/notifications/host-context-changed") {
      applyContext(data.params);
    }
  });

  request("ui/initialize", {
    appInfo: { name: "phantra-card", version: "1" },
    appCapabilities: {},
    protocolVersion: PROTOCOL
  }).then(function (result) {
    applyContext(result && result.hostContext);
    sendInitialized();
  }).catch(function () { sendInitialized(); });
  setTimeout(sendInitialized, 1500);
})();
</script>
</body>
</html>
""".replace("__PROTOCOL__", PROTOCOL_VERSION)


def view_uri() -> str:
    """`ui://phantra/card-<hash>.html`: a host caches a view against its URI,
    so a changed view is a new URI and never a stale copy."""
    return f"ui://phantra/card-{hashlib.sha256(VIEW_HTML.encode()).hexdigest()[:10]}.html"


def media_host() -> str:
    """The one origin the card may load images and clips from: where the
    bucket is served (`R2_PUBLIC_BASE_URL`), else the production media domain.
    An origin only -- a CSP source with a path would match less than intended."""
    from urllib.parse import urlsplit

    from . import storage
    base = storage.public_base_url() or DEFAULT_MEDIA_HOST
    parts = urlsplit(base)
    if parts.scheme != "https" or not parts.netloc:
        return DEFAULT_MEDIA_HOST
    return f"https://{parts.netloc}"


def csp() -> dict[str, list[str]]:
    """Images and clips from our media host and nowhere else; the card never
    calls out (`connectDomains` empty) and loads no script or font."""
    return {"resourceDomains": [media_host()], "connectDomains": []}


def tool_meta(uri: str) -> dict[str, Any]:
    """What a card-carrying tool declares: the standard key, and the alias
    ChatGPT also reads."""
    return {"ui": {"resourceUri": uri}, "openai/outputTemplate": uri}


def build():
    """(the Apps extension carrying the card's resource, its URI). Pass the
    first to `MCPServer(extensions=[...])`."""
    from mcp.server.apps import APP_MIME_TYPE, Apps
    from mcp.server.mcpserver.resources import FunctionResource

    uri = view_uri()
    apps = Apps()
    apps.add_resource(FunctionResource(
        uri=uri, name="phantra-card", title="Phantra card",
        description="A price, a still or a clip, drawn from the tool's result.",
        mime_type=APP_MIME_TYPE,
        meta={"ui": {"prefersBorder": True, "csp": csp()}},
        fn=lambda: VIEW_HTML))
    return apps, uri


__all__ = ["TOOLS", "VIEW_HTML", "view_uri", "media_host", "csp", "tool_meta", "build"]
