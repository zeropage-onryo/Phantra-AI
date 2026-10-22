"use client";

/* The Effects tab (/studio/effects, 2026-10-22, docs/tasks/task-effects-tab.md),
   behind the `effects_tab` capability (the server page does the 404).

   One table, two doors. This page reads the SAME effects listing the
   composer's `/effects` gallery reads (GET /api/effects, lib/effects.ts) and
   opens the SAME priced card (effect-step.tsx) -- so an effect is never
   described in two places and never priced in two places. What this page
   adds is a way in: a drop zone whose clip or still becomes the source for
   every card, before / after cards that play on hover, a Free or Pro badge
   (never a credit number; the number is on the card a click opens), and
   two filters read off the table's own fields.

   NOTHING RUNS FROM A CARD. A click opens the priced card; its Approve is
   the one click that spends, at the price it showed, through
   POST /api/effects/run exactly as the composer does. A finished result
   offers Make It Pro (the bundle's own card, when the table has it), Share
   (the Library's share and download) and a hand-off to Vesper. */
import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import Link from "next/link";
import { Download, FolderOpen, Sparkles, Upload, Wand2, X } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { EffectStep } from "@/components/studio/effect-step";
import { ShareControls } from "@/components/studio/asset-viewer";
import { mediaSrc, newMadeId, type Made } from "@/lib/composer";
import { madeStatus } from "@/lib/made-state";
import { assetId } from "@/lib/continue";
import { begin, candidateOf, requestOf, unavailable, type Candidate, type Effect, type EffectState } from "@/lib/effects";
import {
  AUDIENCES,
  TIERS,
  acceptsFile,
  badgeOf,
  filterEffects,
  fits,
  makeItPro,
  sourceLine,
  tierCounts,
  tierOf,
  vesperHref,
  type Audience,
  type Tier,
} from "@/lib/effects-tab";
import { isPlaceholder, itemFor, loadShowcase, restingFrame, type ShowcaseItem, type ShowcaseManifest } from "@/lib/showcase";
import {
  announceBalanceChange,
  cutUploadMedia,
  getEffects,
  getMedia,
  renderDownloadHref,
  runEffect,
  uploadRefs,
  waitForJob,
  type EffectsCatalogue,
  type Job,
  type MediaItem,
} from "@/lib/studio-api";
import type { Turn } from "@/lib/assistant";
import "@/components/studio/asset-viewer.css";
import "@/components/studio/effects-tab.css";
/* eslint-disable @next/next/no-img-element */

/* ── one before / after card ── */
function ShowcaseCard({ effect, item, why, onOpen }: { effect: Effect; item: ShowcaseItem; why: string; onOpen: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const clip = item.kind === "clip";
  const play = () => {
    const v = video.current;
    if (!clip || !v) return;
    v.play()
      .then(() => setPlaying(true))
      .catch(() => {});
  };
  const stop = () => {
    const v = video.current;
    if (!clip || !v) return;
    v.pause();
    v.currentTime = 0;
    setPlaying(false);
  };
  return (
    <li>
      <button
        type="button"
        className="fxt-card"
        disabled={!!why}
        onClick={onOpen}
        onMouseEnter={play}
        onMouseLeave={stop}
        onFocus={play}
        onBlur={stop}
        aria-label={`${effect.label} · ${badgeOf(effect)}${why ? ` · ${why}` : ""}`}
      >
        {/* every tile is 16:9 so the rows line up; a vertical or square
            example sits letterboxed inside it (data-fit), never stretched */}
        <span className="fxt-media" data-fit={item.aspect === "16:9" ? undefined : "contain"} data-playing={playing ? "1" : undefined}>
          <img src={restingFrame(item)} alt="" loading="lazy" />
          {clip ? (
            <video ref={video} className="after" src={item.after} poster={item.poster ?? undefined} muted loop playsInline preload="none" />
          ) : item.before ? (
            <img className="after" src={item.after} alt="" loading="lazy" />
          ) : null}
          {!isPlaceholder(item) ? <span className="lab">{clip || item.before ? "hover · after" : "example"}</span> : null}
          <span className="fxt-badge" data-tier={tierOf(effect)}>
            {badgeOf(effect)}
          </span>
        </span>
        <span className="fxt-card-body">
          <b>{effect.label}</b>
          <span>{effect.blurb}</span>
          {why ? <i>{why}</i> : <small>{effect.takes === "video" ? "on a clip" : "on a still"}</small>}
        </span>
      </button>
    </li>
  );
}

/* ── the page ── */
export function EffectsTab() {
  const { me, toast } = useShell();
  const [fx, setFx] = useState<EffectsCatalogue | null>(null);
  const [fxError, setFxError] = useState("");
  const [showcase, setShowcase] = useState<ShowcaseManifest | null>(null);
  const [tier, setTier] = useState<Tier>("all");
  const [audience, setAudience] = useState<Audience>("all");
  const [source, setSource] = useState<Candidate | null>(null);
  const [over, setOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [picker, setPicker] = useState<MediaItem[] | null>(null);
  // the open priced card: one at a time, the composer's own component on a
  // turn this page holds. `made` lands on it when Approve has run.
  const [card, setCard] = useState<{ turn: Turn; effect: Effect } | null>(null);
  const [busy, setBusy] = useState(false);
  // every result this visit made, newest first, each with its three actions
  const [results, setResults] = useState<{ turn: Turn; effect: Effect }[]>([]);
  const file = useRef<HTMLInputElement>(null);
  const workspace = me?.account?.slug ?? "";

  useEffect(() => {
    if (!workspace) return;
    let live = true;
    getEffects()
      .then((r) => live && setFx(r))
      .catch((e) => live && setFxError(e instanceof Error ? e.message : "The effects could not be listed"));
    loadShowcase().then((m) => live && setShowcase(m));
    return () => {
      live = false;
    };
  }, [workspace]);

  const items = useMemo(() => filterEffects(fx?.items ?? [], tier, audience), [fx, tier, audience]);
  const counts = useMemo(() => tierCounts(fx?.items ?? []), [fx]);
  const bundle = useMemo(() => makeItPro(fx?.items ?? []), [fx]);
  const candidates = useMemo(() => (source ? [source] : []), [source]);

  /* ── the source: a dropped file, or a pick from the Library ──
     "It becomes the source for every card": a card already open and still
     waiting is bound to the new source too (a card that has run keeps the
     source it ran on). */
  const load = useCallback((next: Candidate | null) => {
    setSource(next);
    setCard((c) => {
      if (!c || c.turn.made || !c.turn.effect) return c;
      const on = next && fits(c.effect, next) ? [next] : [];
      const state = begin(c.effect, on, c.turn.effect.id, { on, options: c.turn.effect.options, prompt: c.turn.effect.prompt });
      return { ...c, turn: { ...c.turn, effect: state } };
    });
  }, []);
  const takeFile = useCallback(
    async (f: File) => {
      const kind = acceptsFile(f);
      if (!kind) {
        toast("Drop a clip (mp4, mov, webm) or a still (jpg, png, webp)", "err");
        return;
      }
      setLoading(true);
      try {
        if (kind === "clip") {
          const up = await cutUploadMedia(f);
          load({ ref: up.handle, kind: "clip", from: `dropped · ${f.name}` });
        } else {
          const up = await uploadRefs([f]);
          const url = up.urls[0];
          if (!url) throw new Error("That image could not be read");
          load({ ref: url, kind: "image", thumb: url, from: `dropped · ${f.name}` });
        }
        setPicker(null);
      } catch (e) {
        toast(e instanceof Error ? e.message : "That could not be loaded", "err");
      } finally {
        setLoading(false);
      }
    },
    [load, toast],
  );
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void takeFile(f);
  };
  const openPicker = () => {
    if (picker) return setPicker(null);
    getMedia({})
      .then((w) => setPicker(w.items.filter((m) => m.generated_id)))
      .catch(() => toast("The Library could not be read", "err"));
  };
  const pick = (m: MediaItem) => {
    const clip = m.kind === "video";
    load({
      ref: `gen:${m.generated_id}`,
      kind: clip ? "clip" : "image",
      thumb: clip ? (m.poster ?? undefined) : (m.thumb ?? m.url),
      from: "your Library",
    });
    setPicker(null);
  };

  /* ── a card: the composer's own priced step, on this page's turn ── */
  const open = (effect: Effect, on?: Candidate[]) => {
    const state = begin(effect, candidates, newMadeId(), { on: on ?? null });
    setCard({ turn: { role: "assistant", content: effect.label, effect: state }, effect });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const change = (next: EffectState) =>
    setCard((c) => (c && c.turn.effect?.id === next.id && c.turn.made?.status !== "running" ? { ...c, turn: { ...c.turn, effect: next } } : c));
  const patch = (id: string, fields: Partial<Made>) => {
    const apply = (t: Turn) => (t.made?.id === id && t.made ? { ...t, made: { ...t.made, ...fields } } : t);
    setCard((c) => (c ? { ...c, turn: apply(c.turn) } : c));
    setResults((all) => all.map((r) => ({ ...r, turn: apply(r.turn) })));
  };
  const finish = (madeId: string, job: Job) => {
    announceBalanceChange();
    const out = typeof job.output === "string" ? job.output : "";
    if (job.status !== "done" || !out) {
      const why = job.error || "The effect was not made. Nothing was charged.";
      patch(madeId, { status: "failed", detail: why });
      toast(why, "err");
      return;
    }
    const extra = job as unknown as { media?: string; asset?: string | null };
    patch(madeId, {
      status: "done",
      detail: job.detail || "",
      asset: extra.asset ?? null,
      ...(extra.media === "video" ? { clip: out, image: null } : { image: out, clip: null }),
    });
  };
  /* Approve: the one click that spends, at the price the card showed. The
     body is the composer's (page.tsx approveEffect), on this page's turn. */
  async function approve(credits: number, charged: boolean) {
    const state = card?.turn.effect;
    if (!card || !state || busy || card.turn.made?.status === "running") return;
    const madeId = newMadeId();
    const made: Made = {
      id: madeId,
      output: "image",
      refs: [],
      status: "running",
      detail: `${state.label}…`,
      prompt: state.prompt,
      effect: state.effect,
      model: state.effect,
    };
    const running = { ...card, turn: { ...card.turn, made, effect: { ...state, paid: { credits, charged } } } };
    setBusy(true);
    setCard(running);
    setResults((all) => [running, ...all]);
    try {
      const started = await runEffect({ ...requestOf(state), expect_credits: credits });
      patch(madeId, { jobId: started.job_id });
      const job = await waitForJob(started.job_id, (j) => patch(madeId, { detail: j.detail || "" }));
      finish(madeId, job);
    } catch (e) {
      // refused before anything ran (a price that moved, a source that is
      // gone): the card goes back to waiting and prices itself again
      setResults((all) => all.filter((r) => r.turn.made?.id !== madeId));
      setCard((c) => (c && c.turn.effect?.id === state.id ? { ...c, turn: { ...c.turn, made: undefined, effect: { ...state, paid: undefined } } } : c));
      toast(e instanceof Error ? e.message : "That did not go through.", "err");
    } finally {
      setBusy(false);
    }
  }

  const ready = !!fx?.ready;
  const sourceThumb = source?.thumb ? mediaSrc(source.thumb) : "";

  return (
    <section className="view fxt" style={{ paddingTop: 0 }}>
      <div className="vhead" style={{ marginTop: 8 }}>
        <h2>Effects</h2>
        <span className="spacer" />
        <span className="m">Browsing is free. A card shows its price before anything runs.</span>
      </div>

      {/* 1. the drop zone: what every card works on */}
      <div
        className="fxt-drop"
        data-over={over ? "1" : undefined}
        data-loaded={source ? "1" : undefined}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <div className="fxt-drop-what">
          {sourceThumb ? <img src={sourceThumb} alt="" /> : <Upload strokeWidth={1.5} />}
          <div>
            <b>{source ? (source.kind === "clip" ? "Your clip" : "Your still") : "Drop a clip"}</b>
            <span>{loading ? "Loading…" : sourceLine(source)}</span>
          </div>
        </div>
        <div className="fxt-drop-acts">
          <input
            ref={file}
            type="file"
            accept="video/*,image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void takeFile(f);
              e.target.value = "";
            }}
          />
          <button type="button" className="fxt-btn primary" onClick={() => file.current?.click()} disabled={loading}>
            <Upload strokeWidth={1.8} /> Choose a file
          </button>
          <button type="button" className="fxt-btn" onClick={openPicker} disabled={loading} aria-expanded={!!picker}>
            <FolderOpen strokeWidth={1.8} /> Pick from the Library
          </button>
          {source ? (
            <button type="button" className="fxt-btn" onClick={() => load(null)}>
              <X strokeWidth={1.8} /> Clear
            </button>
          ) : null}
        </div>
      </div>

      {picker ? (
        <div className="fxt-pick" role="dialog" aria-label="Pick from the Library">
          <div className="fxt-pick-head">
            <b>Your Library</b>
            <span>{picker.length ? "A render becomes the source for every card." : "Nothing on the wall yet."}</span>
            <button type="button" className="fxt-btn" style={{ marginLeft: "auto" }} onClick={() => setPicker(null)}>
              <X strokeWidth={1.8} /> Close
            </button>
          </div>
          <ul className="fxt-pick-grid">
            {picker.map((m) => (
              <li key={m.asset_id}>
                <button type="button" onClick={() => pick(m)} title={m.prompt || m.asset_name} aria-label={`Use ${m.kind} ${m.generated_id}`}>
                  {m.kind === "video" ? m.poster ? <img src={mediaSrc(m.poster)} alt="" loading="lazy" /> : null : <img src={mediaSrc(m.thumb ?? m.url)} alt="" loading="lazy" />}
                  <span className="k">{m.kind === "video" ? "clip" : "still"}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* the open priced card, beside its result */}
      {card ? (
        <div className="fxt-open" role="region" aria-label={`${card.effect.label} card`}>
          <div className="fxt-open-head">
            <Wand2 strokeWidth={1.6} width={14} height={14} />
            <b>{card.effect.label}</b>
            <span>{badgeOf(card.effect)} · the price is on the card; nothing runs until Approve</span>
            <button type="button" className="x" aria-label="Close the card" onClick={() => setCard(null)}>
              <X strokeWidth={1.8} />
            </button>
          </div>
          <EffectStep turn={card.turn} effect={card.effect} busy={busy} exempt={!!fx?.exempt} onChange={change} onApprove={approve} />
          <ResultPane turn={card.turn} effect={card.effect} bundle={bundle} onMakeItPro={(on) => bundle && open(bundle, on)} />
        </div>
      ) : null}

      {/* 2. the filters, read off the table */}
      <div className="fxt-filters">
        <div role="group" aria-label="Free or Pro">
          {TIERS.map((t) => (
            <button key={t.id} type="button" aria-pressed={tier === t.id} onClick={() => setTier(t.id)}>
              {t.label}
              {t.id === "free" && counts.free ? ` · ${counts.free}` : t.id === "pro" && counts.pro ? ` · ${counts.pro}` : ""}
            </button>
          ))}
        </div>
        <div role="group" aria-label="What it is for">
          {AUDIENCES.map((a) => (
            <button key={a.id} type="button" aria-pressed={audience === a.id} onClick={() => setAudience(a.id)}>
              {a.label}
            </button>
          ))}
        </div>
        <span className="m">{fx ? `${items.length} of ${fx.items.length}` : fxError ? "" : "Loading…"}</span>
      </div>
      {fxError ? <p className="fxt-note">{fxError}</p> : null}
      {fx && !ready ? <p className="fxt-note">Effects are not set up on this server yet. The cards show what each one does.</p> : null}

      {/* 3. the grid: one before / after card per effect the table runs today */}
      <ul className="fxt-grid" aria-label="Effects">
        {items.map((e) => (
          <ShowcaseCard
            key={e.id}
            effect={e}
            item={itemFor(showcase, e.id)}
            why={!ready ? "" : source && !fits(e, source) ? (e.takes === "video" ? "Needs a clip" : "Needs a still") : ""}
            onOpen={() => open(e)}
          />
        ))}
      </ul>
      {fx && items.length === 0 ? <p className="m">Nothing under these filters.</p> : null}

      {/* 4. what this visit made */}
      {results.length ? (
        <>
          <div className="vhead">
            <h2>Results</h2>
            <span className="spacer" />
            <span className="m">Every result is in your Library too.</span>
          </div>
          <ul className="fxt-results">
            {results.map((r) => (
              <li key={r.turn.made?.id ?? r.turn.effect?.id}>
                <b>{r.effect.label}</b>
                <ResultPane turn={r.turn} effect={r.effect} bundle={bundle} onMakeItPro={(on) => bundle && open(bundle, on)} compact />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

/* ── a result and its three doors ── */
function ResultPane({
  turn,
  effect,
  bundle,
  onMakeItPro,
  compact,
}: {
  turn: Turn;
  effect: Effect;
  bundle: Effect | null;
  onMakeItPro: (on: Candidate[]) => void;
  compact?: boolean;
}) {
  const made = turn.made;
  const status = made ? madeStatus(made) : undefined;
  if (!made || status !== "done") {
    return (
      <div className="fxt-result">
        <div className="fxt-result-empty">
          {!made
            ? "The result lands here. Approve on the card runs it at the price shown."
            : status === "running"
              ? made.detail || "Working…"
              : made.detail || "Not made. Nothing was charged."}
        </div>
      </div>
    );
  }
  const id = assetId(made.asset);
  const self = candidateOf({ image: made.image, clip: made.clip, asset: made.asset }, "this result");
  const toVesper = vesperHref(made.asset, effect.label);
  const proWhy = bundle && self ? unavailable(bundle, [self]) : "";
  return (
    <div className="fxt-result">
      {made.clip ? (
        <video className="fxt-result-media" src={mediaSrc(made.clip)} controls playsInline />
      ) : made.image ? (
        <img className="fxt-result-media" src={mediaSrc(made.image)} alt={`${effect.label} result`} />
      ) : null}
      <div className="fxt-result-acts">
        {bundle && bundle.id !== effect.id && self ? (
          <button type="button" className="fxt-btn primary" disabled={!!proWhy} title={proWhy || "Opens the bundle's card with its price. Nothing runs until you approve."} onClick={() => onMakeItPro([self])}>
            <Sparkles strokeWidth={1.8} /> Make It Pro
          </button>
        ) : null}
        {id !== null ? <ShareControls key={id} id={id} /> : null}
        {id !== null ? (
          <a className="fxt-btn" href={renderDownloadHref(id)} download title="Save the file">
            <Download strokeWidth={1.8} /> {compact ? "" : "Download"}
          </a>
        ) : null}
        {toVesper ? (
          <Link className="fxt-btn" href={toVesper} title="Opens Create with this result attached">
            <Wand2 strokeWidth={1.8} /> Turn this into a full piece with Vesper
          </Link>
        ) : null}
      </div>
    </div>
  );
}
