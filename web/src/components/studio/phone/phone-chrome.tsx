"use client";

/* THE PHONE'S CHROME (2026-10-26, Mike's "Phantra Mobile Studio" canvas,
   after a side-by-side with Higgsfield's mobile site). Under 720px the
   desktop rail and header step aside (studio.css hides them there) and
   the studio is three things:

   - a top bar with ONLY the menu button (left, Mike's call) and the logo;
   - a bottom bar of five labelled tabs: Home · Assets · a big Create
     button · Effects · Profile;
   - a full-screen menu holding everything that left the bar (Projects,
     the Image and Video generators, Voice where the rail shows it, Ad
     Studio, Elements, Brand kits, Calendar, Plugins, Settings).

   The credit pill, search, the activity tray and New session are not on a
   phone's top bar: credits live on the Profile tab (/studio/me). None of
   this is drawn above 720px. Nothing here spends. */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AudioLines,
  Clapperboard,
  FolderKanban,
  House,
  ImageIcon,
  LayoutGrid,
  PanelLeft,
  PanelLeftClose,
  Plus,
  Plug,
  Sparkles,
  UserRound,
} from "lucide-react";
import { OwlLockup, OwlMark } from "@/components/owl-lockup";
import { effectsDoor, EFFECTS_TAB_HREF, type Capabilities } from "@/lib/create-v2";
import { useShell } from "@/components/studio/shell";
import { useAssistantThread } from "@/components/studio/assistant-thread";
import { listChats, type ChatSummary } from "@/lib/assistant";
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

/** The phone's top bar (2026-11-04, Mike's mobile canvas): the menu on the
 *  left and, until there is a plan, a yellow Upgrade on the right. The logo
 *  is in the drawer and above the Create box, not here. */
export function PhoneTop({ onMenu }: { onMenu: () => void }) {
  const { balance, signedOut } = useShell();
  const upgrade = !signedOut && balance !== null && !balance.plan && !balance.exempt;
  return (
    <header className="ph-top">
      <button type="button" className="ph-round ph-bare" onClick={onMenu} aria-label="Menu">
        <PanelLeft strokeWidth={1.9} />
      </button>
      <span className="ph-top-gap" />
      {upgrade ? (
        <Link href="/studio/settings/plan" className="ph-upgrade">
          Upgrade
        </Link>
      ) : null}
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
/* THE DOCKED BOX'S HEIGHT (2026-10-29). On a phone every create box --
   Create, the chat, Image, Video -- is pinned above the tab bar from the
   moment the page opens, the way Higgsfield's is (Mike: "the create is
   still not staying at the bottom when you load it"). A pinned box takes no
   room in the page, so the page keeps --ph-dock clear under its last line:
   this measures whichever box is on screen and keeps the number current as
   it grows with what is typed. */
const DOCKS = [
  '.view[data-page="compose"] .zc .stack',
  '.view[data-page="chat"] .zc.zc-active .zc-dock:has(.zc-project)',
  '.view[data-page="chat"] .zc.zc-active .zc-dock:not(:has(.zc-project)) .zc-box',
  ".dg .dgv-dock",
].join(", ");

function usePhoneDock(pathname: string) {
  useEffect(() => {
    const root = document.documentElement;
    let seen: Element | null = null;
    const ro = new ResizeObserver(() => {
      if (seen) root.style.setProperty("--ph-dock", `${Math.ceil(seen.getBoundingClientRect().height)}px`);
    });
    const find = () => {
      const el = document.querySelector(DOCKS);
      if (el === seen) return;
      if (seen) ro.unobserve(seen);
      seen = el;
      if (el) ro.observe(el);
      else root.style.removeProperty("--ph-dock");
    };
    find();
    // the page under the shell draws after the route changes, and the chat
    // swaps its box when a project opens: look again when the tree changes
    const mo = new MutationObserver(find);
    mo.observe(document.body, { childList: true, subtree: true });
    return () => {
      mo.disconnect();
      ro.disconnect();
      root.style.removeProperty("--ph-dock");
    };
  }, [pathname]);
}

export function PhoneTabs({ caps, unseen = 0 }: { caps: Capabilities; unseen?: number }) {
  const pathname = usePathname() || "/studio";
  const on = phoneTabOf(pathname);
  usePhoneDock(pathname);
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

/** THE DRAWER (2026-11-04, Mike's mobile canvas after Higgsfield's mobile
 *  site): a 322px panel on the left over a dimmed page. STATIC on purpose --
 *  it appears and goes at once, no slide, fade or bounce (no transition or
 *  animation anywhere in .ph-menu). Create, Image, Video, Effects, Projects,
 *  MCP, the three latest chats and the account card. What left it (Ad Studio,
 *  Elements, Brand kits, Calendar, Plugins, Affiliate) is on the Profile tab. */
export function PhoneMenu({ open, onClose, caps }: { open: boolean; onClose: () => void; caps: Capabilities }) {
  const { me, balance, signedOut } = useShell();
  const router = useRouter();
  const pathname = usePathname() || "/studio";
  const { openChat } = useAssistantThread();
  const [chats, setChats] = useState<ChatSummary[] | null>(null);
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
  // the latest chats are read each time the drawer opens
  useEffect(() => {
    if (!open || signedOut) return;
    let live = true;
    listChats()
      .then((l) => live && setChats(l.chats.slice(0, 3)))
      .catch(() => live && setChats([]));
    return () => {
      live = false;
    };
  }, [open, signedOut]);
  if (!open) return null;
  const here = phoneTabOf(pathname);
  const row = (href: string, label: string, Icon: typeof House, opts: { on?: boolean; tag?: string } = {}) => (
    <Link href={href} className="ph-menu-row" aria-current={opts.on ? "page" : undefined} onClick={onClose}>
      <Icon strokeWidth={1.9} />
      <span className="ph-menu-name">{label}</span>
      {opts.tag ? <span className="ph-tag">{opts.tag}</span> : null}
    </Link>
  );
  async function pick(c: ChatSummary) {
    onClose();
    try {
      if (!c.open) await openChat(c.id);
      router.push("/studio/chat");
    } catch {
      /* the chat could not be opened: stay where we are */
    }
  }
  const who = me?.user.display_name || me?.user.email || "Your account";
  const credits = balance ? (balance.exempt ? "Not charged" : `${Math.max(balance.available, 0).toLocaleString("en-US")} credits`) : "";
  return (
    <div className="ph-menu" role="dialog" aria-modal="true" aria-label="Menu">
      <button type="button" className="ph-scrim" onClick={onClose} aria-label="Close menu" tabIndex={-1} />
      <nav className="ph-drawer" aria-label="Studio">
        <header className="ph-drawer-top">
          <Link href="/studio" className="ph-logo" aria-label="Phantra home" onClick={onClose}>
            <OwlLockup className="ph-lockup ph-lockup-lg" />
          </Link>
          <button type="button" className="ph-round ph-bare" onClick={onClose} aria-label="Close menu">
            <PanelLeftClose strokeWidth={1.9} />
          </button>
        </header>
        <div className="ph-drawer-list">
          {row(COMPOSE_HREF, "Create", Plus, { on: here === "create" || here === "home" })}
          {row("/studio/image", "Image", ImageIcon)}
          {row("/studio/video", "Video", Clapperboard)}
          {caps.voice_tab === true ? row("/studio/voice", "Voice", AudioLines) : null}
          {row(effectsHref(caps), "Effects", Sparkles, { tag: "NEW" })}
          {row("/studio/projects", "Projects", FolderKanban)}
          <Link href="/mcp" className="ph-menu-row ph-menu-mcp" onClick={onClose}>
            <Plug strokeWidth={1.9} />
            <span className="ph-menu-name">MCP</span>
            <span className="ph-pill">Connect</span>
          </Link>
          {chats && chats.length > 0 ? (
            <>
              <div className="ph-drawer-label">Recent chats</div>
              {chats.map((c) => (
                <button key={c.id} type="button" className="ph-chat-row" data-open={c.open ? "1" : undefined} onClick={() => pick(c)}>
                  <span>{c.title || "New chat"}</span>
                </button>
              ))}
            </>
          ) : null}
        </div>
        <div className="ph-drawer-foot">
          {signedOut ? (
            <Link href="/studio/me" className="ph-account" onClick={onClose}>
              <span className="ph-account-text">
                <b>Sign in</b>
              </span>
            </Link>
          ) : (
            <Link href="/studio/me" className="ph-account" onClick={onClose}>
              <OwlMark className="ph-account-owl" />
              <span className="ph-account-text">
                <b>{who}</b>
                {credits ? <span>{credits}</span> : null}
              </span>
              {balance && !balance.plan && !balance.exempt ? <span className="ph-account-up">Upgrade</span> : null}
            </Link>
          )}
        </div>
      </nav>
    </div>
  );
}
