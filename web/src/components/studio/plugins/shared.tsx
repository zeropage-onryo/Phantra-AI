/* The editor panels on /studio/plugins (2026-10-23; the Adobe panel covers
   Premiere Pro AND After Effects since 2026-11-03). The download is the one
   fact that moves: content/downloads.json read through lib/downloads.ts, so a
   button links a file only once that build is up. */
import { downloadOf, osesOf, type Download, type Entry, type Os, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

export type Panel = {
  id: PanelId;
  app: string;
  /** one logo per app the panel lives in */
  logos: string[];
  /** the old one-app anchors (#premiere, #aftereffects) still open the panel */
  aliases?: string[];
};

export const PANELS: Panel[] = [
  { id: "resolve", app: "DaVinci Resolve", logos: ["/brand/plugins/davinci-resolve.svg"] },
  {
    id: "adobe",
    app: "Premiere Pro & After Effects",
    logos: ["/brand/plugins/premiere-pro.svg", "/brand/plugins/after-effects.svg"],
    aliases: ["premiere", "aftereffects"],
  },
];

export const panelById = (id: string | null | undefined): Panel =>
  PANELS.find((p) => p.id === id || p.aliases?.includes(id ?? "")) ?? PANELS[0];

export const downloadFor = (id: PanelId, os: Os = "mac"): Download =>
  downloadOf(id, DOWNLOADS as Record<PanelId, Entry>, os);

export const downloadsFor = (id: PanelId): Download[] => osesOf(id).map((os) => downloadFor(id, os));

export function PanelLogo({ panel, size = 36 }: { panel: Panel; size?: number }) {
  return (
    <span className="inline-flex shrink-0 items-center" style={{ gap: Math.round(size / 6) }}>
      {panel.logos.map((src) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={src} src={src} alt="" width={size} height={size} style={{ width: size, height: size }} className="shrink-0 rounded-[6px]" />
      ))}
    </span>
  );
}
