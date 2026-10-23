"use client";

/* /studio/plugins (2026-10-23, Mike: "add it to the ui and give me a more
   visually appealing design"). Where the Plugins flyout's DaVinci Resolve and
   Premiere Pro rows open (#resolve, #premiere). The one loud thing is the
   drawn editor at the top: a viewer, a timeline, and the Phantra panel docked
   beside it, with the clip Phantra made landing on V2 at the playhead. The
   rest is quiet: the download, the copies signed in to this workspace (with
   the code box), and the four steps on a marker ruler. Facts and the live
   calls are ./shared.tsx; styles are .zplug in studio.css. */
import { useEffect, useMemo, useState } from "react";
import { Download as DownloadIcon } from "lucide-react";
import {
  CodeConnect,
  ConnectionRows,
  LICENSE_LINE,
  PANELS,
  PanelLogo,
  downloadFor,
  panelById,
  stepsFor,
  useConnections,
  type Panel,
} from "./shared";
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

function DownloadSlab({ panel }: { panel: Panel }) {
  const d = downloadFor(panel.id);
  const ready = Boolean(d.url && d.size !== null);
  const label = panel.id === "resolve" ? "Download for Mac" : "Download for Premiere Pro";
  return (
    <div className="zplug-dl">
      <div className="zplug-dl-app">
        <PanelLogo panel={panel} size={44} />
        <div>
          <h2>{panel.app}</h2>
          <p>{panel.needs}</p>
        </div>
      </div>
      {ready ? (
        <a className="zplug-dl-btn" href={d.url!} download={d.file}>
          <DownloadIcon aria-hidden /> {label}
        </a>
      ) : (
        <span className="zplug-dl-btn off" aria-disabled="true">
          <DownloadIcon aria-hidden /> {panel.id === "resolve" ? "Mac installer coming soon" : "Coming soon"}
        </span>
      )}
      <p className="zplug-dl-file">
        {ready ? (
          <>
            {d.file}, {humanSize(d.size!)}
          </>
        ) : (
          <>Version {d.version}. The download appears here as soon as it is up.</>
        )}
      </p>
    </div>
  );
}

export function PluginsPage() {
  const [panel, pick] = useHashPanel();
  const conn = useConnections();
  const mine = conn.forPanel(panel);
  const steps = stepsFor(panel);

  return (
    <main className="zplug">
      <header className="zplug-head">
        <div className="zplug-title">
          <h1>
            Phantra,
            <br />
            inside your edit
          </h1>
          <p>
            Your Library on the timeline, and images, video and effects made from the clip you are cutting. Anything that
            costs credits shows its price and waits for your yes.
          </p>
        </div>
        <div className="zplug-apps" role="tablist" aria-label="Editing app">
          {PANELS.map((p) => {
            const n = conn.forPanel(p).length;
            return (
              <button
                key={p.id}
                type="button"
                role="tab"
                aria-selected={p.id === panel.id}
                className="zplug-app"
                onClick={() => pick(p)}
              >
                <PanelLogo panel={p} size={28} />
                <span>
                  <b>{p.app}</b>
                  <small className={n ? "on" : ""}>{n ? (n === 1 ? "Connected" : `${n} copies connected`) : "Not connected"}</small>
                </span>
              </button>
            );
          })}
        </div>
      </header>

      <EditorScene key={panel.id} panel={panel} />

      <section className="zplug-get">
        <DownloadSlab panel={panel} />
        <div className="zplug-copies">
          <h2>Signed in to this workspace</h2>
          {conn.items === null ? null : mine.length ? (
            <ConnectionRows list={mine} busy={conn.busy} onDisconnect={(c) => void conn.disconnect(c)} />
          ) : (
            <p className="zplug-empty">
              No {panel.app} panel yet. Once it is installed, press Sign in in the panel and type its code here.
            </p>
          )}
          <div className="zplug-code">
            <label htmlFor="panel-code">The code your panel shows</label>
            <CodeConnect onConnected={() => void conn.reload()} compact />
          </div>
        </div>
      </section>

      <section className="zplug-setup" aria-labelledby="zplug-setup-h">
        <h2 id="zplug-setup-h">Set up in {steps.length} steps</h2>
        <ol className="zplug-ruler">
          {steps.map((s, i) => (
            <li key={s.title}>
              <span className="zplug-marker" aria-hidden>
                {i + 1}
              </span>
              <b>{s.title}</b>
              <p>{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <p className="zplug-foot">{LICENSE_LINE}</p>
    </main>
  );
}
