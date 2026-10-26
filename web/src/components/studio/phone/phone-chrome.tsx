"use client";

/* THE PHONE'S CHROME (2026-10-26, Mike's "Phantra Mobile Studio" canvas,
   after a side-by-side with Higgsfield's mobile site). Under 720px the
   desktop rail and header step aside (studio.css hides them there) and
   the studio is three things:

   - a top bar with ONLY the menu button (left, Mike's call) and the logo;
   - a bottom bar of five labelled tabs: Home · Assets · a big Create
     button · Effects · Profile;
   - a full-screen menu holding everything that left the bar (Projects,
     the Image and Video generators, Elements, Brand kits, Calendar,
     Plugins, Settings).

   The credit pill, search, the activity tray and New session are not on a
   phone's top bar: credits live on the Profile tab (/studio/me). None of
   this is drawn above 720px. Nothing here spends. */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  AtSign,
  CalendarDays,
  Clapperboard,
  FolderKanban,
  House,
  ImageIcon,
  LayoutGrid,
  Menu,
  Palette,
  Plug,
  Settings,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { OwlLockup } from "@/components/owl-lockup";
import { effectsDoor, EFFECTS_TAB_HREF, type Capabilities } from "@/lib/create-v2";
import { SETTINGS_HOME } from "@/lib/settings-sections";
import "./phone.css";

/** Where the Create button goes: the compose page, the box alone. */
export const COMPOSE_HREF = "/studio/new";

/** Where the Effects tab goes: the Effects page when its flag is on, else
 *  the composer's own gallery, opened on the compose page. */
export const effectsHref = (caps: Capabilities) => (effectsDoor(caps) === "tab" ? EFFECTS_TAB_HREF : `${COMPOSE_HREF}?open=effects`);

export type PhoneTab = "home" | "assets" | "create" | "effects" | "profile" | null;

/** Which tab a path lights. Exported for the tests. */
export function phoneTabOf(pathname: string): PhoneTab {
  const p = pathname.replace(/\/$/, "") || "/studio";
  if (p === "/studio") return "home";
  if (p === COMPOSE_HREF || p === "/studio/chat") return "create";
  if (p.startsWith("/studio/assets")) return "assets";
  if (p.startsWith("/studio/effects")) return "effects";
  if (p.startsWith("/studio/me") || p.startsWith("/studio/settings")) return "profile";
  return null;
}

/** The phone's top bar: the menu on the left, then the logo. */
export function PhoneTop({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="ph-top">
      <button type="button" className="ph-round" onClick={onMenu} aria-label="Menu">
        <Menu strokeWidth={2} />
      </button>
      <Link href="/studio" className="ph-logo" aria-label="Phantra home">
        {/* the site's own lockup: the owl behind the hand-drawn "phantra" */}
        <OwlLockup intro className="ph-lockup" />
      </Link>
    </header>
  );
}

const Star = () => (
  <svg viewBox="0 0 24 24" aria-hidden fill="currentColor">
    <path d="M12 2.5c.5 4.6 2.9 7 7.5 7.5v.9c-4.6.5-7 2.9-7.5 7.5h-.9c-.5-4.6-2.9-7-7.5-7.5V10c4.6-.5 7-2.9 7.5-7.5z" transform="translate(.4 1.6)" />
  </svg>
);

/** The phone's five tabs. `unseen`: the what's-new count (shell.tsx), a dot
 *  on Home, where the news is on a phone. */
export function PhoneTabs({ caps, unseen = 0 }: { caps: Capabilities; unseen?: number }) {
  const pathname = usePathname() || "/studio";
  const on = phoneTabOf(pathname);
  const tab = (id: Exclude<PhoneTab, null | "create">, href: string, label: string, Icon: typeof House) => (
    <Link href={href} className="ph-tab" aria-current={on === id ? "page" : undefined}>
      <Icon strokeWidth={1.9} />
      <span>{label}</span>
      {id === "home" && unseen > 0 ? <span className="nbadge dot ph-new" aria-label={`${unseen} new`} /> : null}
    </Link>
  );
  return (
    <nav className="ph-tabs" aria-label="Studio">
      {tab("home", "/studio", "Home", House)}
      {tab("assets", "/studio/assets", "Assets", LayoutGrid)}
      <Link href={COMPOSE_HREF} className="ph-create" aria-label="Create" aria-current={on === "create" ? "page" : undefined}>
        <Star />
      </Link>
      {tab("effects", effectsHref(caps), "Effects", Sparkles)}
      {tab("profile", "/studio/me", "Profile", UserRound)}
    </nav>
  );
}

/** Everything that left the bar, as one full-screen sheet. */
export function PhoneMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  // every link in it closes it on the way (onClick), so there is no
  // route watcher here
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    const was = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", esc);
      document.body.style.overflow = was;
    };
  }, [open, onClose]);
  if (!open) return null;
  const row = (href: string, label: string, Icon: typeof House) => (
    <Link href={href} className="ph-menu-row" onClick={onClose}>
      <Icon strokeWidth={1.9} />
      {label}
    </Link>
  );
  return (
    <div className="ph-menu" role="dialog" aria-modal="true" aria-label="Menu">
      <header className="ph-top">
        <button type="button" className="ph-round" onClick={onClose} aria-label="Close menu">
          <X strokeWidth={2.2} />
        </button>
        <Link href="/studio" className="ph-logo" aria-label="Phantra home" onClick={onClose}>
          <OwlLockup className="ph-lockup" />
        </Link>
      </header>
      <nav className="ph-menu-list" aria-label="Tools">
        {row("/studio/projects", "Projects", FolderKanban)}
        {row("/studio/video", "Video", Clapperboard)}
        {row("/studio/image", "Image", ImageIcon)}
        {row("/studio/elements", "Elements", AtSign)}
        {row("/studio/brand", "Brand kits", Palette)}
        {row("/studio/calendar", "Calendar", CalendarDays)}
        {row("/studio/plugins", "Plugins", Plug)}
        {row(SETTINGS_HOME, "Settings", Settings)}
      </nav>
      <div className="ph-menu-foot">
        <Link href={COMPOSE_HREF} className="ph-go" onClick={onClose}>
          Start creating
        </Link>
      </div>
    </div>
  );
}
