"use client";

/* Five layouts of /studio/plugins for Mike to choose from (2026-10-23). All
   five draw the same facts (./shared.tsx); only the arrangement differs.
   Once one is picked the other four and the ?v= switch go. */
import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, Check, Download as DownloadIcon, KeyRound, MonitorPlay, Plug } from "lucide-react";
import {
  CodeConnect,
  ConnectedPill,
  ConnectionRows,
  DownloadButton,
  Eyebrow,
  LICENSE_LINE,
  PANELS,
  PanelLogo,
  Pill,
  StepList,
  downloadFor,
  panelById,
  stepsFor,
  useConnections,
  type Panel,
} from "./shared";

const DISPLAY = "[font-family:var(--display)] uppercase tracking-[0.02em]";
const CARD = "rounded-[var(--r2)] border border-[var(--edge)] bg-[var(--panel)]";

/** #resolve / #premiere picks the panel the flyout row was for. */
function useHashPanel(): [Panel, (p: Panel) => void] {
  const [panel, setPanel] = useState<Panel>(PANELS[0]);
  useEffect(() => {
    const read = () => setPanel(panelById(window.location.hash.slice(1)));
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);
  const pick = (p: Panel) => {
    setPanel(p);
    history.replaceState(null, "", `#${p.id}`);
  };
  return [panel, pick];
}

function Header({ eyebrow, title, dek }: { eyebrow: string; title: string; dek: string }) {
  return (
    <header>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className={`mt-2 text-[34px] leading-none text-[var(--text)] ${DISPLAY}`}>{title}</h1>
      <p className="mt-3 max-w-[62ch] text-[14px] leading-relaxed text-[var(--bone-3)]">{dek}</p>
    </header>
  );
}

const DEK =
  "A Phantra panel inside your editor: your Library on the timeline, and images, video and effects made from the clip you're cutting. Every spend is priced in credits and waits for your yes.";

function Foot() {
  return <p className="mt-10 max-w-[70ch] text-[12px] leading-relaxed text-[var(--dim)]">{LICENSE_LINE}</p>;
}

/* ── 1. Two cards side by side ──────────────────────────────────────────── */

export function V1Cards() {
  const conn = useConnections();
  return (
    <main className="mx-auto w-full max-w-[1100px] px-6 py-10">
      <Header eyebrow="Plugins · Creative apps" title="Editor panels" dek={DEK} />
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {PANELS.map((p) => {
          const mine = conn.forPanel(p);
          return (
            <article key={p.id} id={p.id} className={`${CARD} scroll-mt-6 p-6`}>
              <div className="flex items-start gap-3">
                <PanelLogo panel={p} size={44} />
                <div className="min-w-0 flex-1">
                  <h2 className="text-[18px] font-semibold text-[var(--text)]">{p.app}</h2>
                  <p className="mt-0.5 text-[12px] text-[var(--dim)]">{p.needs}</p>
                </div>
                <ConnectedPill count={mine.length} />
              </div>
              <p className="mt-4 text-[14px] leading-relaxed text-[var(--bone-2)]">{p.does}</p>
              <div className="mt-5">
                <DownloadButton panel={p} />
              </div>
              <div className="mt-6">
                <Eyebrow>Setup</Eyebrow>
                <div className="mt-2">
                  <StepList steps={stepsFor(p)} />
                </div>
              </div>
              {mine.length ? (
                <div className="mt-5">
                  <Eyebrow>Connected</Eyebrow>
                  <ConnectionRows list={mine} busy={conn.busy} onDisconnect={(c) => void conn.disconnect(c)} />
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
      <Foot />
    </main>
  );
}

/* ── 2. One app at a time: a switch, the steps, the panel itself ─────────── */

export function V2Tabs() {
  const [panel, pick] = useHashPanel();
  const conn = useConnections();
  const mine = conn.forPanel(panel);
  return (
    <main className="mx-auto w-full max-w-[1100px] px-6 py-10">
      <Header eyebrow="Plugins" title="Phantra in your editor" dek={DEK} />
      <div role="tablist" className="mt-7 inline-flex rounded-[14px] border border-[var(--edge)] bg-[var(--well)] p-1">
        {PANELS.map((p) => (
          <button
            key={p.id}
            role="tab"
            aria-selected={p.id === panel.id}
            onClick={() => pick(p)}
            className={`flex h-10 items-center gap-2 rounded-[10px] px-4 text-[14px] ${
              p.id === panel.id ? "bg-[var(--raise)] text-[var(--text)]" : "text-[var(--bone-3)] hover:text-[var(--text)]"
            }`}
          >
            <PanelLogo panel={p} size={20} /> {p.app}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <section className={`${CARD} p-6`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <ConnectedPill count={mine.length} />
            <DownloadButton panel={panel} />
          </div>
          <p className="mt-4 text-[13px] text-[var(--dim)]">Needs: {panel.needs}</p>
          <ol className="mt-6 space-y-5">
            {stepsFor(panel).map((s, i) => (
              <li key={s.title} className="flex gap-4">
                <span
                  className={`inline-flex size-9 shrink-0 items-center justify-center rounded-full border text-[15px] ${DISPLAY} ${
                    i === 0 ? "border-[var(--signal)] text-[var(--signal)]" : "border-[var(--edge-hi)] text-[var(--bone-3)]"
                  }`}
                >
                  {i + 1}
                </span>
                <div className="pt-1">
                  <p className="text-[15px] font-medium text-[var(--text)]">{s.title}</p>
                  <p className="mt-1 text-[13px] leading-relaxed text-[var(--bone-3)]">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
          {mine.length ? (
            <div className="mt-7 border-t border-[var(--line)] pt-4">
              <ConnectionRows list={mine} busy={conn.busy} onDisconnect={(c) => void conn.disconnect(c)} />
            </div>
          ) : null}
        </section>

        <aside className={`${CARD} overflow-hidden p-4`}>
          <Eyebrow>{panel.id === "resolve" ? "The panel in Resolve" : "What it does"}</Eyebrow>
          {panel.id === "resolve" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src="/plugins/panel-library.webp"
              alt="The Phantra panel's Library tab"
              className="mt-3 h-[360px] w-full rounded-[12px] border border-[var(--edge)] object-cover object-top"
            />
          ) : null}
          <ul className="mt-3 space-y-3">
            {panel.features.map((f) => (
              <li key={f.title}>
                <p className="text-[13px] font-medium text-[var(--text)]">{f.title}</p>
                <p className="text-[12px] leading-relaxed text-[var(--bone-3)]">{f.body}</p>
              </li>
            ))}
          </ul>
        </aside>
      </div>
      <Foot />
    </main>
  );
}

/* ── 3. Your connected panels first, setup folded below ──────────────────── */

export function V3Connected() {
  const conn = useConnections();
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => setOpen(window.location.hash.slice(1) || null), []);
  const all = conn.items ?? [];
  return (
    <main className="mx-auto w-full max-w-[820px] px-6 py-10">
      <Header eyebrow="Plugins" title="Editor panels" dek={DEK} />

      <section className={`${CARD} mt-8 p-6`}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-[16px] font-semibold text-[var(--text)]">
            <Plug className="size-4 text-[var(--signal)]" aria-hidden /> Connected to this workspace
          </h2>
          <Pill tone={all.length ? "ok" : "neutral"}>{all.length}</Pill>
        </div>
        <div className="mt-3">
          {conn.items === null ? null : all.length ? (
            <ConnectionRows list={all} busy={conn.busy} onDisconnect={(c) => void conn.disconnect(c)} />
          ) : (
            <p className="text-[13px] text-[var(--dim)]">No panel is signed in yet. Install one below, press Sign in, and type its code here.</p>
          )}
        </div>
        <div className="mt-5 border-t border-[var(--line)] pt-5">
          <p className="mb-2 flex items-center gap-2 text-[13px] text-[var(--bone-2)]">
            <KeyRound className="size-3.5" aria-hidden /> Have a code from a panel?
          </p>
          <CodeConnect onConnected={() => void conn.reload()} compact />
        </div>
      </section>

      <div className="mt-6 space-y-3">
        {PANELS.map((p) => {
          const isOpen = open === p.id;
          const mine = conn.forPanel(p);
          return (
            <section key={p.id} id={p.id} className={`${CARD} scroll-mt-6`}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : p.id)}
                className="flex w-full items-center gap-3 p-5 text-left"
              >
                <PanelLogo panel={p} size={36} />
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] font-semibold text-[var(--text)]">{p.app}</p>
                  <p className="truncate text-[12px] text-[var(--dim)]">{p.does}</p>
                </div>
                <ConnectedPill count={mine.length} />
                <ChevronDown className={`size-4 text-[var(--dim)] transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden />
              </button>
              {isOpen ? (
                <div className="border-t border-[var(--line)] px-5 pb-5 pt-4">
                  <p className="text-[13px] text-[var(--dim)]">Needs: {p.needs}</p>
                  <div className="mt-4">
                    <DownloadButton panel={p} />
                  </div>
                  <div className="mt-5">
                    <StepList steps={stepsFor(p)} />
                  </div>
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
      <Foot />
    </main>
  );
}

/* ── 4. A checklist you finish on this page ───────────────────────────────── */

export function V4Checklist() {
  const [panel, pick] = useHashPanel();
  const conn = useConnections();
  const connected = conn.forPanel(panel).length > 0;
  const d = downloadFor(panel.id);
  const items = [
    {
      title: `Download the ${panel.app} panel`,
      body: d.url ? `${d.file}` : `Version ${d.version}. The download goes up here as soon as the build is ready.`,
      action: <DownloadButton panel={panel} />,
    },
    ...panel.install.map((s) => ({ title: s.title, body: s.body, action: null })),
    {
      title: "Press Sign in, then type the code here",
      body: "The panel shows a code like KDPX-7QHR. Only type a code your own panel is showing you.",
      action: <CodeConnect onConnected={() => void conn.reload()} compact />,
    },
  ];
  return (
    <main className="mx-auto w-full max-w-[760px] px-6 py-10">
      <Header eyebrow="Plugins · Setup" title="Set up your editor" dek="Four steps, and the last one happens on this page." />
      <div className="mt-7 grid grid-cols-2 gap-3">
        {PANELS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => pick(p)}
            aria-pressed={p.id === panel.id}
            className={`flex items-center gap-3 rounded-[16px] border p-4 text-left ${
              p.id === panel.id
                ? "border-[var(--signal)] bg-[var(--signal-wash)]"
                : "border-[var(--edge)] bg-[var(--panel)] hover:border-[var(--edge-hi)]"
            }`}
          >
            <PanelLogo panel={p} size={32} />
            <span className="flex-1 text-[14px] font-medium text-[var(--text)]">{p.app}</span>
            {conn.forPanel(p).length ? <Check className="size-4 text-[var(--ok)]" aria-label="connected" /> : null}
          </button>
        ))}
      </div>
      <p className="mt-3 text-[12px] text-[var(--dim)]">Needs: {panel.needs}</p>

      <ol className={`${CARD} mt-5 divide-y divide-[var(--line)]`}>
        {items.map((it, i) => (
          <li key={it.title} className="flex gap-4 p-5">
            <span
              className={`mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full border text-[12px] ${
                connected ? "border-[var(--ok)] bg-[var(--ok)] text-[var(--ground)]" : "border-[var(--edge-hi)] text-[var(--bone-3)]"
              }`}
            >
              {connected ? <Check className="size-3.5" strokeWidth={3} aria-hidden /> : i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-medium text-[var(--text)]">{it.title}</p>
              <p className="mt-1 text-[13px] leading-relaxed text-[var(--bone-3)]">{it.body}</p>
              {it.action && !(connected && i === items.length - 1) ? <div className="mt-3">{it.action}</div> : null}
            </div>
          </li>
        ))}
      </ol>
      {connected ? (
        <div className="mt-4 rounded-[16px] border border-[color-mix(in_srgb,var(--ok)_40%,transparent)] p-4">
          <p className="text-[14px] text-[var(--ok)]">{panel.app} is connected to this workspace.</p>
          <div className="mt-2">
            <ConnectionRows list={conn.forPanel(panel)} busy={conn.busy} onDisconnect={(c) => void conn.disconnect(c)} />
          </div>
        </div>
      ) : null}
      <Foot />
    </main>
  );
}

/* ── 5. A showcase: the panel first, then how to get it ───────────────────── */

export function V5Showcase() {
  const conn = useConnections();
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => setOpen(window.location.hash.slice(1) || "resolve"), []);
  return (
    <main className="mx-auto w-full max-w-[1100px] px-6 py-10">
      <section className={`${CARD} relative overflow-hidden p-8 md:p-10`}>
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 size-[420px] rounded-full"
          style={{ background: "radial-gradient(circle, var(--signal-wash), transparent 65%)" }}
        />
        <div className="relative grid items-center gap-8 md:grid-cols-[1.1fr_1fr]">
          <div>
            <div className="flex gap-2">
              {PANELS.map((p) => (
                <PanelLogo key={p.id} panel={p} size={30} />
              ))}
            </div>
            <h1 className={`mt-5 text-[46px] leading-[0.95] text-[var(--text)] ${DISPLAY}`}>
              Phantra,
              <br />
              <span className="text-[var(--signal)]">inside the cut.</span>
            </h1>
            <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed text-[var(--bone-2)]">{DEK}</p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Pill tone="signal">
                <MonitorPlay className="size-3.5" aria-hidden /> DaVinci Resolve Studio
              </Pill>
              <Pill tone="signal">
                <MonitorPlay className="size-3.5" aria-hidden /> Premiere Pro
              </Pill>
            </div>
          </div>
          <div className="flex justify-center gap-3">
            {/* eslint-disable @next/next/no-img-element */}
            <img
              src="/plugins/panel-library.webp"
              alt="The panel's Library tab"
              className="w-[46%] max-w-[210px] rounded-[14px] border border-[var(--edge-hi)] shadow-2xl"
            />
            <img
              src="/plugins/panel-make.webp"
              alt="The panel's Make tab"
              className="mt-8 w-[46%] max-w-[210px] rounded-[14px] border border-[var(--edge-hi)] shadow-2xl"
            />
            {/* eslint-enable @next/next/no-img-element */}
          </div>
        </div>
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-3">
        {PANELS[0].features.map((f, i) => (
          <div key={f.title} className={`${CARD} p-5`}>
            <span className={`text-[22px] text-[var(--signal)] ${DISPLAY}`}>0{i + 1}</span>
            <p className="mt-2 text-[15px] font-medium text-[var(--text)]">{f.title}</p>
            <p className="mt-1 text-[13px] leading-relaxed text-[var(--bone-3)]">{f.body}</p>
          </div>
        ))}
      </section>

      <h2 className={`mt-10 text-[22px] text-[var(--text)] ${DISPLAY}`}>Get it</h2>
      <div className="mt-3 space-y-3">
        {PANELS.map((p) => {
          const isOpen = open === p.id;
          return (
            <section key={p.id} id={p.id} className={`${CARD} scroll-mt-6`}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : p.id)}
                className="flex w-full items-center gap-3 p-5 text-left"
              >
                <PanelLogo panel={p} size={32} />
                <span className="flex-1 text-[15px] font-semibold text-[var(--text)]">{p.app}</span>
                <ConnectedPill count={conn.forPanel(p).length} />
                <span className="hidden items-center gap-1.5 text-[12px] text-[var(--dim)] sm:inline-flex">
                  <DownloadIcon className="size-3.5" aria-hidden /> v{downloadFor(p.id).version}
                </span>
                <ChevronDown className={`size-4 text-[var(--dim)] transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden />
              </button>
              {isOpen ? (
                <div className="grid gap-6 border-t border-[var(--line)] p-5 md:grid-cols-[1fr_1.3fr]">
                  <div>
                    <p className="text-[13px] leading-relaxed text-[var(--bone-2)]">{p.does}</p>
                    <p className="mt-2 text-[12px] text-[var(--dim)]">Needs: {p.needs}</p>
                    <div className="mt-4">
                      <DownloadButton panel={p} />
                    </div>
                  </div>
                  <StepList steps={stepsFor(p)} />
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
      <Foot />
    </main>
  );
}

export const VARIANTS = [
  { n: 1, name: "Cards", View: V1Cards },
  { n: 2, name: "Tabs", View: V2Tabs },
  { n: 3, name: "Connected first", View: V3Connected },
  { n: 4, name: "Checklist", View: V4Checklist },
  { n: 5, name: "Showcase", View: V5Showcase },
] as const;

/** The review strip (Layout 1..5) and the layout it picks. */
export function PluginsReview({ v }: { v?: string }) {
  const pick = VARIANTS.find((x) => x.n === Number(v)) ?? VARIANTS[0];
  const View = pick.View;
  return (
    <div className="w-full">
      <nav aria-label="Layouts" className="mx-auto flex w-full max-w-[1100px] flex-wrap items-center gap-1.5 px-6 pt-5 text-[12px]">
        <span className="mr-1 font-mono uppercase tracking-[0.12em] text-[var(--dimmer)]">Layout</span>
        {VARIANTS.map((x) => (
          <Link
            key={x.n}
            href={`/studio/plugins?v=${x.n}`}
            className={`rounded-full border px-3 py-1 ${
              x.n === pick.n
                ? "border-[var(--signal)] text-[var(--signal)]"
                : "border-[var(--edge)] text-[var(--bone-3)] hover:text-[var(--text)]"
            }`}
          >
            {x.n} · {x.name}
          </Link>
        ))}
      </nav>
      <View />
    </div>
  );
}
