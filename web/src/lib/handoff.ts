/* A request handed over from the Claude connector (2026-10-20).

   The Claude listing makes nothing from a prompt: `open_in_studio`
   (src/mcp_server.py) answers a link to Create with the prompt in ?spark=
   and the Image | Video switch in ?kind=. Only that tool writes ?kind=, so
   the two together mark a hand-off, and a hand-off opens CLEAN: no
   leftover attachments or brief from the saved draft, and no remembered
   project unless the link names one (?project=). A remembered project can be
   exploring, where a send only talks -- the opposite of what the person
   came to do. A project the link names keeps its own Explore / Make. */

export type Kind = "image" | "video";

export function handoffKind(params: { get(name: string): string | null }): Kind | null {
  const spark = params.get("spark");
  const kind = params.get("kind");
  return spark && spark.trim() && (kind === "image" || kind === "video") ? kind : null;
}

/** The project Create opens: the link's, else (not on a hand-off) the
    one this browser last used. 0 means none. */
export function openingProject(
  params: { get(name: string): string | null },
  remembered: () => number | null,
): number {
  const named = Number(params.get("project")) || 0;
  if (named) return named;
  // a "Use kit" link (?kit=, lib/kit-use.ts) is a conversation outside any
  // project: a remembered project would hide the kit it asked for
  const kit = Number(params.get("kit"));
  if (Number.isInteger(kit) && kit > 0) return 0;
  return handoffKind(params) ? 0 : remembered() || 0;
}
