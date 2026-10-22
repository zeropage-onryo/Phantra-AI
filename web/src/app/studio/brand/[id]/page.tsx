"use client";

/* One brand kit (2026-10-20, docs/tasks/task-brand-kit.md §7).

   A form column and a live preview, like the studio's other making pages:
   identity, visual, look, voice, sound, products and characters on the
   left; on the right the palette, a caption in the kit's own font and
   colours, the end card exactly as an export draws it (the API's Pillow
   drawing, free), and the line every still, keyframe and clip gains.

   Files go up the moment they are dropped (the kit already exists); the
   fields save with Save. An SVG logo is drawn to a PNG here, in the
   browser -- the PNG is what renders, the SVG is kept beside it. A font
   needs the person to say they may embed it in video (the licence rule
   Canva and Adobe Express both state). Nothing on this page spends.

   A kit imported from a website (2026-10-21) also carries how sure the
   import was of each colour: a chip per swatch, its reason on click, and a
   "Which is your brand colour?" pick when the primary is not certain. The
   contrast lines are worked out here from the palette and stored nowhere. */
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Copy, ImagePlus, Plus, Trash2, Upload, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  deleteBrandKit,
  duplicateBrandKit,
  endCardUrl,
  getAssets,
  getBrandKit,
  removeKitFile,
  restoreBrandKit,
  updateBrandKit,
  uploadKitFile,
  type Asset,
} from "@/lib/studio-api";
import {
  FILE_SLOTS,
  LIMITS,
  PALETTE_ROLES,
  type Kit,
  type KitFile,
  type KitSpec,
  type PaletteRole,
  CONTRAST_MIN,
  contrastChecks,
  evidenceFor,
  fileFor,
  formatAesthetics,
  parseAesthetics,
  primaryChoices,
  splitLines,
  fontFaces,
  captionSample,
  fontStack,
  isFontRole,
  isSvg,
  normaliseHex,
  problems,
  roleColour,
  splitList,
  withDefaults,
} from "@/lib/brand-kit";
import { useShell } from "@/components/studio/shell";
/* eslint-disable @next/next/no-img-element */

const BTN = "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] transition disabled:opacity-40";
const PRI = `${BTN} bg-white text-black! hover:bg-white/90 disabled:bg-white/15 disabled:text-white/40! disabled:opacity-100`;
const GHOST = `${BTN} border border-white/15 text-white/80 hover:border-white/40`;
const FIELD =
  "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white/90 outline-none focus:border-white/30";
const LABEL = "mb-1 block text-[11px] uppercase tracking-wide text-white/40";
const HINT = "text-[12px] leading-relaxed text-white/40";
const CARD = "flex flex-col gap-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 sm:p-5";
const ROLES_NO_EXTRA = PALETTE_ROLES.filter((r) => r !== "extra") as Exclude<PaletteRole, "extra">[];
// the editor's transitions most kits want; the API takes any of the 58
const TRANSITIONS: [string, string][] = [
  ["fade", "Crossfade"], ["dissolve", "Dissolve"], ["fadeblack", "Dip to black"], ["fadewhite", "Dip to white"],
  ["slideleft", "Slide left"], ["slideright", "Slide right"], ["slideup", "Slide up"], ["smoothleft", "Smooth left"],
  ["wipeleft", "Wipe left"], ["circleopen", "Circle open"],
];
const ASPECTS = ["16:9", "9:16", "1:1"] as const;

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className={CARD}>
      <header className="flex flex-col gap-1">
        <h2 className="text-[15px] font-semibold text-white/90">{title}</h2>
        {hint ? <p className={HINT}>{hint}</p> : null}
      </header>
      {children}
    </section>
  );
}

function Field({ label, children, note }: { label: string; children: React.ReactNode; note?: string }) {
  return (
    <label className="block">
      <span className={LABEL}>{label}</span>
      {children}
      {note ? <span className={`${HINT} mt-1 block`}>{note}</span> : null}
    </label>
  );
}

function RoleSelect<T extends string>({ value, onChange, options, label }: {
  value: T;
  onChange: (v: T) => void;
  options: readonly T[];
  label: string;
}) {
  return (
    <select className={FIELD} value={value} aria-label={label} onChange={(e) => onChange(e.target.value as T)}>
      {options.map((o) => (
        <option key={o} value={o}>
          {o.replace("_", " ")}
        </option>
      ))}
    </select>
  );
}

/** an SVG file drawn to a PNG no wider or taller than 2048px */
async function svgToPng(file: File): Promise<Blob> {
  const text = await file.text();
  const url = URL.createObjectURL(new Blob([text], { type: "image/svg+xml" }));
  try {
    const img = new Image();
    await new Promise<void>((ok, fail) => {
      img.onload = () => ok();
      img.onerror = () => fail(new Error("that SVG does not draw"));
      img.src = url;
    });
    const w0 = img.naturalWidth || 1024;
    const h0 = img.naturalHeight || 1024;
    const scale = 2048 / Math.max(w0, h0);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(w0 * scale);
    canvas.height = Math.round(h0 * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((ok, fail) =>
      canvas.toBlob((b) => (b ? ok(b) : fail(new Error("that SVG does not draw"))), "image/png"),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}

function FileSlot({ kit, role, label, accept, onUpload, onRemove, busy }: {
  kit: Kit;
  role: string;
  label: string;
  accept: string;
  onUpload: (role: string, file: File, licensed: boolean) => void;
  onRemove: (f: KitFile) => void;
  busy: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [licensed, setLicensed] = useState(false);
  const file = fileFor(kit, role);
  const font = isFontRole(role);
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-white/10 bg-black/30 p-3">
      <span className={LABEL}>{label}</span>
      <div className="flex min-h-14 items-center gap-3">
        {file ? (
          font ? (
            <span className="text-[20px] text-white/90" style={{ fontFamily: fontStack(kit, role === "font_heading" ? "heading" : "body") }}>
              {file.family || file.filename} · Aa Bb 123
            </span>
          ) : (
            <span className="flex h-14 w-full items-center justify-center rounded-md" style={{ background: role === "logo_dark" ? "#111" : "#f4f3f2" }}>
              <img src={`${API_URL}${file.url}`} alt={label} className="max-h-12 max-w-[85%] object-contain" />
            </span>
          )
        ) : (
          <span className={HINT}>{font ? "TTF or OTF" : "PNG, WebP or SVG"}</span>
        )}
      </div>
      {font ? (
        <label className="flex items-start gap-2 text-[12px] text-white/60">
          <input type="checkbox" checked={licensed} onChange={(e) => setLicensed(e.target.checked)} className="mt-0.5" />
          I have the right to embed this font in video (its licence allows it).
        </label>
      ) : null}
      <div className="flex gap-2">
        <button
          type="button"
          className={GHOST}
          disabled={busy || (font && !licensed)}
          onClick={() => input.current?.click()}
        >
          <Upload size={13} /> {file ? "Replace" : "Upload"}
        </button>
        {file ? (
          <button type="button" className={GHOST} onClick={() => onRemove(file)} disabled={busy}>
            <X size={13} /> Remove
          </button>
        ) : null}
      </div>
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (f) onUpload(role, f, licensed);
        }}
      />
    </div>
  );
}

function ElementPicker({ title, items, picked, onToggle, claims, onClaims }: {
  title: string;
  items: Asset[];
  picked: number[];
  onToggle: (id: number, name: string) => void;
  claims?: Record<number, string>;
  onClaims?: (id: number, text: string) => void;
}) {
  if (!items.length) return <p className={HINT}>No {title.toLowerCase()} in Elements yet.</p>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((a) => {
        const id = Number(a.id.split("-").pop());
        const on = picked.includes(id);
        return (
          <div key={a.id} className="flex flex-col gap-2 rounded-lg border border-white/10 bg-black/30 p-2.5">
            <label className="flex items-center gap-2 text-[13px] text-white/85">
              <input type="checkbox" checked={on} onChange={() => onToggle(id, a.name)} />
              {a.name}
            </label>
            {on && onClaims ? (
              <input
                className={FIELD}
                placeholder="Claims allowed about it, comma-separated (none = make no claims)"
                value={claims?.[id] ?? ""}
                onChange={(e) => onClaims(id, e.target.value)}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export default function BrandKitPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useShell();
  const [kit, setKit] = useState<Kit | null>(null);
  const [name, setName] = useState("");
  const [spec, setSpec] = useState<KitSpec>(withDefaults(null));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aspect, setAspect] = useState<(typeof ASPECTS)[number]>("16:9");
  const [elements, setElements] = useState<Asset[]>([]);
  // list fields are edited as text and split on save, so a comma typed is never eaten
  const [lists, setLists] = useState({ banned: "", use: "", avoid: "", never: "", selling: "", aesthetics: "" });
  const [why, setWhy] = useState<string | null>(null);
  const [claims, setClaims] = useState<Record<number, string>>({});
  const refInput = useRef<HTMLInputElement>(null);
  const musicInput = useRef<HTMLInputElement>(null);

  const adopt = (k: Kit, keepFields = false) => {
    setKit(k);
    if (keepFields) return;
    const s = withDefaults(k.spec);
    setName(k.name);
    setSpec(s);
    setLists({
      banned: s.look.banned.join(", "),
      use: s.voice.use.join(", "),
      avoid: s.voice.avoid.join(", "),
      never: s.never_claim.join(", "),
      selling: s.identity.selling_points.join("\n"),
      aesthetics: formatAesthetics(s.look.aesthetics),
    });
    setClaims(Object.fromEntries(s.products.map((p) => [p.id, (p.claims ?? []).join(", ")])));
    setDirty(false);
  };

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    getBrandKit(id)
      .then((k) => adopt(k))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the kit"));
    getAssets(undefined, "elements")
      .then((r) => setElements(r.items))
      .catch(() => setElements([]));
  }, [id]);

  const edit = (change: (s: KitSpec) => KitSpec) => {
    setSpec((s) => change(structuredClone(s)));
    setDirty(true);
  };

  const composed = (): KitSpec => ({
    ...spec,
    identity: { ...spec.identity, selling_points: splitLines(lists.selling) },
    look: { ...spec.look, banned: splitList(lists.banned), aesthetics: parseAesthetics(lists.aesthetics) },
    voice: { ...spec.voice, use: splitList(lists.use), avoid: splitList(lists.avoid) },
    never_claim: splitList(lists.never),
    products: spec.products.map((p) => ({ ...p, claims: splitList(claims[p.id] ?? "") })),
  });
  const issues = problems(name, composed());

  const save = () => {
    if (issues.length) return;
    setSaving(true);
    updateBrandKit(id, { name: name.trim(), spec: composed() })
      .then((k) => {
        adopt(k);
        toast("Kit saved · projects on it use it from the next scene, still, clip and export");
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not save", "err"))
      .finally(() => setSaving(false));
  };

  const upload = async (role: string, file: File, licensed: boolean) => {
    setBusy(true);
    try {
      let last: Kit | null = null;
      if (isSvg(file) && role.startsWith("logo_")) {
        const png = await svgToPng(file);
        last = (await uploadKitFile(id, role, png, file.name.replace(/\.svg$/i, ".png"))).kit;
        last = (await uploadKitFile(id, `${role}_source`, file, file.name)).kit;
      } else {
        last = (await uploadKitFile(id, role, file, file.name, licensed)).kit;
      }
      if (last) adopt(last, dirty);
      toast(`${file.name} added`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not upload", "err");
    } finally {
      setBusy(false);
    }
  };

  const removeFile = (f: KitFile) =>
    removeKitFile(id, f.id)
      .then((r) => r.kit && adopt(r.kit, dirty))
      .catch((e) => toast(e instanceof Error ? e.message : "Could not remove", "err"));

  const fontsCss = useMemo(() => (kit ? fontFaces(kit, API_URL) : ""), [kit]);
  const references = (kit?.files ?? []).filter((f) => f.role === "reference");
  const music = (kit?.files ?? []).filter((f) => f.role === "music_ref");
  const props = elements.filter((a) => a.id.startsWith("prop-"));
  const cast = elements.filter((a) => a.id.startsWith("character-"));
  const cap = spec.captions;
  const capFill = roleColour(spec, cap.fill, "#FFFFFF");
  const capBox = cap.box === "none" ? "transparent" : roleColour(spec, cap.box, "#000000");
  const capOutline = cap.outline === "none" ? null : roleColour(spec, cap.outline, "#000000");
  const capPos = { bottom: "flex-end", lower_third: "flex-end", top: "flex-start" }[cap.position];
  const contrast = contrastChecks(spec);
  const choices = primaryChoices(spec);
  const setPrimary = (hex: string) => edit((s) => {
    const at = s.palette.findIndex((p) => p.role === "primary");
    const same = s.palette.findIndex((p) => normaliseHex(p.hex) === hex);
    if (same >= 0 && same !== at) {
      if (at >= 0) s.palette[at].role = s.palette[same].role === "primary" ? "extra" : s.palette[same].role;
      s.palette[same].role = "primary";
    } else if (at >= 0) s.palette[at].hex = hex;
    else s.palette.unshift({ hex, role: "primary", name: "" });
    if (s.import?.roles?.primary) s.import.roles.primary = { why: "picked on the kit page", confidence: "high" };
    return s;
  });

  if (error) {
    return (
      <section className="view">
        <div className="stateline err" style={{ padding: "14px 42px" }}>{error}</div>
      </section>
    );
  }
  if (!kit) return <section className="view"><span className="m" style={{ padding: 24 }}>loading…</span></section>;

  return (
    <section className="view" style={{ paddingTop: 0 }}>
      {fontsCss ? <style>{fontsCss}</style> : null}
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-5 sm:px-8">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={GHOST} onClick={() => router.push("/studio/brand")}>
            <ArrowLeft size={13} /> Kits
          </button>
          <input
            className={`${FIELD} max-w-sm text-[15px] font-semibold`}
            value={name}
            maxLength={80}
            aria-label="Kit name"
            onChange={(e) => {
              setName(e.target.value);
              setDirty(true);
            }}
          />
          <span className="flex-1" />
          <button
            type="button"
            className={GHOST}
            onClick={() =>
              duplicateBrandKit(id)
                .then((k) => router.push(`/studio/brand/${k.id}`))
                .catch((e) => toast(e instanceof Error ? e.message : "Could not duplicate", "err"))
            }
          >
            <Copy size={13} /> Duplicate
          </button>
          <button
            type="button"
            className={GHOST}
            onClick={() =>
              deleteBrandKit(id)
                .then(() => {
                  toast(`${kit.name} deleted`, "ok", { action: { label: "Undo", run: () => restoreBrandKit(id) } });
                  router.push("/studio/brand");
                })
                .catch((e) => toast(e instanceof Error ? e.message : "Could not delete", "err"))
            }
          >
            <Trash2 size={13} /> Delete
          </button>
          <button type="button" className={PRI} disabled={!dirty || saving || issues.length > 0} onClick={save}>
            {saving ? "Saving…" : dirty ? "Save" : "Saved"}
          </button>
        </div>
        {issues.length && dirty ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-[13px] text-amber-100">
            {issues.map(([f, m]) => `${f}: ${m}`).join(" · ")}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Section title="Identity" hint="The logo and lines the end card and the writer use.">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {FILE_SLOTS.filter((s) => s.role.startsWith("logo_")).map((s) => (
                  <FileSlot key={s.role} kit={kit} {...s} onUpload={upload} onRemove={removeFile} busy={busy} />
                ))}
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Tagline">
                  <input className={FIELD} maxLength={LIMITS.tagline} value={spec.identity.tagline}
                    onChange={(e) => edit((s) => ({ ...s, identity: { ...s.identity, tagline: e.target.value } }))} />
                </Field>
                <Field label="Website (end card)">
                  <input className={FIELD} maxLength={120} value={spec.identity.url} placeholder="example.com"
                    onChange={(e) => edit((s) => ({ ...s, identity: { ...s.identity, url: e.target.value } }))} />
                </Field>
                <Field label="Positioning (one line)">
                  <input className={FIELD} maxLength={LIMITS.line} value={spec.identity.positioning}
                    onChange={(e) => edit((s) => ({ ...s, identity: { ...s.identity, positioning: e.target.value } }))} />
                </Field>
                <Field label="Audience (one line)">
                  <input className={FIELD} maxLength={LIMITS.line} value={spec.identity.audience}
                    onChange={(e) => edit((s) => ({ ...s, identity: { ...s.identity, audience: e.target.value } }))} />
                </Field>
              </div>
              <Field label={`Selling points · up to ${LIMITS.sellingPoints}`}
                note={`One per line, ${LIMITS.sellingPoint} characters each. The writer and the brain lean on them.`}>
                <textarea className={`${FIELD} min-h-20`} value={lists.selling}
                  placeholder={"Vetted staff within 24 hours\nOne rate, no agency fee"}
                  onChange={(e) => { setLists((l) => ({ ...l, selling: e.target.value })); setDirty(true); }} />
              </Field>
            </Section>

            <Section title="Visual" hint="Colours by role, two fonts, how captions look, and the end card.">
              <div className="flex flex-col gap-2">
                <span className={LABEL}>Palette</span>
                {spec.palette.map((sw, i) => (
                  <div key={i} className="grid grid-cols-[40px_1fr_1fr_1fr_auto_auto] items-center gap-2">
                    <input
                      type="color"
                      aria-label={`Colour ${i + 1}`}
                      value={normaliseHex(sw.hex) ?? "#000000"}
                      className="h-9 w-10 cursor-pointer rounded border border-white/10 bg-transparent"
                      onChange={(e) => edit((s) => { s.palette[i].hex = e.target.value.toUpperCase(); return s; })}
                    />
                    <input className={FIELD} value={sw.hex} aria-label={`Hex ${i + 1}`}
                      onChange={(e) => edit((s) => { s.palette[i].hex = e.target.value; return s; })}
                      onBlur={(e) => { const n = normaliseHex(e.target.value); if (n) edit((s) => { s.palette[i].hex = n; return s; }); }} />
                    <RoleSelect label={`Role ${i + 1}`} value={sw.role} options={PALETTE_ROLES}
                      onChange={(v) => edit((s) => { s.palette[i].role = v; return s; })} />
                    <input className={FIELD} value={sw.name} placeholder="name (orange)" maxLength={40}
                      onChange={(e) => edit((s) => { s.palette[i].name = e.target.value; return s; })} />
                    {(() => {
                      const ev = sw.role === "extra" ? null : evidenceFor(spec, sw.role);
                      if (!ev) return <span />;
                      const key = `${i}-${sw.role}`;
                      return (
                        <button type="button" onClick={() => setWhy(why === key ? null : key)}
                          title={ev.why || "no reason recorded"} aria-expanded={why === key}
                          className={`rounded-full border px-2 py-0.5 text-[10.5px] ${ev.confidence === "high"
                            ? "border-white/20 text-white/70" : "border-amber-400/40 text-amber-200"}`}>
                          {ev.confidence}
                        </button>
                      );
                    })()}
                    <button type="button" className="zdx" aria-label={`Remove colour ${i + 1}`}
                      onClick={() => edit((s) => { s.palette.splice(i, 1); return s; })}>
                      <X size={13} />
                    </button>
                  </div>
                ))}
                {why ? (() => {
                  const [at, role] = why.split("-");
                  const ev = evidenceFor(spec, role);
                  return ev && spec.palette[Number(at)] ? (
                    <p className={`${HINT} rounded-md bg-black/30 px-3 py-2`}>
                      <b className="text-white/70">{role}</b>, {ev.confidence} confidence: {ev.why || "no reason recorded"}
                      {spec.import?.source ? ` · from ${spec.import.source}` : ""}
                    </p>
                  ) : null;
                })() : null}
                {choices.length ? (
                  <div className="flex flex-col gap-2 rounded-lg border border-amber-400/30 bg-amber-400/5 p-3">
                    <span className="text-[13px] text-white/85">Which is your brand colour?</span>
                    <span className={HINT}>The import was not sure. Pick the one your brand leads with.</span>
                    <div className="flex flex-wrap gap-2">
                      {choices.map((c) => {
                        const on = normaliseHex(spec.palette.find((p) => p.role === "primary")?.hex ?? "") === c.hex;
                        return (
                          <button key={c.hex} type="button" onClick={() => setPrimary(c.hex)} title={c.why}
                            className={`inline-flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[12px] ${on
                              ? "border-[var(--signal)] text-white" : "border-white/15 text-white/70"}`}>
                            <span className="h-4 w-4 rounded" style={{ background: c.hex }} />
                            {c.hex}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
                {contrast.length ? (
                  <div className="flex flex-col gap-1.5">
                    <span className={LABEL}>Text contrast · WCAG wants {CONTRAST_MIN}:1</span>
                    {contrast.map((c) => (
                      <div key={`${c.fgIndex}-${c.bg}`} className="flex flex-wrap items-center gap-2 text-[12.5px]">
                        <span className="inline-flex h-7 items-center rounded px-2 font-semibold" style={{ background: c.bg, color: c.fg }}>Aa</span>
                        <span className={c.ok ? "text-white/60" : "text-amber-200"}>
                          {c.label} · {c.ratio.toFixed(2)}:1{c.ok ? "" : " — hard to read"}
                        </span>
                        {!c.ok ? (
                          <button type="button" className={GHOST}
                            onClick={() => edit((s) => { s.palette[c.fgIndex].hex = c.alternative.hex; return s; })}>
                            <span className="h-3 w-3 rounded-sm border border-white/30" style={{ background: c.alternative.hex }} />
                            Use {c.alternative.hex} · {c.alternative.ratio.toFixed(2)}:1
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
                {spec.palette.length < LIMITS.palette ? (
                  <button type="button" className={`${GHOST} self-start`}
                    onClick={() => edit((s) => {
                      const free = ROLES_NO_EXTRA.find((r) => !s.palette.some((p) => p.role === r)) ?? "extra";
                      s.palette.push({ hex: "#FFFFFF", role: free, name: "" });
                      return s;
                    })}>
                    <Plus size={13} /> Add colour
                  </button>
                ) : null}
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {FILE_SLOTS.filter((s) => isFontRole(s.role)).map((s) => (
                  <FileSlot key={s.role} kit={kit} {...s} onUpload={upload} onRemove={removeFile} busy={busy} />
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="Caption font">
                  <RoleSelect label="Caption font" value={cap.font} options={["heading", "body"] as const}
                    onChange={(v) => edit((s) => ({ ...s, captions: { ...s.captions, font: v } }))} />
                </Field>
                <Field label="Caption colour">
                  <RoleSelect label="Caption colour" value={cap.fill} options={ROLES_NO_EXTRA}
                    onChange={(v) => edit((s) => ({ ...s, captions: { ...s.captions, fill: v } }))} />
                </Field>
                <Field label="Box behind">
                  <RoleSelect label="Box behind" value={cap.box} options={["none", ...ROLES_NO_EXTRA] as const}
                    onChange={(v) => edit((s) => ({ ...s, captions: { ...s.captions, box: v } }))} />
                </Field>
                <Field label="Outline">
                  <RoleSelect label="Outline" value={cap.outline} options={["none", ...ROLES_NO_EXTRA] as const}
                    onChange={(v) => edit((s) => ({ ...s, captions: { ...s.captions, outline: v } }))} />
                </Field>
                <Field label="Position">
                  <RoleSelect label="Position" value={cap.position} options={["bottom", "lower_third", "top"] as const}
                    onChange={(v) => edit((s) => ({ ...s, captions: { ...s.captions, position: v } }))} />
                </Field>
                <Field label={`Size · ${(cap.size * 100).toFixed(1)}% of height`}>
                  <input type="range" min={0.025} max={0.1} step={0.005} value={cap.size} className="w-full"
                    onChange={(e) => edit((s) => ({ ...s, captions: { ...s.captions, size: Number(e.target.value) } }))} />
                </Field>
                <Field label={`Safe zone · ${Math.round(spec.safe_zone * 100)}%`}>
                  <input type="range" min={0} max={0.2} step={0.01} value={spec.safe_zone} className="w-full"
                    onChange={(e) => edit((s) => ({ ...s, safe_zone: Number(e.target.value) }))} />
                </Field>
                <label className="flex items-center gap-2 self-end pb-2 text-[13px] text-white/75">
                  <input type="checkbox" checked={cap.uppercase}
                    onChange={(e) => edit((s) => ({ ...s, captions: { ...s.captions, uppercase: e.target.checked } }))} />
                  Uppercase
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="End card">
                  <select className={FIELD} value={spec.end_card.on ? "on" : "off"}
                    onChange={(e) => edit((s) => ({ ...s, end_card: { ...s.end_card, on: e.target.value === "on" } }))}>
                    <option value="on">On every export</option>
                    <option value="off">Off</option>
                  </select>
                </Field>
                <Field label={`Card length · ${spec.end_card.seconds}s`}>
                  <input type="range" min={1} max={6} step={0.5} value={spec.end_card.seconds} className="w-full"
                    onChange={(e) => edit((s) => ({ ...s, end_card: { ...s.end_card, seconds: Number(e.target.value) } }))} />
                </Field>
                <Field label="Card background">
                  <RoleSelect label="Card background" value={spec.end_card.background} options={ROLES_NO_EXTRA}
                    onChange={(v) => edit((s) => ({ ...s, end_card: { ...s.end_card, background: v } }))} />
                </Field>
                <Field label="Transition in">
                  <select className={FIELD} value={spec.motion.transition}
                    onChange={(e) => edit((s) => ({ ...s, motion: { ...s.motion, transition: e.target.value } }))}>
                    {TRANSITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    {!TRANSITIONS.some(([v]) => v === spec.motion.transition) ? (
                      <option value={spec.motion.transition}>{spec.motion.transition}</option>
                    ) : null}
                  </select>
                </Field>
                <Field label="Default export shape">
                  <select className={FIELD} value={spec.aspect}
                    onChange={(e) => edit((s) => ({ ...s, aspect: e.target.value as KitSpec["aspect"] }))}>
                    <option value="">Keep the cut&rsquo;s</option>
                    {ASPECTS.map((a) => <option key={a} value={a}>{a}</option>)}
                  </select>
                </Field>
                <label className="flex items-center gap-2 self-end pb-2 text-[13px] text-white/75">
                  <input type="checkbox" checked={spec.end_card.show_url}
                    onChange={(e) => edit((s) => ({ ...s, end_card: { ...s.end_card, show_url: e.target.checked } }))} />
                  Website on the card
                </label>
              </div>
            </Section>

            <Section title="Look" hint="Added to every still, keyframe and clip a project on this kit renders. Up to 8 reference images; a keyframe carries the first three, after the scene's own photos.">
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
                {references.map((f) => (
                  <div key={f.id} className="group relative aspect-square overflow-hidden rounded-md border border-white/10">
                    <img src={`${API_URL}${f.url}`} alt="" className="h-full w-full object-cover" />
                    <button type="button" className="zdx absolute top-1 right-1 bg-black/70 opacity-0 group-hover:opacity-100"
                      aria-label="Remove reference" onClick={() => removeFile(f)}>
                      <X size={12} />
                    </button>
                  </div>
                ))}
                {references.length < LIMITS.references ? (
                  <button type="button" disabled={busy}
                    className="flex aspect-square items-center justify-center rounded-md border border-dashed border-white/20 text-white/50 hover:border-white/40"
                    onClick={() => refInput.current?.click()} aria-label="Add reference images">
                    <ImagePlus size={18} strokeWidth={1.5} />
                  </button>
                ) : null}
              </div>
              <input ref={refInput} type="file" accept="image/*" multiple hidden
                onChange={async (e) => {
                  const files = Array.from(e.target.files ?? []).slice(0, LIMITS.references - references.length);
                  e.target.value = "";
                  for (const f of files) await upload("reference", f, false);
                }} />
              <Field label={`Style description · ${spec.look.style.length}/${LIMITS.style}`}>
                <textarea className={`${FIELD} min-h-24`} maxLength={LIMITS.style} value={spec.look.style}
                  placeholder="Warm orange-on-cream, soft daylight, clean rounded UI surfaces, generous negative space."
                  onChange={(e) => edit((s) => ({ ...s, look: { ...s.look, style: e.target.value } }))} />
              </Field>
              <Field label="Banned elements" note="Comma-separated. Never written into a scene, and sent as Avoid: on every render.">
                <input className={FIELD} value={lists.banned}
                  onChange={(e) => { setLists((l) => ({ ...l, banned: e.target.value })); setDirty(true); }} />
              </Field>
              <Field label={`Aesthetics · up to ${LIMITS.aesthetics}`}
                note="One per line, as tag: why it fits. The tags ride on the look line.">
                <textarea className={`${FIELD} min-h-20`} value={lists.aesthetics}
                  placeholder={"warm minimal: cream backgrounds and one orange\nfriendly: rounded type, real people"}
                  onChange={(e) => { setLists((l) => ({ ...l, aesthetics: e.target.value })); setDirty(true); }} />
              </Field>
            </Section>

            <Section title="Voice" hint="How the writer and the brain speak for this brand.">
              <Field label={`Tone rules · ${spec.voice.tone.length}/${LIMITS.tone}`}>
                <textarea className={`${FIELD} min-h-20`} maxLength={LIMITS.tone} value={spec.voice.tone}
                  onChange={(e) => edit((s) => ({ ...s, voice: { ...s.voice, tone: e.target.value } }))} />
              </Field>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Words to use">
                  <input className={FIELD} value={lists.use}
                    onChange={(e) => { setLists((l) => ({ ...l, use: e.target.value })); setDirty(true); }} />
                </Field>
                <Field label="Words never to use">
                  <input className={FIELD} value={lists.avoid}
                    onChange={(e) => { setLists((l) => ({ ...l, avoid: e.target.value })); setDirty(true); }} />
                </Field>
              </div>
              <Field label="Call-to-action style">
                <input className={FIELD} maxLength={LIMITS.cta} value={spec.voice.cta}
                  onChange={(e) => edit((s) => ({ ...s, voice: { ...s.voice, cta: e.target.value } }))} />
              </Field>
            </Section>

            <Section title="Sound" hint="Stored with the kit now; the audio layer reads it when it lands. Exports stay at -14 LUFS until then.">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="Default voice">
                  <input className={FIELD} maxLength={LIMITS.line} value={spec.sound.voice} placeholder="warm, unhurried, female"
                    onChange={(e) => edit((s) => ({ ...s, sound: { ...s.sound, voice: e.target.value } }))} />
                </Field>
                <Field label="Music genre">
                  <input className={FIELD} maxLength={80} value={spec.sound.music.genre}
                    onChange={(e) => edit((s) => ({ ...s, sound: { ...s.sound, music: { ...s.sound.music, genre: e.target.value } } }))} />
                </Field>
                <Field label="BPM">
                  <input className={FIELD} type="number" min={40} max={220} value={spec.sound.music.bpm ?? ""}
                    onChange={(e) => edit((s) => ({ ...s, sound: { ...s.sound, music: { ...s.sound.music, bpm: e.target.value ? Number(e.target.value) : null } } }))} />
                </Field>
                <Field label="Loudness target (LUFS)">
                  <input className={FIELD} type="number" min={-30} max={-6} step={0.5} value={spec.sound.loudness ?? ""}
                    onChange={(e) => edit((s) => ({ ...s, sound: { ...s.sound, loudness: e.target.value ? Number(e.target.value) : null } }))} />
                </Field>
              </div>
              <Field label="Music mood">
                <input className={FIELD} maxLength={LIMITS.line} value={spec.sound.music.mood}
                  onChange={(e) => edit((s) => ({ ...s, sound: { ...s.sound, music: { ...s.sound.music, mood: e.target.value } } }))} />
              </Field>
              <div className="flex flex-wrap items-center gap-2">
                {music.map((f) => (
                  <span key={f.id} className="inline-flex items-center gap-1.5 rounded-full border border-white/15 px-2.5 py-1 text-[12px] text-white/70">
                    {f.filename || "reference track"}
                    <button type="button" aria-label="Remove track" onClick={() => removeFile(f)}><X size={11} /></button>
                  </span>
                ))}
                {music.length < 3 ? (
                  <button type="button" className={GHOST} disabled={busy} onClick={() => musicInput.current?.click()}>
                    <Upload size={13} /> Reference track
                  </button>
                ) : null}
                <input ref={musicInput} type="file" accept="audio/mpeg,audio/mp4,audio/wav,.mp3,.m4a,.wav" hidden
                  onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) upload("music_ref", f, false); }} />
              </div>
            </Section>

            <Section title="Products & characters" hint="Linked from Elements -- nothing is re-uploaded. The writer names them, and keeps product claims to the ones allowed here.">
              <span className={LABEL}>Products</span>
              <ElementPicker
                title="Products"
                items={props}
                picked={spec.products.map((p) => p.id)}
                claims={claims}
                onClaims={(pid, text) => { setClaims((c) => ({ ...c, [pid]: text })); setDirty(true); }}
                onToggle={(pid, pname) => edit((s) => {
                  const at = s.products.findIndex((p) => p.id === pid);
                  if (at >= 0) s.products.splice(at, 1);
                  else s.products.push({ kind: "prop", id: pid, name: pname, claims: [] });
                  return s;
                })}
              />
              <Field label="Claims never to make" note="Comma-separated.">
                <input className={FIELD} value={lists.never}
                  onChange={(e) => { setLists((l) => ({ ...l, never: e.target.value })); setDirty(true); }} />
              </Field>
              <span className={LABEL}>Recurring characters</span>
              <ElementPicker
                title="Characters"
                items={cast}
                picked={spec.characters.map((c) => c.id)}
                onToggle={(cid, cname) => edit((s) => {
                  const at = s.characters.findIndex((c) => c.id === cid);
                  if (at >= 0) s.characters.splice(at, 1);
                  else s.characters.push({ kind: "character", id: cid, name: cname });
                  return s;
                })}
              />
            </Section>
          </div>

          <aside className="flex flex-col gap-4 lg:sticky lg:top-4 lg:self-start">
            <div className={CARD}>
              <span className={LABEL}>Palette</span>
              <div className="flex h-10 overflow-hidden rounded-md">
                {spec.palette.length ? spec.palette.map((s, i) => (
                  <span key={i} className="flex flex-1 items-end p-1 text-[9px]" style={{ background: normaliseHex(s.hex) ?? "#000", color: "#0008" }}>
                    {s.role}
                  </span>
                )) : <span className={HINT}>No colours yet.</span>}
              </div>
              <span className={LABEL}>Caption</span>
              <div
                className="relative flex aspect-video flex-col items-center rounded-md p-3"
                style={{
                  background: "linear-gradient(135deg,#3a3935,#151514)",
                  justifyContent: capPos,
                  alignItems: cap.position === "lower_third" ? "flex-start" : "center",
                  paddingBottom: cap.position === "bottom" ? `${(spec.safe_zone + 0.06) * 100}%` : undefined,
                }}
              >
                <span
                  style={{
                    fontFamily: fontStack(kit, cap.font),
                    color: capFill,
                    background: capBox,
                    padding: cap.box === "none" ? 0 : "2px 8px",
                    fontSize: `${Math.max(10, cap.size * 200)}px`,
                    fontWeight: 700,
                    textTransform: cap.uppercase ? "uppercase" : "none",
                    WebkitTextStroke: capOutline ? `1px ${capOutline}` : undefined,
                  }}
                >
                  {captionSample(spec)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={LABEL} style={{ marginBottom: 0 }}>End card</span>
                <span className="flex-1" />
                {ASPECTS.map((a) => (
                  <button key={a} type="button" onClick={() => setAspect(a)}
                    className={`rounded-md px-2 py-0.5 text-[11px] ${aspect === a ? "bg-white/15 text-white" : "text-white/50"}`}>
                    {a}
                  </button>
                ))}
              </div>
              <img
                key={`${kit.hash}-${aspect}`}
                src={endCardUrl(kit.id, aspect, kit.hash)}
                alt="The end card as an export draws it"
                className="mx-auto max-h-80 rounded-md border border-white/10 object-contain"
              />
              <p className={HINT}>Drawn from the saved kit{dirty ? " — save to see your changes" : ""}.</p>
              <span className={LABEL}>Added to every still, keyframe and clip</span>
              <pre className="whitespace-pre-wrap rounded-md bg-black/40 p-2 text-[11.5px] leading-relaxed text-white/70">
                {kit.look_suffix || "Nothing yet — write a style description, add colours or banned elements."}
              </pre>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
