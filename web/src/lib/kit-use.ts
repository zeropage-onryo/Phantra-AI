/* "Use kit" (2026-10-22, Mike: "can we add something like this to the brand
   kit section?" -- a Use Kit menu like Higgsfield's). Every item is a LINK
   into Create with the kit switched on for that conversation (`?kit=<id>`,
   the same pick as the composer's "Kit: ▾" picker outside a project), and
   at most a first line typed into the box. Nothing here sends, makes or
   spends: the send is still the person's, and its price is on the card. */

export type KitUse = {
  id: string;
  label: string;
  note: string;
  href: string;
};

type KitLike = { id: number; name: string };

/** /studio with the kit on, an output, a starting line and a frame. */
export function kitHref(
  kit: KitLike,
  opts: { kind?: "image" | "video"; spark?: string; frame?: string } = {},
): string {
  const q = new URLSearchParams({ kit: String(kit.id) });
  if (opts.kind) q.set("kind", opts.kind);
  if (opts.spark) q.set("spark", opts.spark);
  if (opts.frame) q.set("frame", opts.frame);
  return `/studio?${q}`;
}

/** The starters: a line typed into the box for the person to finish. */
export function kitStarters(kit: KitLike): KitUse[] {
  const n = kit.name.trim() || "this brand";
  return [
    {
      id: "ad",
      label: "Product ad",
      note: "a short video ad, written in the kit's voice",
      href: kitHref(kit, { kind: "video", spark: `A 15-second ad for ${n}: ` }),
    },
    {
      id: "social",
      label: "Social post",
      note: "a 4:5 still for the feed, in the kit's look",
      href: kitHref(kit, { kind: "image", frame: "4:5", spark: `A ${n} social post image: ` }),
    },
    {
      id: "hero",
      label: "Hero image",
      note: "a wide 16:9 still for a site or a banner",
      href: kitHref(kit, { kind: "image", frame: "16:9", spark: `A ${n} hero image: ` }),
    },
  ];
}

/** The plain doors: Vesper, or an empty box on Image or Video. */
export function kitDoors(kit: KitLike): KitUse[] {
  return [
    { id: "agent", label: "Ask Vesper", note: "talk it through; Vesper works from the kit", href: kitHref(kit) },
    { id: "image", label: "Create image", note: "an empty box on Image, kit on", href: kitHref(kit, { kind: "image" }) },
    { id: "video", label: "Create video", note: "an empty box on Video, kit on", href: kitHref(kit, { kind: "video" }) },
  ];
}

/** The kit a Create link asks for, or 0. */
export function kitParam(params: { get(name: string): string | null }): number {
  const n = Number(params.get("kit"));
  return Number.isInteger(n) && n > 0 ? n : 0;
}
