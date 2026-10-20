"use client";

/* The project's BRAND KIT select (2026-10-20, docs/tasks/task-brand-kit.md).
   Saved the moment it changes, like the Explore switch: from then on every
   scene this project writes takes the kit's voice, every still, keyframe
   and clip its look, and every editor export its captions and end card.
   "No kit" is the project as it always was. */
import { useEffect, useState } from "react";
import Link from "next/link";
import { getProjectKit, listBrandKits, setProjectKit } from "@/lib/studio-api";
import type { Kit } from "@/lib/brand-kit";
import { useShell } from "@/components/studio/shell";

export function BrandKitPicker({ projectId, label }: { projectId: number; label: string }) {
  const { toast } = useShell();
  const [kits, setKits] = useState<Kit[] | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [gone, setGone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    Promise.all([listBrandKits(), getProjectKit(projectId)])
      .then(([list, mine]) => {
        if (!live) return;
        setKits(list.kits);
        setPicked(mine.brand_kit?.id ?? null);
        // picked once, since deleted: the project reads as having none
        setGone(!!mine.picked && !mine.brand_kit);
      })
      .catch(() => live && setKits([]));
    return () => {
      live = false;
    };
  }, [projectId]);

  const choose = async (value: string) => {
    const next = value ? Number(value) : null;
    const was = picked;
    setPicked(next);
    setBusy(true);
    try {
      const got = await setProjectKit(projectId, next);
      setGone(false);
      toast(
        got.brand_kit
          ? `${got.brand_kit.name} on this project — its next scene, still, clip and export use it`
          : "No brand kit — this project works as before",
        "ok",
        { action: { label: "Undo", run: () => setProjectKit(projectId, was).then(() => setPicked(was)) } },
      );
    } catch (e) {
      setPicked(was);
      toast(e instanceof Error ? e.message : "The kit was not saved", "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <label className="flex flex-col gap-1.5">
      <span className={label}>BRAND KIT — ITS VOICE, LOOK, CAPTIONS AND END CARD</span>
      <div className="flex items-center gap-2">
        <select
          value={picked ?? ""}
          disabled={busy || kits === null}
          onChange={(e) => void choose(e.target.value)}
          className="h-10 min-w-0 flex-1 rounded-[6px] border border-noir-line bg-noir-bg px-2 text-[13px] text-bone outline-none focus:border-bone3"
          aria-label="Brand kit"
        >
          <option value="">No kit</option>
          {(kits ?? []).map((k) => (
            <option key={k.id} value={k.id}>
              {k.name}
            </option>
          ))}
        </select>
        <Link href={picked ? `/studio/brand/${picked}` : "/studio/brand"} className="font-plex text-[11px] text-bone3! hover:text-bone!">
          {picked ? "Open" : "Kits"}
        </Link>
      </div>
      {gone ? <span className="font-plex text-[11px] text-bone3">The kit this project picked was deleted.</span> : null}
    </label>
  );
}
