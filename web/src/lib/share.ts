/* A shared render's public page (/v/<token>; src/shares.py, 2026-10-20).

   The page and its share card read the API's public route on the SERVER
   (API_UPSTREAM, the same upstream the rewrites proxy to), never from the
   browser: the token is the address, and nothing else about the share is
   needed to draw it. Only what the owner agreed is public comes back -- the
   media, its poster and the workspace's name; never the prompt or a price. */
export type PublicShare = {
  kind: "video" | "image";
  /** a playable address minted on read: absolute on the bucket, else a
   *  /renders path this site proxies */
  url: string;
  poster: string | null;
  creator: string;
  shared_at: string;
};

const UPSTREAM = () => (process.env.API_UPSTREAM || "http://localhost:8000").replace(/\/+$/, "");

/** The share, or null for an unknown, revoked or deleted one (or an API that
 *  did not answer: the page is then its 404, never a broken player). */
export async function readShare(token: string): Promise<PublicShare | null> {
  if (!/^[A-Za-z0-9_-]{8,64}$/.test(token)) return null;
  try {
    const res = await fetch(`${UPSTREAM()}/public/share/${encodeURIComponent(token)}`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = (await res.json()) as PublicShare;
    return body && typeof body.url === "string" ? body : null;
  } catch {
    return null;
  }
}

/** "Made by Maya's Studio with Phantra", or without a name when there is none. */
export const madeBy = (s: Pick<PublicShare, "creator">) =>
  s.creator.trim() ? `Made by ${s.creator.trim()} with Phantra` : "Made with Phantra";
