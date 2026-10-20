"use client";

/* The stream above the composer, drawn to the "ZPF Composer Directions"
   mock: what was asked as a bubble on the right, what came back under it.

   A SEND (a turn carrying `made`) shows its result as tiles -- an IMAGE
   turn the still, a VIDEO turn the written scene as its timed shots. A
   scene is text until it is rendered, so a shot tile is its still
   when one has been drawn and its number otherwise, never fake footage;
   a tile with a clip (rendered later, read back here) gets the play mark.
   The Guide's turns are the same stream: the person's words on the
   right, the answer on the left with its chips, sheet and confirm card.
   Since 2026-10-04 every send IS a Guide turn, and when the brain makes
   (make_image / make_video) its one-line answer carries `made`: the line
   on the left, the tiles under it. A make proposal is never a confirm card;
   a STILL is a step card instead (2026-10-08, after Runway Agent's chat):
   its prompt, its frame, and Approve with the model and price under it --
   then the same card as the step's record, the still drawn below it. */
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Clapperboard,
  Download,
  Ellipsis,
  Film,
  ImagePlus,
  Images,
  Play,
  RotateCcw,
  Scissors,
  Shuffle,
  Sparkles,
  UserRound,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { renderDownloadHref, sceneHref } from "@/lib/studio-api";
import { assetId, continueActions, split, type ContinueAction, type ContinueKind } from "@/lib/continue";
import { OpenInEditor } from "@/components/cut/open-in-editor";
import { TopUpLink } from "@/components/studio/top-up-link";
import { NOT_SENT, NOT_SENT_CREDITS } from "@/lib/out-of-credits";
import { cssAspect, isMake, isSheetTool, madeMeta, mediaSrc, type Made } from "@/lib/composer";
import type { ContactSheet, Turn } from "@/lib/assistant";
import { lookedLine } from "@/lib/skills";
import { isLookTool } from "@/lib/look-research";
import { heldLine, stillsFor } from "@/lib/result-numbers";
import { renderLine, type ModelOption, type StepModel } from "@/lib/step-model";
import { LookCard, LookResearchNote } from "@/components/studio/look-research";
import { isSwitchTool } from "@/lib/explore";
import { SwitchCard } from "@/components/studio/explore-switch";
import { failLine, madeStatus } from "@/lib/made-state";
import { PlanCard, type PlanHandlers } from "@/components/studio/make-plan-card";
import { EffectStep } from "@/components/studio/effect-step";
import type { Effect, EffectState } from "@/lib/effects";
import { ContactSheetView } from "@/components/studio/contact-sheet";
import { TypedText } from "@/components/studio/typed-text";
import { SheetStep, StillStep, isSheetStep, isStillStep, lineIsPrompt } from "@/components/studio/still-step";
import { RenderCard } from "@/components/studio/render-card";
import { cardFonts } from "@/components/studio/card-fonts";
import type { Concept } from "@/lib/studio-api";
import { cutLine, joinable, trimProblem } from "@/lib/final-cut";

const pad = (n: number) => String(n).padStart(2, "0");

export type Live = { progress: number; detail: string };

type Handlers = {
  busy: boolean;
  /** an /image-models id -> its label, for the meta line */
  modelLabel: (id?: string) => string | undefined;
  /** a "continue" action under a result (lib/continue.ts): the ones that
   *  act here. Links -- Download, the Library, the editor, the canvas --
   *  are drawn as links and never call this. */
  onContinue: (t: Turn, a: ContinueAction) => void;
  /** which effects the server's table holds, and whether it can run them */
  continueHas: { effects: string[]; ready: boolean };
  onSelect: (madeId: string, n: number) => void;
  /** a scene's Render card (drawn in its turn) read the scene: its clips
   *  go onto the turn's tiles */
  onScene: (madeId: string, scene: Concept) => void;
  /** join a rendered scene's shots into one video (lib/final-cut.ts) */
  onJoin: (m: Made) => void;
  /** trim the final cut into a new clip, free (seconds) */
  onTrim: (m: Made, start: number, end: number) => void;
  onChip: (text: string) => void;
  onDecide: (i: number, yes: boolean) => void;
  /** THE MODEL A STILL IS DRAWN ON (lib/step-model.ts): the menu, the
   *  model a step stands on (the person's choice, the brain's proposal or
   *  the picker's), the change, and a warning when that model takes no
   *  references while pictures are attached */
  stillModels: ModelOption[];
  stillModelOf: (t: Turn) => StepModel;
  onStillModel: (i: number, id: string) => void;
  stillWarn: (t: Turn) => string;
  /** the clip models, for naming the one a scene was proposed for */
  clipModels: ModelOption[];
  /** an account that is not charged: no prices in the model menu */
  exempt: boolean;
  /** a result's number was clicked: it goes into the box as "#3", so the
   *  next message can point at it (lib/result-numbers.ts) */
  onRefer: (n: number) => void;
  /** the look the open project has now ("" for none, or no project): the
   *  save-look card says when saving replaces one */
  projectLook: string;
  onToggleFrame: (i: number, id: string) => void;
  onKeep: (i: number, sheet: ContactSheet) => void;
  /** a make_image step's Approve: the only click that spends here */
  onApprove: (i: number) => void;
  /** under Approve: the model that draws the still (this one, else the
   *  picker's) and what one costs -- "Nano Banana · 10 credits" */
  stillLine: (modelId?: string) => string;
  /** an element sheet step's Approve: saves the character, draws the sheet */
  onApproveSheet: (i: number) => void;
  /** under the sheet's Approve: "Nano Banana Pro · 36 credits" */
  sheetLine: string;
  /** a plan's card (lib/make-plan.ts), by the plan's id */
  plan: (planId: string) => PlanHandlers;
  /** an effect's card (lib/effects.ts): the table's row for it, whether
   *  this account is charged, a changed choice, and the click that spends */
  effectItem: (effectId: string) => Effect | undefined;
  effectExempt: boolean;
  onEffectChange: (next: EffectState) => void;
  onEffectApprove: (id: string, credits: number, charged: boolean) => void;
};

function Meta({ m, live, h }: { m: Made; live?: Live; h: Handlers }) {
  if (m.status === "running") {
    return (
      <div className="zc-meta">
        <span className="zc-live" aria-hidden />
        {live?.detail || m.detail || (m.output === "image" ? "Drawing the image…" : "Writing the scene…")}
      </div>
    );
  }
  // a still that "finished" with nothing drawn did not finish (lib/made-state.ts)
  const state = madeStatus(m);
  if (state === "failed") {
    return (
      <div className="zc-meta bad">
        {m.output === "image" ? failLine(m.detail) : m.detail || "That one did not finish."}
        {/* an empty balance is the one failure with a way out on it */}
        <TopUpLink text={m.detail} />
      </div>
    );
  }
  if (state === "stopped") return <div className="zc-meta">Stopped</div>;
  return (
    <div className="zc-meta">
      {/* its short number: say "3" in a sentence, or click to put "#3" in the box */}
      {m.n ? (
        <button
          type="button"
          className="zc-num"
          title={`Result ${m.n}: point at it in your next message ("make ${m.n} warmer"). Click to put #${m.n} in the box.`}
          onClick={() => h.onRefer(m.n as number)}
        >
          #{m.n}
        </button>
      ) : null}
      {madeMeta(m, h.modelLabel(m.model))}
      {/* a scene the brain proposed a renderer for: where its Render card opens */}
      {m.renderModel && renderLine(h.clipModels, m.renderModel, m.renderWhy) ? (
        <span className="zc-proposed">{renderLine(h.clipModels, m.renderModel, m.renderWhy)}</span>
      ) : null}
    </div>
  );
}

/* one plate with the percentage and the red bar, while a send runs */
function RunningTile({ m, live }: { m: Made; live?: Live }) {
  const pct = Math.round((live?.progress ?? 0) * 100);
  return (
    <div className={`zc-tiles${m.output === "image" ? " one" : ""}`}>
      <div className="zc-tilewrap">
        <div className="zc-tile running" style={{ aspectRatio: m.output === "image" ? cssAspect(m.frame) ?? "4 / 5" : undefined }}>
          <span className="zc-pct">{pct}%</span>
          <span className="zc-bar" style={{ width: `${Math.max(4, pct)}%` }} />
        </div>
        <span className="zc-label">{m.output === "image" ? "Image 01" : "Writing…"}</span>
      </div>
    </div>
  );
}

const ICON: Record<ContinueKind, LucideIcon> = {
  effect: Wand2,
  gallery: Sparkles,
  variation: Shuffle,
  shot: Film,
  reference: ImagePlus,
  element: UserRound,
  download: Download,
  library: Images,
  editor: Scissors,
  canvas: Clapperboard,
  render: Play,
  reuse: RotateCcw,
};
/* a send that did not finish puts its prompt back in the box */
const RETRY: ContinueAction = { id: "reuse", kind: "reuse", label: "Try again", title: "", primary: true };

/* What a finished result can be carried on to (lib/continue.ts): the few
   next moves in the row, the rest under More. Nothing in it spends: an
   effect or a variation opens a card with its price, and that card's
   Approve is the click. */
function ContinueRow({ m, turn, h, director }: { m: Made; turn: Turn; h: Handlers; director: string | null }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", off);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", off);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const render = assetId(m.asset);
  const { row, more } = split(
    continueActions(
      {
        output: m.output,
        image: m.image,
        clip: m.clip,
        asset: m.asset,
        conceptId: m.conceptId,
        effect: m.effect,
        prompt: m.prompt ?? turn.content,
      },
      h.continueHas,
    ),
  );
  if (!row.length && !more.length) return null;

  const draw = (a: ContinueAction, inMenu: boolean) => {
    const Icon = ICON[a.kind];
    const cls = inMenu ? undefined : "zc-act";
    const role = inMenu ? "menuitem" : undefined;
    const inner = (
      <>
        <Icon strokeWidth={1.6} /> {a.label}
      </>
    );
    const done = () => setOpen(false);
    if (a.kind === "download" && render !== null) {
      return (
        <a key={a.id} className={cls} role={role} href={renderDownloadHref(render)} title={a.title} onClick={done}>
          {inner}
        </a>
      );
    }
    if (a.kind === "library" && render !== null) {
      return (
        <Link key={a.id} className={cls} role={role} href={`/studio/assets?open=${render}`} title={a.title}>
          {inner}
        </Link>
      );
    }
    if (a.kind === "canvas") {
      return director ? (
        <Link key={a.id} className={cls} role={role} href={director} title={a.title}>
          {inner}
        </Link>
      ) : null;
    }
    if (a.kind === "editor") {
      return m.asset ? (
        <OpenInEditor key={a.id} handles={[m.asset]} className={cls} title={a.title}>
          {inner}
        </OpenInEditor>
      ) : null;
    }
    return (
      <button
        key={a.id}
        type="button"
        className={cls}
        role={role}
        disabled={h.busy}
        title={a.title}
        onClick={() => {
          done();
          h.onContinue(turn, a);
        }}
      >
        {inner}
      </button>
    );
  };

  return (
    <div className="zc-actions">
      {row.map((a) => draw(a, false))}
      {more.length ? (
        <span className="pillwrap" ref={box}>
          <button type="button" className="zc-act" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            <Ellipsis strokeWidth={1.6} /> More
          </button>
          {open ? (
            <span className="pillmenu zc-more" role="menu">
              {more.map((a) => draw(a, true))}
            </span>
          ) : null}
        </span>
      ) : null}
    </div>
  );
}

/** RUNWAY'S FINAL CUT, in the turn: the scene's shots joined into one
 *  video once the last one lands, filed straight in the Library. Free.
 *  Under it: the Library, a quick Trim (a new clip, also free) and the
 *  editor for anything more. */
function FinalCutView({ m, h }: { m: Made; h: Handlers }) {
  const cut = m.finalCut;
  const shots = (m.parts ?? []).length;
  const ratio = cssAspect(m.frame) ?? "9 / 16";
  const [trimOpen, setTrimOpen] = useState(false);
  const [from, setFrom] = useState("0");
  const [to, setTo] = useState("");
  if (!cut || cut.status === "failed") {
    return (
      <div className="zc-final">
        {cut ? <p className="zc-final-line failed" role="alert">{cutLine(cut, shots)}</p> : null}
        <div className="zc-actions">
          <button type="button" className="zc-act" onClick={() => h.onJoin(m)}>
            <Film strokeWidth={1.6} /> {cut ? "Try joining again" : `Join the ${shots} shots into one video · free`}
          </button>
        </div>
      </div>
    );
  }
  const libraryId = assetId(cut.asset);
  const trim = cut.trim;
  const seconds = cut.seconds ?? null;
  const end = to === "" ? (seconds ?? NaN) : Number(to);
  const problem = trimProblem(Number(from), end, seconds);
  const trimming = trim?.status === "running";
  const trimId = assetId(trim?.asset);
  return (
    <div className="zc-final" data-final-cut={m.conceptId}>
      {cut.status === "done" && cut.url ? (
        <div className="zc-tiles one">
          <div className="zc-tilewrap" style={{ maxWidth: `calc(420px * (${ratio}))` }}>
            <div className="zc-tile clip fill" style={{ aspectRatio: ratio }}>
              <video src={mediaSrc(cut.url)} controls playsInline preload="metadata" />
            </div>
          </div>
        </div>
      ) : null}
      <p className="zc-final-line" role="status">
        {cutLine(cut, shots)}
      </p>
      {cut.status === "done" ? (
        <div className="zc-actions">
          {libraryId !== null ? (
            <Link className="zc-act" href={`/studio/assets?open=${libraryId}`} title="Open it on the Library wall">
              <Images strokeWidth={1.6} /> See it in the Library
            </Link>
          ) : null}
          {cut.asset ? (
            <button
              type="button"
              className="zc-act"
              aria-expanded={trimOpen}
              disabled={trimming}
              onClick={() => setTrimOpen((o) => !o)}
              title="Keep part of it as a new clip. Free."
            >
              <Scissors strokeWidth={1.6} /> {trimming ? "Trimming…" : "Trim"}
            </button>
          ) : null}
          {m.conceptId ? (
            <OpenInEditor concept_id={m.conceptId} className="zc-act" title="Open this cut in the editor: cuts, music, captions. Free.">
              <Clapperboard strokeWidth={1.6} /> Edit the cut
            </OpenInEditor>
          ) : null}
        </div>
      ) : null}
      {trimOpen && cut.status === "done" && cut.asset ? (
        <form
          className="zc-trim"
          onSubmit={(e) => {
            e.preventDefault();
            if (problem || trimming) return;
            h.onTrim(m, Number(from), end);
            setTrimOpen(false);
          }}
        >
          <label>
            From
            <input type="number" min={0} step={0.1} value={from} onChange={(e) => setFrom(e.target.value)} aria-label="Start, in seconds" />
            s
          </label>
          <label>
            to
            <input
              type="number"
              min={0}
              step={0.1}
              value={to}
              placeholder={seconds ? seconds.toFixed(1) : ""}
              onChange={(e) => setTo(e.target.value)}
              aria-label="End, in seconds"
            />
            s
          </label>
          <button type="submit" className="zc-act" disabled={!!problem}>
            Trim · free
          </button>
          {problem ? <span className="zc-final-line failed">{problem}</span> : null}
        </form>
      ) : null}
      {trim ? (
        trim.status === "done" && trim.url ? (
          <div className="zc-final" data-trim={trimId ?? undefined}>
            <div className="zc-tiles one">
              <div className="zc-tilewrap" style={{ maxWidth: `calc(320px * (${ratio}))` }}>
                <div className="zc-tile clip fill" style={{ aspectRatio: ratio }}>
                  <video src={mediaSrc(trim.url)} controls playsInline preload="metadata" />
                </div>
              </div>
            </div>
            <p className="zc-final-line">
              Trimmed · {trim.start.toFixed(1)}–{trim.end.toFixed(1)}s · free{trimId !== null ? " · in your Library" : ""}
              {trimId !== null ? (
                <>
                  {" · "}
                  <Link href={`/studio/assets?open=${trimId}`}>open</Link>
                </>
              ) : null}
            </p>
          </div>
        ) : (
          <p className={`zc-final-line${trim.status === "failed" ? " failed" : ""}`} role="status">
            {trim.status === "running"
              ? `Trimming ${trim.start.toFixed(1)}–${trim.end.toFixed(1)}s…`
              : trim.detail || "The trim was not made. Nothing was charged."}
          </p>
        )
      ) : null}
    </div>
  );
}

/** every shot of a written scene has its clip (or the whole scene does) */
function sceneRendered(m: Made): boolean {
  const parts = m.parts ?? [];
  return parts.length ? parts.every((p) => !!p.media_url) : !!m.sceneClip;
}

function MadeView({ m, live, h, turn }: { m: Made; live?: Live; h: Handlers; turn: Turn }) {
  const still = useReducedMotion();
  const selected = m.shot ?? 1;
  const tile = (i: number) => ({
    initial: still ? false : { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.28, delay: Math.min(i, 6) * 0.05, ease: [0.22, 0.61, 0.36, 1] as const },
  });

  const state = madeStatus(m);
  let body: React.ReactNode = null;
  if (state === "running") body = <RunningTile m={m} live={live} />;
  else if (state === "done" && m.output === "image") {
    const ratio = cssAspect(m.frame) ?? "4 / 5";
    body = m.clip ? (
      // an effect that made a clip: it plays where a still would be drawn,
      // at its own shape, and is not a button (its controls are)
      <div className="zc-tiles one">
        <motion.div className="zc-tilewrap" {...tile(0)} style={{ maxWidth: 420 }}>
          <div className="zc-tile on clip">
            <video src={mediaSrc(m.clip)} controls muted loop playsInline preload="metadata" />
          </div>
          <span className="zc-label on">Clip 01</span>
        </motion.div>
      </div>
    ) : (
      <div className="zc-tiles one">
        <motion.div className="zc-tilewrap" {...tile(0)} style={{ maxWidth: `calc(420px * (${ratio}))` }}>
          <button type="button" className="zc-tile on" style={{ aspectRatio: ratio }} onClick={() => h.onSelect(m.id, 1)}>
            {/* done means drawn: a still with no image is `failed` above */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={mediaSrc(m.image ?? "")} alt="" />
          </button>
          <span className="zc-label on">Image 01 · selected</span>
        </motion.div>
      </div>
    );
  } else if (state === "done") {
    const parts = m.parts ?? [];
    body = parts.length ? (
      <div className={`zc-tiles${parts.length >= 4 ? " four" : ""}`}>
        {parts.map((p, i) => {
          const on = p.n === selected;
          return (
            <motion.div key={p.n} className="zc-tilewrap" {...tile(i)}>
              {p.media_url ? (
                // a shot with its clip plays where its still was
                <div className={`zc-tile clip${on ? " on" : ""}`} title={p.text || p.prompt || `Shot ${pad(p.n)}`}>
                  <video src={mediaSrc(p.media_url)} poster={p.reference_image ? mediaSrc(p.reference_image) : undefined} controls muted loop playsInline preload="metadata" />
                  <span className="zc-badge">{p.seconds}s</span>
                </div>
              ) : (
              <button
                type="button"
                className={`zc-tile${on ? " on" : ""}`}
                aria-pressed={on}
                title={p.text || p.prompt || `Shot ${pad(p.n)}`}
                onClick={() => h.onSelect(m.id, p.n)}
              >
                {p.reference_image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={mediaSrc(p.reference_image)} alt="" />
                ) : (
                  <span className="zc-tile-n">{pad(p.n)}</span>
                )}
                {!p.reference_image && (p.text || p.prompt) ? (
                  <span className="zc-tile-text">
                    <span>{p.text || p.prompt}</span>
                  </span>
                ) : null}
                {p.media_url ? (
                  <span className="zc-play" aria-label="rendered">
                    <Play strokeWidth={2} fill="currentColor" />
                  </span>
                ) : null}
                <span className="zc-badge">{p.seconds}s</span>
              </button>
              )}
              <span className={`zc-label${on ? " on" : ""}`}>
                Shot {pad(p.n)} · {p.start}–{p.end}s{on ? " · selected" : ""}
              </span>
            </motion.div>
          );
        })}
      </div>
    ) : (
      <div className="zc-tiles one">
        <motion.div className="zc-tilewrap" {...tile(0)}>
          <div className={`zc-tile on${m.sceneClip ? " clip" : ""}`}>
            {m.sceneClip ? <video src={mediaSrc(m.sceneClip)} controls muted loop playsInline preload="metadata" /> : <span className="zc-tile-n">01</span>}
            {m.seconds ? <span className="zc-badge">{m.seconds}s</span> : null}
          </div>
          <span className="zc-label on">One continuous shot · {m.detail}</span>
        </motion.div>
      </div>
    );
  }

  // the scene's canvas: inside its project's workspace when it is filed
  // under one, else on its own (/studio/scene resolves which)
  const director = m.conceptId ? sceneHref(m.conceptId, m.output === "video" ? selected : 1) : null;

  return (
    <>
      <Meta m={m} live={live} h={h} />
      {body}
      {state === "done" && m.output === "video" && m.conceptId && joinable(m.parts) ? (
        <FinalCutView m={m} h={h} />
      ) : null}
      {state === "done" && m.output === "video" && m.conceptId && !m.planned && !sceneRendered(m) ? (
        // THE PRICED BUTTON, IN THE TURN (2026-10-20, Mike: "you still have
        // to approve in chat, but you can generate video directly from
        // chat"). The same card the workspace opens: its price, its model
        // pick, its Draft first, its keyframes, and the one click that
        // spends. It reads the scene back when a render ends, and the clips
        // land on the tiles above; once every shot has one, it goes away.
        <div className={`ss ${cardFonts}`} data-render-turn={m.conceptId}>
          <div className="ss-head">
            <Film aria-hidden />
            <b>Render</b>
            <span>{m.title || "this scene"}</span>
          </div>
          <RenderCard conceptId={m.conceptId} noStrip onScene={(c) => h.onScene(m.id, c)} />
        </div>
      ) : null}
      {state === "done" ? (
        <ContinueRow m={m} turn={turn} h={h} director={director} />
      ) : (state === "failed" || state === "stopped") && !turn.effect ? (
        <div className="zc-actions">
          <button type="button" className="zc-act" disabled={h.busy} onClick={() => h.onContinue(turn, RETRY)}>
            <RotateCcw strokeWidth={1.6} /> Try again
          </button>
        </div>
      ) : null}
    </>
  );
}

export function ComposerStream({
  turns,
  live,
  choices,
  working,
  writing = "",
  handlers,
}: {
  turns: Turn[];
  /** progress per running send, by made id (page state) */
  live: Record<string, Live>;
  /** the Guide's offered replies after its newest answer */
  choices: string[];
  /** the Guide is answering: its detail line, drawn as a working row */
  working: string | null;
  /** its answer so far, as the model writes it (the job's `partial`) */
  writing?: string;
  handlers: Handlers;
}) {
  const still = useReducedMotion();
  if (!turns.length) return null;
  const lastAnswer = turns.map((t) => t.role === "assistant" && !t.failed).lastIndexOf(true);
  return (
    <div className="zc-stream" aria-live="polite">
      <AnimatePresence initial={false}>
        {turns.map((t, i) => (
          <motion.article
            key={t.made?.id ?? `${i}:${t.role}`}
            className="zc-turn"
            initial={still ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 0.61, 0.36, 1] }}
          >
            {t.role === "user" ? (
              <div className="zc-ask">
                <div className={`zc-bubble${t.failed ? " failed" : ""}`}>
                  {t.made?.refs.length ? (
                    <span className="zc-bubble-refs">
                      {t.made.refs.slice(0, 4).map((u) => (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img key={u} src={mediaSrc(u)} alt="" />
                      ))}
                      {t.made.refs.length > 4 ? <b>+{t.made.refs.length - 4}</b> : null}
                    </span>
                  ) : null}
                  {t.skill ? <span className="zc-bubble-skill">{t.skill} skill</span> : null}
                  <p>{t.content}</p>
                  {t.failed ? (
                    <span className="zc-bubble-failed">
                      {/* the refusal's own reason first: "out of credits" is untrue
                          for a trial whose thinking is used and whose credits are not */}
                      {t.failedWhy ? `Not sent — ${t.failedWhy}` : t.short ? NOT_SENT_CREDITS : NOT_SENT}
                      {t.short ? <TopUpLink always /> : null}
                    </span>
                  ) : null}
                </div>
              </div>
            ) : (
              <div className="zc-reply">
                {lookedLine(t.looked) ? <span className="zc-looked">{lookedLine(t.looked)}</span> : null}
                {/* a still's step card carries its prompt; the line is the same words */}
                {lineIsPrompt(t) || isSheetStep(t) || (t.effect && !t.reply) ? null : <p>{t.content}</p>}
                {/* a look researched by name: where it was read from */}
                <LookResearchNote items={t.reply?.research} />
                {t.reply?.sheet ? (
                  <ContactSheetView
                    sheet={t.reply.sheet}
                    chosen={t.chosen ?? {}}
                    kept={!!t.kept}
                    busy={handlers.busy}
                    name="The Guide"
                    onToggle={(id) => handlers.onToggleFrame(i, id)}
                    onKeep={(sh) => handlers.onKeep(i, sh)}
                  />
                ) : null}
                {t.reply?.proposal && isLookTool(t.reply.proposal.tool) ? (
                  <LookCard
                    label={t.reply.proposal.label}
                    look={String(t.reply.proposal.args.look ?? "")}
                    current={handlers.projectLook}
                    decided={t.decided}
                    busy={handlers.busy}
                    onDecide={(yes) => handlers.onDecide(i, yes)}
                  />
                ) : null}
                {/* asked to make while the project explores: the way out */}
                {t.reply?.proposal && isSwitchTool(t.reply.proposal.tool) ? (
                  <SwitchCard
                    kind={t.reply.proposal.args.kind}
                    decided={t.decided}
                    busy={handlers.busy}
                    onDecide={(yes) => handlers.onDecide(i, yes)}
                  />
                ) : null}
                {t.reply?.proposal &&
                !isLookTool(t.reply.proposal.tool) &&
                !isSwitchTool(t.reply.proposal.tool) &&
                !isMake(t.reply.proposal.tool) &&
                !isSheetTool(t.reply.proposal.tool) ? (
                  <div className={`ccard${t.decided ? ` ${t.decided}` : ""}`}>
                    <b>{t.reply.proposal.label}</b>
                    <dl>
                      {Object.entries(t.reply.proposal.args).map(([k, v]) => (
                        <div key={k}>
                          <dt>{k}</dt>
                          <dd>{String(v)}</dd>
                        </div>
                      ))}
                    </dl>
                    {t.decided ? (
                      <span className="ccard-state">{t.decided === "done" ? "Done" : "Skipped"}</span>
                    ) : (
                      <div className="ccard-actions">
                        <button type="button" className="yes" disabled={handlers.busy} onClick={() => handlers.onDecide(i, true)}>
                          Confirm
                        </button>
                        <button type="button" disabled={handlers.busy} onClick={() => handlers.onDecide(i, false)}>
                          Skip
                        </button>
                      </div>
                    )}
                  </div>
                ) : null}
                {isStillStep(t) ? (
                  <StillStep
                    turn={t}
                    line={handlers.stillLine(t.made?.model ?? handlers.stillModelOf(t).id)}
                    busy={handlers.busy}
                    onApprove={() => handlers.onApprove(i)}
                    held={heldLine(stillsFor(turns, t.reply?.proposal?.args.results).map((s) => s.n))}
                    models={handlers.exempt ? handlers.stillModels.map((m) => ({ ...m, credits: null })) : handlers.stillModels}
                    model={handlers.stillModelOf(t)}
                    onModel={(id) => handlers.onStillModel(i, id)}
                    warn={handlers.stillWarn(t)}
                  />
                ) : null}
                {t.plan ? <PlanCard plan={t.plan} h={handlers.plan(t.plan.id)} /> : null}
                {t.effect ? (
                  <EffectStep
                    turn={t}
                    effect={handlers.effectItem(t.effect.effect)}
                    busy={handlers.busy}
                    exempt={handlers.effectExempt}
                    onChange={handlers.onEffectChange}
                    onApprove={(credits, charged) => handlers.onEffectApprove(t.effect?.id ?? "", credits, charged)}
                  />
                ) : null}
                {isSheetStep(t) ? (
                  <SheetStep
                    turn={t}
                    line={handlers.sheetLine}
                    busy={handlers.busy}
                    onApprove={() => handlers.onApproveSheet(i)}
                  />
                ) : null}
                {i === lastAnswer && choices.length ? (
                  <div className="zc-choices">
                    {choices.map((c) => (
                      <button type="button" key={c} onClick={() => handlers.onChip(c)}>
                        {c}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
            {t.made ? <MadeView m={t.made} live={live[t.made.id]} h={handlers} turn={t} /> : null}
          </motion.article>
        ))}
      </AnimatePresence>
      {working !== null && writing.trim() ? (
        // the answer being written, on the left where it will land; the turn
        // that lands replaces it with the same words, so it is hidden from a
        // screen reader (this stream is a live region and would read every
        // few characters)
        <div className="zc-reply zc-typing" aria-hidden>
          <p>
            <TypedText text={writing.trim()} caret="zc-caret" />
          </p>
        </div>
      ) : null}
      {working !== null ? (
        <div className="zc-working" role="status">
          <span className="zc-live" aria-hidden /> {working || "Thinking…"}
        </div>
      ) : null}
    </div>
  );
}
