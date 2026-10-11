"use client";

/* Review and post (2026-10-11, src/publish_review.py).

   Claude (the `prepare_post` tool) or a studio button drafts a post and
   sends the person here. Nothing has been posted yet. This page is where
   the person sees the clip and the account it goes to, answers every
   question the platform requires, and presses Post themselves -- the only
   way a post leaves the studio.

   It follows TikTok's Direct Post guidelines, because its audit reviews
   this exact screen: the account's name and what it may post are fetched
   fresh on every load; who can see the post has NO default; comments,
   Duet and Stitch start unticked and stay off when the account has them
   off; commercial content is disclosed with the platform's own labels;
   the declaration under the button is the server's text, word for word;
   and nothing is sent until the person agrees and presses Post. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, Clock, Send, XCircle } from "lucide-react";
import { ApiError } from "@/lib/api";
import {
  cancelPublish,
  getPublishSession,
  submitPublish,
  type PublishChoices,
  type PublishSession,
} from "@/lib/studio-api";

const CARD = "rounded-xl border border-white/10 bg-white/[0.03] p-4 sm:p-5";
const BTN = "rounded-lg px-3 py-1.5 text-[13px] transition disabled:opacity-40";
// `!`: the studio's `.zps button { color: inherit }` outranks a plain colour class
const PRI = `${BTN} bg-white text-black! hover:bg-white/90 disabled:bg-white/15 disabled:text-white/40! disabled:opacity-100`;
const GHOST = `${BTN} border border-white/15 text-white/80 hover:border-white/40`;
const FIELD =
  "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white/90 outline-none focus:border-white/30";
const LABEL = "mb-1 block text-[11px] uppercase tracking-wide text-white/40";
const HINT = "text-[12px] text-white/40";
const WARN = "rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-[13px] text-amber-100";
const ERR = "rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-[13px] text-red-200";

const PRIVACY_LABEL: Record<string, string> = {
  PUBLIC_TO_EVERYONE: "Everyone",
  MUTUAL_FOLLOW_FRIENDS: "Friends",
  FOLLOWER_OF_CREATOR: "Followers",
  SELF_ONLY: "Only me",
};

const errorText = (err: unknown, fallback: string) =>
  err instanceof ApiError ? err.message : err instanceof Error ? err.message || fallback : fallback;

function Check({
  label,
  checked,
  disabled,
  note,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  note?: string;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className={`flex items-start gap-2 text-[13px] ${disabled ? "text-white/35" : "text-white/85"}`}>
      <input
        type="checkbox"
        className="mt-0.5"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        {label}
        {note ? <span className={`${HINT} block`}>{note}</span> : null}
      </span>
    </label>
  );
}

export default function PublishReview() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<PublishSession | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // null until the person edits it: the drafted caption shows until then
  const [captionEdit, setCaptionEdit] = useState<string | null>(null);
  const [choices, setChoices] = useState<Omit<PublishChoices, "caption">>({
    privacy_level: null, // no default: the guidelines require the person to choose
    allow_comment: false,
    allow_duet: false,
    allow_stitch: false,
    commercial: { enabled: false, your_brand: false, branded_content: false },
    is_aigc: true,
    consent: false,
  });

  const load = useCallback(async () => {
    try {
      const s = await getPublishSession(id);
      setSession(s);
      setLoadError(null);
      return s;
    } catch (err) {
      setLoadError(errorText(err, "Could not load this post."));
      return null;
    }
  }, [id]);

  useEffect(() => {
    let live = true;
    getPublishSession(id).then(
      (s) => {
        if (live) setSession(s);
      },
      (err) => {
        if (live) setLoadError(errorText(err, "Could not load this post."));
      },
    );
    return () => {
      live = false;
    };
  }, [id]);

  // TikTok processes a post after the press; poll until it says how it ended
  useEffect(() => {
    if (session?.status !== "posting") return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [session?.status, load]);

  const creator = session?.creator ?? null;
  const branded = choices.commercial.enabled && choices.commercial.branded_content;
  const commercialIncomplete =
    choices.commercial.enabled && !choices.commercial.your_brand && !choices.commercial.branded_content;
  const tooLong = !!(creator?.max_seconds && session?.seconds && session.seconds > creator.max_seconds);
  const declaration = branded ? session?.declarations?.branded : session?.declarations?.default;

  const blocked = useMemo(() => {
    if (!session || session.status !== "draft") return "This post can no longer be sent.";
    if (session.media_problem) return session.media_problem;
    if (session.creator_problem || !creator) return session.creator_problem || "Loading the account…";
    if (tooLong) return `This clip is longer than this account may post (${creator.max_seconds}s).`;
    if (!choices.privacy_level) return "Choose who can see this post.";
    if (commercialIncomplete) return "Choose “Your brand”, “Branded content” or both.";
    if (!choices.consent) return "Agree to the declaration to post.";
    return null;
  }, [session, creator, tooLong, choices, commercialIncomplete]);

  const caption = captionEdit ?? session?.caption ?? "";
  const set = <K extends keyof typeof choices>(key: K, value: (typeof choices)[K]) =>
    setChoices((c) => ({ ...c, [key]: value }));
  const setCommercial = (patch: Partial<PublishChoices["commercial"]>) =>
    setChoices((c) => {
      const commercial = { ...c.commercial, ...patch };
      // branded content cannot be private: drop "Only me" if it was chosen
      const nowBranded = commercial.enabled && commercial.branded_content;
      const privacy = nowBranded && c.privacy_level === "SELF_ONLY" ? null : c.privacy_level;
      // the declaration text changes with branded content: agreement to the
      // old text is not agreement to the new one
      const wasBranded = c.commercial.enabled && c.commercial.branded_content;
      const consent = nowBranded === wasBranded ? c.consent : false;
      return { ...c, commercial, privacy_level: privacy, consent };
    });

  async function post() {
    if (blocked || busy) return;
    setBusy(true);
    setSendError(null);
    try {
      setSession(await submitPublish(id, { ...choices, caption }));
    } catch (err) {
      setSendError(errorText(err, "The post was not sent."));
    } finally {
      setBusy(false);
    }
  }

  async function discard() {
    setBusy(true);
    try {
      setSession(await cancelPublish(id));
    } catch (err) {
      setSendError(errorText(err, "Could not discard the draft."));
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="mx-auto w-full max-w-3xl p-6">
        <div className={ERR}>{loadError}</div>
      </div>
    );
  }
  if (!session) return <div className="mx-auto w-full max-w-3xl p-6 text-[13px] text-white/50">Loading…</div>;

  const finished = session.status !== "draft";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-center gap-2">
        <Send size={18} className="text-white/60" />
        <h1 className="text-[15px] tracking-wide">Post to TikTok</h1>
        <span className={HINT}>
          {session.created_via === "mcp" ? "drafted by Claude — " : ""}nothing is posted until you press Post
        </span>
      </header>

      {session.status === "posting" ? (
        <div className={WARN}>
          <Clock size={14} className="mr-1 inline" /> Sent. TikTok is processing it — it can take a few
          minutes to appear on your profile.
          {session.poll_problem ? <span className="block opacity-70">{session.poll_problem}</span> : null}
        </div>
      ) : null}
      {session.status === "published" ? (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-[13px] text-emerald-100">
          <CheckCircle2 size={14} className="mr-1 inline" /> Posted to TikTok.
        </div>
      ) : null}
      {session.status === "failed" ? (
        <div className={ERR}>
          <XCircle size={14} className="mr-1 inline" /> TikTok did not post it
          {session.result?.error ? `: ${session.result.error}` : "."}
        </div>
      ) : null}
      {session.status === "cancelled" ? <div className={WARN}>This draft was discarded.</div> : null}
      {session.status === "expired" ? (
        <div className={WARN}>This draft expired. Ask Claude or the studio to prepare it again.</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-[minmax(0,280px)_1fr]">
        <section className={CARD}>
          <label className={LABEL}>Preview</label>
          <video
            src={session.media_url}
            controls
            playsInline
            className="mx-auto aspect-[9/16] max-h-[55vh] w-auto max-w-full rounded-lg bg-black object-contain md:max-h-none md:w-full"
          />
          <p className={`${HINT} mt-2`}>
            {session.source}
            {session.seconds ? ` · ${Math.round(session.seconds)}s` : ""}
          </p>
        </section>

        <section className={`${CARD} flex flex-col gap-4`}>
          <div>
            <label className={LABEL}>Posting to</label>
            {creator ? (
              <div className="flex items-center gap-2 text-[13px]">
                {creator.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={creator.avatar_url} alt="" className="size-7 rounded-full" />
                ) : null}
                <span className="text-white/90">{creator.nickname}</span>
                <span className="text-white/40">@{creator.username}</span>
              </div>
            ) : (
              <div className={session.creator_problem ? ERR : HINT}>
                {session.creator_problem || "Loading the account…"}
              </div>
            )}
          </div>

          {session.media_problem && !finished ? <div className={ERR}>{session.media_problem}</div> : null}

          <div>
            <label className={LABEL} htmlFor="caption">
              Caption
            </label>
            <textarea
              id="caption"
              className={`${FIELD} min-h-[90px]`}
              maxLength={session.caption_max ?? 2200}
              disabled={finished}
              value={caption}
              onChange={(e) => setCaptionEdit(e.target.value)}
            />
            <p className={HINT}>
              {caption.length}/{session.caption_max ?? 2200}
            </p>
          </div>

          <div>
            <label className={LABEL} htmlFor="privacy">
              Who can see this post
            </label>
            <select
              id="privacy"
              className={FIELD}
              disabled={finished || !creator}
              value={choices.privacy_level ?? ""}
              onChange={(e) => set("privacy_level", e.target.value || null)}
            >
              <option value="" disabled>
                Choose…
              </option>
              {(creator?.privacy_options ?? []).map((p) => {
                const off = branded && p === "SELF_ONLY";
                return (
                  <option key={p} value={p} disabled={off}>
                    {PRIVACY_LABEL[p] ?? p}
                    {off ? " — not available for branded content" : ""}
                  </option>
                );
              })}
            </select>
          </div>

          <div className="grid gap-2">
            <label className={LABEL}>Allow others to</label>
            <Check
              label="Comment"
              checked={choices.allow_comment}
              disabled={finished || !creator || creator.comment_disabled}
              note={creator?.comment_disabled ? "Turned off in your TikTok settings" : undefined}
              onChange={(v) => set("allow_comment", v)}
            />
            <Check
              label="Duet"
              checked={choices.allow_duet}
              disabled={finished || !creator || creator.duet_disabled}
              note={creator?.duet_disabled ? "Turned off in your TikTok settings" : undefined}
              onChange={(v) => set("allow_duet", v)}
            />
            <Check
              label="Stitch"
              checked={choices.allow_stitch}
              disabled={finished || !creator || creator.stitch_disabled}
              note={creator?.stitch_disabled ? "Turned off in your TikTok settings" : undefined}
              onChange={(v) => set("allow_stitch", v)}
            />
          </div>

          <div className="grid gap-2">
            <label className={LABEL}>Disclose commercial content</label>
            <Check
              label="This post promotes a brand, product or service"
              checked={choices.commercial.enabled}
              disabled={finished}
              onChange={(v) => setCommercial({ enabled: v, ...(v ? {} : { your_brand: false, branded_content: false }) })}
            />
            {choices.commercial.enabled ? (
              <div className="ml-6 grid gap-2">
                <Check
                  label="Your brand"
                  note="You are promoting yourself or your own business. It will be labeled “Promotional content”."
                  checked={choices.commercial.your_brand}
                  disabled={finished}
                  onChange={(v) => setCommercial({ your_brand: v })}
                />
                <Check
                  label="Branded content"
                  note="You are promoting another brand or a third party. It will be labeled “Paid partnership”."
                  checked={choices.commercial.branded_content}
                  disabled={finished}
                  onChange={(v) => setCommercial({ branded_content: v })}
                />
              </div>
            ) : null}
          </div>

          <Check
            label="Label as AI-generated"
            checked={session.ai_generated || choices.is_aigc}
            disabled={finished || session.ai_generated}
            note={
              session.ai_generated
                ? "Made with the studio's AI models, so TikTok's AI-generated label is always on."
                : "Turn off only if this is your own camera footage."
            }
            onChange={(v) => set("is_aigc", v)}
          />

          {!finished ? (
            <div className="grid gap-3 border-t border-white/10 pt-4">
              <Check
                label={declaration ?? ""}
                checked={choices.consent}
                onChange={(v) => set("consent", v)}
              />
              {sendError ? <div className={ERR}>{sendError}</div> : null}
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className={PRI} disabled={!!blocked || busy} onClick={post}>
                  {busy ? "Sending…" : "Post"}
                </button>
                <button type="button" className={GHOST} disabled={busy} onClick={discard}>
                  Discard draft
                </button>
                {blocked ? <span className={HINT}>{blocked}</span> : null}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
