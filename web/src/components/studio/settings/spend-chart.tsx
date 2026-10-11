"use client";

/* Credits spent per day (Settings → Usage, 2026-10-11): one series, one
   colour -- the signal, checked against the card with the dataviz skill's
   validator -- thin bars with a rounded data end, growing from one
   baseline, 2px of surface between neighbours, a solid hairline grid.

   Reading a value never depends on the pointer: hovering or arrowing onto
   a day shows it, and every day with spend is also in a table a screen
   reader gets (and the history under the chart is the same numbers, line
   by line). The geometry is lib/credit-history.ts. */
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { barPath, dayLabel, layoutBars, niceMax, tickDays, type Summary } from "@/lib/credit-history";
import { creditsText, num } from "@/lib/credits";

const HEIGHT = 168;
const PAD = { top: 10, right: 6, bottom: 24, left: 44 };

export function SpendChart({ days }: { days: Summary["days"] }) {
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState<number | null>(null);

  // drawn at real pixels, not scaled: axis text must stay its own size
  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const measure = () => setWidth(Math.max(240, Math.round(el.clientWidth)));
    measure();
    const watch = new ResizeObserver(measure);
    watch.observe(el);
    return () => watch.disconnect();
  }, []);

  const values = days.map((d) => d.credits);
  const max = niceMax(Math.max(0, ...values));
  const plotW = width - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const bars = layoutBars(values, plotW, plotH, max);
  const slot = days.length ? plotW / days.length : 0;
  const grid = [0, max / 2, max];
  const at = active !== null && days[active] ? { ...days[active], bar: bars[active] } : null;

  const move = (e: KeyboardEvent<HTMLDivElement>) => {
    const delta = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (e.key === "Escape") return setActive(null);
    if (e.key === "Home") return setActive(0);
    if (e.key === "End") return setActive(days.length - 1);
    if (!delta || !days.length) return;
    e.preventDefault();
    setActive((i) => Math.min(days.length - 1, Math.max(0, (i ?? (delta > 0 ? -1 : days.length)) + delta)));
  };

  return (
    <div
      className="zset-chart"
      ref={frame}
      tabIndex={0}
      role="group"
      aria-label="Credits spent per day. Use the left and right arrow keys to read each day."
      onKeyDown={move}
      onBlur={() => setActive(null)}
      onPointerLeave={() => setActive(null)}
    >
      <svg width={width} height={HEIGHT} role="presentation" aria-hidden>
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {grid.map((v) => {
            const y = plotH - (v / max) * plotH;
            return (
              <g key={v}>
                <line className={v === 0 ? "zset-chart-base" : "zset-chart-grid"} x1={0} x2={plotW} y1={y} y2={y} />
                <text className="zset-chart-tick" x={-10} y={y} dy="0.32em" textAnchor="end">
                  {num(v)}
                </text>
              </g>
            );
          })}
          {bars.map((bar, i) => (
            <path key={days[i].day} className="zset-chart-bar" data-active={i === active ? "1" : undefined} d={barPath(bar)} />
          ))}
          {tickDays(days.length).map((i) => (
            <text
              key={days[i].day}
              className="zset-chart-tick"
              x={i * slot + slot / 2}
              y={plotH + 16}
              textAnchor={i === 0 ? "start" : i === days.length - 1 ? "end" : "middle"}
              dx={i === 0 ? -slot / 2 : i === days.length - 1 ? slot / 2 : 0}
            >
              {dayLabel(days[i].day)}
            </text>
          ))}
          {/* the hit targets: the whole column of each day, not just its bar */}
          {days.map((d, i) => (
            <rect
              key={d.day}
              x={i * slot}
              y={0}
              width={slot}
              height={plotH}
              fill="transparent"
              onPointerEnter={() => setActive(i)}
              onPointerDown={() => setActive(i)}
            />
          ))}
        </g>
      </svg>
      {at ? (
        <div
          className="zset-chart-tip"
          style={{
            left: Math.min(width - 60, Math.max(60, PAD.left + at.bar.x + at.bar.width / 2)),
            top: PAD.top + at.bar.y,
          }}
        >
          <b>{creditsText(at.credits)}</b>
          <span>{dayLabel(at.day)}</span>
        </div>
      ) : null}
      {/* said once when a day is read, for a screen reader following the arrow keys */}
      <span className="sr-only" aria-live="polite">
        {at ? `${dayLabel(at.day)}: ${creditsText(at.credits)}` : ""}
      </span>
      <table className="sr-only">
        <caption>Credits spent per day, days with spend only</caption>
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Credits</th>
          </tr>
        </thead>
        <tbody>
          {days
            .filter((d) => d.credits > 0)
            .map((d) => (
              <tr key={d.day}>
                <th scope="row">{dayLabel(d.day)}</th>
                <td>{num(d.credits)}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
