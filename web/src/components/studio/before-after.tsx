"use client";

/* Before and after on one slider (lib/before-after.ts): the result drawn at
   its own shape, the original over it clipped at the divider. Drag anywhere
   (a range input lies over the picture, so the keyboard works too). With
   `still` it is a fixed half-and-half: a tile that is itself a button. */
import { useState } from "react";
import "@/components/studio/before-after.css";
/* eslint-disable @next/next/no-img-element */

export function BeforeAfter({
  before,
  after,
  alt = "",
  still = false,
  start = 50,
}: {
  before: string;
  after: string;
  alt?: string;
  still?: boolean;
  start?: number;
}) {
  const [split, setSplit] = useState(start);
  // an original that will not load (gone from the store, a dead link): the
  // result alone, drawn as it always was, rather than half a broken picture
  const [lost, setLost] = useState(false);
  if (lost) return <img className="ba-alone" src={after} alt={alt ? `${alt}: after` : ""} />;
  return (
    <div className="ba" data-still={still ? "1" : undefined}>
      <img className="ba-after" src={after} alt={alt ? `${alt}: after` : ""} />
      <img
        className="ba-before"
        src={before}
        alt={alt ? `${alt}: before` : ""}
        style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
        onError={() => setLost(true)}
      />
      <span className="ba-line" aria-hidden style={{ left: `${split}%` }} />
      {still ? null : (
        <>
          <span className="ba-tag ba-tag-b" aria-hidden>
            Before
          </span>
          <span className="ba-tag ba-tag-a" aria-hidden>
            After
          </span>
          <input
            className="ba-range"
            type="range"
            min={0}
            max={100}
            value={split}
            aria-label="Compare before and after"
            onChange={(e) => setSplit(Number(e.target.value))}
          />
        </>
      )}
    </div>
  );
}
