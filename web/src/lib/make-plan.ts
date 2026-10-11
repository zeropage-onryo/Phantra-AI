/* A plan: several makes in a row, proposed by the brain as ONE answer
   (src/guide_tools.py make_plan; docs/tasks/task-studio-agent.md item 2).

   "Make an ad from these photos" is a hero still, then the scene, then its
   keyframes, then its clip. The brain used to be able to propose one of
   those per message. Now it proposes the list, and the studio runs it in
   order through the same doors each step always had -- the still's step
   card, the scene writer, the Elements create route, the keyframes
   approve, the scene's priced render -- so every price, charge and job is
   what it was.

   The plan lives on its assistant turn (`Turn.plan`) and is saved with the
   thread. A step's RESULT is an ordinary turn appended under the card (a
   still's step card and tile, a scene's shot tiles); the step only keeps
   the made id that links to it.

   What costs credits waits: with "Ask first" on, a paid step stops at
   `waiting` until its own Approve, beside its price. "Approve all" covers
   only the steps whose price was on the card when it was clicked -- a
   scene's keyframes are priced once the scene exists, so they still ask.

   A CLIP IS NEVER RENDERED ON A BATCH YES (2026-10-11,
   docs/tasks/task-higgsfield-shape.md). A `render` step -- it was `queue`,
   which only sent the scene to a page that approved it -- is priced once
   its scene exists and ALWAYS stops for its own Approve: "Approve all"
   leaves it out, and Auto does not cover it. Its Approve counts only once
   its price is on the card.

   Pure and import-free on purpose: tests/make-plan.test.mjs runs this file as
   it is. */

export const PLAN_TOOL = "make_plan";

export type StepDo = "image" | "scene" | "sheet" | "keep" | "keyframes" | "render";
export type StepStatus = "pending" | "waiting" | "running" | "done" | "failed" | "skipped";

export type PlanStep = {
  /** 1-based, as the card numbers it */
  n: number;
  do: StepDo;
  /** one line from the brain: what this step is for */
  why: string;
  /** the step's own arguments, as its tool takes them */
  args: Record<string, unknown>;
  /** earlier steps whose picture this one is held to */
  uses: number[];
  /** keyframes / render: the scene step it acts on */
  scene?: number;
  status: StepStatus;
  /** why it failed or was skipped, or what it did */
  note?: string;
  /** the turn its result was drawn into (Turn.made.id) */
  madeId?: string;
  conceptId?: number | null;
  image?: string | null;
  /** what it costs, once that is known */
  credits?: number | null;
  /** keyframes: how many stills the quote is for */
  stills?: number;
  /** render: how many clips the quote is for, and on what */
  shots?: number;
  renderer?: string;
  /** the person changed it before it ran */
  edited?: boolean;
};

export type Plan = {
  id: string;
  summary: string;
  steps: PlanStep[];
  /** steps approved ahead of their turn */
  approved: number[];
  started?: boolean;
  /** the person stopped it: nothing further starts until Resume */
  stopped?: boolean;
  /** it finished once, and the conversation around it was cleared then: a
   *  step re-run later must not clear the box a second time */
  closed?: boolean;
};

export type GenerateMode = "ask" | "auto";
export type Phase = "idle" | "running" | "waiting" | "paused" | "finished";

const DOES: StepDo[] = ["image", "scene", "sheet", "keep", "keyframes", "render"];
const PAID: StepDo[] = ["image", "sheet", "keyframes", "render"];
/* what a step used to be called (a plan saved before 2026-10-11) */
const ALIASES: Record<string, StepDo> = { queue: "render" };
/* acts on a scene step earlier in the same plan */
const ON_SCENE: StepDo[] = ["keyframes", "render"];
export const MIN_STEPS = 2;
export const MAX_STEPS = 8;

export const isPaid = (s: PlanStep) => PAID.includes(s.do);
const over = (s: PlanStep) => s.status === "done" || s.status === "skipped";

const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");
const int = (v: unknown) => (typeof v === "number" && Number.isInteger(v) ? v : null);

/** The plan off a proposal's args, as the server cleaned them
    ({summary, steps: [{n, do, args, why, uses, scene}]}). null when it is
    not a plan a card can draw: fewer than two steps a card knows. */
export function planOf(raw: unknown, id: string): Plan | null {
  const a = (raw ?? {}) as { summary?: unknown; steps?: unknown };
  if (!Array.isArray(a.steps)) return null;
  const steps: PlanStep[] = [];
  for (const item of a.steps.slice(0, MAX_STEPS)) {
    const s = (item ?? {}) as Record<string, unknown>;
    const doing = (ALIASES[str(s.do)] ?? str(s.do)) as StepDo;
    if (!DOES.includes(doing)) return null;
    const n = steps.length + 1;
    const args = s.args && typeof s.args === "object" && !Array.isArray(s.args) ? (s.args as Record<string, unknown>) : {};
    const uses = (Array.isArray(s.uses) ? s.uses : []).map(int).filter((u): u is number => u !== null && u >= 1 && u < n);
    const scene = int(s.scene);
    steps.push({
      n,
      do: doing,
      why: str(s.why),
      args,
      uses: [...new Set(uses)],
      ...(scene !== null && scene >= 1 && scene < n ? { scene } : {}),
      status: "pending",
    });
  }
  if (steps.length < MIN_STEPS) return null;
  return { id, summary: str(a.summary), steps, approved: [] };
}

export const stepAt = (plan: Plan, n: number) => plan.steps.find((s) => s.n === n) ?? null;

/** The scene step a keyframes / render step acts on. */
export const sceneOf = (plan: Plan, s: PlanStep) => (s.scene ? stepAt(plan, s.scene) : null);

/** Why a step cannot run, or "" when it can: its scene was skipped, failed
    or never written. A step that only USES an earlier picture is never
    blocked by it -- without the picture it is drawn from its own prompt. */
export function blockedBy(plan: Plan, s: PlanStep): string {
  if (!ON_SCENE.includes(s.do)) return "";
  const scene = sceneOf(plan, s);
  if (!scene || scene.do !== "scene") return "there is no scene step for it";
  if (scene.status === "skipped") return `step ${scene.n} was skipped`;
  if (scene.status === "failed") return `step ${scene.n} did not finish`;
  if (scene.status === "done" && !scene.conceptId) return `step ${scene.n} wrote no scene`;
  return "";
}

/** The step the plan is on: the first one neither done nor skipped. */
export const nextStep = (plan: Plan) => plan.steps.find((s) => !over(s)) ?? null;

export const finished = (plan: Plan) => plan.steps.every(over);

/** A step that asks every time: a clip. Neither "Approve all" nor Auto
    covers it. */
export const alwaysAsks = (s: PlanStep) => s.do === "render";

/** Does this step stop for its own Approve? Only what spends, and only
    when it was not approved ahead of its turn. With Auto on, nothing stops
    -- except a render, which always does. */
export const needsApproval = (plan: Plan, s: PlanStep, mode: GenerateMode) =>
  isPaid(s) && (mode === "ask" || alwaysAsks(s)) && !plan.approved.includes(s.n);

export function phase(plan: Plan): Phase {
  if (finished(plan)) return "finished";
  if (plan.steps.some((s) => s.status === "running")) return "running";
  if (plan.steps.some((s) => s.status === "waiting")) return "waiting";
  return plan.started ? "paused" : "idle";
}

export function patchStep(plan: Plan, n: number, p: Partial<PlanStep>): Plan {
  return { ...plan, steps: plan.steps.map((s) => (s.n === n ? { ...s, ...p } : s)) };
}

/* The plan moved back to an earlier step (an edit, a step brought back):
   a later step that was waiting for its Approve is no longer the one the
   plan is on. It goes back to pending, so the card offers Resume and the
   plan runs from its first unfinished step again. */
const unwait = (plan: Plan): Plan => ({
  ...plan,
  steps: plan.steps.map((s) => (s.status === "waiting" ? { ...s, status: "pending" as const } : s)),
});

/** Skip a step, and with a scene the steps that only exist for it. */
export function skipStep(plan: Plan, n: number): Plan {
  const s = stepAt(plan, n);
  if (!s || s.status === "running" || s.status === "done") return plan;
  let out = patchStep(plan, n, { status: "skipped", note: "skipped" });
  if (s.do === "scene") {
    for (const d of plan.steps) {
      if (d.scene === n && !over(d) && d.status !== "running") {
        out = patchStep(out, d.n, { status: "skipped", note: `step ${n} was skipped` });
      }
    }
  }
  return out;
}

/** Change a step's arguments. One that already ran (or failed) goes back
    to pending with its result forgotten -- so the plan re-runs THAT step
    and nothing else: every other finished step stays finished. */
export function editStep(plan: Plan, n: number, args: Record<string, unknown>): Plan {
  const s = stepAt(plan, n);
  if (!s || s.status === "running") return plan;
  const ran = s.status === "done" || s.status === "failed";
  const next = { ...s.args, ...args };
  // a scene's new words say their own shot count; the brain's old one would
  // only be a stale label on the card
  if (s.do === "scene" && "prompt" in args) delete next.shots;
  let out = patchStep(unwait(plan), n, {
    args: next,
    edited: true,
    ...(ran ? { status: "pending", note: undefined, madeId: undefined, image: undefined, conceptId: undefined } : {}),
  });
  // a scene written again is another scene: what was priced for the old
  // one (its keyframes, its clip) is priced again, and approved again
  const stale = s.do === "scene" ? plan.steps.filter((d) => d.scene === n && !over(d)).map((d) => d.n) : [];
  for (const d of stale) out = patchStep(out, d, { credits: undefined, stills: undefined, shots: undefined, renderer: undefined });
  // an approval was for the step as it read then
  return { ...out, approved: plan.approved.filter((a) => a !== n && !stale.includes(a)) };
}

/** Bring a skipped step back. */
export function restoreStep(plan: Plan, n: number): Plan {
  const s = stepAt(plan, n);
  return s && s.status === "skipped" ? patchStep(unwait(plan), n, { status: "pending", note: undefined }) : plan;
}

export function approveStep(plan: Plan, n: number): Plan {
  const s = stepAt(plan, n);
  // a render is approved at a price: before its scene exists there is none
  if (!s || (alwaysAsks(s) && typeof s.credits !== "number")) return plan;
  return plan.approved.includes(n) ? plan : { ...plan, approved: [...plan.approved, n] };
}

/** "Approve all": every paid step still to run whose price is on the card
    -- never a render, which is approved on its own. */
export function approveAll(plan: Plan, prices: Prices): Plan {
  const ahead = plan.steps
    .filter((s) => !over(s) && isPaid(s) && !alwaysAsks(s) && priceOf(s, prices) !== null)
    .map((s) => s.n);
  return { ...plan, approved: [...new Set([...plan.approved, ...ahead])] };
}

/** The pictures a step is held to: its used steps that drew one. */
export function picturesFor(plan: Plan, s: PlanStep): string[] {
  return s.uses
    .map((u) => stepAt(plan, u))
    .filter((u): u is PlanStep => !!u && u.status === "done" && !!u.image)
    .map((u) => u.image as string);
}

export type Prices = { image: number | null; sheet: number | null };

/** What a step costs in credits, or null while that is not known: a still
    and a sheet are priced by the model picked; a scene's keyframes and its
    clip only once the scene exists (the step carries the quote then).
    Free steps: 0. */
export function priceOf(s: PlanStep, prices: Prices): number | null {
  if (!isPaid(s)) return 0;
  if (typeof s.credits === "number") return s.credits;
  if (s.do === "image") return prices.image;
  if (s.do === "sheet") return prices.sheet;
  return null;
}

/** The total still ahead: the credits that are known, how many paid steps
    carry a price, and how many do not have one on the card yet. */
export function ahead(plan: Plan, prices: Prices): { credits: number; priced: number; unpriced: number } {
  let credits = 0;
  let priced = 0;
  let unpriced = 0;
  for (const s of plan.steps) {
    if (over(s) || !isPaid(s)) continue;
    const p = priceOf(s, prices);
    if (p === null) unpriced += 1;
    else {
      credits += p;
      priced += 1;
    }
  }
  return { credits, priced, unpriced };
}

/** What "Approve all" would approve right now: the priced steps ahead
    that a batch yes covers -- so never a render. */
export function batchOf(plan: Plan, prices: Prices): { credits: number; priced: number } {
  let credits = 0;
  let priced = 0;
  for (const s of plan.steps) {
    if (over(s) || !isPaid(s) || alwaysAsks(s)) continue;
    const p = priceOf(s, prices);
    if (p === null) continue;
    credits += p;
    priced += 1;
  }
  return { credits, priced };
}

/** Is a render still ahead? The card says it asks on its own. */
export const renderAhead = (plan: Plan) => plan.steps.some((s) => !over(s) && alwaysAsks(s));

export const progress = (plan: Plan) => ({
  done: plan.steps.filter((s) => s.status === "done").length,
  of: plan.steps.filter((s) => s.status !== "skipped").length,
});

const KIND: Record<StepDo, string> = {
  image: "Still",
  scene: "Scene",
  sheet: "Element sheet",
  keep: "Keep references",
  keyframes: "Keyframes",
  render: "Render the clip",
};

/** "Scene · 3 shots · 10s" */
export function stepTitle(s: PlanStep): string {
  const bits = [KIND[s.do]];
  if (s.do === "image" && str(s.args.aspect)) bits.push(str(s.args.aspect));
  if (s.do === "scene") {
    const shots = int(s.args.shots);
    const seconds = int(s.args.seconds);
    if (shots) bits.push(`${shots} shot${shots === 1 ? "" : "s"}`);
    if (seconds) bits.push(`${seconds}s`);
  }
  if (s.do === "sheet" && str(s.args.name)) bits.push(str(s.args.name));
  return bits.join(" · ");
}

/** What the step will do, in words: its prompt, or a plain sentence. */
export function stepText(plan: Plan, s: PlanStep): string {
  if (s.do === "image" || s.do === "scene") return str(s.args.prompt);
  if (s.do === "sheet") {
    const wear = str(s.args.notes);
    return `Save ${str(s.args.name) || "this person"} as a character from the attached photos and draw the reference sheet${wear ? `, wearing ${wear}` : ""}.`;
  }
  if (s.do === "keep") {
    const k = Array.isArray(s.args.candidate_ids) ? s.args.candidate_ids.length : 0;
    return `Keep ${k} reference frame${k === 1 ? "" : "s"} from the sheet above and attach ${k === 1 ? "it" : "them"} to the box.`;
  }
  const scene = s.scene ? `the scene from step ${s.scene}` : "the scene";
  return s.do === "keyframes"
    ? `Draw the first frame of each shot in ${scene}, so the clips have something to start from.`
    : `Render the clip of ${scene}. It always waits for you: its price appears here once the plan reaches it, and nothing renders until you press Render.`;
}

/** Can the person still change this step? Everything a step is made from
    is theirs to change (2026-10-11; invideo's editable approve card): the
    words, and the settings that ride with them. */
export const editable = (s: PlanStep) =>
  (s.do === "image" || s.do === "scene" || s.do === "sheet") && s.status !== "running";

/* ── a step's fields ── */
export type StepField =
  | { key: string; label: string; kind: "words"; value: string; required: boolean }
  | { key: string; label: string; kind: "line"; value: string; required: boolean }
  | { key: string; label: string; kind: "choice"; value: string; options: string[] }
  | { key: string; label: string; kind: "number"; value: number | null; min: number; max: number; unit: string };

export type FieldLimits = {
  /** the frames a still can be drawn at; none listed = the field is not offered */
  aspects: string[];
  /** a scene's shortest and longest; null = not known, the field is not offered */
  seconds: { min: number; max: number } | null;
};

/** What a person can change on this step, in the order it is drawn. A step
    that only acts on another (keep, keyframes, render) has nothing to edit. */
export function fieldsOf(s: PlanStep, limits: FieldLimits): StepField[] {
  if (s.do === "image") {
    const out: StepField[] = [{ key: "prompt", label: "What to draw", kind: "words", value: str(s.args.prompt), required: true }];
    if (limits.aspects.length) {
      const now = str(s.args.aspect);
      out.push({ key: "aspect", label: "Shape", kind: "choice", value: limits.aspects.includes(now) ? now : "", options: limits.aspects });
    }
    return out;
  }
  if (s.do === "scene") {
    const out: StepField[] = [{ key: "prompt", label: "The scene", kind: "words", value: str(s.args.prompt), required: true }];
    if (limits.seconds) {
      out.push({ key: "seconds", label: "Length", kind: "number", value: int(s.args.seconds) || null, min: limits.seconds.min, max: limits.seconds.max, unit: "s" });
    }
    return out;
  }
  if (s.do === "sheet") {
    return [
      { key: "name", label: "Saved as", kind: "line", value: str(s.args.name), required: true },
      { key: "notes", label: "Outfit", kind: "line", value: str(s.args.notes), required: false },
    ];
  }
  return [];
}

/** A person's edit, held to what the step can take: a key the step does not
    have is dropped, a choice off the list is dropped, a number is clamped
    and "" clears an optional one. A required field left empty refuses the
    whole edit (null): a step with no words cannot run. Returns only what
    CHANGED -- {} means nothing did. */
export function cleanEdit(s: PlanStep, draft: Record<string, unknown>, limits: FieldLimits): Record<string, unknown> | null {
  const out: Record<string, unknown> = {};
  for (const f of fieldsOf(s, limits)) {
    if (!(f.key in draft)) continue;
    const raw = draft[f.key];
    if (f.kind === "words" || f.kind === "line") {
      const text = String(raw ?? "").trim();
      if (!text && f.required) return null;
      if (text !== f.value) out[f.key] = text;
    } else if (f.kind === "choice") {
      const pick = String(raw ?? "");
      if (f.options.includes(pick) && pick !== f.value) out[f.key] = pick;
    } else {
      if (raw === "" || raw === null || raw === undefined) continue;
      const n = Math.round(Number(raw));
      if (!Number.isFinite(n)) continue;
      const held = Math.max(f.min, Math.min(f.max, n));
      if (held !== f.value) out[f.key] = held;
    }
  }
  return out;
}

/* ── the plan against the balance ──
   invideo's users learn what a job costs when the credits are gone. The
   card says it before Start: what is still to spend, what the account has,
   and how far short it is when it is short. */
export type Budget = {
  credits: number;
  unpriced: number;
  /** how many credits short; 0 when it fits, is not charged, or the balance is not known */
  short: number;
  line: string;
};

export function budget(
  plan: Plan,
  prices: Prices,
  account: { available: number | null; exempt: boolean },
  mode: GenerateMode,
): Budget {
  const total = ahead(plan, prices);
  if (!total.priced && !total.unpriced) return { credits: 0, unpriced: 0, short: 0, line: "Nothing left in this plan costs credits" };
  const later = total.unpriced ? " · keyframes and the clip are priced once the scene is written" : "";
  // with Auto on nothing stops -- except a render, which always does
  const asks = mode === "ask" ? " · each paid step asks first" : renderAhead(plan) ? " · the clip asks first" : "";
  if (account.exempt) return { credits: total.credits, unpriced: total.unpriced, short: 0, line: `This account is not charged${later}${asks}` };
  const n = (v: number) => v.toLocaleString("en-US");
  const have = account.available;
  const short = have === null ? 0 : Math.max(total.credits - Math.max(have, 0), 0);
  const against = have === null ? "" : short ? ` · you have ${n(Math.max(have, 0))}, ${n(short)} short` : ` · you have ${n(have)}`;
  return { credits: total.credits, unpriced: total.unpriced, short, line: `Still to spend: ${n(total.credits)} credits${against}${later}${asks}` };
}

export type MadeLike = { status: string; image?: string | null; conceptId?: number | null };

/** After a reload, or when a result landed while nobody was looping: bring
    each step in line with the turn its result was drawn into, and put a
    step that says "running" with nothing behind it back to pending.
    Returns the SAME plan object when nothing changed. */
export function reconcile(plan: Plan, mades: Record<string, MadeLike | undefined>, live: number[] = []): Plan {
  let out = plan;
  for (const s of plan.steps) {
    const m = s.madeId ? mades[s.madeId] : undefined;
    const drew = !!m && m.status === "done" && (s.do === "scene" ? !!m.conceptId : !!m.image);
    if (s.status === "failed") {
      // its own card's "Approve again" ran it once more, outside the plan
      if (m && m.status === "running") out = patchStep(out, s.n, { status: "running", note: undefined });
      else if (drew) out = patchStep(out, s.n, { status: "done", image: m?.image ?? null, conceptId: m?.conceptId ?? null, note: undefined });
      continue;
    }
    if (s.status !== "running") continue;
    if (m && m.status === "running") continue;
    if (m && m.status === "done") {
      out = patchStep(out, s.n, drew
        ? { status: "done", image: m.image ?? null, conceptId: m.conceptId ?? null, note: undefined }
        : { status: "failed", note: s.do === "scene" ? "no scene was written" : "nothing was drawn" });
      continue;
    }
    if (m) {
      out = patchStep(out, s.n, { status: "failed", note: m.status === "stopped" ? "stopped" : "did not finish" });
      continue;
    }
    if (!live.includes(s.n)) out = patchStep(out, s.n, { status: "pending", note: "interrupted" });
  }
  return out;
}
