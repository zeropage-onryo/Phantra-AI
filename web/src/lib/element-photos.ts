/* Where to DRAW an element's photo from (2026-10-11).

   An element's `photos` are stored NAMES -- `/characters/michael/photo/
   01-headshot.jpg` -- because that is what goes on a shot: the bucket key
   carries the account and, signed, an expiry, so no fetchable URL can be
   kept on a row (src/media.py). A name is not an address. Drawing one
   means asking the API's photo route, which answers with a redirect into
   the bucket; the element panel did exactly that, the redirect pointed at
   a key the bucket no longer held, and the main picture was dead.

   The listing says where each photo is, parallel to `photos`:
   `photo_full` (the master) and `photo_thumbs` (the 480px derivative),
   both minted for the signed-in account. These helpers pick from them and
   keep the name's own route as the second try, so a listing from an older
   API, or a signed address that has expired on a page left open, still
   draws.

   No imports, on purpose: tests/element-photos.test.mjs loads this file
   with node's type stripping, where the "@/..." alias does not resolve. */

export type PhotoLists = {
  photos: string[];
  /** the drawn sheet's stored name, when one exists (it is also in `photos`) */
  sheet?: string | null;
  photo_full?: string[] | null;
  photo_thumbs?: string[] | null;
};

const ABSOLUTE = /^(https?:|blob:|data:)/;

/** a site-relative path rides the API base ("" when the Next proxy serves
 *  the photo routes same-origin); anything absolute is already an address */
const from = (base: string, url: string) => (ABSOLUTE.test(url) ? url : `${base}${url}`);

/** the minted entry beside `name`, or nothing. A list that is not the
 *  same length as `photos` is not parallel to it and is not trusted: the
 *  wrong index would draw a different photo under this one's name. */
function minted(a: PhotoLists, name: string, list: string[] | null | undefined): string {
  const i = a.photos.indexOf(name);
  if (i < 0 || !list || list.length !== a.photos.length) return "";
  return list[i] || "";
}

/** Every address worth trying for one photo at full size, best first:
 *  the minted one, then the name through the photo route. `name` is an
 *  entry of `a.photos` (or the poster, which is already an address). */
export function photoSources(a: PhotoLists, name: string, base = ""): string[] {
  const out: string[] = [];
  for (const url of [minted(a, name, a.photo_full), name]) {
    const src = url ? from(base, url) : "";
    if (src && !out.includes(src)) out.push(src);
  }
  return out;
}

/** The small address for one photo (a strip tile, a plate): the 480px
 *  derivative when the listing names one, else the full-size choice. */
export function photoThumb(a: PhotoLists, name: string, base = ""): string {
  const small = minted(a, name, a.photo_thumbs);
  return small ? from(base, small) : (photoSources(a, name, base)[0] ?? "");
}

/* The sheet IS the element once drawn (2026-10-12): it is what every shot is
   held to. The photos it was drawn from stay on the element only so the
   sheet can be redrawn, so the card shows the sheet alone and the detail
   view files the photos as SOURCE photos (Mike, 2026-10-14). */

/** the element's photos other than its sheet: what a redraw is made from */
export function sourcePhotos(a: PhotoLists): string[] {
  return a.sheet ? a.photos.filter((u) => u !== a.sheet) : a.photos.slice();
}

/** the card's footer line: what the element is made of */
export function framesLine(a: PhotoLists): string {
  const n = sourcePhotos(a).length;
  const plural = (k: number, one: string) => `${k} ${one}${k === 1 ? "" : "s"}`;
  if (a.sheet) return n ? `sheet · from ${plural(n, "photo")}` : "sheet";
  return n ? plural(n, "frame") : "no photos yet";
}
