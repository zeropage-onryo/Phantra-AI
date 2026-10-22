"use client";

/* The Create page v2's sections (2026-10-22, docs/tasks/task-create-page-v2.md):
   everything under the composer when `create_v2` is on, top to bottom in
   lib/create-v2 SECTIONS. The composer itself is unchanged and sits above;
   this component only FILLS its box (`onFill`), opens the effects door or
   links elsewhere. It never sends and nothing here is priced.

   Reads, all free: the showcase manifest (lib/showcase), the project's kit
   (GET /api/projects/{id}/brand-kit, for the badge), the account's projects
   and renders (the lists Projects and the Library already read), the week
   (GET /api/trending) and the effects table the gallery already holds. */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Film } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { getMedia, getProjectKit, listProjects, type EffectsCatalogue, type MediaItem, type Project } from "@/lib/studio-api";
import type { Candidate, Effect } from "@/lib/effects";
import { loadShowcase, PLACEHOLDER, type ShowcaseManifest } from "@/lib/showcase";
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
  NEW_TILES,
  personalRow,
  trendCards,
  USE_CASE_TABS,
  type Capabilities,
  type InputChip,
  type KitPalette,
  type MadeCard,
  type TrendingWeek,
  type UseCaseTab,
} from "@/lib/create-v2";
import {
  ChipButton,
  ContinueCardView,
  EffectCardView,
  FoundingBannerView,
  LookCardView,
  MadeCardView,
  NewTileView,
  PersonalCardView,
  ShowcaseCard,
  TrendCardView,
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
};

/** The whole v2 block, or nothing: the page's one branch on the flag. */
export function CreateV2(props: CreateV2Props) {
  if (!createV2On(props.caps)) return null;
  return <CreateV2Sections {...props} />;
}

function Row({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="cv2-row" role="list" aria-label={label}>
      {children}
    </div>
  );
}

function CreateV2Sections({ caps, projectId, fx, onFill, onFocus, onAttach, onEffects, onRemixImage }: CreateV2Props) {
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
  const [slide, setSlide] = useState(0);

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

  const chip = (c: InputChip) => {
    if (c.action === "focus") onFocus();
    else if (c.action === "fill") onFill(c.fill ?? "");
    else if (c.action === "attach") onAttach();
    else if (door === "gallery") openEffects("finish");
  };

  const continueRow = useMemo(() => continueCards(projects, media), [projects, media]);
  const personal = useMemo(() => personalRow(projects), [projects]);
  const trends = useMemo(() => trendCards(week), [week]);
  const made = useMemo(() => madeFeed(media), [media]);
  const liveEffects: Effect[] = fx?.ready ? fx.items.slice(0, 6) : [];
  const tabs = USE_CASE_TABS.find((t) => t.id === tab) ?? USE_CASE_TABS[0];

  const remix = (card: MadeCard) => {
    if (card.kind === "video") onEffects([{ ref: `gen:${card.id}`, kind: "clip", thumb: card.thumb ?? undefined, from: "the render you picked to remix" }], "finish");
    else onRemixImage(card.url, card.prompt);
  };

  return (
    <div className="cv2" data-create-v2>
      {/* 1. beside the Vesper bar: what to start from, and where a clip goes */}
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

      {/* 2. returning users only */}
      {continueRow.length ? (
        <section className="cv2-section" data-section="continue">
          <h2>Continue where you left off</h2>
          <Row label="Continue">
            {continueRow.map((c) => (
              <ContinueCardView key={c.id} card={c} kit={kit} />
            ))}
          </Row>
        </section>
      ) : null}

      {/* 3. launch carousel, live features only */}
      <section className="cv2-section" data-section="launch">
        <div className="cv2-head">
          <h2>What Phantra does</h2>
          <span className="cv2-arrows">
            <button type="button" aria-label="Previous" onClick={() => setSlide((s) => (s + LAUNCH_SLIDES.length - 1) % LAUNCH_SLIDES.length)}>
              <ChevronLeft strokeWidth={2} />
            </button>
            <button type="button" aria-label="Next" onClick={() => setSlide((s) => (s + 1) % LAUNCH_SLIDES.length)}>
              <ChevronRight strokeWidth={2} />
            </button>
          </span>
        </div>
        <div className="cv2-carousel" style={{ transform: `translateX(-${slide * 100}%)` }}>
          {LAUNCH_SLIDES.map((s) => (
            <ShowcaseCard
              key={s.id}
              title={s.title}
              line={s.line}
              item={item(s.showcase)}
              kit={kit}
              eyebrow="Live now"
              onPick={() => (s.href === "effects" ? (door === "tab" ? router.push(EFFECTS_TAB_HREF) : openEffects("finish")) : onFill(s.fill ?? ""))}
            />
          ))}
        </div>
      </section>

      {/* 4. use-case tabs: a card fills the box with a brief */}
      <section className="cv2-section" data-section="usecases">
        <div className="cv2-head">
          <h2>Start from a use case</h2>
          <div className="cv2-tabs" role="tablist">
            {USE_CASE_TABS.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={t.id === tab} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <Row label={tabs.label}>
          {tabs.cards.map((c) => (
            <UseCaseCard key={c.id} card={c} item={item(c.showcase)} kit={kit} onPick={(card) => onFill(card.brief)} />
          ))}
        </Row>
      </section>

      {/* 5. trending this week: this account's own week */}
      <section className="cv2-section" data-section="trending">
        <div className="cv2-head">
          <h2>Trending this week</h2>
          <span className="cv2-note">in your studio, last {week?.days ?? 7} days</span>
        </div>
        {trends.length ? (
          <Row label="Trending">
            {trends.map((t) => (
              <TrendCardView key={t.id} card={t} kit={kit} onPick={(card) => (card.kind === "brief" ? onFill(card.brief ?? "") : openEffects())} />
            ))}
          </Row>
        ) : (
          <p className="cv2-empty">Nothing yet this week. Run an effect or write a scene and it shows here.</p>
        )}
      </section>

      {/* 6. personalized: from the account's own projects */}
      {personal ? (
        <section className="cv2-section" data-section="personal">
          <h2>{personal.because}</h2>
          <Row label="For you">
            {personal.cards.map((c) => (
              <PersonalCardView key={c.id} card={c} kit={kit} onPick={(card) => onFill(card.brief)} />
            ))}
          </Row>
        </section>
      ) : null}

      {/* 7. the effects strip: free looks, then the live table */}
      <section className="cv2-section" data-section="effects">
        <div className="cv2-head">
          <h2>Effects</h2>
          {door === "tab" ? (
            <Link className="cv2-more" href={EFFECTS_TAB_HREF}>
              All effects
            </Link>
          ) : (
            <button type="button" className="cv2-more" onClick={() => openEffects()}>
              All effects
            </button>
          )}
        </div>
        <Row label="Effects">
          {LOOKS.map((l) => (
            <LookCardView
              key={l.id}
              look={l}
              item={item(l.showcase)}
              kit={kit}
              onPick={(look) => (door === "tab" ? router.push(`${EFFECTS_TAB_HREF}?look=${look.id}`) : openEffects(look.tab))}
            />
          ))}
          {liveEffects.map((e) => (
            <EffectCardView key={e.id} effect={e} kit={kit} onPick={(effect) => openEffects(effect.category)} />
          ))}
        </Row>
      </section>

      {/* 8. new at Phantra */}
      <section className="cv2-section" data-section="new">
        <h2>New at Phantra</h2>
        <Row label="New">
          {NEW_TILES.map((t) => (
            <NewTileView key={t.id} tile={t} item={t.showcase ? item(t.showcase) : null} kit={kit} />
          ))}
        </Row>
      </section>

      {/* 9. one Founding 500 banner */}
      <section className="cv2-section" data-section="founding">
        <FoundingBannerView kit={kit} />
      </section>

      {/* 10. made in Phantra, with Remix */}
      <section className="cv2-section" data-section="made">
        <div className="cv2-head">
          <h2>Made in Phantra</h2>
          <Link className="cv2-more" href="/studio/assets">
            Library
          </Link>
        </div>
        {made.length ? (
          <Row label="Made in Phantra">
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
