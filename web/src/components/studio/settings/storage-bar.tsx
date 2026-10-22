"use client";

/* Storage, next to the plan (2026-10-20, Mike's call). What the workspace
   keeps in the bucket against its plan's limit (GET /api/storage,
   src/storage_quota.py): renders, element photos and uploads. Renders in
   the Trash don't count. Past the limit, uploads are refused; renders are
   not. A server that cannot count (no bucket) says so and shows no bar. */
import { useEffect, useState } from "react";
import Link from "next/link";
import { getStorage, type StorageUsage } from "@/lib/studio-api";

export function StorageBar() {
  const [s, setS] = useState<StorageUsage | null>(null);
  useEffect(() => {
    getStorage()
      .then(setS)
      .catch(() => setS(null));
  }, []);
  if (!s) return null;
  if (!s.measured)
    return (
      <div className="zset-storage">
        <div className="zset-storage-head">
          <span>Storage</span>
          <span className="m">not measured on this server</span>
        </div>
      </div>
    );
  const pct = s.limit_bytes ? Math.min(100, ((s.used_bytes ?? 0) / s.limit_bytes) * 100) : 0;
  const tone = s.over ? "over" : s.near ? "near" : "";
  return (
    <div className="zset-storage" data-tone={tone || undefined}>
      <div className="zset-storage-head">
        <span>Storage</span>
        <span className="m">
          <b>{s.used_gb} GB</b>
          {s.limit_gb ? ` of ${s.limit_gb} GB` : " · no limit"}
        </span>
      </div>
      {s.limit_bytes ? (
        <div
          className="zset-storage-track"
          role="meter"
          aria-label="Storage used"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(pct)}
        >
          <span style={{ width: `${Math.max(pct, 1.5)}%` }} />
        </div>
      ) : null}
      {s.over ? (
        <p className="zset-storage-note">Full: uploads are paused. Renders still work.</p>
      ) : s.near ? (
        <p className="zset-storage-note">Almost full.</p>
      ) : null}
      {s.trash_count ? (
        <Link className="zset-storage-trash" href="/studio/assets#trash">
          {s.trash_count} in the Trash, not counted · emptied after {s.trash_days} days
        </Link>
      ) : null}
    </div>
  );
}
