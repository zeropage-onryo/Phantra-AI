import Link from "next/link";

// The wordmark the header and footer share: the name set in the body face
// at 600 -- a logo-sized word, not a headline. Text only; no mark.
export function Wordmark({ className = "" }: { className?: string; intro?: boolean }) {
  return (
    <Link href="/" className={`group flex items-center gap-2.5 ${className}`} aria-label="Phantra home">
      <span className="text-[17px] font-semibold tracking-[-0.02em] text-foreground">phantra</span>
    </Link>
  );
}
