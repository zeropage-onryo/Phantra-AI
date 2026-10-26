"use client";

/* The Showcase list (2026-10-25, docs/tasks/task-whats-new.md step 2): the
   announcements the Create wall is waiting on, for the OWNERS of the house
   account only. The server decides who that is; anyone else gets a 404 from
   /api/whats-new/showcase and this draws nothing.

   A waiting row is a new model, effect, look, skill or feature the boot sync
   found. Its picture is ONE render on the house account: the button names
   its price and the click is the approval (409 if the price moved). The take
   lands here for Keep (live for everyone) or Redo (back to waiting; the take
   stays in the Library). An effect or a look has nothing to render on its
   own, so it takes a Library item by its gen:<id>; a words-only tile keeps
   straight away. Live and skipped rows fold away under one line. */
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { refreshJobs } from "@/lib/jobs";
import {
  showcaseActions,
  showcaseApprove,
  showcaseEdit,
  showcaseList,
  showcaseMove,
  showcasePick,
  type ShowcaseItem,
} from "@/lib/whats-new";

const WAITING = new Set(["pending", "rendering", "review"]);
const STATUS_WORDS: Record<string, string> = {
  pending: "waiting",
  rendering: "rendering…",
  review: "ready to keep",
  live: "live",
  skipped: "skipped",
};

/* eslint-disable @next/next/no-img-element */
function Take({ item }: { item: ShowcaseItem }) {
  if (!item.media_url) return <span className="block h-[72px] w-[128px] rounded-[4px] bg-noir-slate" aria-hidden />;
  return item.media_type === "video" ? (
    <video
      src={item.media_url}
      poster={item.poster_url ?? undefined}
      className="block h-[72px] w-[128px] rounded-[4px] object-cover"
      muted
      loop
      playsInline
      controls
    />
  ) : (
    <img src={item.media_url} alt="" className="block h-[72px] w-[128px] rounded-[4px] object-cover" />
  );
}

export function ShowcaseList({ toast }: { toast: (text: string, kind?: "ok" | "err") => void }) {
  const [items, setItems] = useState<ShowcaseItem[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showDone, setShowDone] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [picks, setPicks] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    showcaseList()
      .then((r) => setItems(r.items))
      .catch(() => setItems(null)); // 404: not the house account's owner -- draw nothing
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  // a render is a job: look again while one runs
  const rendering = !!items?.some((i) => i.status === "rendering");
  useEffect(() => {
    if (!rendering) return;
    const t = window.setInterval(load, 4000);
    return () => window.clearInterval(t);
  }, [rendering, load]);

  if (!items) return null;
  const waiting = items.filter((i) => WAITING.has(i.status));
  const done = items.filter((i) => !WAITING.has(i.status));

  const run = (id: string, p: Promise<unknown>, ok: string) => {
    setBusy(id);
    p.then(() => {
      toast(ok, "ok");
      load();
      refreshJobs();
    })
      .catch((err) => {
        toast(err instanceof ApiError ? err.message : "That didn't go through", "err");
        load();
      })
      .finally(() => setBusy(null));
  };

  const row = (item: ShowcaseItem) => {
    const acts = showcaseActions(item);
    const draft = drafts[item.id];
    return (
      <div
        key={item.id}
        className="qrow"
        style={{ alignItems: "flex-start", gridTemplateColumns: "128px minmax(0, 1fr) 96px minmax(0, max-content)" }}
      >
        <Take item={item} />
        <div className="qinfo">
          <div className="qn">
            <span className="m">{item.tag}</span> {item.title}
          </div>
          <div className="qm m">
            {item.line}
            {item.model ? ` · ${item.model}` : ""}
            {item.params.seconds ? ` · ${item.params.seconds}s` : ""}
            {item.params.resolution ? ` · ${item.params.resolution}` : ""}
          </div>
          {item.status === "pending" && (item.media_kind === "clip" || item.media_kind === "still") ? (
            <textarea
              className="mt-1 w-full rounded-[4px] border border-[var(--line)] bg-transparent p-2 text-[13px]"
              rows={2}
              value={draft ?? item.prompt}
              onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: e.target.value }))}
              aria-label="Showcase prompt"
            />
          ) : null}
          {item.note ? <div className="qm" style={{ color: "var(--danger)" }}>{item.note}</div> : null}
          {item.price_note ? <div className="qm m">{item.price_note}</div> : null}
          {acts.includes("pick") ? (
            <div className="mt-1 flex items-center gap-2">
              <input
                className="w-[120px] rounded-[4px] border border-[var(--line)] bg-transparent px-2 py-1 text-[12px]"
                placeholder="gen:123"
                value={picks[item.id] ?? ""}
                onChange={(e) => setPicks((p) => ({ ...p, [item.id]: e.target.value }))}
                aria-label="A Library item to use"
              />
              <button
                type="button"
                className="tag"
                disabled={busy === item.id || !(picks[item.id] ?? "").trim()}
                onClick={() => run(item.id, showcasePick(item.id, picks[item.id].trim()), "Picked; keep it to go live")}
              >
                Use this Library item
              </button>
            </div>
          ) : null}
        </div>
        <span className="m">{STATUS_WORDS[item.status] ?? item.status}</span>
        <span className="flex flex-col items-end gap-2 whitespace-nowrap">
          {draft !== undefined && draft !== item.prompt ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id}
              onClick={() =>
                run(
                  item.id,
                  showcaseEdit(item.id, { prompt: draft }).then(() =>
                    setDrafts((d) => {
                      const next = { ...d };
                      delete next[item.id];
                      return next;
                    }),
                  ),
                  "Prompt saved",
                )
              }
            >
              Save prompt
            </button>
          ) : null}
          {acts.includes("approve") && typeof item.credits === "number" ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id || (draft !== undefined && draft !== item.prompt)}
              title="Renders once on the house account; the take waits here for Keep"
              onClick={() => run(item.id, showcaseApprove(item.id, item.credits as number), "Rendering the showcase")}
            >
              {`Render · ${item.credits} credits`}
            </button>
          ) : null}
          {acts.includes("keep") ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id}
              onClick={() => run(item.id, showcaseMove(item.id, "keep"), "Live for everyone")}
            >
              Keep
            </button>
          ) : null}
          {acts.includes("redo") ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id}
              onClick={() => run(item.id, showcaseMove(item.id, "redo"), "Back to waiting; the take is in the Library")}
            >
              Redo
            </button>
          ) : null}
          {acts.includes("skip") ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id}
              onClick={() => run(item.id, showcaseMove(item.id, "skip"), "Skipped; it won't be shown")}
            >
              Skip
            </button>
          ) : null}
          {acts.includes("restore") ? (
            <button
              type="button"
              className="tag"
              disabled={busy === item.id}
              onClick={() => run(item.id, showcaseMove(item.id, "restore"), "Back to waiting")}
            >
              Restore
            </button>
          ) : null}
        </span>
      </div>
    );
  };

  return (
    <>
      <div className="chead">
        <h3>Showcase · {waiting.length}</h3>
        <span className="m">what the Create wall is waiting on · house account only</span>
        <span className="spacer" />
        {done.length ? (
          <button type="button" className="tag" onClick={() => setShowDone((v) => !v)}>
            {showDone ? "Hide live and skipped" : `Live and skipped · ${done.length}`}
          </button>
        ) : null}
      </div>
      <div className="qlist">
        {waiting.length ? (
          waiting.map(row)
        ) : (
          <p className="stateline" style={{ padding: 0 }}>
            Nothing waiting. A new model, effect, look or skill shows up here after the next deploy.
          </p>
        )}
        {showDone ? done.map(row) : null}
      </div>
    </>
  );
}
