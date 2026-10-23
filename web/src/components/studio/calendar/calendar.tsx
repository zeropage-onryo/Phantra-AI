"use client";

/* The calendar (2026-10-22, docs/tasks/task-calendar.md): what goes out,
   where and when. A reader over GET /api/posts with three writes -- move
   (PUT /date), state (POST /state) and the drawer's create / patch -- and
   NOTHING on it spends credits.

   Four views over the same rows. WEEK: seven columns, an hour a row, a
   card is the render's poster + the platform's mark + the words + its
   state; drag a card to another hour and it moves (Undo puts it back);
   the dashed boxes are an account's posting times with nothing in them.
   MONTH: chips per day. LIST: by day, with Upcoming / Needs you / Sent /
   Drafts. FEED (Later's visual planner): one account's grid as it will
   look once the queue lands, over the account's real recent posts.

   The strip beside the week is the Library's unposted renders (Buffer's
   ideas column): drag one onto a day and the drawer opens on that render
   at that hour. "New post", a free slot, a card and a drop all open the
   same drawer (post-drawer.tsx).

   Keyboard (Cron): T today, ←/→ a week or month, W M L F the views, N a
   new post, ? the list. No key sends anything. */
/* eslint-disable @next/next/no-img-element */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Keyboard, Plus, X } from "lucide-react";
import { ApiError } from "@/lib/api";
import {
  freeSlots,
  getFeed,
  getMedia,
  getSocialConnections,
  listPosts,
  movePost,
  setPostState,
  type Feed,
  type FreeSlot,
  type MediaItem,
  type Post,
  type SocialConnection,
} from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { UrlParams } from "@/components/studio/url-params";
import { PlatformIcon, StateGlyph, stateWord } from "./marks";
import { PostDrawer, type DrawerOpen } from "./post-drawer";
import {
  DAY_MS,
  addDays,
  addMonths,
  atHour,
  dayKey,
  fmtDay,
  fmtHour,
  fmtMonth,
  fmtTime,
  fmtWeekRange,
  fmtWhen,
  sameDay,
  snapHour,
  startOfDay,
  startOfWeek,
  whenOf,
} from "./time";
import "./calendar.css";

type View = "week" | "month" | "list" | "feed";
const VIEWS: { id: View; label: string; key: string }[] = [
  { id: "week", label: "Week", key: "W" },
  { id: "month", label: "Month", key: "M" },
  { id: "list", label: "List", key: "L" },
  { id: "feed", label: "Feed", key: "F" },
];
const HOUR_PX = 52;
const FIRST_HOUR_SHOWN = 7;
/** the platforms whose own feed the Feed view can draw */
const FEED_PROVIDERS = new Set(["instagram", "tiktok", "youtube", "x"]);
const DRAG_POST = "text/x-phantra-post";
const DRAG_SOURCE = "text/x-phantra-source";

const isReady = (c: SocialConnection) => c.status !== "pending";
const liveState = (p: Post) => p.state !== "cancelled";

/** the poster a card draws: the Library's thumbnail for the render when
 *  the wall is loaded, else the still itself, else nothing (a video's
 *  file is never drawn as an <img>) */
function posterOf(post: Post, wall: Map<number, MediaItem>): string | null {
  const m = post.source_ref.match(/^gen:(\d+)$/);
  const item = m ? wall.get(Number(m[1])) : undefined;
  if (item) return item.poster || item.thumb || (item.kind === "image" ? item.url : null);
  return post.media.kind === "image" ? post.media.media_url || null : null;
}

function titleOf(post: Post, wall: Map<number, MediaItem>) {
  const m = post.source_ref.match(/^gen:(\d+)$/);
  const item = m ? wall.get(Number(m[1])) : undefined;
  if (item?.prompt) return item.prompt.length > 48 ? `${item.prompt.slice(0, 47)}…` : item.prompt;
  return post.caption ? (post.caption.length > 48 ? `${post.caption.slice(0, 47)}…` : post.caption) : post.source_ref;
}

export function Calendar() {
  const { me, toast } = useShell();
  const [view, setView] = useState<View>("week");
  const [at, setAt] = useState<Date>(() => startOfDay(new Date()));
  const [connections, setConnections] = useState<SocialConnection[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [slots, setSlots] = useState<FreeSlot[]>([]);
  const [wall, setWall] = useState<MediaItem[]>([]);
  const [hidden, setHidden] = useState<Set<number>>(() => new Set());
  const [drawer, setDrawer] = useState<DrawerOpen | null>(null);
  const [stripOpen, setStripOpen] = useState(true);
  const [keysOpen, setKeysOpen] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [clock, setClock] = useState(() => new Date());
  const [feedFor, setFeedFor] = useState<number | null>(null);
  const [feed, setFeed] = useState<Feed | null>(null);
  const urlDone = useRef(false);

  // the range the current view reads
  const range = useMemo(() => {
    if (view === "week") {
      const start = startOfWeek(at);
      return { start, end: addDays(start, 7) };
    }
    if (view === "month") {
      const first = new Date(at.getFullYear(), at.getMonth(), 1);
      const start = startOfWeek(first);
      return { start, end: addDays(start, 42) };
    }
    const start = addDays(startOfDay(new Date()), -14);
    return { start, end: addDays(start, 90) };
  }, [view, at]);

  const wallById = useMemo(() => {
    const m = new Map<number, MediaItem>();
    for (const item of wall) if (item.generated_id) m.set(item.generated_id, item);
    return m;
  }, [wall]);

  const reload = useCallback(() => {
    if (!me) return;
    listPosts({ start: range.start.toISOString(), end: range.end.toISOString() })
      .then((r) => {
        setPosts(r.posts);
        setClock(new Date());
        setProblem(null);
      })
      .catch((err) => setProblem(err instanceof ApiError ? err.message : "Could not read the calendar"));
    if (view === "week") {
      freeSlots(range.start.toISOString(), range.end.toISOString())
        .then((r) => setSlots(r.slots))
        .catch(() => setSlots([]));
    }
  }, [me, range, view]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!me) return;
    getSocialConnections()
      .then((r) => {
        const ready = r.connections.filter(isReady);
        setConnections(ready);
        setFeedFor((cur) => cur ?? ready.find((c) => FEED_PROVIDERS.has(c.provider))?.id ?? null);
      })
      .catch(() => setConnections([]));
    getMedia({})
      .then((r) => setWall(r.items))
      .catch(() => setWall([]));
  }, [me]);

  // the feed: one account at a time, read when the view is open
  useEffect(() => {
    if (view !== "feed" || !feedFor || !me) return;
    let gone = false;
    getFeed(feedFor)
      .then((f) => !gone && setFeed(f))
      .catch((err) => !gone && setProblem(err instanceof ApiError ? err.message : "Could not read the feed"));
    return () => {
      gone = true;
    };
  }, [view, feedFor, me, posts]);

  // the deep link: ?view=&at=&open=
  const onParams = useCallback((params: URLSearchParams) => {
    const v = params.get("view") as View | null;
    if (v && VIEWS.some((x) => x.id === v)) setView(v);
    const day = params.get("at");
    if (day && /^\d{4}-\d{2}-\d{2}$/.test(day)) setAt(startOfDay(new Date(`${day}T00:00:00`)));
    const open = params.get("open");
    if (open && /^\d+$/.test(open)) setDrawer({ mode: "open", id: Number(open) });
    urlDone.current = true;
  }, []);
  useEffect(() => {
    if (!urlDone.current) return;
    const q = new URLSearchParams();
    if (view !== "week") q.set("view", view);
    if (!sameDay(at, clock)) q.set("at", dayKey(at));
    if (drawer?.mode === "open") q.set("open", String(drawer.id));
    const qs = q.toString();
    window.history.replaceState(null, "", `/studio/calendar${qs ? `?${qs}` : ""}`);
  }, [view, at, drawer, clock]);

  const step = useCallback(
    (n: number) => setAt((d) => (view === "month" ? addMonths(d, n) : addDays(d, 7 * n))),
    [view],
  );

  // keyboard (Cron): nothing here sends
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target as HTMLElement | null)?.isContentEditable) return;
      if (drawer) {
        if (e.key === "Escape") setDrawer(null);
        return;
      }
      const k = e.key.toLowerCase();
      if (k === "t") setAt(startOfDay(new Date()));
      else if (e.key === "ArrowLeft") step(-1);
      else if (e.key === "ArrowRight") step(1);
      else if (k === "w") setView("week");
      else if (k === "m") setView("month");
      else if (k === "l") setView("list");
      else if (k === "f") setView("feed");
      else if (k === "n") setDrawer({ mode: "new" });
      else if (e.key === "?") setKeysOpen((o) => !o);
      else if (e.key === "Escape") setKeysOpen(false);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer, step]);

  const shown = useMemo(() => posts.filter((p) => liveState(p) && !hidden.has(p.connection_id)), [posts, hidden]);

  /** move a post; the toast's Undo moves it back */
  const move = useCallback(
    (post: Post, to: Date) => {
      const from = post.publish_at;
      setPosts((cur) => cur.map((p) => (p.id === post.id ? { ...p, publish_at: to.toISOString() } : p)));
      movePost(post.id, to.toISOString())
        .then((moved) => {
          setPosts((cur) => cur.map((p) => (p.id === moved.id ? moved : p)));
          toast(`Moved to ${fmtWhen(to)}`, "ok", {
            action: {
              label: "Undo",
              run: () => movePost(post.id, from).then((back) => setPosts((cur) => cur.map((p) => (p.id === back.id ? back : p)))),
            },
          });
          reload();
        })
        .catch((err) => {
          setPosts((cur) => cur.map((p) => (p.id === post.id ? post : p)));
          toast(err instanceof ApiError ? err.message : "Could not move the post", "err");
        });
    },
    [reload, toast],
  );

  const postAgain = useCallback(
    (post: Post) => {
      setPostState(post.id, "queued")
        .then(() => {
          toast("Queued again; it goes on the next tick", "ok");
          reload();
        })
        .catch((err) => toast(err instanceof ApiError ? err.message : "Could not queue the post", "err"));
    },
    [reload, toast],
  );

  /** the renders nobody has posted yet (the strip) */
  const unposted = useMemo(() => {
    const used = new Set(posts.filter(liveState).map((p) => p.source_ref));
    return wall.filter((i) => i.generated_id && !used.has(`gen:${i.generated_id}`)).slice(0, 12);
  }, [wall, posts]);

  const title = view === "month" ? fmtMonth(at) : view === "week" ? fmtWeekRange(startOfWeek(at)) : view === "list" ? "Next 90 days" : "";
  const needsYou = posts.filter((p) => p.state === "error").length;

  return (
    <section className="view cal" style={{ paddingTop: 0 }}>
      <UrlParams onParams={onParams} />
      <div className="vhead" style={{ marginTop: 8 }}>
        <div>
          <h2>Calendar</h2>
          <p className="m" style={{ margin: "2px 0 0" }}>
            What goes out, where and when. Nothing on this page spends credits.
          </p>
        </div>
        <span className="spacer" />
        <button type="button" className="cal-primary" onClick={() => setDrawer({ mode: "new" })}>
          <Plus strokeWidth={2.2} /> New post <kbd>N</kbd>
        </button>
      </div>

      <div className="cal-bar">
        <div className="cal-seg" role="group" aria-label="View">
          {VIEWS.map((v) => (
            <button key={v.id} type="button" aria-pressed={view === v.id} onClick={() => setView(v.id)} title={`${v.label} (${v.key})`}>
              {v.label}
            </button>
          ))}
        </div>
        {view !== "feed" && view !== "list" ? (
          <>
            <button type="button" className="cal-ib" aria-label={view === "month" ? "Previous month" : "Previous week"} onClick={() => step(-1)}>
              <ChevronLeft strokeWidth={2} />
            </button>
            <button type="button" className="cal-btn" onClick={() => setAt(startOfDay(new Date()))}>
              Today
            </button>
            <button type="button" className="cal-ib" aria-label={view === "month" ? "Next month" : "Next week"} onClick={() => step(1)}>
              <ChevronRight strokeWidth={2} />
            </button>
          </>
        ) : null}
        <span className="cal-range">{title}</span>
        <span className="spacer" />
        {view === "feed" ? null : (
          <div className="cal-chips" role="group" aria-label="Accounts shown">
            {connections.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`cal-chip${hidden.has(c.id) ? " off" : ""}`}
                aria-pressed={!hidden.has(c.id)}
                onClick={() =>
                  setHidden((h) => {
                    const n = new Set(h);
                    if (n.has(c.id)) n.delete(c.id);
                    else n.add(c.id);
                    return n;
                  })
                }
                title={hidden.has(c.id) ? "Show this account" : "Hide this account"}
              >
                <PlatformIcon provider={c.provider} size={13} />
                {c.label || c.display_name}
              </button>
            ))}
            <Link href="/studio/settings/connections" className="cal-chip add">
              + Connect an account
            </Link>
          </div>
        )}
      </div>

      {problem ? <p className="stateline err">{problem}</p> : null}
      {!connections.length && me ? (
        <p className="stateline">
          No account connected yet. <Link href="/studio/settings/connections">Connect one</Link> and the calendar fills from the Library&apos;s
          Post… button or from here.
        </p>
      ) : null}
      {needsYou && view !== "list" ? (
        <button type="button" className="cal-needs" onClick={() => setView("list")}>
          <StateGlyph state="error" /> {needsYou === 1 ? "One post" : `${needsYou} posts`} did not go out. See the list.
        </button>
      ) : null}

      {view === "week" ? (
        <div className="cal-weekwrap">
          {stripOpen ? (
            <LibraryStrip items={unposted} onHide={() => setStripOpen(false)} />
          ) : (
            <button type="button" className="cal-stripopen" onClick={() => setStripOpen(true)} title="Show unposted renders">
              Library
            </button>
          )}
          <WeekView
            monday={startOfWeek(at)}
            posts={shown}
            slots={slots.filter((s) => !hidden.has(s.connection_id))}
            wall={wallById}
            clock={clock}
            onOpen={(id) => setDrawer({ mode: "open", id })}
            onMove={move}
            onDropSource={(source, when, meta) => setDrawer({ mode: "new", source, at: when, ...meta })}
            onSlot={(slot, when) => setDrawer({ mode: "new", at: when, connection_id: slot.connection_id })}
          />
        </div>
      ) : null}
      {view === "month" ? (
        <MonthView
          month={at}
          start={range.start}
          posts={shown}
          clock={clock}
          onOpen={(id) => setDrawer({ mode: "open", id })}
          onDay={(d) => {
            setAt(d);
            setView("week");
          }}
        />
      ) : null}
      {view === "list" ? <ListView posts={posts.filter((p) => !hidden.has(p.connection_id))} wall={wallById} clock={clock} onOpen={(id) => setDrawer({ mode: "open", id })} onPostAgain={postAgain} onMove={move} /> : null}
      {view === "feed" ? (
        <FeedView
          connections={connections.filter((c) => FEED_PROVIDERS.has(c.provider))}
          others={connections.filter((c) => !FEED_PROVIDERS.has(c.provider))}
          picked={feedFor}
          onPick={setFeedFor}
          feed={feed}
          busy={feedFor !== null && feed?.connection.id !== feedFor}
          wall={wallById}
          onOpen={(id) => setDrawer({ mode: "open", id })}
          onSwap={(a, b) => {
            // two moves, one Undo
            const whenA = a.publish_at;
            const whenB = b.publish_at;
            if (!whenA || !whenB) return;
            Promise.all([movePost(a.id, whenB), movePost(b.id, whenA)])
              .then(() => {
                toast("Swapped the two dates", "ok", {
                  action: { label: "Undo", run: () => Promise.all([movePost(a.id, whenA), movePost(b.id, whenB)]).then(reload) },
                });
                reload();
              })
              .catch((err) => toast(err instanceof ApiError ? err.message : "Could not swap them", "err"));
          }}
        />
      ) : null}

      <div className="cal-legend">
        {(["queued", "publishing", "published", "error", "draft"] as const).map((s) => (
          <span key={s}>
            <StateGlyph state={s} /> {stateWord(s)}
          </span>
        ))}
        <span className="spacer" />
        {view === "week" ? <span>Dashed boxes are posting times with nothing in them yet. Drag a card to move it; a sent post stays where it landed.</span> : null}
        <button type="button" className="cal-keys" onClick={() => setKeysOpen((o) => !o)} aria-expanded={keysOpen}>
          <Keyboard strokeWidth={1.8} /> <kbd>?</kbd>
        </button>
      </div>
      {keysOpen ? (
        <div className="cal-keysheet" role="dialog" aria-label="Keyboard shortcuts">
          <div className="cal-keysheet-head">
            <b>Keyboard</b>
            <button type="button" className="cal-ib" aria-label="Close" onClick={() => setKeysOpen(false)}>
              <X strokeWidth={2} />
            </button>
          </div>
          <dl>
            <dt><kbd>T</kbd></dt><dd>today</dd>
            <dt><kbd>←</kbd> <kbd>→</kbd></dt><dd>a week, or a month</dd>
            <dt><kbd>W</kbd> <kbd>M</kbd> <kbd>L</kbd> <kbd>F</kbd></dt><dd>week, month, list, feed</dd>
            <dt><kbd>N</kbd></dt><dd>new post</dd>
            <dt><kbd>Esc</kbd></dt><dd>close the drawer</dd>
          </dl>
          <p className="cal-hint">No key sends anything.</p>
        </div>
      ) : null}

      {drawer ? (
        <PostDrawer
          open={drawer}
          connections={connections}
          wall={wallById}
          siblings={drawer.mode === "open" ? posts.filter((p) => p.id !== drawer.id && p.group_id === posts.find((x) => x.id === drawer.id)?.group_id) : []}
          onClose={() => setDrawer(null)}
          onChanged={reload}
          toast={toast}
        />
      ) : null}
    </section>
  );
}

/* ── the Library strip ──────────────────────────────────────────────── */

function LibraryStrip({ items, onHide }: { items: MediaItem[]; onHide: () => void }) {
  return (
    <aside className="cal-lib" aria-label="Unposted renders">
      <div className="cal-lib-head">
        <span>From the Library</span>
        <button type="button" className="cal-ib sm" aria-label="Hide the strip" onClick={onHide}>
          <ChevronLeft strokeWidth={2} />
        </button>
      </div>
      <p className="cal-hint">Renders nobody has posted yet. Drag one onto a day.</p>
      {!items.length ? <p className="cal-hint">Everything on the wall is posted or queued.</p> : null}
      {items.map((i) => {
        const poster = i.poster || i.thumb || (i.kind === "image" ? i.url : null);
        const title = i.prompt ? (i.prompt.length > 40 ? `${i.prompt.slice(0, 39)}…` : i.prompt) : i.asset_name;
        return (
          <div
            key={i.asset_id}
            className="cal-lib-tile"
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(DRAG_SOURCE, JSON.stringify({ source: `gen:${i.generated_id}`, poster, title, kind: i.kind }));
              e.dataTransfer.effectAllowed = "copy";
            }}
            title="Drag onto a day"
          >
            <div className="cal-lib-po">
              {poster ? <img src={poster} alt="" /> : null}
              <span>{i.kind === "video" ? "clip" : "still"}</span>
            </div>
            <b>{title}</b>
            <small>{i.model_label || i.provider || ""}</small>
          </div>
        );
      })}
      <Link href="/studio/assets" className="cal-lib-more">
        All renders
      </Link>
    </aside>
  );
}

/* ── week ──────────────────────────────────────────────────────────── */

/** Posts that sit on each other in a column share its width: cards whose
 *  tops are closer than a card's height form a cluster, and each takes a
 *  lane. Two accounts at 9:00 are two half-width cards side by side. */
const CARD_PX = 64;
function lanes(posts: Post[]): { post: Post; lane: number; lanesInCluster: number }[] {
  const sorted = [...posts].sort((a, b) => (a.publish_at ?? "").localeCompare(b.publish_at ?? "") || a.id - b.id);
  const out: { post: Post; lane: number; lanesInCluster: number }[] = [];
  let cluster: { post: Post; lane: number; top: number }[] = [];
  const flush = () => {
    const n = Math.max(1, ...cluster.map((c) => c.lane + 1));
    for (const c of cluster) out.push({ post: c.post, lane: c.lane, lanesInCluster: n });
    cluster = [];
  };
  for (const p of sorted) {
    const t = whenOf(p.publish_at);
    const top = (t.getHours() + t.getMinutes() / 60) * HOUR_PX;
    const clusterEnd = cluster.length ? Math.max(...cluster.map((c) => c.top + CARD_PX)) : -1;
    if (cluster.length && top >= clusterEnd) flush();
    const taken = new Set(cluster.filter((c) => top < c.top + CARD_PX).map((c) => c.lane));
    let lane = 0;
    while (taken.has(lane)) lane += 1;
    cluster.push({ post: p, lane, top });
  }
  flush();
  return out;
}

type WeekProps = {
  monday: Date;
  posts: Post[];
  slots: FreeSlot[];
  wall: Map<number, MediaItem>;
  clock: Date;
  onOpen: (id: number) => void;
  onMove: (post: Post, to: Date) => void;
  onDropSource: (source: string, when: Date, meta: { poster?: string | null; title?: string; kind?: string }) => void;
  onSlot: (slot: FreeSlot, when: Date) => void;
};

function WeekView({ monday, posts, slots, wall, clock, onOpen, onMove, onDropSource, onSlot }: WeekProps) {
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(monday, i)), [monday]);
  const now = clock;
  const scroller = useRef<HTMLDivElement | null>(null);
  const [ghost, setGhost] = useState<{ day: number; hour: number } | null>(null);
  useEffect(() => {
    scroller.current?.scrollTo({ top: FIRST_HOUR_SHOWN * HOUR_PX });
  }, [monday]);

  const byDay = useMemo(() => {
    const m = new Map<string, Post[]>();
    for (const p of posts) {
      const k = dayKey(whenOf(p.publish_at));
      m.set(k, [...(m.get(k) ?? []), p]);
    }
    return m;
  }, [posts]);
  const slotsByDay = useMemo(() => {
    const m = new Map<string, FreeSlot[]>();
    for (const s of slots) {
      const k = dayKey(new Date(s.publish_at));
      m.set(k, [...(m.get(k) ?? []), s]);
    }
    return m;
  }, [slots]);

  const hourAt = (e: React.DragEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    return snapHour(e.clientY - rect.top, HOUR_PX);
  };

  return (
    <div className="cal-week">
      <div className="cal-week-head">
        <div />
        {days.map((d) => (
          <div key={d.toISOString()} className={`cal-dh${sameDay(d, now) ? " today" : ""}`}>
            <small>{d.toLocaleDateString(undefined, { weekday: "short" }).toUpperCase()}</small>
            <b>{d.getDate()}</b>
          </div>
        ))}
      </div>
      <div className="cal-week-body" ref={scroller}>
        <div className="cal-hours" aria-hidden="true">
          {Array.from({ length: 24 }, (_, h) => (
            <span key={h} style={{ top: h * HOUR_PX }}>
              {fmtHour(h)}
            </span>
          ))}
        </div>
        {days.map((d, di) => {
          const past = d.getTime() + DAY_MS <= now.getTime();
          const today = sameDay(d, now);
          const key = dayKey(d);
          return (
            <div
              key={key}
              className={`cal-day${past ? " past" : ""}${today ? " today" : ""}${ghost?.day === di ? " over" : ""}`}
              style={{ height: 24 * HOUR_PX }}
              onDragOver={(e) => {
                if (!e.dataTransfer.types.includes(DRAG_POST) && !e.dataTransfer.types.includes(DRAG_SOURCE)) return;
                e.preventDefault();
                setGhost({ day: di, hour: hourAt(e) });
              }}
              onDragLeave={() => setGhost((g) => (g?.day === di ? null : g))}
              onDrop={(e) => {
                e.preventDefault();
                const when = atHour(d, hourAt(e));
                setGhost(null);
                const pid = e.dataTransfer.getData(DRAG_POST);
                if (pid) {
                  const post = posts.find((p) => p.id === Number(pid));
                  if (post) onMove(post, when);
                  return;
                }
                const raw = e.dataTransfer.getData(DRAG_SOURCE);
                if (raw) {
                  try {
                    const data = JSON.parse(raw) as { source: string; poster?: string | null; title?: string; kind?: string };
                    onDropSource(data.source, when, { poster: data.poster, title: data.title, kind: data.kind });
                  } catch {
                    /* not ours */
                  }
                }
              }}
            >
              {Array.from({ length: 23 }, (_, h) => (
                <i key={h} className="cal-line" style={{ top: (h + 1) * HOUR_PX }} />
              ))}
              {today ? (
                <div className="cal-now" style={{ top: (now.getHours() + now.getMinutes() / 60) * HOUR_PX }}>
                  <i />
                </div>
              ) : null}
              {(slotsByDay.get(key) ?? []).map((s) => {
                const t = new Date(s.publish_at);
                const hour = t.getHours() + t.getMinutes() / 60;
                return (
                  <button
                    key={`${s.connection_id}-${s.publish_at}`}
                    type="button"
                    className="cal-slot"
                    style={{ top: hour * HOUR_PX + 2 }}
                    onClick={() => onSlot(s, t)}
                    title={`${s.label}: a posting time with nothing in it`}
                  >
                    <PlatformIcon provider={s.provider} size={11} mono /> <b>{fmtTime(t)}</b> free slot
                  </button>
                );
              })}
              {lanes(byDay.get(key) ?? []).map(({ post: p, lane, lanesInCluster }) => {
                const t = whenOf(p.publish_at);
                const hour = t.getHours() + t.getMinutes() / 60;
                const poster = posterOf(p, wall);
                const movable = p.state !== "published" && p.state !== "publishing";
                const width = 100 / lanesInCluster;
                return (
                  <article
                    key={p.id}
                    className={`cal-post ${p.state}${lanesInCluster > 1 ? " narrow" : ""}`}
                    style={{ top: hour * HOUR_PX + 2, left: `calc(${lane * width}% + 4px)`, right: "auto", width: `calc(${width}% - 8px)` }}
                    draggable={movable}
                    onDragStart={(e) => {
                      e.dataTransfer.setData(DRAG_POST, String(p.id));
                      e.dataTransfer.effectAllowed = "move";
                    }}
                    onClick={() => onOpen(p.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onOpen(p.id);
                    }}
                    tabIndex={0}
                    role="button"
                    aria-label={`${titleOf(p, wall)}, ${p.provider_name}, ${fmtTime(t)}, ${stateWord(p.state)}`}
                  >
                    <div className="cal-thumb">{poster ? <img src={poster} alt="" /> : null}</div>
                    <div className="cal-meta">
                      <b>{titleOf(p, wall)}</b>
                      <span className="cal-st">
                        <PlatformIcon provider={p.provider} size={12} /> {fmtTime(t)}
                      </span>
                      <span className={`cal-st ${p.state}`}>
                        <StateGlyph state={p.state} /> {p.state === "error" ? "Refused · open" : stateWord(p.state)}
                      </span>
                    </div>
                  </article>
                );
              })}
              {ghost?.day === di ? (
                <div className="cal-ghost" style={{ top: ghost.hour * HOUR_PX + 2 }}>
                  {fmtTime(atHour(d, ghost.hour))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── month ─────────────────────────────────────────────────────────── */

function MonthView({ month, start, posts, clock, onOpen, onDay }: { month: Date; start: Date; posts: Post[]; clock: Date; onOpen: (id: number) => void; onDay: (d: Date) => void }) {
  const now = clock;
  const days = useMemo(() => Array.from({ length: 42 }, (_, i) => addDays(start, i)), [start]);
  const byDay = useMemo(() => {
    const m = new Map<string, Post[]>();
    for (const p of posts) {
      const k = dayKey(whenOf(p.publish_at));
      m.set(k, [...(m.get(k) ?? []), p]);
    }
    return m;
  }, [posts]);
  return (
    <div className="cal-month">
      {["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"].map((d) => (
        <div key={d} className="cal-mdh">
          {d}
        </div>
      ))}
      {days.map((d) => {
        const key = dayKey(d);
        const rows = (byDay.get(key) ?? []).sort((a, b) => (a.publish_at ?? "").localeCompare(b.publish_at ?? ""));
        const out = d.getMonth() !== month.getMonth();
        const past = d.getTime() + DAY_MS <= now.getTime();
        return (
          <div key={key} className={`cal-mc${out ? " out" : ""}${past ? " past" : ""}${sameDay(d, now) ? " today" : ""}`}>
            <button type="button" className="cal-mn" onClick={() => onDay(d)} title="Open this week">
              {d.getDate()}
            </button>
            {rows.slice(0, 3).map((p) => (
              <button key={p.id} type="button" className={`cal-mp ${p.state}`} onClick={() => onOpen(p.id)}>
                <PlatformIcon provider={p.provider} size={11} />
                {p.state !== "queued" ? <StateGlyph state={p.state} size={9} /> : null}
                <span>{p.caption || p.source_ref}</span>
              </button>
            ))}
            {rows.length > 3 ? (
              <button type="button" className="cal-more" onClick={() => onDay(d)}>
                +{rows.length - 3} more
              </button>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/* ── list ──────────────────────────────────────────────────────────── */

type Filter = "upcoming" | "needs" | "sent" | "drafts";

function ListView({ posts, wall, clock, onOpen, onPostAgain, onMove }: { posts: Post[]; wall: Map<number, MediaItem>; clock: Date; onOpen: (id: number) => void; onPostAgain: (p: Post) => void; onMove: (p: Post, to: Date) => void }) {
  const [filter, setFilter] = useState<Filter>("upcoming");
  const now = clock.getTime();
  const needs = posts.filter((p) => p.state === "error").length;
  const rows = posts
    .filter((p) => {
      if (filter === "needs") return p.state === "error";
      if (filter === "sent") return p.state === "published";
      if (filter === "drafts") return p.state === "draft";
      return (p.state === "queued" || p.state === "publishing" || p.state === "error") && whenOf(p.publish_at).getTime() >= now - 6 * 3600 * 1000;
    })
    .sort((a, b) => (filter === "sent" ? (b.publish_at ?? "").localeCompare(a.publish_at ?? "") : (a.publish_at ?? "").localeCompare(b.publish_at ?? "")));
  const groups: { key: string; label: string; rows: Post[] }[] = [];
  for (const p of rows) {
    const d = whenOf(p.publish_at);
    const key = dayKey(d);
    const last = groups[groups.length - 1];
    const today = sameDay(d, clock);
    const tomorrow = sameDay(d, addDays(clock, 1));
    const label = `${today ? "TODAY · " : tomorrow ? "TOMORROW · " : ""}${fmtDay(d).toUpperCase()}`;
    if (last && last.key === key) last.rows.push(p);
    else groups.push({ key, label, rows: [p] });
  }
  return (
    <div className="cal-listwrap">
      <div className="cal-seg" role="group" aria-label="Show">
        {(
          [
            ["upcoming", "Upcoming"],
            ["needs", needs ? `Needs you · ${needs}` : "Needs you"],
            ["sent", "Sent"],
            ["drafts", "Drafts"],
          ] as [Filter, string][]
        ).map(([id, label]) => (
          <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="cal-list">
        {!groups.length ? <p className="stateline" style={{ padding: 12 }}>Nothing here.</p> : null}
        {groups.map((g) => (
          <div key={g.key}>
            <div className={`cal-lg${g.label.startsWith("TODAY") ? " today" : ""}`}>{g.label}</div>
            {g.rows.map((p) => {
              const t = whenOf(p.publish_at);
              const poster = posterOf(p, wall);
              return (
                <div key={p.id} className={`cal-lr ${p.state}`}>
                  <span className="cal-tm">{fmtTime(t)}</span>
                  <div className="cal-thumb sm">{poster ? <img src={poster} alt="" /> : null}</div>
                  <div className="cal-nm">
                    <b>{titleOf(p, wall)}</b>
                    <small>{p.state === "error" ? p.error || "The platform refused it." : p.caption || "No words yet."}</small>
                  </div>
                  <span className="cal-to">
                    <PlatformIcon provider={p.provider} size={13} /> {p.provider_name}
                  </span>
                  <span className={`cal-st ${p.state}`}>
                    <StateGlyph state={p.state} /> {stateWord(p.state)}
                    {p.release_url ? (
                      <>
                        {" · "}
                        <a href={p.release_url} target="_blank" rel="noreferrer">
                          open
                        </a>
                      </>
                    ) : null}
                  </span>
                  <div className="cal-acts">
                    {p.state === "error" ? (
                      <button type="button" className="cal-primary sm" onClick={() => onPostAgain(p)}>
                        Post again
                      </button>
                    ) : null}
                    {p.state === "queued" || p.state === "draft" || p.state === "error" ? (
                      <button type="button" className="cal-btn sm" onClick={() => onMove(p, addDays(t, 1))} title="Move it a day later">
                        +1 day
                      </button>
                    ) : null}
                    <button type="button" className="cal-btn sm" onClick={() => onOpen(p.id)}>
                      Open
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── feed ──────────────────────────────────────────────────────────── */

type FeedProps = {
  connections: SocialConnection[];
  others: SocialConnection[];
  picked: number | null;
  onPick: (id: number) => void;
  feed: Feed | null;
  busy: boolean;
  wall: Map<number, MediaItem>;
  onOpen: (id: number) => void;
  onSwap: (a: Post, b: Post) => void;
};

function FeedView({ connections, others, picked, onPick, feed, busy, wall, onOpen, onSwap }: FeedProps) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  if (!connections.length) {
    return (
      <p className="stateline">
        The feed shows one account&apos;s grid as it will look.{" "}
        {others.length ? `${others.map((c) => c.provider_name).join(" and ")} ${others.length === 1 ? "has" : "have"} no feed; connect` : "Connect"} an
        Instagram, TikTok, YouTube or X account <Link href="/studio/settings/connections">in Settings</Link>.
      </p>
    );
  }
  const conn = connections.find((c) => c.id === picked) ?? connections[0];
  const ours = (feed?.posts ?? []).filter((p) => p.state !== "cancelled");
  const upcoming = ours.filter((p) => p.state !== "published");
  const sent = ours.filter((p) => p.state === "published");
  const movable = (p: Post) => p.state === "queued" || p.state === "draft" || p.state === "error";
  return (
    <div className="cal-feedwrap">
      <div className="cal-bar" style={{ marginBottom: 12 }}>
        <span className="m">One account at a time:</span>
        <div className="cal-acc" role="group" aria-label="Account">
          {connections.map((c) => (
            <button key={c.id} type="button" aria-pressed={c.id === conn.id} onClick={() => onPick(c.id)} aria-label={`${c.provider_name} ${c.label}`} title={c.label}>
              <PlatformIcon provider={c.provider} size={16} />
            </button>
          ))}
        </div>
        <span className="spacer" />
        {others.length ? <span className="m">{others.map((c) => c.provider_name).join(", ")}: no feed, not offered here</span> : null}
      </div>
      <div className="cal-feed">
        <div className="cal-phone" aria-label={`${conn.provider_name} grid, ${conn.label}`}>
          <div className="cal-ph">
            <span className="cal-pav">{conn.avatar_url ? <img src={conn.avatar_url} alt="" /> : <PlatformIcon provider={conn.provider} size={16} />}</span>
            <div>
              <b>{conn.label || conn.display_name}</b>
              <small>
                {upcoming.length} upcoming · {sent.length + (feed?.recent.length ?? 0)} posted
              </small>
            </div>
            <span className="spacer" />
            {busy ? <span className="m">reading…</span> : null}
          </div>
          <div className="cal-grid">
            {upcoming.map((p) => {
              const poster = posterOf(p, wall);
              const t = whenOf(p.publish_at);
              return (
                <div
                  key={`p${p.id}`}
                  className={`cal-tile ${p.state}${dragging === p.id ? " drag" : ""}${over === p.id ? " over" : ""}`}
                  draggable={movable(p)}
                  onDragStart={(e) => {
                    e.dataTransfer.setData(DRAG_POST, String(p.id));
                    setDragging(p.id);
                  }}
                  onDragEnd={() => {
                    setDragging(null);
                    setOver(null);
                  }}
                  onDragOver={(e) => {
                    if (dragging && dragging !== p.id && movable(p)) {
                      e.preventDefault();
                      setOver(p.id);
                    }
                  }}
                  onDragLeave={() => setOver((o) => (o === p.id ? null : o))}
                  onDrop={(e) => {
                    e.preventDefault();
                    const a = upcoming.find((x) => x.id === dragging);
                    if (a && a.id !== p.id) onSwap(a, p);
                    setDragging(null);
                    setOver(null);
                  }}
                  onClick={() => onOpen(p.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onOpen(p.id);
                  }}
                  title={movable(p) ? "Drag onto another tile to swap their dates" : undefined}
                >
                  {poster ? <img src={poster} alt="" /> : null}
                  <span className="cal-td">
                    <StateGlyph state={p.state} size={9} /> {fmtDay(t)}
                  </span>
                  <span className="cal-tn">{titleOf(p, wall)}</span>
                </div>
              );
            })}
            {sent.map((p) => {
              const poster = posterOf(p, wall);
              return (
                <a key={`s${p.id}`} className="cal-tile pub" href={p.release_url || undefined} target="_blank" rel="noreferrer">
                  {poster ? <img src={poster} alt="" /> : null}
                  <span className="cal-td">
                    <StateGlyph state="published" size={9} /> {fmtDay(whenOf(p.published_at || p.publish_at))}
                  </span>
                  <span className="cal-tn">{titleOf(p, wall)}</span>
                </a>
              );
            })}
            {(feed?.recent ?? []).map((m) => (
              <a key={`r${m.id}`} className="cal-tile pub" href={m.url || undefined} target="_blank" rel="noreferrer">
                {m.thumb ? <img src={m.thumb} alt="" /> : null}
                <span className="cal-td">{m.at ? fmtDay(new Date(m.at)) : ""}</span>
                {m.caption ? <span className="cal-tn">{m.caption}</span> : null}
              </a>
            ))}
            {!upcoming.length && !sent.length && !(feed?.recent.length ?? 0) && !busy ? (
              <p className="cal-hint" style={{ gridColumn: "1 / -1", padding: 12 }}>
                Nothing to draw yet{feed && !feed.offered ? " (this platform has no feed to read)" : ""}.
              </p>
            ) : null}
          </div>
        </div>
        <div className="cal-q">
          <h3>Queue · {conn.label || conn.display_name}</h3>
          <p className="cal-hint">
            Newest first, the way the grid reads. The platform&apos;s own posts are read once a day through your connection.
            {feed?.note ? ` Last read: ${feed.note}` : ""}
          </p>
          {[...upcoming, ...sent].map((p, i) => (
            <button key={p.id} type="button" className={`cal-qr ${p.state}`} onClick={() => onOpen(p.id)}>
              <span className="cal-qi">{i + 1}</span>
              <div className="cal-thumb sm">{posterOf(p, wall) ? <img src={posterOf(p, wall)!} alt="" /> : null}</div>
              <div className="cal-nm">
                <b>{titleOf(p, wall)}</b>
                <small>{p.state === "error" ? p.error : p.caption || "No words yet."}</small>
              </div>
              <span className={`cal-st ${p.state}`}>
                <StateGlyph state={p.state} /> {fmtWhen(whenOf(p.publish_at))}
              </span>
            </button>
          ))}
          <p className="cal-hint">A swap in the grid is two moves, undone with one toast. A published tile cannot move.</p>
        </div>
      </div>
    </div>
  );
}
