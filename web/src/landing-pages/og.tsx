import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";
import { getMakePage, makePath, type MakePage, type MakeSection } from "./pages";

// A landing page's own share card (2026-10-11). Until today every /make and
// /models page named the home page's card, so a shared Veo link and a shared
// Ideogram link looked the same. The card is the root card's plate
// (app/opengraph-image.tsx) with the page's name, its accent and one of its
// own stills, built by the two thin files app/<section>/[slug]/opengraph-image.tsx.
//
// The still is the page's `card`, else its first still under public/ (a
// clip's poster counts). It is read off disk: every card is drawn at build
// time (the route files' generateStaticParams, with dynamicParams off), and
// that is where the stills are then. A page with no still, or a still that
// cannot be read, gets the plate alone -- a card is never worth failing a
// build over.

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_TYPE = "image/png";
/** One alt for every card: a route's `alt` export cannot read its params. */
export const OG_ALT = "A page of Phantra: its name beside a still made in the studio.";

const RED = "#e4002b";
const INK = "#0b0a08";

const MIME: Record<string, string> = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png" };

/** The still a page's card shows: a path under public/, or undefined. */
export function cardStill(page: MakePage): string | undefined {
  const tiles = [
    ...(page.heroMedia ?? []),
    ...(page.overview?.items.flatMap((item) => (item.media ? [item.media] : [])) ?? []),
    ...page.wall.tiles,
  ];
  const local = (src?: string) => (src && src.startsWith("/") && /\.(jpe?g|png)$/i.test(src) ? src : undefined);
  return local(page.card) ?? tiles.map((t) => local(t.src)).find(Boolean);
}

async function dataUrl(src: string): Promise<string | undefined> {
  const mime = MIME[src.split(".").pop()!.toLowerCase()];
  try {
    const bytes = await readFile(join(process.cwd(), "public", src));
    return `data:${mime};base64,${bytes.toString("base64")}`;
  } catch {
    return undefined;
  }
}

/** "Veo 3.1 AI Video Generator" under the h1 "Veo 3.1" reads "AI Video Generator". */
export function cardKind(page: MakePage): string {
  const rest = page.title.startsWith(page.h1) ? page.title.slice(page.h1.length).trim() : "";
  // "Text to Video AI" under "Text to Video" leaves "AI": too short to be a kind
  return rest.length >= 6 ? rest : "Phantra";
}

export async function ogCard(section: MakeSection, slug: string): Promise<ImageResponse> {
  const page = getMakePage(slug, section);
  // an unknown slug still answers with a card (the page itself is the 404)
  const name = page?.h1 ?? "Phantra";
  const kind = page ? cardKind(page) : "Phantra";
  const accent = page?.accent.primary ?? RED;
  const onAccent = page?.accent.primaryForeground ?? "#ffffff";
  const src = page ? cardStill(page) : undefined;
  const still = src ? await dataUrl(src) : undefined;
  const size = name.length <= 9 ? 132 : name.length <= 13 ? 108 : name.length <= 18 ? 84 : 68;

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: INK, color: "#fafafa", fontFamily: "sans-serif" }}>
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: 64,
            borderLeft: `14px solid ${accent}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ width: 18, height: 18, borderRadius: 9, border: `3px solid ${RED}` }} />
            <div style={{ display: "flex", fontSize: 30, fontWeight: 700, letterSpacing: 2 }}>
              PHANTRA
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <div
              style={{
                display: "flex",
                padding: "10px 18px",
                borderRadius: 6,
                background: accent,
                color: onAccent,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: 5,
                textTransform: "uppercase",
              }}
            >
              {kind}
            </div>
            <div
              style={{
                display: "flex",
                marginTop: 26,
                fontSize: size,
                fontWeight: 800,
                lineHeight: 0.95,
                letterSpacing: -2,
                textTransform: "uppercase",
              }}
            >
              {name}
            </div>
          </div>
          {/* the longest path (nano-banana's) has to fit the column on one line */}
          <div style={{ display: "flex", fontSize: 19, letterSpacing: 1, color: "#9a9a9a" }}>
            {page ? `zeropage.studio${makePath(page)}` : "zeropage.studio"}
          </div>
        </div>
        {still && (
          // eslint-disable-next-line @next/next/no-img-element -- Satori draws <img>, not next/image
          <img src={still} alt="" width={456} height={630} style={{ width: 456, height: 630, objectFit: "cover" }} />
        )}
      </div>
    ),
    OG_SIZE,
  );
}
