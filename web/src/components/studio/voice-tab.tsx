"use client";

/* The Voice section (/studio/voice, 2026-10-26; docs/tasks/task-voice-tab.md),
   behind the `voice_tab` capability (the server page does the 404).

   Every voice model on one page, in the direct generators' layout (Mike,
   2026-10-27: "design the UI to match that of what we have" -- the Image
   page, components/studio/direct-generator.tsx):

     panel (left)   -- the Model menu (the server's list, GET /api/voice,
                       src/voice_studio.py), the picked model's fields, and
                       the one yellow button that spends, carrying its price;
     stage (middle) -- what is being listened to or made, else the starters;
     history (right)-- what this visit made.

   The models: text to speech (ElevenLabs v3), the voice library (MiniMax
   Speech-02 HD), dialogue (VibeVoice 7B), cloning your own voice (MiniMax
   Voice Clone, after the consent line) and dubbing a clip (ElevenLabs
   Dubbing). The price on the button is ALWAYS the server's quote for
   exactly what is on screen, re-asked on every change, and the run carries
   it as `expect_credits`: a moved price is refused (409) and re-asked. */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AudioLines,
  Download,
  Languages,
  LayoutGrid,
  Library,
  MessagesSquare,
  Mic,
  Plus,
  RotateCcw,
  Upload,
  UserRound,
  Wand2,
  X,
} from "lucide-react";
import { cardFonts } from "@/components/studio/card-fonts";
import { ModelMenu, type MenuItem } from "@/components/studio/direct-generator";
import { useShell } from "@/components/studio/shell";
import { ApiError } from "@/lib/api";
import { mediaSrc, newMadeId } from "@/lib/composer";
import { assetId } from "@/lib/continue";
import { TOP_UP_HREF, needsCredits } from "@/lib/out-of-credits";
import { dubMissing, dubRequest, languageName, type DubState } from "@/lib/dubbing";
import {
  VOICE_STARTERS,
  addLine,
  addSpeaker,
  beginDialogue,
  beginLibrary,
  beginSpeak,
  cloneMissing,
  cloneRequest,
  dialogueMissing,
  dialogueRequest,
  dialogueScript,
  goLabel,
  isSampleFile,
  keepLine,
  libraryMissing,
  libraryRequest,
  libraryVoiceName,
  pickModel,
  presetLabel,
  removeSpeaker,
  speakMissing,
  speakRequest,
  waveBars,
  type ClonedVoice,
  type CloneState,
  type DialogueState,
  type LibraryState,
  type Paid,
  type SpeakState,
  type VoiceKind,
  type VoiceMenu,
} from "@/lib/voice-tab";
import {
  announceBalanceChange,
  cutUploadMedia,
  getMedia,
  getRender,
  getVoiceMenu,
  quoteClone,
  quoteDialogue,
  quoteDub,
  quoteLibrary,
  quoteSpeak,
  removeClone,
  renderDownloadHref,
  runClone,
  runDialogue,
  runDub,
  runLibrary,
  runSpeak,
  waitForJob,
  type MediaItem,
} from "@/lib/studio-api";
import "@/components/studio/direct-generator.css";
import "@/components/studio/voice-tab.css";
/* eslint-disable @next/next/no-img-element */

const ICON: Record<VoiceKind, typeof Mic> = { speak: Mic, library: Library, dialogue: MessagesSquare, clone: UserRound, dub: Languages };
const VERB: Record<VoiceKind, string> = {
  speak: "Make the voice",
  library: "Make the voice",
  dialogue: "Make the dialogue",
  clone: "Clone my voice",
  dub: "Dub it",
};

/** Something this visit made, or is making: a read, a dialogue, a clone's
 *  preview (audio), or a dubbed clip (video). */
type Out = {
  id: string;
  kind: VoiceKind;
  media: "audio" | "video";
  status: "running" | "done" | "failed";
  title: string;
  words: string;
  credits: number;
  detail: string;
  src?: string;
  seconds?: number | null;
  asset?: string | null;
  voiceId?: string;
  outOfCredits?: boolean;
};

/** The server's price for `body`, asked again whenever it changes (or
 *  `again` moves); null while something stops it. */
function usePrice<B>(body: B | null, quote: (b: B) => Promise<Paid>, again: number) {
  const [price, setPrice] = useState<Paid | null>(null);
  const [problem, setProblem] = useState("");
  const [pricing, setPricing] = useState(false);
  const asked = useRef(0);
  const key = body ? JSON.stringify(body) : "";
  useEffect(() => {
    if (!body) return;
    const mine = ++asked.current;
    const timer = setTimeout(() => {
      setPricing(true);
      quote(body)
        .then((q) => {
          if (mine !== asked.current) return;
          setPrice({ credits: q.credits, charged: q.charged });
          setProblem("");
        })
        .catch((e) => {
          if (mine !== asked.current) return;
          setPrice(null);
          setProblem(e instanceof Error ? e.message : "That cannot be priced.");
        })
        .finally(() => {
          if (mine === asked.current) setPricing(false);
        });
    }, 350);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key stands for the body
  }, [key, again]);
  return { price: body ? price : null, problem: body ? problem : "", pricing: !!body && pricing };
}

/* ── the page ── */
export function VoiceTab() {
  const { me, toast } = useShell();
  const router = useRouter();
  const params = useSearchParams();
  const [menu, setMenu] = useState<VoiceMenu | null>(null);
  const [menuError, setMenuError] = useState("");
  const [picked, setPicked] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const workspace = me?.account?.slug ?? "";

  // each model keeps its own fields while another is looked at
  const [speak, setSpeak] = useState<SpeakState>(() => beginSpeak(null));
  const [lib, setLib] = useState<LibraryState>(() => beginLibrary(null));
  const [libLang, setLibLang] = useState("");
  const [dia, setDia] = useState<DialogueState>({ speakers: [], lines: [] });
  const [clone, setClone] = useState<CloneState>({ name: "", sample: null });
  const [dub, setDub] = useState<DubState>({ id: "dub", clip: null, target: "", source: "", speakers: "", consent: false });
  const [dubPoster, setDubPoster] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [picking, setPicking] = useState<MediaItem[] | null>(null);

  const [outs, setOuts] = useState<Out[]>([]);
  const [shownId, setShownId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [again, setAgain] = useState(0);
  const script = useRef<HTMLTextAreaElement>(null);
  const sampleInput = useRef<HTMLInputElement>(null);
  const clipInput = useRef<HTMLInputElement>(null);

  const load = useCallback(
    (first: boolean) =>
      getVoiceMenu()
        .then((m) => {
          setMenu(m);
          if (!first) return;
          setPicked(pickModel(m.models, params.get("model") ?? (params.get("on") ? "dub" : null)));
          setSpeak(beginSpeak(m));
          setLib(beginLibrary(m.library));
          setLibLang(m.library.languages.find((l) => l.voices.some((v) => v.id === m.library.default_voice))?.language ?? m.library.languages[0]?.language ?? "");
          setDia(beginDialogue(m.dialogue));
        })
        .catch((e) => setMenuError(e instanceof Error ? e.message : "The voice models could not be listed")),
    [params],
  );
  useEffect(() => {
    if (!workspace) return;
    void load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per workspace
  }, [workspace]);

  // ?on=gen:<id> (the Library's Dub): that clip is the dub's source
  const onParam = params.get("on");
  const appliedOn = useRef(false);
  useEffect(() => {
    if (appliedOn.current || !onParam) return;
    appliedOn.current = true;
    const id = assetId(onParam);
    if (id === null) return;
    getRender(id)
      .then((r) => {
        if (r.kind !== "video") throw new Error("not a clip");
        setDub((d) => ({ ...d, clip: { ref: r.ref, kind: "clip", from: r.prompt ? r.prompt.slice(0, 60) : "a clip from your Library" } }));
        setDubPoster(r.thumb ?? null);
      })
      .catch(() => toast("That clip is not on your Library wall", "err"));
  }, [onParam, toast]);

  const model = menu?.models.find((m) => m.id === picked) ?? null;
  const kind: VoiceKind = model?.kind ?? "speak";
  const exempt = !!menu?.exempt;
  const choose = (id: string) => {
    const m = menu?.models.find((x) => x.id === id);
    setPicked(id);
    setOpen(null);
    if (m) router.replace(`/studio/voice?model=${m.kind}`, { scroll: false });
  };

  /* ── what stops the price, and the body it is asked for ── */
  const dubMenu = useMemo(() => (menu ? { ...menu.dub, ready: menu.ready, exempt: menu.exempt } : null), [menu]);
  const gap = !menu
    ? "loading"
    : kind === "speak"
      ? speakMissing(speak, menu)
      : kind === "library"
        ? libraryMissing(lib, menu.library)
        : kind === "dialogue"
          ? dialogueMissing(dia, menu.dialogue)
          : kind === "clone"
            ? cloneMissing(clone, menu.clone)
            : dubMenu
              ? dubMissing(dub, dubMenu)
              : "loading";
  const body = useMemo(() => {
    if (gap) return null;
    if (kind === "speak") return { kind, b: speakRequest(speak) } as const;
    if (kind === "library") return { kind, b: libraryRequest(lib) } as const;
    if (kind === "dialogue") return { kind, b: dialogueRequest(dia) } as const;
    if (kind === "clone") {
      const b = cloneRequest(clone);
      return b ? ({ kind, b } as const) : null;
    }
    const b = dubRequest(dub);
    return b ? ({ kind, b } as const) : null;
  }, [gap, kind, speak, lib, dia, clone, dub]);
  const quoteAny = useCallback(
    (x: NonNullable<typeof body>): Promise<Paid> =>
      x.kind === "speak"
        ? quoteSpeak(x.b)
        : x.kind === "library"
          ? quoteLibrary(x.b)
          : x.kind === "dialogue"
            ? quoteDialogue(x.b)
            : x.kind === "clone"
              ? quoteClone(x.b)
              : quoteDub(x.b),
    [],
  );
  const { price, problem, pricing } = usePrice(body, quoteAny, again);
  const needsConsent = kind === "dub" && !dub.consent;
  const canSend = !!menu?.ready && !!body && !!price && !pricing && !sending && !needsConsent;

  /* ── the one click that spends ── */
  const patch = (id: string, fields: Partial<Out>) => setOuts((all) => all.map((o) => (o.id === id ? { ...o, ...fields } : o)));
  async function generate() {
    if (!canSend || !body || !price || !menu) return;
    const id = newMadeId();
    const expect = { expect_credits: price.credits };
    const title =
      kind === "speak"
        ? speak.voice
        : kind === "library"
          ? libraryVoiceName(menu.library, lib.voice).split(" · ")[0]
          : kind === "dialogue"
            ? `${dia.speakers.length} voices`
            : kind === "clone"
              ? clone.name.trim()
              : `Dubbed into ${languageName(dubMenu, dub.target)}`;
    const words =
      kind === "speak"
        ? speak.script.trim()
        : kind === "library"
          ? lib.script.trim()
          : kind === "dialogue"
            ? dia.lines
                .filter((l) => l.text.trim())
                .map((l) => `${l.speaker + 1}: ${l.text.trim()}`)
                .join("  ·  ")
            : kind === "clone"
              ? menu.clone.consent_line
              : (dub.clip?.from ?? "");
    setSending(true);
    setOuts((all) => [
      {
        id,
        kind,
        media: kind === "dub" ? "video" : "audio",
        status: "running",
        title,
        words,
        credits: price.credits,
        detail: kind === "clone" ? "Listening for the consent line…" : "Starting…",
      },
      ...all,
    ]);
    setShownId(id);
    try {
      const started =
        body.kind === "speak"
          ? await runSpeak({ ...body.b, ...expect })
          : body.kind === "library"
            ? await runLibrary({ ...body.b, ...expect })
            : body.kind === "dialogue"
              ? await runDialogue({ ...body.b, ...expect })
              : body.kind === "clone"
                ? await runClone({ ...body.b, ...expect })
                : await runDub({ ...body.b, ...expect });
      announceBalanceChange();
      setSending(false);
      const job = await waitForJob(started.job_id, (j) => patch(id, { detail: j.detail || "Working…" }));
      announceBalanceChange();
      const out = job as unknown as { output?: string | null; seconds?: number | null; asset?: string | null; voice_id?: string };
      if (job.status !== "done" || !out.output) {
        const why = job.error || "It was not made. Nothing was charged.";
        patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why) });
        return;
      }
      patch(id, { status: "done", detail: job.detail || "Done", src: out.output, seconds: out.seconds ?? null, asset: out.asset ?? null, voiceId: out.voice_id });
      if (kind === "clone") {
        setClone({ name: "", sample: null });
        void load(false);
      }
    } catch (e) {
      setSending(false);
      if (e instanceof ApiError && e.status === 409) {
        // the price moved under the button: nothing ran, and it prices itself again
        setOuts((all) => all.filter((o) => o.id !== id));
        setShownId(null);
        setAgain((n) => n + 1);
        toast(`${e.message}. Nothing ran — check the price and press the button again.`, "err");
        return;
      }
      const why = e instanceof Error ? e.message : "That did not go through.";
      patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why, e instanceof ApiError ? e.status : undefined) });
    }
  }

  /* ── uploads and the Library picker ── */
  async function takeSample(f: File | undefined) {
    if (!f || !menu) return;
    if (!isSampleFile(f.name, menu.clone.types)) {
      toast(`The sample must be ${menu.clone.types.join(", ")}`, "err");
      return;
    }
    setUploading(true);
    try {
      const r = await cutUploadMedia(f);
      setClone((c) => ({ ...c, sample: { audio: r.handle, seconds: r.seconds ?? null, filename: r.filename } }));
    } catch (e) {
      toast(e instanceof Error ? e.message : "The sample did not upload.", "err");
    } finally {
      setUploading(false);
    }
  }
  async function takeClip(f: File | undefined) {
    if (!f) return;
    if (!/^video\//.test(f.type) && !/\.(mp4|mov|webm|m4v)$/i.test(f.name)) {
      toast("Choose a clip: mp4, mov or webm", "err");
      return;
    }
    setUploading(true);
    try {
      const up = await cutUploadMedia(f);
      setDub((d) => ({ ...d, clip: { ref: up.handle, kind: "clip", from: f.name } }));
      setDubPoster(null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "The clip did not upload.", "err");
    } finally {
      setUploading(false);
    }
  }
  const openClips = () => {
    if (picking) {
      setPicking(null);
      return;
    }
    getMedia({ kind: "video" })
      .then((w) => setPicking(w.items.filter((m) => m.kind === "video" && m.generated_id)))
      .catch(() => toast("The Library could not be read", "err"));
  };

  const useClone = (v: ClonedVoice) => {
    const libModel = menu?.models.find((m) => m.kind === "library");
    if (!libModel) return;
    setLib((l) => ({ ...l, voice: v.id }));
    setLibLang("Your voices");
    choose(libModel.id);
  };
  const forget = (v: ClonedVoice) =>
    removeClone(v.id)
      .then(() => load(false))
      .catch((e) => toast(e instanceof Error ? e.message : "That voice could not be removed.", "err"));

  const reuse = (o: Out) => {
    const m = menu?.models.find((x) => x.kind === o.kind);
    if (m) choose(m.id);
    if (o.kind === "speak") setSpeak((s) => ({ ...s, script: o.words }));
    if (o.kind === "library") setLib((s) => ({ ...s, script: o.words }));
    script.current?.focus();
  };

  /* ── the panel's fields, per model ── */
  const modelItems: MenuItem[] = (menu?.models ?? []).map((m) => {
    const Icon = ICON[m.kind] ?? AudioLines;
    return { id: m.id, name: m.title, note: m.label, right: "", icon: <Icon strokeWidth={1.6} /> };
  });
  const scriptField = (value: string, max: number, onChange: (v: string) => void, placeholder: string) => (
    <label className="dg-field">
      <span className="dg-lab-row">
        <span className="dg-lab">Script</span>
        <span className="dg-count">
          {value.trim().length.toLocaleString("en-US")} / {max.toLocaleString("en-US")}
        </span>
      </span>
      <textarea
        ref={script}
        className="dg-prompt"
        value={value}
        maxLength={max}
        rows={6}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            void generate();
          }
        }}
      />
    </label>
  );

  let fields: ReactNode = null;
  if (menu && kind === "speak") {
    fields = (
      <>
        {scriptField(speak.script, menu.speak.script_max, (v) => setSpeak((s) => ({ ...s, script: v })), "What the voice says. Tags like [laughs], [whispers] or [sighs] set the delivery.")}
        <div className="dg-field">
          <span className="dg-lab">Voice</span>
          <ModelMenu
            open={open === "voice"}
            onOpen={() => setOpen(open === "voice" ? null : "voice")}
            onClose={() => setOpen(null)}
            label={speak.voice}
            sub="ElevenLabs v3"
            items={menu.speak.voices.map((v) => ({ id: v, name: v, note: "", right: "" }))}
            picked={speak.voice}
            onPick={(v) => {
              setSpeak((s) => ({ ...s, voice: v }));
              setOpen(null);
            }}
            title={`${menu.speak.voices.length} voices`}
            foot="Switching keeps your script."
          />
        </div>
        <div className="dg-field">
          <span className="dg-lab">
            Language <em>optional</em>
          </span>
          <input className="vx-input vx-short" value={speak.language} maxLength={2} placeholder="auto" aria-label="Language, a two-letter code" onChange={(e) => setSpeak((s) => ({ ...s, language: e.target.value }))} />
          <p className="dg-hint">A two-letter code like en or es. Left empty, the model hears it in the script.</p>
        </div>
      </>
    );
  } else if (menu && kind === "library") {
    const voices = menu.library.languages.find((l) => l.language === libLang)?.voices ?? [];
    fields = (
      <>
        {scriptField(lib.script, menu.library.script_max, (v) => setLib((s) => ({ ...s, script: v })), "What the voice says, in the voice's language.")}
        <div className="dg-field">
          <span className="dg-lab">Language</span>
          <div className="vx-pills" role="radiogroup" aria-label="Language">
            {menu.library.languages.map((l) => (
              <button
                key={l.language}
                type="button"
                role="radio"
                aria-checked={l.language === libLang}
                onClick={() => {
                  setLibLang(l.language);
                  if (l.voices[0]) setLib((s) => ({ ...s, voice: l.voices[0].id }));
                }}
              >
                {l.language}
              </button>
            ))}
          </div>
        </div>
        <div className="dg-field">
          <span className="dg-lab-row">
            <span className="dg-lab">Voice</span>
            <span className="dg-count">{voices.length}</span>
          </span>
          <ModelMenu
            open={open === "libvoice"}
            onOpen={() => setOpen(open === "libvoice" ? null : "libvoice")}
            onClose={() => setOpen(null)}
            label={libraryVoiceName(menu.library, lib.voice).split(" · ")[0]}
            sub={libLang}
            items={voices.map((v) => ({ id: v.id, name: v.name, note: "", right: "" }))}
            picked={lib.voice}
            onPick={(v) => {
              setLib((s) => ({ ...s, voice: v }));
              setOpen(null);
            }}
            title={`${libLang} · ${voices.length} voices`}
            foot="Switching keeps your script."
          />
        </div>
        <div className="dg-field">
          <span className="dg-lab">Emotion</span>
          <div className="vx-pills" role="radiogroup" aria-label="Emotion">
            {["", ...menu.library.emotions].map((x) => (
              <button key={x || "auto"} type="button" role="radio" aria-checked={lib.emotion === x} onClick={() => setLib((s) => ({ ...s, emotion: x }))}>
                {x ? x[0].toUpperCase() + x.slice(1) : "Auto"}
              </button>
            ))}
          </div>
        </div>
        <div className="vx-sliders">
          <label className="dg-field">
            <span className="dg-lab-row">
              <span className="dg-lab">Speed</span>
              <span className="dg-count">{lib.speed.toFixed(2)}×</span>
            </span>
            <input type="range" className="vx-range" min={menu.library.speed[0]} max={menu.library.speed[1]} step={0.05} value={lib.speed} onChange={(e) => setLib((s) => ({ ...s, speed: Number(e.target.value) }))} />
          </label>
          <label className="dg-field">
            <span className="dg-lab-row">
              <span className="dg-lab">Pitch</span>
              <span className="dg-count">{lib.pitch > 0 ? `+${lib.pitch}` : lib.pitch}</span>
            </span>
            <input type="range" className="vx-range" min={menu.library.pitch[0]} max={menu.library.pitch[1]} step={1} value={lib.pitch} onChange={(e) => setLib((s) => ({ ...s, pitch: Number(e.target.value) }))} />
          </label>
        </div>
      </>
    );
  } else if (menu && kind === "dialogue") {
    const setLine = (i: number, p: Partial<{ speaker: number; text: string }>) => setDia((d) => ({ ...d, lines: d.lines.map((l, k) => (k === i ? { ...l, ...p } : l)) }));
    fields = (
      <>
        <div className="dg-field">
          <span className="dg-lab-row">
            <span className="dg-lab">Speakers</span>
            <span className="dg-count">
              {dia.speakers.length} of {menu.dialogue.max_speakers}
            </span>
          </span>
          <div className="vx-cast">
            {dia.speakers.map((p, i) => (
              <div key={i} className="vx-cast-one" data-n={i}>
                <span className="vx-n">{i + 1}</span>
                <select value={p} aria-label={`Voice of speaker ${i + 1}`} onChange={(e) => setDia((d) => ({ ...d, speakers: d.speakers.map((x, k) => (k === i ? e.target.value : x)) }))}>
                  {menu.dialogue.presets.map((x) => (
                    <option key={x} value={x}>
                      {presetLabel(x)}
                    </option>
                  ))}
                </select>
                {dia.speakers.length > 1 ? (
                  <button type="button" className="vx-x" aria-label={`Remove speaker ${i + 1} and their lines`} onClick={() => setDia((d) => removeSpeaker(d, i))}>
                    <X strokeWidth={2} />
                  </button>
                ) : (
                  <span />
                )}
              </div>
            ))}
            {dia.speakers.length < menu.dialogue.max_speakers ? (
              <button type="button" className="vx-ghost-btn" onClick={() => setDia((d) => addSpeaker(d, menu.dialogue))}>
                <Plus strokeWidth={1.8} /> Add a speaker
              </button>
            ) : null}
          </div>
        </div>
        <div className="dg-field">
          <span className="dg-lab-row">
            <span className="dg-lab">Lines</span>
            <span className="dg-count">
              {dialogueScript(dia).length.toLocaleString("en-US")} / {menu.dialogue.script_max.toLocaleString("en-US")}
            </span>
          </span>
          <ol className="vx-lines">
            {dia.lines.map((l, i) => (
              <li key={i} data-n={l.speaker}>
                <button
                  type="button"
                  className="vx-who"
                  title="Who says it: tap for the next speaker"
                  aria-label={`Line ${i + 1} is speaker ${l.speaker + 1}; tap for the next speaker`}
                  onClick={() => setLine(i, { speaker: (l.speaker + 1) % Math.max(1, dia.speakers.length) })}
                >
                  {l.speaker + 1}
                </button>
                <textarea
                  rows={2}
                  value={l.text}
                  placeholder={`${presetLabel(dia.speakers[l.speaker] ?? "").split(" · ")[0]} says…`}
                  aria-label={`Line ${i + 1}`}
                  onChange={(e) => setLine(i, { text: e.target.value })}
                />
                {dia.lines.length > 1 ? (
                  <button type="button" className="vx-x" aria-label={`Remove line ${i + 1}`} onClick={() => setDia((d) => ({ ...d, lines: d.lines.filter((_, k) => k !== i) }))}>
                    <X strokeWidth={2} />
                  </button>
                ) : (
                  <span />
                )}
              </li>
            ))}
          </ol>
          <button type="button" className="vx-ghost-btn" disabled={dia.lines.length >= menu.dialogue.max_lines} onClick={() => setDia((d) => addLine(d, menu.dialogue.max_lines))}>
            <Plus strokeWidth={1.8} /> Add a line
          </button>
          <p className="dg-hint">The price is the most it can cost: the words at a slow pace, in 15-second steps.</p>
        </div>
      </>
    );
  } else if (menu && kind === "clone") {
    fields = (
      <>
        <div className="vx-consent">
          <b>Your own voice only</b>
          <ol>
            <li>Start a recording. Your phone&apos;s voice memos is fine.</li>
            <li>
              Read this line first:
              <q>{menu.clone.consent_line}</q>
            </li>
            <li>
              Keep talking naturally for at least {menu.clone.min_seconds} more seconds (up to {Math.round(menu.clone.max_seconds / 60)} minutes).
            </li>
          </ol>
          <small>The studio listens for the line before anything is charged. Without it, no clone is made.</small>
        </div>
        <div className="dg-field">
          <span className="dg-lab">Sample</span>
          {clone.sample ? (
            <div className="vx-file">
              <AudioLines strokeWidth={1.6} />
              <span>
                <b>{clone.sample.filename}</b>
                <small>{clone.sample.seconds ? `${clone.sample.seconds.toFixed(1)}s` : ""}</small>
              </span>
              <button type="button" className="vx-x" aria-label="Remove the sample" onClick={() => setClone((c) => ({ ...c, sample: null }))}>
                <X strokeWidth={2} />
              </button>
            </div>
          ) : (
            <div className="dg-tray" data-size="lg">
              <button type="button" className="dg-add" disabled={uploading} onClick={() => sampleInput.current?.click()}>
                <Upload strokeWidth={1.8} />
                <span>{uploading ? "…" : "Upload"}</span>
              </button>
            </div>
          )}
          <input
            ref={sampleInput}
            type="file"
            accept={menu.clone.types.join(",") + ",audio/*"}
            hidden
            onChange={(e) => {
              void takeSample(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <p className="dg-hint">{menu.clone.types.join(" · ")}</p>
        </div>
        <label className="dg-field">
          <span className="dg-lab">Name</span>
          <input className="vx-input" value={clone.name} maxLength={menu.clone.name_max} placeholder="e.g. My voice" onChange={(e) => setClone((c) => ({ ...c, name: e.target.value }))} />
        </label>
      </>
    );
  } else if (menu && dubMenu && kind === "dub") {
    fields = (
      <>
        <div className="dg-field">
          <span className="dg-lab">Clip</span>
          {dub.clip ? (
            <div className="vx-file">
              {dubPoster ? <img src={mediaSrc(dubPoster)} alt="" /> : <Languages strokeWidth={1.6} />}
              <span>
                <b>{dub.clip.from}</b>
                <small>{dub.clip.ref}</small>
              </span>
              <button
                type="button"
                className="vx-x"
                aria-label="Remove the clip"
                onClick={() => {
                  setDub((d) => ({ ...d, clip: null }));
                  setDubPoster(null);
                }}
              >
                <X strokeWidth={2} />
              </button>
            </div>
          ) : (
            <div className="dg-tray" data-size="lg">
              <button type="button" className="dg-add" disabled={uploading} onClick={() => clipInput.current?.click()}>
                <Upload strokeWidth={1.8} />
                <span>{uploading ? "…" : "Upload"}</span>
              </button>
              <button type="button" className="dg-add" onClick={openClips} aria-expanded={!!picking}>
                <LayoutGrid strokeWidth={1.8} />
                <span>Library</span>
              </button>
            </div>
          )}
          <input
            ref={clipInput}
            type="file"
            accept="video/*"
            hidden
            onChange={(e) => {
              void takeClip(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <p className="dg-hint">A clip with people speaking, up to {Math.round(menu.dub.max_seconds / 60)} minutes, with its sound.</p>
        </div>
        <div className="dg-field">
          <span className="dg-lab">Dub into</span>
          <div className="vx-pills" role="radiogroup" aria-label="Dub into">
            {menu.dub.languages.map((l) => (
              <button key={l.code} type="button" role="radio" aria-checked={dub.target === l.code} onClick={() => setDub((d) => ({ ...d, target: l.code }))}>
                {l.name}
              </button>
            ))}
          </div>
        </div>
        <div className="vx-sliders">
          <label className="dg-field">
            <span className="dg-lab">
              Spoken now <em>optional</em>
            </span>
            <input className="vx-input" value={dub.source} maxLength={2} placeholder="auto" onChange={(e) => setDub((d) => ({ ...d, source: e.target.value }))} />
          </label>
          <label className="dg-field">
            <span className="dg-lab">
              People <em>optional</em>
            </span>
            <input className="vx-input" value={dub.speakers} inputMode="numeric" maxLength={2} placeholder="auto" onChange={(e) => setDub((d) => ({ ...d, speakers: e.target.value }))} />
          </label>
        </div>
        <label className="vx-check">
          <input type="checkbox" checked={dub.consent} onChange={(e) => setDub((d) => ({ ...d, consent: e.target.checked }))} />
          <span>The voices on this clip are mine, or the people who own them agreed to it being dubbed.</span>
        </label>
      </>
    );
  }

  const shown = outs.find((o) => o.id === shownId) ?? null;
  const started =
    kind === "speak"
      ? !!speak.script.trim()
      : kind === "library"
        ? !!lib.script.trim()
        : kind === "dialogue"
          ? dia.lines.some((l) => l.text.trim())
          : kind === "clone"
            ? !!(clone.sample || clone.name.trim())
            : !!(dub.clip || dub.target);
  const note = gap && gap !== "loading" ? (started ? gap : "") : problem || (needsConsent && price ? "Tick the box above first." : "");

  return (
    <section className={`view dg dgi vx ${cardFonts}`}>
      <form
        className="dg-panel"
        onSubmit={(e) => {
          e.preventDefault();
          void generate();
        }}
      >
        <div className="dg-field">
          <span className="dg-lab">Model</span>
          <ModelMenu
            open={open === "model"}
            onOpen={() => setOpen(open === "model" ? null : "model")}
            onClose={() => setOpen(null)}
            label={model?.title ?? (menuError ? "Unavailable" : "Loading…")}
            sub={model?.label ?? ""}
            items={modelItems}
            picked={picked}
            onPick={choose}
            title={`${modelItems.length} voice models`}
            foot="Each one keeps what you typed while you look at another."
            disabled={!modelItems.length}
          />
          {model ? <p className="dg-hint">{model.what}</p> : null}
        </div>

        {fields}

        <span className="dg-grow" />
        {/* the foot stays in view while a long panel (the library, a
            dialogue) scrolls: the price is always beside its button */}
        <div className="vx-foot">
          {note ? <p className={`dg-note${problem ? " err" : ""}`}>{note}</p> : null}
          {menuError ? <p className="dg-note err">{menuError}</p> : null}
          {menu && !menu.ready ? <p className="dg-note err">Voice models are not set up on this server yet.</p> : null}
          <button type="submit" className="dg-go" disabled={!canSend} data-busy={pricing || sending ? "1" : undefined}>
            {sending ? <span className="dg-spin sm" aria-hidden /> : <Wand2 strokeWidth={1.8} />}
            {sending ? "Starting…" : body ? goLabel(VERB[kind], price, pricing || (!price && !problem), exempt) : VERB[kind]}
          </button>
          <p className="dg-hint">⌘↵ makes it. Everything you make here also lands in your Library.</p>
        </div>
      </form>

      <VoiceStage
        shown={shown}
        kind={kind}
        clones={menu?.clone.voices ?? []}
        keepDays={menu?.clone.keep_days ?? 7}
        exempt={exempt}
        onStarter={(t) => {
          if (kind === "library") setLib((s) => ({ ...s, script: t }));
          else {
            const m = menu?.models.find((x) => x.kind === "speak");
            if (kind !== "speak" && m) choose(m.id);
            setSpeak((s) => ({ ...s, script: t }));
          }
          script.current?.focus();
        }}
        onReuse={reuse}
        onUseClone={useClone}
        onForget={(v) => void forget(v)}
      />

      <aside className="dg-history vx-history" aria-label="Made on this visit">
        <span className="dg-lab">This visit</span>
        {outs.length ? (
          <ul>
            {outs.map((o) => {
              const Icon = ICON[o.kind] ?? AudioLines;
              return (
                <li key={o.id}>
                  <button type="button" className="dg-hist vx-hist" aria-pressed={o.id === shownId} onClick={() => setShownId(o.id)} title={o.words || o.title}>
                    {o.status === "running" ? (
                      <span className="dg-spin sm" aria-hidden />
                    ) : (
                      <span className="vx-hist-bars" data-failed={o.status === "failed" ? "1" : undefined} aria-hidden>
                        {waveBars(o.id + o.words, 9).map((h, k) => (
                          <i key={k} style={{ height: `${Math.round(h * 100)}%` }} />
                        ))}
                      </span>
                    )}
                    <span className="vx-hist-name">
                      <Icon strokeWidth={1.8} />
                      {o.status === "failed" ? "not made" : o.title}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="dg-hint">Nothing yet.</p>
        )}
        <Link className="dg-hist-more" href="/studio/assets">
          Open the Library
        </Link>
      </aside>

      {picking ? (
        <div className="dg-picker vx-picker" role="dialog" aria-label="Pick a clip">
          <div className="dg-picker-head">
            <b>Your clips</b>
            <span className="dg-grow" />
            <button type="button" className="dg-icon" aria-label="Close" onClick={() => setPicking(null)}>
              <X strokeWidth={1.8} />
            </button>
          </div>
          {picking.length ? (
            <ul className="dg-picker-grid">
              {picking.map((m) => (
                <li key={m.asset_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setDub((d) => ({ ...d, clip: { ref: `gen:${m.generated_id}`, kind: "clip", from: m.prompt ? m.prompt.slice(0, 60) : "a clip from your Library" } }));
                      setDubPoster(m.poster ?? null);
                      setPicking(null);
                    }}
                    title={m.prompt || m.asset_name}
                  >
                    {m.poster ? <img src={mediaSrc(m.poster)} alt="" loading="lazy" /> : <span className="vx-noposter">clip</span>}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="dg-hint">No clips on the wall yet.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}

/* ── the stage: what is being listened to, made, or the starters ── */
function VoiceStage({
  shown,
  kind,
  clones,
  keepDays,
  exempt,
  onStarter,
  onReuse,
  onUseClone,
  onForget,
}: {
  shown: Out | null;
  kind: VoiceKind;
  clones: ClonedVoice[];
  keepDays: number;
  exempt: boolean;
  onStarter: (t: string) => void;
  onReuse: (o: Out) => void;
  onUseClone: (v: ClonedVoice) => void;
  onForget: (v: ClonedVoice) => void;
}) {
  if (!shown) {
    if (kind === "clone") {
      return (
        <div className="dg-stage" data-empty="1">
          <div className="dg-empty vx-voices-stage">
            <span className="dg-anton">Your voices</span>
            <p>
              {clones.length
                ? `A voice nobody reads in for ${keepDays} days is deleted by the model. Read something in it to keep it.`
                : "Clone your own voice from a sample that starts with the consent line. It then reads any script in the voice library."}
            </p>
            {clones.length ? (
              <ul className="vx-clone-cards">
                {clones.map((v) => (
                  <li key={v.id}>
                    <b>{v.name}</b>
                    {v.preview_url ? <audio controls preload="metadata" src={mediaSrc(v.preview_url)} /> : null}
                    <small>{keepLine(v)}</small>
                    <div className="dg-acts">
                      <button type="button" className="dg-btn" onClick={() => onUseClone(v)}>
                        <Library strokeWidth={1.8} /> Read a script in it
                      </button>
                      <button type="button" className="dg-btn" onClick={() => onForget(v)}>
                        <X strokeWidth={1.8} /> Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      );
    }
    if (kind === "dub") {
      return (
        <div className="dg-stage" data-empty="1">
          <div className="dg-empty">
            <span className="dg-anton">Your clip, in another language</span>
            <p>Pick a clip with people speaking and a language. The same voices say it again in that language, and the dub lands in your Library.</p>
          </div>
        </div>
      );
    }
    return (
      <div className="dg-stage" data-empty="1">
        <div className="dg-empty">
          <span className="dg-anton">{kind === "dialogue" ? "What they say plays here" : "What you say plays here"}</span>
          <p>And in your Library&apos;s audio, ready for the editor&apos;s voice track. Nothing is read until you press the button.</p>
          {kind === "dialogue" ? null : (
            <>
              <div className="dg-starters">
                {VOICE_STARTERS.map((s) => (
                  <button key={s} type="button" onClick={() => onStarter(s)}>
                    {s}
                  </button>
                ))}
              </div>
              <small>A starter only fills the script.</small>
            </>
          )}
        </div>
      </div>
    );
  }

  const genId = /^gen:(\d+)$/.exec(shown.asset ?? "")?.[1];
  return (
    <div className="dg-stage-wrap">
      <div className="dg-stage" data-status={shown.status}>
        {shown.status === "done" && shown.src ? (
          shown.media === "video" ? (
            <video key={shown.src} src={mediaSrc(shown.src)} controls playsInline autoPlay />
          ) : (
            <div className="vx-listen">
              <span className="dg-anton vx-listen-title">{shown.title}</span>
              <div className="vx-wave" aria-hidden>
                {waveBars(shown.id + shown.words).map((h, k) => (
                  <i key={k} style={{ height: `${Math.round(h * 100)}%` }} />
                ))}
              </div>
              <audio key={shown.src} src={mediaSrc(shown.src)} controls autoPlay preload="metadata" />
            </div>
          )
        ) : (
          <div className="dg-wait">
            <div className="dg-wait-card">
              {shown.status === "running" ? <span className="dg-spin" aria-hidden /> : null}
              <b data-failed={shown.status === "failed" ? "1" : undefined}>{shown.status === "failed" ? "Not made" : shown.detail}</b>
              <p>
                {shown.status === "failed"
                  ? shown.detail
                  : `It lands here and in your Library. ${shown.credits.toLocaleString("en-US")} credits are held, and given back if it fails.`}
              </p>
              <div className="dg-acts">
                {shown.status === "failed" && shown.outOfCredits ? (
                  <Link className="dg-btn" href={TOP_UP_HREF}>
                    Add credits
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="dg-bar">
        <span className="dg-chip">{shown.title}</span>
        {shown.seconds ? <span className="dg-chip">{shown.seconds.toFixed(1)}s</span> : null}
        <span className="dg-chip">
          {shown.credits.toLocaleString("en-US")} credits{shown.status === "running" ? " held" : exempt ? " · not charged" : ""}
        </span>
        <span className="dg-grow" />
        {shown.status === "done" ? (
          <>
            {shown.kind === "speak" || shown.kind === "library" ? (
              <button type="button" className="dg-btn" onClick={() => onReuse(shown)} title="Put this script back in the panel">
                <RotateCcw strokeWidth={1.8} /> Reuse script
              </button>
            ) : null}
            {genId ? (
              <Link className="dg-btn" href={`/studio/assets?open=${genId}`}>
                <LayoutGrid strokeWidth={1.8} /> Open in Library
              </Link>
            ) : null}
            {shown.src ? (
              <a className="dg-icon" href={genId ? renderDownloadHref(Number(genId)) : mediaSrc(shown.src)} download title="Download" aria-label="Download">
                <Download strokeWidth={1.8} />
              </a>
            ) : null}
          </>
        ) : null}
      </div>
      {shown.words ? <p className="dg-stage-prompt">{shown.words}</p> : null}
    </div>
  );
}
