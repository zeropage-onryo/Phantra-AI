"use client";

/* Vesper's interactive bits (2026-10-27, lib/vesper-voice.ts holds the
   rules): what he remembers (the newest projects and renders, read off the
   studio's own lists, cached a couple of minutes per tab), his speech
   bubble, and his gaze, which follows a pointer that comes near him.

   Shared by the corner (assistant-pill.tsx) and the peek behind the Create
   box (vesper-peek.tsx), so the two never talk over each other: the last
   time he spoke is one value per tab. */
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { getMedia, listProjects } from "@/lib/studio-api";
import { LINE_MS, NO_RECENT, gaze, maySpeak, type Line, type Recent } from "@/lib/vesper-voice";

const SPOKE_KEY = "phantra.vesper.spoke";
const SAID_KEY = "phantra.vesper.said";
const CACHE_MS = 2 * 60 * 1000;

let cache: { at: number; account: string; recent: Recent } | null = null;
// the read in flight, and whose it is: a switch of workspace mid-read must
// never file one workspace's work under the other
let pending: { account: string; read: Promise<Recent> } | null = null;

async function readRecent(): Promise<Recent> {
  const [projects, media] = await Promise.all([
    listProjects().catch(() => ({ items: [] })),
    getMedia().catch(() => null),
  ]);
  return {
    projects: (projects.items ?? []).slice(0, 5).map((p) => ({
      id: p.id,
      title: p.title,
      scenes: p.concepts ?? 0,
      rendered: p.rendered ?? 0,
    })),
    renders: (media?.items ?? []).slice(0, 5).map((m) => ({
      kind: m.kind,
      model: m.model_label || "",
      prompt: (m.prompt || "").replace(/\s+/g, " ").trim().slice(0, 160),
      project: m.project_title ?? null,
    })),
  };
}

/** his memory: newest projects and renders, or empty while it loads */
export function useRecentWork(account: string | null | undefined): Recent {
  const [recent, setRecent] = useState<Recent>(() =>
    cache && account && cache.account === account ? cache.recent : NO_RECENT,
  );
  useEffect(() => {
    if (!account) return;
    if (cache && cache.account === account && Date.now() - cache.at < CACHE_MS) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- the cache is a module value
      setRecent(cache.recent);
      return;
    }
    let live = true;
    if (!pending || pending.account !== account) {
      const mine = { account, read: readRecent() };
      mine.read.finally(() => {
        if (pending === mine) pending = null;
      });
      pending = mine;
    }
    const asked = pending;
    asked.read.then((r) => {
      cache = { at: Date.now(), account: asked.account, recent: r };
      if (live) setRecent(r);
    });
    return () => {
      live = false;
    };
  }, [account]);
  return recent;
}

function lastSpoke(): number | null {
  try {
    const n = Number(sessionStorage.getItem(SPOKE_KEY));
    return n > 0 ? n : null;
  } catch {
    return null;
  }
}
function saidSet(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SAID_KEY) || "[]") as string[]);
  } catch {
    return new Set();
  }
}

/** One line at a time, gone by itself after LINE_MS. `say` refuses (and
    returns false) inside the quiet gap unless the line is urgent. */
export function useVoice() {
  const [line, setLine] = useState<Line | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  const hush = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setLine(null);
  }, []);
  const say = useCallback((l: Line, urgent = false, ms = LINE_MS) => {
    const now = Date.now();
    if (!maySpeak(lastSpoke(), now, urgent)) return false;
    try {
      sessionStorage.setItem(SPOKE_KEY, String(now));
      const said = saidSet();
      said.add(l.id);
      sessionStorage.setItem(SAID_KEY, JSON.stringify([...said].slice(-40)));
    } catch {
      /* a private window: he may speak a little more often */
    }
    setLine(l);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setLine(null), ms);
    return true;
  }, []);
  return { line, say, hush, said: saidSet };
}

/** He looks toward a pointer that comes near: sets --gx / --gy (-1..1) on
    the element, eased by CSS. Off under reduced motion and on touch. */
export function useGaze(ref: RefObject<HTMLElement | null>, where: unknown = null) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(hover: hover)").matches) return;
    let frame = 0;
    let at: { x: number; y: number } | null = null;
    const draw = () => {
      frame = 0;
      const box = el.getBoundingClientRect();
      const g = gaze({ x: box.left + box.width / 2, y: box.top + box.height * 0.35 }, at);
      el.style.setProperty("--gx", String(g.x));
      el.style.setProperty("--gy", String(g.y));
    };
    const move = (e: PointerEvent) => {
      at = { x: e.clientX, y: e.clientY };
      if (!frame) frame = requestAnimationFrame(draw);
    };
    const leave = () => {
      at = null;
      if (!frame) frame = requestAnimationFrame(draw);
    };
    window.addEventListener("pointermove", move, { passive: true });
    document.addEventListener("pointerleave", leave);
    return () => {
      window.removeEventListener("pointermove", move);
      document.removeEventListener("pointerleave", leave);
      if (frame) cancelAnimationFrame(frame);
    };
    // `where` changes when the element is drawn somewhere else (a portal)
  }, [ref, where]);
}

/** the speech bubble: tap it to act on the line, × to wave it off */
export function VoiceBubble({
  line,
  onAct,
  onClose,
  className = "",
}: {
  line: Line | null;
  onAct: (l: Line) => void;
  onClose: () => void;
  className?: string;
}) {
  if (!line) return null;
  const acts = !!(line.fill || line.project);
  return (
    <span className={`vv-bubble ${className}`} role="status" key={line.id}>
      {acts ? (
        <button type="button" className="vv-say" onClick={() => onAct(line)}>
          {line.text}
        </button>
      ) : (
        <span className="vv-say">{line.text}</span>
      )}
      <button type="button" className="vv-x" aria-label="Dismiss" onClick={onClose}>
        ×
      </button>
    </span>
  );
}
