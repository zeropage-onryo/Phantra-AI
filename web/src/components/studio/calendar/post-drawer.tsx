"use client";

/* The slot editor (2026-10-22, docs/tasks/task-calendar.md): the one
   drawer the calendar opens, on a card, a free slot, "New post" or a drop
   from the Library strip. The Library's Post… panel with three things
   added from the canvas:

   - accounts are picked by clicking their avatars (one clip to several
     accounts: one `posts` row each, one group, all-or-nothing on the
     server), with a words tab per account when one wants its own;
   - the preview is drawn in the platform's own shape (a story frame, a
     Discord message, a post on X), so what the platform will refuse is
     visible before it does;
   - When defaults to the account's next free posting time, with Now and
     Pick a time beside it; the send button is split, Post now under its
     caret. Post now still goes through the worker's next tick.

   Nothing here spends. An existing post's drawer edits its words, moves
   it, queues it again after a refusal, or cancels it. */
/* eslint-disable @next/next/no-img-element */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronDown, Send, X } from "lucide-react";
import { ApiError } from "@/lib/api";
import {
  createPostGroup,
  deletePost,
  getPost,
  getSocialProviders,
  movePost,
  nextFreeSlot,
  patchPost,
  setPostState,
  type MediaItem,
  type Post,
  type SocialConnection,
  type SocialProvider,
} from "@/lib/studio-api";
import type { ToastOpts } from "@/components/studio/shell";
import { PlatformIcon, StateGlyph, stateWord } from "./marks";
import { ProviderFields, missing, type Values } from "./provider-fields";
import { fmtWhen, toLocalInput, whenOf } from "./time";

export type DrawerOpen =
  | { mode: "open"; id: number }
  | { mode: "new"; source?: string; at?: Date; connection_id?: number; poster?: string | null; title?: string; kind?: string };

type Props = {
  open: DrawerOpen;
  connections: SocialConnection[];
  wall: Map<number, MediaItem>;
  siblings: Post[];
  onClose: () => void;
  onChanged: () => void;
  toast: (text: string, kind?: "ok" | "err", opts?: ToastOpts) => void;
};

/** the platforms' limits until the catalogue has answered */
const LIMITS: Record<string, number> = { discord: 2000, instagram: 2200, x: 280, tiktok: 2200, youtube: 5000, reddit: 300, linkedin: 3000 };

/** the catalogue, read once per drawer: each platform's own form and limit */
function useProviders() {
  const [providers, setProviders] = useState<Record<string, SocialProvider>>({});
  useEffect(() => {
    let gone = false;
    getSocialProviders()
      .then((r) => !gone && setProviders(Object.fromEntries(r.providers.map((p) => [p.id, p]))))
      .catch(() => {});
    return () => {
      gone = true;
    };
  }, []);
  return providers;
}

const posterOfItem = (i: MediaItem | undefined) => (i ? i.poster || i.thumb || (i.kind === "image" ? i.url : null) : null);

export function PostDrawer(props: Props) {
  return (
    <div className="cal-scrim" onClick={props.onClose} role="presentation">
      <aside className="cal-drawer" role="dialog" aria-label="Post" onClick={(e) => e.stopPropagation()}>
        {props.open.mode === "open" ? <Existing {...props} id={props.open.id} /> : <Fresh {...props} seed={props.open} />}
      </aside>
    </div>
  );
}

/* ── the preview, in the platform's shape ──────────────────────────── */

function Preview({ provider, poster, caption, handle, kind, postType }: { provider: string; poster: string | null; caption: string; handle: string; kind?: string; postType?: string }) {
  const words = caption.trim() || "Your words here";
  if (provider === "discord") {
    return (
      <div className="cal-pv discord" aria-label="Preview as a Discord message">
        <span className="cal-pv-av">
          <PlatformIcon provider="discord" size={14} />
        </span>
        <div>
          <b>Phantra</b> <small>bot · today</small>
          <p>{words}</p>
          <div className="cal-pv-att">{poster ? <img src={poster} alt="" /> : <span>{kind === "video" ? "clip.mp4" : "still.png"}</span>}</div>
        </div>
      </div>
    );
  }
  if (provider === "x" || provider === "linkedin" || provider === "reddit") {
    const label = provider === "x" ? "Preview as a post on X" : provider === "linkedin" ? "Preview as a LinkedIn post" : "Preview as a Reddit link post";
    return (
      <div className="cal-pv x" aria-label={label}>
        <div className="cal-pv-row">
          <span className="cal-pv-av" />
          <b>{handle || "you"}</b>
          <small>· now</small>
        </div>
        <p>{words}</p>
        <div className="cal-pv-media">{poster ? <img src={poster} alt="" /> : null}</div>
      </div>
    );
  }
  // instagram, tiktok, youtube: a 9:16 frame
  const story = provider === "instagram" && postType === "story";
  return (
    <div className={`cal-pv tall ${provider}`} aria-label={`Preview as ${provider === "instagram" ? (story ? "an Instagram story" : "an Instagram reel") : provider === "youtube" ? "a YouTube short" : "a TikTok video"}`}>
      {poster ? <img src={poster} alt="" /> : null}
      {story ? (
        <div className="cal-pv-bars">
          <i />
          <i />
          <i />
        </div>
      ) : null}
      <div className="cal-pv-head">
        <span className="cal-pv-av" />
        <b>{handle || "you"}</b>
      </div>
      <div className="cal-pv-cap">{story ? null : words}</div>
    </div>
  );
}

/* ── a new post ────────────────────────────────────────────────────── */

function Fresh({ seed, connections, wall, onClose, onChanged, toast }: Props & { seed: Extract<DrawerOpen, { mode: "new" }> }) {
  const [source, setSource] = useState<string | null>(seed.source ?? null);
  const [picks, setPicks] = useState<number[]>(() => {
    if (seed.connection_id && connections.some((c) => c.id === seed.connection_id)) return [seed.connection_id];
    return connections[0] ? [connections[0].id] : [];
  });
  const [tab, setTab] = useState<number | "all">("all");
  const [caption, setCaption] = useState("");
  const [overrides, setOverrides] = useState<Record<number, string>>({});
  // each platform's own form, per picked connection (a subreddit, a story switch)
  const [settingsBy, setSettingsBy] = useState<Record<number, Values>>({});
  const providers = useProviders();
  const [whenMode, setWhenMode] = useState<"slot" | "now" | "pick">(seed.at ? "pick" : "slot");
  const [picked, setPicked] = useState<string>(() => toLocalInput(seed.at ?? new Date(Date.now() + 3600 * 1000)));
  // the next free slot, for the account it was read for (undefined = reading)
  const [slotState, setSlotState] = useState<{ forId: number | null; slot: { publish_at: string } | null }>({ forId: null, slot: null });
  const [menu, setMenu] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const first = connections.find((c) => c.id === picks[0]) ?? null;
  const item = useMemo(() => {
    const m = source?.match(/^gen:(\d+)$/);
    return m ? wall.get(Number(m[1])) : undefined;
  }, [source, wall]);
  const poster = seed.poster ?? posterOfItem(item);
  const kind = seed.kind ?? item?.kind;
  const limit = first ? providers[first.provider]?.caption_max ?? LIMITS[first.provider] ?? 5000 : 5000;
  /** the required platform fields still empty, by account label */
  const incomplete = picks.flatMap((id) => {
    const c = connections.find((x) => x.id === id);
    const fields = c ? providers[c.provider]?.settings ?? [] : [];
    return missing(fields, settingsBy[id] ?? {}).map((label) => `${c?.label || c?.provider_name}: ${label}`);
  });

  // the next free slot of the first picked account
  const firstId = first?.id ?? null;
  useEffect(() => {
    if (firstId === null) return;
    let gone = false;
    nextFreeSlot(firstId)
      .then((r) => {
        if (gone) return;
        setSlotState({ forId: firstId, slot: r.slot });
        if (!r.slot) setWhenMode((m) => (m === "slot" ? "pick" : m));
      })
      .catch(() => !gone && setSlotState({ forId: firstId, slot: null }));
    return () => {
      gone = true;
    };
  }, [firstId]);
  const slot: { publish_at: string } | null | undefined = first === null ? null : slotState.forId === first.id ? slotState.slot : undefined;

  const toggle = (id: number) =>
    setPicks((cur) => {
      const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
      if (tab !== "all" && !next.includes(tab)) setTab("all");
      return next;
    });

  const whenIso = () => {
    if (whenMode === "now") return null;
    if (whenMode === "slot" && slot) return slot.publish_at;
    return new Date(picked).toISOString();
  };

  const submit = (now = false) => {
    if (!source || !picks.length || busy) return;
    setBusy(true);
    setProblem(null);
    createPostGroup({
      connection_ids: picks,
      source,
      caption: caption.trim(),
      captions: Object.fromEntries(Object.entries(overrides).filter(([id]) => picks.includes(Number(id)))),
      settings_by: Object.fromEntries(Object.entries(settingsBy).filter(([id]) => picks.includes(Number(id)))),
      publish_at: now ? null : whenIso(),
    })
      .then((r) => {
        const when = r.posts[0]?.publish_at;
        toast(now ? `Posting to ${picks.length === 1 ? first?.provider_name : `${picks.length} accounts`} now` : `Scheduled for ${when ? fmtWhen(new Date(when)) : "now"}`, "ok");
        onChanged();
        onClose();
      })
      .catch((err) => {
        setBusy(false);
        setProblem(err instanceof ApiError ? err.message : "Could not schedule the post");
      });
  };

  const unposted = useMemo(() => Array.from(wall.values()).slice(0, 12), [wall]);
  const words = tab === "all" ? caption : (overrides[tab] ?? caption);

  return (
    <>
      <div className="cal-dr-top">
        <div style={{ flex: 1 }}>
          <h2>New post</h2>
          <p>{seed.at ? `Dropped on ${fmtWhen(seed.at)}` : "One render, to the accounts you pick, at one time."}</p>
        </div>
        <button type="button" className="cal-ib" aria-label="Close" onClick={onClose}>
          <X strokeWidth={2} />
        </button>
      </div>
      <div className="cal-dr-body">
        {!source ? (
          <div className="cal-fld">
            <span>Which render</span>
            {!unposted.length ? (
              <p className="cal-hint">
                Nothing on the wall yet. <Link href="/studio">Make something</Link> first.
              </p>
            ) : (
              <div className="cal-pickgrid">
                {unposted.map((i) => (
                  <button key={i.asset_id} type="button" onClick={() => setSource(`gen:${i.generated_id}`)} title={i.prompt || i.asset_name}>
                    {posterOfItem(i) ? <img src={posterOfItem(i)!} alt="" /> : <span>{i.kind}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="cal-prev">
            {first ? <Preview provider={first.provider} poster={poster} caption={words} handle={first.handle || first.label} kind={kind} /> : null}
            <dl>
              <dt>Render</dt>
              <dd>{seed.title || item?.prompt?.slice(0, 60) || source}</dd>
              {item?.model_label ? (
                <>
                  <dt>Made on</dt>
                  <dd>{item.model_label}</dd>
                </>
              ) : null}
              <dt>Kind</dt>
              <dd>{kind === "video" ? "clip" : kind === "image" ? "still" : "—"}</dd>
              <dd>
                <button type="button" className="cal-link" onClick={() => setSource(null)}>
                  Pick another
                </button>
              </dd>
            </dl>
          </div>
        )}

        <div className="cal-fld">
          <span>To · click the accounts</span>
          {!connections.length ? (
            <p className="cal-hint">
              No account connected yet. <Link href="/studio/settings/connections">Connect one</Link>.
            </p>
          ) : (
            <div className="cal-picks" role="group" aria-label="Accounts">
              {connections.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`cal-pick${picks.includes(c.id) ? " on" : ""}`}
                  aria-pressed={picks.includes(c.id)}
                  aria-label={`${c.provider_name} ${c.label}`}
                  title={`${c.provider_name} · ${c.label}${c.status !== "connected" ? " (needs reconnecting)" : ""}`}
                  onClick={() => toggle(c.id)}
                  disabled={busy}
                >
                  <PlatformIcon provider={c.provider} size={18} />
                  <span className={`cal-glyph ${c.status === "connected" ? "published" : "error"}`} style={{ width: 9, height: 9 }} />
                </button>
              ))}
              <Link href="/studio/settings/connections" className="cal-pick add" aria-label="Connect an account">
                +
              </Link>
            </div>
          )}
          {picks.length > 1 ? (
            <div className="cal-ptabs" role="tablist" aria-label="Words for">
              <button type="button" role="tab" aria-selected={tab === "all"} onClick={() => setTab("all")}>
                All
              </button>
              {picks.map((id) => {
                const c = connections.find((x) => x.id === id);
                return c ? (
                  <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
                    <PlatformIcon provider={c.provider} size={12} /> {c.label || c.provider_name}
                    {overrides[id] !== undefined ? " ·" : ""}
                  </button>
                ) : null;
              })}
            </div>
          ) : null}
          {picks.length > 1 ? <p className="cal-hint">The same render goes to each. A tab holds its own words; All is what the rest use.</p> : null}
          {picks.map((id) => {
            const c = connections.find((x) => x.id === id);
            const fields = c ? providers[c.provider]?.settings ?? [] : [];
            if (!c || !fields.length) return null;
            return (
              <div key={id} className="cal-pf-block">
                <span className="cal-pf-title">
                  <PlatformIcon provider={c.provider} size={12} /> {c.provider_name} · {c.label}
                </span>
                <ProviderFields fields={fields} values={settingsBy[id] ?? {}} onChange={(v) => setSettingsBy((m) => ({ ...m, [id]: v }))} disabled={busy} compact />
              </div>
            );
          })}
        </div>

        <label className="cal-fld">
          <span>Words{tab !== "all" ? ` · ${connections.find((c) => c.id === tab)?.label ?? ""}` : ""}</span>
          <textarea
            className="cal-in"
            value={words}
            onChange={(e) => {
              const v = e.target.value.slice(0, limit);
              if (tab === "all") setCaption(v);
              else setOverrides((o) => ({ ...o, [tab]: v }));
            }}
            placeholder={first?.provider === "instagram" ? "Caption and hashtags" : "What to say with it"}
            rows={3}
            disabled={busy}
          />
          <small className="cal-cnt">
            {words.length} / {limit.toLocaleString()}
            {tab !== "all" && overrides[tab as number] !== undefined ? (
              <>
                {" · "}
                <button type="button" className="cal-link" onClick={() => setOverrides((o) => Object.fromEntries(Object.entries(o).filter(([k]) => Number(k) !== tab)))}>
                  use All
                </button>
              </>
            ) : null}
          </small>
        </label>

        <div className="cal-fld">
          <span>When</span>
          <div className="cal-when" role="radiogroup" aria-label="When">
            {slot ? (
              <button type="button" aria-pressed={whenMode === "slot"} onClick={() => setWhenMode("slot")} disabled={busy}>
                <StateGlyph state="queued" size={9} /> Next free slot · {fmtWhen(new Date(slot.publish_at))}
              </button>
            ) : null}
            <button type="button" aria-pressed={whenMode === "now"} onClick={() => setWhenMode("now")} disabled={busy}>
              Now
            </button>
            <button type="button" aria-pressed={whenMode === "pick"} onClick={() => setWhenMode("pick")} disabled={busy}>
              Pick a time
            </button>
            {whenMode === "pick" ? <input className="cal-in" type="datetime-local" value={picked} onChange={(e) => setPicked(e.target.value)} disabled={busy} aria-label="Date and time" style={{ width: "auto" }} /> : null}
          </div>
          {first ? (
            <p className="cal-hint">
              {slot === null
                ? `${first.label || first.provider_name} has no posting times yet; set them in Settings → Connections and the drawer fills the next free one in.`
                : slot === undefined
                  ? "Looking for the next free slot…"
                  : `Posting times for ${first.label || first.provider_name}: ${Object.values(first.posting_times.days).flat().length} a week (`}
              {slot ? <Link href="/studio/settings/connections">change</Link> : null}
              {slot ? ")." : ""}
            </p>
          ) : null}
        </div>

        {incomplete.length ? <p className="cal-hint">Still needed: {incomplete.join(", ")}.</p> : null}
        {problem ? <p className="cal-alert">{problem}</p> : null}
        <p className="cal-hint">The studio posts it as you, from the accounts above, by its own clock. You can move or cancel it until it goes. Nothing here spends credits.</p>
      </div>
      <div className="cal-dr-foot">
        <div className="cal-split">
          {menu ? (
            <div className="cal-menu" role="menu">
              <button type="button" role="menuitem" onClick={() => submit(true)}>
                <b>Post now</b>
                <small>Sent on the worker&apos;s next tick, within 20s</small>
              </button>
              <button type="button" role="menuitem" onClick={() => submit(false)}>
                <b>Schedule</b>
                <small>{whenMode === "now" ? "Now" : whenMode === "slot" && slot ? fmtWhen(new Date(slot.publish_at)) : fmtWhen(new Date(picked))}</small>
              </button>
            </div>
          ) : null}
          <button type="button" className="cal-primary" onClick={() => submit(whenMode === "now")} disabled={busy || !source || !picks.length || incomplete.length > 0} title={incomplete.length ? `Still needed: ${incomplete.join(", ")}` : undefined}>
            <Send strokeWidth={1.8} /> {busy ? "Scheduling…" : whenMode === "now" ? "Post now" : "Schedule"}
          </button>
          <button type="button" className="cal-primary caret" aria-label="More ways to send" aria-expanded={menu} onClick={() => setMenu((m) => !m)} disabled={busy || !source || !picks.length || incomplete.length > 0}>
            <ChevronDown strokeWidth={2.4} />
          </button>
        </div>
        <span className="spacer" />
        <button type="button" className="cal-btn" onClick={onClose} disabled={busy}>
          Cancel
        </button>
      </div>
    </>
  );
}

/* ── an existing post ──────────────────────────────────────────────── */

function Existing({ id, connections, wall, siblings, onClose, onChanged, toast }: Props & { id: number }) {
  const [post, setPost] = useState<Post | null>(null);
  const [caption, setCaption] = useState("");
  const [when, setWhen] = useState("");
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let gone = false;
    getPost(id)
      .then((p) => {
        if (gone) return;
        setPost(p);
        setCaption(p.caption);
        setWhen(toLocalInput(whenOf(p.publish_at)));
      })
      .catch((err) => !gone && setProblem(err instanceof ApiError ? err.message : "Could not read the post"));
    return () => {
      gone = true;
    };
  }, [id]);

  const conn = connections.find((c) => c.id === post?.connection_id) ?? null;
  const item = useMemo(() => {
    const m = post?.source_ref.match(/^gen:(\d+)$/);
    return m ? wall.get(Number(m[1])) : undefined;
  }, [post, wall]);
  const poster = posterOfItem(item) ?? (post?.media.kind === "image" ? post.media.media_url ?? null : null);
  const frozen = !post || post.state === "publishing" || post.state === "published";
  const providers = useProviders();
  const limit = post ? providers[post.provider]?.caption_max ?? LIMITS[post.provider] ?? 5000 : 5000;
  const fields = post ? providers[post.provider]?.settings ?? [] : [];

  const run = (what: () => Promise<unknown>, said: string) => {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    what()
      .then(() => {
        toast(said, "ok");
        onChanged();
        return getPost(id).then((p) => {
          setPost(p);
          setCaption(p.caption);
          setWhen(toLocalInput(whenOf(p.publish_at)));
        });
      })
      .catch((err) => setProblem(err instanceof ApiError ? err.message : "That did not work"))
      .finally(() => setBusy(false));
  };

  const saveWords = () => {
    if (!post || frozen || caption.trim() === post.caption) return;
    run(() => patchPost(post.id, { caption: caption.trim() }), "Words saved");
  };
  const move = () => {
    if (!post || frozen) return;
    const iso = new Date(when).toISOString();
    if (iso === post.publish_at) return;
    run(() => movePost(post.id, iso), `Moved to ${fmtWhen(new Date(iso))}`);
  };

  if (!post) {
    return (
      <>
        <div className="cal-dr-top">
          <div style={{ flex: 1 }}>
            <h2>Post</h2>
            <p>{problem ?? "Reading…"}</p>
          </div>
          <button type="button" className="cal-ib" aria-label="Close" onClick={onClose}>
            <X strokeWidth={2} />
          </button>
        </div>
      </>
    );
  }
  const t = whenOf(post.publish_at);
  const title = item?.prompt ? (item.prompt.length > 60 ? `${item.prompt.slice(0, 59)}…` : item.prompt) : post.caption || post.source_ref;
  return (
    <>
      <div className="cal-dr-top">
        <div style={{ flex: 1 }}>
          <h2>{title}</h2>
          <p>
            {fmtWhen(t)} · {post.provider_name}
            {conn ? ` · ${conn.label}` : ""}
          </p>
        </div>
        <button type="button" className="cal-ib" aria-label="Close" onClick={onClose}>
          <X strokeWidth={2} />
        </button>
      </div>
      <div className="cal-dr-body">
        {post.state === "error" ? (
          <div className="cal-alert" role="alert">
            <b>Did not go out</b>
            <span>{post.error || "The platform refused it."} Nothing was sent.</span>
          </div>
        ) : null}
        {post.state === "publishing" ? (
          <div className="cal-alert warm" role="status">
            <b>Sending now</b>
            <span>{post.pending ? "The platform has it and is processing the file." : "The worker holds it."} It cannot be changed until it lands.</span>
          </div>
        ) : null}
        {post.state === "published" ? (
          <div className="cal-alert ok" role="status">
            <b>Published</b>
            <span>
              {post.published_at ? fmtWhen(new Date(post.published_at)) : ""}
              {post.release_url ? (
                <>
                  {" · "}
                  <a href={post.release_url} target="_blank" rel="noreferrer">
                    open on {post.provider_name}
                  </a>
                </>
              ) : null}
            </span>
          </div>
        ) : null}

        <div className="cal-prev">
          <Preview provider={post.provider} poster={poster} caption={caption} handle={conn?.handle || conn?.label || ""} kind={post.media.kind} postType={String(post.settings.post_type ?? "")} />
          <dl>
            <dt>Render</dt>
            <dd>{item?.prompt?.slice(0, 60) || post.source_ref}</dd>
            {post.media.seconds ? (
              <>
                <dt>Length</dt>
                <dd>{Math.round(post.media.seconds)}s</dd>
              </>
            ) : null}
            {item?.model_label ? (
              <>
                <dt>Made on</dt>
                <dd>{item.model_label}</dd>
              </>
            ) : null}
            <dt>State</dt>
            <dd>
              <StateGlyph state={post.state} /> {stateWord(post.state)}
            </dd>
          </dl>
        </div>

        {siblings.length ? (
          <div className="cal-fld">
            <span>Same press, other accounts</span>
            <div className="cal-sibs">
              {siblings.map((s) => (
                <span key={s.id} className={`cal-sib ${s.state}`}>
                  <PlatformIcon provider={s.provider} size={12} /> {s.provider_name} <StateGlyph state={s.state} size={9} /> {stateWord(s.state)}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <label className="cal-fld">
          <span>Words</span>
          <textarea className="cal-in" value={caption} onChange={(e) => setCaption(e.target.value.slice(0, limit))} onBlur={saveWords} rows={3} disabled={busy || frozen} />
          <small className="cal-cnt">
            {caption.length} / {limit.toLocaleString()}
          </small>
        </label>

        {fields.length ? (
          <div className="cal-fld">
            <span>{post.provider_name} settings</span>
            <ProviderFields
              fields={fields}
              values={post.settings as Values}
              onChange={(v) => {
                if (frozen) return;
                setPost({ ...post, settings: v });
              }}
              disabled={busy || frozen}
              compact
            />
            {!frozen && missing(fields, post.settings as Values).length === 0 ? (
              <button type="button" className="cal-link" style={{ alignSelf: "flex-start" }} onClick={() => run(() => patchPost(post.id, { settings: post.settings }), "Settings saved")} disabled={busy}>
                Save settings
              </button>
            ) : null}
          </div>
        ) : null}

        <div className="cal-fld">
          <span>When</span>
          <div className="cal-when">
            <input className="cal-in" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} onBlur={move} disabled={busy || frozen} aria-label="Date and time" style={{ width: "auto" }} />
          </div>
        </div>

        {post.events?.length ? (
          <div className="cal-fld">
            <span>What happened</span>
            <div className="cal-log" aria-label="Post log">
              {post.events.map((e, i) => (
                <div key={i}>
                  <span className="cal-tm">{e.at ? fmtWhen(new Date(e.at)) : ""}</span>
                  <span className={`cal-glyph ${e.event === "error" ? "error" : e.event === "published" ? "published" : e.event === "publishing" ? "publishing" : "queued"}`} style={{ width: 9, height: 9 }} />
                  <span>
                    {e.event}
                    {e.detail ? ` · ${e.detail}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {problem ? <p className="cal-alert">{problem}</p> : null}
        <p className="cal-hint">Posted as you, from the account above, by the studio&apos;s own clock. Nothing here spends credits.</p>
      </div>
      <div className="cal-dr-foot">
        {post.state === "error" || post.state === "queued" || post.state === "draft" || post.state === "cancelled" ? (
          <div className="cal-split">
            {menu ? (
              <div className="cal-menu" role="menu">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenu(false);
                    run(async () => {
                      if (post.state !== "queued") await setPostState(post.id, "queued");
                      await movePost(post.id, null);
                    }, "Going out on the next tick");
                  }}
                >
                  <b>Post now</b>
                  <small>Sent on the worker&apos;s next tick, within 20s</small>
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenu(false);
                    run(() => setPostState(post.id, "queued"), `Queued for ${fmtWhen(t)}`);
                  }}
                >
                  <b>{post.state === "error" ? "Post again" : "Queue"} at {fmtWhen(t)}</b>
                  <small>Keeps the time above</small>
                </button>
              </div>
            ) : null}
            <button
              type="button"
              className="cal-primary"
              disabled={busy}
              onClick={() => (post.state === "queued" ? run(() => movePost(post.id, null), "Going out on the next tick") : run(() => setPostState(post.id, "queued"), post.state === "error" ? "Queued again" : "Queued"))}
            >
              <Send strokeWidth={1.8} /> {post.state === "error" ? "Post again" : post.state === "queued" ? "Post now" : "Schedule"}
            </button>
            {post.state !== "queued" ? (
              <button type="button" className="cal-primary caret" aria-label="More ways to send" aria-expanded={menu} onClick={() => setMenu((m) => !m)} disabled={busy}>
                <ChevronDown strokeWidth={2.4} />
              </button>
            ) : null}
          </div>
        ) : null}
        <span className="spacer" />
        {post.state === "queued" || post.state === "draft" || post.state === "error" ? (
          <button type="button" className="cal-btn danger" disabled={busy} onClick={() => run(() => setPostState(post.id, "cancelled"), "Cancelled; it will not go out")}>
            Cancel post
          </button>
        ) : null}
        {post.state === "cancelled" ? (
          <button
            type="button"
            className="cal-btn danger"
            disabled={busy}
            onClick={() =>
              deletePost(post.id)
                .then(() => {
                  toast("Removed from the calendar", "ok");
                  onChanged();
                  onClose();
                })
                .catch((err) => setProblem(err instanceof ApiError ? err.message : "Could not remove it"))
            }
          >
            Remove
          </button>
        ) : null}
      </div>
    </>
  );
}
