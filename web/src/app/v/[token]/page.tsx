import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DEFAULT_MASCOT, mascotSrc } from "@/lib/mascot";
import { madeBy, readShare } from "@/lib/share";

/* A render its owner pressed Share on (src/shares.py, 2026-10-20): the video
   (or still), Vesper, and who made it -- nothing else. Drawn per request:
   an Unshare takes it down on the next load. Never indexed: it is a
   person's work, shared by link, not a page of ours. */

type Props = { params: Promise<{ token: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params;
  const share = await readShare(token);
  if (!share) return { title: "Not found", robots: { index: false, follow: false } };
  const line = madeBy(share);
  return {
    title: line,
    description: `${line}. Phantra is an AI studio: tell its agent, Vesper, what you are making.`,
    robots: { index: false, follow: true },
    openGraph: { type: share.kind === "video" ? "video.other" : "website", title: line, url: `/v/${token}` },
    twitter: { card: "summary_large_image", title: line },
  };
}

export default async function SharedRender({ params }: Props) {
  const { token } = await params;
  const share = await readShare(token);
  if (!share) notFound();
  const line = madeBy(share);
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#040405] px-4 py-10 text-[#f4f3f2]">
      <figure className="w-full max-w-[720px] overflow-hidden rounded-2xl border border-[#262522] bg-black">
        {share.kind === "video" ? (
          <video
            src={share.url}
            poster={share.poster ?? undefined}
            controls
            autoPlay
            muted
            loop
            playsInline
            className="block max-h-[78vh] w-full object-contain"
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- a minted, per-request address
          <img src={share.url} alt={line} className="block max-h-[78vh] w-full object-contain" />
        )}
      </figure>
      <div className="flex items-center gap-4">
        {/* eslint-disable-next-line @next/next/no-img-element -- the mascot set on R2 */}
        <img src={mascotSrc(DEFAULT_MASCOT, "made", 320)} alt="Vesper, the Phantra AI agent" width={96} height={96} className="size-24 object-contain" />
        <div className="flex flex-col gap-1">
          <p className="text-[15px] text-[#cdc9c0]">{line}</p>
          <Link href="/" className="text-[15px] font-medium text-white underline underline-offset-4 hover:text-[#ff4d6a]">
            Make your own with Vesper
          </Link>
        </div>
      </div>
    </main>
  );
}
