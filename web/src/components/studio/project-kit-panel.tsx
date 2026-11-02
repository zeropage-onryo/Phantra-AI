"use client";

/* The project page's BRAND KIT panel (2026-11-02, Mike's pick "B2" on the
   project-page design canvas: the doors float on the cover, and under them
   a brand kit widget "that you can adjust and change").

   Everything it does goes through the routes the kit pages already use:
   - the switch turns the project's kit on or off (PUT /projects/{id}/brand-kit
     with the kit, or with null). Off remembers the kit it was, so On puts the
     same one back.
   - the picker swaps the project's kit, or makes a new one and opens it for
     editing here.
   - Edit kit changes the kit ITSELF -- name, tagline, colours, voice words --
     through PATCH /brand-kits/{id}, after the same checks the kit page makes
     (lib/brand-kit problems). A kit belongs to the account, so every project
     using it gets the change; the panel says how many do. Fonts, logos and
     the rest stay on the full kit page, which the panel links to.

   Nothing here spends. Styles: project-home.css (pj-kit-). */
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Check, ChevronDown, Pencil, Plus, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  createBrandKit,
  getProjectKit,
  listBrandKits,
  setProjectKit,
  updateBrandKit,
} from "@/lib/studio-api";
import {
  type Kit,
  type Swatch,
  LIMITS,
  fileFor,
  fontFaces,
  fontStack,
  logoFor,
  normaliseHex,
  problems,
  roleColour,
  splitList,
  withDefaults,
} from "@/lib/brand-kit";
import { useShell } from "@/components/studio/shell";

type Draft = { name: string; tagline: string; palette: Swatch[]; voice: string };

const draftOf = (kit: Kit): Draft => {
  const spec = withDefaults(kit.spec);
  return {
    name: kit.name,
    tagline: spec.identity.tagline,
    palette: spec.palette.map((s) => ({ ...s })),
    voice: spec.voice.use.join(", "),
  };
};

/** the words the Voice tile shows: the kit's "use" words, else its tone's first phrases */
function voiceWords(kit: Kit): string[] {
  const spec = withDefaults(kit.spec);
  if (spec.voice.use.length) return spec.voice.use.slice(0, 6);
  return splitList(spec.voice.tone).slice(0, 4);
}

export function ProjectKitPanel({ projectId }: { projectId: number }) {
  const { toast } = useShell();
  const [kits, setKits] = useState<Kit[] | null>(null);
  const [current, setCurrent] = useState<number | null>(null);
  // the kit the switch puts back when it is turned on again
  const [last, setLast] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    Promise.all([listBrandKits(), getProjectKit(projectId)])
      .then(([list, mine]) => {
        if (!live) return;
        setKits(list.kits);
        const id = mine.brand_kit?.id ?? null;
        setCurrent(id);
        setLast(id ?? list.kits[0]?.id ?? null);
      })
      .catch(() => live && setKits([]));
    return () => {
      live = false;
    };
  }, [projectId]);

  // the picker closes on a click outside it or on Escape
  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (menu.current && !menu.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const kit = useMemo(() => (kits ?? []).find((k) => k.id === current) ?? null, [kits, current]);
  const shownKit = kit ?? (kits ?? []).find((k) => k.id === last) ?? null;
  const fontsCss = useMemo(() => (shownKit ? fontFaces(shownKit, API_URL) : ""), [shownKit]);
  const on = current !== null;

  /** put `next` on the project (null = off); the toast carries Undo */
  const choose = async (next: number | null, quiet = false) => {
    const was = current;
    setBusy(true);
    setCurrent(next);
    if (next !== null) setLast(next);
    try {
      const got = await setProjectKit(projectId, next);
      if (!quiet)
        toast(
          got.brand_kit
            ? `${got.brand_kit.name} is on — this project's next scene, still, clip and export use it`
            : "Brand kit off — this project works without one",
          "ok",
          {
            action: {
              label: "Undo",
              run: () => setProjectKit(projectId, was).then(() => setCurrent(was)),
            },
          },
        );
    } catch (e) {
      setCurrent(was);
      toast(e instanceof Error ? e.message : "The kit was not changed", "err");
    } finally {
      setBusy(false);
    }
  };

  const toggle = () => {
    if (on) {
      setDraft(null);
      void choose(null);
    } else if (last !== null) {
      void choose(last);
    } else {
      setOpen(true); // no kit yet: the picker offers New kit
    }
  };

  const newKit = async () => {
    setOpen(false);
    setBusy(true);
    try {
      const made = await createBrandKit("Untitled kit");
      setKits((list) => [...(list ?? []), made]);
      await choose(made.id, true);
      setDraft(draftOf(made));
      setError("");
    } catch (e) {
      toast(e instanceof Error ? e.message : "The kit was not made", "err");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = () => {
    if (!kit) return;
    setOpen(false);
    setError("");
    setDraft(draftOf(kit));
  };

  const save = async () => {
    if (!kit || !draft) return;
    const palette: Swatch[] = [];
    for (const s of draft.palette) {
      const hex = normaliseHex(s.hex);
      if (!hex) {
        setError(`“${s.hex || "(empty)"}” is not a colour — use #RRGGBB`);
        return;
      }
      palette.push({ ...s, hex });
    }
    const base = withDefaults(kit.spec);
    const spec = {
      ...base,
      identity: { ...base.identity, tagline: draft.tagline.trim() },
      palette,
      voice: { ...base.voice, use: splitList(draft.voice) },
    };
    const wrong = problems(draft.name, spec);
    if (wrong.length) {
      setError(wrong[0][1].replace(/^./, (c) => c.toUpperCase()));
      return;
    }
    setBusy(true);
    try {
      const saved = await updateBrandKit(kit.id, { name: draft.name.trim(), spec });
      setKits((list) => (list ?? []).map((k) => (k.id === saved.id ? saved : k)));
      setDraft(null);
      setError("");
      toast(`${saved.name} saved`, "ok");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The kit was not saved");
    } finally {
      setBusy(false);
    }
  };

  const setSwatch = (i: number, hex: string) =>
    setDraft((d) => (d ? { ...d, palette: d.palette.map((s, j) => (j === i ? { ...s, hex } : s)) } : d));
  const addSwatch = () =>
    setDraft((d) =>
      d && d.palette.length < LIMITS.palette
        ? { ...d, palette: [...d.palette, { hex: "#FFFFFF", role: "extra", name: "" }] }
        : d,
    );
  const dropSwatch = (i: number) =>
    setDraft((d) => (d ? { ...d, palette: d.palette.filter((_, j) => j !== i) } : d));

  const editing = !!draft && on;
  const spec = shownKit ? withDefaults(shownKit.spec) : null;
  const bg = spec ? roleColour(spec, "background", "#1c1b19") : "#1c1b19";
  const logo = shownKit ? fileFor(shownKit, logoFor(bg)) ?? fileFor(shownKit, "logo_light") ?? fileFor(shownKit, "logo_dark") : undefined;
  const swatches = editing ? draft!.palette : spec?.palette ?? [];
  const others = Math.max(0, (shownKit?.projects ?? 1) - 1);

  return (
    <section className="pj-kit" aria-labelledby="pj-kit-title">
      {fontsCss ? <style>{fontsCss}</style> : null}
      <div className="pj-kit-head">
        <h2 id="pj-kit-title">Brand Kit</h2>
        <button
          type="button"
          className="pj-switch"
          role="switch"
          aria-checked={on}
          aria-label="Use a brand kit in this project"
          disabled={busy || kits === null}
          onClick={toggle}
        >
          <span className="pj-switch-track">
            <span className="pj-switch-knob" />
          </span>
          {on ? "On for this project" : "Off"}
        </button>
        <span className="pj-grow" />

        <div className="pj-kit-pick" ref={menu}>
          <button
            type="button"
            className="pj-pill"
            aria-haspopup="menu"
            aria-expanded={open}
            disabled={busy || kits === null}
            onClick={() => setOpen((v) => !v)}
          >
            {shownKit ? (
              <span className="pj-dots" aria-hidden>
                {(withDefaults(shownKit.spec).palette.slice(0, 3)).map((s, i) => (
                  <span key={i} style={{ background: s.hex }} />
                ))}
              </span>
            ) : null}
            {kits === null ? "…" : shownKit ? shownKit.name : "Pick a kit"}
            <ChevronDown size={14} strokeWidth={2.2} aria-hidden />
          </button>
          {open ? (
            <div className="pj-menu" role="menu">
              <div className="pj-menu-label">Your kits</div>
              {(kits ?? []).map((k) => {
                const ks = withDefaults(k.spec);
                return (
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={k.id === current}
                    key={k.id}
                    className="pj-menu-item"
                    onClick={() => {
                      setOpen(false);
                      setDraft(null);
                      if (k.id !== current) void choose(k.id);
                    }}
                  >
                    <span className="pj-mono" style={{ background: roleColour(ks, "primary", "#2e2d2a"), color: roleColour(ks, "text", "#f4f3f2") }}>
                      {k.name.trim().charAt(0).toUpperCase() || "K"}
                    </span>
                    <span className="pj-grow">{k.name}</span>
                    {k.id === current ? <Check size={16} strokeWidth={2.4} className="pj-check" aria-hidden /> : null}
                  </button>
                );
              })}
              {kits && !kits.length ? <p className="pj-menu-empty">No kits yet.</p> : null}
              <div className="pj-menu-rule" />
              <button type="button" role="menuitem" className="pj-menu-item" onClick={() => void newKit()}>
                <span className="pj-mono pj-mono-new">
                  <Plus size={14} strokeWidth={2.2} aria-hidden />
                </span>
                New kit
              </button>
              <Link href="/studio/brand" role="menuitem" className="pj-menu-item pj-menu-quiet">
                Manage all kits →
              </Link>
            </div>
          ) : null}
        </div>

        {on && kit ? (
          editing ? (
            <>
              <button type="button" className="pj-pill" disabled={busy} onClick={() => {
                  setDraft(null);
                  setError("");
                }}
              >
                Cancel
              </button>
              <button type="button" className="pj-pill pj-pill-on" disabled={busy} onClick={() => void save()}>
                <Check size={14} strokeWidth={2.4} aria-hidden />
                {busy ? "Saving…" : "Done"}
              </button>
            </>
          ) : (
            <button type="button" className="pj-pill" disabled={busy} onClick={startEdit}>
              <Pencil size={14} strokeWidth={2.2} aria-hidden />
              Edit kit
            </button>
          )
        ) : null}
      </div>

      {kits === null ? (
        <div className="pj-kit-grid" aria-hidden>
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="pj-tile pj-tile-wait" />
          ))}
        </div>
      ) : !on ? (
        <p className="pj-kit-off">
          {kits.length
            ? "The kit is off. Stills and scenes in this project won't use a brand's colours, fonts or voice."
            : "No brand kit yet. Make one and every still, scene and export in this project follows it."}
          {!kits.length ? (
            <button type="button" className="pj-pill pj-kit-make" disabled={busy} onClick={() => void newKit()}>
              <Plus size={14} strokeWidth={2.2} aria-hidden />
              New kit
            </button>
          ) : null}
        </p>
      ) : kit && spec ? (
        <>
          <div className="pj-kit-grid">
            <div className="pj-tile">
              <div className="pj-tile-label">Identity</div>
              <div className="pj-ident">
                <span className="pj-logo" style={{ background: bg }}>
                  {logo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={`${API_URL}${logo.url}`} alt="" />
                  ) : (
                    <span style={{ color: roleColour(spec, "primary", "#f4f3f2"), fontFamily: fontStack(kit, "heading") }}>
                      {kit.name.trim().charAt(0).toUpperCase() || "K"}
                    </span>
                  )}
                </span>
                {editing ? (
                  <div className="pj-grow pj-fields">
                    <label>
                      <span className="pj-sr">Kit name</span>
                      <input className="pj-field" value={draft!.name} maxLength={80} onChange={(e) => setDraft({ ...draft!, name: e.target.value })} />
                    </label>
                    <label>
                      <span className="pj-sr">Tagline</span>
                      <input
                        className="pj-field"
                        value={draft!.tagline}
                        placeholder="Tagline"
                        maxLength={LIMITS.tagline}
                        onChange={(e) => setDraft({ ...draft!, tagline: e.target.value })}
                      />
                    </label>
                  </div>
                ) : (
                  <div className="pj-grow pj-ident-text">
                    <strong>{kit.name}</strong>
                    <span>{spec.identity.tagline || "No tagline yet"}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pj-tile">
              <div className="pj-tile-label">Colours</div>
              {swatches.length || editing ? (
                <div className={`pj-swatches ${editing ? "pj-swatches-edit" : ""}`}>
                  {swatches.map((s, i) => (
                    <div key={i} className="pj-swatch">
                      {editing ? (
                        <>
                          <label className="pj-chip-colour" style={{ background: normaliseHex(s.hex) ?? "#000" }}>
                            <span className="pj-sr">{`Pick colour ${i + 1}`}</span>
                            <input type="color" value={(normaliseHex(s.hex) ?? "#000000").toLowerCase()} onChange={(e) => setSwatch(i, e.target.value.toUpperCase())} />
                          </label>
                          <label>
                            <span className="pj-sr">{`Colour ${i + 1} hex`}</span>
                            <input className="pj-field pj-hex" value={s.hex} onChange={(e) => setSwatch(i, e.target.value)} />
                          </label>
                          <button type="button" className="pj-x" aria-label={`Remove colour ${i + 1}`} onClick={() => dropSwatch(i)}>
                            <X size={12} strokeWidth={2.4} aria-hidden />
                          </button>
                        </>
                      ) : (
                        <>
                          <span className="pj-chip-colour" style={{ background: s.hex }} title={s.name || s.role} />
                          <span className="pj-hex-text">{s.hex}</span>
                        </>
                      )}
                    </div>
                  ))}
                  {editing && swatches.length < LIMITS.palette ? (
                    <button type="button" className="pj-swatch-add" aria-label="Add a colour" onClick={addSwatch}>
                      <Plus size={16} strokeWidth={2} aria-hidden />
                    </button>
                  ) : null}
                </div>
              ) : (
                <p className="pj-tile-empty">No colours yet.</p>
              )}
            </div>

            <div className="pj-tile">
              <div className="pj-tile-label">Type</div>
              <div className="pj-type" style={{ fontFamily: fontStack(kit, "heading"), color: roleColour(spec, "primary", "#f4f3f2") }}>
                Aa Bold
              </div>
              <div className="pj-tile-note">
                {fileFor(kit, "font_heading") || fileFor(kit, "font_body")
                  ? [fileFor(kit, "font_heading")?.family, fileFor(kit, "font_body")?.family].filter(Boolean).join(" · ") || "The kit's own fonts"
                  : "No fonts uploaded yet"}
              </div>
              <Link href={`/studio/brand/${kit.id}`} className="pj-tile-link">
                Fonts &amp; logo on the full kit →
              </Link>
            </div>

            <div className="pj-tile">
              <div className="pj-tile-label">Voice</div>
              {editing ? (
                <>
                  <label>
                    <span className="pj-sr">Voice words, comma separated</span>
                    <input className="pj-field" value={draft!.voice} placeholder="bold, warm, direct" onChange={(e) => setDraft({ ...draft!, voice: e.target.value })} />
                  </label>
                  <div className="pj-tile-note">Comma separated</div>
                </>
              ) : voiceWords(kit).length ? (
                <div className="pj-words">
                  {voiceWords(kit).map((w) => (
                    <span key={w}>{w}</span>
                  ))}
                </div>
              ) : (
                <p className="pj-tile-empty">No voice yet.</p>
              )}
            </div>
          </div>
          {editing ? (
            <p className={`pj-kit-note ${error ? "pj-kit-err" : ""}`} role={error ? "alert" : undefined}>
              {error ||
                `Changes save to the kit itself${others ? `, so the ${others} other project${others === 1 ? "" : "s"} using ${kit.name} get them too` : ""}.`}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
