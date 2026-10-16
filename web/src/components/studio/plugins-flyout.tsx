"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Puzzle } from "lucide-react";

type Plugin = { name: string; href?: string };
type Group = { label: string; items: Plugin[] };

/* The rail's Plugins row and its flyout (plan 2026-10-16). Live rows link out
   to the page where each client adds the Phantra connector. Everything else is
   listed so people can see what is coming, and reads as disabled. */
export const PLUGIN_GROUPS: Group[] = [
  {
    label: "MCP",
    items: [
      { name: "ChatGPT", href: "https://chatgpt.com/plugins" },
      { name: "Claude", href: "https://claude.ai/customize/connectors" },
      { name: "Grok Bot" },
      { name: "Muse" },
    ],
  },
  { label: "On the go", items: [{ name: "Mobile app" }] },
  {
    label: "Creative apps",
    items: [{ name: "Premiere Pro" }, { name: "After Effects" }, { name: "DaVinci Resolve" }],
  },
  { label: "For developers", items: [{ name: "Developer API" }] },
];

/** The Plugins row for the studio rail. The flyout is portalled to the body
 *  because the rail clips its children, and it opens to the right of the row. */
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
                  {g.items.map((it) =>
                    it.href ? (
                      <a
                        key={it.name}
                        role="menuitem"
                        className="pfrow"
                        href={it.href}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <span className="pfic" aria-hidden />
                        {it.name}
                        <span className="pftag live">Live</span>
                      </a>
                    ) : (
                      <div key={it.name} role="menuitem" aria-disabled="true" className="pfrow off">
                        <span className="pfic" aria-hidden />
                        {it.name}
                        <span className="pftag soon">Coming soon</span>
                      </div>
                    ),
                  )}
                </div>
              ))}
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
