"use client";

import { useEffect, useRef } from "react";

// The ground of the /mcp hero (2026-10-16, Mike's pick of "B · Particle form"
// from the white-morph previews, coloured "Iridescent" and a little brighter
// on 2026-10-17): soft pastel points on black drifting between a
// sphere, a ring and a wave while turning slowly. Canvas 2D, no images. It
// draws one still frame under reduced motion, stops while the hero is off
// screen or the tab is hidden, and uses fewer points on small screens. The
// scrim keeps a dark centre behind the copy. Decorative, so hidden from
// assistive tech.

type Pt = { u: number; phi: number; th: number; j: number };

function makePoints(n: number): Pt[] {
  const pts: Pt[] = [];
  for (let i = 0; i < n; i++) {
    pts.push({
      u: i / n,
      phi: Math.acos(1 - (2 * (i + 0.5)) / n),
      th: Math.PI * (1 + Math.sqrt(5)) * i,
      j: (Math.sin(i * 12.9898) * 43758.5453) % 1,
    });
  }
  return pts;
}

function shape(p: Pt, which: number, t: number): [number, number, number] {
  if (which === 0) {
    return [Math.sin(p.phi) * Math.cos(p.th), Math.cos(p.phi), Math.sin(p.phi) * Math.sin(p.th)];
  }
  if (which === 1) {
    const a = p.u * Math.PI * 2;
    const R = 0.72;
    const r = 0.3;
    return [(R + r * Math.cos(p.th)) * Math.cos(a), r * Math.sin(p.th), (R + r * Math.cos(p.th)) * Math.sin(a)];
  }
  const gx = ((p.u * 47) % 1) * 2 - 1;
  const gz = (Math.floor(p.u * 47) / 47) * 2 - 1;
  return [gx * 1.1, 0.22 * Math.sin(gx * 4 + t * 0.9) * Math.cos(gz * 3 - t * 0.6), gz * 1.1];
}

// hue in degrees, saturation and lightness in percent -> 0-255 channels
function hsl(h: number, s: number, l: number): [number, number, number] {
  const sat = s / 100;
  const lig = l / 100;
  const hue = ((h % 360) + 360) % 360;
  const k = (n: number) => (n + hue / 30) % 12;
  const a = sat * Math.min(lig, 1 - lig);
  const f = (n: number) => lig - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [Math.round(255 * f(0)), Math.round(255 * f(8)), Math.round(255 * f(4))];
}

export function ParticleMorph() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    const ctx = cv?.getContext("2d");
    if (!cv || !ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let pts: Pt[] = [];
    let W = 0;
    let H = 0;
    let t = 6;
    let last = 0;
    let raf = 0;
    let visible = true;

    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      const cx = W / 2;
      const cy = H * 0.47;
      const S = Math.min(W, H) * (W < 640 ? 0.42 : 0.34);
      const cyc = (t * 0.08) % 3;
      const from = Math.floor(cyc);
      const to = (from + 1) % 3;
      let f = cyc - from;
      f = f < 0.6 ? 0 : (f - 0.6) / 0.4;
      f = f * f * (3 - 2 * f);
      const ry = t * 0.15;
      const cosY = Math.cos(ry);
      const sinY = Math.sin(ry);
      const cosX = Math.cos(0.35);
      const sinX = Math.sin(0.35);
      for (const p of pts) {
        const A = shape(p, from, t);
        const B = shape(p, to, t);
        const br = 1 + 0.03 * Math.sin(t * 0.7 + p.j * 6.28);
        const x = (A[0] + (B[0] - A[0]) * f) * br;
        const y = (A[1] + (B[1] - A[1]) * f) * br;
        const z = (A[2] + (B[2] - A[2]) * f) * br;
        const x2 = x * cosY + z * sinY;
        const z2 = -x * sinY + z * cosY;
        const y2 = y * cosX - z2 * sinX;
        const z3 = y * sinX + z2 * cosX;
        const per = 2.6 / (2.6 + z3);
        const px = cx + x2 * S * per;
        const py = cy + y2 * S * per;
        // quieter behind the copy: points fade toward the centre of the text block
        const dx = (px - cx) / (W * (W < 640 ? 0.48 : 0.3));
        const dy = (py - cy) / (H * 0.24);
        const quiet = Math.min(1, 0.22 + 0.78 * Math.min(1, dx * dx + dy * dy));
        const a = Math.min(1, 0.38 + 0.66 * ((1 - z3) / 2)) * quiet;
        // iridescent: a soft pastel hue that runs across the form and drifts with time
        const [r, g, bl] = hsl((x2 * 0.5 + 0.5) * 300 + t * 12, 75, 82);
        const s = 2.1 * per;
        ctx.fillStyle = `rgba(${r},${g},${bl},${a.toFixed(3)})`;
        ctx.fillRect(px, py, s, s);
      }
    };

    const size = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = cv.clientWidth;
      H = cv.clientHeight;
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      pts = makePoints(W < 640 ? 1200 : 2200);
      draw();
    };

    const loop = (now: number) => {
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
      last = now;
      if (visible && !document.hidden && !reduce.matches) {
        t += dt;
        draw();
      }
      raf = requestAnimationFrame(loop);
    };

    const ro = new ResizeObserver(size);
    ro.observe(cv);
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
    });
    io.observe(cv);
    const onMotion = () => draw();
    reduce.addEventListener("change", onMotion);
    size();
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      reduce.removeEventListener("change", onMotion);
    };
  }, []);

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-black">
      <canvas ref={ref} className="absolute inset-0 block h-full w-full" />
      <span className="absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_50%_46%,rgba(0,0,0,0.55)_0%,rgba(0,0,0,0)_70%)]" />
      <span className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0.6)_0%,rgba(0,0,0,0)_18%,rgba(0,0,0,0)_78%,rgba(0,0,0,1)_100%)]" />
    </div>
  );
}
