"use client";

/* A project's HOME (2026-11-02, Mike's pick "B2" on the project-page design
   canvas, Runway's project page as the model): the project's latest render
   as a full-bleed cover with the title on it, two doors floating over its
   bottom edge -- Generate in Session (the Create chat, scoped to the
   project) and Create Workflow (the node canvas, project-workspace.tsx) --
   the brand kit panel (project-kit-panel.tsx), the look and brief, and the
   project's creation spaces: its chat and its scenes.

   /studio/projects/<id> opens here. The workspace (scenes, canvas, brief
   panes) is the same address with ?view=canvas, ?scene=, or ?new=1 (a blank
   canvas, the browser-local draft), so every older scene link still lands
   on its canvas. Nothing on this page spends. Styles: project-home.css. */
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, MessageCircle, Plus, Workflow } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  boardConcepts,
  getProject,
  projectMessages,
  rememberActiveProject,
  updateProject,
  workspaceHref,
  type Concept,
  type Project,
  type ProjectMessage,
} from "@/lib/studio-api";
import { heroOf, RefImg, thumbOf } from "@/components/studio/concept-card";
import { ProjectKitPanel } from "@/components/studio/project-kit-panel";
import { renderedOf } from "@/lib/render-choice";
import { useShell } from "@/components/studio/shell";
import "@/components/studio/project-home.css";

type Filter = "all" | "sessions" | "workflows";
type Editing = "look" | "brief" | null;

/** "today", "yesterday", "3 days ago", else the date */
function ago(iso?: string | null): string {
  const t = Date.parse(iso || "");
  if (!Number.isFinite(t)) return "";
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const clipSrc = (url: string) => (url.startsWith("/") ? API_URL + url : url);

/** where a scene stands, in a few words */
function standing(c: Concept): { text: string; tone: "" | "ok" | "warn" } {
  const done = renderedOf(c.media_url, c.timeline?.parts);
  if (done.state === "done") return { text: "rendered", tone: "ok" };
  if (done.state === "partial") return { text: `${done.clips} of ${done.of} rendered`, tone: "" };
  if (!(c.refs || []).length) return { text: "needs a reference photo", tone: "warn" };
  return { text: "not rendered yet", tone: "" };
}

/** the first line of a chat turn, short enough for a card title */
const firstLine = (s: string, max = 60) => {
  const line = (s || "").split("\n").map((l) => l.trim()).find(Boolean) || "";
  return line.length > max ? `${line.slice(0, max - 1)}…` : line;
};

export function ProjectHome({ id }: { id: number }) {
  const { me, toast } = useShell();
  const [project, setProject] = useState<Project | null>(null);
  const [missing, setMissing] = useState("");
  const [scenes, setScenes] = useState<Concept[] | null>(null);
  const [chat, setChat] = useState<{ items: ProjectMessage[]; more: boolean } | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [editing, setEditing] = useState<Editing>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!me) return;
    let live = true;
    rememberActiveProject(id);
    getProject(id)
      .then((p) => live && setProject(p))
      .catch((e) => live && setMissing(e instanceof Error ? e.message : "This project could not be opened"));
    boardConcepts("all", id)
      .then((r) => live && setScenes(r.items.filter((c) => c.is_scene && !c.archived)))
      .catch(() => live && setScenes([]));
    projectMessages(id)
      .then((r) => live && setChat({ items: r.items, more: r.has_more }))
      .catch(() => live && setChat({ items: [], more: false }));
    return () => {
      live = false;
    };
  }, [me, id]);

  // newest first; the cover is the newest scene with a clip
  const ordered = useMemo(
    () => [...(scenes || [])].sort((a, b) => (Date.parse(b.created_at || "") || b.id) - (Date.parse(a.created_at || "") || a.id)),
    [scenes],
  );
  const coverClip = ordered.find((c) => c.media_url)?.media_url || "";
  const coverStill = useMemo(() => {
    for (const c of ordered) {
      const h = heroOf(c);
      if (h.kind === "keyframe") return h.url;
    }
    return project?.cover || "";
  }, [ordered, project]);
  // the scene the Workflow door continues: the newest one still being worked on, else the newest
  const continuing = ordered.find((c) => renderedOf(c.media_url, c.timeline?.parts).state !== "done") || ordered[0] || null;

  const hasChat = !!chat && chat.items.length > 0;
  const sessionHref = `/studio${hasChat ? "/chat" : ""}?project=${id}`;
  const sparkHref = (spark: string) => `/studio?project=${id}&spark=${encodeURIComponent(spark)}`;
  const remember = () => rememberActiveProject(id);

  const openEditor = (which: Exclude<Editing, null>) => {
    if (editing === which) return setEditing(null);
    setText(which === "look" ? project?.look || "" : project?.brief || "");
    setEditing(which);
  };
  const saveEditor = useCallback(async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const next = await updateProject(id, editing === "look" ? { look: text.trim() } : { brief: text.trim() });
      setProject(next);
      setEditing(null);
      toast(editing === "look" ? "Look saved — the next still and scene follow it" : "Brief saved", "ok");
    } catch (e) {
      toast(e instanceof Error ? e.message : "That was not saved", "err");
    } finally {
      setSaving(false);
    }
  }, [editing, id, text, toast]);

  if (missing && !project) {
    return (
      <div className="pj pj-missing">
        <p>{missing}</p>
        <Link href="/studio/projects">← All projects</Link>
      </div>
    );
  }

  const rendered = ordered.filter((c) => renderedOf(c.media_url, c.timeline?.parts).state === "done").length;
  const lastUser = chat?.items.filter((m) => m.role === "user").at(-1) ?? chat?.items.at(-1);
  const showSessions = filter !== "workflows";
  const showWorkflows = filter !== "sessions";

  return (
    <div className="pj">
      {/* ── the cover ── */}
      <header className="pj-cover">
        {coverClip ? (
          <video
            className="pj-cover-media"
            src={clipSrc(coverClip)}
            poster={coverStill ? clipSrc(coverStill) : undefined}
            autoPlay
            muted
            loop
            playsInline
            aria-hidden
          />
        ) : coverStill ? (
          <RefImg url={coverStill} eager className="pj-cover-media" deadLabel="" />
        ) : null}
        <div className="pj-cover-fade" aria-hidden />
        <div className="pj-cover-bar">
          <Link href="/studio/projects" className="pj-back">
            <ArrowLeft size={16} strokeWidth={2} aria-hidden />
            All projects
          </Link>
        </div>
        <div className="pj-cover-title">
          <h1>{project?.title || " "}</h1>
          <p>
            {scenes === null
              ? " "
              : [
                  `${ordered.length} scene${ordered.length === 1 ? "" : "s"}`,
                  rendered ? `${rendered} rendered` : "",
                  project?.updated_at ? `updated ${ago(project.updated_at)}` : "",
                ]
                  .filter(Boolean)
                  .join(" · ")}
          </p>
        </div>
      </header>

      {/* ── the two doors ── */}
      <div className="pj-doors">
        <div className="pj-door">
          <Link href={sessionHref} onClick={remember} className="pj-door-main">
            <span className="pj-door-icon">
              <MessageCircle size={22} strokeWidth={2} aria-hidden />
            </span>
            <span className="pj-grow">
              <span className="pj-door-title">{hasChat ? "Continue in Session" : "Generate in Session"}</span>
              <span className="pj-door-sub">Chat with Vesper. Stills and scenes on an ask.</span>
            </span>
            <ArrowRight size={20} strokeWidth={2} className="pj-door-arrow" aria-hidden />
          </Link>
          <div className="pj-door-chips">
            <Link href={sparkHref("Make 3 stills for this project")} onClick={remember} className="pj-chip">
              Make 3 stills
            </Link>
            <Link href={sparkHref("Write a 15 second spot for this project")} onClick={remember} className="pj-chip">
              Write a 15s spot
            </Link>
          </div>
        </div>
        <div className="pj-door">
          <Link
            href={continuing ? workspaceHref(id, continuing.id) : `/studio/projects/${id}?new=1`}
            className="pj-door-main"
          >
            <span className="pj-door-icon pj-door-icon-on">
              <Workflow size={22} strokeWidth={2} aria-hidden />
            </span>
            <span className="pj-grow">
              <span className="pj-door-title">{continuing ? "Open Workflow" : "Create Workflow"}</span>
              <span className="pj-door-sub">
                {continuing ? `Continue “${continuing.title || "Untitled"}” on the nodes.` : "Build a scene shot by shot on the nodes."}
              </span>
            </span>
            <ArrowRight size={20} strokeWidth={2} className="pj-door-arrow" aria-hidden />
          </Link>
          <div className="pj-graph" aria-hidden>
            <span>Prompt</span>
            <i />
            <span className="pj-graph-on">Scene</span>
            <i />
            <span>Shots</span>
          </div>
        </div>
      </div>

      <div className="pj-body">
        <ProjectKitPanel projectId={id} />

        {/* ── look, brief, elements ── */}
        <div className="pj-chips">
          <button type="button" className="pj-chip" aria-expanded={editing === "look"} onClick={() => openEditor("look")}>
            {project?.look ? `Look: ${firstLine(project.look, 34)}` : "Add a look"}
          </button>
          <button type="button" className="pj-chip" aria-expanded={editing === "brief"} onClick={() => openEditor("brief")}>
            {project?.brief ? "Brief" : "Write a brief"}
          </button>
          <Link href="/studio/elements" className="pj-chip">
            Elements
          </Link>
        </div>
        {editing ? (
          <div className="pj-editor">
            <label htmlFor="pj-editor-text">{editing === "look" ? "The project's look" : "The project's brief"}</label>
            <p>
              {editing === "look"
                ? "How everything in this project should look: light, lens, colour, mood. Every still and scene follows it."
                : "What this project is for. Vesper reads it on every turn."}
            </p>
            <textarea id="pj-editor-text" value={text} rows={editing === "look" ? 3 : 6} onChange={(e) => setText(e.target.value)} />
            <div className="pj-editor-acts">
              <button type="button" className="pj-pill" disabled={saving} onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button type="button" className="pj-pill pj-pill-white" disabled={saving} onClick={() => void saveEditor()}>
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ) : null}

        {/* ── creation spaces ── */}
        <div className="pj-spaces-head">
          <h2>Creation Spaces</h2>
          <div className="pj-tabs" role="tablist" aria-label="Show">
            {(["all", "sessions", "workflows"] as Filter[]).map((f) => (
              <button key={f} type="button" role="tab" aria-selected={filter === f} onClick={() => setFilter(f)}>
                {f === "all" ? "All" : f === "sessions" ? "Sessions" : "Workflows"}
              </button>
            ))}
          </div>
        </div>

        <div className="pj-grid">
          {scenes === null || chat === null
            ? Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="pj-card pj-card-wait" aria-hidden>
                  <div className="pj-card-pic" />
                  <div className="pj-card-line" />
                </div>
              ))
            : null}

          {showSessions && hasChat && lastUser ? (
            <Link href={`/studio/chat?project=${id}`} onClick={remember} className="pj-card">
              <div className="pj-card-pic pj-card-chat">
                <span className="pj-bubble pj-bubble-me">{firstLine(lastUser.content, 90)}</span>
              </div>
              <div className="pj-card-title">Project chat</div>
              <div className="pj-card-meta">
                <MessageCircle size={12} strokeWidth={2.2} aria-hidden />
                Session · {chat!.items.length}
                {chat!.more ? "+" : ""} messages · {ago(chat!.items.at(-1)?.created_at)}
              </div>
            </Link>
          ) : null}

          {showWorkflows
            ? ordered.map((c) => {
                const hero = heroOf(c);
                const s = standing(c);
                return (
                  <Link key={c.id} href={workspaceHref(id, c.id)} className="pj-card">
                    <div className="pj-card-pic">
                      {hero.kind !== "none" ? (
                        <RefImg
                          url={hero.url}
                          thumb={hero.kind === "ref"}
                          small={hero.kind === "ref" ? thumbOf(c, 0) : ""}
                          className="pj-card-img"
                          deadLabel=""
                        />
                      ) : (
                        <span className="pj-card-dots" />
                      )}
                    </div>
                    <div className="pj-card-title">{c.title || "Untitled"}</div>
                    <div className={`pj-card-meta ${s.tone ? `pj-${s.tone}` : ""}`}>
                      <Workflow size={12} strokeWidth={2.2} aria-hidden />
                      Workflow · {s.text}
                    </div>
                  </Link>
                );
              })
            : null}

          {scenes !== null && chat !== null ? (
            <div className="pj-card pj-card-new">
              <Link href={`/studio?project=${id}`} onClick={remember} className="pj-new-row">
                <MessageCircle size={16} strokeWidth={2} aria-hidden />
                <span className="pj-grow">Generate in Session</span>
                <ArrowRight size={14} strokeWidth={2} aria-hidden />
              </Link>
              <Link href={`/studio/projects/${id}?new=1`} className="pj-new-row">
                <Plus size={16} strokeWidth={2} aria-hidden />
                <span className="pj-grow">Create Workflow</span>
                <ArrowRight size={14} strokeWidth={2} aria-hidden />
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
