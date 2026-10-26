"use client";

/* The brand kit page's "Use kit ▾" (2026-10-22, Mike, after Higgsfield's Use
   Kit menu). Three kinds of item, none of which spends:

   - Start: Vesper, or an empty box on Image or Video, the kit on for that
     conversation (a Create link, lib/kit-use.ts);
   - Starters: the same, with a first line typed in the box to finish;
   - Put on a project: the project's kit pick (PUT /projects/<id>/brand-kit,
     what the project panel's picker does), with Undo, then the project.

   The links go through Create's own ?kit= / ?kind= / ?spark= / ?frame=, so
   what opens is exactly what the composer's own picker would give. */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Clapperboard, FolderOpen, Image as ImageIcon, MessageCircle, Sparkles } from "lucide-react";
import { getProjectKit, listProjects, setProjectKit, type Project } from "@/lib/studio-api";
import { kitDoors, kitStarters, type KitUse } from "@/lib/kit-use";
import { useShell } from "@/components/studio/shell";

const ICONS: Record<string, React.ReactNode> = {
  agent: <MessageCircle size={14} />,
  image: <ImageIcon size={14} />,
  video: <Clapperboard size={14} />,
};

const ITEM =
  "flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-white/90 hover:bg-white/8 focus:bg-white/8 focus:outline-none";
const MENU_W = 290;
const HEAD = "px-2.5 pt-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-white/40";

export function UseKitMenu({
  kit,
  unsaved = false,
  className,
  buttonClassName,
  label = "Use kit",
}: {
  kit: { id: number; name: string };
  /** the trigger's own look (the brand pages' pill, 2026-10-26); the old box otherwise */
  buttonClassName?: string;
  label?: string;
  /** the page holds edits not saved yet: the studio would use the saved kit */
  unsaved?: boolean;
  className?: string;
}) {
  const router = useRouter();
  const { toast } = useShell();
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<Project[] | null>(null);
  // which edge the menu hangs from: the button's right unless that would run
  // it off the left of a narrow screen (the phone, where the button wraps)
  const [fromLeft, setFromLeft] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const off = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", off);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", off);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  // the projects, read the first time the menu opens
  useEffect(() => {
    if (!open || projects !== null) return;
    listProjects()
      .then((r) => setProjects(r.items.filter((p) => !p.archived)))
      .catch(() => setProjects([]));
  }, [open, projects]);

  const go = (use: KitUse) => {
    setOpen(false);
    router.push(use.href);
  };

  const putOn = async (p: Project) => {
    setOpen(false);
    try {
      const was = await getProjectKit(p.id).catch(() => null);
      const before = was?.brand_kit?.id ?? null;
      if (before === kit.id) {
        router.push(`/studio/projects/${p.id}`);
        return;
      }
      await setProjectKit(p.id, kit.id);
      toast(`${kit.name} is on ${p.title || "the project"}`, "ok", {
        action: { label: "Undo", run: () => setProjectKit(p.id, before) },
      });
      router.push(`/studio/projects/${p.id}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not put the kit on that project", "err");
    }
  };

  const row = (use: KitUse, icon: React.ReactNode) => (
    <button type="button" role="menuitem" key={use.id} className={ITEM} onClick={() => go(use)}>
      <span className="mt-0.5 text-white/60">{icon}</span>
      <span className="flex min-w-0 flex-col">
        <span>{use.label}</span>
        <span className="text-[11.5px] text-white/45">{use.note}</span>
      </span>
    </button>
  );

  return (
    <div className={`relative ${className ?? ""}`} ref={box}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          const r = box.current?.getBoundingClientRect();
          setFromLeft(!!r && r.right < MENU_W + 16);
          setOpen((v) => !v);
        }}
        className={
          buttonClassName ??
          "inline-flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-[13px] text-white hover:border-white/40"
        }
      >
        {label} <ChevronDown size={13} />
      </button>
      {open ? (
        <div
          role="menu"
          aria-label={`Use ${kit.name}`}
          style={{ width: MENU_W }}
          className={`absolute ${fromLeft ? "left-0" : "right-0"} z-40 mt-1.5 max-w-[calc(100vw-32px)] rounded-[18px] border border-[var(--edge-hi)] bg-[var(--raise)] p-1.5 shadow-2xl`}
        >
          {unsaved ? (
            <p className="mx-1 mb-1 rounded-md bg-amber-500/10 px-2.5 py-2 text-[12px] text-amber-100">
              You have unsaved changes. Save first, or the studio uses the kit as it was last saved.
            </p>
          ) : null}
          <div className={HEAD}>Start with {kit.name}</div>
          {kitDoors(kit).map((u) => row(u, ICONS[u.id]))}
          <div className="my-1 border-t border-white/10" />
          <div className={HEAD}>Starters</div>
          {kitStarters(kit).map((u) => row(u, <Sparkles size={14} />))}
          <div className="my-1 border-t border-white/10" />
          <div className={HEAD}>Put on a project</div>
          {projects === null ? (
            <div className="px-2.5 py-2 text-[12px] text-white/45">loading…</div>
          ) : projects.length ? (
            <div className="max-h-48 overflow-y-auto">
              {projects.map((p) => (
                <button type="button" role="menuitem" key={p.id} className={ITEM} onClick={() => putOn(p)}>
                  <span className="mt-0.5 text-white/60">
                    <FolderOpen size={14} />
                  </span>
                  <span className="truncate">{p.title || "Untitled project"}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="px-2.5 py-2 text-[12px] text-white/45">
              No projects yet. Ask Vesper to start one and it can carry this kit.
            </div>
          )}
          <p className="px-2.5 pt-1.5 pb-1 text-[11px] text-white/35">Nothing here spends. Every make shows its price first.</p>
        </div>
      ) : null}
    </div>
  );
}
