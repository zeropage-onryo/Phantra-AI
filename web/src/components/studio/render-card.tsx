"use client";

/* The Render card (2026-10-11, docs/tasks/task-higgsfield-shape.md step 1).

   A scene is rendered from the scene. This is the body the Queue page's
   card used to carry -- the renderer chip with its model / length / frame
   pickers, the priced "Draw keyframes" button, the priced Render button --
   lifted onto its own component so the workspace's scene list, the canvas
   and the composer open the SAME card: one price, one approve, one place
   that can refuse. There is no board to pick a scene on first and no Queue
   page to approve it from.

   What it is told is only the scene's id. Everything it draws is
   GET /api/scenes/{id}/render (the scene, its default renderer, that pick's
   price with its signed tokens, the renderer catalogue); a changed pick
   asks /quote; the click posts /approve with the tokens for THAT pick.
   Nothing here computes a price, and nothing renders without the click.

   "Draft first" (src/drafts.py, where the model has a cheaper frame) only
   moves the pick to that frame; the priced button, then reading "Draft",
   is still the one click that spends. Finishing a draft is on Renders.

   The gates are the server's and are only mirrored here so a dead button
   says why: no reference photos (`blocked`, the reference gate's reason),
   no renderer configured, a length the model does not take, a balance too
   short. The approve asks every one of them again.

   Whether this scene is rendering RIGHT NOW is read off the studio's live
   job list (lib/jobs.ts): the approve names the scene on its job from the
   start, so a card opened in another tab, or reopened, says "Rendering"
   too, and the priced button cannot be pressed twice. */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { Popover } from "@base-ui/react/popover";
import { ChevronDown, X } from "lucide-react";
import {
  announceBalanceChange,
  announceQueueChange,
  drawKeyframes,
  getJob,
  sceneApprove,
  sceneHref,
  sceneQuote,
  sceneRender,
  type Concept,
  type RenderChoice,
  type RenderQuote,
  type RendererSpec,
} from "@/lib/studio-api";
import { cardFonts } from "@/components/studio/card-fonts";
import { RefImg, partsOf, windowLabel } from "@/components/studio/concept-card";
import { useShell } from "@/components/studio/shell";
import { rememberJob, useJobs } from "@/lib/jobs";
import {
  chipText,
  creditsText,
  draftFrame,
  held,
  isDraft,
  keyframeButton,
  keyframeCeilingNote,
  keyframeCount,
  priceText,
  keyframeNote,
  keyframePrice,
  legalDuration,
  liveJobFor,
  pickFor,
  planFor,
  renderText,
  renderedOf,
  shotsToDraw,
  specOf,
  withDraft,
  withModel,
  type AxisLike,
  type Pick,
  type Renderers,
} from "@/lib/render-choice";

const PILL =
  "min-h-11 rounded-[6px] border px-3 font-plex! text-xs! focus-visible:rounded-[6px]! disabled:cursor-not-allowed";
const pill = (on: boolean, off = false) =>
  `${PILL} ${off ? (on ? "border-noir-line3 bg-noir-line3 text-bone!" : "border-noir-line2 text-[var(--dimmer)]!") : on ? "border-bone bg-bone text-noir-bg!" : "border-noir-line3 text-bone! hover:border-bone"}`;
const POPK = "mb-2 font-plex text-[11px] tracking-[0.14em] text-bone3";
const NOTE = "m-0 font-plex text-[11px] tracking-[0.06em] text-bone3";

export type RenderCardProps = {
  conceptId: number;
  /** the scene is open on its canvas already: no "open the canvas" link */
  onCanvas?: boolean;
  /** a render or the keyframes were approved and their job started */
  onStarted?: (what: "render" | "keyframes", jobId: number | null) => void;
  /** the scene as the card last read it -- on open, and again whenever a
   *  render or a keyframe job on it ends. The composer draws the clips it
   *  carries into the chat turn the card sits in. */
  onScene?: (scene: Concept) => void;
  /** the shots are drawn right above the card (the composer's turn): no strip */
  noStrip?: boolean;
  /** THE CHAT'S CARD (2026-10-23, Mike: "i just want approve buttons"):
   *  only the priced Approve buttons -- the keyframes, then the render --
   *  each carrying its model and price, plus why a scene cannot render yet.
   *  No model popover, no draft toggle, no one-shot buttons: the model is
   *  picked on the box's settings line, and the full card still opens from
   *  the storyboard and the workspace. When the last clip lands the chat
   *  joins the shots into one video (the Final cut), as before. */
  approveOnly?: boolean;
};

export function RenderCard({ conceptId, onCanvas, onStarted, onScene, noStrip, approveOnly }: RenderCardProps) {
  const { balance, toast } = useShell();
  const jobs = useJobs();
  const [scene, setScene] = useState<Concept | null>(null);
  const [renderers, setRenderers] = useState<Record<string, RendererSpec>>({});
  const [error, setError] = useState("");
  const [quotes, setQuotes] = useState<Record<string, RenderQuote | { error: string }>>({});
  const [busy, setBusy] = useState<"" | "render" | "keyframes">("");
  const [popOpen, setPopOpen] = useState(false);
  const [, repaint] = useState(0); // `held` lives outside state: it outlives the card
  const seq = useRef(0);
  // held in a ref: a new callback each render must not re-read the scene
  const sceneOut = useRef(onScene);
  useEffect(() => {
    sceneOut.current = onScene;
  }, [onScene]);

  const load = useCallback(() => {
    const mine = ++seq.current;
    return sceneRender(conceptId)
      .then((r) => {
        if (mine !== seq.current) return;
        setScene(r.scene);
        setRenderers(r.renderers || {});
        setError("");
        sceneOut.current?.(r.scene);
      })
      .catch((e) => {
        if (mine === seq.current) setError(e instanceof Error ? e.message : "This scene could not be priced");
      });
  }, [conceptId]);
  useEffect(() => {
    void load();
  }, [load]);

  // what is working on this scene right now, off the one job list
  const rendering = liveJobFor(jobs, conceptId, "render");
  const drawing = liveJobFor(jobs, conceptId, "keyframe");
  // a job on this scene that just ended changed its row: read it back
  const wasLive = useRef(false);
  useEffect(() => {
    const live = !!rendering || !!drawing;
    if (wasLive.current && !live) {
      void load();
      announceQueueChange();
      announceBalanceChange();
    }
    wasLive.current = live;
  }, [rendering, drawing, load]);

  const catalogue = renderers as unknown as Renderers;
  const pick: Pick | null = scene ? pickFor(catalogue, scene.id, scene.render_default) : null;
  const hold = (next: Pick | null) => {
    if (!scene || !next) return;
    held.set(scene.id, next);
    repaint((n) => n + 1);
  };
  const quoteKey = (c: Concept, p: Pick) => `${p.provider}|${p.model}|${p.frame}${c.timeline ? "" : `|${p.duration}`}`;
  const served = (c: Concept, p: Pick): RenderQuote | null => {
    const q = c.quote;
    if (!q || q.error || q.provider !== p.provider || q.model !== p.model || q.frame !== p.frame) return null;
    if (!q.timed && q.durations[0] !== p.duration) return null;
    return q;
  };
  const quote = scene && pick ? served(scene, pick) ?? quotes[quoteKey(scene, pick)] ?? null : null;
  const choiceOf = (p: Pick): RenderChoice => ({
    provider: p.provider,
    model: p.model,
    duration: p.duration ?? undefined,
    frame: p.frame ?? undefined,
  });
  const locked = !!scene && (!!scene.blocked || !(scene.refs || []).length);
  // a pick the card was not served with is priced once, by the server
  const wantKey = scene && pick && !locked && renderers[pick.provider]?.available && !served(scene, pick) ? quoteKey(scene, pick) : "";
  useEffect(() => {
    if (!scene || !pick || !wantKey || wantKey in quotes) return;
    let stale = false;
    sceneQuote(scene.id, choiceOf(pick))
      .then((q) => !stale && setQuotes((w) => ({ ...w, [wantKey]: q })))
      .catch((e) => !stale && setQuotes((w) => ({ ...w, [wantKey]: { error: e instanceof Error ? e.message : "no price" } })));
    return () => {
      stale = true;
    };
    // `pick` is derived from scene + held; wantKey names it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantKey]);

  if (error && !scene) return <p className="m-0 text-[13px] text-noir-danger" role="alert">{error}</p>;
  if (!scene)
    return (
      <div aria-hidden className="flex flex-col gap-3 motion-safe:animate-pulse">
        <div className="h-11 rounded-[8px] bg-noir-raise" />
        <div className="h-[52px] rounded-[8px] bg-noir-slate" />
      </div>
    );

  const exempt = !!balance?.exempt;
  const charged = !!balance && !balance.exempt;
  const parts = partsOf(scene);
  const done = renderedOf(scene.media_url, parts);
  const oneAtATime = shotsToDraw(parts, scene.keyframes?.stills);
  const r = pick ? renderers[pick.provider] : undefined;
  const spec = pick ? specOf(catalogue, pick.provider, pick.model) : null;
  const plan = pick && spec ? planFor(spec, pick, scene.timeline ? parts : null, quote) : null;
  const noKey = r && !r.available ? `${r.label} is not configured` : "";
  const badLength = !!(pick && spec && plan && !plan.timed && !legalDuration(spec.duration as AxisLike, Number(pick.duration)));
  const short = !!plan && plan.credits !== null && charged && plan.credits > balance!.available;
  const working = !!rendering || busy === "render";
  const disabled = locked || !pick || !!noKey || badLength || short || working || done.state === "done";
  const label = working
    ? "Rendering…"
    : done.state === "done"
      ? "Rendered"
      : locked
        ? "Add references to render"
        : !pick || !spec || !plan
          ? "No renderer is configured"
          : noKey
            ? noKey
            : badLength
              ? `${spec.id} renders ${spec.duration.min}-${spec.duration.max}s`
              : short
                ? `Need ${plan.credits!.toLocaleString("en-US")} cr · have ${Math.max(balance!.available, 0).toLocaleString("en-US")}`
                : renderText(plan, exempt, isDraft(spec, pick));
  const providerIds = Object.keys(renderers);
  const why = locked
    ? `Cannot render yet · ${scene.blocked || "no reference photos attached"}`
    : done.state === "done"
      ? "Every shot has its clip."
      : done.state === "partial"
        ? `${done.clips} of ${done.of} shots rendered · Render makes the other ${done.of - done.clips}`
        : keyframeNote(parts, scene.reference_image);

  const approve = async () => {
    if (disabled || !pick) return;
    setBusy("render");
    setPopOpen(false);
    try {
      // the tokens always describe THIS pick: a pick the card was not
      // served with is quoted on the click when its price has not landed
      const cached = quote && !("error" in quote && quote.error) ? (quote as RenderQuote) : await sceneQuote(scene.id, choiceOf(pick));
      const tokens = (cached.renders || []).map((x) => x.token).filter((t): t is string => !!t);
      const res = await sceneApprove(scene.id, tokens.length ? { ...choiceOf(pick), tokens } : choiceOf(pick));
      const made = res.render;
      const charge = res.quote && res.quote.credits != null ? creditsText(res.quote.credits, exempt) : null;
      toast(made ? `Rendering ${scene.n} — ${made.model} · ${made.frame}${charge ? ` · ${charge}` : ""}` : `Rendering ${scene.n}`);
      held.delete(scene.id);
      // the job BEFORE the button is released: "rendering" is read off the
      // job list, and a priced button live for the beat before the stream
      // says so is a button that can be pressed twice
      if (res.job_id) await getJob(res.job_id).then(rememberJob).catch(() => {});
      announceQueueChange();
      announceBalanceChange();
      onStarted?.("render", res.job_id ?? null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "That did not go through", "err");
      void load(); // a refusal usually means the scene or the price moved
    } finally {
      setBusy("");
    }
  };
  // `part` draws that one shot's still, at one still's price; none is the strip
  const draw = async (part?: number) => {
    const q = scene.keyframes;
    if (!q || busy || drawing) return;
    setBusy("keyframes");
    try {
      const res = await drawKeyframes(scene.id, part);
      toast(
        part === undefined
          ? `Drawing ${keyframeCount(q)} for ${scene.n} — ${keyframePrice(q, exempt)}`
          : `Drawing shot ${part}'s keyframe for ${scene.n} — ${creditsText(res.keyframes?.credits ?? q.each, exempt)}`,
      );
      if (res.job_id) await getJob(res.job_id).then(rememberJob).catch(() => {});
      announceBalanceChange();
      onStarted?.("keyframes", res.job_id ?? null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "That did not go through", "err");
    } finally {
      setBusy("");
    }
  };

  if (approveOnly) {
    const modelName = pick ? (r?.models || []).find((m) => m.id === pick.model)?.label || pick.model : "";
    const ready = !disabled && !!plan;
    const approveLabel = ready ? `Approve · ${modelName} · ${plan!.n} shot${plan!.n === 1 ? "" : "s"} · ${priceText(plan!, exempt)}` : label;
    const kf = !locked && done.state !== "done" && (scene.keyframes || drawing) ? scene.keyframes : null;
    return (
      <div className="flex min-w-0 flex-col gap-2" data-render-card={scene.id} data-approve-only="">
        {locked ? (
          <>
            <p className={`${NOTE} text-noir-danger!`} role="alert">
              {why}
            </p>
            {!onCanvas ? (
              <Link
                href={sceneHref(scene.id, 1)}
                className="inline-flex min-h-11 items-center self-start rounded-[8px] border border-noir-line px-3 font-plex! text-[11px]! tracking-[0.08em] text-noir-red2! hover:border-noir-red2"
              >
                ATTACH REFERENCES ON ITS CANVAS →
              </Link>
            ) : null}
          </>
        ) : null}
        {kf || drawing ? (
          <button
            type="button"
            disabled={!!drawing || busy === "keyframes" || working || !scene.keyframes}
            onClick={() => void draw()}
            className="inline-flex min-h-11 items-center justify-between gap-2 rounded-[8px] border border-noir-line px-3 font-plex! text-[11px]! tracking-[0.08em] text-bone! hover:enabled:border-bone disabled:cursor-wait disabled:text-bone3!"
          >
            <span>
              {drawing || busy === "keyframes"
                ? `DRAWING KEYFRAMES…${drawing?.detail ? ` ${drawing.detail.toUpperCase()}` : ""}`
                : `APPROVE ${keyframeCount(scene.keyframes!).toUpperCase()}`}
            </span>
            {scene.keyframes ? <span className="shrink-0 whitespace-nowrap">{keyframePrice(scene.keyframes, exempt).toUpperCase()}</span> : null}
          </button>
        ) : null}
        {done.state !== "done" && !locked ? (
          <button
            type="button"
            data-render={scene.id}
            disabled={disabled}
            title={approveLabel}
            onClick={() => void approve()}
            className="min-h-11 min-w-0 truncate rounded-[8px] bg-noir-red px-3 font-tight! text-[14px]! font-semibold leading-none! text-noir-bg! hover:enabled:bg-noir-red2 focus-visible:rounded-[8px]! disabled:cursor-not-allowed disabled:bg-noir-line2 disabled:text-bone3!"
          >
            {approveLabel}
          </button>
        ) : null}
        {rendering ? (
          <p className={NOTE} role="status">
            {rendering.detail || "Rendering"} · the shots join into one video when the last one lands.
          </p>
        ) : done.state === "partial" && !locked ? (
          <p className={NOTE}>{why}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-col gap-3" data-render-card={scene.id}>
      {/* the shots, as frames whose WIDTH is their share of the scene */}
      {parts.length && !noStrip ? (
        <div className="flex min-w-0 gap-1" role="group" aria-label={`${parts.length} shots`}>
          {parts.map((p) => (
            <div
              key={p.n}
              style={{ flexGrow: Number(p.seconds) > 0 ? Number(p.seconds) : 1 }}
              className={`relative h-11 min-w-0 basis-0 overflow-hidden rounded-[4px] bg-noir-slate ${p.media_url ? "opacity-60" : ""}`}
              title={p.text || p.prompt || ""}
            >
              {p.reference_image ? <RefImg url={p.reference_image} className="block size-full object-cover" deadLabel="" /> : null}
              <span className="absolute bottom-1 left-1.5 whitespace-nowrap font-plex text-[10px] leading-none text-bone [text-shadow:0_0_3px_#000,0_0_3px_#000]">
                {windowLabel(p)}
                {p.media_url ? " ✓" : ""}
              </span>
            </div>
          ))}
        </div>
      ) : null}
      <p className={`${NOTE} ${locked ? "text-noir-danger!" : ""}`} role={locked ? "alert" : undefined}>
        {why}
      </p>
      {/* what the shot planner put back and what will not fit (src/timeline.py
          keep): a reference it had left off every shot, a shot with no photos,
          a voiceover longer than its window. Facts, not a lock: Render stays. */}
      {(scene.timeline?.warnings || []).length ? (
        <ul className="m-0 flex list-none flex-col gap-1 p-0" aria-label="Notes on the shots">
          {scene.timeline!.warnings!.map((w) => (
            <li key={w} className={`${NOTE} text-noir-red2`}>
              {w}
            </li>
          ))}
        </ul>
      ) : null}
      {locked && !onCanvas ? (
        <Link
          href={sceneHref(scene.id, 1)}
          className="inline-flex min-h-11 items-center self-start rounded-[8px] border border-noir-line px-3 font-plex! text-[11px]! tracking-[0.08em] text-noir-red2! hover:border-noir-red2"
        >
          ATTACH REFERENCES ON ITS CANVAS →
        </Link>
      ) : null}

      {!locked && done.state !== "done" && (scene.keyframes || drawing) ? (
        // nothing is drawn until this is pressed (2026-09-29): a still costs credits
        <button
          type="button"
          disabled={!!drawing || busy === "keyframes" || working || !scene.keyframes}
          onClick={() => void draw()}
          className="inline-flex min-h-11 items-center justify-between gap-2 rounded-[8px] border border-noir-line px-3 font-plex! text-[11px]! tracking-[0.08em] text-bone! hover:enabled:border-bone disabled:cursor-wait disabled:text-bone3!"
        >
          <span>
            {drawing || busy === "keyframes"
              ? `DRAWING KEYFRAMES…${drawing?.detail ? ` ${drawing.detail.toUpperCase()}` : ""}`
              : keyframeButton(scene.keyframes!).toUpperCase()}
          </span>
          {/* the price never breaks: "UP TO 66 CREDITS" is one thing to read */}
          {scene.keyframes ? (
            <span className="shrink-0 whitespace-nowrap">{keyframePrice(scene.keyframes, exempt).toUpperCase()}</span>
          ) : null}
        </button>
      ) : null}
      {/* a price that is a ceiling says why it may come in lower (2026-10-11) */}
      {!locked && done.state !== "done" && !drawing && keyframeCeilingNote(scene.keyframes) ? (
        <p className={NOTE}>{keyframeCeilingNote(scene.keyframes)}</p>
      ) : null}
      {!locked && done.state !== "done" && oneAtATime.length ? (
        // one shot's still on its own (2026-10-11): a shot worth looking at
        // before the strip is paid for. Each button is its own priced click.
        <div className="flex min-w-0 flex-wrap items-center gap-1.5" role="group" aria-label="Draw one shot's keyframe">
          {/* the price is on every button; "not charged" is said once, here */}
          <span className={`${NOTE} w-full`}>{exempt ? "Or one shot · not charged:" : "Or one shot:"}</span>
          {oneAtATime.map((p) => (
            <button
              key={p.n}
              type="button"
              disabled={!!drawing || busy === "keyframes" || working}
              onClick={() => void draw(p.n)}
              aria-label={`Draw shot ${p.n}'s keyframe, ${creditsText(scene.keyframes!.each, exempt)}`}
              className="inline-flex min-h-11 items-center gap-2 rounded-[8px] border border-noir-line px-3 font-plex! text-[11px]! tracking-[0.08em] text-bone! hover:enabled:border-bone disabled:cursor-wait disabled:text-bone3!"
            >
              <span>SHOT {p.n}</span>
              <span className="text-bone3">{scene.keyframes!.each.toLocaleString("en-US")} CR</span>
            </button>
          ))}
        </div>
      ) : null}

      {/* the renderer: ONE chip, and a popover over the same catalogue */}
      {done.state !== "done" ? (
        <Popover.Root open={popOpen && !working && !locked && !!pick} onOpenChange={setPopOpen}>
          <Popover.Trigger
            disabled={locked || !pick || working}
            aria-label={locked || !pick ? "Renderer locked" : `Change renderer — ${spec && plan ? chipText(spec, pick, plan) : ""}`}
            className="flex h-11 w-full items-center justify-between gap-2 rounded-[8px] border border-noir-line bg-noir-well px-3 font-plex! text-xs! leading-none! tracking-[0.06em] text-bone! hover:enabled:border-bone focus-visible:rounded-[8px]! disabled:cursor-not-allowed disabled:text-bone3! data-[popup-open]:[&>svg]:rotate-180"
          >
            <span className="min-w-0 truncate">
              {locked ? "RENDERER LOCKED" : !pick || !spec || !plan ? "NO RENDERER CONFIGURED" : chipText(spec, pick, plan)}
            </span>
            <ChevronDown size={16} strokeWidth={2} aria-hidden className="flex-none" />
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Positioner side="bottom" align="start" sideOffset={8} className="z-[960]">
              <Popover.Popup
                aria-label={`Renderer for ${scene.title}`}
                className={`${cardFonts} flex w-[var(--anchor-width)] min-w-[280px] flex-col gap-2.5 rounded-[10px] border border-noir-line3 bg-noir-raise p-4 text-bone shadow-[0_18px_40px_rgb(0_0_0/0.55)] outline-none`}
              >
                {pick && spec && plan && r ? (
                  <>
                    <div>
                      <div className={POPK}>MODEL</div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {providerIds.map((name) => {
                          const v = renderers[name];
                          // an unconfigured renderer is one dead pill, not a row of them
                          if (!v.available)
                            return (
                              <button type="button" key={name} disabled className={pill(false, true)}>
                                {v.label} · not configured
                              </button>
                            );
                          return (v.models || []).map((m) => (
                            <button
                              type="button"
                              key={`${name}|${m.id}`}
                              title={v.label}
                              disabled={m.available === false}
                              aria-pressed={pick.provider === name && pick.model === m.id}
                              className={pill(pick.provider === name && pick.model === m.id, m.available === false)}
                              onClick={() => hold(withModel(catalogue, name, m.id))}
                            >
                              {m.label}
                              {m.available === false ? " · not on this account" : ""}
                            </button>
                          ));
                        })}
                      </div>
                    </div>
                    <div className="mt-1 grid grid-cols-2 gap-3">
                      <div>
                        <div className={POPK}>LENGTH{plan.timed ? " · PER SHOT" : ""}</div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {plan.timed ? (
                            // no length control: every shot's length is its window's
                            <span className="font-plex text-[11px] text-bone3" title={`each shot renders at its own window's length, fitted up to what ${spec.id} can make`}>
                              {plan.lengths.length ? `${plan.lengths.join(" + ")}s · set by the windows` : plan.refused || "pricing…"}
                            </span>
                          ) : spec.duration.kind === "range" ? (
                            <span className="flex items-center gap-2 font-plex text-[11px] text-bone3">
                              <input
                                type="number"
                                min={spec.duration.min}
                                max={spec.duration.max}
                                step={1}
                                value={pick.duration ?? ""}
                                aria-label={`Length in seconds, ${spec.duration.min} to ${spec.duration.max}`}
                                onChange={(e) => hold({ ...pick, duration: e.target.value === "" ? null : Number(e.target.value) })}
                                className="h-11 w-[72px] rounded-[6px] border border-noir-line3 bg-noir-well text-center font-plex! text-[13px]! text-bone! outline-none focus:border-bone"
                              />
                              sec · {spec.duration.min}–{spec.duration.max}
                            </span>
                          ) : (
                            (spec.duration.values || []).map((d) => (
                              <button
                                type="button"
                                key={String(d)}
                                disabled={spec.duration.kind === "fixed"}
                                title={spec.duration.kind === "fixed" ? spec.duration.note || "the only length this model offers" : undefined}
                                aria-pressed={Number(d) === pick.duration}
                                className={pill(Number(d) === pick.duration, spec.duration.kind === "fixed")}
                                onClick={() => hold({ ...pick, duration: Number(d) })}
                              >
                                {d}s
                              </button>
                            ))
                          )}
                        </div>
                      </div>
                      <div>
                        <div className={POPK}>FRAME · {String(r.frame_axis || "resolution").toUpperCase()}</div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {(spec.frame.values || []).map((f) => (
                            <button
                              type="button"
                              key={String(f)}
                              disabled={spec.frame.kind === "fixed"}
                              title={spec.frame.kind === "fixed" ? spec.frame.note || "the only frame this model offers" : undefined}
                              aria-pressed={String(f) === pick.frame}
                              className={pill(String(f) === pick.frame, spec.frame.kind === "fixed")}
                              onClick={() => hold({ ...pick, frame: String(f) })}
                            >
                              {String(f)}
                              {String(f) === draftFrame(spec) ? " · draft" : ""}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="font-plex text-[11px] text-bone3">Greyed out = not available on this server</div>
                  </>
                ) : null}
              </Popover.Popup>
            </Popover.Positioner>
          </Popover.Portal>
        </Popover.Root>
      ) : null}

      {pick && scene.render_model && pick.model === scene.render_model && !locked && done.state !== "done" ? (
        // The brain proposed this model for the scene (src/model_menu.py): it
        // is only where the card opened -- the pick above is the person's.
        <p className={NOTE} data-proposed={scene.id}>
          Proposed for this scene{scene.render_model_why ? `: ${scene.render_model_why}` : ""}. Pick another above if you
          prefer.
        </p>
      ) : null}

      {pick && spec && draftFrame(spec) && !locked && done.state !== "done" ? (
        // Draft, then finish (src/drafts.py): the same render at this model's
        // cheapest frame. It only changes the pick -- the priced button below
        // is still the one click that spends.
        <button
          type="button"
          data-draft={scene.id}
          aria-pressed={isDraft(spec, pick)}
          disabled={working}
          title={`Render at ${draftFrame(spec)} first: the cheapest ${spec.id} makes. Finish the take you keep from Renders.`}
          className={`${pill(isDraft(spec, pick))} w-full`}
          onClick={() => hold(withDraft(spec, pick, !isDraft(spec, pick)))}
        >
          {isDraft(spec, pick) ? `Drafting at ${draftFrame(spec)} · tap for full quality` : `Draft first · ${draftFrame(spec)} · cheaper`}
        </button>
      ) : null}

      <button
        type="button"
        data-render={scene.id}
        disabled={disabled}
        title={label}
        onClick={() => void approve()}
        className="h-[52px] min-w-0 truncate rounded-[8px] bg-noir-red px-2.5 font-bebas! text-[22px]! leading-none! tracking-[0.05em] text-noir-bg! hover:enabled:bg-noir-red2 focus-visible:rounded-[8px]! disabled:cursor-not-allowed disabled:bg-noir-line2 disabled:text-bone3! max-sm:text-[18px]!"
      >
        {label}
      </button>
      {rendering ? (
        <p className={NOTE} role="status">
          {rendering.detail || "Rendering"} · it keeps going if you close this. Renders lists it.
        </p>
      ) : done.state !== "done" && !locked ? (
        <p className={NOTE}>Nothing is rendered until you press it. Credit is held first and released if the render fails.</p>
      ) : null}
    </div>
  );
}

/** The Render card in a dialog: what the scene list's Render button and the
 *  canvas's "Render…" open (the composer draws the card in its turn). `conceptId` null = shut. */
export function RenderDialog({
  conceptId,
  title,
  onCanvas,
  onClose,
}: {
  conceptId: number | null;
  title?: string;
  onCanvas?: boolean;
  onClose: () => void;
}) {
  return (
    <Dialog.Root
      open={conceptId !== null}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[940] bg-black/60" />
        <Dialog.Popup
          className={`${cardFonts} fixed left-1/2 top-1/2 z-[941] flex max-h-[calc(100dvh-32px)] w-[460px] max-w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-[12px] border border-noir-line bg-noir-panel p-5 font-tight text-sm text-bone outline-none [color-scheme:dark]`}
        >
          <div className="flex min-w-0 items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="font-plex text-[11px] tracking-[0.14em] text-bone3">RENDER</div>
              <Dialog.Title className="m-0 truncate font-bebas text-[26px] font-normal leading-none tracking-[0.03em]">
                {title || "This scene"}
              </Dialog.Title>
            </div>
            <Dialog.Close
              aria-label="Close"
              className="flex size-9 flex-none items-center justify-center rounded-[8px] border border-noir-line bg-transparent p-0 text-bone2! hover:border-bone hover:text-bone!"
            >
              <X size={16} strokeWidth={2} aria-hidden />
            </Dialog.Close>
          </div>
          {conceptId !== null ? <RenderCard key={conceptId} conceptId={conceptId} onCanvas={onCanvas} /> : null}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
