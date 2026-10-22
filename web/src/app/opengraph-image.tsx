import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";

import { OWL, VIEWBOX, WORD } from "@/components/owl-lockup-paths";

// The share card for the home page (2026-10-16, Mike's pick of "Option A ·
// The lockup" off the share-card options page). It replaced the September
// noir card (red uppercase "CREATES FOR YOU.", a red ring dot), which the
// rename had only re-worded, so every shared phantra.ai link still looked
// like the old site.
//
// The editorial skin's warm black, the owl lockup at rest top left, the
// hero's headline in the serif, and the hero's ASCII field with one orange
// ripple on the right. Rendered at build time by Next from this route; the
// <meta og:image> tags in layout.tsx (and lib/page-meta.ts) point here.
//
// Fonts are the OFL Lora and JetBrains Mono files in web/assets/og-fonts/,
// read off disk at build: Satori takes ttf/otf/woff only, and a fetch at
// build time is one more way for a deploy to fail.
//
// The /make and /models pages draw their own cards (landing-pages/og.tsx);
// they still use the older plate.

export const alt = "Phantra — The AI content studio that creates for you.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BG = "#0b0a08"; // .editorial --background
const INK = "#fafafa";
const MUTED = "#9d9a95";
const DOT = "#2a2724"; // the field's resting characters
const EMBER = "#ff7a1a"; // the ripple, as the hero's ASCII layer draws it
const EMBER_DIM = "#b85414";

const fontDir = join(process.cwd(), "assets/og-fonts");
const lora = readFile(join(fontDir, "lora-400.woff"));
const mono = readFile(join(fontDir, "jetbrains-mono-400.woff"));

// The ASCII field: a fixed seed so every build draws the same card.
const FIELD = { cols: 134, rows: 36, size: 15, line: 18, cx: 112, cy: 17 };
const CHARS = ".,:;-~=+*";
const RING = "oO0@*";

type Run = { text: string; color: string };

function field(): Run[][] {
  let seed = 7;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed / 2147483648;
  };
  const pick = (s: string) => s[Math.floor(rand() * s.length)];
  const lines: Run[][] = [];
  for (let y = 0; y < FIELD.rows; y++) {
    const runs: Run[] = [];
    const push = (ch: string, color: string) => {
      const last = runs[runs.length - 1];
      if (last && last.color === color) last.text += ch;
      else runs.push({ text: ch, color });
    };
    for (let x = 0; x < FIELD.cols; x++) {
      const on = rand() < 0.55;
      const ch = pick(CHARS);
      if (!on) {
        push(" ", DOT);
        continue;
      }
      // a character cell is about half as wide as it is tall
      const d = Math.hypot((x - FIELD.cx) * 0.55, y - FIELD.cy);
      if (Math.abs(d - 9) < 0.9) push(pick(RING), EMBER);
      else if (Math.abs(d - 14) < 0.7) push(ch, EMBER_DIM);
      else push(ch, DOT);
    }
    lines.push(runs);
  }
  return lines;
}

/** The lockup at rest: the owl behind the p, the word in front with a gap cut around it. */
function Lockup({ width }: { width: number }) {
  const { x, y, w, h } = VIEWBOX;
  return (
    <svg width={width} height={(width * h) / w} viewBox={`${x} ${y} ${w} ${h}`}>
      <path d={OWL} fill={INK} fillRule="evenodd" />
      {/* the 12-unit gap the site's WALL clip makes, drawn as a stroke in the background colour */}
      <path d={WORD} fill={BG} stroke={BG} strokeWidth={24} strokeLinejoin="round" />
      <path d={WORD} fill={INK} fillRule="evenodd" />
    </svg>
  );
}

export default async function OpenGraphImage() {
  const lines = field();
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: BG }}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            fontFamily: "JetBrains Mono",
            fontSize: FIELD.size,
            lineHeight: `${FIELD.line}px`,
          }}
        >
          {lines.map((runs, i) => (
            <div key={i} style={{ display: "flex", whiteSpace: "pre", height: FIELD.line }}>
              {runs.map((run, j) => (
                <span key={j} style={{ color: run.color }}>
                  {run.text}
                </span>
              ))}
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", left: 72, top: 74, display: "flex" }}>
          <Lockup width={276} />
        </div>
        <div
          style={{
            position: "absolute",
            left: 72,
            bottom: 108,
            width: 792,
            display: "flex",
            fontFamily: "Lora",
            fontSize: 91,
            lineHeight: 1.02,
            letterSpacing: "-0.025em",
            color: INK,
          }}
        >
          The AI content studio that creates for you.
        </div>
        <div
          style={{
            position: "absolute",
            left: 72,
            bottom: 60,
            display: "flex",
            fontFamily: "JetBrains Mono",
            fontSize: 19,
            letterSpacing: "0.06em",
            color: MUTED,
          }}
        >
          phantra.ai
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Lora", data: await lora, weight: 400, style: "normal" },
        { name: "JetBrains Mono", data: await mono, weight: 400, style: "normal" },
      ],
    },
  );
}
