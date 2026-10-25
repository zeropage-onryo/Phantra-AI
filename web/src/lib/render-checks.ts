/* What a look at each landed clip saw (src/render_qc.py, 2026-10-25):
   per shot ("0" for a scene rendered whole), the problems it found in
   plain words and up to three notes with a time in the clip. Advice
   under a clip already paid for, never a lock. */
export type RenderCheck = { media: string; problems: string[]; notes: string[] };
export type RenderChecks = Record<string, RenderCheck>;

/** One line per problem and note, shot by shot, in shot order; a scene
    rendered whole has no "Shot n:" prefix. Clean clips say nothing. */
export function checkLines(checks: RenderChecks | null | undefined): string[] {
  if (!checks) return [];
  const out: string[] = [];
  for (const key of Object.keys(checks).sort((a, b) => Number(a) - Number(b))) {
    const c = checks[key];
    const head = key === "0" ? "" : `Shot ${key}: `;
    const seen = new Set<string>();
    for (const line of [...(c.problems ?? []), ...(c.notes ?? [])]) {
      const text = line.trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      out.push(head + text.charAt(0).toUpperCase() + text.slice(1));
    }
  }
  return out;
}
