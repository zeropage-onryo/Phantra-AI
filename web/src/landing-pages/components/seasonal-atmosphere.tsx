// The seasonal look's one decoration (2026-10-27, the Halloween page):
// a low moon glow, a band of night fog over the hero, and a few bats that
// drift across it. Drawn only inside the page's season (make-page.tsx),
// behind nothing a person clicks (pointer-events: none) and quiet enough
// that the hero's type reads through it. Reduced motion keeps the moon and
// the fog and parks the bats.
const BAT =
  "M0 6C2 2 4 2 6 5C7 3 9 3 10 5C11 3 13 3 14 5C16 2 18 2 20 6C17 5 15 6 14 8C12 7 11 8 10 10C9 8 8 7 6 8C5 6 3 5 0 6Z";

const BATS = [
  { top: "13%", size: 40, dur: 26, delay: -4 },
  { top: "24%", size: 28, dur: 34, delay: -16 },
  { top: "8%", size: 22, dur: 40, delay: -27 },
  { top: "34%", size: 32, dur: 30, delay: -9 },
];

export function SeasonalAtmosphere() {
  return (
    <div aria-hidden className="seasonal-atmosphere pointer-events-none absolute inset-x-0 top-0 z-[1] h-[min(900px,100svh)] overflow-hidden">
      <style>{`
        .seasonal-atmosphere .moon { position:absolute; right:6%; top:70px; width:clamp(120px,14vw,210px); aspect-ratio:1; border-radius:9999px;
          background: radial-gradient(circle at 42% 40%, rgba(255,236,200,0.85) 0%, rgba(255,196,120,0.55) 34%, rgba(255,122,26,0.18) 58%, rgba(255,122,26,0) 70%);
          opacity:.7; }
        .seasonal-atmosphere .fog { position:absolute; inset:0;
          background: radial-gradient(70% 55% at 50% 0%, rgba(91,42,130,0.30) 0%, rgba(91,42,130,0) 70%),
                      linear-gradient(180deg, rgba(11,8,16,0) 55%, rgba(11,8,16,0.0) 100%); }
        .seasonal-atmosphere .bat { position:absolute; left:-40px; fill:#8a63a8; opacity:.55; }
        @media (prefers-reduced-motion: no-preference) {
          .seasonal-atmosphere .bat { animation: seasonal-bat linear infinite; }
          @keyframes seasonal-bat {
            0% { transform: translate3d(0,0,0) scaleY(1); }
            25% { transform: translate3d(28vw,-18px,0) scaleY(.7); }
            50% { transform: translate3d(56vw,10px,0) scaleY(1); }
            75% { transform: translate3d(84vw,-12px,0) scaleY(.7); }
            100% { transform: translate3d(112vw,0,0) scaleY(1); }
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .seasonal-atmosphere .bat:nth-child(n) { left:auto; right:22%; }
        }
      `}</style>
      <div className="fog" />
      <div className="moon" />
      {BATS.map((b, i) => (
        <svg
          key={i}
          className="bat"
          viewBox="0 0 20 10"
          width={b.size}
          height={b.size / 2}
          style={{ top: b.top, animationDuration: `${b.dur}s`, animationDelay: `${b.delay}s` }}
        >
          <path d={BAT} />
        </svg>
      ))}
    </div>
  );
}
