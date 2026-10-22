"use client";

/* The Create page v2's sections (2026-10-22, docs/tasks/task-create-page-v2.md):
   everything under the composer when `create_v2` is on, top to bottom in
   lib/create-v2 SECTIONS. The composer itself is unchanged and sits above;
   this component only FILLS its box (`onFill`), opens the effects door or
   links elsewhere. It never sends and nothing here is priced.

   Reshaped the same evening on Mike's references (Runway's "New at
   Runway" cards, Higgsfield's home): the sections are media now. The
   highlights are a row of four tiles with the words under the picture;
   the use cases a strip of tiles with the words over it; the looks a
   strip of portrait clips; New at Phantra big two-column cards with the
   picture bleeding off the edge and a button, Kling 4.0 first as a
   spotlight. Every picture is a showcase render (lib/showcase): the slate
   of group 12 was rendered for exactly these cards.

   Reads, all free: the showcase manifest (lib/showcase), the project's kit
   (GET /api/projects/{id}/brand-kit, for the badge), the account's projects
   and renders (the lists Projects and the Library already read), the week
   (GET /api/trending) and the effects table the gallery already holds. */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Film } from "lucide-react";
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
  type NewTile,
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

function Row({ children, label, className = "cv2-row" }: { children: React.ReactNode; label: string; className?: string }) {
  return (
    // a group, not a list: the cards are buttons and links, not list items
    <div className={className} role="group" aria-label={label}>
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
  const personal = useMemo(() => personalRow(projects), [projects]);
  const trends = useMemo(() => trendCards(week), [week]);
  const made = useMemo(() => madeFeed(media), [media]);
  const liveEffects: Effect[] = fx?.ready ? fx.items.slice(0, 6) : [];
  const tabs = USE_CASE_TABS.find((t) => t.id === tab) ?? USE_CASE_TABS[0];
  // the Kling 4.0 spotlight only while the server says the slot is ready
  const newTiles = NEW_TILES.filter((t) => t.id !== "kling4" || caps.kling_4 === true);
  const pickTile = (t: NewTile) => (t.fill ? onFill(t.fill) : undefined);

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

      {/* 3. the highlights: four tiles, the words under the picture; live features only */}
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
              eyebrow={s.eyebrow}
              onPick={() => (s.href === "effects" ? effectsDoorOpen() : onFill(s.fill ?? ""))}
            />
          ))}
        </Row>
      </section>

      {/* 4. use-case tabs over a strip of tiles: a tile fills the box with a brief */}
      <section className="cv2-section" data-section="usecases">
        <div className="cv2-head">
          <h2>Start from a use case</h2>
          {/* pressed buttons, not a tablist: the strip below is a group, not a tabpanel */}
          <div className="cv2-tabs" role="group" aria-label="Use case">
            {USE_CASE_TABS.map((t) => (
              <button key={t.id} type="button" aria-pressed={t.id === tab} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <Row label={tabs.label} className="cv2-strip">
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

      {/* 7. the effects strip: the free looks as portrait clips, then the live table */}
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
        <Row label="Effects" className="cv2-strip cv2-strip-tall">
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

      {/* 8. new at Phantra: big cards, two across */}
      <section className="cv2-section" data-section="new">
        <h2>New at Phantra</h2>
        <Row label="New" className="cv2-grid2">
          {newTiles.map((t) => (
            <NewTileView key={t.id} tile={t} item={t.showcase ? item(t.showcase) : null} kit={kit} onPick={pickTile} />
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
