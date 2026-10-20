"use client";

/* Brand kits (2026-10-20, docs/tasks/task-brand-kit.md).

   One card per kit -- its swatches, its logo, its name and how many
   projects picked it -- with New, Duplicate and Delete (with Undo). A kit is
   one client's identity, look, voice and sound; it does nothing until a
   project picks it (the project's Brand kit select), and then every scene
   that project writes, every still, keyframe and clip it renders, and every
   Cut export reads it. Nothing on this page spends. */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Copy, Palette, Plus, Trash2 } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  createBrandKit,
  deleteBrandKit,
  duplicateBrandKit,
  listBrandKits,
  restoreBrandKit,
} from "@/lib/studio-api";
import { type Kit, fileFor, kitSummary, logoFor, roleColour, withDefaults } from "@/lib/brand-kit";
import { useShell } from "@/components/studio/shell";
/* eslint-disable @next/next/no-img-element */

const BTN = "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] transition disabled:opacity-40";
const PRI = `${BTN} bg-white text-black! hover:bg-white/90`;
const GHOST = `${BTN} border border-white/15 text-white/80 hover:border-white/40`;

function KitCard({ kit, onOpen, onCopy, onDelete }: {
  kit: Kit;
  onOpen: () => void;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const spec = withDefaults(kit.spec);
  const bg = roleColour(spec, "background", "#151514");
  const logo = fileFor(kit, logoFor(bg)) ?? fileFor(kit, "logo_light") ?? fileFor(kit, "logo_dark");
  return (
    <article
      className="group flex cursor-pointer flex-col overflow-hidden rounded-xl border border-white/10 bg-white/[0.03] transition hover:border-white/30"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <div className="relative flex h-36 items-center justify-center" style={{ background: bg }}>
        {logo ? (
          <img src={`${API_URL}${logo.url}`} alt="" className="max-h-20 max-w-[70%] object-contain" />
        ) : (
          <span className="text-2xl font-semibold" style={{ color: roleColour(spec, "primary", "#f4f3f2") }}>
            {kit.name}
          </span>
        )}
        <div
          className="absolute top-2 right-2 flex gap-1.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
          onClick={(e) => e.stopPropagation()}
        >
          <button type="button" className="zdx bg-black/70" title="Duplicate" aria-label={`Duplicate ${kit.name}`} onClick={onCopy}>
            <Copy size={13} strokeWidth={1.7} />
          </button>
          <button type="button" className="zdx bg-black/70" title="Delete" aria-label={`Delete ${kit.name}`} onClick={onDelete}>
            <Trash2 size={13} strokeWidth={1.7} />
          </button>
        </div>
      </div>
      <div className="flex h-2">
        {spec.palette.map((s, i) => (
          <span key={i} className="flex-1" style={{ background: s.hex }} title={`${s.role} ${s.hex}`} />
        ))}
      </div>
      <div className="flex flex-col gap-1 p-3">
        <b className="text-[14px] text-white/90">{kit.name}</b>
        <span className="text-[12px] text-white/45">{kitSummary(kit)}</span>
      </div>
    </article>
  );
}

export default function BrandKitsPage() {
  const { toast } = useShell();
  const router = useRouter();
  const [kits, setKits] = useState<Kit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    listBrandKits()
      .then((r) => {
        setKits(r.kits);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
  useEffect(() => {
    load();
  }, []);

  const create = () => {
    if (!name.trim()) return;
    setBusy(true);
    createBrandKit(name.trim())
      .then((kit) => router.push(`/studio/brand/${kit.id}`))
      .catch((e) => toast(e instanceof Error ? e.message : "Could not create the kit", "err"))
      .finally(() => setBusy(false));
  };

  const copy = (kit: Kit) =>
    duplicateBrandKit(kit.id)
      .then((made) => {
        toast(`${made.name} made`);
        load();
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not duplicate", "err"));

  const remove = (kit: Kit) => {
    setKits((was) => (was ?? []).filter((k) => k.id !== kit.id));
    deleteBrandKit(kit.id)
      .then(() =>
        toast(`${kit.name} deleted${kit.projects ? ` · ${kit.projects} project${kit.projects === 1 ? "" : "s"} now have no kit` : ""}`, "ok", {
          action: { label: "Undo", run: () => restoreBrandKit(kit.id).then(load) },
        }),
      )
      .catch((e) => {
        toast(e instanceof Error ? e.message : "Could not delete", "err");
        load();
      });
  };

  return (
    <section className="view" style={{ paddingTop: 0 }}>
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-8">
        <header className="flex flex-col gap-2">
          <p className="kicker">Brand kits</p>
          <h1 className="text-2xl font-semibold text-white/95">One kit per client</h1>
          <p className="max-w-2xl text-[13px] leading-relaxed text-white/55">
            A kit holds a brand&rsquo;s logo, palette, fonts, look, voice and sound. Pick it on a project and every scene the
            project writes takes its tone, every still and clip takes its look, and every export from the editor takes its
            captions and logo end card &mdash; with nothing retyped. A project with no kit works exactly as before.
          </p>
        </header>

        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <input
            className="zin"
            style={{ maxWidth: 320 }}
            placeholder="New kit — the client's name"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
            aria-label="New kit name"
          />
          <button type="submit" className={PRI} disabled={busy || !name.trim()}>
            <Plus size={14} strokeWidth={2.2} /> New kit
          </button>
        </form>

        {error ? <div className="stateline err">{error}</div> : null}
        {kits && !kits.length ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-white/15 p-10 text-center text-[13px] text-white/50">
            <Palette size={22} strokeWidth={1.5} />
            No brand kits yet. Name one above to start.
          </div>
        ) : null}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(kits ?? []).map((kit) => (
            <KitCard
              key={kit.id}
              kit={kit}
              onOpen={() => router.push(`/studio/brand/${kit.id}`)}
              onCopy={() => copy(kit)}
              onDelete={() => remove(kit)}
            />
          ))}
        </div>
        {!kits && !error ? <span className="text-[12px] text-white/40">loading…</span> : null}
        <p className="text-[12px] text-white/35">
          <button type="button" className={GHOST} onClick={() => router.push("/studio/projects")}>
            Pick a kit on a project
          </button>
        </p>
      </div>
    </section>
  );
}
