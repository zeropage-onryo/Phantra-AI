"use client";

/* The settings area's frame (2026-10-11): the section nav on the left and
   the open section beside it. A phone gets the nav as a row of pills over
   the section. The list of sections is lib/settings-sections.ts -- the
   ⌘K palette reads the same one. */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ComponentType, type ReactNode } from "react";
import { ChartNoAxesColumn, Coins, Plug, SlidersHorizontal, UserRound, Users } from "lucide-react";
import { goToSignIn } from "@/lib/api";
import { SECTIONS, sectionOf, type SectionId } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { Button, EmptyState, SettingsCard } from "@/components/studio/settings/ui";

const ICONS: Record<SectionId, ComponentType<{ strokeWidth?: number; "aria-hidden"?: boolean }>> = {
  account: UserRound,
  plan: Coins,
  usage: ChartNoAxesColumn,
  workspace: Users,
  connections: Plug,
  preferences: SlidersHorizontal,
};

export function SettingsFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const open = sectionOf(pathname);
  const { signedOut } = useShell();
  // on a phone the nav is a row of pills that scrolls sideways: bring the
  // open section's pill into view, or a deep link lands with it off screen
  const nav = useRef<HTMLElement>(null);
  useEffect(() => {
    const row = nav.current;
    const pill = row?.querySelector<HTMLElement>('a[aria-current="page"]');
    if (!row || !pill || row.scrollWidth <= row.clientWidth) return;
    const from = row.getBoundingClientRect();
    const at = pill.getBoundingClientRect();
    row.scrollTo({ left: row.scrollLeft + at.left - from.left - (row.clientWidth - at.width) / 2 });
  }, [open?.id]);

  return (
    <div className="zset">
      <div className="zset-wrap">
        <aside className="zset-side">
          <h1 className="zset-title">Settings</h1>
          <nav className="zset-nav" aria-label="Settings sections" ref={nav}>
            {SECTIONS.map((s) => {
              const Glyph = ICONS[s.id];
              return (
                <Link key={s.id} href={s.href} aria-current={open?.id === s.id ? "page" : undefined}>
                  <Glyph strokeWidth={1.6} aria-hidden />
                  {s.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <div className="zset-main">
          {signedOut ? (
            <SettingsCard>
              <EmptyState
                icon={UserRound}
                title="Sign in to see your settings"
                action={
                  <Button variant="primary" onClick={() => goToSignIn(undefined, pathname || undefined)}>
                    Sign in
                  </Button>
                }
              >
                Your account, your credits and your connections are behind your sign-in.
              </EmptyState>
            </SettingsCard>
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  );
}
