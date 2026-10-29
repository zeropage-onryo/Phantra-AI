/* The two editor panels on /studio/plugins (2026-10-23). The download is the
   one fact that moves: content/downloads.json read through lib/downloads.ts,
   so a button links a file only once that build is up. */
import { downloadOf, type Download, type Entry, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

export type Panel = { id: PanelId; app: string; logo: string };

export const PANELS: Panel[] = [
  { id: "resolve", app: "DaVinci Resolve", logo: "/brand/plugins/davinci-resolve.svg" },
  { id: "premiere", app: "Premiere Pro", logo: "/brand/plugins/premiere-pro.svg" },
];

export const panelById = (id: string | null | undefined): Panel => PANELS.find((p) => p.id === id) ?? PANELS[0];

export const downloadFor = (id: PanelId): Download => downloadOf(id, DOWNLOADS as Record<PanelId, Entry>);

export function PanelLogo({ panel, size = 36 }: { panel: Panel; size?: number }) {
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={panel.logo} alt="" width={size} height={size} style={{ width: size, height: size }} className="shrink-0 rounded-[6px]" />;
}
