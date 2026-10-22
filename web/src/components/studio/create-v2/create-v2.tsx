"use client";

/* The Create page's sections (2026-10-22, docs/tasks/task-create-page-v2.md):
   everything under the composer on the Create HOME (/studio) when
   `create_v2` is on, top to bottom in lib/create-v2 SECTIONS. The composer
   itself sits above; this component only FILLS its box (`onFill`), opens a
   door (effects, the talking-photo card) or links elsewhere. It never sends
   and nothing here is priced.

   THE RUNWAY / HIGGSFIELD PASS (2026-10-22, Mike's pick on the "Phantra
   Create Page Redesign" canvas): full width instead of a 1180px column, and
   a hierarchy -- the highlights row (Higgsfield's top row), ONE promo banner
   in the studio's yellow beside six tool tiles (Higgsfield's middle row),
   the use cases as a rail of picture cards under tabs (Runway's top), the
   person's own work as one row, the effects as portrait tiles with their
   names under them (the week's most-run one wears POPULAR: the old text-only
   Trending row printed the table's raw ids), and Made in Phantra. The rows
   scroll with Embla and arrow buttons, never a browser scrollbar. With a
   conversation open none of this shows: the chat has its own page,
   /studio/chat (app/studio/(create)/create-view.tsx).

   Reads, all free: the showcase manifest (lib/showcase), the project's kit
   (GET /api/projects/{id}/brand-kit, for the badge), the account's projects
   and renders (the lists Projects and the Library already read), the week
   (GET /api/trending, for the POPULAR tag) and the effects table the gallery
   already holds. */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import useEmblaCarousel from "embla-carousel-react";
import { ArrowLeft, ArrowRight, Film } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { getMedia, getProjectKit, listProjects, type EffectsCatalogue, type MediaItem, type Project } from "@/lib/studio-api";
import type { Candidate, Effect } from "@/lib/effects";
import { loadShowcase, PLACEHOLDER, showcaseKey, type ShowcaseManifest } from "@/lib/showcase";
import {
  continueCards,
  createV2On,
  effectsDoor,
  EFFECTS_TAB_HREF,
  INPUT_CHIPS,
  kitPalette,
  LAUNCH_SLIDES,
  LOOKS,
  madeFeed,
  personalRow,
  popularEffect,
  PROMO,
  TOOL_TILES,
  USE_CASE_TABS,
  type Capabilities,
  type InputChip,
  type KitPalette,
  type MadeCard,
  type ToolTile,
  type TrendingWeek,
  type UseCaseTab,
} from "@/lib/create-v2";
import {
  ChipButton,
  ContinueCardView,
  EffectTileView,
  LookCardView,
  MadeCardView,
  PersonalCardView,
  PromoView,
  ShowcaseCard,
  ToolTileView,
  UseCaseCard,
} from "./cards";
import "./create-v2.css";

export type CreateV2Props = {
  caps: Capabilities;
  /** the project the composer writes inside, for its kit */
  projectId: number | null;
  /** the effects table the gallery holds (null until it loads) */
  fx: EffectsCatalogue | null;
  /** put text in the box and focus it; never sends */
  onFill: (text: string) => void;
  /** focus the box with what it has */
  onFocus: () => void;
  /** the composer's reference picker */
  onAttach: () => void;
  /** the composer's gallery, plainly or on one result, on a tab */
  onEffects: (on?: Candidate[] | null, tab?: string) => void;
  /** Remix a still: attach it and fill the box */
  onRemixImage: (url: string, prompt: string) => void;
  /** the talking-photo card (its Render is the one click that spends) */
  onTalk: () => void;
};

/** The whole block, or nothing: the page's one branch on the flag. */
export function CreateV2(props: CreateV2Props) {
  if (!createV2On(props.caps)) return null;
  return <CreateV2Sections {...props} />;
}

function Row({ children, label, className = "cv2-row" }: { children: ReactNode; label: string; className?: string }) {
  return (
    // a group, not a list: the cards are buttons and links, not list items
    <div className={className} role="group" aria-label={label}>
      {children}
    </div>
  );
}

/** A row that scrolls sideways (Runway's rails): Embla drags and snaps it,
 *  the arrows page it, and there is no browser scrollbar. The arrows only
 *  show while there is somewhere to go. */
function Rail({ children, label, className = "", heading }: { children: ReactNode; label: string; className?: string; heading?: ReactNode }) {
  const [ref, api] = useEmblaCarousel({ align: "start", dragFree: true, containScroll: "trimSnaps" });
  const [can, setCan] = useState({ prev: false, next: false });
  const sync = useCallback(() => {
    if (!api) return;
    setCan({ prev: api.canScrollPrev(), next: api.canScrollNext() });
  }, [api]);
  useEffect(() => {
    if (!api) return;
    // the first read on the next frame (Embla has measured by then), then on its events
    const first = requestAnimationFrame(sync);
    api.on("select", sync).on("reInit", sync).on("scroll", sync);
    return () => {
      cancelAnimationFrame(first);
      api.off("select", sync).off("reInit", sync).off("scroll", sync);
    };
  }, [api, sync]);
  return (
    <>
      {heading}
      <div className="cv2-rail-box">
        <div className="cv2-rail" ref={ref}>
          <div className={`cv2-rail-track${className ? ` ${className}` : ""}`} role="group" aria-label={label}>
            {children}
          </div>
        </div>
        {can.prev ? (
          <button type="button" className="cv2-arrow prev" aria-label={`Back: ${label}`} onClick={() => api?.scrollPrev()}>
            <ArrowLeft strokeWidth={2} />
          </button>
        ) : null}
        {can.next ? (
          <button type="button" className="cv2-arrow next" aria-label={`More: ${label}`} onClick={() => api?.scrollNext()}>
            <ArrowRight strokeWidth={2} />
          </button>
        ) : null}
      </div>
    </>
  );
}

function CreateV2Sections({ caps, projectId, fx, onFill, onFocus, onAttach, onEffects, onRemixImage, onTalk }: CreateV2Props) {
  const router = useRouter();
  const [manifest, setManifest] = useState<ShowcaseManifest | null>(null);
  // the kit of the project it was read for: a project change shows no kit
  // until its own answer lands, with no reset in an effect
  const [kitFor, setKitFor] = useState<{ projectId: number; kit: KitPalette | null } | null>(null);
  const kit = kitFor && kitFor.projectId === projectId ? kitFor.kit : null;
  const [projects, setProjects] = useState<Project[]>([]);
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [week, setWeek] = useState<TrendingWeek | null>(null);
  const [tab, setTab] = useState<UseCaseTab["id"]>("marketing");

  useEffect(() => {
    let live = true;
    loadShowcase().then((m) => live && setManifest(m));
    listProjects()
      .then((r) => live && setProjects(r.items))
      .catch(() => live && setProjects([]));
    getMedia()
      .then((r) => live && setMedia(r.items))
      .catch(() => live && setMedia([]));
    apiFetch<TrendingWeek>("/trending")
      .then((r) => live && setWeek(r))
      .catch(() => live && setWeek(null));
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (projectId === null) return;
    let live = true;
    getProjectKit(projectId)
      .then((r) => live && setKitFor({ projectId, kit: kitPalette(r.brand_kit) }))
      .catch(() => live && setKitFor({ projectId, kit: null }));
    return () => {
      live = false;
    };
  }, [projectId]);

  // a Create key ("create.hero.split", "look.noir") straight off the manifest, else the placeholder
  const item = (key: string) => manifest?.items[key] ?? PLACEHOLDER;
  const door = effectsDoor(caps);
  const openEffects = (tab?: string) => onEffects(null, tab);
  const effectsDoorOpen = () => (door === "tab" ? router.push(EFFECTS_TAB_HREF) : openEffects("finish"));

  const chip = (c: InputChip) => {
    if (c.action === "focus") onFocus();
    else if (c.action === "fill") onFill(c.fill ?? "");
    else if (c.action === "attach") onAttach();
    else if (door === "gallery") openEffects("finish");
  };

  const continueRow = useMemo(() => continueCards(projects, media), [projects, media]);
  const personal = useMemo(() => personalRow(projects, media), [projects, media]);
  const made = useMemo(() => madeFeed(media, 12), [media]);
  // the live effects the strip can SHOW: those with an example render
  const shownEffects: Effect[] = fx?.ready ? fx.items.filter((e) => !!manifest?.items[showcaseKey(e.id)] && !LOOKS.some((l) => l.id === e.id)) : [];
  const popular = popularEffect(week, [...LOOKS.map((l) => l.id), ...shownEffects.map((e) => e.id)]);
  const tabs = USE_CASE_TABS.find((t) => t.id === tab) ?? USE_CASE_TABS[0];
  // the promo only while the Kling slot is live; with none the tiles take the row
  const promo = caps.kling_4 === true ? PROMO : null;
  const pickTool = (t: ToolTile) => (t.talk ? onTalk() : t.fill ? onFill(t.fill) : undefined);

  const remix = (card: MadeCard) => {
    if (card.kind === "video") onEffects([{ ref: `gen:${card.id}`, kind: "clip", thumb: card.thumb ?? undefined, from: "the render you picked to remix" }], "finish");
    else onRemixImage(card.url, card.prompt);
  };
  const effectsMore =
    door === "tab" ? (
      <Link className="cv2-more" href={EFFECTS_TAB_HREF}>
        All effects →
      </Link>
    ) : (
      <button type="button" className="cv2-more" onClick={() => openEffects()}>
        All effects →
      </button>
    );

  return (
    <div className="cv2" data-create-v2>
      {/* 1. under the box: what to start from, and where a clip goes */}
      <section className="cv2-section cv2-vesper" data-section="vesper" aria-label="Start from">
        <div className="cv2-chips">
          {INPUT_CHIPS.map((c) => (
            <ChipButton key={c.id} chip={c} onPick={chip} />
          ))}
        </div>
        {door === "tab" ? (
          <Link className="cv2-drop" href={EFFECTS_TAB_HREF}>
            <Film strokeWidth={1.6} /> Drop a clip → Effects
          </Link>
        ) : (
          <button type="button" className="cv2-drop" onClick={() => openEffects("finish")}>
            <Film strokeWidth={1.6} /> Drop a clip → Effects
          </button>
        )}
      </section>

      {/* 2. the highlights: four wide tiles, caps titles, a clip plays on hover */}
      <section className="cv2-section" data-section="launch">
        <h2>What Phantra does</h2>
        <Row label="What Phantra does" className="cv2-grid4">
          {LAUNCH_SLIDES.map((s) => (
            <ShowcaseCard
              key={s.id}
              title={s.title}
              line={s.line}
              item={item(s.showcase)}
              kit={kit}
              onPick={() => (s.href === "effects" ? effectsDoorOpen() : onFill(s.fill ?? ""))}
            />
          ))}
        </Row>
      </section>

      {/* 3. one promo banner beside six tool tiles */}
      <section className={`cv2-section cv2-bento${promo ? "" : " no-promo"}`} data-section="promo" aria-label="New at Phantra">
        {promo ? <PromoView promo={promo} item={item(promo.showcase)} kit={kit} onPick={(p) => onFill(p.fill)} /> : null}
        <Row label="Tools" className="cv2-tools">
          {TOOL_TILES.map((t) => (
            <ToolTileView key={t.id} tile={t} kit={kit} onPick={pickTool} />
          ))}
        </Row>
      </section>

      {/* 4. use-case tabs over a rail of picture cards: a card fills the box with a brief */}
      <section className="cv2-section" data-section="usecases">
        <Rail
          label={tabs.label}
          className="cv2-strip"
          heading={
            <div className="cv2-head">
              <h2>Start from a use case</h2>
              {/* pressed buttons, not a tablist: the rail below is a group, not a tabpanel */}
              <div className="cv2-tabs" role="group" aria-label="Use case">
                {USE_CASE_TABS.map((t) => (
                  <button key={t.id} type="button" aria-pressed={t.id === tab} onClick={() => setTab(t.id)}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          }
        >
          {tabs.cards.map((c) => (
            <UseCaseCard key={c.id} card={c} item={item(c.showcase)} kit={kit} onPick={(card) => onFill(card.brief)} />
          ))}
        </Rail>
      </section>

      {/* 5. the person's own work: the project and the last render, then next things; returning users only */}
      {continueRow.length || personal ? (
        <section className="cv2-section" data-section="work">
          <div className="cv2-head">
            <h2>Pick up where you left off</h2>
            <Link className="cv2-more" href="/studio/projects">
              All projects →
            </Link>
          </div>
          <Row label="Your work" className="cv2-work">
            {continueRow.map((c) => (
              <ContinueCardView key={c.id} card={c} kit={kit} />
            ))}
            {personal?.cards.map((c) => (
              <PersonalCardView key={c.id} card={c} kit={kit} onPick={(card) => onFill(card.brief)} />
            ))}
          </Row>
        </section>
      ) : null}

      {/* 6. effects: the free looks, then the live effects that have an example */}
      <section className="cv2-section" data-section="effects">
        <Rail
          label="Effects"
          className="cv2-strip cv2-strip-tall"
          heading={
            <div className="cv2-head">
              <h2>
                Effects <span className="cv2-note">Drop a clip on one</span>
              </h2>
              {effectsMore}
            </div>
          }
        >
          {LOOKS.map((l) => (
            <LookCardView
              key={l.id}
              look={l}
              item={item(l.showcase)}
              kit={kit}
              tag={l.id === popular ? "POPULAR" : "FREE"}
              onPick={(look) => (door === "tab" ? router.push(`${EFFECTS_TAB_HREF}?look=${look.id}`) : openEffects(look.tab))}
            />
          ))}
          {shownEffects.map((e) => (
            <EffectTileView
              key={e.id}
              effect={e}
              item={item(showcaseKey(e.id))}
              kit={kit}
              tag={e.id === popular ? "POPULAR" : e.free ? "FREE" : null}
              onPick={(effect) => openEffects(effect.category)}
            />
          ))}
        </Rail>
      </section>

      {/* 7. made in Phantra, with Remix */}
      <section className="cv2-section" data-section="made">
        <div className="cv2-head">
          <h2>Made in Phantra</h2>
          <Link className="cv2-more" href="/studio/assets">
            Your Library →
          </Link>
        </div>
        {made.length ? (
          <Row label="Made in Phantra" className="cv2-made-grid">
            {made.map((m) => (
              <MadeCardView key={m.id} card={m} kit={kit} onRemix={remix} />
            ))}
          </Row>
        ) : (
          <p className="cv2-empty">Your renders land here, each with a Remix.</p>
        )}
      </section>
    </div>
  );
}
