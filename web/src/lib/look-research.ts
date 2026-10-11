/* A look researched by name (2026-10-11; item 10 of
   docs/tasks/task-studio-agent.md, src/look_research.py).

   The brain's research_look reads the web for what a named film, person,
   brand or era LOOKS like and hands back labelled lines; the reply carries
   what it read (`reply.research`) so the thread can say where the look came
   from, and a look the person asks to keep comes back as a set_project_look
   proposal the confirm card saves to the project.

   This is the page's half, with nothing imported, so
   tests/look-research.test.mjs runs it as it is: how a stored look splits
   into its labelled lines, which source is safe to link, and the one line a
   research record says. */

export type LookSource = { title: string; host: string; url: string };
export type LookResearch = {
  subject: string;
  kind?: string;
  ok: boolean;
  lines: { label: string; text: string }[];
  sources: LookSource[];
  /** whether any web page stood behind the look */
  checked: boolean;
  note?: string;
};

/** the write the brain proposes inside a project, and the read behind it */
export const LOOK_TOOL = "set_project_look";
export const RESEARCH_TOOL = "research_look";
export const isLookTool = (tool?: string | null) => tool === LOOK_TOOL;

/** A look as the card draws it: "LABEL: text" lines become label + text,
    any other line is text alone. A label is short, upper-case words -- a
    sentence with a colon in it is not one. */
export function lookLines(look: string | null | undefined): { label: string; text: string }[] {
  const out: { label: string; text: string }[] = [];
  for (const raw of (look ?? "").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const at = line.indexOf(":");
    const head = at > 0 ? line.slice(0, at).trim() : "";
    const labelled = head.length > 0 && head.length <= 40 && /^[A-Z][A-Z &/-]*$/.test(head);
    const text = labelled ? line.slice(at + 1).trim() : line;
    if (text) out.push({ label: labelled ? head : "", text });
  }
  return out;
}

/** Only http(s) is ever linked: a source's address came off the web. */
export function safeHref(url: string | null | undefined): string | null {
  const u = (url ?? "").trim();
  return /^https?:\/\/[^\s"'<>]+$/i.test(u) ? u : null;
}

/** The sources worth showing: one per page, each with a name to show. */
export function shownSources(r: LookResearch | null | undefined): { name: string; href: string | null }[] {
  const seen = new Set<string>();
  const out: { name: string; href: string | null }[] = [];
  for (const s of r?.sources ?? []) {
    const name = (s.host || s.title || "").trim();
    const key = (s.url || name).trim();
    if (!name || seen.has(key)) continue;
    seen.add(key);
    out.push({ name, href: safeHref(s.url) });
  }
  return out;
}

/** What one research record says, in a line. */
export function researchLine(r: LookResearch): string {
  const name = r.subject || "that";
  if (!r.ok) return `Could not research “${name}”${r.note ? `: ${r.note}` : ""}`;
  if (!r.checked) return `The look of “${name}”, from general knowledge. No page could be read, so it is unchecked.`;
  const n = shownSources(r).length;
  return `The look of “${name}”, read from ${n} page${n === 1 ? "" : "s"}`;
}

/** The caption word for the tool's run ("looked at the web"). */
export const RESEARCH_WORDS = "the web";

/** What saving a look does, said on the card before the click. */
export function saveNote(current: string | null | undefined): string {
  return (current ?? "").trim()
    ? "Replaces the look this project has now. Every scene written in the project is held to it."
    : "Every scene written in this project is held to it.";
}

/** A project's look was saved from the chat: the workspace, which holds its
    own copy of the project, takes the new one. Only ever called in a browser. */
export const LOOK_EVENT = "zpf:project-look";
export function announceLook(project: { id: number; look?: string }): void {
  window.dispatchEvent(new CustomEvent(LOOK_EVENT, { detail: { project } }));
}
