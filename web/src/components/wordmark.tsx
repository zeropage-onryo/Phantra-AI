import Link from "next/link";

import { OwlLockup } from "@/components/owl-lockup";

// The logo the header and footer share: the hand-drawn lowercase "phantra"
// with the owl hiding behind its p (the trademark lockup, 2026-10-15). With
// `intro` (the site header) the owl makes one round behind the word the first
// time it loads in a browser session; everywhere else it stays at rest.
export function Wordmark({ className = "", intro = false }: { className?: string; intro?: boolean }) {
  return (
    <Link href="/" className={`group flex items-center text-foreground ${className}`} aria-label="Phantra home">
      <OwlLockup intro={intro} className="h-6 w-auto" />
    </Link>
  );
}
