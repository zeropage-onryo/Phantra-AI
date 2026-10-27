"use client";

/* /studio/plugins (2026-10-23, Mike: "add it to the ui and give me a more
   visually appealing design"). Where the Plugins flyout's DaVinci Resolve and
   Premiere Pro rows open (#resolve, #premiere). The one loud thing is the
   drawn editor at the top: a viewer, a timeline, and the Phantra panel docked
   beside it, with the clip Phantra made landing on V2 at the playhead. Under
   it, the plain part (Mike: "simple like this with the downloader attached"):
   app tabs, three steps, and the download buttons. The copies signed in are
   under Settings > Connections > Apps. Facts are ./shared.tsx; styles are
   .zplug in studio.css. */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { PANELS, PanelLogo, downloadFor, panelById, type Panel } from "./shared";
import { humanSize } from "@/lib/downloads";

/** #resolve / #premiere picks the app the flyout row was for. */
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

/** A steady, made-up waveform for the A1 clip (the same on every render). */
function wavePath(width: number, height: number, n = 160): string {
  const mid = height / 2;
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) {
    const x = (i / n) * width;
    const t = i / n;
    const env = 0.35 + 0.65 * Math.abs(Math.sin(t * Math.PI * 3.1 + 0.4));
    const amp = (0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.31))) * env * (mid - 1);
    pts.push(`${x.toFixed(1)},${(mid - amp).toFixed(1)}`);
  }
  const back: string[] = [];
  for (let i = n; i >= 0; i--) {
    const [x, y] = pts[i].split(",").map(Number);
    back.push(`${x.toFixed(1)},${(height - y).toFixed(1)}`);
  }
  return `M${pts.join(" L")} L${back.join(" L")} Z`;
}

const CLIPS = [
  { src: "/make/ai-short-film-maker/dawn.jpg", from: 0, to: 17 },
  { src: "/make/ai-trailer-maker/convoy.jpg", from: 17, to: 36 },
  { src: "/make/ai-short-film-maker/busstop.jpg", from: 36, to: 52 },
  { src: "/make/ai-trailer-maker/corridor.jpg", from: 52, to: 79 },
  { src: "/make/ai-trailer-maker/ship.jpg", from: 79, to: 100 },
];
const PLAYHEAD = 62; // percent along the timeline
const TICKS = ["00:00:00", "00:00:05", "00:00:10", "00:00:15"];

function EditorScene({ panel }: { panel: Panel }) {
  const wave = useMemo(() => wavePath(1000, 40), []);
  const resolve = panel.id === "resolve";
  return (
    <figure className="zed" data-app={panel.id} aria-label={`The Phantra panel docked in ${panel.app}, next to the timeline`}>
      <div className="zed-bar" aria-hidden>
        <span className="zed-lights">
          <i />
          <i />
          <i />
        </span>
        <span className="zed-app">{resolve ? "DaVinci Resolve Studio" : "Adobe Premiere Pro"}</span>
        <span className="zed-proj">Night shift, edit 3</span>
      </div>
      <div className="zed-body" aria-hidden>
        <div className="zed-main">
          <div className="zed-viewer">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/make/ai-trailer-maker/corridor.jpg" alt="" />
            <span className="zed-tc">00:00:12:08</span>
          </div>
          <div className="zed-timeline" style={{ ["--ph" as string]: `${PLAYHEAD}%` }}>
            <div className="zed-labels">
              <span className="zed-ruler-gap" />
              <span>V2</span>
              <span>V1</span>
              <span>A1</span>
            </div>
            <div className="zed-lanes">
              <div className="zed-ruler">
                {TICKS.map((t, i) => (
                  <span key={t} style={{ left: `${(i / TICKS.length) * 100}%` }}>
                    {t}
                  </span>
                ))}
              </div>
              <div className="zed-lane">
                <div className="zed-clip made" style={{ left: `${PLAYHEAD}%`, width: "19%" }}>
                  <span className="zed-made-l">Made in Phantra</span>
                </div>
              </div>
              <div className="zed-lane">
                {CLIPS.map((c) => (
                  <div
                    key={c.src}
                    className="zed-clip video"
                    style={{ left: `${c.from}%`, width: `${c.to - c.from}%`, backgroundImage: `url(${c.src})` }}
                  />
                ))}
              </div>
              <div className="zed-lane">
                <div className="zed-clip audio" style={{ left: "0%", width: "100%" }}>
                  <svg viewBox="0 0 1000 40" preserveAspectRatio="none">
                    <path d={wave} />
                  </svg>
                </div>
              </div>
              <div className="zed-playhead">
                <span />
              </div>
            </div>
          </div>
        </div>

        <aside className="zed-panel">
          <div className="zp-top">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/phantra-owl-icon.svg" alt="" />
            <b>Phantra</b>
            <span>1,240 credits</span>
          </div>
          <div className="zp-tabs">
            <span>Library</span>
            <span className="on">Make</span>
            <span>Jobs</span>
          </div>
          <div className="zp-from">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/make/ai-trailer-maker/corridor.jpg" alt="" />
            <span>From the frame at the playhead</span>
          </div>
          <p className="zp-prompt">Slow push down the corridor as the lights fail one by one</p>
          <div className="zp-opts">
            <span>Kling 4</span>
            <span>5s</span>
            <span>1080p</span>
          </div>
          <div className="zp-price">
            <div>
              <b>60 credits</b>
              <small>Nothing is charged until you approve</small>
            </div>
            <span className="zp-approve">Approve</span>
          </div>
          <div className="zp-lib">
            {["/make/ai-trailer-maker/convoy.jpg", "/make/ai-trailer-maker/ship.jpg", "/make/ai-short-film-maker/dawn.jpg"].map(
              (src, i) => (
                <div key={src}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt="" />
                  <span>{["Convoy at dusk", "Wreck in the dunes", "Walk home"][i]}</span>
                  <em>Insert</em>
                </div>
              ),
            )}
          </div>
        </aside>
      </div>
    </figure>
  );
}

/* the two platform marks for the download buttons */
function AppleMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="zplug-os">
      <path d="M16.37 12.6c-.02-2.2 1.8-3.26 1.88-3.31-1.03-1.5-2.62-1.7-3.18-1.73-1.35-.14-2.64.8-3.33.8-.69 0-1.74-.78-2.87-.76-1.47.02-2.83.86-3.59 2.18-1.53 2.66-.39 6.6 1.1 8.76.73 1.06 1.6 2.24 2.73 2.2 1.1-.05 1.51-.71 2.84-.71 1.32 0 1.7.71 2.86.69 1.18-.02 1.93-1.07 2.65-2.13.84-1.22 1.18-2.41 1.2-2.47-.03-.01-2.27-.87-2.29-3.46ZM14.2 6.12c.6-.73 1.01-1.75.9-2.76-.87.04-1.92.58-2.55 1.31-.56.64-1.05 1.68-.92 2.67.97.07 1.96-.49 2.57-1.22Z" />
    </svg>
  );
}
function WindowsMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="zplug-os">
      <path d="M3 5.1 10.2 4v7.1H3V5.1Zm0 13.8 7.2 1.1v-7H3v5.9Zm8-14.9L21 2.5v8.6H11V4Zm0 16L21 21.5v-8.5H11V20Z" />
    </svg>
  );
}

type Step = { title: string; body: ReactNode };

const GUIDE: Record<Panel["id"], Step[]> = {
  resolve: [
    {
      title: "Download the plugin",
      body: "Download the Mac installer for free. It works with DaVinci Resolve Studio 20.1 or newer. It doesn't work in the free version of Resolve, which has no Workflow Integrations menu.",
    },
    {
      title: "Launch the installer",
      // the installer isn't signed yet: until it is, macOS stops it once, and
      // closing that warning installs nothing (the same steps as /download)
      body: (
        <>
          Quit Resolve, open the package and follow the steps. It finds your Resolve and installs the plugin in a few
          clicks. The first time, macOS says it can&apos;t check the installer because it isn&apos;t signed yet: press
          Done, open System Settings → Privacy &amp; Security, press Open Anyway next to the Phantra installer, and
          confirm. Closing that message without Open Anyway installs nothing.
        </>
      ),
    },
    {
      title: "Find Phantra inside Resolve",
      body: (
        <>
          In Resolve, go to Workspace → Workflow Integrations → Phantra. Press Sign in and type the code it shows at{" "}
          <Link href="/studio/link">phantra.ai/studio/link</Link>.
        </>
      ),
    },
  ],
  premiere: [
    {
      title: "Download the plugin",
      body: "Download the plugin for free. One file installs on Mac and Windows, for Premiere Pro 25.6 or newer.",
    },
    {
      title: "Launch the installer",
      body: "Double-click the .ccx file. The Creative Cloud app installs the plugin into Premiere.",
    },
    {
      title: "Find Phantra inside Premiere",
      body: (
        <>
          In Premiere, go to Window → Extensions (or UXP Plugins) → Phantra. Press Sign in and type the code it shows at{" "}
          <Link href="/studio/link">phantra.ai/studio/link</Link>.
        </>
      ),
    },
  ],
};

function Downloads({ panel }: { panel: Panel }) {
  const d = downloadFor(panel.id);
  const ready = Boolean(d.url && d.size !== null);
  const button = (os: "mac" | "windows" | "both", live: boolean) => {
    const mark = os === "windows" ? <WindowsMark /> : os === "mac" ? <AppleMark /> : null;
    const name = os === "windows" ? "Windows" : os === "mac" ? "Mac" : "Mac and Windows";
    return live ? (
      <a key={os} className="zplug-get-btn" href={d.url!} download={d.file} aria-label={`Download for ${name}`}>
        {mark}
        {os === "both" ? (
          <>
            <AppleMark />
            <WindowsMark />
          </>
        ) : null}
        Download
      </a>
    ) : (
      <span key={os} className="zplug-get-btn off" aria-disabled="true" title={`${name}: coming soon`}>
        {mark}
        {os === "both" ? (
          <>
            <AppleMark />
            <WindowsMark />
          </>
        ) : null}
        {os === "windows" ? "Coming later" : "Coming soon"}
      </span>
    );
  };
  return (
    <div className="zplug-dls">
      <div className="zplug-btns">
        {panel.id === "resolve" ? [button("mac", ready), button("windows", false)] : [button("both", ready)]}
      </div>
      <p className="zplug-legal">
        {ready ? `${d.file}, ${humanSize(d.size!)}. ` : `Version ${d.version}. The download appears here as soon as it is up. `}
        By downloading the plugin, you agree to the <Link href="/download/license">Phantra Plugin License</Link> and
        our <Link href="/terms">Terms</Link>, and acknowledge our <Link href="/privacy">Privacy Policy</Link>.
      </p>
    </div>
  );
}

export function PluginsPage() {
  const [panel, pick] = useHashPanel();
  return (
    <main className="zplug">
      <header className="zplug-title">
        <h1>
          Phantra,
          <br />
          inside your edit
        </h1>
        <p>
          Your Library on the timeline, and images, video and effects made from the clip you are cutting, right inside your
          editing app. Anything that costs credits shows its price and waits for your yes.
        </p>
      </header>

      <EditorScene key={panel.id} panel={panel} />

      <section className="zplug-guide" aria-label="Install the plugin">
        <div className="zplug-tabs" role="tablist" aria-label="Editing app">
          {PANELS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={p.id === panel.id}
              className="zplug-tab"
              onClick={() => pick(p)}
            >
              <PanelLogo panel={p} size={18} />
              {p.app}
            </button>
          ))}
        </div>
        <ol className="zplug-steps">
          {GUIDE[panel.id].map((s, i) => (
            <li key={s.title}>
              <span className="zplug-step-n">Step {i + 1}</span>
              <h2>{s.title}</h2>
              <p>{s.body}</p>
            </li>
          ))}
        </ol>
        <Downloads panel={panel} />
      </section>
    </main>
  );
}
