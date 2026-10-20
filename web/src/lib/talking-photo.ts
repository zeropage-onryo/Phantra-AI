/* A talking photo in the composer (src/talking_photo.py through
   /api/talking-photo/*; docs/tasks/task-talking-photo.md, 2026-10-20).

   A photo of a person speaks a voice track. Two ways it starts, both ending
   on one card in the thread: `/talking-photo`, or the brain's talking_photo
   proposal (which may name a still by number and draft the words). The card
   asks for three things -- the photo, the person's word that the face is
   theirs or its owner agreed, and the voice -- and has two priced clicks:
   the voice preview (a typed script read aloud, optional) and the render.

   The voice is an `asset:<id>` either way: an .mp3/.wav uploaded to the
   editor's bin, or the preview the server filed there. A preview belongs to
   the words and the voice it was read from; change either and it is no
   longer the voice the render would use.

   Pure and import-free on purpose: tests/talking-photo.test.mjs runs this
   file as it is. */

export const TALK_TOOL = "talking_photo";
export const AUDIO_TYPES = [".mp3", ".wav"];

/** Something the photo could be (the shape of lib/effects.ts Candidate). */
export type PhotoChoice = {
  /** what the server is sent: `gen:<id>`, else the reference as the
   *  composer holds it (an attachment, an element's photo name) */
  ref: string;
  kind: "image" | "clip";
  thumb?: string;
  from: string;
};

/** GET /api/talking-photo */
export type TalkMenu = {
  voices: string[];
  default_voice: string;
  script_min: number;
  script_max: number;
  audio_min: number;
  audio_cap: number;
  audio_types: string[];
  prompt_max: number;
  ready: boolean;
  exempt: boolean;
};

export type Paid = { credits: number; charged: boolean };

/** The voice the person uploaded (POST /api/cut/media). */
export type VoiceUpload = { audio: string; seconds: number | null; filename: string };

/** A voice preview: running, or read and filed. `script` / `voice` /
 *  `language` are what it was read FROM. */
export type VoicePreview = {
  status: "running" | "done" | "failed";
  jobId?: number;
  script: string;
  voice: string;
  language: string;
  paid: Paid;
  audio?: string;
  seconds?: number | null;
  url?: string;
  error?: string;
};

/** One talking photo, on its way to a clip: saved on its turn (`Turn.talk`). */
export type TalkState = {
  id: string;
  photo: PhotoChoice | null;
  consent: boolean;
  mode: "script" | "upload";
  script: string;
  voice: string;
  /** an ISO 639-1 code, or "" to let the model tell */
  language: string;
  upload?: VoiceUpload;
  preview?: VoicePreview;
  prompt: string;
  /** what Render was pressed at */
  paid?: Paid;
};

/** A new card. The photo is the still the proposal pointed at, else the
    first image attached to the box, else the newest still -- or none, and
    the card asks. Clips are never a photo. */
export function beginTalk(
  all: PhotoChoice[],
  id: string,
  given: { on?: PhotoChoice | null; script?: string | null; prompt?: string | null; voice?: string } = {},
): TalkState {
  const on = given.on && given.on.kind === "image" ? given.on : null;
  return {
    id,
    photo: on ?? all.find((c) => c.kind === "image") ?? null,
    consent: false,
    mode: "script",
    script: (given.script ?? "").trim(),
    voice: given.voice ?? "Rachel",
    language: "",
    prompt: (given.prompt ?? "").trim(),
  };
}

/** The photos the card offers: images only, each once, in order. */
export function photoChoices(all: PhotoChoice[]): PhotoChoice[] {
  const seen = new Set<string>();
  return all.filter((c) => c.kind === "image" && !seen.has(c.ref) && (seen.add(c.ref), true));
}

export const isAudioFile = (name: string) => AUDIO_TYPES.some((t) => name.toLowerCase().endsWith(t));

/** Is the preview the one these words and this voice would make? */
export function previewCurrent(s: Pick<TalkState, "preview" | "script" | "voice" | "language">): boolean {
  const p = s.preview;
  return !!p && p.script === s.script.trim() && p.voice === s.voice && p.language === s.language.trim().toLowerCase();
}

/** The voice the render would use, `asset:<id>`, or null. */
export function voiceOf(s: TalkState): string | null {
  if (s.mode === "upload") return s.upload?.audio ?? null;
  return previewCurrent(s) && s.preview?.status === "done" ? (s.preview.audio ?? null) : null;
}

/** Its measured length, when known. */
export function voiceSeconds(s: TalkState): number | null {
  if (s.mode === "upload") return s.upload?.seconds ?? null;
  return previewCurrent(s) ? (s.preview?.seconds ?? null) : null;
}

/** What stops the PREVIEW from being priced: "" when nothing does. */
export function scriptMissing(s: Pick<TalkState, "script">, menu: Pick<TalkMenu, "script_min" | "script_max">): string {
  const n = s.script.trim().length;
  if (!n) return "Write what the photo should say";
  if (n < menu.script_min) return `A few more words: at least ${menu.script_min} characters (it needs ${4} seconds of voice)`;
  if (n > menu.script_max) return `Keep it under ${menu.script_max.toLocaleString()} characters`;
  return "";
}

/** A voice's length against the model's floor and the plan's cap. */
export function lengthProblem(seconds: number | null | undefined, menu: Pick<TalkMenu, "audio_min" | "audio_cap">): string {
  if (seconds == null) return "";
  if (seconds < menu.audio_min) return `The voice is ${seconds.toFixed(1)}s; it needs at least ${menu.audio_min}s`;
  if (seconds > menu.audio_cap + 0.5) return `The voice is ${seconds.toFixed(1)}s; your plan makes talking clips up to ${menu.audio_cap}s`;
  return "";
}

/** What stops the RENDER from being priced: "" when nothing does. The
    consent box is not here: the price shows before it is ticked. */
export function talkMissing(s: TalkState, menu: Pick<TalkMenu, "audio_min" | "audio_cap">): string {
  if (!s.photo) return "Pick the photo that speaks";
  if (s.mode === "upload" && !s.upload) return "Upload the voice: an .mp3 or .wav";
  if (s.mode === "script" && !voiceOf(s)) {
    return s.preview?.status === "running" && previewCurrent(s) ? "Reading the voice…" : "Preview the voice first: the clip is as long as it is";
  }
  return lengthProblem(voiceSeconds(s), menu);
}

/** The body /api/talking-photo/voice/{quote,run} take. */
export const voiceRequest = (s: Pick<TalkState, "script" | "voice" | "language">) => ({
  script: s.script.trim(),
  voice: s.voice,
  language: s.language.trim().toLowerCase(),
});

/** The body /api/talking-photo/{quote,run} take; null until there is one. */
export function talkRequest(s: TalkState, projectId?: number | null) {
  const audio = voiceOf(s);
  if (!s.photo || !audio) return null;
  return {
    photo: s.photo.ref,
    audio,
    prompt: s.prompt.trim(),
    consent: s.consent,
    ...(projectId ? { project_id: projectId } : {}),
  };
}

/** "1,234 credits", or "… · not charged" on an exempt account */
export const priceLine = (p: Paid, exempt = false) =>
  p.charged && !exempt ? `${p.credits.toLocaleString()} credits` : `${p.credits.toLocaleString()} credits · not charged`;
