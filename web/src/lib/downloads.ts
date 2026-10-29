// The editor panels' downloads (docs/tasks/task-plugin-repos.md, Part 2). The
// builds are made in the panels' own private repos and uploaded by
// ops/upload_plugin_r2.py to site/downloads/<plugin>/<version>/<file>, beside
// a SHA256SUMS. content/downloads.json is the one list the page reads: a
// panel is offered only once it is `live` AND its size and sha256 are filled
// in from the upload's report, so a page can never link a file that is not up.
// Pure and import-free: tests/downloads.test.mjs runs it under node --test,
// and the page hands it the JSON.

export const DOWNLOAD_BASE = "https://media.phantra.ai/site/downloads";

export type PanelId = "resolve" | "premiere";
export type Entry = { version: string; size: number | null; sha256: string | null; live: boolean };

const EXT: Record<PanelId, string> = { resolve: ".pkg", premiere: ".ccx" };

export type Download = {
  id: PanelId;
  version: string;
  file: string;
  /** null until the build is up: the page shows "Coming soon" and no link */
  url: string | null;
  size: number | null;
  sha256: string | null;
};

export function fileName(id: PanelId, version: string): string {
  return `phantra-${id}-plugin-${version}${EXT[id]}`;
}

export function downloadOf(id: PanelId, entries: Record<PanelId, Entry>): Download {
  const e = entries[id];
  const file = fileName(id, e.version);
  const ready = e.live && typeof e.size === "number" && e.size > 0 && /^[0-9a-f]{64}$/.test(e.sha256 ?? "");
  return {
    id,
    version: e.version,
    file,
    url: ready ? `${DOWNLOAD_BASE}/${id}/${e.version}/${file}` : null,
    size: ready ? e.size : null,
    sha256: ready ? e.sha256 : null,
  };
}

/** "48 KB", "1.2 MB": what a download button says beside its version. */
export function humanSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
