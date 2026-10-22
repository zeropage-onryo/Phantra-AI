import { ImageResponse } from "next/og";
import { DEFAULT_MASCOT, mascotSrc } from "@/lib/mascot";
import { madeBy, readShare } from "@/lib/share";

/* A shared render's card (2026-10-20): its poster (or the still itself)
   beside Vesper and who made it. Drawn on request -- a share is not known
   at build time -- and a share that is gone still gets the plate. Only an
   absolute address is drawn: a /renders path is this site's proxy, which
   the image renderer cannot reach on its own. */

export const alt = "A video made with Phantra, beside Vesper, the Phantra AI agent.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const absolute = (u?: string | null) => (u && /^https:\/\//.test(u) ? u : undefined);

export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const share = await readShare(token);
  const picture = share ? absolute(share.kind === "video" ? share.poster : share.url) : undefined;
  const line = share ? madeBy(share) : "Made with Phantra";
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: "#040405", color: "#f4f3f2", fontFamily: "sans-serif" }}>
        <div style={{ width: 720, height: "100%", display: "flex", background: "#0b0b0b", borderRight: "14px solid #e4002b" }}>
          {picture ? (
            <img src={picture} width={720} height={630} style={{ objectFit: "cover" }} alt="" />
          ) : null}
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 40, gap: 24 }}>
          <img src={mascotSrc(DEFAULT_MASCOT, "made", 320)} width={260} height={260} alt="" />
          <div style={{ fontSize: 34, textAlign: "center", lineHeight: 1.2 }}>{line}</div>
          <div style={{ fontSize: 24, color: "#b3afa6" }}>phantra.ai</div>
        </div>
      </div>
    ),
    size,
  );
}
