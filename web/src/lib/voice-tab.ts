/* The Voice section (/studio/voice, 2026-10-26, docs/tasks/task-voice-tab.md).

   Mike: "I want voice to have a separate UI section for all our voice
   models." One page, one card per model the server lists (GET /api/voice,
   src/voice_studio.py) -- text to speech and dubbing so far -- so a new
   voice model is a row on the server, not a new page.

   Pure and import-free on purpose: tests/voice-tab.test.mjs runs this file
   as it is. */

export type VoiceKind = "speak" | "library" | "dialogue" | "clone" | "dub";

/** One model on the page (src/voice_studio.py models()). No price in it:
 *  `priced` says HOW it is priced; the number is the card's quote. */
export type VoiceModel = {
  id: string;
  kind: VoiceKind;
  label: string;
  title: string;
  what: string;
  priced: string;
  checked: string;
};

/** GET /api/voice */
export type VoiceMenu = {
  models: VoiceModel[];
  speak: { voices: string[]; default_voice: string; script_max: number };
  library: LibraryMenu;
  dialogue: DialogueMenu;
  clone: CloneMenu;
  dub: {
    languages: { code: string; name: string }[];
    max_seconds: number;
    speakers_max: number;
    label: string;
    checked: string;
  };
  ready: boolean;
  exempt: boolean;
};

export type Paid = { credits: number; charged: boolean };

/** The speak panel as the person has it. */
export type SpeakState = { script: string; voice: string; language: string };

/** A read this visit made (or is making). */
export type Read = {
  id: string;
  status: "running" | "done" | "failed";
  voice: string;
  script: string;
  paid: Paid;
  jobId?: number;
  audio?: string;
  seconds?: number | null;
  url?: string;
  error?: string;
};

/** The model the page opens on: the one the address names, else the first. */
export function pickModel(models: Pick<VoiceModel, "id" | "kind">[], wanted?: string | null): string {
  const w = (wanted ?? "").trim();
  const hit = models.find((m) => m.id === w || m.kind === w);
  return hit?.id ?? models[0]?.id ?? "";
}

export const beginSpeak = (menu?: Pick<VoiceMenu, "speak"> | null): SpeakState => ({
  script: "",
  voice: menu?.speak.default_voice ?? "Rachel",
  language: "",
});

/** What stops a read from being priced: "" when nothing does. */
export function speakMissing(s: SpeakState, menu: Pick<VoiceMenu, "speak">): string {
  const n = s.script.trim().length;
  if (!n) return "Write the words to be read";
  if (n > menu.speak.script_max) return `Keep it under ${menu.speak.script_max.toLocaleString()} characters`;
  if (!menu.speak.voices.includes(s.voice)) return "Pick one of the voices";
  const lang = s.language.trim().toLowerCase();
  if (lang && !/^[a-z]{2}$/.test(lang)) return "The language is a two-letter code, like en or es";
  return "";
}

/** The body /api/voice/speak/{quote,run} take. */
export const speakRequest = (s: SpeakState, projectId?: number | null) => ({
  script: s.script.trim(),
  voice: s.voice,
  language: s.language.trim().toLowerCase(),
  ...(projectId ? { project_id: projectId } : {}),
});

/** The key a read's price depends on. */
export const speakPriceKey = (s: SpeakState) => JSON.stringify(speakRequest(s));

/** "1,234 / 5,000" under the box */
export const charCount = (s: Pick<SpeakState, "script">, max: number) =>
  `${s.script.trim().length.toLocaleString()} / ${max.toLocaleString()}`;

/** "144 credits", or "… · not charged" on an exempt account */
export const priceLine = (p: Paid, exempt = false) =>
  p.charged && !exempt ? `${p.credits.toLocaleString()} credits` : `${p.credits.toLocaleString()} credits · not charged`;

/** A finished job's fields onto its read. */
export function settleRead(r: Read, job: { status: string; error?: string | null; output?: string | null; audio?: string; seconds?: number | null }): Read {
  if (job.status === "done" && job.audio) {
    return { ...r, status: "done", audio: job.audio, seconds: job.seconds ?? null, url: job.output ?? undefined };
  }
  return { ...r, status: "failed", error: job.error || "The voice was not made. Nothing was charged." };
}

/** A read's caption: "Aria · 4.2s · 12 credits" */
export function readLine(r: Pick<Read, "voice" | "seconds" | "paid">, exempt = false): string {
  return [r.voice, r.seconds ? `${r.seconds.toFixed(1)}s` : "", priceLine(r.paid, exempt)].filter(Boolean).join(" · ");
}

/* ── the voice library (MiniMax Speech-02 HD; src/voice_models.py) ── */

export type LibraryMenu = {
  languages: { language: string; voices: { id: string; name: string }[] }[];
  default_voice: string;
  emotions: string[];
  speed: [number, number];
  pitch: [number, number];
  script_max: number;
};

export type LibraryState = { script: string; voice: string; emotion: string; speed: number; pitch: number };

export const beginLibrary = (lib?: Pick<LibraryMenu, "default_voice"> | null): LibraryState => ({
  script: "",
  voice: lib?.default_voice ?? "Wise_Woman",
  emotion: "",
  speed: 1,
  pitch: 0,
});

/** Every library voice id, for "is this one on the list". */
export const libraryVoiceIds = (lib: Pick<LibraryMenu, "languages">) => lib.languages.flatMap((l) => l.voices.map((v) => v.id));

/** A library voice's name ("Calm Woman · English"), else its id. */
export function libraryVoiceName(lib: Pick<LibraryMenu, "languages"> | null | undefined, id: string): string {
  for (const l of lib?.languages ?? []) {
    const v = l.voices.find((x) => x.id === id);
    if (v) return `${v.name} · ${l.language}`;
  }
  return id;
}

/** What stops a library read from being priced: "" when nothing does. */
export function libraryMissing(s: LibraryState, lib: LibraryMenu): string {
  const n = s.script.trim().length;
  if (!n) return "Write the words to be read";
  if (n > lib.script_max) return `Keep it under ${lib.script_max.toLocaleString()} characters`;
  if (!libraryVoiceIds(lib).includes(s.voice)) return "Pick one of the voices";
  if (s.emotion && !lib.emotions.includes(s.emotion)) return "Pick one of the emotions";
  if (!(s.speed >= lib.speed[0] && s.speed <= lib.speed[1])) return `Speed is ${lib.speed[0]} to ${lib.speed[1]}`;
  if (!Number.isInteger(s.pitch) || s.pitch < lib.pitch[0] || s.pitch > lib.pitch[1]) return `Pitch is ${lib.pitch[0]} to ${lib.pitch[1]}`;
  return "";
}

/** The body /api/voice/library/{quote,run} take. */
export const libraryRequest = (s: LibraryState, projectId?: number | null) => ({
  script: s.script.trim(),
  voice: s.voice,
  emotion: s.emotion,
  speed: s.speed,
  pitch: s.pitch,
  ...(projectId ? { project_id: projectId } : {}),
});

/* ── dialogue (VibeVoice 7B; src/voice_models.py) ── */

export type DialogueMenu = { presets: string[]; max_speakers: number; max_lines: number; script_max: number };
export type DialogueLine = { speaker: number; text: string };
export type DialogueState = { speakers: string[]; lines: DialogueLine[] };

/** Two speakers and an empty line each, the first two English presets. */
export function beginDialogue(dia?: Pick<DialogueMenu, "presets"> | null): DialogueState {
  const en = (dia?.presets ?? []).filter((p) => p.includes("[EN]") && !p.includes("Background"));
  const two = en.length >= 2 ? en.slice(0, 2) : (dia?.presets ?? []).slice(0, 2);
  return { speakers: two, lines: two.map((_, i) => ({ speaker: i, text: "" })) };
}

/** "Mary [EN] (Background Music)" -> "Mary · EN · with music" */
export function presetLabel(p: string): string {
  const m = /^(.+?)\s*\[([A-Z]+)\]\s*(\(Background Music\))?$/.exec(p.trim());
  if (!m) return p;
  return [m[1], m[2], m[3] ? "with music" : ""].filter(Boolean).join(" · ");
}

/** Add a speaker (the next preset not yet used, else the first). */
export function addSpeaker(s: DialogueState, dia: Pick<DialogueMenu, "presets" | "max_speakers">): DialogueState {
  if (s.speakers.length >= dia.max_speakers) return s;
  const next = dia.presets.find((p) => !s.speakers.includes(p)) ?? dia.presets[0];
  return next ? { ...s, speakers: [...s.speakers, next] } : s;
}

/** Remove a speaker: their lines go, and the later speakers' numbers move up. */
export function removeSpeaker(s: DialogueState, i: number): DialogueState {
  if (s.speakers.length <= 1 || i < 0 || i >= s.speakers.length) return s;
  return {
    speakers: s.speakers.filter((_, k) => k !== i),
    lines: s.lines.filter((l) => l.speaker !== i).map((l) => (l.speaker > i ? { ...l, speaker: l.speaker - 1 } : l)),
  };
}

/** Add a line for the speaker after the last line's (round the table). */
export function addLine(s: DialogueState, max = 200): DialogueState {
  if (s.lines.length >= max || !s.speakers.length) return s;
  const last = s.lines[s.lines.length - 1];
  const speaker = last ? (last.speaker + 1) % s.speakers.length : 0;
  return { ...s, lines: [...s.lines, { speaker, text: "" }] };
}

const oneLine = (t: string) => t.split(/\s+/).filter(Boolean).join(" ");

/** The script the model is sent, as the server builds it (for the count). */
export const dialogueScript = (s: DialogueState) =>
  s.lines
    .filter((l) => oneLine(l.text))
    .map((l) => `Speaker ${l.speaker}: ${oneLine(l.text)}`)
    .join("\n");

/** What stops a dialogue from being priced: "" when nothing does. */
export function dialogueMissing(s: DialogueState, dia: DialogueMenu): string {
  if (!s.speakers.length) return "Add a speaker";
  if (s.speakers.length > dia.max_speakers) return `Up to ${dia.max_speakers} speakers`;
  if (s.speakers.some((p) => !dia.presets.includes(p))) return "Pick a voice for every speaker";
  const filled = s.lines.filter((l) => oneLine(l.text));
  if (!filled.length) return "Write the first line";
  if (filled.some((l) => /^speaker\s*\d+\s*:/i.test(oneLine(l.text)))) return "Leave out the 'Speaker N:' labels; the studio adds them";
  const used = new Set(filled.map((l) => l.speaker));
  const idle = s.speakers.map((_, i) => i).filter((i) => !used.has(i));
  if (idle.length) return `Speaker ${idle.map((i) => i + 1).join(", ")} has no lines yet`;
  if (dialogueScript(s).length > dia.script_max) return `Keep it under ${dia.script_max.toLocaleString()} characters`;
  return "";
}

/** The body /api/voice/dialogue/{quote,run} take: only the lines with words. */
export const dialogueRequest = (s: DialogueState, projectId?: number | null) => ({
  speakers: s.speakers,
  lines: s.lines.filter((l) => oneLine(l.text)).map((l) => ({ speaker: l.speaker, text: oneLine(l.text) })),
  ...(projectId ? { project_id: projectId } : {}),
});

/* ── cloning your own voice (MiniMax Voice Clone; src/voice_clone.py) ── */

export type ClonedVoice = {
  id: string;
  name: string;
  preview_audio: string | null;
  preview_url?: string | null;
  created_at: string;
  /** when MiniMax deletes it if it is never read in; null once kept */
  expires_at: string | null;
  kept: boolean;
};

export type CloneMenu = {
  consent_line: string;
  min_seconds: number;
  max_seconds: number;
  types: string[];
  name_max: number;
  max_clones: number;
  keep_days: number;
  voices: ClonedVoice[];
};

/** The sample the person uploaded (POST /api/cut/media). */
export type Sample = { audio: string; seconds: number | null; filename: string };
export type CloneState = { name: string; sample: Sample | null };

export const isSampleFile = (name: string, types: string[]) => types.some((t) => name.toLowerCase().endsWith(t));

/** What stops a clone from being priced: "" when nothing does. */
export function cloneMissing(s: CloneState, cm: Pick<CloneMenu, "min_seconds" | "max_seconds" | "name_max" | "max_clones" | "voices">): string {
  if (cm.voices.length >= cm.max_clones) return `You have ${cm.max_clones} voices; remove one first`;
  if (!s.sample) return "Upload your sample";
  const secs = s.sample.seconds;
  if (secs != null && secs < cm.min_seconds) return `The sample is ${secs.toFixed(1)}s; it needs at least ${cm.min_seconds}s`;
  if (secs != null && secs > cm.max_seconds + 0.5) return `The sample is ${Math.round(secs)}s; trim it to ${cm.max_seconds}s`;
  const name = s.name.trim();
  if (!name) return "Name the voice";
  if (name.length > cm.name_max) return `Keep the name under ${cm.name_max} characters`;
  return "";
}

/** The body /api/voice/clone/{quote,run} take; null until there is one. */
export const cloneRequest = (s: CloneState) => (s.sample ? { sample: s.sample.audio, name: s.name.trim().split(/\s+/).join(" ") } : null);

/** "Read it in within 5 days to keep it", "Kept", or "Read it in today to keep it". */
export function keepLine(v: Pick<ClonedVoice, "expires_at" | "kept">, now: Date = new Date()): string {
  if (v.kept || !v.expires_at) return "Kept";
  const ms = new Date(v.expires_at).getTime() - now.getTime();
  const days = Math.ceil(ms / 86_400_000);
  if (days <= 1) return "Read something in it today to keep it";
  return `Read something in it within ${days} days to keep it`;
}

/* ── the stage's starters: each only fills the script ── */
export const VOICE_STARTERS = [
  "Welcome back. Tonight we taste three wines from the same hill, and only one of them is worth the drive.",
  "[whispers] Don't turn around. Whatever you heard in the hallway, it wasn't the wind.",
  "New season, new drop. Doors open Friday at ten. Bring a friend, leave with two.",
  "Thanks for calling. Your order is on its way, and it should reach you by Thursday afternoon.",
];

/** The spend button's words: what the panel makes, and its price. */
export function goLabel(verb: string, quote: Paid | null, pricing: boolean, exempt: boolean): string {
  if (!quote || pricing) return `${verb} · pricing…`;
  const n = quote.credits.toLocaleString("en-US");
  return exempt || !quote.charged ? `${verb} · ${n} credits · not charged` : `${verb} · ${n} credits`;
}

/** Deterministic bar heights (0.15..1) for a read's waveform card: the
    same words always draw the same shape. Not the real audio. */
export function waveBars(seed: string, n = 48): number[] {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
    const base = 0.35 + 0.45 * Math.sin((i / n) * Math.PI);
    out.push(Math.max(0.15, Math.min(1, base * (0.55 + (h % 1000) / 1100))));
  }
  return out;
}
