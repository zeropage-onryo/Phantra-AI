"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowUpRight, Code, Music2, Puzzle, Smartphone, type LucideIcon } from "lucide-react";
import { BrandMark, type BrandMarkId } from "@/components/studio/plugin-marks";

type Plugin = { name: string; href?: string; icon?: LucideIcon; mark?: BrandMarkId };
type Group = { label: string; items: Plugin[] };

/* The rail's Plugins row and its flyout (plan 2026-10-16). Live rows link out
   to the page where each client adds the Phantra connector. Everything else is
   listed so people can see what is coming, and reads as disabled. */
export const PLUGIN_GROUPS: Group[] = [
  {
    label: "MCP",
    items: [
      { name: "ChatGPT", href: "https://chatgpt.com/plugins", mark: "chatgpt" },
      { name: "Claude", href: "https://claude.ai/customize/connectors", mark: "claude" },
      { name: "Grok Bot", mark: "grok" },
      { name: "Muse", icon: Music2 },
    ],
  },
  { label: "On the go", items: [{ name: "Mobile app", icon: Smartphone }] },
  {
    label: "Creative apps",
    items: [
      { name: "Premiere Pro", mark: "premierepro" },
      { name: "After Effects", mark: "aftereffects" },
      { name: "DaVinci Resolve", mark: "davinciresolve" },
    ],
  },
  { label: "For developers", items: [{ name: "Developer API", icon: Code }] },
];

/** The Plugins row for the studio rail. The flyout is portalled to the body
 *  because the rail clips its children, and it opens to the right of the row.
 *  Under 720px it becomes a bottom sheet over a tap-to-close backdrop. */
export function PluginsRailItem() {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    // Placed once on open, while the pointer is still in the widened rail.
    const place = () => {
      const r = btn.current?.getBoundingClientRect();
      if (r) setPos({ top: r.top, left: r.right + 8 });
    };
    place();
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!panel.current?.contains(t) && !btn.current?.contains(t)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btn.current?.focus();
      }
    };
    window.addEventListener("resize", place);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", place);
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <>
      <button
        ref={btn}
        type="button"
        className="pfbtn"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Plugins"
        onClick={() => setOpen((v) => !v)}
      >
        <Puzzle strokeWidth={1.35} />
        <span className="rl">Plugins</span>
      </button>
      {open && pos && typeof document !== "undefined"
        ? createPortal(
            <>
              <div className="pfbd" aria-hidden onClick={() => setOpen(false)} />
              <div
                ref={panel}
                className="pfly"
                role="menu"
                aria-label="Plugins"
                style={{ top: pos.top, left: pos.left }}
              >
                {PLUGIN_GROUPS.map((g, i) => (
                  <div key={g.label}>
                    {i > 0 ? <div className="pfsep" /> : null}
                    <div className="pfh">{g.label}</div>
                    {g.items.map((it) => {
                      const Icon = it.icon ?? Puzzle;
                      return it.href ? (
                        <a
                          key={it.name}
                          role="menuitem"
                          className="pfrow live"
                          href={it.href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <span className="pfic" aria-hidden>
                            {it.mark ? <BrandMark id={it.mark} size={16} /> : <Icon strokeWidth={1.75} aria-hidden="true" />}
                          </span>
                          <span className="pflabel">{it.name}</span>
                          <ArrowUpRight className="pfarr" strokeWidth={1.75} aria-hidden="true" />
                          <span className="pftag live">Live</span>
                        </a>
                      ) : (
                        <div
                          key={it.name}
                          role="menuitem"
                          aria-disabled="true"
                          className="pfrow off"
                        >
                          <span className="pfic" aria-hidden>
                            {it.mark ? <BrandMark id={it.mark} size={16} /> : <Icon strokeWidth={1.75} aria-hidden="true" />}
                          </span>
                          <span className="pflabel">{it.name}</span>
                          <span className="pftag soon">Coming soon</span>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </>,
            document.body,
          )
        : null}
    </>
  );
}
