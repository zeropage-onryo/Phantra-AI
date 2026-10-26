"use client";

/* Brand kits (2026-10-20, docs/tasks/task-brand-kit.md).

   One card per kit -- its swatches, its logo, its name and how many
   projects picked it -- with New, Duplicate and Delete (with Undo). A kit is
   one client's identity, look, voice and sound; it does nothing until a
   project picks it (the project's Brand kit select), and then every scene
   that project writes, every still, keyframe and clip it renders, and every
   Cut export reads it. Nothing on this page spends.

   "New kit from a website" (2026-10-21, src/brand_import.py) renders the
   site, reads its colours, fonts and logo, and files them as a NEW kit; the
   job's steps show here, then a link to the kit. Free, ten an hour. */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, Copy, Globe, Plus, Trash2, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  createBrandKit,
  deleteBrandKit,
  duplicateBrandKit,
  importBrandKit,
  listBrandKits,
  waitForJob,
  restoreBrandKit,
} from "@/lib/studio-api";
import { type Kit, fileFor, fontFaces, fontStack, kitSummary, logoFor, roleColour, withDefaults } from "@/lib/brand-kit";
import { UseKitMenu } from "@/components/studio/use-kit-menu";
import { cardFonts } from "@/components/studio/card-fonts";
import "./brand.css";
import { useShell } from "@/components/studio/shell";
/* eslint-disable @next/next/no-img-element */

/* r3 (2026-10-26, Mike's pick "Brand 01" on the design canvas): a hero
   with the website reader, then big cards -- the kit's background with its
   logo, its palette, its two fonts drawn in themselves, its name and how
   many projects use it. Hover (or focus) shows Duplicate, Delete and the
   Use menu. Styles: brand.css (bk-). */
function KitCard({ kit, onOpen, onCopy, onDelete }: {
  kit: Kit;
  onOpen: () => void;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const spec = withDefaults(kit.spec);
  const bg = roleColour(spec, "background", "#151514");
  const logo = fileFor(kit, logoFor(bg)) ?? fileFor(kit, "logo_light") ?? fileFor(kit, "logo_dark");
  const fonts = (kit.files ?? []).filter((f) => f.role.startsWith("font_"));
  return (
    <article
      className="bk-card"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <div className="bk-card-face" style={{ background: bg }}>
        {logo ? (
          <img src={`${API_URL}${logo.url}`} alt="" />
        ) : (
          <span className="bk-card-word" style={{ color: roleColour(spec, "primary", "#f4f3f2"), fontFamily: fontStack(kit, "heading") }}>
            {kit.name}
          </span>
        )}
        <div className="bk-card-acts" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
          <UseKitMenu kit={{ id: kit.id, name: kit.name }} buttonClassName="bk-pill bk-pill-sm" label="Use" />
          <span className="bk-grow" />
          <button type="button" className="bk-icon" title="Duplicate" aria-label={`Duplicate ${kit.name}`} onClick={onCopy}>
            <Copy size={14} strokeWidth={1.7} />
          </button>
          <button type="button" className="bk-icon" title="Delete" aria-label={`Delete ${kit.name}`} onClick={onDelete}>
            <Trash2 size={14} strokeWidth={1.7} />
          </button>
        </div>
      </div>
      <div className="bk-card-body">
        <div className="bk-swatches">
          {spec.palette.length ? (
            spec.palette.map((s, i) => <span key={i} style={{ background: s.hex }} title={`${s.role} ${s.hex}`} />)
          ) : (
            <span className="bk-swatch-none">no colours yet</span>
          )}
        </div>
        <div className="bk-card-type">
          <span className="bk-card-aa" style={{ fontFamily: fontStack(kit, "heading") }}>
            Aa
          </span>
          <small>
            {fonts.length
              ? fonts.map((f) => f.family || f.filename).filter(Boolean).join(" · ")
              : "No fonts yet"}
          </small>
        </div>
        <div className="bk-card-name">
          <b>{kit.name}</b>
          <small>
            {kit.projects ? `${kit.projects} project${kit.projects === 1 ? "" : "s"}` : "on no project"}
          </small>
        </div>
        <small className="bk-card-sum">{kitSummary(kit)}</small>
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
  const [site, setSite] = useState("");
  const [reading, setReading] = useState<{ step: string; done?: { id: number; name: string; notes: string[] }; error?: string } | null>(null);

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

  const fromSite = async () => {
    if (!site.trim() || (reading && !reading.done && !reading.error)) return;
    setReading({ step: "starting" });
    try {
      const { job_id } = await importBrandKit(site.trim());
      const job = await waitForJob(job_id, (j) => setReading({ step: j.detail || "reading the website" }), 800);
      if (job.status !== "done") throw new Error(job.error || "The website could not be read.");
      const extra = job as unknown as {
        kit_id?: number;
        kit_name?: string;
        notes?: string[];
        products?: number;
        references?: number;
      };
      const filed = [
        extra.products ? `${extra.products} product${extra.products === 1 ? "" : "s"} added to Elements` : "",
        extra.references ? `${extra.references} look reference${extra.references === 1 ? "" : "s"}` : "",
      ].filter(Boolean);
      setReading({
        step: "done",
        done: {
          id: Number(extra.kit_id ?? job.ref_id),
          name: extra.kit_name || "the new kit",
          notes: [...(filed.length ? [`From its pictures: ${filed.join(", ")}.`] : []), ...(extra.notes ?? [])],
        },
      });
      setSite("");
      load();
    } catch (e) {
      setReading({ step: "failed", error: e instanceof Error ? e.message : "The website could not be read." });
    }
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

  const fontsCss = useMemo(() => (kits ?? []).map((k) => fontFaces(k, API_URL)).join(""), [kits]);
  const busyReading = !!reading && !reading.done && !reading.error;
  const [naming, setNaming] = useState(false);
  const nameEl = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (naming) nameEl.current?.focus();
  }, [naming]);

  return (
    <section className={`view bk ${cardFonts}`}>
      {fontsCss ? <style>{fontsCss}</style> : null}
      <div className="bk-hero">
        <div className="bk-hero-copy">
          <h1 className="bk-anton">Brand kits</h1>
          <p>
            One client&rsquo;s logo, palette, fonts, look, voice and sound. A kit does nothing until a project or a chat
            picks it; then every scene takes its tone, every still and clip its look, and every export its captions and end
            card. Nothing on this page spends.
          </p>
        </div>
        <form
          className="bk-read"
          onSubmit={(e) => {
            e.preventDefault();
            void fromSite();
          }}
        >
          <div className="bk-read-bar" data-busy={busyReading ? "1" : undefined}>
            <Globe size={16} strokeWidth={1.7} />
            <input
              placeholder="https://yourbrand.com"
              value={site}
              inputMode="url"
              onChange={(e) => setSite(e.target.value)}
              aria-label="Website address"
              disabled={busyReading}
            />
            <button type="submit" className="bk-ok" disabled={!site.trim() || busyReading}>
              {busyReading ? (
                <>
                  <span className="bk-spin" aria-hidden /> Reading…
                </>
              ) : (
                "Read the site"
              )}
            </button>
          </div>
          {busyReading ? (
            <p className="bk-read-step" role="status">
              {reading?.step}…
            </p>
          ) : reading?.error ? (
            <p className="bk-read-err" role="status">
              {reading.error}
            </p>
          ) : reading?.done ? (
            <div className="bk-read-done" role="status">
              <span>
                <Check size={14} strokeWidth={2.4} /> Made <Link href={`/studio/brand/${reading.done.id}`}>{reading.done.name}</Link>. Open it
                to check the colours, and pick the brand colour if we were not sure.
              </span>
              {reading.done.notes.map((n, i) => (
                <small key={i}>{n}</small>
              ))}
            </div>
          ) : (
            <p className="bk-read-step">
              Free. Reads the site&rsquo;s colours, fonts and logo into a NEW kit; products and app screens become product
              elements, the rest look references. Use pictures you have the right to use.
            </p>
          )}
        </form>
      </div>

      {error ? <div className="stateline err">{error}</div> : null}
      <div className="bk-grid">
        {(kits ?? []).map((kit) => (
          <KitCard
            key={kit.id}
            kit={kit}
            onOpen={() => router.push(`/studio/brand/${kit.id}`)}
            onCopy={() => copy(kit)}
            onDelete={() => remove(kit)}
          />
        ))}
        {naming ? (
          <form
            className="bk-new"
            data-open="1"
            onSubmit={(e) => {
              e.preventDefault();
              create();
            }}
          >
            <b>New kit</b>
            <input
              ref={nameEl}
              className="bk-input"
              placeholder="The client's name"
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
              aria-label="New kit name"
              onKeyDown={(e) => e.key === "Escape" && setNaming(false)}
            />
            <div className="bk-row">
              <button type="submit" className="bk-ok" disabled={busy || !name.trim()}>
                {busy ? "Making…" : "Make the kit"}
              </button>
              <button type="button" className="bk-icon" aria-label="Cancel" onClick={() => setNaming(false)}>
                <X size={14} />
              </button>
            </div>
          </form>
        ) : (
          <button type="button" className="bk-new" onClick={() => setNaming(true)}>
            <Plus size={20} strokeWidth={1.8} />
            <b>Blank kit</b>
            <small>or read a website above</small>
          </button>
        )}
      </div>
      {kits && !kits.length ? (
        <p className="bk-empty">A kit is how a client looks and sounds. Read their website to start one, or make a blank kit.</p>
      ) : null}
      {!kits && !error ? <p className="bk-empty">Loading…</p> : null}
    </section>
  );
}
