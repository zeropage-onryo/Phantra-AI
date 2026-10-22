"use client";

/* The ad card in the composer (lib/ad-card.ts; docs/tasks/task-url-to-ad.md
   step 3). The beats the motion ad wrote, as a strip of frames with their
   times and voiceover lines; a beat opens to change its headline or its
   line, or to be removed; Build makes the cut from exactly what is on the
   card and Open goes to the editor. Writing and building are both free.

   Simple on purpose: everything else about a beat (the screen, the colour,
   the length) is the editor's once it is built. The look is the step
   card's (still-step.css) with a strip of its own (ad-step.css). */
import Link from "next/link";
import { Check, Clapperboard, Mic, Music, TriangleAlert } from "lucide-react";
import { partButton, type AudioPart } from "@/lib/ad-audio";
import {
  canBuild,
  editBeat,
  editorHref,
  onWhat,
  removeBeat,
  scriptOf,
  span,
  windows,
  wordCount,
  type AdState,
} from "@/lib/ad-card";
import "@/components/studio/still-step.css";
import "@/components/studio/ad-step.css";

export function AdStep({
  ad,
  onPatch,
  onBuild,
  onAudio,
}: {
  ad: AdState;
  onPatch: (fn: (s: AdState) => AdState) => void;
  onBuild: () => void;
  /** the voiceover's or the music's click: it spends, at the price shown */
  onAudio: (which: "voice" | "music") => void;
}) {
  const beats = ad.beats ?? [];
  const times = windows(beats);
  const open = ad.open && beats[ad.open - 1] ? ad.open : null;
  const beat = open ? beats[open - 1] : null;
  const words = wordCount(scriptOf(beats));
  const state = ad.status === "built" ? "done" : ad.status === "ready" ? "waiting" : ad.status;
  const status =
    ad.status === "writing"
      ? "Writing"
      : ad.status === "building"
        ? "Building"
        : ad.status === "built"
          ? "Built"
          : ad.status === "failed"
            ? "Not written"
            : "Ready to build";

  return (
    <div className="ss ad" data-state={state}>
      <div className="ss-head">
        <Clapperboard aria-hidden />
        <b>Ad</b>
        <span>
          · {ad.seconds}s · {ad.aspect}
          {ad.kit ? ` · ${ad.kit} kit` : ""}
        </span>
        <em>{status}</em>
      </div>

      {ad.status === "writing" ? (
        <span className="ss-ok">
          <span className="ss-live" aria-hidden />
          Writing the beats…
        </span>
      ) : null}

      {ad.status === "failed" ? <p className="ad-err">{ad.error || "The ad was not written. Nothing was charged."}</p> : null}

      {beats.length ? (
        <>
          <div className="ad-title">
            <strong>{ad.title}</strong>
            <span>
              {beats.length} beat{beats.length === 1 ? "" : "s"}
              {ad.cards?.length ? ` · ${ad.cards.length} screen${ad.cards.length === 1 ? "" : "s"}` : ""}
              {words ? ` · voiceover ${words} words` : ""}
              {ad.edited ? " · changed by you" : ""}
            </span>
          </div>

          <ol className="ad-strip" aria-label="The beats">
            {beats.map((b, i) => (
              <li key={i}>
                <button
                  type="button"
                  className="ad-beat"
                  data-bg={b.background === "primary" ? "primary" : "plain"}
                  aria-pressed={open === i + 1}
                  disabled={ad.status !== "ready"}
                  onClick={() => onPatch((s) => ({ ...s, open: s.open === i + 1 ? null : i + 1 }))}
                >
                  <span className="ad-time">{span(times[i])}</span>
                  {b.big_word ? <span className="ad-big" aria-hidden>{b.big_word}</span> : null}
                  <span className="ad-hl">{b.headline || b.label || "—"}</span>
                  {b.card || b.picture ? <span className="ad-card-mark" aria-hidden /> : null}
                </button>
                <span className="ad-on">{onWhat(b, ad)}</span>
                {b.voiceover ? <span className="ad-vo">“{b.voiceover}”</span> : null}
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {beat && open && ad.status === "ready" ? (
        <div className="ad-edit">
          <span className="ad-edit-head">
            Beat {open} of {beats.length} · {span(times[open - 1])}
          </span>
          <label>
            <span>On screen</span>
            <input
              value={beat.headline}
              maxLength={120}
              onChange={(e) => onPatch((s) => editBeat(s, open, { headline: e.target.value }))}
            />
          </label>
          <label>
            <span>Voiceover</span>
            <textarea
              rows={2}
              value={beat.voiceover ?? ""}
              maxLength={200}
              onChange={(e) => onPatch((s) => editBeat(s, open, { voiceover: e.target.value }))}
            />
          </label>
          <div className="ad-edit-go">
            <button type="button" className="ad-btn" onClick={() => onPatch((s) => ({ ...s, open: null }))}>
              Done
            </button>
            <button
              type="button"
              className="ad-btn quiet"
              disabled={beats.length <= 1}
              onClick={() => onPatch((s) => removeBeat(s, open))}
            >
              Remove beat
            </button>
          </div>
        </div>
      ) : null}

      {ad.warnings?.length && ad.status !== "writing" ? (
        <ul className="ad-warn">
          {ad.warnings.map((w, i) => (
            <li key={i}>
              <TriangleAlert aria-hidden />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {ad.status === "ready" && ad.error ? <p className="ad-err">{ad.error}</p> : null}

      {ad.status === "ready" || ad.status === "building" ? (
        <div className="ss-go">
          {ad.status === "building" ? (
            <span className="ss-ok">
              <span className="ss-live" aria-hidden />
              Building the ad…
            </span>
          ) : (
            <button type="button" disabled={!canBuild(ad)} onClick={onBuild}>
              Build the ad · free
            </button>
          )}
          <small>Opens in the editor. The voiceover is read and the music added there.</small>
        </div>
      ) : null}

      {ad.status === "built" && (ad.voice || ad.music) ? (
        <ol className="ad-audio" aria-label="Sound on the ad">
          <AudioRow
            n={1}
            icon={<Mic aria-hidden />}
            title="Voiceover"
            detail={`${ad.voice?.label ? `${ad.voice.label} · ` : ""}${words} words, from the start`}
            part={ad.voice}
            button={partButton("voice", ad.voice, !!ad.exempt)}
            placed="On the voice track"
            onRun={() => onAudio("voice")}
          />
          <AudioRow
            n={2}
            icon={<Music aria-hidden />}
            title="Music bed"
            detail={`${ad.music?.label ? `${ad.music.label} · ` : ""}in the kit's direction, under the voice`}
            part={ad.music}
            button={partButton("music", ad.music, !!ad.exempt)}
            placed="On the music track"
            onRun={() => onAudio("music")}
          />
        </ol>
      ) : null}

      {ad.status === "built" && ad.cutId ? (
        <div className="ss-go">
          <span className="ss-ok">
            <Check strokeWidth={2.2} />
            Built for free.
          </span>
          <Link className="ad-btn solid" href={editorHref(ad.cutId)}>
            Open in the editor
          </Link>
        </div>
      ) : null}
    </div>
  );
}

function AudioRow({
  n,
  icon,
  title,
  detail,
  part,
  button,
  placed,
  onRun,
}: {
  n: number;
  icon: React.ReactNode;
  title: string;
  detail: string;
  part?: AudioPart;
  button: string;
  placed: string;
  onRun: () => void;
}) {
  const done = part?.status === "placed";
  return (
    <li data-state={part?.status ?? "pricing"}>
      <span className="ad-n">{done ? <Check strokeWidth={2.4} aria-label="done" /> : n}</span>
      <span className="ad-what">
        <b>
          {icon} {title}
        </b>
        <small>{detail}</small>
        {part?.note ? <small className={part.status === "failed" || part.status === "off" ? "bad" : ""}>{part.note}</small> : null}
      </span>
      {done ? (
        <span className="ad-placed">{placed}</span>
      ) : part?.status === "off" ? null : (
        <button
          type="button"
          className={`ad-btn${n === 1 ? " signal" : ""}`}
          disabled={part?.status !== "ready" && part?.status !== "failed"}
          onClick={onRun}
        >
          {part?.status === "failed" ? `Try again · ${part.credits ?? "?"} credits` : button}
        </button>
      )}
    </li>
  );
}
