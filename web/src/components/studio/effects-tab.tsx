"use client";

/* The Effects page (/studio/effects), behind the `effects_tab` capability
   (the server page does the 404). Rebuilt 2026-10-26 to Mike's pick "R2·04"
   (docs/tasks/task-effects-page-r2.md): an upload panel on the left, and on
   the right a featured strip over pill tabs and a dense wall of examples.

   One table, two doors, still. The page reads the SAME listing the
   composer's `/effects` gallery reads (GET /api/effects, lib/effects.ts);
   every templated row is split into one tile per template
   (lib/effects-wall.ts) off that listing's own option values. A tile with no
   example in the showcase manifest is not on the wall (Mike, 2026-10-25); a
   search finds every tile.

   NOTHING RUNS FROM A TILE. A tile is chosen into the panel; the price is
   the server's (POST /api/effects/quote), asked again as a choice changes,
   and the panel's Approve -- showing that number -- is the one click that
   spends, through POST /api/effects/run with `expect_credits`, exactly as the
   composer's card. A finished result offers Make It Pro, Share, Download and
   a hand-off to Vesper. */
import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import Link from "next/link";
import { Check, Download, FolderOpen, Plus, Search, Sparkles, Upload, Wand2, X } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { ShareControls } from "@/components/studio/asset-viewer";
import { mediaSrc, newMadeId, type Made } from "@/lib/composer";
import { madeStatus } from "@/lib/made-state";
import { assetId } from "@/lib/continue";
import {
  begin,
  candidateOf,
  missing,
  optionLabel,
  requestOf,
  unavailable,
  valueLabel,
  type Candidate,
  type Effect,
  type EffectState,
  type OptionValue,
} from "@/lib/effects";
import { acceptsFile, fits, makeItPro, vesperHref } from "@/lib/effects-tab";
import {
  featured as pickFeatured,
  openOptions,
  readContent,
  slotLabel,
  tabsShown,
  tilesFrom,
  waiting,
  wallFor,
  type TabId,
  type Tile,
} from "@/lib/effects-wall";
import { loadShowcase, restingFrame, type ShowcaseItem, type ShowcaseManifest } from "@/lib/showcase";
import {
  announceBalanceChange,
  cutUploadMedia,
  getEffects,
  getMedia,
  quoteEffect,
  renderDownloadHref,
  runEffect,
  uploadRefs,
  waitForJob,
  type EffectsCatalogue,
  type Job,
  type MediaItem,
} from "@/lib/studio-api";
import type { Turn } from "@/lib/assistant";
import pageFile from "@/content/effects-page.json";
import "@/components/studio/asset-viewer.css";
import "@/components/studio/effects-tab.css";
/* eslint-disable @next/next/no-img-element */

const CONTENT = readContent(pageFile);

/* ── an example, playing: a clip loops muted, a still is drawn ── */
function Example({ item, alt = "" }: { item: ShowcaseItem; alt?: string }) {
  const rest = restingFrame(item);
  if (item.kind === "clip") {
    return <video src={item.after} poster={rest ?? undefined} autoPlay muted loop playsInline preload="metadata" aria-label={alt || undefined} />;
  }
  return <img src={rest ?? item.after} alt={alt} loading="lazy" />;
}

/* ── one tile on the wall ── */
function WallTile({ tile, chosen, why, onPick }: { tile: Tile; chosen: boolean; why: string; onPick: () => void }) {
  return (
    <li>
      <button
        type="button"
        className="fxw-tile"
        data-chosen={chosen ? "1" : undefined}
        data-dim={why ? "1" : undefined}
        aria-pressed={chosen}
        onClick={onPick}
        aria-label={`${tile.name}${tile.free ? " · free" : ""}${why ? ` · ${why}` : ""}`}
      >
        {tile.media ? <Example item={tile.media} /> : <span className="fxw-none">No example yet</span>}
        {tile.isNew ? <span className="fxw-tag">NEW</span> : tile.free ? <span className="fxw-tag">FREE</span> : null}
        {chosen ? (
          <span className="fxw-check" aria-hidden>
            <Check strokeWidth={3} />
          </span>
        ) : null}
        <span className="fxw-name">{tile.name}</span>
        {why ? <span className="fxw-why">{why}</span> : null}
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
  const [tab, setTab] = useState<TabId>("all");
  const [query, setQuery] = useState("");
  const [chosenKey, setChosenKey] = useState<string | null>(null);
  // what the effect works on: one source, and a second for a row that takes two
  const [source, setSource] = useState<Candidate | null>(null);
  const [second, setSecond] = useState<Candidate | null>(null);
  const [options, setOptions] = useState<Record<string, OptionValue>>({});
  const [prompt, setPrompt] = useState("");
  // the last quote, for the request it priced: a stale one is never shown
  const [quote, setQuote] = useState<{ key: string; price: { credits: number; charged: boolean } | null; problem: string } | null>(null);
  const [over, setOver] = useState(false);
  const [loading, setLoading] = useState<"" | "first" | "second">("");
  const [picker, setPicker] = useState<{ for: "first" | "second"; items: MediaItem[] } | null>(null);
  const [busy, setBusy] = useState(false);
  // the run in the panel now, and every result this visit made, newest first
  const [current, setCurrent] = useState<{ turn: Turn; effect: Effect } | null>(null);
  const [results, setResults] = useState<{ turn: Turn; effect: Effect }[]>([]);
  const file = useRef<HTMLInputElement>(null);
  const fileFor = useRef<"first" | "second">("first");
  const asked = useRef(0);
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

  const tiles = useMemo(() => tilesFrom(fx?.items ?? [], showcase, CONTENT), [fx, showcase]);
  const wall = useMemo(() => wallFor(tiles, tab, query), [tiles, tab, query]);
  const tabs = useMemo(() => tabsShown(tiles), [tiles]);
  const strip = useMemo(() => pickFeatured(tiles, CONTENT), [tiles]);
  const bundle = useMemo(() => makeItPro(fx?.items ?? []), [fx]);
  const chosen = useMemo(() => tiles.find((t) => t.key === chosenKey) ?? null, [tiles, chosenKey]);
  const effect = chosen?.effect ?? null;
  const ready = !!fx?.ready;
  const exempt = !!fx?.exempt;

  // the run's request, as the server is sent it: the tile's fixed option
  // and the person's choices on top of the row's defaults
  const state: EffectState | null = useMemo(() => {
    if (!chosen || !effect) return null;
    const on = [source, second].filter((c): c is Candidate => !!c && fits(effect, c));
    const base = begin(effect, [], "panel", { on, options: { ...options, ...(chosen.preset ? { [chosen.preset.name]: chosen.preset.value } : {}) } });
    return { ...base, prompt: effect.prompt === "none" ? "" : prompt };
  }, [chosen, effect, source, second, options, prompt]);
  const gap = effect && state ? missing(effect, state) : "Pick an effect";
  const unquotable = effect && state ? missing(effect, { ...state, prompt: "x" }) : "pick";
  const running = current?.turn.made?.status === "running";

  /* the price: the server's, asked again whenever something that moves it changes */
  const priced = state ? JSON.stringify([state.effect, state.sources.map((s) => s.ref), state.options]) : "";
  const price = quote && quote.key === priced && !unquotable ? quote.price : null;
  const problem = quote && quote.key === priced && !unquotable ? quote.problem : "";
  useEffect(() => {
    if (!state || unquotable || !ready) return;
    const mine = ++asked.current;
    const key = priced;
    const timer = setTimeout(() => {
      quoteEffect({ ...requestOf(state), prompt: effect?.prompt === "required" ? state.prompt.trim() || "x" : requestOf(state).prompt })
        .then((q) => mine === asked.current && setQuote({ key, price: { credits: q.credits, charged: q.charged }, problem: "" }))
        .catch((e) => mine === asked.current && setQuote({ key, price: null, problem: e instanceof Error ? e.message : "That cannot be priced." }));
    }, 250);
    return () => clearTimeout(timer);
    // `priced` stands for the effect, its sources and its options
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priced, unquotable, ready]);

  /* ── choosing a tile: the panel takes it; the source stays ── */
  const choose = (tile: Tile) => {
    if (running) return;
    setChosenKey(tile.key);
    setOptions({});
    setPrompt("");
    setCurrent(null);
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 900px)").matches) window.scrollTo({ top: 0, behavior: "smooth" });
  };

  /* ── the source: a dropped or chosen file, or a pick from the Library ── */
  const takeFile = useCallback(
    async (f: File, slot: "first" | "second") => {
      const kind = acceptsFile(f);
      if (!kind) {
        toast("Drop a clip (mp4, mov, webm) or a photo (jpg, png, webp)", "err");
        return;
      }
      setLoading(slot);
      try {
        let next: Candidate;
        if (kind === "clip") {
          const up = await cutUploadMedia(f);
          next = { ref: up.handle, kind: "clip", from: f.name };
        } else {
          const up = await uploadRefs([f]);
          const url = up.urls[0];
          if (!url) throw new Error("That image could not be read");
          next = { ref: url, kind: "image", thumb: url, from: f.name };
        }
        (slot === "first" ? setSource : setSecond)(next);
        setPicker(null);
      } catch (e) {
        toast(e instanceof Error ? e.message : "That could not be loaded", "err");
      } finally {
        setLoading("");
      }
    },
    [toast],
  );
  const onDrop = (e: DragEvent, slot: "first" | "second") => {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void takeFile(f, slot);
  };
  const chooseFile = (slot: "first" | "second") => {
    fileFor.current = slot;
    file.current?.click();
  };
  const openPicker = (slot: "first" | "second") => {
    if (picker?.for === slot) return setPicker(null);
    getMedia({})
      .then((w) => setPicker({ for: slot, items: w.items.filter((m) => m.generated_id) }))
      .catch(() => toast("The Library could not be read", "err"));
  };
  const pick = (m: MediaItem) => {
    const clip = m.kind === "video";
    const next: Candidate = { ref: `gen:${m.generated_id}`, kind: clip ? "clip" : "image", thumb: clip ? (m.poster ?? undefined) : (m.thumb ?? m.url), from: "your Library" };
    (picker?.for === "second" ? setSecond : setSource)(next);
    setPicker(null);
  };

  /* ── a result ── */
  const patch = (id: string, fields: Partial<Made>) => {
    const apply = (t: Turn) => (t.made?.id === id && t.made ? { ...t, made: { ...t.made, ...fields } } : t);
    setCurrent((c) => (c ? { ...c, turn: apply(c.turn) } : c));
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

  /* Approve: the one click that spends, at the price the button shows. */
  async function approve() {
    if (!state || !effect || !price || busy || running || gap) return;
    const madeId = newMadeId();
    const made: Made = { id: madeId, output: "image", refs: [], status: "running", detail: `${chosen?.name ?? state.label}…`, prompt: state.prompt, effect: state.effect, model: state.effect };
    const run = { turn: { role: "assistant" as const, content: chosen?.name ?? state.label, effect: { ...state, paid: price }, made }, effect };
    setBusy(true);
    setCurrent(run);
    setResults((all) => [run, ...all]);
    try {
      const started = await runEffect({ ...requestOf(state), expect_credits: price.credits });
      patch(madeId, { jobId: started.job_id });
      const job = await waitForJob(started.job_id, (j) => patch(madeId, { detail: j.detail || "" }));
      finish(madeId, job);
    } catch (e) {
      // refused before anything ran (a price that moved, a source that is gone)
      setResults((all) => all.filter((r) => r.turn.made?.id !== madeId));
      setCurrent(null);
      toast(e instanceof Error ? e.message : "That did not go through.", "err");
    } finally {
      setBusy(false);
    }
  }
  const makeProOn = (on: Candidate[]) => {
    if (!bundle) return;
    const tile = tiles.find((t) => t.key === bundle.id);
    if (tile) choose(tile);
    if (on[0]) setSource(on[0]);
  };

  const wants = effect ? slotLabel(effect, chosen?.preset?.name) : "Photo or clip";
  const takesTwo = !!effect && effect.sources.max > 1;
  const mismatch = effect && source && !fits(effect, source) ? (effect.takes === "video" ? "This effect works on a clip" : "This effect works on a photo") : "";
  const buttonLine = !chosen
    ? "Pick an effect"
    : !ready
      ? "Effects are not set up on this server yet"
      : gap
        ? gap.startsWith("Needs") && !source
          ? `Add a ${wants.toLowerCase()} to continue`
          : gap
        : problem
          ? problem
          : !price
            ? "Pricing…"
            : price.credits === 0 && !price.charged
              ? `Run ${chosen.name} · Free`
              : `Approve · ${price.credits.toLocaleString()} credits${price.charged && !exempt ? "" : " · not charged"}`;
  const canRun = !!chosen && ready && !gap && !!price && !busy && !running;

  const slot = (which: "first" | "second") => {
    const held = which === "first" ? source : second;
    const label = which === "first" ? wants : `Second ${wants.toLowerCase()}`;
    return (
      <div
        key={which}
        className="fxp-slot"
        data-over={over && which === "first" ? "1" : undefined}
        data-filled={held ? "1" : undefined}
        onDragOver={(e) => {
          e.preventDefault();
          if (which === "first") setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => onDrop(e, which)}
      >
        {held ? (
          held.thumb ? (
            <img src={mediaSrc(held.thumb)} alt="" className="fxp-thumb" />
          ) : (
            <span className="fxp-thumb fxp-thumb-clip">clip</span>
          )
        ) : (
          <span className="fxp-thumb fxp-thumb-empty" aria-hidden>
            {loading === which ? <span className="fxp-spin" /> : <Plus strokeWidth={1.8} />}
          </span>
        )}
        <span className="fxp-slot-words">
          <b>{label}</b>
          <span>{loading === which ? "Loading…" : held ? held.from : which === "second" ? "Optional · for effects with two people" : "Drop it here, choose a file or use your Library"}</span>
        </span>
        <span className="fxp-slot-acts">
          {held ? (
            <button type="button" className="fxp-icon" aria-label={`Remove the ${label.toLowerCase()}`} onClick={() => (which === "first" ? setSource : setSecond)(null)}>
              <X strokeWidth={2} />
            </button>
          ) : (
            <>
              <button type="button" className="fxp-icon" aria-label="Choose a file" title="Choose a file" onClick={() => chooseFile(which)} disabled={!!loading}>
                <Upload strokeWidth={1.8} />
              </button>
              <button type="button" className="fxp-icon" aria-label="Pick from the Library" title="Pick from the Library" aria-expanded={picker?.for === which} onClick={() => openPicker(which)} disabled={!!loading}>
                <FolderOpen strokeWidth={1.8} />
              </button>
            </>
          )}
        </span>
      </div>
    );
  };

  const shown = current?.turn.made && madeStatus(current.turn.made) !== "running" ? current : null;

  return (
    <section className="view fxw" style={{ paddingTop: 0 }}>
      <input
        ref={file}
        type="file"
        accept="video/*,image/*"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void takeFile(f, fileFor.current);
          e.target.value = "";
        }}
      />

      {/* ── the panel: what runs, on what, at what price ── */}
      <aside className="fxp" aria-label="Run an effect" data-idle={!chosen && !shown && !running ? "1" : undefined}>
        <div className="fxp-cover" data-result={shown ? "1" : undefined}>
          {running ? (
            <div className="fxp-running">
              <span className="fxp-spin" />
              <span>{current?.turn.made?.detail || "Working…"}</span>
            </div>
          ) : shown?.turn.made?.clip ? (
            <video src={mediaSrc(shown.turn.made.clip)} controls playsInline autoPlay muted loop />
          ) : shown?.turn.made?.image ? (
            <img src={mediaSrc(shown.turn.made.image)} alt={`${shown.effect.label} result`} />
          ) : chosen?.media ? (
            <Example item={chosen.media} />
          ) : null}
          {!running && !shown ? <span className="fxp-title">{chosen ? chosen.name : "Pick an effect"}</span> : null}
          {chosen && !running ? (
            <button
              type="button"
              className="fxp-change"
              onClick={() => {
                setChosenKey(null);
                setCurrent(null);
              }}
            >
              {shown ? "New run" : "Change"}
            </button>
          ) : null}
        </div>

        {chosen && !shown ? <small className="fxp-model">{chosen.effect.recipe ? `Phantra recipe · ${chosen.effect.made_with || chosen.effect.label}` : chosen.effect.label}{chosen.free ? " · free" : ""}</small> : null}

        {shown ? <ResultPane turn={shown.turn} effect={shown.effect} bundle={bundle} onMakeItPro={makeProOn} /> : null}

        {slot("first")}
        {mismatch ? <p className="fxp-note">{mismatch}</p> : null}
        {takesTwo ? slot("second") : null}

        {picker ? (
          <div className="fxp-pick" role="dialog" aria-label="Pick from the Library">
            <div className="fxp-pick-head">
              <b>Your Library</b>
              <button type="button" className="fxp-icon" aria-label="Close the Library" onClick={() => setPicker(null)}>
                <X strokeWidth={2} />
              </button>
            </div>
            {picker.items.length ? (
              <ul>
                {picker.items.map((m) => (
                  <li key={m.asset_id}>
                    <button type="button" onClick={() => pick(m)} title={m.prompt || m.asset_name} aria-label={`Use ${m.kind} ${m.generated_id}`}>
                      {m.kind === "video" ? (m.poster ? <img src={mediaSrc(m.poster)} alt="" loading="lazy" /> : null) : <img src={mediaSrc(m.thumb ?? m.url)} alt="" loading="lazy" />}
                      <span>{m.kind === "video" ? "clip" : "photo"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="fxp-note">Nothing in your Library yet.</p>
            )}
          </div>
        ) : null}

        {chosen && effect && effect.prompt !== "none" ? (
          <label className="fxp-field">
            <span>{effect.hint || (effect.prompt === "required" ? "Prompt" : "Prompt · optional")}</span>
            <textarea
              value={prompt}
              rows={2}
              maxLength={effect.recipe ? 200 : 2000}
              placeholder={effect.recipe ? "Leave it empty and the recipe decides" : effect.takes === "video" ? "What it should sound like…" : effect.category === "image_edit" ? "What to change…" : "Describe the scene…"}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </label>
        ) : null}

        {chosen
          ? openOptions(chosen).map(([name, o]) => {
              const value = state?.options[name];
              const few = o.values.length <= 4;
              return (
                <div key={name} className="fxp-field">
                  <span>{optionLabel(name)}</span>
                  {few ? (
                    <div className="fxp-seg" role="group" aria-label={optionLabel(name)}>
                      {o.values.map((v) => (
                        <button key={String(v)} type="button" aria-pressed={String(value) === String(v)} onClick={() => setOptions((all) => ({ ...all, [name]: v }))}>
                          {valueLabel(name, v)}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <select
                      value={value === undefined ? "" : String(value)}
                      aria-label={optionLabel(name)}
                      onChange={(e) => {
                        const v = o.values.find((x) => String(x) === e.target.value);
                        setOptions((all) => {
                          const next = { ...all };
                          if (v === undefined) delete next[name];
                          else next[name] = v;
                          return next;
                        });
                      }}
                    >
                      {o.required ? (
                        <option value="" disabled>
                          Pick one
                        </option>
                      ) : o.default === null ? (
                        <option value="">None</option>
                      ) : null}
                      {o.values.map((v) => (
                        <option key={String(v)} value={String(v)}>
                          {valueLabel(name, v)}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              );
            })
          : null}

        <span className="fxp-grow" />
        <button type="button" className="fxp-approve" disabled={!canRun} onClick={() => void approve()}>
          {running ? "Working…" : buttonLine}
        </button>
        <small className="fxp-small">{chosen && price ? "Nothing is charged if it fails." : "Browsing is free. Nothing runs until you approve."}</small>
      </aside>

      {/* ── the wall ── */}
      <div className="fxw-main">
        {strip.length && !query ? (
          <div className="fxw-strip" data-n={strip.length}>
            {strip.map((t, i) => (
              <button key={t.key} type="button" className="fxw-feature" data-big={i === 0 ? "1" : undefined} data-chosen={t.key === chosenKey ? "1" : undefined} onClick={() => choose(t)} aria-label={`${t.name}${t.free ? " · free" : ""}`}>
                {t.media ? <Example item={t.media} /> : null}
                <span className="fxw-tag">{i === 0 && t.isNew ? "NEW THIS WEEK" : t.isNew ? "NEW" : t.free ? "FREE" : "POPULAR"}</span>
                <span className="fxw-feature-name">{t.name}</span>
              </button>
            ))}
          </div>
        ) : null}

        <div className="fxw-bar">
          <div className="fxw-tabs" role="group" aria-label="Effect groups">
            {tabs.map((t) => (
              <button key={t.id} type="button" aria-pressed={tab === t.id} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <label className="fxw-search">
            <Search strokeWidth={1.8} aria-hidden />
            <input type="search" value={query} placeholder={tiles.length ? `Search ${tiles.length} effects` : "Search"} aria-label="Search effects" onChange={(e) => setQuery(e.target.value)} />
          </label>
        </div>

        {fxError ? <p className="fxw-note">{fxError}</p> : null}
        {fx && !ready ? <p className="fxw-note">Effects are not set up on this server yet. The tiles show what each one does.</p> : null}

        <ul className="fxw-grid" aria-label="Effects">
          {wall.map((t) => (
            <WallTile key={t.key} tile={t} chosen={t.key === chosenKey} why={source && !fits(t.effect, source) ? (t.effect.takes === "video" ? "Needs a clip" : "Needs a photo") : ""} onPick={() => choose(t)} />
          ))}
        </ul>
        {fx && !wall.length ? <p className="fxw-note">{query ? "No effect by that name." : "Nothing here yet."}</p> : null}
        {fx && !query && waiting(tiles) ? (
          <p className="fxw-more">
            {waiting(tiles).toLocaleString()} more effects are ready to run and land here as their examples are made. Search to use one now.
          </p>
        ) : null}

        {results.length > 1 ? (
          <>
            <h3 className="fxw-h">This visit</h3>
            <ul className="fxw-results">
              {results.slice(1).map((r) => (
                <li key={r.turn.made?.id ?? r.turn.effect?.id}>
                  <b>{r.turn.content}</b>
                  <ResultPane turn={r.turn} effect={r.effect} bundle={bundle} onMakeItPro={makeProOn} compact />
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </section>
  );
}

/* ── a result and its doors ── */
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
    return <p className="fxp-note">{!made ? "" : status === "running" ? made.detail || "Working…" : made.detail || "Not made. Nothing was charged."}</p>;
  }
  const id = assetId(made.asset);
  const self = candidateOf({ image: made.image, clip: made.clip, asset: made.asset }, "this result");
  const toVesper = vesperHref(made.asset, effect.label);
  const proWhy = bundle && self ? unavailable(bundle, [self]) : "";
  return (
    <div className="fxp-result">
      {compact ? made.clip ? <video src={mediaSrc(made.clip)} controls playsInline /> : made.image ? <img src={mediaSrc(made.image)} alt={`${effect.label} result`} /> : null : null}
      <div className="fxp-result-acts">
        {bundle && bundle.id !== effect.id && self ? (
          <button type="button" className="fxp-pill primary" disabled={!!proWhy} title={proWhy || "Puts Make It Pro in the panel with this result. Nothing runs until you approve."} onClick={() => onMakeItPro([self])}>
            <Sparkles strokeWidth={1.8} /> Make It Pro
          </button>
        ) : null}
        {id !== null ? <ShareControls key={id} id={id} /> : null}
        {id !== null ? (
          <a className="fxp-pill" href={renderDownloadHref(id)} download title="Save the file">
            <Download strokeWidth={1.8} /> Download
          </a>
        ) : null}
        {toVesper ? (
          <Link className="fxp-pill" href={toVesper} title="Opens Create with this result attached">
            <Wand2 strokeWidth={1.8} /> Make a full piece with Vesper
          </Link>
        ) : null}
      </div>
    </div>
  );
}
