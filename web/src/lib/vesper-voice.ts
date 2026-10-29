/* What Vesper says on his own (2026-10-27, Mike: "can he be interactive
   sometimes?" -- he speaks up now and then, reacts to what you do, follows
   the cursor, offers tips on Create, and "holds memory on your projects,
   last few assets rendered"). Pure, so web/tests/vesper-voice.test.mjs can
   hold it to that: which line, from what he knows, and how often.

   He speaks "sometimes": one line at most every SPEAK_GAP_MS per tab
   (a reply he is waiting on never counts against it), and a line goes by
   itself after LINE_MS. A tip waits TIP_IDLE_MS of an empty, untouched box.
   Every line is free: nothing here calls a model or spends. */

export const SPEAK_GAP_MS = 3 * 60 * 1000;
export const LINE_MS = 7000;
export const TIP_IDLE_MS = 25 * 1000;

/** what he remembers, read off the studio's own lists (newest first) */
export type RecentProject = { id: number; title: string; scenes: number; rendered: number };
export type RecentRender = { kind: "image" | "video"; model: string; prompt: string; project: string | null };
export type Recent = { projects: RecentProject[]; renders: RecentRender[] };
export const NO_RECENT: Recent = { projects: [], renders: [] };

/** a line, and what tapping it does: put words in the box, or open a project */
export type Line = {
  id: string;
  text: string;
  fill?: string;
  project?: number;
};

const firstName = (who?: string | null) => (who || "").trim().split(/\s+/)[0] || "";
const quoted = (s: string, n = 40) => {
  const t = s.replace(/\s+/g, " ").trim();
  return `“${t.length > n ? `${t.slice(0, n - 1)}…` : t}”`;
};
const what = (r: RecentRender) => (r.kind === "video" ? "clip" : "still");

/** the hello, once per tab: by name, and about the newest project if there is one */
export function greeting(who: string | null | undefined, recent: Recent): Line {
  const hi = `Hey${firstName(who) ? ` ${firstName(who)}` : ""}`;
  const p = recent.projects[0];
  if (p) return { id: `hi-p${p.id}`, text: `${hi} — pick up ${quoted(p.title)}?`, project: p.id };
  return { id: "hi", text: `${hi} — what are we making today?` };
}

/** a make just landed in the box */
export function landed(kind: "image" | "video"): Line {
  return kind === "video"
    ? { id: "landed-v", text: "That one came out. Another take, or join it into a cut?" }
    : { id: "landed-i", text: "Fresh still. Want me to animate it?", fill: "Animate my last still" };
}

export function failed(): Line {
  return { id: "failed", text: "That one didn't go through, and nothing was charged. Try it again?" };
}

/** Tips for an idle, empty box: from his memory first, then general ones.
    `said` holds what he has already offered this tab, so he never repeats
    himself until he has run through the lot. */
export function tips(recent: Recent, said: ReadonlySet<string> = new Set()): Line[] {
  const out: Line[] = [];
  const r = recent.renders[0];
  if (r) {
    const by = r.model ? ` on ${r.model}` : "";
    out.push({
      id: `again-${what(r)}-${r.prompt.slice(0, 24)}`,
      text: `Your last ${what(r)}${by} — want a new take on it?`,
      fill: `Another take of my last ${what(r)}: ${r.prompt}`,
    });
  }
  const p = recent.projects.find((x) => x.scenes > x.rendered) ?? recent.projects[0];
  if (p) {
    const left = p.scenes - p.rendered;
    out.push({
      id: `proj-${p.id}`,
      text:
        left > 0
          ? `${quoted(p.title)} has ${left} scene${left === 1 ? "" : "s"} not rendered yet. Open it?`
          : `Want the next scene for ${quoted(p.title)}?`,
      project: p.id,
    });
  }
  out.push(
    { id: "g-story", text: "Stuck? Give me one sentence and I'll pitch three directions.", fill: "Pitch me three directions for " },
    { id: "g-look", text: "Name a film or a photographer and I'll match its look.", fill: "Match the look of " },
    { id: "g-product", text: "Got a product photo? Drop it in and I'll make an ad.", fill: "Make a 10 second ad for my product" },
  );
  const fresh = out.filter((l) => !said.has(l.id));
  return fresh.length ? fresh : out;
}

/** may he speak now? A line he is waiting on (`urgent`) always may. */
export function maySpeak(lastAt: number | null, now: number, urgent = false): boolean {
  return urgent || lastAt == null || now - lastAt >= SPEAK_GAP_MS;
}

/** Where his gaze goes: -1..1 on each axis toward the pointer, 0 when it is
    far (he only notices what is near him), eased so he never snaps. */
export function gaze(
  me: { x: number; y: number },
  pointer: { x: number; y: number } | null,
  reach = 380,
): { x: number; y: number } {
  if (!pointer) return { x: 0, y: 0 };
  const dx = pointer.x - me.x;
  const dy = pointer.y - me.y;
  const d = Math.hypot(dx, dy);
  if (d > reach || d < 1) return { x: 0, y: 0 };
  const pull = 1 - d / reach;
  const r = (v: number) => Math.round(v * 100) / 100;
  return { x: r((dx / d) * pull), y: r((dy / d) * pull) };
}
