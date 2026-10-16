"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { AnimatePresence, animate, motion } from "motion/react";
import type { Mood } from "@/lib/mascot";
import { useStill } from "@/components/motion/use-still";
import { Flicker } from "@/components/landing/vesper-motion";
import {
  BRIEFS,
  CLIP_SECONDS,
  DEMO_MODELS,
  LOOKS,
  PREFILL_EVENT,
  SCENES,
  SCENE_STILL,
  TIMECODES,
  VESPER_ALT,
  VESPER_MOODS,
  customBrief,
  priceFor,
  still as stillOf,
  vesperSrc,
  type Brief,
  type BriefKey,
} from "@/components/landing/vesper-content";

// The lantern stage's playable demo (2026-10-15, the mockup Mike approved):
// a SCRIPTED walk through what Vesper does in the studio -- the plan, the
// stills, the priced checkpoint, the clips. Nothing here calls a model,
// signs anybody in or spends: every line is fixed copy, every still is a
// poster the site already ships, and the credit figures are read off the
// generated catalogue (vesper-content.ts) and labelled as examples.
//
// The first render (the server's, and the page with JS off) is the demo at
// rest: the Sneaker brief played through to the price checkpoint, so the
// stage reads complete before anyone touches it.

type Status = "Listening" | "Planning shots" | "Drawing stills" | "Rendering" | "Waiting for your OK" | "Ready to cut";
type StageState = "wait" | "think" | "idle";

const MOOD_OF: Record<Status, Mood> = {
  Listening: "listen",
  "Planning shots": "think",
  "Drawing stills": "think",
  Rendering: "think",
  "Waiting for your OK": "awake",
  "Ready to cut": "made",
};
const LAMP = { calm: "#9fd8ff", made: "#7debaa", oops: "#ff5c5c" } as const;

type Demo = {
  key: BriefKey | "custom" | null;
  brief: Brief | null;
  look: number[];
  flash: number[];
  stills: string[];
  fading: boolean[];
  on: boolean[];
  model: number;
  /** cards made after the first render rise in; the resting ones do not */
  fresh: boolean;
  plan: boolean;
  planBusy: boolean;
  stillsShown: boolean;
  stillsIn: number;
  stillsDone: boolean;
  price: boolean;
  locked: boolean;
  prog: { n: number; k: number; fill: boolean } | null;
  clips: boolean;
};

const EMPTY: Demo = {
  key: null,
  brief: null,
  look: [0, 0, 0],
  flash: [0, 0, 0],
  stills: [],
  fading: [false, false, false],
  on: [true, true, true],
  model: 0,
  fresh: true,
  plan: false,
  planBusy: false,
  stillsShown: false,
  stillsIn: 0,
  stillsDone: false,
  price: false,
  locked: false,
  prog: null,
  clips: false,
};

const fromBrief = (key: BriefKey | "custom", brief: Brief): Demo => ({
  ...EMPTY,
  key,
  brief,
  look: brief.look.slice(),
  stills: brief.stills.slice(),
});

/* the stage at rest: the Sneaker brief, planned, drawn, approved, priced */
const REST: Demo = {
  ...fromBrief("sneaker", BRIEFS.sneaker),
  fresh: false,
  plan: true,
  planBusy: true,
  stillsShown: true,
  stillsIn: 3,
  stillsDone: true,
  price: true,
};
const REST_LINE = { lead: "Stills approved.", rest: " Auto never skips this step." };
/* Vesper's lines for the plan, the stills and the clips: the flow says them,
   and on a phone the swipe track says them again for the board in view */
const PLAN_LINE = {
  lead: "Here’s the plan:",
  rest: " three shots, 5 s each. Pick a look for any shot, then I’ll draw the stills.",
};
const DRAW_LINE = {
  lead: "Drawing the stills.",
  rest: " These set the look of each clip. Keep the ones you like, redraw the rest.",
};
const DONE_LINE = { lead: "Your shots are ready to cut.", rest: " Trim, reorder or swap a model in the editor." };

/* phones (<=760px, 2026-10-16, Mike's pick "B · Swipe"): the plan, the stills
   and the price become one swipe track, and the lantern takes each board's
   colour */
const PHONE = "(max-width: 760px)";
type Board = "plan" | "stills" | "front";
const BOARD_LAMP: Record<Board, string> = { plan: LAMP.calm, stills: "#ffc98a", front: "#ffe0a3" };
const BOARD_NAME: Record<Board, string> = { plan: "The plan", stills: "The stills", front: "Before render" };
/* the boards on the stage, in order: a phone swipes between these */
const boardsOf = (x: Demo): Board[] => {
  if (!x.brief) return [];
  const b: Board[] = [];
  if (x.plan) b.push("plan");
  if (x.stillsShown) b.push("stills");
  if (x.price || x.prog || x.clips) b.push("front");
  return b;
};

const count = (d: Demo) => d.on.filter(Boolean).length;
const clipsWord = (n: number) => (n === 1 ? "clip" : "clips");

const CHECK = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
    <path d="M3 8.5l3 3 7-7" />
  </svg>
);
const REDO = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden>
    <path d="M13 8a5 5 0 1 1-1.5-3.6" />
    <path d="M13 2.5v3h-3" />
  </svg>
);
const PREV = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
    <path d="M10 3L5 8l5 5" />
  </svg>
);
const NEXT = (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
    <path d="M6 3l5 5-5 5" />
  </svg>
);
const PLAY = (
  <svg viewBox="0 0 16 16" fill="#fff" aria-hidden>
    <path d="M4.5 2.8v10.4l8.5-5.2z" />
  </svg>
);

function Seg({
  labels,
  active,
  label,
  onPick,
  disabled,
  id,
}: {
  labels: readonly string[];
  active: number;
  label?: string;
  onPick: (i: number) => void;
  disabled?: boolean;
  id?: string;
}) {
  return (
    <div className="vh-seg" role="group" aria-label={label} aria-labelledby={id}>
      {labels.map((l, j) => (
        <button key={l} type="button" aria-pressed={j === active} disabled={disabled} onClick={() => onPick(j)}>
          {l}
        </button>
      ))}
    </div>
  );
}

/* eslint-disable @next/next/no-img-element -- posters already in public/ and the mascot set on R2, all sized by CSS */
export function VesperStage({ captions }: { captions: ReactNode }) {
  const still = useStill();
  const stillRef = useRef(still);
  useEffect(() => {
    stillRef.current = still;
  }, [still]);

  const [d, setD] = useState<Demo>(REST);
  const dRef = useRef<Demo>(REST);
  const upd = useCallback((fn: (d: Demo) => Demo) => {
    dRef.current = fn(dRef.current);
    setD(dRef.current);
  }, []);

  const [status, setStatusState] = useState<{ text: Status; s: StageState; base: Mood }>({
    text: "Waiting for your OK",
    s: "wait",
    base: "awake",
  });
  const statusRef = useRef(status);
  const [voice, setVoice] = useState({ ...REST_LINE, typed: (REST_LINE.lead + REST_LINE.rest).length, dots: false });
  const [log, setLog] = useState<string[]>([]);
  const [hold, setHold] = useState<Mood | null>(null);
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [listening, setListening] = useState(false);
  const [auto, setAuto] = useState(false);
  const autoRef = useRef(auto);
  const pickAuto = (on: boolean) => {
    autoRef.current = on;
    setAuto(on);
  };
  const [msg, setMsg] = useState("");
  const [figure, setFigureState] = useState(priceFor(DEMO_MODELS[0], 3));
  const figureRef = useRef(figure);
  const setFigure = (v: number) => {
    figureRef.current = v;
    setFigureState(v);
  };
  const figureRun = useRef<{ stop: () => void } | null>(null);
  const run = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const form = useRef<HTMLFormElement>(null);

  /* every mood is fetched up front, so a crossfade never waits on a load */
  useEffect(() => {
    for (const m of VESPER_MOODS) {
      const img = new Image();
      img.src = vesperSrc(m);
    }
    return () => {
      if (holdTimer.current) clearTimeout(holdTimer.current);
      figureRun.current?.stop();
      run.current += 1;
    };
  }, []);

  const wait = (ms: number) =>
    stillRef.current ? Promise.resolve() : new Promise<void>((r) => setTimeout(r, ms));

  const setStatus = (text: Status, s: StageState, mood?: Mood) => {
    const next = { text, s, base: mood ?? MOOD_OF[text] };
    statusRef.current = next;
    setStatusState(next);
  };
  const holdMood = (m: Mood, ms: number) => {
    setHold(m);
    if (holdTimer.current) clearTimeout(holdTimer.current);
    holdTimer.current = setTimeout(() => setHold(null), ms);
  };
  const clearHold = () => {
    if (holdTimer.current) clearTimeout(holdTimer.current);
    setHold(null);
  };

  /* Vesper speaks as a subtitle over the stage: dots, then the line typed */
  const say = async (lead: string, rest: string, tok: number, quiet = false): Promise<boolean> => {
    if (!quiet) setLog((l) => [...l, `Vesper: ${lead}${rest}`]);
    const n = (lead + rest).length;
    if (stillRef.current) {
      setVoice({ lead, rest, typed: n, dots: false });
      return tok === run.current;
    }
    setVoice({ lead, rest, typed: 0, dots: true });
    await wait(600);
    if (tok !== run.current) return false;
    setVoice({ lead, rest, typed: 0, dots: false });
    await new Promise<void>((res) => {
      const step = Math.min(25, 1200 / n);
      const t0 = performance.now();
      const tick = (now: number) => {
        if (tok !== run.current) return res();
        const k = Math.min(n, Math.floor((now - t0) / step) + 1);
        setVoice((v) => ({ ...v, typed: k }));
        if (k < n) requestAnimationFrame(tick);
        else res();
      };
      requestAnimationFrame(tick);
    });
    return tok === run.current;
  };

  /* ---- the flow ---- */

  async function start(key: BriefKey | "custom", text?: string) {
    const tok = ++run.current;
    const brief = key === "custom" ? customBrief(text ?? "") : BRIEFS[key];
    clearHold();
    upd(() => fromBrief(key, brief));
    setLog([`You: ${brief.say}`]);
    if (!stillRef.current) holdMood("listen", 900);
    setStatus("Planning shots", "think");
    const ok = await say(PLAN_LINE.lead, PLAN_LINE.rest, tok);
    if (!ok) return;
    upd((x) => ({ ...x, plan: true }));
    setStatus("Waiting for your OK", "wait");
  }

  async function drawStills() {
    const tok = run.current;
    if (dRef.current.planBusy) return;
    upd((x) => ({ ...x, planBusy: true }));
    setStatus("Drawing stills", "think");
    const ok = await say(DRAW_LINE.lead, DRAW_LINE.rest, tok);
    if (!ok) return;
    upd((x) => ({ ...x, stillsShown: true, stillsIn: 0 }));
    for (let i = 0; i < 3; i++) {
      await wait(250);
      if (tok !== run.current) return;
      upd((x) => ({ ...x, stillsIn: i + 1 }));
    }
    if (autoRef.current) {
      await wait(300);
      if (tok !== run.current) return;
      await approveStills();
    } else setStatus("Waiting for your OK", "wait");
  }

  async function approveStills() {
    const tok = run.current;
    const cur = dRef.current;
    if (count(cur) === 0 || cur.stillsDone) return;
    upd((x) => ({ ...x, stillsDone: true }));
    setStatus("Planning shots", "think");
    const n = count(cur);
    const ok = await say(autoRef.current ? "Stills approved on Auto." : REST_LINE.lead, REST_LINE.rest, tok);
    if (!ok) return;
    figureRun.current?.stop();
    setFigure(priceFor(DEMO_MODELS[dRef.current.model], n));
    upd((x) => ({ ...x, price: true }));
    setStatus("Waiting for your OK", "wait");
  }

  function pickModel(j: number) {
    if (dRef.current.locked) return;
    upd((x) => ({ ...x, model: j }));
    const to = priceFor(DEMO_MODELS[j], count(dRef.current));
    figureRun.current?.stop();
    if (stillRef.current) return setFigure(to);
    figureRun.current = animate(figureRef.current, to, {
      duration: 0.38,
      ease: [0.33, 1, 0.68, 1],
      onUpdate: (v) => setFigure(Math.round(v)),
    });
  }

  async function approveRender() {
    const tok = run.current;
    const cur = dRef.current;
    if (cur.locked) return;
    upd((x) => ({ ...x, locked: true }));
    const m = DEMO_MODELS[cur.model];
    const n = count(cur);
    setStatus("Rendering", "think");
    const ok = await say("Rendering…", ` ${n} ${clipsWord(n)} on ${m.name}.`, tok);
    if (!ok) return;
    upd((x) => ({ ...x, prog: { n, k: 0, fill: false } }));
    if (!stillRef.current) {
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      upd((x) => ({ ...x, prog: x.prog && { ...x.prog, fill: true } }));
      for (let k = 1; k <= n; k++) {
        await wait(2000 / n);
        if (tok !== run.current) return;
        upd((x) => ({ ...x, prog: x.prog && { ...x.prog, k } }));
      }
    } else upd((x) => ({ ...x, prog: { n, k: n, fill: true } }));
    const ok2 = await say(DONE_LINE.lead, DONE_LINE.rest, tok);
    if (!ok2) return;
    upd((x) => ({ ...x, clips: true }));
    setStatus("Ready to cut", "idle");
  }

  async function notYet() {
    const tok = run.current;
    if (dRef.current.locked) return;
    holdMood("oops", 2000);
    const ok = await say("No problem.", " Change a shot or a model, and I’ll re-price it.", tok);
    if (ok) setStatus("Waiting for your OK", "wait");
  }

  function greet() {
    const tok = ++run.current;
    clearHold();
    upd(() => ({ ...EMPTY }));
    setLog([]);
    setStatus("Listening", "idle", "awake");
    void say(
      "Hi, I’m Vesper.",
      " Tell me what you’re making, or pick a scene below. I’ll plan it, draw it, and show you the price before anything renders.",
      tok,
    );
    input.current?.focus({ preventScroll: true });
  }

  function pickLook(i: number, j: number) {
    upd((x) => {
      const look = x.look.slice();
      const flash = x.flash.slice();
      look[i] = j;
      flash[i] += 1;
      return { ...x, look, flash };
    });
  }

  function toggleKeep(i: number) {
    if (dRef.current.stillsDone) return;
    upd((x) => {
      const on = x.on.slice();
      on[i] = !on[i];
      return { ...x, on };
    });
  }

  function redraw(i: number) {
    const cur = dRef.current;
    if (cur.stillsDone || !cur.brief) return;
    const all = cur.brief.stills.concat(cur.brief.pool);
    const at = all.indexOf(cur.stills[i]);
    let next: string | null = null;
    for (let k = 1; k <= all.length; k++) {
      const cand = all[(at + k) % all.length];
      if (!cur.stills.includes(cand)) {
        next = cand;
        break;
      }
    }
    if (!next) return;
    const swap = (fading: boolean) =>
      upd((x) => {
        const stills = x.stills.slice();
        const f = x.fading.slice();
        stills[i] = next!;
        f[i] = fading;
        return { ...x, stills, fading: f };
      });
    if (stillRef.current) return swap(false);
    upd((x) => {
      const f = x.fading.slice();
      f[i] = true;
      return { ...x, fading: f };
    });
    setTimeout(() => {
      swap(true);
      setTimeout(() => unfade(i), 600);
    }, 180);
  }
  const unfade = (i: number) =>
    upd((x) => {
      if (!x.fading[i]) return x;
      const f = x.fading.slice();
      f[i] = false;
      return { ...x, fading: f };
    });

  /* a starting point or a showcase tile puts its line in the composer */
  useEffect(() => {
    const onPrefill = (e: Event) => {
      const text = (e as CustomEvent<string | null>).detail;
      form.current?.scrollIntoView({ behavior: stillRef.current ? "auto" : "smooth", block: "center" });
      if (typeof text === "string") setMsg(text);
      const el = input.current;
      if (!el) return;
      el.focus({ preventScroll: true });
      if (typeof text === "string")
        requestAnimationFrame(() => {
          try {
            el.setSelectionRange(text.length, text.length);
          } catch {}
        });
    };
    window.addEventListener(PREFILL_EVENT, onPrefill);
    return () => window.removeEventListener(PREFILL_EVENT, onPrefill);
  }, []);

  function send(e: FormEvent) {
    e.preventDefault();
    const v = msg.trim();
    if (!v) return input.current?.focus();
    setMsg("");
    void start("custom", v);
  }

  /* ---- phones: the plan, the stills and the price as one swipe track ----
     The swiping is CSS scroll-snap (vesper.css, <=760px). This only reads
     which board the track came to rest on, so Vesper says that board's line
     and the lantern takes its colour, and it follows the flow to each new
     board. Above 760px the track is `display: contents` and none of this
     runs. */
  const [phone, setPhone] = useState(false);
  const phoneRef = useRef(false);
  const track = useRef<HTMLDivElement>(null);
  const [board, setBoard] = useState(0);
  const boardRef = useRef(0);
  const settle = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(PHONE);
    const apply = () => {
      phoneRef.current = mq.matches;
      setPhone(mq.matches);
    };
    apply();
    /* at rest a phone opens on the plan, so Vesper starts there too */
    if (mq.matches && dRef.current === REST) {
      const next = { text: "Waiting for your OK" as Status, s: "wait" as StageState, base: "listen" as Mood };
      statusRef.current = next;
      setStatusState(next);
      setVoice({ ...PLAN_LINE, typed: (PLAN_LINE.lead + PLAN_LINE.rest).length, dots: false });
    }
    mq.addEventListener("change", apply);
    return () => {
      mq.removeEventListener("change", apply);
      if (settle.current) clearTimeout(settle.current);
    };
  }, []);

  /* the boards drawn in the track: an empty slot is hidden on a phone */
  const slotsIn = useCallback(
    () =>
      Array.from(track.current?.children ?? []).filter(
        (el): el is HTMLElement => el instanceof HTMLElement && el.classList.contains("vh-slot") && el.childElementCount > 0,
      ),
    [],
  );
  const goTo = useCallback(
    (i: number) => {
      const el = track.current;
      const slot = slotsIn()[i];
      if (!el || !slot) return;
      const pad = parseFloat(getComputedStyle(el).paddingLeft) || 0;
      el.scrollTo({ left: slot.offsetLeft - pad, behavior: stillRef.current ? "auto" : "smooth" });
    },
    [slotsIn],
  );

  function narrate(kind: Board) {
    if (!phoneRef.current || statusRef.current.s === "think") return;
    const tok = ++run.current;
    clearHold();
    if (kind === "front" && dRef.current.clips) {
      setStatus("Ready to cut", "idle");
      void say(DONE_LINE.lead, DONE_LINE.rest, tok, true);
      return;
    }
    setStatus("Waiting for your OK", "wait", kind === "plan" ? "listen" : "awake");
    const line = kind === "plan" ? PLAN_LINE : kind === "stills" ? DRAW_LINE : REST_LINE;
    void say(line.lead, line.rest, tok, true);
  }

  function onTrackScroll() {
    const el = track.current;
    const slots = slotsIn();
    if (!el || !phoneRef.current || !slots.length) return;
    const pad = parseFloat(getComputedStyle(el).paddingLeft) || 0;
    let i = 0;
    let best = Infinity;
    slots.forEach((s, k) => {
      const dist = Math.abs(s.offsetLeft - pad - el.scrollLeft);
      if (dist < best) {
        best = dist;
        i = k;
      }
    });
    setBoard(i);
    if (settle.current) clearTimeout(settle.current);
    settle.current = setTimeout(() => {
      if (i === boardRef.current) return;
      boardRef.current = i;
      const kind = boardsOf(dRef.current)[i];
      if (kind) narrate(kind);
    }, 140);
  }

  const boards = boardsOf(d);
  const lastBoard = boards[boards.length - 1] ?? null;
  /* the flow opened a new board (a new brief, the stills, the price): go to it */
  const prevLast = useRef<Board | null>(lastBoard);
  useEffect(() => {
    if (prevLast.current === lastBoard) return;
    prevLast.current = lastBoard;
    if (!phoneRef.current || !lastBoard) return;
    const i = boardsOf(dRef.current).length - 1;
    boardRef.current = i;
    setBoard(i);
    requestAnimationFrame(() => goTo(i));
  }, [lastBoard, goTo]);

  const at = Math.max(0, Math.min(board, boards.length - 1));
  const go = (i: number) => goTo(Math.max(0, Math.min(boards.length - 1, i)));
  const onBoard = phone ? boards[at] : undefined;

  /* the track is as tall as the board in view, so a short board (the stills)
     never leaves an empty band above the arrows */
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    if (!phone) {
      el.style.removeProperty("height");
      return;
    }
    const slot = slotsIn()[at];
    if (!slot) return;
    const fit = () => {
      const cs = getComputedStyle(el);
      el.style.height = `${slot.offsetHeight + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)}px`;
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(slot);
    return () => ro.disconnect();
  }, [phone, at, boards.length, slotsIn]);

  /* ---- what is drawn ---- */

  const full = voice.lead + voice.rest;
  const typing = !voice.dots && voice.typed < full.length;
  const mood: Mood =
    hold ??
    (voice.dots
      ? "think"
      : typing
        ? "talk"
        : listening && status.text === "Listening"
          ? "listen"
          : status.base);
  const lamp =
    mood === "made" ? LAMP.made : mood === "oops" ? LAMP.oops : onBoard ? BOARD_LAMP[onBoard] : LAMP.calm;
  const n = count(d);
  const model = DEMO_MODELS[d.model];
  const enter = d.fresh ? " vh-enter" : "";
  const brief = d.brief;

  return (
    <motion.div
      className="vh-stage"
      id="stage"
      data-s={status.s}
      aria-label="Vesper demo"
      role="region"
      style={{ "--vh-lamp": LAMP.calm } as CSSProperties}
      animate={{ "--vh-lamp": lamp } as never}
      transition={{ duration: still ? 0 : 0.7, ease: "easeInOut" }}
    >
      <span className="vh-lb vh-t" aria-hidden />
      <span className="vh-lb vh-b" aria-hidden />

      <div className="vh-voice">
        <div className="vh-vstatus">
          <i className="vh-live" aria-hidden />
          Vesper · <span role="status">{status.text}</span>
        </div>
        <p className="vh-line" aria-hidden>
          {voice.dots ? (
            <span className="vh-dots">
              <i />
              <i />
              <i />
            </span>
          ) : (
            <>
              <b>{full.slice(0, Math.min(voice.typed, voice.lead.length))}</b>
              <span>{voice.typed > voice.lead.length ? full.slice(voice.lead.length, voice.typed) : ""}</span>
            </>
          )}
        </p>
      </div>

      <div className="vh-figwrap">
        <div className="vh-fig" role="img" aria-label={VESPER_ALT}>
          <span className="vh-lamp" aria-hidden>
            <Flicker className="vh-pool" />
            <Flicker className="vh-core" breathe />
          </span>
          <Flicker className="vh-floor" style={{ x: "-50%", y: 0 }} />
          <AnimatePresence initial={false}>
            <motion.img
              key={mood}
              src={vesperSrc(mood)}
              alt=""
              width={500}
              height={500}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: still ? 0 : 0.2, ease: "easeOut" }}
            />
          </AnimatePresence>
        </div>
        {captions}
      </div>

      <div className="vh-brief">
        <span className="vh-k">Your brief</span>
        <p>{brief ? `“${brief.say}”` : "Pick a scene below, or type your own."}</p>
      </div>

      <div className="vh-mode">
        <span className="vh-k" id="vh-mode-l">
          Approvals
        </span>
        <Seg labels={["Ask first", "Auto"]} active={auto ? 1 : 0} id="vh-mode-l" onPick={(j) => pickAuto(j === 1)} />
        <p className="vh-hint">Auto skips the stills check. It never skips the price.</p>
      </div>

      {/* the three boards; on a phone this is the swipe track */}
      <div className="vh-track" ref={track} onScroll={onTrackScroll} role="group" aria-label="Plan, stills and price">
        {/* 1 the plan, stage left */}
        <div className="vh-slot vh-slot-plan" aria-label="Shot plan" data-on={onBoard === "plan" || undefined}>
          {brief && d.plan && (
            <div className={`vh-cc${enter}`}>
              <span className="vh-cue">01 · The plan</span>
              <div className="vh-cc-top">
                <span className="vh-k">Plan · {brief.ratio} · 15 s</span>
                <span className="vh-badge">3 shots</span>
              </div>
              <ol className="vh-rows">
                {brief.shots.map((s, i) => (
                  <li key={i} className="vh-row">
                    <div className="vh-row-tx">
                      <div className="vh-row-h">
                        <span className="vh-k">Shot {i + 1}</span>
                        <b>{s.title}</b>
                        <span className="vh-tc">{TIMECODES[i]}</span>
                      </div>
                      <span key={d.flash[i]} className={`vh-desc${d.flash[i] ? " vh-flash" : ""}`}>
                        {s.looks[d.look[i]]}
                      </span>
                    </div>
                    <Seg
                      labels={LOOKS}
                      active={d.look[i]}
                      label={`Look for shot ${i + 1}`}
                      onPick={(j) => pickLook(i, j)}
                    />
                  </li>
                ))}
              </ol>
              <div className="vh-acts">
                <button type="button" className="vh-btn vh-btn-white vh-btn-sm" disabled={d.planBusy} onClick={drawStills}>
                  Draw the stills
                </button>
                <button
                  type="button"
                  className="vh-btn vh-btn-quiet vh-btn-sm"
                  disabled={d.planBusy}
                  onClick={(e) => {
                    const b = e.currentTarget
                      .closest(".vh-cc")
                      ?.querySelector<HTMLButtonElement>('.vh-seg button[aria-pressed="true"]');
                    b?.focus();
                  }}
                >
                  Change a shot
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 2 the stills, stage right, fanned */}
        <div className="vh-slot vh-slot-stills" aria-label="Stills" data-on={onBoard === "stills" || undefined}>
          {brief && d.stillsShown && (
            <div className={`vh-cc${enter}${d.stillsDone ? " vh-done" : ""}`}>
              <span className="vh-cue">02 · The stills</span>
              <div className="vh-cc-top">
                <span className="vh-k">Keep or redraw</span>
                <span className="vh-badge">
                  {d.stillsDone ? (
                    <>
                      {CHECK}Approved
                    </>
                  ) : (
                    `${n} of 3 kept`
                  )}
                </span>
              </div>
              <div className="vh-stills">
                {d.stills.map((name, i) => (
                  <div key={i} className="vh-fan">
                    <div
                      className={`vh-tile vh-st-tile${i < d.stillsIn ? " vh-in" : ""}${d.on[i] ? "" : " vh-off"}`}
                    >
                      <img
                        src={stillOf(name)}
                        alt={`Still for shot ${i + 1}`}
                        loading="lazy"
                        decoding="async"
                        className={d.fading[i] ? "vh-fade" : undefined}
                        onLoad={() => unfade(i)}
                      />
                      <span className="vh-tag">Shot {i + 1}</span>
                      <button
                        type="button"
                        className="vh-tb vh-chk"
                        aria-pressed={d.on[i]}
                        aria-label={`Keep still for shot ${i + 1}`}
                        disabled={d.stillsDone}
                        onClick={() => toggleKeep(i)}
                      >
                        {CHECK}
                      </button>
                      <button
                        type="button"
                        className="vh-tb vh-redo"
                        aria-label={`Redraw still for shot ${i + 1}`}
                        disabled={d.stillsDone}
                        onClick={() => redraw(i)}
                      >
                        {REDO}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="vh-acts">
                <button
                  type="button"
                  className={`vh-btn vh-btn-sm ${d.stillsDone ? "vh-btn-quiet" : "vh-btn-white"}`}
                  disabled={d.stillsDone || n === 0}
                  onClick={approveStills}
                >
                  {d.stillsDone ? "Stills approved" : "Approve stills"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 3 the price, front and centre at Vesper's feet; then the clips */}
        <div className="vh-slot vh-slot-front" aria-label="Price and clips" data-on={onBoard === "front" || undefined}>
          {brief && d.price && (
            <div className={`vh-cc${enter}`}>
              <span className="vh-cue">03 · Before render</span>
              <div className="vh-cc-top">
                <span className="vh-k">Checkpoint</span>
                <span className="vh-badge">example prices</span>
              </div>
              <div className="vh-spec">
                {n} {clipsWord(n)} · {model.name} · {n * CLIP_SECONDS} s
              </div>
              <div className="vh-sugg">
                <span className="vh-k">
                  Vesper suggests: <b>{DEMO_MODELS[0].name}</b>
                </span>
                <Seg
                  labels={DEMO_MODELS.map((m) => m.name)}
                  active={d.model}
                  label="Render model"
                  disabled={d.locked}
                  onPick={pickModel}
                />
              </div>
              <div className="vh-price">
                <strong>{figure.toLocaleString("en-US")}</strong>
                <span>credits</span>
              </div>
              <div className="vh-acts">
                <button
                  type="button"
                  className="vh-btn vh-btn-red vh-btn-sm"
                  style={{ padding: "0 26px" }}
                  disabled={d.locked}
                  onClick={approveRender}
                >
                  Approve
                </button>
                <button type="button" className="vh-btn vh-btn-quiet vh-btn-sm" disabled={d.locked} onClick={notYet}>
                  Not yet
                </button>
              </div>
              <p className="vh-yes">Nothing renders until you say yes.</p>
            </div>
          )}
          {brief && d.prog && (
            <div className="vh-prog">
              <div className="vh-bar">
                <i style={{ width: d.prog.fill ? "100%" : 0 }} />
              </div>
              <div className="vh-bar-l">
                {d.prog.k} of {d.prog.n} clips
              </div>
            </div>
          )}
          {brief && d.clips && (
            <div className={`vh-cc${enter}`}>
              <span className="vh-cue">04 · The clips</span>
              <div className="vh-cc-top">
                <span className="vh-k">
                  Clips · {brief.ratio} · {n * CLIP_SECONDS} s
                </span>
                <span className="vh-badge">{CHECK}Rendered</span>
              </div>
              <div className="vh-clips">
                {d.stills.map((name, i) =>
                  d.on[i] ? (
                    <div key={i} className="vh-tile vh-clip">
                      <img src={stillOf(name)} alt={`Clip for shot ${i + 1}`} loading="lazy" decoding="async" />
                      <span className="vh-tag">{model.name}</span>
                      <span className="vh-play">
                        <span>{PLAY}</span>
                      </span>
                      <span className="vh-dur">0:05</span>
                    </div>
                  ) : null,
                )}
              </div>
              <div className="vh-acts">
                <button type="button" className="vh-btn vh-btn-white vh-btn-sm" onClick={greet}>
                  Make another
                </button>
                <Link className="vh-btn vh-btn-quiet vh-btn-sm" href="/studio/cut">
                  Open in the editor
                </Link>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* a phone's way through the track: arrows, a dot per board, "N of 3" */}
      <div className="vh-cnav" hidden={!phone || boards.length < 2}>
        <button type="button" className="vh-arrow" aria-label="Previous board" disabled={at <= 0} onClick={() => go(at - 1)}>
          {PREV}
        </button>
        <div className="vh-cdots">
          {boards.map((b, i) => (
            <button
              key={b}
              type="button"
              aria-label={`${i + 1} of ${boards.length}: ${BOARD_NAME[b]}`}
              aria-current={i === at}
              onClick={() => go(i)}
            >
              <i />
            </button>
          ))}
        </div>
        <span className="vh-count">
          {at + 1} of {boards.length}
        </span>
        <button
          type="button"
          className="vh-arrow"
          aria-label="Next board"
          disabled={at >= boards.length - 1}
          onClick={() => go(at + 1)}
        >
          {NEXT}
        </button>
      </div>

      <div className="vh-scenes">
        <span className="vh-k">Pick a scene</span>
        <div className="vh-scene-row" role="group" aria-label="Example briefs">
          {SCENES.map((s) => (
            <button
              key={s.key}
              type="button"
              className="vh-scene"
              aria-current={d.key === s.key}
              onClick={() => void start(s.key)}
            >
              <span className={`vh-frame${BRIEFS[s.key].ratio === "16:9" ? " vh-w" : ""}`} aria-hidden>
                <img src={stillOf(SCENE_STILL[s.key])} alt="" loading="lazy" decoding="async" />
              </span>
              <span className="vh-sc-tx">
                <span className="vh-k">{s.label}</span>
                <b>{s.title}</b>
                <span>{s.line}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="vh-comp">
        <form className="vh-form" ref={form} onSubmit={send}>
          <label className="vh-sr" htmlFor="vh-msg">
            Message Vesper
          </label>
          <input
            id="vh-msg"
            ref={input}
            type="text"
            autoComplete="off"
            placeholder="Or tell Vesper your own idea…"
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            onFocus={() => setListening(true)}
            onBlur={() => setListening(false)}
          />
          <button className="vh-btn vh-btn-white" type="submit">
            Send
          </button>
        </form>
      </div>

      <div className="vh-sr" role="log" aria-live="polite" aria-label="Conversation with Vesper">
        {log.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>
    </motion.div>
  );
}
/* eslint-enable @next/next/no-img-element */
