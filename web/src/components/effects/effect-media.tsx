import type { ShowcaseItem } from "@/lib/showcase";
import { stillOf } from "@/lib/public-effects";

/* One effect's example on the public pages: a clip plays muted on a loop
   (its poster first), a still is a picture. `rest` draws a clip as its
   poster only -- the gallery's cards, so a page of 30 does not play 30
   videos at once. A clip with no poster rests on its own first frame. */
export function EffectMedia({
  media,
  alt,
  rest = false,
  className = "",
}: {
  media: ShowcaseItem;
  alt: string;
  rest?: boolean;
  className?: string;
}) {
  const still = stillOf(media);
  if (media.kind === "still") {
    // eslint-disable-next-line @next/next/no-img-element -- a media.phantra.ai address, not a bundled asset
    return <img src={media.after} alt={alt} loading="lazy" className={`size-full object-cover ${className}`} />;
  }
  if (rest && still) {
    // eslint-disable-next-line @next/next/no-img-element -- as above
    return <img src={still} alt={alt} loading="lazy" className={`size-full object-cover ${className}`} />;
  }
  return (
    <video
      src={rest ? `${media.after}#t=0.1` : media.after}
      poster={still ?? undefined}
      autoPlay={!rest}
      muted
      loop
      playsInline
      preload={rest ? "metadata" : "auto"}
      aria-label={alt}
      className={`size-full object-cover ${className}`}
    />
  );
}
