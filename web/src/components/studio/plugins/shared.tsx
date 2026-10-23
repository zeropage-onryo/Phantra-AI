"use client";

/* The editor panels inside the studio (2026-10-23, Mike: the Plugins tab's
   DaVinci Resolve and Premiere Pro rows are live and open this page). One
   set of facts for every layout of /studio/plugins: the panels' own READMEs
   (the private repos phantra-resolve-plugin and phantra-premiere-plugin),
   the same as the public /download page. The download is the one fact that
   moves: content/downloads.json, read through lib/downloads.ts, so a button
   exists only once a build is up.

   The live parts come from the panels' own API door, the same calls the
   Settings > Connections > Apps card makes: which copies of a panel are
   signed in to this workspace, and approving a code a panel shows. */
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Check, Download as DownloadIcon } from "lucide-react";
import { ApiError } from "@/lib/api";
import {
  approvePluginLink,
  getPluginLink,
  listPluginConnections,
  revokePluginConnection,
  type PluginConnection,
  type PluginLinkPreview,
} from "@/lib/studio-api";
import { downloadOf, humanSize, type Download, type Entry, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

export type Step = { title: string; body: string };

export type Panel = {
  id: PanelId;
  app: string;
  /** the client label the API gives a connected copy */
  client: string;
  logo: string;
  needs: string;
  does: string;
  features: { title: string; body: string }[];
  install: Step[];
};

export const SIGN_IN: Step[] = [
  { title: "Press Sign in", body: "The panel shows a code like KDPX-7QHR and opens phantra.ai/studio/link." },
  { title: "Type the code", body: "Type it here or on that page and press Connect. The panel signs in by itself." },
];

export const PANELS: Panel[] = [
  {
    id: "resolve",
    app: "DaVinci Resolve",
    client: "DaVinci Resolve",
    logo: "/brand/plugins/davinci-resolve.svg",
    needs: "DaVinci Resolve Studio 19.0.2 or newer on macOS. The free version doesn't load Workflow Integrations.",
    does: "Your Library in the Media Pool, and images, video and effects made from the clip you're cutting.",
    features: [
      { title: "Library", body: "Import into a Phantra bin, or Insert at the playhead on a free track." },
      { title: "Make", body: "Images, video and effects, each priced in credits and confirmed before it runs." },
      { title: "From the timeline", body: "Send the clip or the frame at the playhead. Sending is free." },
    ],
    install: [
      { title: "Quit Resolve, open the installer", body: "Double-click the .pkg, press Continue and type your Mac password." },
      { title: "Open the panel", body: "Workspace, Workflow Integrations, Phantra." },
    ],
  },
  {
    id: "premiere",
    app: "Premiere Pro",
    client: "Premiere Pro",
    logo: "/brand/plugins/premiere-pro.svg",
    needs: "Adobe Premiere Pro 25.6 or newer, with the Creative Cloud app.",
    does: "Your Library in a Phantra bin, and the selected clip or frame sent up to edit, then brought back.",
    features: [
      { title: "Library", body: "Import into a Phantra bin, or drop it at the playhead." },
      { title: "Make", body: "Images, video and effects on a Library item, each priced before it runs." },
      { title: "From the timeline", body: "Send the selected clip or the frame at the playhead." },
    ],
    install: [
      { title: "Install the .ccx file", body: "Double-click it; the Creative Cloud app adds the panel." },
      { title: "Open the panel", body: "Window, Extensions (or UXP Plugins), Phantra." },
    ],
  },
];

export const panelById = (id: string | null | undefined): Panel => PANELS.find((p) => p.id === id) ?? PANELS[0];

export const stepsFor = (panel: Panel): Step[] => [...panel.install, ...SIGN_IN];

export const downloadFor = (id: PanelId): Download => downloadOf(id, DOWNLOADS as Record<PanelId, Entry>);

/** The copies of each panel signed in to this workspace (Settings > Connections > Apps). */
export function useConnections() {
  const [items, setItems] = useState<PluginConnection[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const load = useCallback(async () => {
    try {
      setItems((await listPluginConnections()).items);
    } catch {
      setItems([]);
    }
  }, []);
  useEffect(() => {
    // the same first read as Settings > Connections > Apps (the state is set in the callback)
    listPluginConnections()
      .then((r) => setItems(r.items))
      .catch(() => setItems([]));
  }, []);
  const disconnect = async (c: PluginConnection) => {
    setBusy(c.id);
    try {
      await revokePluginConnection(c.id);
      await load();
    } finally {
      setBusy(null);
    }
  };
  const forPanel = (panel: Panel) => (items ?? []).filter((c) => c.client === panel.client);
  return { items, busy, disconnect, reload: load, forPanel };
}

export function when(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/* ── small pieces every layout draws ── */

export function PanelLogo({ panel, size = 36 }: { panel: Panel; size?: number }) {
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={panel.logo} alt="" width={size} height={size} style={{ width: size, height: size }} className="shrink-0 rounded-[10px]" />;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--dim)]">{children}</span>;
}

export function Pill({ tone = "neutral", children }: { tone?: "neutral" | "ok" | "signal"; children: ReactNode }) {
  const look =
    tone === "ok"
      ? "border-[color-mix(in_srgb,var(--ok)_45%,transparent)] text-[var(--ok)]"
      : tone === "signal"
        ? "border-[color-mix(in_srgb,var(--signal)_45%,transparent)] text-[var(--signal)]"
        : "border-[var(--edge-hi)] text-[var(--bone-2)]";
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12px] ${look}`}>{children}</span>;
}

export function ConnectedPill({ count }: { count: number }) {
  return count > 0 ? (
    <Pill tone="ok">
      <span className="size-1.5 rounded-full bg-[var(--ok)]" aria-hidden />
      {count === 1 ? "Connected" : `${count} connected`}
    </Pill>
  ) : (
    <Pill>Not connected</Pill>
  );
}

/** The download: a button once the build is up, otherwise said plainly. */
export function DownloadButton({ panel, wide }: { panel: Panel; wide?: boolean }) {
  const d = downloadFor(panel.id);
  if (!d.url || d.size === null) {
    return (
      <div className={`flex flex-wrap items-center gap-3 ${wide ? "w-full" : ""}`}>
        <span
          aria-disabled="true"
          className="inline-flex h-10 items-center gap-2 rounded-[12px] border border-[var(--edge-hi)] px-4 text-[14px] text-[var(--dim)]"
        >
          <DownloadIcon className="size-4" aria-hidden /> Download on the way
        </span>
        <span className="font-mono text-[12px] text-[var(--dim)]">v{d.version}</span>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <a
        href={d.url}
        download={d.file}
        className="inline-flex h-10 items-center gap-2 rounded-[12px] bg-[var(--signal-dim)] px-4 text-[14px] font-medium text-[var(--on-signal)] hover:bg-[var(--signal-dim-hi)]"
      >
        <DownloadIcon className="size-4" aria-hidden /> Download
      </a>
      <span className="font-mono text-[12px] text-[var(--bone-3)]">
        v{d.version} · {humanSize(d.size)}
      </span>
    </div>
  );
}

export function StepList({ steps, done = 0, numbered = true }: { steps: Step[]; done?: number; numbered?: boolean }) {
  return (
    <ol className="divide-y divide-[var(--line)] border-y border-[var(--line)]">
      {steps.map((s, i) => (
        <li key={s.title} className="flex gap-4 py-3.5">
          {i < done ? (
            <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-[var(--ok)] text-[var(--ground)]">
              <Check className="size-3" strokeWidth={3} aria-hidden />
            </span>
          ) : numbered ? (
            <span className="w-5 shrink-0 pt-0.5 font-mono text-[12px] text-[var(--dim)]">{String(i + 1).padStart(2, "0")}</span>
          ) : null}
          <div>
            <p className="text-[14px] font-medium text-[var(--text)]">{s.title}</p>
            <p className="mt-0.5 text-[13px] leading-relaxed text-[var(--bone-3)]">{s.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

const CODE_SHAPE = /^[A-Z0-9]{4}-?[A-Z0-9]{4}$/;
const tidy = (raw: string) => {
  const t = raw.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
  return t.length > 4 ? `${t.slice(0, 4)}-${t.slice(4)}` : t;
};

/** Type the code a panel shows, see which app is asking, Connect. The same
 *  two calls as /studio/link, and the same rule: the code is only ever
 *  typed, never taken from an address. */
export function CodeConnect({ onConnected, compact }: { onConnected?: () => void; compact?: boolean }) {
  const [code, setCode] = useState("");
  const [preview, setPreview] = useState<PluginLinkPreview | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const check = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    if (!CODE_SHAPE.test(code)) {
      setMsg({ tone: "err", text: "A code is 8 letters and numbers, like KDPX-7QHR." });
      return;
    }
    setBusy(true);
    try {
      setPreview(await getPluginLink(code));
    } catch (err) {
      setMsg({ tone: "err", text: err instanceof ApiError ? err.message : "Couldn't check that code." });
    } finally {
      setBusy(false);
    }
  };
  const connect = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      const made = await approvePluginLink(preview.code);
      setMsg({ tone: "ok", text: `${made.connection.client} is connected. Go back to it; it signs in on its own.` });
      setPreview(null);
      setCode("");
      onConnected?.();
    } catch (err) {
      setMsg({ tone: "err", text: err instanceof ApiError ? err.message : "Couldn't connect. Get a new code from the panel." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      {preview ? (
        <div className="rounded-[14px] border border-[var(--edge)] bg-[var(--well)] p-4">
          <p className="text-[14px] text-[var(--text)]">
            <b>{preview.client}</b>
            {preview.device ? ` (it says it's on ${preview.device})` : ""} wants to use your studio
            {preview.workspace ? ` ${preview.workspace}` : ""}.
          </p>
          <p className="mt-2 text-[12px] leading-relaxed text-[var(--bone-3)]">
            Only connect a code your own {preview.client} panel is showing you right now.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void connect()}
              className="h-9 rounded-[10px] bg-[var(--signal-dim)] px-4 text-[14px] font-medium text-[var(--on-signal)] hover:bg-[var(--signal-dim-hi)] disabled:opacity-60"
            >
              {busy ? "Connecting…" : `Connect ${preview.client}`}
            </button>
            <button type="button" onClick={() => setPreview(null)} className="h-9 rounded-[10px] border border-[var(--edge-hi)] px-4 text-[14px] text-[var(--bone)]">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={check} className={`flex gap-2 ${compact ? "" : "flex-wrap"}`}>
          <label htmlFor="panel-code" className="sr-only">
            The code your panel shows
          </label>
          <input
            id="panel-code"
            value={code}
            onChange={(e) => setCode(tidy(e.target.value))}
            placeholder="KDPX-7QHR"
            autoComplete="off"
            spellCheck={false}
            className="h-10 min-w-0 flex-1 rounded-[12px] border border-[var(--edge-hi)] bg-[var(--well)] px-3.5 font-mono text-[16px] tracking-[0.2em] text-[var(--text)] placeholder:text-[var(--dimmer)] focus:border-[var(--signal)] focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || code.length < 9}
            className="h-10 shrink-0 rounded-[12px] border border-[var(--edge-hi)] px-4 text-[14px] text-[var(--text)] hover:bg-[var(--raise)] disabled:opacity-50"
          >
            {busy ? "Checking…" : "Check code"}
          </button>
        </form>
      )}
      {msg ? (
        <p className={`mt-2 text-[13px] ${msg.tone === "ok" ? "text-[var(--ok)]" : "text-[var(--danger-hi)]"}`}>{msg.text}</p>
      ) : null}
    </div>
  );
}

export function ConnectionRows({
  list,
  busy,
  onDisconnect,
}: {
  list: PluginConnection[];
  busy: number | null;
  onDisconnect: (c: PluginConnection) => void;
}) {
  if (!list.length) return <p className="text-[13px] text-[var(--dim)]">No copy connected yet.</p>;
  return (
    <ul className="divide-y divide-[var(--line)]">
      {list.map((c) => (
        <li key={c.id} className="flex items-center gap-3 py-2.5">
          <span className="size-1.5 shrink-0 rounded-full bg-[var(--ok)]" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] text-[var(--text)]">{c.device || c.client}</p>
            <p className="text-[12px] text-[var(--dim)]">
              Connected {when(c.created_at)} · last used {when(c.last_used_at)}
            </p>
          </div>
          <button
            type="button"
            disabled={busy === c.id}
            onClick={() => onDisconnect(c)}
            className="h-8 shrink-0 rounded-[10px] border border-[var(--edge-hi)] px-3 text-[12px] text-[var(--bone)] hover:bg-[var(--raise)]"
          >
            {busy === c.id ? "…" : "Disconnect"}
          </button>
        </li>
      ))}
    </ul>
  );
}

export const LICENSE_LINE = (
  <>
    Free to install and use with your Phantra account, under the{" "}
    <a href="/download/license" className="underline underline-offset-4 hover:text-[var(--text)]">
      Phantra Plugin License
    </a>
    . Signed in with a code, never a password; disconnect any copy here or under Settings, Connections, Apps.
  </>
);
