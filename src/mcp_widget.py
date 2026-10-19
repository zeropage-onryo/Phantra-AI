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
TOOLS = ("quote", "generate_image", "project", "scene")
# Results that hold image links get a note for the model. ChatGPT cannot show an image from our
# host when the MODEL writes it into its reply as markdown (a gray placeholder, 2026-10-16), so
# the model is told not to; where a card is attached it is told the card already shows them.
NOTE_ON_CARD = ("A card with this (and its image) is already on screen: do not embed or link "
                "its images and do not list what it lists again; answer in a sentence or two.")
NOTE_NO_CARD = ("Do not embed or link images from this result: ChatGPT cannot display them "
                "in a reply. Say what is there in words, and offer `scene` or `project` for "
                "a card, or `share_link` for a file.")
NOTE_TOOLS = {"project": NOTE_ON_CARD, "scene": NOTE_ON_CARD, "projects": NOTE_NO_CARD,
              "library": NOTE_NO_CARD, "elements": NOTE_NO_CARD, "recent": NOTE_NO_CARD}

VIEW_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phantra</title>
<style>
  :root { color-scheme: light dark; --accent: #FEE32D; --on-accent: #171717; }
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }
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
  .compact { display: flex; gap: 12px; align-items: center; padding: 12px; }
  .thumb { flex: 0 0 auto; width: 64px; height: 64px; border-radius: 8px; object-fit: cover;
           background: light-dark(#f3f3f3, #181818); }
  .col { flex: 1 1 auto; min-width: 0; }
  .price { margin: 4px 0 0; font-size: 20px; font-weight: 700; line-height: 1.15; }
  .line { margin: 2px 0 0; font-size: 12px; color: var(--color-text-secondary, light-dark(#666, #aaa));
          font-variant-numeric: tabular-nums; }
  .rows { margin: 8px 0 0; padding: 0; list-style: none; }
  .rows li { display: flex; gap: 8px; align-items: center; padding: 5px 0; font-size: 13px; }
  .rows li + li { border-top: 1px solid var(--color-border-primary, light-dark(#ececec, #303030)); }
  .rows .id { flex: 0 0 auto; width: 38px; color: var(--color-text-secondary, light-dark(#666, #aaa));
              font-variant-numeric: tabular-nums; }
  .rows .name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tiny { flex: 0 0 auto; width: 28px; height: 28px; border-radius: 6px; object-fit: cover;
          background: light-dark(#f3f3f3, #181818); }
  /* the accent goes on buttons and the progress dot only (OpenAI: never backgrounds or text) */
  .actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .btn { font: inherit; font-weight: 600; font-size: 13px; padding: 7px 14px; border-radius: 999px;
         cursor: pointer; background: transparent; color: inherit;
         border: 1px solid var(--color-border-primary, light-dark(#d0d0d0, #444)); }
  .btn.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .skeleton { position: relative; aspect-ratio: 1 / 1; width: 100%; max-height: 420px; overflow: hidden;
              background: light-dark(#ececec, #262626); }
  .skeleton::after { content: ""; position: absolute; inset: 0; background-size: 200% 100%;
                     animation: sweep 1.6s linear infinite;
                     background: linear-gradient(100deg, transparent 30%,
                                 light-dark(#ffffff99, #ffffff14) 50%, transparent 70%); }
  @keyframes sweep { from { background-position: 200% 0; } to { background-position: -200% 0; } }
  @media (prefers-reduced-motion: reduce) {
    .skeleton::after { animation: none; } .dot { animation: none; } }
  .progress { position: absolute; top: 12px; left: 12px; z-index: 1; display: inline-flex;
              align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px;
              font-size: 13px; font-weight: 600;
              background: light-dark(#ffffffcc, #000000a6); border: 1px solid light-dark(#d9d9d9, #444); }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent);
         animation: pulse 1.2s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .35; } }
  .caption .m { font-weight: 600; margin: 0 0 2px; }
  .caption .p { margin: 0; opacity: .85; display: -webkit-box; -webkit-line-clamp: 2;
                -webkit-box-orient: vertical; overflow: hidden; }
  .caption { position: absolute; left: 0; right: 0; bottom: 0; z-index: 1; padding: 22px 14px 12px;
             font-size: 13px; color: #f5f5f5;
             background: linear-gradient(transparent, light-dark(#000000b3, #000000cc)); }
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

  // The tool's answer. Our tools return a plain dict, which the SDK sends as JSON text and NOT as
  // structuredContent, so read that when the structured form is absent (found live 2026-10-16).
  function payload(p) {
    if (p.structuredContent && typeof p.structuredContent === "object") return p.structuredContent;
    var blocks = p.content || [];
    for (var i = 0; i < blocks.length; i++) {
      if (blocks[i] && blocks[i].type === "text" && typeof blocks[i].text === "string") {
        try {
          var parsed = JSON.parse(blocks[i].text);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
        } catch (e) { /* prose, not our JSON */ }
      }
    }
    return null;
  }

  function pic(url, cls) {
    var u = safeUrl(url);
    if (!u) return null;
    var im = document.createElement("img");
    im.className = cls; im.alt = ""; im.src = u;
    im.addEventListener("load", reportSize);
    im.addEventListener("error", function () { im.style.display = "none"; });
    return im;
  }
  function statusBadge(status) {
    var t = String(status || "").replace(/_/g, " ");
    if (!t) return null;
    var good = /render(ed)?$|done|complete/i.test(t) && !/started/i.test(t);
    return el("span", "badge" + (good ? " ok" : ""), t.charAt(0).toUpperCase() + t.slice(1));
  }

  // a project: its cover, its title, and one row per scene
  function renderProject(sc) {
    var scenes = sc.scenes.slice(0, 8);
    var rendered = sc.scenes.filter(function (x) { return x && x.clip; }).length;
    var cover = null;
    for (var i = 0; i < sc.scenes.length && !cover; i++) {
      if (sc.scenes[i] && sc.scenes[i].still) cover = sc.scenes[i].still;
    }
    var top = el("div", "compact");
    var im = pic(cover, "thumb");
    if (im) top.appendChild(im);
    var col = el("div", "col");
    col.appendChild(el("p", "title", String(sc.title)));
    col.appendChild(el("p", "line", sc.scenes.length + " scene" + (sc.scenes.length === 1 ? "" : "s") +
                                    " \u00b7 " + rendered + " rendered"));
    top.appendChild(col);
    card.appendChild(top);
    var body = el("div", "body");
    body.style.paddingTop = "0";
    var list = el("ul", "rows");
    scenes.forEach(function (x) {
      if (!x) return;
      var li = el("li");
      li.appendChild(el("span", "id", "#" + x.id));
      var t = pic(x.still, "tiny");
      if (t) li.appendChild(t);
      li.appendChild(el("span", "name", String(x.title || "Untitled")));
      var b = statusBadge(x.status);
      if (b) li.appendChild(b);
      list.appendChild(li);
    });
    body.appendChild(list);
    if (sc.scenes.length > scenes.length) {
      body.appendChild(el("p", "note", "and " + (sc.scenes.length - scenes.length) + " more"));
    }
    card.appendChild(body);
    reportSize();
  }

  // one scene: its keyframe, its title and how it stands
  function renderScene(sc) {
    var row = el("div", "compact");
    var im = pic(sc.keyframe, "thumb");
    if (im) row.appendChild(im);
    var col = el("div", "col");
    var head = el("div", "head");
    head.appendChild(el("p", "title", String(sc.title || "Scene " + sc.scene_id)));
    var b = statusBadge(sc.rendered ? "rendered" : sc.status);
    if (b) head.appendChild(b);
    col.appendChild(head);
    var bits = ["Scene " + sc.scene_id];
    if (typeof sc.seconds === "number") bits.push(sc.seconds + " s");
    if (sc.shots.length) bits.push(sc.shots.length + " shot" + (sc.shots.length === 1 ? "" : "s"));
    col.appendChild(el("p", "line", bits.join(" \u00b7 ")));
    row.appendChild(col);
    card.appendChild(row);
    reportSize();
  }

  function ratioCss(a) {
    var m = /^([0-9.]+):([0-9.]+)$/.exec(String(a || ""));
    return m ? m[1] + " / " + m[2] : "1 / 1";
  }
  function skeleton(quote, status, label) {
    var sk = el("div", "skeleton");
    sk.style.aspectRatio = ratioCss(quote && quote.aspect);
    var pill = el("div", "progress");
    pill.appendChild(el("span", "dot"));
    pill.appendChild(el("span", "", status === "queued" ? "Queued" : "Processing"));
    sk.appendChild(pill);
    var cap = el("div", "caption");
    var what = quote && (quote.label || quote.model);
    if (what || label) {
      cap.appendChild(el("p", "m", String(what || label) + (quote && quote.aspect ? " \u00b7 " + quote.aspect : "")));
    }
    if (quote && quote.prompt) cap.appendChild(el("p", "p", String(quote.prompt)));
    if (cap.firstChild) sk.appendChild(cap);
    return sk;
  }
  // A started job: show the skeleton, ask `job` (read-only) until it ends, then draw the result in
  // place. If the host will not let the card call a tool, say so after a while; the chat still has it.
  // The Approve button: a person pressed a priced button, which is the approval. It sends back the
  // arguments the quote was signed over (already normalized by the server) with its one-time token.
  function approve(quote, btn) {
    btn.disabled = true;
    btn.textContent = "Starting\u2026";
    function stop(message) {
      card.textContent = "";
      card.appendChild(el("div", "slim", message));
      reportSize();
    }
    var args = {};
    Object.keys(quote.approve_args).forEach(function (k) { args[k] = quote.approve_args[k]; });
    args.quote_token = quote.quote_token;
    request("tools/call", { name: "generate_image", arguments: args })
      .then(function (res) {
        var out = payload(res || {});
        if (out && out.job_id !== undefined) {
          card.textContent = "";
          liveJob(out, out.quote || quote, out.status || "running");
        } else if (out && (out.media_url || (out.result && out.result.media_url))) {
          render(out);
        } else {
          var why = out && (out.note || out.error);
          stop(String(why || "That did not start. Nothing was charged. Ask me for a new quote."));
        }
      })
      .catch(function () {
        stop("That did not start, and nothing was charged. The price may have expired: " +
             "ask me for a new quote, or say yes in the chat.");
      });
  }

  var polling = false;
  function liveJob(sc, quote, status) {
    card.appendChild(skeleton(quote, status, sc.label));
    reportSize();
    if (polling || sc.job_id === undefined) return;
    polling = true;
    var began = Date.now(), misses = 0;
    function giveUp() {
      polling = false;
      card.textContent = "";
      card.appendChild(el("div", "slim", "Still working. Ask me for the result and I will check."));
      reportSize();
    }
    function tick() {
      if (Date.now() - began > 240000) { giveUp(); return; }
      request("tools/call", { name: "job", arguments: { job_id: sc.job_id, wait: 10 } })
        .then(function (res) {
          misses = 0;
          var snap = payload(res || {});
          var st = snap && snap.status;
          if (st === "done" || st === "failed" || st === "cancelled") {
            polling = false;
            render({ status: st, result: snap.result, error: snap.error, quote: quote });
            return;
          }
          setTimeout(tick, 1000);
        })
        .catch(function () { if (++misses >= 3) giveUp(); else setTimeout(tick, 2500); });
    }
    tick();
  }

  function render(sc) {
    card.textContent = "";
    if (!sc || typeof sc !== "object") return;
    if (Array.isArray(sc.shots) && sc.scene_id !== undefined) { renderScene(sc); return; }
    if (Array.isArray(sc.scenes) && sc.title && sc.id !== undefined) { renderProject(sc); return; }
    var r = (sc.result && typeof sc.result === "object") ? sc.result : null;
    var quote = (sc.quote && typeof sc.quote === "object") ? sc.quote
              : (r && r.quote && typeof r.quote === "object") ? r.quote : null;
    var status = sc.status || (r && r.status) || "";
    var running = status === "running" || status === "queued" || status === "pending";
    var failed = status === "failed" || status === "error" || status === "cancelled";
    var mediaUrl = safeUrl(sc.media_url || (r && r.media_url) || sc.preview_url);
    var mediaKind = sc.media_kind || (r && r.media_kind) || "";

    if (running || (sc.job_id !== undefined && !sc.media_url && !failed && sc.quote)) {
      liveJob(sc, quote, status);                    // the card itself waits for the job
      return;
    }
    var finished = !!(sc.media_url || (r && r.media_url)) && !sc.needs_approval;
    var price = quote ? num(quote.credits) : num(sc.credits_needed);
    var balance = quote ? num(quote.balance) : num(sc.balance);
    var after = quote ? num(quote.balance_after) : (balance !== null && price !== null ? balance - price : null);
    var title = sc.title || (quote && (quote.label || quote.model)) ||
                (sc.scene_id ? "Scene " + sc.scene_id : sc.label || "Phantra");
    var badge = null;
    if (failed) badge = ["Didn\u2019t finish", "bad"];
    else if (sc.refused === "insufficient_credits") badge = ["Not enough credits", "bad"];
    else if (sc.needs_approval) badge = ["Ready to approve", "warn"];
    else if (sc.affordable === false) badge = ["Over your balance", "bad"];
    else if (sc.affordable === true && sc.credits_needed) badge = ["Within your balance", "ok"];
    else if (finished) badge = ["Done", "ok"];

    function media() {
      var m;
      if (isVideo(mediaUrl, mediaKind) && finished) {
        m = document.createElement("video");
        m.controls = true; m.playsInline = true; m.preload = "metadata";
      } else {
        m = document.createElement("img");
        m.alt = "Image from Phantra";
        m.loading = "eager";
      }
      m.src = mediaUrl;
      m.addEventListener("load", reportSize);
      m.addEventListener("loadedmetadata", reportSize);
      m.addEventListener("error", function () { m.style.display = "none"; reportSize(); });
      return m;
    }
    function headRow(parent) {
      var head = el("div", "head");
      head.appendChild(el("p", "title", String(title)));
      if (badge) head.appendChild(el("span", "badge " + badge[1], badge[0]));
      parent.appendChild(head);
    }

    if (finished && mediaUrl) {
      // a finished still or clip is the thing itself: full width, one line, two buttons
      var big = media(); big.className = "media"; card.appendChild(big);
      var body = el("div", "body");
      var bits = [];
      if (quote && (quote.label || quote.model)) bits.push(String(quote.label || quote.model));
      if (quote && quote.charged && price !== null) bits.push(credits(price) + " used");
      if (quote && quote.charged && after !== null) bits.push("balance " + credits(after));
      if (bits.length) body.appendChild(el("p", "line", bits.join(" \u00b7 ")));
      var ref = (r && r.ref) || sc.ref;
      var openUrl = safeUrl(sc.media_url || (r && r.media_url));
      var saveUrl = safeUrl((r && r.download_url) || sc.download_url) || openUrl;
      if (openUrl) {
        var actions = el("div", "actions");
        var save = el("button", "btn primary", "Download");
        save.type = "button";
        save.addEventListener("click", function () {
          request("ui/open-link", { url: saveUrl }).catch(function () { window.open(saveUrl, "_blank"); });
        });
        actions.appendChild(save);
        if (typeof ref === "string" && /^gen:[0-9]+$/.test(ref)) {
          var use = el("button", "btn", "Reference");
          use.type = "button";
          use.addEventListener("click", function () {
            var say = "Use " + ref + " as a reference for my next one.";
            request("ui/message", { role: "user", content: [{ type: "text", text: say }] })
              .catch(function () {});
          });
          actions.appendChild(use);
        }
        body.appendChild(actions);
      }
      card.appendChild(body);
      reportSize();
      return;
    }

    // a price, or a refusal: one compact row (a small picture when there is one), no table
    var row = el("div", "compact");
    if (mediaUrl) { var th = media(); th.className = "thumb"; row.appendChild(th); }
    var col = el("div", "col");
    headRow(col);
    if (failed) {
      var why = sc.error || (r && (r.error || r.note)) || "It did not finish.";
      col.appendChild(el("p", "line", String(why)));
      if (!/charged/i.test(String(why))) col.appendChild(el("p", "line", "Nothing was charged."));
    } else if (sc.refused === "insufficient_credits") {
      var need = num(sc.needs), have = num(sc.available);
      if (need !== null) col.appendChild(el("p", "price", credits(need)));
      if (have !== null) col.appendChild(el("p", "line", "You have " + credits(have)));
    } else {
      if (price !== null) {
        col.appendChild(el("p", "price", credits(price) + (quote && quote.charged === false ? " (not charged)" : "")));
      }
      if (balance !== null && after !== null) {
        col.appendChild(el("p", "line", "Balance " + balance.toLocaleString() + " \u2192 " + credits(after)));
      } else if (balance !== null) {
        col.appendChild(el("p", "line", "Balance " + credits(balance)));
      }
    }
    row.appendChild(col);
    card.appendChild(row);
    var canApprove = !!(sc.needs_approval && sc.can_approve !== false && quote && quote.quote_token &&
                        quote.approve_args && price !== null);
    if (canApprove) {
      var go = el("button", "btn primary", "Approve \u00b7 " + credits(price));
      go.type = "button";
      go.addEventListener("click", function () { approve(quote, go); });
      var ab = el("div", "actions");
      ab.style.marginTop = "8px";
      ab.appendChild(go);
      col.appendChild(ab);
    }
    var note = null;
    if (sc.needs_approval && sc.can_approve !== false) {
      note = canApprove ? "Nothing is spent until you press Approve or say yes in the chat."
                        : "Nothing is spent until you say yes in the chat.";
    }
    else if (sc.scene_id && sc.credits_needed) note = "A quote only. Nothing is spent until you say yes in the chat.";
    if (note) {
      var nb = el("div", "body");
      nb.style.paddingTop = "0";
      nb.appendChild(el("p", "note", note));
      card.appendChild(nb);
    }
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
      render(payload(data.params || {}));
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
