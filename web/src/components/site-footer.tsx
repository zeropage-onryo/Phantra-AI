import Link from "next/link";
import { Wordmark } from "@/components/wordmark";
import { OwlLockup } from "@/components/owl-lockup";
import { BrandLogo } from "@/components/mcp/brand-logos";
import { CHATGPT_PLUGIN_URL } from "@/lib/connect-claude";
import { makePath, pagesIn } from "@/landing-pages/pages";
import { pageLabel } from "@/landing-pages/shared";

const COLUMNS: { title: string; links: [string, string][] }[] = [
  {
    title: "Studio",
    links: [
      ["How it works", "/#how"],
      ["Models", "/models"],
      ["MCP & Claude plugin", "/mcp"],
      ["Frames", "/#frames"],
      ["Who it's for", "/#work"],
    ],
  },
  {
    // "Tools" (Mike, 2026-10-02): the word the generator sites use and the
    // phrase people search; "Make" is the URL segment, not a label.
    title: "Tools",
    // every /make landing page, off its own entry, so the site links to
    // each one from every page (crawlers find it; the person does too)
    // and the /make hub first (2026-10-27), which groups them
    // and the public Effects gallery (2026-11-05): its one link off the
    // site's chrome, by Mike's call -- not in the header, not on the home
    links: [["All tools", "/make"], ["Effects", "/effects"], ...pagesIn("make").map((page): [string, string] => [page.h1, makePath(page)])],
  },
  {
    // every model's own page, under /models (2026-10-05, Mike's call)
    title: "Models",
    links: pagesIn("models").map((page) => [pageLabel(page), makePath(page)]),
  },
  {
    title: "Plans",
    links: [
      ["Pricing", "/pricing"],
      ["What's new", "/whats-new"],
      ["FAQ", "/faq"],
      ["Support", "/support"],
      ["Affiliates", "/affiliates"],
      ["Creators", "/creators"],
      ["Sign in", "/studio"],
      ["Start creating", "/studio"],
    ],
  },
  {
    title: "Legal",
    links: [
      ["Terms", "/terms"],
      ["Privacy", "/privacy"],
      ["Data deletion", "/data-deletion"],
    ],
  },
];

/** `compact` (the home page, 2026-10-26): on a phone the footer is the
 *  Studio, Plans and Legal links in two columns; the Tools and Models lists
 *  stay in the page (crawlers follow them) but are not drawn under 640px,
 *  where the header's menu carries both.
 *
 *  `lemon` (the home page, 2026-11-02, Mike's "17d" pick): the footer on the
 *  Phantra lemon, dark ink, a closing line with Start free and Use it in
 *  ChatGPT above the same columns, and the lockup large and faint behind. */
export function SiteFooter({ compact = false, lemon = false }: { compact?: boolean; lemon?: boolean }) {
  const linkClass = lemon
    ? "text-sm text-[#2b2a1a] underline-offset-2 transition-colors hover:text-[var(--lemon-ink)] hover:underline"
    : "text-sm text-[var(--nav-fg)] transition-colors hover:text-foreground";
  return (
    <footer
      className={
        lemon
          ? "relative overflow-hidden bg-[var(--lemon)] text-[var(--lemon-ink)]"
          : "border-t border-border"
      }
    >
      {lemon && (
        <div aria-hidden className="pointer-events-none absolute -bottom-10 left-6 w-[min(1100px,90vw)] opacity-[0.08] sm:left-20">
          <OwlLockup className="h-auto w-full" />
        </div>
      )}
      <div className="relative mx-auto max-w-[1200px] px-6 py-14">
        {lemon && (
          <div className="mb-12 flex flex-col gap-6 border-b-[1.5px] border-[rgba(11,10,8,0.18)] pb-10 md:flex-row md:items-center md:justify-between">
            <h2 className="serif text-[clamp(2rem,4vw,3.25rem)] leading-none tracking-[-0.02em]">Make your first video today.</h2>
            <div className="flex flex-wrap items-center gap-3">
              <a
                href={CHATGPT_PLUGIN_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-12 items-center gap-2.5 rounded-full border-2 border-[var(--lemon-ink)] px-5 text-[15px] font-bold"
              >
                <BrandLogo name="openai" className="size-5" />
                Use it in ChatGPT
                <span className="sr-only">(opens in a new tab)</span>
              </a>
              <Link
                href="/studio"
                className="inline-flex min-h-12 items-center rounded-full bg-[var(--lemon-ink)] px-6 text-[15px] font-bold text-[var(--lemon)] transition-colors hover:bg-[#252422]"
              >
                Start free
              </Link>
            </div>
          </div>
        )}
        <div
          className={`grid sm:grid-cols-2 md:grid-cols-[1.4fr_repeat(5,1fr)] ${compact ? "grid-cols-2 gap-x-6 gap-y-10 sm:gap-10" : "gap-10"}`}
        >
          <div className={`max-w-xs ${compact ? "col-span-2 sm:col-span-1" : ""}`}>
            {lemon ? (
              <Link href="/" aria-label="Phantra home" className="flex items-center text-[var(--lemon-ink)]">
                <OwlLockup className="h-8 w-auto" />
              </Link>
            ) : (
              <Wordmark />
            )}
            <p className={`mt-4 text-sm leading-relaxed ${lemon ? "" : "text-[var(--ink-2)]"}`}>
              {lemon
                ? "AI image & video, made for you — for filmmakers, brands, and creators."
                : "The AI content studio that creates for you — for filmmakers, brands, and creators."}
            </p>
          </div>
          {COLUMNS.map((column) => (
            <div
              key={column.title}
              className={`flex-col gap-3 ${compact && (column.title === "Tools" || column.title === "Models") ? "hidden sm:flex" : "flex"}`}
            >
              <span className={lemon ? "serif text-[18px]" : "eyebrow"}>{column.title}</span>
              {column.links.map(([label, href]) => (
                <Link key={label + href} href={href} className={linkClass}>
                  {label}
                </Link>
              ))}
            </div>
          ))}
        </div>

        <div
          className={`mt-12 flex flex-col gap-2 border-t pt-6 text-[13px] sm:flex-row sm:items-center sm:justify-between ${
            lemon ? "border-[rgba(11,10,8,0.18)] font-medium" : "border-border text-[var(--ink-3)]"
          }`}
        >
          <span>© {new Date().getFullYear()} Phantra</span>
          <span>From idea to creation</span>
        </div>
      </div>
    </footer>
  );
}
