"use client";

/* Settings → Preferences (2026-10-11): how the studio behaves for you.

   - The assistant: which creature, its look, its colour and how it talks.
     Saved to the account (PUT /api/assistant/persona), so every browser
     meets the same one; the floating assistant on this page changes the
     moment it is saved (lib/assistant PERSONA_EVENT). The options are
     lib/mascot.ts -- the same pictures the assistant's own card offers.
   - Generation defaults, ON THIS BROWSER: the image model and Ask / Auto
     are the composer's own remembered choices (lib/composer.ts), so
     setting them here and picking them on Create are one thing. The frame
     and the scene length are a default a new scene starts from
     (lib/scene-defaults.ts). None of it follows you to another device.
   - Notifications: the activity tray's own switch (lib/notify-pref.ts).
   - Keyboard: the shortcuts that exist, to read (lib/shortcuts.ts).

   Nothing here spends, and nothing here changes what a render costs. */
import { useEffect, useState, useSyncExternalStore, type CSSProperties } from "react";
import { apiFetch } from "@/lib/api";
import {
  TONES,
  announcePersona,
  asMascotPersona,
  getAssistantMemory,
  loadPersona,
  putPersona,
  savePersona,
  type Persona,
  type Tone,
} from "@/lib/assistant";
import { GENERATE_MODES, loadGenerateMode, loadImageModel, saveGenerateMode, saveImageModel } from "@/lib/composer";
import {
  CREATURES,
  DEFAULT_AVATAR,
  coloursOf,
  creatureOf,
  decodeMascot,
  encodeMascot,
  looksOf,
  nameOf,
  type ColourId,
  type Mascot,
} from "@/lib/mascot";
import { NOTIFY_BLOCKED, canNotify, readNotify, setNotify, subscribeNotify } from "@/lib/notify-pref";
import { modKey } from "@/lib/palette";
import { loadFrame, loadSceneSeconds, saveFrame, saveSceneSeconds, startFrame, startSeconds } from "@/lib/scene-defaults";
import { SECTIONS } from "@/lib/settings-sections";
import { SHORTCUTS, keyLabel } from "@/lib/shortcuts";
import { getImageModels, type ImageModels } from "@/lib/studio-api";
import { AssistantAvatar, MascotStill } from "@/components/studio/assistant-avatar";
import { useShell } from "@/components/studio/shell";
import {
  Button,
  Field,
  Row,
  SectionHeader,
  Segmented,
  Select,
  SettingsCard,
  Skeleton,
  SkeletonRows,
  Switch,
  errorText,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "preferences")!;
const subscribeNothing = () => () => {};

/* ── the assistant ── */

function AssistantCard() {
  const { me, toast } = useShell();
  const account = me?.account?.slug ?? "";
  // what is saved, and what is being tried on before Save
  const [saved, setSaved] = useState<Persona | null>(null);
  const [draft, setDraft] = useState<Persona | null>(null);
  const [busy, setBusy] = useState(false);

  // the browser's copy paints first; the account's copy then wins
  useEffect(() => {
    if (!account) return;
    let live = true;
    const local = loadPersona(account);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is only readable after mount
    setSaved(local ?? asMascotPersona({ avatar: DEFAULT_AVATAR }));
    getAssistantMemory()
      .then((m) => live && m.persona && setSaved(asMascotPersona(m.persona)))
      .catch(() => {
        /* the browser's copy is what there is */
      });
    return () => {
      live = false;
    };
  }, [account]);

  if (!saved) return <SkeletonRows rows={3} />;

  const now = draft ?? saved;
  const mascot = decodeMascot(now.avatar);
  const looks = looksOf(creatureOf(mascot));
  const look = looks.find((l) => l.id === mascot.look) ?? looks[0];
  const colours = coloursOf(look.id);
  const colour = colours.find((c) => c.id === mascot.colour) ?? colours[0];
  const dirty = !!draft && (draft.avatar !== saved.avatar || draft.tone !== saved.tone);

  // a look keeps the colour picked when it comes in that colour
  const inColour = (lookId: string, c: ColourId): Mascot => ({
    look: lookId,
    colour: coloursOf(lookId).some((x) => x.id === c) ? c : "own",
  });
  const wear = (m: Mascot) => setDraft({ name: nameOf(m), avatar: encodeMascot(m), tone: now.tone });

  const apply = async (next: Persona, said: string, undo?: Persona) => {
    setBusy(true);
    try {
      const res = await putPersona(next);
      const kept = asMascotPersona(res.persona);
      savePersona(account, kept);
      announcePersona();
      setSaved(kept);
      setDraft(null);
      toast(said, "ok", undo ? { action: { label: "Undo", run: () => apply(undo, `${undo.name} is back`) } } : undefined);
    } catch (err) {
      toast(errorText(err, "Could not save the assistant"), "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="zset-id">
        <span className="zset-mascot">
          <AssistantAvatar avatar={now.avatar} state="idle" size="xl" title={`${now.name}, your assistant`} />
        </span>
        <div className="zset-id-text">
          <b>{now.name}</b>
          <span>
            {[look.label, colours.length > 1 ? colour.name : null, TONES.find((t) => t.id === now.tone)?.label]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
        {dirty ? (
          <div className="zset-actions zset-id-actions">
            <Button
              variant="primary"
              disabled={busy}
              onClick={() => apply(draft!, `${draft!.name} it is`, saved)}
            >
              {busy ? "Saving…" : "Save"}
            </Button>
            <Button variant="quiet" disabled={busy} onClick={() => setDraft(null)}>
              Cancel
            </Button>
          </div>
        ) : null}
      </div>
      <Row
        wide
        label="Who"
        hint="The name comes with the creature."
        control={
          <div className="zset-picks" role="group" aria-label="Creature">
            {CREATURES.map((c) => {
              const first = looksOf(c.id)[0].id;
              return (
                <button
                  type="button"
                  key={c.id}
                  className="zset-pick"
                  aria-pressed={look.creature === c.id}
                  title={c.note}
                  onClick={() => wear(inColour(first, mascot.colour))}
                >
                  <MascotStill avatar={encodeMascot({ look: first, colour: "own" })} px={48} />
                  {c.name}
                </button>
              );
            })}
          </div>
        }
      />
      {looks.length > 1 ? (
      <Row
        wide
        label="Look"
        control={
          <div className="zset-picks" role="group" aria-label="Look">
            {looks.map((l) => (
              <button
                type="button"
                key={l.id}
                className="zset-pick"
                aria-pressed={l.id === look.id}
                onClick={() => wear(inColour(l.id, mascot.colour))}
              >
                <MascotStill avatar={encodeMascot(inColour(l.id, mascot.colour))} px={48} />
                {l.label}
              </button>
            ))}
          </div>
        }
      />
      ) : null}
      {colours.length > 1 ? (
      <Row
        label="Colour"
        hint={colour.name}
        control={
          <div className="zset-swatches" role="group" aria-label="Colour">
            {colours.map((c) => (
              <button
                type="button"
                key={c.id}
                className="zset-swatch"
                aria-pressed={c.id === colour.id}
                aria-label={c.id === "own" ? `${c.name}, its own colour` : c.name}
                title={c.name}
                style={{ "--sw": c.hex } as CSSProperties}
                onClick={() => wear({ look: look.id, colour: c.id })}
              />
            ))}
          </div>
        }
      />
      ) : null}
      <Row
        label="How it talks"
        hint="The tone of its answers, not what it knows."
        control={
          <Segmented<Tone>
            label="How the assistant talks"
            value={now.tone}
            options={TONES.map((t) => ({ id: t.id, label: t.label }))}
            onChange={(tone) => setDraft({ ...now, tone })}
          />
        }
      />
    </>
  );
}

/* ── generation defaults, on this browser ── */

type Lengths = { min: number; max: number; default: number };
type Frames = { ratios: { id: string; label: string; size: string }[]; default: string };

function DefaultsCard() {
  const { toast } = useShell();
  const [models, setModels] = useState<ImageModels | null>(null);
  const [frames, setFrames] = useState<Frames | null>(null);
  const [lengths, setLengths] = useState<Lengths | null>(null);
  const [asked, setAsked] = useState(false);
  // what this browser holds, read after mount (localStorage)
  const [stored, setStored] = useState<{ model: string; mode: "ask" | "auto"; frame: string; seconds: number } | null>(
    null,
  );
  const [typed, setTyped] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is only readable after mount
    setStored({ model: loadImageModel(), mode: loadGenerateMode(), frame: loadFrame(), seconds: loadSceneSeconds() });
    // each control shows only when its route answers, as on Create
    Promise.allSettled([
      getImageModels().then(setModels),
      apiFetch<Frames>("/render-choices").then(setFrames),
      apiFetch<Lengths>("/scene-lengths").then(setLengths),
    ]).then(() => setAsked(true));
  }, []);

  if (!stored || !asked) return <SkeletonRows rows={4} />;

  const model = models ? (models.items.some((m) => m.id === stored.model) ? stored.model : models.default) : "";
  const picked = models?.items.find((m) => m.id === model);
  const frame = frames ? startFrame(stored.frame, frames.ratios.map((r) => r.id), frames.default) : "";
  const seconds = lengths ? startSeconds(stored.seconds, lengths) : 0;

  const commitSeconds = () => {
    if (typed === null || !lengths) return;
    const n = Math.round(Number(typed));
    setTyped(null);
    if (!Number.isFinite(n) || n === seconds) return;
    const kept = Math.min(lengths.max, Math.max(lengths.min, n));
    saveSceneSeconds(kept);
    setStored({ ...stored, seconds: kept });
    if (kept !== n) toast(`A scene is between ${lengths.min} and ${lengths.max} seconds: set to ${kept}`);
  };

  return (
    <>
      {models ? (
        <Row
          label="Image model"
          htmlFor="pref-image-model"
          hint={
            picked
              ? `${picked.note ? `${picked.note} · ` : ""}${picked.credits} credits a still. The model picker on Create shows the same choice.`
              : "The model a still is drawn on."
          }
          control={
            <Select
              id="pref-image-model"
              className="zset-field-md"
              value={model}
              onChange={(e) => {
                saveImageModel(e.target.value);
                setStored({ ...stored, model: e.target.value });
              }}
            >
              {models.items.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </Select>
          }
        />
      ) : null}
      <Row
        label="Before a still is drawn"
        hint={GENERATE_MODES.find((m) => m.id === stored.mode)?.note}
        control={
          <Segmented
            label="Before a still is drawn"
            value={stored.mode}
            options={[
              { id: "ask", label: "Ask first" },
              { id: "auto", label: "Auto" },
            ]}
            onChange={(mode) => {
              saveGenerateMode(mode);
              setStored({ ...stored, mode });
            }}
          />
        }
      />
      {frames ? (
        <Row
          label="Frame"
          htmlFor="pref-frame"
          hint="The shape a new scene starts in. Changing it on Create is for that scene only."
          control={
            <Select
              id="pref-frame"
              className="zset-field-md"
              value={frame}
              onChange={(e) => {
                saveFrame(e.target.value === frames.default ? "" : e.target.value);
                setStored({ ...stored, frame: e.target.value });
              }}
            >
              {frames.ratios.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                  {r.id === frames.default ? " (the studio’s default)" : ""}
                </option>
              ))}
            </Select>
          }
        />
      ) : null}
      {lengths ? (
        <Row
          label="Scene length"
          htmlFor="pref-seconds"
          hint={`The length a new scene starts at, ${lengths.min} to ${lengths.max} seconds. The studio’s own is ${lengths.default}.`}
          control={
            <>
              <Field
                id="pref-seconds"
                className="zset-field-sm"
                type="number"
                inputMode="numeric"
                min={lengths.min}
                max={lengths.max}
                step={1}
                value={typed ?? String(seconds)}
                onChange={(e) => setTyped(e.target.value)}
                onBlur={commitSeconds}
                onKeyDown={(e) => e.key === "Enter" && commitSeconds()}
              />
              <span className="zset-value">seconds</span>
              {seconds !== lengths.default ? (
                <Button
                  variant="quiet"
                  size="sm"
                  onClick={() => {
                    saveSceneSeconds(0);
                    setTyped(null);
                    setStored({ ...stored, seconds: 0 });
                  }}
                >
                  Reset
                </Button>
              ) : null}
            </>
          }
        />
      ) : null}
      {!models && !frames && !lengths ? (
        <Row label="Defaults" hint="The studio could not be asked for its options just now." />
      ) : null}
    </>
  );
}

/* ── notifications ── */

function NotifyRow() {
  const { toast } = useShell();
  const on = useSyncExternalStore(subscribeNotify, readNotify, () => false);
  const able = useSyncExternalStore(subscribeNothing, canNotify, () => true);
  return (
    <Row
      label="When a long job finishes"
      hint={
        able
          ? "A browser notification for a render, a sheet or an export that ran a while and ended while you were on another tab. The bell in the header has the same switch."
          : "This browser cannot show notifications."
      }
      control={
        <Switch
          label="Notify me when a long job finishes while I am away from this tab"
          checked={on && able}
          disabled={!able}
          onChange={async (next) => {
            if ((await setNotify(next)) === "blocked") toast(NOTIFY_BLOCKED, "err");
          }}
        />
      }
    />
  );
}

/* ── keyboard ── */

function Keys() {
  const mod = useSyncExternalStore(
    subscribeNothing,
    () => modKey(navigator.platform || navigator.userAgent),
    () => "⌘" as const,
  );
  return (
    <div className="zset-keys">
      {SHORTCUTS.map((group) => (
        <section key={group.where} aria-label={group.where}>
          <h4>{group.where}</h4>
          <dl>
            {group.items.map((item) => (
              <div key={item.does}>
                <dt>
                  {item.keys.map((k) => (
                    <kbd key={k}>{keyLabel(k, mod)}</kbd>
                  ))}
                </dt>
                <dd>{item.does}</dd>
              </div>
            ))}
          </dl>
          {group.note ? <p className="zset-note">{group.note}</p> : null}
        </section>
      ))}
    </div>
  );
}

export function PreferencesSection() {
  const { me } = useShell();
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard title="Assistant" description="follows you to every browser">
        {me ? <AssistantCard /> : <SkeletonRows rows={3} />}
      </SettingsCard>
      <SettingsCard title="Generation defaults" description="on this browser">
        {me ? (
          <DefaultsCard />
        ) : (
          <div className="zset-card-pad">
            <Skeleton width="50%" />
          </div>
        )}
      </SettingsCard>
      <SettingsCard title="Notifications" description="on this browser">
        <NotifyRow />
      </SettingsCard>
      <SettingsCard title="Keyboard" description="the shortcuts there are">
        <Keys />
      </SettingsCard>
    </>
  );
}
