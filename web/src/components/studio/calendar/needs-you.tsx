"use client";

/* "Needs you" (2026-10-22, docs/tasks/task-calendar.md): the posts the
   platform refused, drawn above the Renders page's jobs with the reason
   and one button. Post again queues the row for the worker's next tick;
   nothing here spends. Draws nothing when there is nothing to do. */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { listPosts, setPostState, type Post } from "@/lib/studio-api";
import { PlatformIcon, StateGlyph } from "./marks";
import { fmtWhen, whenOf } from "./time";
import "./calendar.css";

export function NeedsYou({ toast }: { toast: (text: string, kind?: "ok" | "err") => void }) {
  const [rows, setRows] = useState<Post[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const load = useCallback(() => {
    listPosts({ state: "error" })
      .then((r) => setRows(r.posts))
      .catch(() => setRows([]));
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (!rows.length) return null;
  return (
    <div className="cal-needsyou" role="status">
      <div className="chead" style={{ marginBottom: 8 }}>
        <h3>Needs you · {rows.length}</h3>
        <span className="m">a post the platform refused; nothing was sent</span>
        <span className="spacer" />
        <Link href="/studio/calendar?view=list" className="m">
          Open the calendar
        </Link>
      </div>
      {rows.map((p) => (
        <div key={p.id} className="cal-lr error" style={{ borderRadius: 8, border: "1px solid var(--danger)", marginBottom: 6 }}>
          <span className="cal-tm">{fmtWhen(whenOf(p.publish_at))}</span>
          <span className="cal-to">
            <PlatformIcon provider={p.provider} size={13} /> {p.provider_name}
          </span>
          <div className="cal-nm">
            <b>{p.caption || p.source_ref}</b>
            <small>{p.error || "The platform refused it."}</small>
          </div>
          <span className="cal-st error">
            <StateGlyph state="error" /> Refused
          </span>
          <div className="cal-acts">
            <Link href={`/studio/calendar?open=${p.id}`} className="cal-btn sm" style={{ textDecoration: "none" }}>
              Open
            </Link>
            <button
              type="button"
              className="cal-primary sm"
              disabled={busy === p.id}
              onClick={() => {
                setBusy(p.id);
                setPostState(p.id, "queued")
                  .then(() => {
                    toast("Queued again; it goes on the next tick", "ok");
                    load();
                  })
                  .catch((err) => toast(err instanceof ApiError ? err.message : "Could not queue it", "err"))
                  .finally(() => setBusy(null));
              }}
            >
              Post again
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
