"use client";

/* The Library's Trash (2026-10-20, Mike's call: a 7-day trash). A deleted
   render waits here, restorable, for `trash_days` days; then the server
   removes its file (src/storage_quota.py). "Delete forever" does that now.
   Items in the trash do not count against storage. */
import { useEffect, useState } from "react";
import { RotateCcw, Trash2 } from "lucide-react";
import { API_URL } from "@/lib/api";
import { deleteForever, getTrash, restoreGenerated, type TrashItem } from "@/lib/studio-api";

const abs = (u: string | null) => (u && u.startsWith("/") ? `${API_URL}${u}` : u || undefined);

function daysLeft(purgeAt: string | null): string {
  if (!purgeAt) return "";
  const ms = new Date(purgeAt).getTime() - Date.now();
  const d = Math.max(0, Math.ceil(ms / 86_400_000));
  return d <= 0 ? "removed today" : d === 1 ? "1 day left" : `${d} days left`;
}

export function TrashView({
  onChange,
  toast,
}: {
  /** after a restore or a delete: the wall and the counts reload */
  onChange: () => void;
  toast: (text: string, kind?: "ok" | "err") => void;
}) {
  const [items, setItems] = useState<TrashItem[] | null>(null);
  const [days, setDays] = useState(7);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    getTrash()
      .then((r) => {
        setItems(r.items);
        setDays(r.trash_days);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Trash unavailable"));
  useEffect(() => {
    load();
  }, []);

  const drop = (id: number) => setItems((all) => (all ? all.filter((x) => x.generated_id !== id) : all));
  const restore = (t: TrashItem) => {
    setBusy(t.generated_id);
    restoreGenerated(t.generated_id)
      .then(() => {
        drop(t.generated_id);
        toast(`${t.provider} is back in the Library`);
        onChange();
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not restore", "err"))
      .finally(() => setBusy(null));
  };
  const forever = (t: TrashItem) => {
    setBusy(t.generated_id);
    deleteForever(t.generated_id)
      .then(() => {
        drop(t.generated_id);
        toast(`${t.provider} deleted for good`);
        onChange();
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not delete", "err"))
      .finally(() => setBusy(null));
  };

  return (
    <div className="wall">
      <p className="trash-note">
        Deleted renders stay here for {days} days and don&apos;t count against your storage. After that they&apos;re
        removed for good.
      </p>
      {error ? <div className="stateline err astate">{error}</div> : null}
      {items && !items.length ? <p className="stateline astate">The trash is empty.</p> : null}
      <div className="trash-grid">
        {(items || []).map((t) => (
          <article key={t.generated_id} className="trash-tile">
            <div className="trash-media">
              {t.kind === "video" ? (
                t.poster ? (
                  // eslint-disable-next-line @next/next/no-img-element -- a poster, sized by its box
                  <img src={abs(t.poster)} alt="" />
                ) : (
                  <video src={abs(t.url)} muted preload="metadata" />
                )
              ) : (
                // eslint-disable-next-line @next/next/no-img-element -- a still, sized by its box
                <img src={abs(t.poster || t.url)} alt="" />
              )}
            </div>
            <div className="trash-meta">
              <b>{t.provider}</b>
              <span>{daysLeft(t.purge_at)}</span>
            </div>
            <div className="trash-acts">
              <button type="button" className="btn" disabled={busy === t.generated_id} onClick={() => restore(t)}>
                <RotateCcw size={13} strokeWidth={1.8} /> Restore
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy === t.generated_id}
                onClick={() => forever(t)}
                title="Remove the file now. This can't be undone."
              >
                <Trash2 size={13} strokeWidth={1.8} /> Delete forever
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
