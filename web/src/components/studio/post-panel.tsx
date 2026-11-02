"use client";

/* "Post…" on a render (2026-10-22, docs/tasks/task-publish-worker.md): the
   Library viewer's door onto `posts`. One connected account, the words,
   now or a time -- and Schedule writes ONE row. Nothing is sent from here:
   the publish worker sends it on the clock, and the toast says when.

   The accounts come from Settings -> Connections; with none connected the
   panel says so and links there. A pending connection (a Discord server
   with no channel picked yet) is not offered. Nothing here spends. */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, Send, X } from "lucide-react";
import { ApiError } from "@/lib/api";
import { createPost, getSocialConnections, getSocialProviders, type SocialConnection, type SocialProvider } from "@/lib/studio-api";
import { ProviderFields, missing, type Values } from "@/components/studio/calendar/provider-fields";
import "@/components/studio/calendar/calendar.css";
import "./post-panel.css";

type Props = {
  /** gen:<id> or asset:<id> */
  source: string;
  kind: "video" | "image" | string;
  onDone: (text: string) => void;
  onError: (text: string) => void;
  onClose: () => void;
  /** filled in by the brain's schedule_post proposal (2026-10-27): the
   *  words, and a local YYYY-MM-DDTHH:MM time (none: post now) */
  caption?: string;
  at?: string | null;
};

/** what the datetime-local input holds for "an hour from now", in local time */
function inAnHour() {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setSeconds(0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function whenWord(iso: string | null | undefined) {
  if (!iso) return "now";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function PostPanel({ source, kind, onDone, onError, onClose, caption: wrote, at: when }: Props) {
  const [connections, setConnections] = useState<SocialConnection[] | null>(null);
  const [connectionId, setConnectionId] = useState<number | null>(null);
  const [caption, setCaption] = useState(wrote ?? "");
  const [mode, setMode] = useState<"now" | "later">(when ? "later" : "now");
  const [at, setAt] = useState(() => when || inAnHour());
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  // the platform's own per-post form (2026-10-22): a subreddit, a story switch
  const [providers, setProviders] = useState<Record<string, SocialProvider>>({});
  const [settings, setSettings] = useState<Values>({});

  useEffect(() => {
    let gone = false;
    getSocialProviders()
      .then((r) => !gone && setProviders(Object.fromEntries(r.providers.map((p) => [p.id, p]))))
      .catch(() => {});
    getSocialConnections()
      .then((r) => {
        if (gone) return;
        const ready = r.connections.filter((c) => c.status === "connected" || c.status === "expired" || c.status === "reconnect");
        setConnections(ready);
        if (ready[0]) setConnectionId(ready[0].id);
      })
      .catch((err) => !gone && setProblem(err instanceof ApiError ? err.message : "Could not read your connected accounts"));
    return () => {
      gone = true;
    };
  }, []);

  const picked = useMemo(() => connections?.find((c) => c.id === connectionId) ?? null, [connections, connectionId]);
  const limit = picked ? providers[picked.provider]?.caption_max ?? 5000 : 5000;
  const fields = picked ? providers[picked.provider]?.settings ?? [] : [];
  const incomplete = missing(fields, settings);
  const needsReconnect = picked ? picked.status !== "connected" : false;

  const submit = () => {
    if (!connectionId || busy) return;
    setBusy(true);
    setProblem(null);
    const publish_at = mode === "later" ? new Date(at).toISOString() : null;
    createPost({ connection_id: connectionId, source, caption: caption.trim(), publish_at, settings })
      .then((post) => {
        onDone(
          publish_at
            ? `Scheduled for ${whenWord(post.publish_at)} on ${post.provider_name}`
            : `Posting to ${post.provider_name} now`,
        );
      })
      .catch((err) => {
        setBusy(false);
        const text = err instanceof ApiError ? err.message : "Could not schedule the post";
        setProblem(text);
        onError(text);
      });
  };

  return (
    <div className="av-post" role="group" aria-label="Post this render">
      <div className="av-post-head">
        <b>
          <Send strokeWidth={1.8} /> Post this {kind === "video" ? "clip" : "still"}
        </b>
        <button type="button" className="av-ib" onClick={onClose} aria-label="Close" title="Close">
          <X strokeWidth={2} />
        </button>
      </div>
      {connections === null && !problem ? (
        <p className="av-post-note">Reading your accounts…</p>
      ) : connections && connections.length === 0 ? (
        <p className="av-post-note">
          No account connected yet. <Link href="/studio/settings/connections">Connect one</Link> and come back.
        </p>
      ) : (
        <>
          <label className="av-post-row">
            <span>To</span>
            <select
              value={connectionId ?? ""}
              onChange={(e) => {
                setConnectionId(Number(e.target.value));
                setSettings({});
              }}
              disabled={busy}
            >
              {(connections ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.provider_name} · {c.label || c.display_name}
                  {c.status !== "connected" ? " (reconnect first)" : ""}
                </option>
              ))}
            </select>
          </label>
          {fields.length ? (
            <div className="av-post-row">
              <span>{picked?.provider_name}</span>
              <ProviderFields fields={fields} values={settings} onChange={setSettings} disabled={busy} compact />
            </div>
          ) : null}
          <label className="av-post-row av-post-words">
            <span>Words</span>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value.slice(0, limit))}
              placeholder={picked?.provider === "instagram" ? "Caption and hashtags" : "What to say with it"}
              rows={3}
              disabled={busy}
            />
            <small>
              {caption.length}/{limit}
            </small>
          </label>
          <div className="av-post-row">
            <span>When</span>
            <div className="av-post-when" role="radiogroup" aria-label="When">
              <button type="button" aria-pressed={mode === "now"} onClick={() => setMode("now")} disabled={busy}>
                Now
              </button>
              <button type="button" aria-pressed={mode === "later"} onClick={() => setMode("later")} disabled={busy}>
                <CalendarClock strokeWidth={1.8} /> Later
              </button>
              {mode === "later" ? (
                <input type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} disabled={busy} aria-label="Date and time" />
              ) : null}
            </div>
          </div>
          {needsReconnect ? (
            <p className="av-post-note av-post-warn">
              That account needs reconnecting first — <Link href="/studio/settings/connections">Settings → Connections</Link>.
            </p>
          ) : null}
          {problem ? <p className="av-post-note av-post-warn">{problem}</p> : null}
          <button type="button" className="av-primary" onClick={submit} disabled={busy || !connectionId || needsReconnect || incomplete.length > 0} title={incomplete.length ? `Still needed: ${incomplete.join(", ")}` : undefined}>
            {busy ? "Scheduling…" : mode === "now" ? "Post now" : "Schedule"}
          </button>
          <p className="av-post-note">
            {incomplete.length ? `Still needed: ${incomplete.join(", ")}. ` : ""}
            <Link href="/studio/calendar">The calendar</Link> shows everything queued. The studio posts it as you, from the account above. Sent on time by the studio&apos;s own clock; you can move or cancel it
            until it goes.
          </p>
        </>
      )}
    </div>
  );
}
