"use client";

/* The Ad Studio (2026-10-26, Mike: "give it its own UI and title 'Ad Studio'
   in the Phantra studio. Combine what we already have").

   Four steps on one page -- the format, the product, the brief, the brand
   kit -- and a card beside them that shows the ad taking shape and the one
   button that starts it in Create (lib/ad-studio.ts handoffHref). Everything
   here is what the studio already had, gathered: the formats are the ad
   skills (prompts/skills), the product is an Elements prop, the kit is a
   brand kit (and "Read a website" is the Brand page's reader), and the make
   happens in Create behind its priced cards. Nothing on this page spends.

   The studios are a paid add-on (src/addons.py). The page is open to
   everyone: without the add-on the steps still work as a preview and the
   card's button becomes the unlock. Styles: ad-studio.css (as-). */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Check, Globe, Lock, Package, Plus } from "lucide-react";
import { getAssets, getStudio, importBrandKit, listBrandKits, waitForJob, type Asset } from "@/lib/studio-api";
import { startCheckout, signInThenCheckout } from "@/lib/site-billing";
import {
  answer,
  briefText,
  formatOf,
  handoffHref,
  missing,
  startBrief,
  switchFormat,
  unlockState,
  type AdBrief,
  type AdFormat,
  type StudioPage,
} from "@/lib/ad-studio";
import { useShell } from "@/components/studio/shell";
import "./ad-studio.css";
/* eslint-disable @next/next/no-img-element */

type KitRow = { id: number; name: string };

const ratio = (aspect: string) => {
  const m = /^(\d+):(\d+)$/.exec(aspect);
  return m ? `${m[1]} / ${m[2]}` : "9 / 16";
};

function lengthLabel(f: AdFormat): string {
  if (f.output === "image" || !f.seconds) return "Still";
  return `${f.seconds[0]}–${f.seconds[1]}s`;
}

function productThumb(a: Asset): string | null {
  return a.photo_thumbs?.[0] ?? a.poster ?? null;
}

export function AdStudio() {
  return (
    <Suspense fallback={null}>
      <AdStudioPage />
    </Suspense>
  );
}

function AdStudioPage() {
  const { toast } = useShell();
  const router = useRouter();
  const params = useSearchParams();
  const [page, setPage] = useState<StudioPage | null>(null);
  const [error, setError] = useState("");
  const [brief, setBrief] = useState<AdBrief | null>(null);
  const [products, setProducts] = useState<Asset[] | null>(null);
  const [kits, setKits] = useState<KitRow[] | null>(null);
  const [site, setSite] = useState("");
  const [reading, setReading] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);

  const load = useCallback(() => {
    getStudio("ads")
      .then((p) => {
        setPage(p);
        setBrief((b) => b ?? (p.formats[0] ? startBrief(p.formats[0]) : null));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "The Ad Studio could not be loaded."));
  }, []);
  const loadKits = useCallback(
    () =>
      listBrandKits()
        .then((r) => {
          const rows = r.kits.map((k) => ({ id: k.id, name: k.name }));
          setKits(rows);
          return rows;
        })
        .catch(() => {
          setKits([]);
          return [] as KitRow[];
        }),
    [],
  );
  useEffect(() => {
    load();
    loadKits();
    getAssets(undefined, "elements")
      .then((r) => setProducts(r.items.filter((a) => a.category === "prop")))
      .catch(() => setProducts([]));
  }, [load, loadKits]);

  // back from Stripe: say so once, read the page again, drop the param
  const checkout = params.get("checkout");
  useEffect(() => {
    if (!checkout) return;
    if (checkout === "success") toast("Ad Studio added to this workspace");
    router.replace("/studio/ads", { scroll: false });
    load();
  }, [checkout, load, router, toast]);

  const format = formatOf(page, brief?.format);
  const unlock = page ? unlockState(page) : null;
  const sentence = page && brief ? briefText(page, brief) : "";
  const advice = format && brief ? missing(format, brief) : [];
  const href = page && brief ? handoffHref(page, brief) : "/studio";
  const needsProduct = !!format?.needs.includes("product");

  const set = (next: AdBrief) => setBrief(next);

  const readSite = async () => {
    if (!site.trim() || reading) return;
    setReading("starting");
    try {
      const { job_id } = await importBrandKit(site.trim());
      const job = await waitForJob(job_id, (j) => setReading(j.detail || "reading the website"), 800);
      if (job.status !== "done") throw new Error(job.error || "The website could not be read.");
      const made = Number((job as unknown as { kit_id?: number }).kit_id ?? job.ref_id);
      const rows = await loadKits();
      const kit = rows.find((k) => k.id === made);
      if (kit && brief) setBrief({ ...brief, kit });
      // the reader files a site's products as Elements: show them here too
      getAssets(undefined, "elements")
        .then((r) => setProducts(r.items.filter((a) => a.category === "prop")))
        .catch(() => {});
      setSite("");
      toast(kit ? `${kit.name} read into a new kit` : "Kit made");
    } catch (e) {
      toast(e instanceof Error ? e.message : "The website could not be read.", "err");
    } finally {
      setReading(null);
    }
  };

  const buy = async () => {
    if (!page?.addon || unlocking) return;
    setUnlocking(true);
    const out = await startCheckout(page.addon.key);
    if (out.kind === "redirect") {
      window.location.href = out.url;
      return;
    }
    setUnlocking(false);
    if (out.kind === "sign-in") signInThenCheckout(page.addon.key);
    else toast(out.message, "err");
  };

  const kitsSorted = useMemo(() => kits ?? [], [kits]);

  if (error) {
    return (
      <section className="view as">
        <div className="stateline err">{error}</div>
      </section>
    );
  }
  if (!page || !brief || !format) {
    return (
      <section className="view as">
        <p className="as-empty">Loading the Ad Studio…</p>
      </section>
    );
  }

  return (
    <section className="view as">
      <header className="as-hero">
        <div className="as-hero-copy">
          <span className="as-kicker">Phantra studio</span>
          <h1 className="as-anton">Ad Studio</h1>
          <p>{page.tagline}</p>
        </div>
        <ol className="as-how" aria-label="How it works">
          <li>
            <b>1</b> Pick a format
          </li>
          <li>
            <b>2</b> Point at the product
          </li>
          <li>
            <b>3</b> Fill the brief
          </li>
          <li>
            <b>4</b> Vesper writes it in Create
          </li>
        </ol>
        <span className={`as-state${page.entitled ? " is-on" : ""}`}>
          {page.entitled ? (
            <>
              <Check size={13} strokeWidth={2.4} /> {page.gated ? "Add-on active" : "Open"}
            </>
          ) : (
            <>
              <Lock size={12} strokeWidth={2.2} /> Preview
            </>
          )}
        </span>
      </header>

      <div className="as-body">
        <div className="as-steps">
          {/* 1 -- the format */}
          <section className="as-step" aria-labelledby="as-format">
            <h2 id="as-format">
              <span>01</span> Format
            </h2>
            <div className="as-formats" role="radiogroup" aria-label="Ad format">
              {page.formats.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  role="radio"
                  aria-checked={f.id === brief.format}
                  className="as-format"
                  onClick={() => set(switchFormat(page, brief, f))}
                >
                  <span className="as-format-top">
                    <b>{f.title}</b>
                    {f.free ? <em className="as-free">Free</em> : null}
                  </span>
                  <span className="as-format-blurb">{f.blurb}</span>
                  <span className="as-format-meta">
                    <span>{f.aspects.join(" · ")}</span>
                    <span>{lengthLabel(f)}</span>
                    {f.output === "image" ? <span>Image</span> : <span>Video</span>}
                  </span>
                </button>
              ))}
            </div>
          </section>

          {/* 2 -- the product */}
          <section className="as-step" aria-labelledby="as-product">
            <h2 id="as-product">
              <span>02</span> Product
              {!needsProduct ? <small>optional for this format</small> : null}
            </h2>
            {format.needs.includes("clip") ? (
              <p className="as-hint">
                A cut-down works on an ad you already made. Once you are in Create, attach it from your Library and Vesper
                re-shapes and trims it for free.
              </p>
            ) : null}
            <div className="as-products">
              {(products ?? []).map((a) => {
                const on = brief.product?.id === a.id;
                const thumb = productThumb(a);
                return (
                  <button
                    key={a.id}
                    type="button"
                    className="as-product"
                    aria-pressed={on}
                    title={a.name}
                    onClick={() => set({ ...brief, product: on ? null : { id: a.id, name: a.name } })}
                  >
                    <span className="as-product-pic">
                      {thumb ? <img src={thumb} alt="" loading="lazy" /> : <Package size={20} strokeWidth={1.6} />}
                      {on ? (
                        <span className="as-tick" aria-hidden>
                          <Check size={12} strokeWidth={3} />
                        </span>
                      ) : null}
                    </span>
                    <span className="as-product-name">{a.name}</span>
                  </button>
                );
              })}
              <Link href="/studio/elements" className="as-product as-product-add">
                <span className="as-product-pic">
                  <Plus size={20} strokeWidth={1.7} />
                </span>
                <span className="as-product-name">Add a product</span>
              </Link>
            </div>
            {products && !products.length ? (
              <p className="as-hint">
                No products yet. Add one on Elements with its photos, or read the brand&rsquo;s website below: its products
                come in as elements.
              </p>
            ) : null}
          </section>

          {/* 3 -- the brief */}
          <section className="as-step" aria-labelledby="as-brief">
            <h2 id="as-brief">
              <span>03</span> Brief
            </h2>
            <div className="as-fields">
              {page.intake.map((q) =>
                q.kind === "choice" ? (
                  <div key={q.id} className="as-field">
                    <span className="as-lab">{q.label}</span>
                    <div className="as-pills" role="radiogroup" aria-label={q.label}>
                      {(q.options ?? []).map((o) => {
                        const on = brief.intake[q.id] === o.id;
                        return (
                          <button
                            key={o.id}
                            type="button"
                            role="radio"
                            aria-checked={on}
                            className="as-pill"
                            onClick={() => set(answer(page, brief, q.id, on ? "" : o.id))}
                          >
                            {o.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <label key={q.id} className="as-field">
                    <span className="as-lab">{q.label}</span>
                    <input
                      className="as-input"
                      value={brief.intake[q.id] ?? ""}
                      placeholder={q.placeholder}
                      maxLength={q.max ?? 200}
                      onChange={(e) => set(answer(page, brief, q.id, e.target.value))}
                    />
                  </label>
                ),
              )}
              <div className="as-field">
                <span className="as-lab">Shape</span>
                <div className="as-pills" role="radiogroup" aria-label="Shape">
                  {format.aspects.map((a) => (
                    <button
                      key={a}
                      type="button"
                      role="radio"
                      aria-checked={brief.aspect === a}
                      className="as-pill"
                      onClick={() => set({ ...brief, aspect: a })}
                    >
                      {a}
                    </button>
                  ))}
                </div>
              </div>
              {format.output === "video" && format.seconds ? (
                <label className="as-field">
                  <span className="as-lab">
                    Length <b className="as-val">{brief.seconds ?? format.default_seconds}s</b>
                  </span>
                  <input
                    type="range"
                    min={format.seconds[0]}
                    max={format.seconds[1]}
                    step={1}
                    value={brief.seconds ?? format.default_seconds ?? format.seconds[0]}
                    onChange={(e) => set({ ...brief, seconds: Number(e.target.value) })}
                  />
                </label>
              ) : null}
            </div>
          </section>

          {/* 4 -- the brand kit */}
          <section className="as-step" aria-labelledby="as-kit">
            <h2 id="as-kit">
              <span>04</span> Brand kit
              {!format.needs.includes("kit") ? <small>optional</small> : null}
            </h2>
            <div className="as-pills" role="radiogroup" aria-label="Brand kit">
              <button
                type="button"
                role="radio"
                aria-checked={!brief.kit}
                className="as-pill"
                onClick={() => set({ ...brief, kit: null })}
              >
                No kit
              </button>
              {kitsSorted.map((k) => (
                <button
                  key={k.id}
                  type="button"
                  role="radio"
                  aria-checked={brief.kit?.id === k.id}
                  className="as-pill"
                  onClick={() => set({ ...brief, kit: k })}
                >
                  {k.name}
                </button>
              ))}
            </div>
            <form
              className="as-read"
              onSubmit={(e) => {
                e.preventDefault();
                void readSite();
              }}
            >
              <Globe size={15} strokeWidth={1.7} />
              <input
                placeholder="Read a brand from its website: https://yourbrand.com"
                value={site}
                inputMode="url"
                onChange={(e) => setSite(e.target.value)}
                aria-label="Brand website"
                disabled={!!reading}
              />
              <button type="submit" className="as-pill as-pill-solid" disabled={!site.trim() || !!reading}>
                {reading ? `${reading}…` : "Read the site"}
              </button>
            </form>
            <p className="as-hint">
              Free. Its colours, fonts and logo become a new kit, and its products come in as elements. Use pictures you have
              the right to use.
            </p>
          </section>
        </div>

        {/* the card: the ad taking shape, and the one action */}
        <aside className="as-card" aria-label="Your ad">
          <div className="as-frame-wrap">
            <div className="as-frame" style={{ aspectRatio: ratio(brief.aspect) }}>
              <span className="as-frame-tag">{format.title}</span>
              <span className="as-frame-dims">
                {brief.aspect}
                {format.output === "video" && brief.seconds ? ` · ${brief.seconds}s` : ""}
              </span>
              {brief.kit ? <span className="as-frame-kit">{brief.kit.name}</span> : null}
            </div>
          </div>
          <div className="as-card-body">
            <span className="as-lab">What Vesper is handed</span>
            <p className="as-sentence">{sentence}</p>
            <ul className="as-facts">
              <li>
                Recipe <b>{format.skill_title ?? format.skill}</b>
              </li>
              <li>
                Product <b>{brief.product?.name ?? "none yet"}</b>
              </li>
              <li>
                Kit <b>{brief.kit?.name ?? "none"}</b>
              </li>
            </ul>
            {advice.length ? (
              <ul className="as-advice">
                {advice.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            ) : null}
            {unlock?.kind === "open" ? (
              <Link href={href} className="as-go">
                Start in Create <ArrowRight size={16} strokeWidth={2.2} />
              </Link>
            ) : unlock?.kind === "buy" ? (
              <button type="button" className="as-go" onClick={buy} disabled={unlocking}>
                {unlocking ? "Opening checkout…" : unlock.label}
              </button>
            ) : unlock?.kind === "plan-first" ? (
              <Link href="/pricing" className="as-go">
                Choose a plan first
              </Link>
            ) : (
              <button type="button" className="as-go" disabled>
                Ad Studio opens soon
              </button>
            )}
            <p className="as-fine">
              {unlock?.kind === "open"
                ? "Opens Create with all of this in the box. Nothing is made until you send it, and every still and clip waits on its priced card."
                : unlock?.kind === "plan-first"
                  ? "Ad Studio is an add-on to a plan. Pick a plan, then add it here."
                  : unlock?.kind === "buy"
                    ? `${page.addon?.blurb ?? ""} A monthly add-on beside your plan; renders still spend your plan's credits.`
                    : "The Ad Studio add-on is not on sale yet. Everything on this page works as a preview."}
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}
