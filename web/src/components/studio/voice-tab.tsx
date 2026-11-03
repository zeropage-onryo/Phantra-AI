"use client";

/* The Voice section (/studio/voice, 2026-10-26, docs/tasks/task-voice-tab.md),
   behind the `voice_tab` capability (the server page does the 404).

   Every voice model on one page. The models are the server's list
   (GET /api/voice, src/voice_studio.py), drawn as cards along the top; the
   one picked opens its panel below:

     * SPEAK -- a script read aloud in one of the model's voices. Its price
       is the server's quote (POST /api/voice/speak/quote), asked again when
       the words, voice or language change, and the Make button runs it at
       that number or not at all. The read lands in the editor's audio bin.
     * DUB -- a clip spoken again in another language: the composer's own
       priced card (dubbing-step.tsx) on a clip from the Library or a file.

   NOTHING RUNS FROM A MODEL CARD. A card opens a panel; each panel has one
   button that spends, beside its price. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AudioLines, Download, FolderOpen, Languages, Library, MessagesSquare, Mic, Plus, Upload, UserRound, X } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { DubbingStep } from "@/components/studio/dubbing-step";
import { mediaSrc, newMadeId, type Made } from "@/lib/composer";
import { madeStatus } from "@/lib/made-state";
import { assetId } from "@/lib/continue";
import { beginDub, dubRequest, languageName, type ClipChoice, type DubMenu, type DubState } from "@/lib/dubbing";
import {
  addLine,
  addSpeaker,
  beginDialogue,
  beginLibrary,
  beginSpeak,
  charCount,
  cloneMissing,
  cloneRequest,
  isSampleFile,
  keepLine,
  dialogueMissing,
  dialogueRequest,
  dialogueScript,
  libraryMissing,
  libraryRequest,
  libraryVoiceName,
  presetLabel,
  removeSpeaker,
  pickModel,
  priceLine,
  readLine,
  settleRead,
  speakMissing,
  speakRequest,
  type ClonedVoice,
  type CloneState,
  type DialogueState,
  type LibraryState,
  type Paid,
  type Read,
  type SpeakState,
  type VoiceMenu,
  type VoiceModel,
} from "@/lib/voice-tab";
import {
  announceBalanceChange,
  cutUploadMedia,
  getMedia,
  getRender,
  getVoiceMenu,
  quoteClone,
  quoteDialogue,
  quoteLibrary,
  quoteSpeak,
  renderDownloadHref,
  runDub,
  removeClone,
  runClone,
  runDialogue,
  runLibrary,
  runSpeak,
  waitForJob,
  type MediaItem,
} from "@/lib/studio-api";
import type { Turn } from "@/lib/assistant";
import "@/components/studio/effects-tab.css";
import "@/components/studio/voice-tab.css";
/* eslint-disable @next/next/no-img-element */

const ICON = { speak: Mic, library: Library, dialogue: MessagesSquare, clone: UserRound, dub: Languages } as const;

export function VoiceTab() {
  const { me, toast } = useShell();
  const router = useRouter();
  const params = useSearchParams();
  const [menu, setMenu] = useState<VoiceMenu | null>(null);
  const [menuError, setMenuError] = useState("");
  const [picked, setPicked] = useState("");
  // a cloned voice the library should open on ("Read a script in it")
  const [useVoice, setUseVoice] = useState<string | null>(null);
  const workspace = me?.account?.slug ?? "";
  const reload = useCallback(() => {
    getVoiceMenu()
      .then(setMenu)
      .catch(() => toast("The voice models could not be read again", "err"));
  }, [toast]);

  useEffect(() => {
    if (!workspace) return;
    let live = true;
    getVoiceMenu()
      .then((m) => {
        if (!live) return;
        setMenu(m);
        setPicked((was) => was || pickModel(m.models, params.get("model") ?? (params.get("on") ? "dub" : null)));
      })
      .catch((e) => live && setMenuError(e instanceof Error ? e.message : "The voice models could not be listed"));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- read the address once, on arrival
  }, [workspace]);

  const model = menu?.models.find((m) => m.id === picked) ?? null;
  const choose = (m: VoiceModel) => {
    setUseVoice(null);
    setPicked(m.id);
    router.replace(`/studio/voice?model=${m.kind}`, { scroll: false });
  };

  return (
    <section className="view fxt vx" style={{ paddingTop: 0 }}>
      <div className="vhead" style={{ marginTop: 8 }}>
        <h2>Voice</h2>
        <span className="spacer" />
        <span className="m">Every voice model in one place. Browsing is free; each panel shows its price before anything runs.</span>
      </div>

      {menuError ? <p className="fxt-note">{menuError}</p> : null}
      {menu && !menu.ready ? <p className="fxt-note">Voice models are not set up on this server yet. The cards show what each one does.</p> : null}

      <ul className="vx-models" aria-label="Voice models" role="tablist">
        {(menu?.models ?? []).map((m) => {
          const Icon = ICON[m.kind] ?? AudioLines;
          return (
            <li key={m.id}>
              <button type="button" role="tab" aria-selected={m.id === picked} className="vx-model" onClick={() => choose(m)}>
                <span className="vx-model-head">
                  <Icon strokeWidth={1.6} />
                  <b>{m.title}</b>
                </span>
                <span className="vx-model-label">{m.label}</span>
                <span className="vx-model-what">{m.what}</span>
                <small>Priced {m.priced}</small>
              </button>
            </li>
          );
        })}
        {!menu && !menuError
          ? [0, 1, 2, 3, 4].map((i) => (
              <li key={i}>
                <div className="vx-model vx-ghost" aria-hidden />
              </li>
            ))
          : null}
      </ul>

      {menu && model?.kind === "speak" ? <SpeakPanel menu={menu} onError={(why) => toast(why, "err")} /> : null}
      {menu && model?.kind === "library" ? <LibraryPanel key={useVoice ?? "library"} menu={menu} initialVoice={useVoice} onError={(why) => toast(why, "err")} /> : null}
      {menu && model?.kind === "dialogue" ? <DialoguePanel menu={menu} onError={(why) => toast(why, "err")} /> : null}
      {menu && model?.kind === "clone" ? (
        <ClonePanel
          menu={menu}
          onError={(why) => toast(why, "err")}
          onChanged={reload}
          onUse={(id) => {
            const lib = menu.models.find((m) => m.kind === "library");
            if (!lib) return;
            setUseVoice(id);
            setPicked(lib.id);
            router.replace("/studio/voice?model=library", { scroll: false });
          }}
        />
      ) : null}
      {menu && model?.kind === "dub" ? <DubPanel menu={menu} initialOn={params.get("on")} onError={(why) => toast(why, "err")} /> : null}
    </section>
  );
}

/* ── the shared half of every read-making panel: its price and its reads ──
   `body` is null while something stops the price (`gap` says what); the
   quote is asked again when the body changes, and Make runs at the number
   shown or not at all. */
function usePricedReads<B>(
  body: B | null,
  quote: (b: B) => Promise<Paid>,
  run: (b: B & { expect_credits: number }) => Promise<{ job_id: number; credits: number; charged: boolean }>,
  onError: (why: string) => void,
) {
  const [price, setPrice] = useState<Paid | null>(null);
  const [problem, setProblem] = useState("");
  const [reads, setReads] = useState<Read[]>([]);
  const [busy, setBusy] = useState(false);
  const [again, setAgain] = useState(0);
  const asked = useRef(0);
  const key = body ? JSON.stringify(body) : "";
  useEffect(() => {
    if (!body) return;
    const mine = ++asked.current;
    const timer = setTimeout(() => {
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
        });
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key stands for the body
  }, [key, again]);
  // a price is only ever shown for a body that can be made
  const shown = body ? price : null;

  async function make(voice: string, words: string) {
    if (!body || !shown || busy) return;
    const id = newMadeId();
    setBusy(true);
    try {
      const started = await run({ ...body, expect_credits: shown.credits });
      const read: Read = { id, status: "running", voice, script: words, paid: { credits: started.credits, charged: started.charged }, jobId: started.job_id };
      setReads((all) => [read, ...all]);
      const job = await waitForJob(started.job_id);
      announceBalanceChange();
      const done = settleRead(read, job as unknown as Parameters<typeof settleRead>[1]);
      setReads((all) => all.map((r) => (r.id === id ? done : r)));
      if (done.status === "failed") onError(done.error ?? "The voice was not made.");
    } catch (e) {
      // refused before anything ran (a price that moved): the panel prices again
      setReads((all) => all.filter((r) => r.id !== id));
      onError(e instanceof Error ? e.message : "That did not go through.");
      setPrice(null);
      setAgain((n) => n + 1);
    } finally {
      setBusy(false);
    }
  }
  return { shown, problem, reads, busy, make };
}

/* the line beside a Make button: what is missing, else the price */
const goLine = (gap: string, started: boolean, problem: string, shown: Paid | null, exempt: boolean) =>
  gap ? (started ? gap : "") : problem || (shown ? priceLine(shown, exempt) : "Pricing…");

/* ── what a panel made: each read with a player and a download ── */
function Reads({ title, reads, exempt, empty }: { title: string; reads: Read[]; exempt: boolean; empty: string }) {
  return (
    <div className="vx-out">
      <div className="vx-out-head">
        <b>{title}</b>
        <span>Each one is in your Library&apos;s audio, ready for the editor&apos;s voice track.</span>
      </div>
      {reads.length ? (
        <ul className="vx-reads">
          {reads.map((r) => (
            <li key={r.id} data-status={r.status}>
              <p className="vx-read-words">{r.script}</p>
              {r.status === "done" && r.url ? (
                <div className="vx-read-play">
                  <audio controls preload="metadata" src={mediaSrc(r.url)} />
                  <a className="fxt-btn" href={mediaSrc(r.url)} download title="Save the file">
                    <Download strokeWidth={1.8} />
                  </a>
                </div>
              ) : null}
              <small>{r.status === "running" ? `${r.voice} · making it…` : r.status === "failed" ? r.error : readLine(r, exempt)}</small>
            </li>
          ))}
        </ul>
      ) : (
        <p className="vx-empty">{empty}</p>
      )}
    </div>
  );
}

/* ── text to speech (ElevenLabs v3) ── */
function SpeakPanel({ menu, onError }: { menu: VoiceMenu; onError: (why: string) => void }) {
  const [s, setS] = useState<SpeakState>(() => beginSpeak(menu));
  const gap = speakMissing(s, menu);
  const { shown, problem, reads, busy, make } = usePricedReads(gap ? null : speakRequest(s), quoteSpeak, runSpeak, onError);
  return (
    <div className="vx-panel" role="tabpanel" aria-label="Text to speech">
      <div className="vx-form">
        <textarea
          className="vx-script"
          rows={6}
          value={s.script}
          maxLength={menu.speak.script_max}
          placeholder="What the voice says. Tags like [laughs], [whispers] or [sighs] set the delivery."
          aria-label="What the voice says"
          onChange={(e) => setS((was) => ({ ...was, script: e.target.value }))}
        />
        <div className="vx-row">
          <label className="vx-field">
            <span>Voice</span>
            <select value={s.voice} aria-label="Voice" onChange={(e) => setS((was) => ({ ...was, voice: e.target.value }))}>
              {menu.speak.voices.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="vx-field">
            <span>Language</span>
            <input
              value={s.language}
              maxLength={2}
              placeholder="auto"
              aria-label="Language, a two-letter code"
              onChange={(e) => setS((was) => ({ ...was, language: e.target.value }))}
            />
          </label>
          <small className="vx-count">{charCount(s, menu.speak.script_max)}</small>
        </div>
        <div className="vx-go">
          <button type="button" className="fxt-btn primary" disabled={!menu.ready || !shown || busy} onClick={() => void make(s.voice, s.script.trim())}>
            <Mic strokeWidth={1.8} /> {busy ? "Reading…" : "Make the voice"}
          </button>
          <small>{goLine(gap, !!s.script.trim(), problem, shown, menu.exempt)}</small>
        </div>
      </div>
      <Reads title="Reads" reads={reads} exempt={menu.exempt} empty="Your reads land here. Make the voice runs it at the price shown." />
    </div>
  );
}

/* ── the voice library (MiniMax Speech-02 HD) ── */
function LibraryPanel({ menu, initialVoice, onError }: { menu: VoiceMenu; initialVoice?: string | null; onError: (why: string) => void }) {
  const lib = menu.library;
  const start = initialVoice && lib.languages.some((l) => l.voices.some((v) => v.id === initialVoice)) ? initialVoice : lib.default_voice;
  const [s, setS] = useState<LibraryState>(() => ({ ...beginLibrary(lib), voice: start }));
  const [language, setLanguage] = useState(() => lib.languages.find((l) => l.voices.some((v) => v.id === start))?.language ?? lib.languages[0]?.language ?? "");
  const gap = libraryMissing(s, lib);
  const { shown, problem, reads, busy, make } = usePricedReads(gap ? null : libraryRequest(s), quoteLibrary, runLibrary, onError);
  const voices = lib.languages.find((l) => l.language === language)?.voices ?? [];
  const pickLanguage = (next: string) => {
    setLanguage(next);
    const first = lib.languages.find((l) => l.language === next)?.voices[0];
    // the voice follows the language; a voice from another one is never kept
    if (first) setS((was) => ({ ...was, voice: first.id }));
  };
  return (
    <div className="vx-panel" role="tabpanel" aria-label="Voice library">
      <div className="vx-form">
        <textarea
          className="vx-script"
          rows={6}
          value={s.script}
          maxLength={lib.script_max}
          placeholder="What the voice says, in the voice's language."
          aria-label="What the voice says"
          onChange={(e) => setS((was) => ({ ...was, script: e.target.value }))}
        />
        <div className="vx-langs" role="tablist" aria-label="Language">
          {lib.languages.map((l) => (
            <button key={l.language} type="button" role="tab" aria-selected={l.language === language} onClick={() => pickLanguage(l.language)}>
              {l.language} <small>{l.voices.length}</small>
            </button>
          ))}
        </div>
        <ul className="vx-voices" role="radiogroup" aria-label="Voice">
          {voices.map((v) => (
            <li key={v.id}>
              <button type="button" role="radio" aria-checked={s.voice === v.id} onClick={() => setS((was) => ({ ...was, voice: v.id }))}>
                {v.name}
              </button>
            </li>
          ))}
        </ul>
        <div className="vx-row">
          <label className="vx-field">
            <span>Emotion</span>
            <select value={s.emotion} aria-label="Emotion" onChange={(e) => setS((was) => ({ ...was, emotion: e.target.value }))}>
              <option value="">The model decides</option>
              {lib.emotions.map((x) => (
                <option key={x} value={x}>
                  {x[0].toUpperCase() + x.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label className="vx-field vx-slider">
            <span>Speed · {s.speed.toFixed(2)}×</span>
            <input type="range" min={lib.speed[0]} max={lib.speed[1]} step={0.05} value={s.speed} aria-label="Speed" onChange={(e) => setS((was) => ({ ...was, speed: Number(e.target.value) }))} />
          </label>
          <label className="vx-field vx-slider">
            <span>Pitch · {s.pitch > 0 ? `+${s.pitch}` : s.pitch}</span>
            <input type="range" min={lib.pitch[0]} max={lib.pitch[1]} step={1} value={s.pitch} aria-label="Pitch" onChange={(e) => setS((was) => ({ ...was, pitch: Number(e.target.value) }))} />
          </label>
          <small className="vx-count">{charCount(s, lib.script_max)}</small>
        </div>
        <div className="vx-go">
          <button type="button" className="fxt-btn primary" disabled={!menu.ready || !shown || busy} onClick={() => void make(libraryVoiceName(lib, s.voice), s.script.trim())}>
            <Library strokeWidth={1.8} /> {busy ? "Reading…" : "Make the voice"}
          </button>
          <small>{goLine(gap, !!s.script.trim(), problem, shown, menu.exempt)}</small>
        </div>
      </div>
      <Reads title="Reads" reads={reads} exempt={menu.exempt} empty="Your reads land here. Make the voice runs it at the price shown." />
    </div>
  );
}

/* ── dialogue (VibeVoice 7B) ── */
function DialoguePanel({ menu, onError }: { menu: VoiceMenu; onError: (why: string) => void }) {
  const dia = menu.dialogue;
  const [s, setS] = useState<DialogueState>(() => beginDialogue(dia));
  const gap = dialogueMissing(s, dia);
  const { shown, problem, reads, busy, make } = usePricedReads(gap ? null : dialogueRequest(s), quoteDialogue, runDialogue, onError);
  const started = s.lines.some((l) => l.text.trim());
  const setLine = (i: number, patch: Partial<{ speaker: number; text: string }>) =>
    setS((was) => ({ ...was, lines: was.lines.map((l, k) => (k === i ? { ...l, ...patch } : l)) }));
  return (
    <div className="vx-panel" role="tabpanel" aria-label="Dialogue">
      <div className="vx-form">
        <div className="vx-cast" aria-label="Speakers">
          {s.speakers.map((p, i) => (
            <div key={i} className="vx-cast-one" data-n={i}>
              <span className="vx-cast-n">Speaker {i + 1}</span>
              <select value={p} aria-label={`Voice of speaker ${i + 1}`} onChange={(e) => setS((was) => ({ ...was, speakers: was.speakers.map((x, k) => (k === i ? e.target.value : x)) }))}>
                {dia.presets.map((x) => (
                  <option key={x} value={x}>
                    {presetLabel(x)}
                  </option>
                ))}
              </select>
              {s.speakers.length > 1 ? (
                <button type="button" className="vx-x" aria-label={`Remove speaker ${i + 1} and their lines`} onClick={() => setS((was) => removeSpeaker(was, i))}>
                  <X strokeWidth={1.8} />
                </button>
              ) : null}
            </div>
          ))}
          {s.speakers.length < dia.max_speakers ? (
            <button type="button" className="fxt-btn" onClick={() => setS((was) => addSpeaker(was, dia))}>
              <Plus strokeWidth={1.8} /> Add a speaker
            </button>
          ) : null}
        </div>
        <ol className="vx-lines" aria-label="The dialogue">
          {s.lines.map((l, i) => (
            <li key={i} data-n={l.speaker}>
              <select value={l.speaker} aria-label={`Who says line ${i + 1}`} onChange={(e) => setLine(i, { speaker: Number(e.target.value) })}>
                {s.speakers.map((p, k) => (
                  <option key={k} value={k}>
                    {k + 1} · {presetLabel(p).split(" · ")[0]}
                  </option>
                ))}
              </select>
              <input value={l.text} placeholder="What they say" aria-label={`Line ${i + 1}`} onChange={(e) => setLine(i, { text: e.target.value })} />
              {s.lines.length > 1 ? (
                <button type="button" className="vx-x" aria-label={`Remove line ${i + 1}`} onClick={() => setS((was) => ({ ...was, lines: was.lines.filter((_, k) => k !== i) }))}>
                  <X strokeWidth={1.8} />
                </button>
              ) : null}
            </li>
          ))}
        </ol>
        <div className="vx-row">
          <button type="button" className="fxt-btn" disabled={s.lines.length >= dia.max_lines} onClick={() => setS((was) => addLine(was, dia.max_lines))}>
            <Plus strokeWidth={1.8} /> Add a line
          </button>
          <small className="vx-count">{`${dialogueScript(s).length.toLocaleString()} / ${dia.script_max.toLocaleString()}`}</small>
        </div>
        <div className="vx-go">
          <button
            type="button"
            className="fxt-btn primary"
            disabled={!menu.ready || !shown || busy}
            onClick={() => void make(`${s.speakers.length} voices`, s.lines.filter((l) => l.text.trim()).map((l) => `${l.speaker + 1}: ${l.text.trim()}`).join("  ·  "))}
          >
            <MessagesSquare strokeWidth={1.8} /> {busy ? "Making it…" : "Make the dialogue"}
          </button>
          <small>{goLine(gap, started, problem, shown, menu.exempt)}</small>
        </div>
        <p className="vx-note">The price is the most it can cost: the words at a slow pace, in 15-second steps.</p>
      </div>
      <Reads title="Dialogues" reads={reads} exempt={menu.exempt} empty="Your dialogues land here. Make the dialogue runs it at the price shown." />
    </div>
  );
}

/* ── cloning your own voice (MiniMax Voice Clone) ──
   Mike's rules (2026-10-27): only your own voice, and you prove it by
   reading the consent line at the start of the sample. The studio listens
   for the line before anything is paid for; no line, no clone. */
function ClonePanel({
  menu,
  onError,
  onChanged,
  onUse,
}: {
  menu: VoiceMenu;
  onError: (why: string) => void;
  /** the voices changed (one made or removed): read the menu again */
  onChanged: () => void;
  /** open the library on this voice */
  onUse: (voiceId: string) => void;
}) {
  const cm = menu.clone;
  const [s, setS] = useState<CloneState>({ name: "", sample: null });
  const [uploading, setUploading] = useState(false);
  const [price, setPrice] = useState<Paid | null>(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [again, setAgain] = useState(0);
  const asked = useRef(0);
  const file = useRef<HTMLInputElement>(null);

  const gap = cloneMissing(s, cm);
  const body = gap ? null : cloneRequest(s);
  const key = body ? JSON.stringify(body) : "";
  useEffect(() => {
    if (!body) return;
    const mine = ++asked.current;
    const timer = setTimeout(() => {
      quoteClone(body)
        .then((q) => {
          if (mine !== asked.current) return;
          setPrice({ credits: q.credits, charged: q.charged });
          setProblem("");
        })
        .catch((e) => {
          if (mine !== asked.current) return;
          setPrice(null);
          setProblem(e instanceof Error ? e.message : "That cannot be priced.");
        });
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key stands for the body
  }, [key, again]);
  const shown = body ? price : null;

  async function pick(f: File | undefined) {
    if (!f) return;
    if (!isSampleFile(f.name, cm.types)) {
      onError(`The sample must be ${cm.types.join(", ")}`);
      return;
    }
    setUploading(true);
    try {
      const r = await cutUploadMedia(f);
      setS((was) => ({ ...was, sample: { audio: r.handle, seconds: r.seconds ?? null, filename: r.filename } }));
    } catch (e) {
      onError(e instanceof Error ? e.message : "The sample did not upload.");
    } finally {
      setUploading(false);
    }
  }

  async function clone() {
    if (!body || !shown || busy) return;
    setBusy(true);
    setStatus("Listening for the consent line…");
    try {
      const started = await runClone({ ...body, expect_credits: shown.credits });
      const job = await waitForJob(started.job_id, (j) => setStatus(j.detail || "Cloning your voice…"));
      announceBalanceChange();
      const out = job as unknown as { voice_id?: string; error?: string | null };
      if (job.status === "done" && out.voice_id) {
        setStatus("");
        setS({ name: "", sample: null });
        onChanged();
      } else {
        setStatus("");
        onError(job.error || "The voice was not cloned. Nothing was charged.");
      }
    } catch (e) {
      // refused before anything ran (a price that moved): price again
      setStatus("");
      onError(e instanceof Error ? e.message : "That did not go through.");
      setPrice(null);
      setAgain((n) => n + 1);
    } finally {
      setBusy(false);
    }
  }

  async function forget(v: ClonedVoice) {
    try {
      await removeClone(v.id);
      onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : "That voice could not be removed.");
    }
  }

  const line = busy ? status : gap ? (s.sample || s.name ? gap : "") : problem || (shown ? priceLine(shown, menu.exempt) : "Pricing…");

  return (
    <div className="vx-panel" role="tabpanel" aria-label="Clone your voice">
      <div className="vx-form">
        <div className="vx-consent">
          <b>Your own voice only</b>
          <ol>
            <li>Start a recording (your phone&apos;s voice memos is fine).</li>
            <li>
              Read this line out loud, first:
              <q>{cm.consent_line}</q>
            </li>
            <li>Keep talking naturally for at least {cm.min_seconds} more seconds (up to {Math.round(cm.max_seconds / 60)} minutes). A quiet room helps.</li>
            <li>Upload it below.</li>
          </ol>
          <small>The studio listens for the line before anything is charged. Without it, no clone is made and nothing is spent.</small>
        </div>
        <div className="fxt-drop" data-loaded={s.sample ? "1" : undefined}>
          <div className="fxt-drop-what">
            <Mic strokeWidth={1.5} />
            <div>
              <b>{s.sample ? s.sample.filename : "Your sample"}</b>
              <span>{uploading ? "Uploading…" : s.sample ? (s.sample.seconds ? `${s.sample.seconds.toFixed(1)}s` : "") : cm.types.join(" · ")}</span>
            </div>
          </div>
          <div className="fxt-drop-acts">
            <input
              ref={file}
              type="file"
              accept={cm.types.join(",") + ",audio/*"}
              hidden
              onChange={(e) => {
                void pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            <button type="button" className="fxt-btn primary" disabled={uploading || busy} onClick={() => file.current?.click()}>
              <Upload strokeWidth={1.8} /> {s.sample ? "Replace the sample" : "Upload the sample"}
            </button>
          </div>
        </div>
        <div className="vx-row">
          <label className="vx-field">
            <span>Name</span>
            <input
              className="vx-name"
              value={s.name}
              maxLength={cm.name_max}
              placeholder="e.g. My voice"
              aria-label="The voice's name"
              onChange={(e) => setS((was) => ({ ...was, name: e.target.value }))}
            />
          </label>
        </div>
        <div className="vx-go">
          <button type="button" className="fxt-btn primary" disabled={!menu.ready || !shown || busy || uploading} onClick={() => void clone()}>
            <UserRound strokeWidth={1.8} /> {busy ? "Cloning…" : "Clone my voice"}
          </button>
          <small>{line}</small>
        </div>
      </div>

      <div className="vx-out">
        <div className="vx-out-head">
          <b>Your voices</b>
          <span>
            {cm.voices.length} of {cm.max_clones}. A voice nobody reads in for {cm.keep_days} days is deleted by the model.
          </span>
        </div>
        {cm.voices.length ? (
          <ul className="vx-reads">
            {cm.voices.map((v) => (
              <li key={v.id} data-status="done">
                <p className="vx-read-words">
                  <b>{v.name}</b>
                </p>
                {v.preview_url ? (
                  <div className="vx-read-play">
                    <audio controls preload="metadata" src={mediaSrc(v.preview_url)} />
                  </div>
                ) : null}
                <small>{keepLine(v)}</small>
                <div className="vx-read-play">
                  <button type="button" className="fxt-btn primary" onClick={() => onUse(v.id)}>
                    <Library strokeWidth={1.8} /> Read a script in it
                  </button>
                  <button type="button" className="fxt-btn" onClick={() => void forget(v)}>
                    <X strokeWidth={1.8} /> Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="vx-empty">Your cloned voices land here, and in the voice library under Your voices.</p>
        )}
      </div>
    </div>
  );
}

/* ── dubbing: the composer's own priced card on a clip picked here ── */
function DubPanel({ menu, initialOn, onError }: { menu: VoiceMenu; initialOn: string | null; onError: (why: string) => void }) {
  const dubMenu: DubMenu = useMemo(() => ({ ...menu.dub, ready: menu.ready, exempt: menu.exempt }), [menu]);
  const [source, setSource] = useState<(ClipChoice & { poster?: string }) | null>(null);
  const [turn, setTurn] = useState<Turn>(() => ({ role: "assistant", content: "Dub a clip", dub: beginDub([], newMadeId(), {}, dubMenu) }));
  const [picker, setPicker] = useState<MediaItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Turn[]>([]);
  const file = useRef<HTMLInputElement>(null);

  const load = useCallback(
    (next: (ClipChoice & { poster?: string }) | null) => {
      setSource(next);
      // a card still waiting is bound to the new clip; one that ran keeps its own
      setTurn((t) => (t.made ? { role: "assistant", content: "Dub a clip", dub: beginDub(next ? [next] : [], newMadeId(), { on: next }, dubMenu) } : { ...t, dub: t.dub ? { ...t.dub, clip: next } : t.dub }));
    },
    [dubMenu],
  );

  // ?on=gen:<id> (a hand-off from the Library): that clip is the source
  const applied = useRef(false);
  useEffect(() => {
    if (applied.current || !initialOn) return;
    applied.current = true;
    const id = assetId(initialOn);
    if (id === null) return;
    getRender(id)
      .then((r) => {
        if (r.kind !== "video") throw new Error("not a clip");
        load({ ref: r.ref, kind: "clip", from: "the clip from your Library", poster: r.thumb ?? undefined });
      })
      .catch(() => onError("That clip is not on your Library wall"));
  }, [initialOn, load, onError]);

  const openPicker = () => {
    if (picker) return setPicker(null);
    getMedia({ kind: "video" })
      .then((w) => setPicker(w.items.filter((m) => m.kind === "video" && m.generated_id)))
      .catch(() => onError("The Library could not be read"));
  };
  const pick = (m: MediaItem) => {
    load({ ref: `gen:${m.generated_id}`, kind: "clip", from: m.prompt ? `“${m.prompt.slice(0, 40)}${m.prompt.length > 40 ? "…" : ""}”` : "a clip from your Library", poster: m.poster ?? undefined });
    setPicker(null);
  };
  async function takeFile(f: File) {
    if (!/^video\//.test(f.type) && !/\.(mp4|mov|webm|m4v)$/i.test(f.name)) {
      onError("Choose a clip: mp4, mov or webm");
      return;
    }
    setLoading(true);
    try {
      const up = await cutUploadMedia(f);
      load({ ref: up.handle, kind: "clip", from: `uploaded · ${f.name}` });
    } catch (e) {
      onError(e instanceof Error ? e.message : "The clip did not upload.");
    } finally {
      setLoading(false);
    }
  }

  const patch = (fn: (s: DubState) => DubState) => setTurn((t) => (t.dub && t.made?.status !== "running" ? { ...t, dub: fn(t.dub) } : t));
  async function approve(credits: number, charged: boolean) {
    const state = turn.dub;
    const body = state ? dubRequest(state) : null;
    if (!state || !body || busy || turn.made?.status === "running") return;
    const made: Made = {
      id: newMadeId(),
      output: "video",
      refs: [],
      status: "running",
      detail: `Dubbing into ${languageName(dubMenu, state.target)}…`,
      prompt: "",
      effect: "dub",
      model: "elevenlabs-dubbing",
    };
    const running: Turn = { ...turn, made, dub: { ...state, paid: { credits, charged } } };
    setBusy(true);
    setTurn(running);
    try {
      const started = await runDub({ ...body, expect_credits: credits });
      const job = await waitForJob(started.job_id, (j) => setTurn((t) => (t.made?.id === made.id && t.made ? { ...t, made: { ...t.made, detail: j.detail || t.made.detail } } : t)));
      announceBalanceChange();
      const out = typeof job.output === "string" ? job.output : "";
      const extra = job as unknown as { asset?: string | null };
      const settled: Made =
        job.status === "done" && out
          ? { ...made, status: "done", detail: job.detail || "", clip: out, image: null, asset: extra.asset ?? null }
          : { ...made, status: "failed", detail: job.error || "The dub was not made. Nothing was charged." };
      const finished = { ...running, made: settled };
      setTurn(finished);
      if (settled.status === "done") setDone((all) => [finished, ...all]);
      else onError(settled.detail ?? "The dub was not made.");
    } catch (e) {
      // refused before anything ran: the card goes back to waiting and prices again
      setTurn((t) => ({ ...t, made: undefined, dub: t.dub ? { ...t.dub, paid: undefined } : t.dub }));
      onError(e instanceof Error ? e.message : "That did not go through.");
    } finally {
      setBusy(false);
    }
  }

  const poster = source?.poster ? mediaSrc(source.poster) : "";

  return (
    <div className="vx-panel" role="tabpanel" aria-label="Dub a clip">
      <div className="vx-form">
        <div className="fxt-drop" data-loaded={source ? "1" : undefined}>
          <div className="fxt-drop-what">
            {poster ? <img src={poster} alt="" /> : <Upload strokeWidth={1.5} />}
            <div>
              <b>{source ? "Your clip" : "Pick a clip with people speaking"}</b>
              <span>{loading ? "Uploading…" : source ? source.from : `Up to ${Math.round(menu.dub.max_seconds / 60)} minutes, with its sound`}</span>
            </div>
          </div>
          <div className="fxt-drop-acts">
            <input
              ref={file}
              type="file"
              accept="video/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void takeFile(f);
                e.target.value = "";
              }}
            />
            <button type="button" className="fxt-btn primary" onClick={openPicker} disabled={loading} aria-expanded={!!picker}>
              <FolderOpen strokeWidth={1.8} /> Pick from the Library
            </button>
            <button type="button" className="fxt-btn" onClick={() => file.current?.click()} disabled={loading}>
              <Upload strokeWidth={1.8} /> Upload a clip
            </button>
            {source ? (
              <button type="button" className="fxt-btn" onClick={() => load(null)}>
                <X strokeWidth={1.8} /> Clear
              </button>
            ) : null}
          </div>
        </div>

        {picker ? (
          <div className="fxt-pick" role="dialog" aria-label="Pick a clip from the Library">
            <div className="fxt-pick-head">
              <b>Your clips</b>
              <span>{picker.length ? "Pick the one to dub." : "No clips on the wall yet."}</span>
              <button type="button" className="fxt-btn" style={{ marginLeft: "auto" }} onClick={() => setPicker(null)}>
                <X strokeWidth={1.8} /> Close
              </button>
            </div>
            <ul className="fxt-pick-grid">
              {picker.map((m) => (
                <li key={m.asset_id}>
                  <button type="button" onClick={() => pick(m)} title={m.prompt || m.asset_name} aria-label={`Use clip ${m.generated_id}`}>
                    {m.poster ? <img src={mediaSrc(m.poster)} alt="" loading="lazy" /> : null}
                    <span className="k">clip</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <DubbingStep turn={turn} menu={dubMenu} choices={source ? [source] : []} busy={busy} onPatch={patch} onApprove={(credits, charged) => void approve(credits, charged)} />
      </div>

      <div className="vx-out">
        <div className="vx-out-head">
          <b>Dubs</b>
          <span>Each one is in your Library.</span>
        </div>
        {done.length ? (
          <ul className="vx-reads">
            {done.map((t) => {
              const id = assetId(t.made?.asset);
              return (
                <li key={t.made?.id} data-status="done">
                  {t.made?.clip ? <video className="vx-dub-media" src={mediaSrc(t.made.clip)} controls playsInline /> : null}
                  <div className="vx-read-play">
                    <small>
                      {t.dub?.clip?.from ?? "A clip"} · into {languageName(dubMenu, t.dub?.target ?? "")}
                      {t.dub?.paid ? ` · ${priceLine(t.dub.paid, menu.exempt)}` : ""}
                    </small>
                    {id !== null ? (
                      <a className="fxt-btn" href={renderDownloadHref(id)} download title="Save the file">
                        <Download strokeWidth={1.8} />
                      </a>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="vx-empty">
            {turn.made && madeStatus(turn.made) === "running" ? turn.made.detail || "Dubbing…" : "Your dubs land here. Render on the card runs it at the price shown."}
          </p>
        )}
      </div>
    </div>
  );
}
