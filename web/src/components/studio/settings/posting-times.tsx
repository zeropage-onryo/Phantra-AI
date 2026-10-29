"use client";

/* Posting times (2026-10-22, docs/tasks/task-calendar.md): the hours one
   account likes to post, by weekday, in the person's own zone. Set once,
   kept on the connection (PUT /api/social/connections/{id}/posting-times).
   The calendar draws them as empty slots and its drawer defaults to the
   next free one; the worker never reads them. Nothing here sends. */
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { setPostingTimes, type PostingTimes, type SocialConnection } from "@/lib/studio-api";
import { Button, Chip, Field } from "@/components/studio/settings/ui";

const DAYS: [string, string][] = [
  ["mon", "Mon"],
  ["tue", "Tue"],
  ["wed", "Wed"],
  ["thu", "Thu"],
  ["fri", "Fri"],
  ["sat", "Sat"],
  ["sun", "Sun"],
];

const zoneOf = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
};

const fmt = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }).replace(/\s?([AP])M$/i, (_, p) => p.toLowerCase());
};

export function PostingTimesEditor({ connection, onSaved, onCancel, toast }: { connection: SocialConnection; onSaved: (c: SocialConnection) => void; onCancel: () => void; toast: (t: string, k?: "ok" | "err") => void }) {
  const stored = connection.posting_times;
  const [tz] = useState(() => (stored.tz && stored.tz !== "UTC" ? stored.tz : zoneOf()));
  const [days, setDays] = useState<Record<string, string[]>>(() => Object.fromEntries(DAYS.map(([k]) => [k, [...(stored.days[k] ?? [])]])));
  const [adding, setAdding] = useState("09:00");
  const [onDays, setOnDays] = useState<Set<string>>(() => new Set(["mon", "tue", "wed", "thu", "fri"]));
  const [busy, setBusy] = useState(false);

  const add = () => {
    if (!/^\d{1,2}:\d{2}$/.test(adding)) return;
    setDays((d) => {
      const next = { ...d };
      for (const k of onDays) next[k] = Array.from(new Set([...(next[k] ?? []), adding])).sort();
      return next;
    });
  };
  const drop = (day: string, t: string) => setDays((d) => ({ ...d, [day]: (d[day] ?? []).filter((x) => x !== t) }));

  const save = () => {
    setBusy(true);
    const body: PostingTimes = { tz, days };
    setPostingTimes(connection.id, body)
      .then((c) => {
        toast("Posting times saved", "ok");
        onSaved(c);
      })
      .catch((err) => toast(err instanceof ApiError ? err.message : "Could not save the times", "err"))
      .finally(() => setBusy(false));
  };

  const total = Object.values(days).reduce((n, l) => n + l.length, 0);
  return (
    <div className="zset-social-pick" style={{ flexDirection: "column", alignItems: "stretch" }}>
      <div className="zset-times" aria-label="Posting times by weekday">
        {DAYS.map(([k, label]) => (
          <div key={k} className="zset-times-day">
            <small>{label}</small>
            {(days[k] ?? []).map((t) => (
              <button key={t} type="button" className="zset-time" onClick={() => drop(k, t)} title="Remove this time">
                {fmt(t)}
              </button>
            ))}
            {!(days[k] ?? []).length ? <span className="zset-time off">—</span> : null}
          </div>
        ))}
      </div>
      <div className="zset-social-pick" style={{ marginTop: 4 }}>
        <Field type="time" value={adding} onChange={(e) => setAdding(e.target.value)} aria-label="A time to add" style={{ flex: "0 0 120px" }} />
        <span style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {DAYS.map(([k, label]) => (
            <Chip
              key={k}
              pressed={onDays.has(k)}
              onClick={() =>
                setOnDays((s) => {
                  const n = new Set(s);
                  if (n.has(k)) n.delete(k);
                  else n.add(k);
                  return n;
                })
              }
            >
              {label}
            </Chip>
          ))}
        </span>
        <Button size="sm" onClick={add} disabled={!onDays.size}>
          Add to those days
        </Button>
      </div>
      <p className="zset-row-hint" style={{ margin: 0 }}>
        {total ? `${total} a week` : "No times yet"} · in {tz}. The calendar shows these as empty slots; the next free one is what a new post
        gets by default. Nothing is sent by them.
      </p>
      <div className="zset-social-pick" style={{ marginTop: 0 }}>
        <Button size="sm" variant="primary" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save times"}
        </Button>
        <Button size="sm" variant="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
