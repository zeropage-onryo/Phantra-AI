/* The Create page v2's cards (2026-10-22, docs/tasks/task-create-page-v2.md;
   reshaped the same evening on Mike's references: Runway's "New at Runway"
   cards and Higgsfield's home tiles -- "the widgets below the create box
   ... so Phantra has visuals". Every card draws a showcase render.

   Written with createElement rather than JSX so tests/create-v2.test.mjs
   can render every card with react-dom/server under node, which only
   strips types. Each card is a pure function of its props: no hooks, no
   fetching, no "@/..." imports beyond the pure helpers.

   THREE SHAPES:
   - a TILE: the picture with the words UNDER it (the highlights row, the
     effects strip) or OVER it, bottom-left (the use-case strip);
   - a BIG CARD: eyebrow, a display title, a line, a button, and the
     picture bleeding off the right edge (New at Phantra); a SPOTLIGHT is
     a big card with no picture and a gradient (Kling 4.0);
   - the small text cards (trending, for-you, continue, made).

   TWO RULES EVERY CARD KEEPS:
   - NO PRICE. A card never reads `credits` off anything it is handed; the
     test renders each one with a priced effect and asserts no number and
     no "credits" in the markup. The priced card before a spend still
     shows the price -- these cards only fill the box or open a door.
   - THE KIT IS SCOPED TO THE CARD. With a kit, the card's root carries the
     kit's palette roles as CSS variables (lib/create-v2 kitVars) and a
     "Kit: <name>" badge; without one it carries no kit colour at all. The
     CSS paints the kit only on the cards that make something in it (a use
     case, a brief for you, continue); a tile of a render stays a tile. */
import { createElement as h, type CSSProperties, type MouseEvent, type ReactNode } from "react";
import type { Effect } from "../../../lib/effects";
import type { ShowcaseItem as Item } from "../../../lib/showcase";
import {
  foundingLines,
  kitVars,
  type ContinueCard,
  type KitPalette,
  type LookCard,
  type MadeCard,
  type NewTile,
  type PersonalCard,
  type TrendCard,
  type UseCase,
  type InputChip,
  FOUNDING_500,
} from "../../../lib/create-v2";

type Kit = KitPalette | null | undefined;

const aspectClass = (a: Item["aspect"]) => `cv2-pic a${a.replace(":", "x")}`;

/** The card's picture: a still, or a clip that plays on hover (muted). */
export function Picture({ item, alt, className }: { item: Item; alt: string; className?: string }) {
  const cls = `${aspectClass(item.aspect)}${className ? ` ${className}` : ""}`;
  if (item.kind === "clip") {
    return h(
      "div",
      { className: cls },
      h("video", {
        src: item.after,
        poster: item.poster ?? undefined,
        muted: true,
        loop: true,
        playsInline: true,
        preload: "metadata",
        "aria-label": alt,
        onMouseEnter: (e: MouseEvent<HTMLVideoElement>) => void e.currentTarget.play().catch(() => {}),
        onMouseLeave: (e: MouseEvent<HTMLVideoElement>) => e.currentTarget.pause(),
      }),
      h("span", { className: "cv2-play", "aria-hidden": true }, "▶"),
    );
  }
  return h("div", { className: cls }, h("img", { src: item.after, alt, loading: "lazy", decoding: "async" }));
}

/** "Kit: <name>" on a card that previews in a kit's roles; nothing without one. */
export function KitBadge({ kit }: { kit: Kit }) {
  if (!kit) return null;
  return h("span", { className: "cv2-kit", title: `Previewing in ${kit.name}'s palette` }, h("span", { className: "cv2-kit-dot", "aria-hidden": true }), `Kit: ${kit.name}`);
}

/** The root every card shares: the kit's variables scoped here, and only here. */
function Card({
  kit,
  className,
  as = "div",
  children,
  ...rest
}: {
  kit: Kit;
  className?: string;
  as?: "div" | "button" | "a";
  children?: ReactNode;
  [prop: string]: unknown;
}) {
  const style = kitVars(kit) as CSSProperties;
  const cls = `cv2-card${kit ? " kit" : ""}${className ? ` ${className}` : ""}`;
  return h(as, { className: cls, style, ...(as === "button" ? { type: "button" } : {}), ...rest }, children);
}

/** The words of a tile or a big card: eyebrow, title, line. */
function Words({ eyebrow, title, line }: { eyebrow?: string; title: string; line?: string }) {
  return h(
    "span",
    { className: "cv2-body" },
    eyebrow ? h("span", { className: "cv2-eyebrow" }, eyebrow) : null,
    h("b", null, title),
    line ? h("span", { className: "cv2-line" }, line) : null,
  );
}

/* ── 1. the input chips ── */
export function ChipButton({ chip, onPick }: { chip: InputChip; onPick: (chip: InputChip) => void }) {
  return h("button", { type: "button", className: "cv2-chip", title: chip.title, onClick: () => onPick(chip) }, chip.label);
}

/* ── 2. continue where you left off ── */
export function ContinueCardView({ card, kit }: { card: ContinueCard; kit?: Kit }) {
  return h(
    Card,
    { kit, as: "a", className: "cv2-continue", href: card.href },
    card.thumb ? h("span", { className: "cv2-thumb", style: { backgroundImage: `url(${card.thumb})` } }) : h("span", { className: "cv2-thumb empty" }),
    h(Words, { eyebrow: card.kind === "project" ? "Project" : "Render", title: card.title, line: card.line }),
    h(KitBadge, { kit }),
  );
}

/* ── 3. a highlight tile: the picture, the words under it (Higgsfield's row) ── */
export function ShowcaseCard({
  title,
  line,
  item,
  kit,
  onPick,
  eyebrow,
}: {
  title: string;
  line: string;
  item: Item;
  kit?: Kit;
  onPick: () => void;
  eyebrow?: string;
}) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-tile cv2-showcase", onClick: onPick, "aria-label": `${title}: ${line}` },
    h(Picture, { item, alt: "" }),
    h(Words, { eyebrow, title, line }),
    h(KitBadge, { kit }),
  );
}

/* ── 4. a use-case tile: the words OVER the picture, bottom-left (Runway's strip) ── */
export function UseCaseCard({ card, item, kit, onPick }: { card: UseCase; item: Item; kit?: Kit; onPick: (card: UseCase) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-tile cv2-usecase", onClick: () => onPick(card), title: card.line, "aria-label": `${card.title}: ${card.line}` },
    h(Picture, { item, alt: "" }),
    h("span", { className: "cv2-cap" }, h("span", { className: "cv2-eyebrow" }, "Start with Vesper"), h("b", null, card.title)),
    h(KitBadge, { kit }),
  );
}

/* ── 5. trending ── */
export function TrendCardView({ card, kit, onPick }: { card: TrendCard; kit?: Kit; onPick: (card: TrendCard) => void }) {
  return h(
    Card,
    { kit, as: "button", className: `cv2-trend ${card.kind}`, onClick: () => onPick(card) },
    h(Words, { eyebrow: card.kind === "effect" ? "Effect" : "Brief", title: card.label, line: card.note }),
    h(KitBadge, { kit }),
  );
}

/* ── 6. personalized ── */
export function PersonalCardView({ card, kit, onPick }: { card: PersonalCard; kit?: Kit; onPick: (card: PersonalCard) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-personal", onClick: () => onPick(card), title: card.brief },
    h(Words, { title: card.title, line: card.brief.length > 110 ? `${card.brief.slice(0, 109)}…` : card.brief }),
    h(KitBadge, { kit }),
  );
}

/* ── 7. the effects strip: a free look as a portrait tile, or a live effect off the table ── */
export function LookCardView({ look, item, kit, onPick }: { look: LookCard; item: Item; kit?: Kit; onPick: (look: LookCard) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-tile cv2-look", onClick: () => onPick(look), "aria-label": `${look.label}: ${look.line}` },
    h(Picture, { item, alt: "" }),
    h(Words, { eyebrow: "Free look", title: look.label, line: look.line }),
    h(KitBadge, { kit }),
  );
}

/** A live effect (GET /api/effects): its label and blurb only. `credits`
 *  is on the row and is NOT drawn -- the gallery's card prices it. */
export function EffectCardView({ effect, kit, onPick }: { effect: Effect; kit?: Kit; onPick: (effect: Effect) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-effect", onClick: () => onPick(effect) },
    h(Words, { eyebrow: effect.output === "video" ? "Clip" : "Still", title: effect.label, line: effect.blurb }),
    h(KitBadge, { kit }),
  );
}

/* ── 8. new at Phantra: Runway's big card, or a spotlight with no picture ── */
export function NewTileView({ tile, item, kit, onPick }: { tile: NewTile; item: Item | null; kit?: Kit; onPick?: (tile: NewTile) => void }) {
  const spotlight = tile.tone === "spotlight";
  const words = h(Words, { eyebrow: tile.eyebrow ?? "New", title: tile.title, line: tile.line });
  // a tile that FILLS the box is a button on the card; a tile that links is a link
  const button = tile.fill && onPick
    ? h("button", { type: "button", className: "cv2-btn", onClick: () => onPick(tile) }, tile.cta)
    : h("a", { className: "cv2-btn", href: tile.href }, tile.cta, h("span", { "aria-hidden": true }, " ↗"));
  return h(
    Card,
    { kit, className: `cv2-big${spotlight ? " cv2-spotlight" : ""}${item ? " has-pic" : ""}` },
    words,
    button,
    item && !spotlight ? h(Picture, { item, alt: "", className: "cv2-bleed" }) : null,
    spotlight ? h("span", { className: "cv2-glow", "aria-hidden": true }) : null,
    h(KitBadge, { kit }),
  );
}

/* ── 9. the Founding 500 banner (one; its numbers are placeholders Mike edits) ── */
export function FoundingBannerView({ offer = FOUNDING_500, kit }: { offer?: typeof FOUNDING_500; kit?: Kit }) {
  const lines = foundingLines(offer);
  return h(
    Card,
    { kit, className: "cv2-founding", role: "region", "aria-label": lines.title },
    h("span", { className: "cv2-eyebrow" }, "Founding members"),
    h("b", null, lines.title),
    h("span", { className: "cv2-line" }, lines.line),
    h("a", { className: "cv2-cta", href: offer.href }, lines.cta),
    h(KitBadge, { kit }),
  );
}

/* ── 10. made in Phantra, with Remix ── */
export function MadeCardView({ card, kit, onRemix }: { card: MadeCard; kit?: Kit; onRemix: (card: MadeCard) => void }) {
  return h(
    Card,
    { kit, className: "cv2-made" },
    h(
      "a",
      { className: "cv2-pic a1x1", href: `/studio/assets?open=${card.id}`, style: card.thumb ? { backgroundImage: `url(${card.thumb})` } : undefined, "aria-label": card.prompt || "Open in the Library" },
      card.kind === "video" ? h("span", { className: "cv2-play", "aria-hidden": true }, "▶") : null,
    ),
    h(
      "span",
      { className: "cv2-body" },
      h("span", { className: "cv2-eyebrow" }, card.model || (card.kind === "video" ? "Clip" : "Still")),
      h("span", { className: "cv2-line" }, card.prompt.length > 80 ? `${card.prompt.slice(0, 79)}…` : card.prompt || "Untitled"),
    ),
    h("button", { type: "button", className: "cv2-remix", onClick: () => onRemix(card) }, "Remix this"),
    h(KitBadge, { kit }),
  );
}
