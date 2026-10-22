"use client";

/* The Create home as a front page (2026-10-22, Mike's pick: board 66 with
   the type of 68 on the "Phantra Create Page Redesign" canvas;
   docs/tasks/task-create-front-page.md). Four pieces, all drawn by
   app/studio/(create)/create-view.tsx around its one composer:

   - FrontBackdrop: renders behind the box, fading into the page;
   - FrontPeek: the tab tucked behind the box's top edge, rotating the
     entries marked `peek` (Kling 4.0 first);
   - FrontTray: hangs off the box's bottom edge, the person's own work by
     stage; a stage is a filter for the wall;
   - FrontWall: the chips and the wall of news in five sizes, each tile the
     whole click.

   Nothing here spends or sends: a tile fills the box, opens a page, the
   effects or the talking-photo card. Reads, all free: the news file
   (src/content/news.json), the showcase manifest, the Library's rows and
   the scenes a render is waiting on (the lists the Library and Renders
   already read). */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import newsFile from "@/content/news.json";
import { RefImg, heroOf } from "@/components/studio/concept-card";
import { getMedia, rendersUnfinished, sceneHref, type Concept, type MediaItem } from "@/lib/studio-api";
import type { Candidate } from "@/lib/effects";
import { loadShowcase, PLACEHOLDER, type ShowcaseItem, type ShowcaseManifest } from "@/lib/showcase";
import { effectsDoor, EFFECTS_TAB_HREF, LOOKS, USE_CASE_TABS, type Capabilities } from "@/lib/create-v2";
import {
  countLabel,
  FILTERS,
  hasWork,
  isFinalCut,
  liveNews,
  peekItems,
  plays,
  readNews,
  splitAccent,
  TAG,
  trayStages,
  wallTiles,
  whenLabel,
  type FrontFilter,
  type MadeTile,
  type NewsAction,
  type NewsItem,
  type NewsSize,
  type Stage,
  type StageId,
} from "@/lib/front-page";
import "./front.css";

/* eslint-disable @next/next/no-img-element -- the showcase's and the Library's own R2 media, already sized (480px thumbs, posters), drawn by CSS */

const NEWS = readNews(newsFile);
/* the renders between the news: every use case's showcase still, its brief the fill */
const MADE: MadeTile[] = USE_CASE_TABS.flatMap((t) => t.cards).map((c) => ({ id: c.id, title: c.title, brief: c.brief, media: c.showcase }));
/* behind the box: the free looks' frames and the first use cases */
const BACKDROP = [...LOOKS.map((l) => l.showcase), ...MADE.slice(0, 8).map((m) => m.media)];

export type Front = {
  on: boolean;
  news: NewsItem[];
  manifest: ShowcaseManifest | null;
  renders: MediaItem[];
  scenes: Concept[];
  stages: Stage[];
  filter: FrontFilter;
  setFilter: (f: FrontFilter) => void;
  stage: StageId | null;
  setStage: (s: StageId | null) => void;
};

/** The page's state, read once the home is the front page. */
export function useFront(on: boolean, caps: Capabilities): Front {
  const [manifest, setManifest] = useState<ShowcaseManifest | null>(null);
  const [wall, setWall] = useState<{ items: MediaItem[]; totals: { image: number; video: number } | null }>({ items: [], totals: null });
  const [scenes, setScenes] = useState<Concept[]>([]);
  const [filter, setFilter] = useState<FrontFilter>("all");
  const [stage, setStageRaw] = useState<StageId | null>(null);

  useEffect(() => {
    if (!on) return;
    let live = true;
    loadShowcase().then((m) => live && setManifest(m));
    getMedia()
      .then((r) => live && setWall({ items: r.items, totals: r.wall ? { image: r.wall.image, video: r.wall.video } : null }))
      .catch(() => live && setWall({ items: [], totals: null }));
    rendersUnfinished()
      .then((r) => live && setScenes(r.items))
      .catch(() => live && setScenes([]));
    return () => {
      live = false;
    };
  }, [on]);

  const news = useMemo(() => liveNews(NEWS, caps), [caps]);
  const stages = useMemo(
    () =>
      trayStages(
        scenes.map((c) => heroOf(c).url),
        wall.items.map((m) => ({ kind: m.kind, model: m.model, thumb: m.thumb, poster: m.poster, url: m.url })),
        wall.totals,
      ),
    [scenes, wall],
  );
  // a stage and a chip are one choice: picking one clears the other
  const setStage = (s: StageId | null) => {
    setStageRaw(s);
    if (s) setFilter("all");
  };
  const pickFilter = (f: FrontFilter) => {
    setFilter(f);
    setStageRaw(null);
  };
  return { on, news, manifest, renders: wall.items, scenes, stages, filter, setFilter: pickFilter, stage, setStage };
}

/* ── what a click does ── */
export type FrontDoors = {
  caps: Capabilities;
  /** put text in the box and focus it; never sends */
  onFill: (text: string) => void;
  onTalk: () => void;
  /** the composer's effects gallery, plainly or on one result, on a tab */
  onEffects: (on?: Candidate[] | null, tab?: string) => void;
  /** Remix a still: attach it and fill the box */
  onRemixImage: (url: string, prompt: string) => void;
};

function useAct({ caps, onFill, onTalk, onEffects }: FrontDoors) {
  const router = useRouter();
  const door = effectsDoor(caps);
  return (a: NewsAction) => {
    if ("fill" in a) onFill(a.fill);
    else if ("href" in a) router.push(a.href);
    else if ("talk" in a) onTalk();
    else if ("look" in a) {
      const look = LOOKS.find((l) => l.id === a.look);
      if (door === "tab") router.push(`${EFFECTS_TAB_HREF}?look=${a.look}`);
      else onEffects(null, look?.tab ?? "finish");
    } else if (door === "tab") router.push(EFFECTS_TAB_HREF);
    else onEffects(null, a.effect);
  };
}

const itemOf = (manifest: ShowcaseManifest | null, key: string): ShowcaseItem => manifest?.items[key] ?? PLACEHOLDER;
const stillOf = (s: ShowcaseItem) => (s.kind === "clip" ? s.poster || s.after : s.after);

/** The headline, its accent in the tag's colour. */
function Headline({ item }: { item: NewsItem }) {
  const [before, accent, after] = splitAccent(item.title, item.accent);
  return (
    <b className="ft-h">
      {before}
      {accent ? <em>{accent}</em> : null}
      {after}
    </b>
  );
}

/* ── behind the box ── */
export function FrontBackdrop({ front }: { front: Front }) {
  if (!front.on) return null;
  return (
    <div className="cf-backdrop" aria-hidden>
      <div className="cf-bd-grid">
        {BACKDROP.map((key, i) => {
          const s = itemOf(front.manifest, key);
          return <img key={`${key}-${i}`} src={stillOf(s)} alt="" loading={i < 7 ? "eager" : "lazy"} />;
        })}
      </div>
      <span className="cf-bd-shade" />
    </div>
  );
}

/* ── the peek tab behind the box's top edge ── */
export function FrontPeek({ front, doors }: { front: Front; doors: FrontDoors }) {
  const act = useAct(doors);
  const items = peekItems(front.news);
  const [at, setAt] = useState(0);
  const [held, setHeld] = useState(false);
  useEffect(() => {
    if (items.length < 2 || held) return;
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const t = window.setInterval(() => setAt((n) => (n + 1) % items.length), 6000);
    return () => window.clearInterval(t);
  }, [items.length, held]);
  if (!front.on || !items.length) return null;
  const item = items[at % items.length];
  const s = itemOf(front.manifest, item.media);
  return (
    <div className="cf-peek" onMouseEnter={() => setHeld(true)} onMouseLeave={() => setHeld(false)} onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}>
      <button type="button" className="cf-peek-go" onClick={() => act(item.action)} aria-label={`${item.title}: ${item.line}`}>
        <img src={stillOf(s)} alt="" />
        <span className={`ft-tag t-${item.type}`}>{TAG[item.type]}</span>
        <span className="cf-peek-words">
          <b>{item.title}</b>
          <span>{item.line}</span>
        </span>
        <span className="cf-peek-try">Try it →</span>
      </button>
      {items.length > 1 ? (
        <span className="cf-peek-dots" role="group" aria-label="Featured">
          {items.map((p, i) => (
            <button key={p.id} type="button" aria-label={p.title} aria-pressed={i === at % items.length} onClick={() => setAt(i)} />
          ))}
        </span>
      ) : null}
    </div>
  );
}

/* ── the tray off the box's bottom edge ── */
export function FrontTray({ front }: { front: Front }) {
  if (!front.on || !hasWork(front.stages)) return null;
  return (
    <div className="cf-tray" role="group" aria-label="Your work">
      {front.stages.map((s) => (
        <button
          key={s.id}
          type="button"
          className={`cf-stage${s.hot ? " hot" : ""}`}
          aria-pressed={front.stage === s.id}
          disabled={!s.count}
          onClick={() => front.setStage(front.stage === s.id ? null : s.id)}
        >
          <span className="cf-stage-pics" aria-hidden>
            {s.thumbs.map((u) => (
              <RefImg key={u} url={u} thumb alt="" />
            ))}
          </span>
          <span className="cf-stage-name">{s.label}</span>
          <b>{countLabel(s.count)}</b>
        </button>
      ))}
    </div>
  );
}

/* ── one tile ── */
function Media({ s, size, autoplay }: { s: ShowcaseItem; size: NewsSize; autoplay: boolean }) {
  const ref = useRef<HTMLVideoElement>(null);
  const clip = s.kind === "clip";
  useEffect(() => {
    const v = ref.current;
    if (!v || !autoplay) return;
    const calm = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const big = window.matchMedia?.("(min-width: 760px)").matches;
    if (!calm && big) void v.play().catch(() => {});
  }, [autoplay]);
  if (!clip) return <img src={s.after} alt="" loading="lazy" />;
  return (
    <video
      ref={ref}
      // a clip with no poster shows its own first frame (the #t asks every browser for one)
      src={s.poster ? s.after : `${s.after}#t=0.1`}
      poster={s.poster ?? undefined}
      muted
      loop
      playsInline
      preload={plays(size) ? "auto" : s.poster ? "none" : "metadata"}
      data-hover={autoplay ? undefined : "1"}
    />
  );
}

/* the hover plays a clip that does not play on its own, and rests it after */
const hoverOn = (e: React.MouseEvent<HTMLElement>) => {
  const v = e.currentTarget.querySelector<HTMLVideoElement>("video[data-hover]");
  if (v) void v.play().catch(() => {});
};
const hoverOff = (e: React.MouseEvent<HTMLElement>) => {
  const v = e.currentTarget.querySelector<HTMLVideoElement>("video[data-hover]");
  if (v) {
    v.pause();
    v.currentTime = 0;
  }
};

function NewsTile({ item, s, onPick, now }: { item: NewsItem; s: ShowcaseItem; onPick: () => void; now: Date }) {
  const when = whenLabel(item.date, now);
  return (
    <button type="button" className={`ft ft-${item.size} ft-news t-${item.type}`} onClick={onPick} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
      <Media s={s} size={item.size} autoplay={plays(item.size)} />
      <span className="ft-shade" aria-hidden />
      <span className={`ft-tag t-${item.type}`}>{TAG[item.type]}</span>
      {s.kind === "clip" ? (
        <span className="ft-play" aria-label="Video">
          ▶
        </span>
      ) : null}
      <span className="ft-words">
        <Headline item={item} />
        {item.line ? <span className="ft-line">{item.line}</span> : null}
        {when ? <span className="ft-when">{when}</span> : null}
      </span>
    </button>
  );
}

function MadeTileView({ made, s, size, onPick }: { made: MadeTile; s: ShowcaseItem; size: NewsSize; onPick: () => void }) {
  return (
    <button type="button" className={`ft ft-${size} ft-made`} onClick={onPick} onMouseEnter={hoverOn} onMouseLeave={hoverOff} aria-label={`${made.title}: start from this`}>
      <Media s={s} size={size} autoplay={false} />
      <span className="ft-made-name" aria-hidden>
        {made.title}
      </span>
    </button>
  );
}

const OWN_SIZES: NewsSize[] = ["medium", "slim", "small", "tall", "small", "medium", "small", "slim"];

/** The person's own work for a stage: a scene opens its page, a still is
 *  remixed in the box, a clip opens the effects on it. */
function OwnWall({ front, stage, doors }: { front: Front; stage: StageId; doors: FrontDoors }) {
  if (stage === "scenes") {
    return (
      <>
        {front.scenes.map((c, i) => (
          <Link key={c.id} href={sceneHref(c.id)} className={`ft ft-${OWN_SIZES[i % OWN_SIZES.length]} ft-own`}>
            <RefImg url={heroOf(c).url} alt="" />
            <span className="ft-shade" aria-hidden />
            <span className="ft-words">
              <b className="ft-h ft-h-own">{c.title || "Untitled scene"}</b>
              <span className="ft-line">{c.blocked ? "Needs a photo" : "Ready to render"}</span>
            </span>
          </Link>
        ))}
      </>
    );
  }
  const rows = front.renders.filter((m) =>
    stage === "stills" ? m.kind === "image" : stage === "cuts" ? isFinalCut(m) : m.kind === "video" && !isFinalCut(m),
  );
  return (
    <>
      {rows.slice(0, 48).map((m, i) => {
        const size = OWN_SIZES[i % OWN_SIZES.length];
        const pick = () =>
          m.kind === "image"
            ? doors.onRemixImage(m.url, m.prompt ?? "")
            : m.generated_id
              ? doors.onEffects([{ ref: `gen:${m.generated_id}`, kind: "clip", thumb: m.poster ?? undefined, from: "the clip you picked" }], "finish")
              : undefined;
        return (
          <button key={m.asset_id} type="button" className={`ft ft-${size} ft-own`} onClick={pick} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
            {m.kind === "video" ? (
              <video src={m.url} poster={m.poster ?? undefined} muted loop playsInline preload="none" data-hover="1" />
            ) : (
              <img src={m.thumb || m.url} alt="" loading="lazy" />
            )}
            <span className="ft-shade" aria-hidden />
            <span className="ft-words">
              <span className="ft-line">{m.model_label || (m.kind === "image" ? "Still" : "Clip")}</span>
            </span>
          </button>
        );
      })}
    </>
  );
}

/* ── the chips and the wall ── */
export function FrontWall({ front, doors }: { front: Front; doors: FrontDoors }) {
  const act = useAct(doors);
  const [now] = useState(() => new Date());
  if (!front.on) return null;
  const tiles = wallTiles(front.filter, front.news, MADE);
  const stage = front.stage ? front.stages.find((s) => s.id === front.stage) : null;
  return (
    <section className="cf-wall" data-section="front" aria-label="What's new">
      <div className="cf-chips" role="group" aria-label="Show">
        {FILTERS.map((f) => (
          <button key={f.id} type="button" aria-pressed={!stage && front.filter === f.id} onClick={() => front.setFilter(f.id)}>
            {f.label}
          </button>
        ))}
      </div>
      {stage ? (
        <p className="cf-showing">
          Your {stage.label.toLowerCase()} · {countLabel(stage.count)}
          <button type="button" onClick={() => front.setStage(null)}>
            Back to the news ×
          </button>
        </p>
      ) : null}
      <div className="cf-grid">
        {stage ? (
          <OwnWall front={front} stage={stage.id} doors={doors} />
        ) : (
          tiles.map((t) =>
            t.kind === "news" ? (
              <NewsTile key={t.key} item={t.item} s={itemOf(front.manifest, t.item.media)} onPick={() => act(t.item.action)} now={now} />
            ) : (
              <MadeTileView key={t.key} made={t.made} s={itemOf(front.manifest, t.made.media)} size={t.size} onPick={() => doors.onFill(t.made.brief)} />
            ),
          )
        )}
      </div>
    </section>
  );
}
