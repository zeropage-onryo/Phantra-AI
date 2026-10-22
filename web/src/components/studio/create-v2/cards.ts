/* The Create page v2's cards (2026-10-22, docs/tasks/task-create-page-v2.md;
   reshaped the same evening on Mike's references: Runway's "New at Runway"
   cards and Higgsfield's home tiles -- "the widgets below the create box
   ... so Phantra has visuals". Every card draws a showcase render.

   Written with createElement rather than JSX so tests/create-v2.test.mjs
   can render every card with react-dom/server under node, which only
   strips types. Each card is a pure function of its props: no hooks, no
   fetching, no "@/..." imports beyond the pure helpers.

   THE SHAPES (the Runway / Higgsfield pass, 2026-10-22, Mike's pick on the
   "Phantra Create Page Redesign" canvas):
   - a TILE: the picture with the words UNDER it (the highlights row, the
     effects strip) or OVER it, bottom-left (the use-case strip);
   - the PROMO: one big picture banner, two display lines and a yellow
     button (Higgsfield's banner);
   - a TOOL TILE: a line icon, a title, a line and a NEW / FREE tag;
   - the WORK row: the project and the last render, then "next for this
     project" cards with a faded picture behind the words.

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
  type PersonalCard,
  type Promo,
  type ToolTag,
  type ToolTile,
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

/** A word on a card's corner: NEW / FREE / POPULAR. Never a price. */
export function Tag({ tag }: { tag: string | null | undefined }) {
  if (!tag) return null;
  return h("span", { className: `cv2-tag t-${tag.toLowerCase()}` }, tag);
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
    h("span", { className: "cv2-cap" }, h("b", null, card.title)),
    h(KitBadge, { kit }),
  );
}

/* ── 5. the work row's "next for this project": the words over a faded picture ── */
export function PersonalCardView({ card, kit, onPick }: { card: PersonalCard; kit?: Kit; onPick: (card: PersonalCard) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-personal", onClick: () => onPick(card), title: card.brief, "aria-label": `${card.title}: ${card.line}` },
    card.thumb ? h("span", { className: "cv2-ghost", style: { backgroundImage: `url(${card.thumb})` }, "aria-hidden": true }) : null,
    h(Words, { eyebrow: "Next for this project", title: card.title, line: card.line }),
    h(KitBadge, { kit }),
  );
}

/* ── 7. the effects strip: a free look as a portrait tile, or a live effect off the table ── */
export function LookCardView({ look, item, kit, onPick, tag = "FREE" }: { look: LookCard; item: Item; kit?: Kit; onPick: (look: LookCard) => void; tag?: string | null }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-tile cv2-look", onClick: () => onPick(look), "aria-label": `${look.label}: ${look.line}` },
    h(Picture, { item, alt: "" }),
    h(Tag, { tag }),
    h(Words, { title: look.label, line: look.line }),
    h(KitBadge, { kit }),
  );
}

/** A live effect that has an example render (lib/showcase showcaseKey): a
 *  portrait tile like a look's, its name under it. `credits` is on the row
 *  and is NOT drawn -- the gallery's card prices it. */
export function EffectTileView({ effect, item, kit, onPick, tag }: { effect: Effect; item: Item; kit?: Kit; onPick: (effect: Effect) => void; tag?: string | null }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-tile cv2-look", onClick: () => onPick(effect), "aria-label": `${effect.label}: ${effect.blurb}` },
    h(Picture, { item, alt: "" }),
    h(Tag, { tag }),
    h(Words, { title: effect.label, line: effect.blurb }),
    h(KitBadge, { kit }),
  );
}

/* ── 3. the promo: one picture banner, the studio's yellow (Higgsfield's) ── */
export function PromoView({ promo, item, kit, onPick }: { promo: Promo; item: Item; kit?: Kit; onPick: (promo: Promo) => void }) {
  return h(
    Card,
    { kit, as: "button", className: "cv2-promo", onClick: () => onPick(promo), "aria-label": `${promo.title}: ${promo.line}` },
    h("span", { className: "cv2-promo-pic", "aria-hidden": true }, h("img", { src: item.poster ?? item.after, alt: "", loading: "lazy", decoding: "async" })),
    h(
      "span",
      { className: "cv2-promo-words" },
      h("b", null, promo.title, h("span", null, promo.subtitle)),
      h("span", { className: "cv2-line" }, promo.line),
      h("span", { className: "cv2-promo-cta" }, promo.cta),
    ),
    h(KitBadge, { kit }),
  );
}

/* ── 3. a tool tile: a line icon, a title, a line, a tag ── */
export function ToolTileView({ tile, kit, onPick }: { tile: ToolTile; kit?: Kit; onPick: (tile: ToolTile) => void }) {
  const inner = [
    h(
      "span",
      { key: "top", className: "cv2-tool-top" },
      h(
        "svg",
        { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true },
        h("path", { d: tile.icon }),
      ),
      h(Tag, { tag: tile.tag as ToolTag | undefined }),
    ),
    h(Words, { key: "words", title: tile.title, line: tile.line }),
    h(KitBadge, { key: "kit", kit }),
  ];
  // a tile that links is a link; one that fills the box or opens a card is a button
  return tile.href
    ? h(Card, { kit, as: "a", className: "cv2-tool", href: tile.href }, ...inner)
    : h(Card, { kit, as: "button", className: "cv2-tool", onClick: () => onPick(tile) }, ...inner);
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
