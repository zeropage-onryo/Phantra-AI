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
const REST_LINE = { lead: "Stills approved.", rest: " Here’s what 3 clips cost to render. Auto never skips this step." };

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
  const say = async (lead: string, rest: string, tok: number): Promise<boolean> => {
    setLog((l) => [...l, `Vesper: ${lead}${rest}`]);
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
    const ok = await say(
      "Here’s the plan:",
      " three shots, 5 s each. Pick a look for any shot, then I’ll draw the stills.",
      tok,
    );
    if (!ok) return;
    upd((x) => ({ ...x, plan: true }));
    setStatus("Waiting for your OK", "wait");
  }

  async function drawStills() {
    const tok = run.current;
    if (dRef.current.planBusy) return;
    upd((x) => ({ ...x, planBusy: true }));
    setStatus("Drawing stills", "think");
    const ok = await say(
      "Drawing the stills.",
      " These set the look of each clip. Keep the ones you like, redraw the rest.",
      tok,
    );
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
    const ok = await say(
      autoRef.current ? "Stills approved on Auto." : "Stills approved.",
      ` Here’s what ${n} ${n === 1 ? "clip costs" : "clips cost"} to render. Auto never skips this step.`,
      tok,
    );
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
    const ok2 = await say("Your shots are ready to cut.", " Trim, reorder or swap a model in the editor.", tok);
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
  const lamp = mood === "made" ? LAMP.made : mood === "oops" ? LAMP.oops : LAMP.calm;
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

      {/* 1 the plan, stage left */}
      <div className="vh-slot vh-slot-plan" aria-label="Shot plan">
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
      <div className="vh-slot vh-slot-stills" aria-label="Stills">
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
      <div className="vh-slot vh-slot-front" aria-label="Price and clips">
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
