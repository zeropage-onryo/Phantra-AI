"use client";

import { useEffect, useRef } from "react";

// The hero's ASCII layer (2026-10-15, Mike picked "A · Ripple" from the
// three mockups): a field of tiny monospace characters behind the hero,
// almost invisible, the way the Claude desktop app's new-session
// background is. A click drops a pebble -- an orange ring of brightened,
// re-rolling characters rolls out from the point and fades, with a few
// crests trailing it, so quick clicks interfere like water. A moving
// cursor leaves a faint trail and the field sends out a faint ring of
// its own every few seconds.
//
// It sits first in the hero section, so the reel's opaque clips and the
// copy column paint over it: the orange shows on the left and in the
// reel's gaps. The field dims under the headline's words so they always
// read.
//
// What keeps it cheap: the dim field is drawn once to an offscreen canvas
// and blitted each frame; only the cells a ring touches are drawn again,
// bucketed by brightness so the fill colour changes a few dozen times a
// frame, not thousands. It runs at most ~60fps, stops while the tab is
// hidden or the hero is scrolled off screen, and with reduced motion the
// field stands still and a click only fades a ring in and out in place.

const BG = "#0b0a08"; // .editorial --background
const SHADES = ["#161513", "#1b1a18", "#232120"];
const SHADE_W = [0.55, 0.33];
const GLYPHS = "abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz+=*/<>";
const GL = GLYPHS.length;
const NL = 28; // brightness levels
const STOPS: [number, [number, number, number]][] = [
  [0.0, [40, 37, 34]],
  [0.16, [86, 46, 22]],
  [0.36, [168, 72, 20]],
  [0.58, [255, 122, 26]], // #ff7a1a
  [0.8, [255, 176, 102]], // #ffb066
  [1.0, [255, 226, 194]],
];
const PAL: string[] = Array.from({ length: NL }, (_, l) => {
  const h = l / (NL - 1);
  let k = 0;
  while (k < STOPS.length - 2 && h > STOPS[k + 1][0]) k++;
  const [h0, c0] = STOPS[k];
  const [h1, c1] = STOPS[k + 1];
  const f = Math.min(1, Math.max(0, (h - h0) / (h1 - h0)));
  return `rgb(${c0.map((v, j) => Math.round(v + (c1[j] - v) * f)).join(",")})`;
});
const HEADLINE_ATT = 0.32; // how much of a ring survives behind the headline

type Ring = { x: number; y: number; t0: number; life: number; rmax: number; amp: number };
type Stats = { work: number; interval: number; frames: number; active: number };

const clamp = (v: number, a: number, b: number) => (v < a ? a : v > b ? b : v);
const smooth = (a: number, b: number, x: number) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const rint = (n: number) => (Math.random() * n) | 0;
const pickShade = () => {
  const r = Math.random();
  return r < SHADE_W[0] ? 0 : r < SHADE_W[0] + SHADE_W[1] ? 1 : 2;
};

export function AsciiRipple() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cvs = ref.current;
    const host = cvs?.parentElement;
    const ctx = cvs?.getContext("2d", { alpha: false });
    if (!cvs || !host || !ctx) return;
    const base = document.createElement("canvas");
    const bctx = base.getContext("2d", { alpha: false });
    if (!bctx) return;

    const rmq = window.matchMedia("(prefers-reduced-motion: reduce)");
    let still = rmq.matches;
    // the site's JetBrains Mono (next/font, preload off: this is its first
    // use on the landing page), with a monospace fallback so the grid's
    // cell width is a monospace one even before the face arrives
    const loaded = getComputedStyle(document.documentElement).getPropertyValue("--font-jetbrains").trim();
    const family = `${loaded ? `${loaded}, ` : ""}ui-monospace, SFMono-Regular, Menlo, monospace`;

    // grid
    let W = 0, H = 0, DPR = 1, CW = 6.6, LH = 15, COLS = 0, ROWS = 0, N = 0, FONT = "";
    let chars = new Uint8Array(0), shade = new Uint8Array(0);
    let heat = new Float32Array(0), mask = new Float32Array(0), sA = new Float32Array(0), cA = new Float32Array(0);
    let stamp = new Int32Array(0), touched = new Int32Array(0), pend = new Int32Array(0);
    let buckets: Int32Array[] = [];
    const bcount = new Int32Array(NL);
    let nT = 0, np = 0, frameId = 1;
    let openRight = 0; // where the reel's first column starts: no glow past it

    let rings: Ring[] = [];
    let nextIdle = 0;
    const mouse = { x: -1e4, y: -1e4, in: false, moved: 0 };
    let raf = 0, last = 0, visible = true, ready = false, disposed = false;
    const stats: Stats = { work: 0, interval: 16.7, frames: 0, active: 0 };

    function build() {
      const r = host!.getBoundingClientRect();
      W = Math.max(1, Math.round(r.width));
      H = Math.max(1, Math.round(r.height));
      DPR = Math.min(2, window.devicePixelRatio || 1);
      const fs = W < 700 ? 10 : 11;
      LH = Math.round(fs * 1.36);
      FONT = `${fs}px ${family}`;
      cvs!.width = Math.round(W * DPR);
      cvs!.height = Math.round(H * DPR);
      base.width = cvs!.width;
      base.height = cvs!.height;
      bctx!.setTransform(DPR, 0, 0, DPR, 0, 0);
      bctx!.font = FONT;
      CW = bctx!.measureText("M").width * 1.08;
      COLS = Math.ceil(W / CW) + 1;
      ROWS = Math.ceil(H / LH) + 1;
      N = COLS * ROWS;
      chars = new Uint8Array(N);
      shade = new Uint8Array(N);
      heat = new Float32Array(N);
      mask = new Float32Array(N);
      sA = new Float32Array(N);
      cA = new Float32Array(N);
      stamp = new Int32Array(N);
      touched = new Int32Array(N);
      pend = new Int32Array(N);
      buckets = Array.from({ length: NL }, () => new Int32Array(Math.max(64, N >> 2)));
      for (let i = 0; i < N; i++) {
        chars[i] = rint(GL);
        shade[i] = pickShade();
        const p = Math.random() * 40;
        sA[i] = Math.sin(p);
        cA[i] = Math.cos(p);
      }
      rings = [];
      drawBase();
      buildMask();
      ctx!.setTransform(1, 0, 0, 1, 0, 0);
      ctx!.drawImage(base, 0, 0);
    }

    function drawBase() {
      bctx!.setTransform(DPR, 0, 0, DPR, 0, 0);
      bctx!.fillStyle = BG;
      bctx!.fillRect(0, 0, W + 2, H + 2);
      bctx!.font = FONT;
      bctx!.textBaseline = "middle";
      for (let s = 0; s < 3; s++) {
        bctx!.fillStyle = SHADES[s];
        for (let i = 0; i < N; i++)
          if (shade[i] === s) bctx!.fillText(GLYPHS[chars[i]], (i % COLS) * CW, ((i / COLS) | 0) * LH + LH / 2);
      }
    }

    function flushPending() {
      if (!np) return;
      bctx!.fillStyle = BG;
      for (let k = 0; k < np; k++) {
        const i = pend[k];
        bctx!.fillRect((i % COLS) * CW - 0.25, ((i / COLS) | 0) * LH, CW + 0.5, LH);
      }
      for (let s = 0; s < 3; s++) {
        bctx!.fillStyle = SHADES[s];
        for (let k = 0; k < np; k++) {
          const i = pend[k];
          if (shade[i] === s) bctx!.fillText(GLYPHS[chars[i]], (i % COLS) * CW, ((i / COLS) | 0) * LH + LH / 2);
        }
      }
      np = 0;
    }

    // the headline's words, as boxes in the canvas's own coordinates
    function buildMask() {
      if (!N) return;
      mask.fill(1);
      openRight = W;
      const origin = cvs!.getBoundingClientRect();
      // the reel's columns are opaque video: a cell under one is never
      // seen, so it is never drawn (the gaps between columns still light)
      const reel = host!.querySelector('[role="img"]');
      if (reel) {
        const rr = reel.getBoundingClientRect();
        for (const col of Array.from(reel.children)) {
          const r = col.getBoundingClientRect();
          if (!r.width || r.width > rr.width || r.height < rr.height * 0.9) continue; // the phone strip slides: skip it
          const c0 = Math.max(0, Math.ceil((r.left - origin.left) / CW)), c1 = Math.min(COLS - 1, Math.floor((r.right - origin.left) / CW) - 1);
          const r0 = Math.max(0, Math.ceil((r.top - origin.top) / LH)), r1 = Math.min(ROWS - 1, Math.floor((r.bottom - origin.top) / LH) - 1);
          for (let row = r0; row <= r1; row++) mask.fill(0, row * COLS + c0, row * COLS + c1 + 1);
          openRight = Math.min(openRight, r.left - origin.left);
        }
      }
      // the fixed header's 60px band: keep the nav's words clean too
      for (let row = 0; row < ROWS && row * LH < 64; row++)
        for (let i = row * COLS, e = i + COLS; i < e; i++) if (mask[i] > HEADLINE_ATT) mask[i] = HEADLINE_ATT;
      const h1 = host!.querySelector("h1");
      if (!h1) return;
      const range = document.createRange();
      range.selectNodeContents(h1);
      const pad = 8, fe = 22;
      for (const r of Array.from(range.getClientRects())) {
        if (r.width < 4) continue;
        const x0 = r.left - origin.left - pad, x1 = r.right - origin.left + pad;
        const y0 = r.top - origin.top + r.height * 0.12 - pad, y1 = r.bottom - origin.top - r.height * 0.08 + pad;
        const c0 = Math.max(0, Math.floor((x0 - fe) / CW)), c1 = Math.min(COLS - 1, Math.ceil((x1 + fe) / CW));
        const r0 = Math.max(0, Math.floor((y0 - fe) / LH)), r1 = Math.min(ROWS - 1, Math.ceil((y1 + fe) / LH));
        for (let row = r0; row <= r1; row++) {
          const py = row * LH + LH / 2, dy = Math.max(y0 - py, 0, py - y1);
          for (let c = c0; c <= c1; c++) {
            const px = c * CW + CW / 2, dx = Math.max(x0 - px, 0, px - x1);
            const m = HEADLINE_ATT + (1 - HEADLINE_ATT) * smooth(0, fe, Math.hypot(dx, dy));
            const i = row * COLS + c;
            if (m < mask[i]) mask[i] = m;
          }
        }
      }
    }

    function add(i: number, v: number) {
      if (mask[i] === 0) return;
      if (stamp[i] !== frameId) {
        stamp[i] = frameId;
        heat[i] = 0;
        touched[nT++] = i;
      }
      heat[i] += v * mask[i];
    }

    // one ring: a bright leading edge and fading crests behind it
    function ring(e: Ring, t: number): boolean {
      const age = t - e.t0, p = age / e.life;
      if (p >= 1) return false;
      let r: number, w: number, amp: number;
      if (still) {
        r = e.rmax * 0.22;
        w = 30;
        amp = Math.sin(Math.PI * p) * 0.75 * e.amp;
      } else {
        r = 10 + e.rmax * (1 - Math.pow(1 - p, 1.6));
        w = 20 + 34 * p;
        amp = Math.pow(1 - p, 0.95) * Math.min(1, p / 0.05) * e.amp;
      }
      const outer = r + 2.4 * w, inner = Math.max(0, r - 4.5 * w);
      const o2 = outer * outer, i2 = inner * inner, cx = e.x, cy = e.y;
      const tw = t * 7, sT = Math.sin(tw), cT = Math.cos(tw);
      const r0 = Math.max(0, Math.floor((cy - outer) / LH)), r1 = Math.min(ROWS - 1, Math.ceil((cy + outer) / LH));
      for (let row = r0; row <= r1; row++) {
        const py = row * LH + LH / 2, dy = py - cy, dy2 = dy * dy;
        if (dy2 > o2) continue;
        const so = Math.sqrt(o2 - dy2), si = dy2 < i2 ? Math.sqrt(i2 - dy2) : 0;
        const ca = Math.max(0, Math.floor((cx - so) / CW)), cb = Math.min(COLS - 1, Math.ceil((cx + so) / CW));
        const o = row * COLS;
        for (let c = ca; c <= cb; c++) {
          const dx = c * CW + CW / 2 - cx;
          if (si > 0 && Math.abs(dx) < si - CW) continue;
          const d = Math.sqrt(dx * dx + dy2), x = (d - r) / w;
          let v = Math.exp(-x * x);
          if (d < r) {
            const k = (r - d) / w;
            v = Math.max(v, 0.42 * Math.exp(-k / 1.4) * (0.5 + 0.5 * Math.cos(k * 2.6)));
          }
          const i = o + c;
          v *= amp * (0.66 + 0.34 * (sA[i] * cT + cA[i] * sT));
          if (v > 0.02) add(i, v);
        }
      }
      if (!still && age < 0.45) {
        // the splash where the pebble landed
        const f = (1 - age / 0.45) * e.amp, R = 34;
        const c0 = Math.max(0, Math.floor((cx - R) / CW)), c1 = Math.min(COLS - 1, Math.ceil((cx + R) / CW));
        const q0 = Math.max(0, Math.floor((cy - R) / LH)), q1 = Math.min(ROWS - 1, Math.ceil((cy + R) / LH));
        for (let row = q0; row <= q1; row++)
          for (let c = c0; c <= c1; c++) {
            const d2 = (c * CW + CW / 2 - cx) ** 2 + (row * LH + LH / 2 - cy) ** 2;
            if (d2 < R * R) add(row * COLS + c, f * 0.9 * Math.exp(-d2 / 300));
          }
      }
      glows.push([cx, cy, Math.max(0, r - 2 * w), r + 2 * w, 0.07 * amp]);
      return true;
    }

    function trail() {
      const e = Math.min(1, mouse.moved / 900);
      mouse.moved *= 0.88;
      if (e < 0.02 || !mouse.in) return;
      const R = 56, x = mouse.x, y = mouse.y;
      const c0 = Math.max(0, Math.floor((x - R) / CW)), c1 = Math.min(COLS - 1, Math.ceil((x + R) / CW));
      const r0 = Math.max(0, Math.floor((y - R) / LH)), r1 = Math.min(ROWS - 1, Math.ceil((y + R) / LH));
      for (let row = r0; row <= r1; row++)
        for (let c = c0; c <= c1; c++) {
          const d2 = ((c * CW + CW / 2 - x) ** 2 + (row * LH + LH / 2 - y) ** 2) / (R * R);
          const i = row * COLS + c;
          if (d2 < 1) add(i, 0.28 * e * (1 - d2) * (0.5 + 0.5 * sA[i]));
        }
    }

    const spawn = (x: number, y: number, amp = 1, t = performance.now() / 1000) =>
      rings.push({ x, y, t0: t, life: still ? 1.6 : 2.8, rmax: clamp(Math.hypot(W, H) * 0.3, 340, 820), amp });

    function idle(t: number) {
      if (still || t < nextIdle) return;
      // the open ground: left of the reel on a wide screen, anywhere on a phone
      const wide = W >= 1024;
      const x = W * (wide ? 0.03 + Math.random() * 0.42 : 0.05 + Math.random() * 0.9);
      const y = H * (0.12 + Math.random() * 0.8);
      rings.push({ x, y, t0: t, life: 3.4, rmax: 240 + Math.random() * 200, amp: 0.32 });
      nextIdle = t + 3.2 + Math.random() * 3;
    }

    let glows: [number, number, number, number, number][] = [];
    function frame(now: number) {
      raf = requestAnimationFrame(frame);
      const gap = now - last;
      if (gap < 15) return; // ~60fps on a high-refresh screen
      last = now;
      const t = now / 1000;
      const w0 = performance.now();
      frameId++;
      nT = 0;
      glows = [];

      idle(t);
      rings = rings.filter((e) => ring(e, t));
      if (!still) trail();

      // the field breathes: a few dim characters re-roll every frame
      if (!still) {
        const n = (N / 900) | 0;
        for (let k = 0; k < n; k++) {
          const i = rint(N);
          chars[i] = rint(GL);
          shade[i] = pickShade();
          pend[np++] = i;
        }
      }
      bcount.fill(0);
      let act = 0;
      for (let k = 0; k < nT; k++) {
        const i = touched[k];
        const h = Math.min(1, heat[i]);
        const L = Math.min(NL - 1, (h * NL) | 0);
        if (L < 1) continue;
        if (!still && Math.random() < h * 0.22 && np < N) {
          chars[i] = rint(GL);
          pend[np++] = i;
        }
        const B = buckets[L];
        if (bcount[L] < B.length) B[bcount[L]++] = i;
        act++;
      }
      flushPending();

      ctx!.setTransform(1, 0, 0, 1, 0, 0);
      ctx!.globalCompositeOperation = "source-over";
      ctx!.drawImage(base, 0, 0);
      ctx!.setTransform(DPR, 0, 0, DPR, 0, 0);

      // a whisper of glow under each ring
      ctx!.globalCompositeOperation = "lighter";
      for (const [x, y, g0, g1, a] of glows) {
        if (a < 0.003) continue;
        const gr = ctx!.createRadialGradient(x, y, g0, x, y, g1);
        gr.addColorStop(0, "rgba(255,110,20,0)");
        gr.addColorStop(0.5, `rgba(255,110,20,${a.toFixed(3)})`);
        gr.addColorStop(1, "rgba(255,110,20,0)");
        ctx!.fillStyle = gr;
        const gx = Math.max(0, x - g1), gw = Math.min(x + g1, openRight) - gx;
        if (gw > 0) ctx!.fillRect(gx, Math.max(0, y - g1), gw, Math.min(H, y + g1) - Math.max(0, y - g1));
      }
      ctx!.globalCompositeOperation = "source-over";

      ctx!.font = FONT;
      ctx!.textBaseline = "middle";
      for (let L = 1; L < NL; L++) {
        const n = bcount[L];
        if (!n) continue;
        ctx!.fillStyle = PAL[L];
        const B = buckets[L];
        for (let k = 0; k < n; k++) {
          const i = B[k];
          ctx!.fillText(GLYPHS[chars[i]], (i % COLS) * CW, ((i / COLS) | 0) * LH + LH / 2);
        }
      }

      stats.work = stats.work * 0.95 + (performance.now() - w0) * 0.05;
      stats.interval = stats.interval * 0.95 + gap * 0.05;
      stats.frames++;
      stats.active = act;
    }

    function sync() {
      const run = ready && !disposed && visible && document.visibilityState === "visible";
      if (run && !raf) {
        last = performance.now() - 20;
        nextIdle = last / 1000 + 1.5;
        raf = requestAnimationFrame(frame);
      } else if (!run && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    }

    // events: the hero section is the surface (the header sits outside it)
    const local = (e: PointerEvent) => {
      const r = cvs.getBoundingClientRect();
      return [e.clientX - r.left, e.clientY - r.top] as const;
    };
    const onDown = (e: PointerEvent) => {
      if (!ready) return;
      const [x, y] = local(e);
      spawn(x, y);
    };
    const onMove = (e: PointerEvent) => {
      const [x, y] = local(e);
      if (mouse.in) mouse.moved += Math.hypot(x - mouse.x, y - mouse.y);
      mouse.x = x;
      mouse.y = y;
      mouse.in = true;
    };
    const onLeave = () => {
      mouse.in = false;
    };
    const onMotion = (e: MediaQueryListEvent) => {
      still = e.matches;
      rings = [];
    };
    host.addEventListener("pointerdown", onDown);
    host.addEventListener("pointermove", onMove, { passive: true });
    host.addEventListener("pointerleave", onLeave);
    document.addEventListener("visibilitychange", sync);
    rmq.addEventListener("change", onMotion);

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      sync();
    });
    io.observe(host);

    let rz = 0, lastW = 0, lastH = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(rz);
      rz = window.setTimeout(() => {
        const r = host.getBoundingClientRect();
        if (Math.round(r.width) === lastW && Math.round(r.height) === lastH) return buildMask();
        lastW = Math.round(r.width);
        lastH = Math.round(r.height);
        if (ready) build();
      }, 120);
    });
    ro.observe(host);
    // the headline's words slide in on mount; measure again once they land
    const remask = [1600, 3200].map((ms) => window.setTimeout(buildMask, ms));

    const dev = process.env.NODE_ENV !== "production";
    // start once the face is in (or after 1.5s on the fallback), and if it
    // lands later, rebuild the grid on its real cell width
    const fontLoad = document.fonts.load(`11px ${family}`).catch(() => undefined);
    fontLoad.then(() => {
      if (!disposed && ready) build();
    });
    const fontReady = Promise.race([fontLoad, new Promise((r) => window.setTimeout(r, 1500))]);
    fontReady.then(() => {
      if (disposed) return;
      build();
      const r = host.getBoundingClientRect();
      lastW = Math.round(r.width);
      lastH = Math.round(r.height);
      ready = true;
      sync();
      if (dev) {
        (window as unknown as { __asciiRipple?: object }).__asciiRipple = {
          stats,
          get running() {
            return raf !== 0;
          },
          get grid() {
            return { CW, LH, COLS, ROWS, DPR, FONT };
          },
        };
      }
    });

    return () => {
      disposed = true;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      window.clearTimeout(rz);
      remask.forEach((id) => window.clearTimeout(id));
      io.disconnect();
      ro.disconnect();
      host.removeEventListener("pointerdown", onDown);
      host.removeEventListener("pointermove", onMove);
      host.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("visibilitychange", sync);
      rmq.removeEventListener("change", onMotion);
      if (dev) delete (window as unknown as { __asciiRipple?: object }).__asciiRipple;
    };
  }, []);

  return <canvas ref={ref} aria-hidden className="pointer-events-none absolute inset-0 block size-full" />;
}
