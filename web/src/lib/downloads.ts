// The editor panels' downloads (docs/tasks/task-plugin-repos.md, Part 2). The
// builds are made in the panels' own private repos and uploaded by
// ops/upload_plugin_r2.py to site/downloads/<plugin>/<version>/<file>, beside
// a SHA256SUMS. content/downloads.json is the one list the page reads: a
// panel is offered only once it is `live` AND its size and sha256 are filled
// in from the upload's report, so a page can never link a file that is not up.
// Pure and import-free: tests/downloads.test.mjs runs it under node --test,
// and the page hands it the JSON.
//
// Two panels (2026-11-03): `resolve` is a Mac .pkg; `adobe` is ONE extension
// for Premiere Pro and After Effects (phantra-premiere-plugin 0.3.0, CEP),
// shipped as a Mac .pkg and, for Windows, a .zxp that aescripts' ZXP Installer
// opens. Each file has its own size and sha256, so each is offered on its own.

export const DOWNLOAD_BASE = "https://media.phantra.ai/site/downloads";

export type PanelId = "resolve" | "adobe";
export type Os = "mac" | "windows";
export type Build = { size: number | null; sha256: string | null };
/** The Mac file's size and sha256 sit at the top (the first shape); a
 *  Windows file, where the panel has one, is `windows`. */
export type Entry = Build & { version: string; live: boolean; windows?: Build | null };

const FILES: Record<PanelId, Partial<Record<Os, string>>> = {
  resolve: { mac: ".pkg" },
  adobe: { mac: ".pkg", windows: ".zxp" },
};

export type Download = {
  id: PanelId;
  os: Os;
  version: string;
  /** null where the panel ships nothing for that OS */
  file: string | null;
  /** null until the build is up: the page shows "Coming soon" and no link */
  url: string | null;
  size: number | null;
  sha256: string | null;
};

/** The OSes a panel ships for, Mac first. */
export function osesOf(id: PanelId): Os[] {
  return (["mac", "windows"] as Os[]).filter((os) => FILES[id][os]);
}

export function fileName(id: PanelId, version: string, os: Os = "mac"): string | null {
  const ext = FILES[id][os];
  return ext ? `phantra-${id}-plugin-${version}${ext}` : null;
}

function ready(e: Entry, build: Build | null | undefined): build is Build & { size: number; sha256: string } {
  return Boolean(
    e.live && build && typeof build.size === "number" && build.size > 0 && /^[0-9a-f]{64}$/.test(build.sha256 ?? ""),
  );
}

export function downloadOf(id: PanelId, entries: Record<PanelId, Entry>, os: Os = "mac"): Download {
  const e = entries[id];
  const file = fileName(id, e.version, os);
  const build = os === "mac" ? e : e.windows;
  const up = file !== null && ready(e, build);
  return {
    id,
    os,
    version: e.version,
    file,
    url: up ? `${DOWNLOAD_BASE}/${id}/${e.version}/${file}` : null,
    size: up ? build.size : null,
    sha256: up ? build.sha256 : null,
  };
}

/** "48 KB", "1.2 MB": what a download button says beside its version. */
export function humanSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
