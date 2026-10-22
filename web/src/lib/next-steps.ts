/* Proactive next steps after a render (2026-10-22, vesper_v2;
   docs/tasks/task-vesper-v2.md).

   Once every shot of a scene has its clip, the turn offers what usually
   comes next: Add Sound Pass, Cut a vertical version, Make 3 ad variants.
   EACH ONE OPENS A PRICED CARD AND NEVER RUNS: a sound pass is the
   add-sound effect's card, a vertical cut the reframe (or, once the free
   looks land, Vertical Ready) card, and the variants a plan card of three
   scenes whose clips each wait at their own price.

   Pure: tests/vesper-v2.test.mjs runs this file as it is. */
import type { Made } from "./composer";
import type { Plan, PlanStep } from "./make-plan";

export type NextStep = {
  id: "sound" | "vertical" | "variants";
  label: string;
  /** the tooltip: what the click opens, and that nothing runs */
  title: string;
  kind: "effect" | "plan";
  /** kind "effect": the effects table's id */
  effect?: string;
};

const CARD = "Opens a priced card. Nothing runs until you approve.";

/** every shot of a written scene has its clip (or the whole scene does) */
export function rendered(m: Pick<Made, "parts" | "sceneClip">): boolean {
  const parts = m.parts ?? [];
  return parts.length ? parts.every((p) => !!p.media_url) : !!m.sceneClip;
}

/** The steps to offer under a rendered scene, from what the effects
    table has today; [] for anything that is not a rendered scene. */
export function nextStepsFor(
  m: Pick<Made, "output" | "parts" | "sceneClip" | "conceptId" | "prompt">,
  has: { effects: string[] },
): NextStep[] {
  if (m.output !== "video" || !rendered(m)) return [];
  const out: NextStep[] = [];
  if (has.effects.includes("add-sound")) {
    out.push({ id: "sound", label: "Add Sound Pass", title: `Sound to the picture (MMAudio). ${CARD}`, kind: "effect", effect: "add-sound" });
  }
  const vertical = ["vertical_ready", "reframe"].find((e) => has.effects.includes(e));
  if (vertical) {
    out.push({
      id: "vertical",
      label: "Cut a vertical version",
      title: `A 9:16 version${vertical === "vertical_ready" ? ", free" : " (reframe)"}. ${CARD}`,
      kind: "effect",
      effect: vertical,
    });
  }
  if (m.conceptId && (m.prompt ?? "").trim()) {
    out.push({ id: "variants", label: "Make 3 ad variants", title: `Three takes on this scene as a plan; each clip waits at its own price. ${CARD}`, kind: "plan" });
  }
  return out;
}

const ANGLES = [
  "a different opening angle and a faster cut",
  "a slower, closer take on the subject",
  "a bolder colour and a punchier last beat",
];

/** A plan of three variant scenes, each followed by its render step --
    the render steps always wait at their price (lib/make-plan.ts). null
    when there is no prompt to vary. */
export function variantsPlan(m: Pick<Made, "prompt" | "seconds" | "title">, id: string): Plan | null {
  const prompt = (m.prompt ?? "").trim();
  if (!prompt) return null;
  // the shape lib/make-plan.ts planOf gives a plan, built here so this file
  // stays import-free; every step starts pending and the plan unstarted
  const steps: PlanStep[] = ANGLES.map((angle, i) => ({
    n: i + 1,
    do: "scene",
    args: { prompt: `${prompt}\n\nVariant ${i + 1} of 3: ${angle}.`, ...(m.seconds ? { seconds: m.seconds } : {}) },
    why: `Variant ${i + 1}: ${angle}`,
    uses: [],
    status: "pending",
  }));
  for (const n of [1, 2, 3]) {
    steps.push({ n: steps.length + 1, do: "render", args: {}, why: `Clip of variant ${n}`, uses: [], scene: n, status: "pending" });
  }
  return { id, summary: `Three variants of ${m.title || "this scene"}, each clip priced on its own`, steps, approved: [] };
}
