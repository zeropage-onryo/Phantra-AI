"use client";

/* THE HISTORY DRAWER (2026-11-03, Mike's pick "C2" on the Sessions & Memory
   canvas). Every chat the studio kept, grouped the way the work is: a
   folder per project (its workspace chat first, then the Create chats that
   ran inside it), then the chats on their own under "Chats". New session
   no longer throws a chat away -- the server parks it (src/assistant_store.py)
   and this drawer brings it back.

   A chat on its own is deleted 14 days after it was last used; its
   countdown shows only in the last week (Mike: no "chats clear after 14
   days" note, and no countdown before the last 7 days). A project's chats
   are kept for as long as the project is.

   Opened by the header's History button and the chat sheet's clock
   (lib/assistant.ts requestHistory), which sit above this provider. Nothing
   here calls a model or spends. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronDown, ChevronRight, MessageSquare, Plus, X } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { useAssistantThread } from "@/components/studio/assistant-thread";
import {
  HISTORY_EVENT,
  countdown,
  deleteChat,
  listChats,
  requestNewSession,
  type ChatList,
  type ChatSummary,
} from "@/lib/assistant";
import { workspaceHref } from "@/lib/studio-api";
import "./chat-history.css";

const CHAT_PAGE = "/studio/chat";

/* "Today", "Yesterday", else "Oct 31" */
function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(new Date()) - day(d)) / 86_400_000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ChatHistory() {
  const { toast } = useShell();
  const { openChat, account } = useAssistantThread();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<ChatList | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  // folders the person opened or closed by hand; the rest follow the default
  // (the folder holding the open chat starts open)
  const [folded, setFolded] = useState<Record<number, boolean>>({});

  const load = useCallback(() => {
    setFailed(false);
    listChats()
      .then(setList)
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    const on = () => {
      setOpen(true);
      load();
    };
    window.addEventListener(HISTORY_EVENT, on);
    return () => window.removeEventListener(HISTORY_EVENT, on);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // a different workspace's history is never shown under this one
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on an account switch
    setList(null);
    setOpen(false);
  }, [account]);

  const groups = useMemo(() => {
    if (!list) return null;
    const byProject = new Map<number, ChatSummary[]>();
    const alone: ChatSummary[] = [];
    // a chat whose project has no folder (archived) is listed with the rest
    const folders = new Set(list.projects.map((p) => p.id));
    for (const c of list.chats) {
      if (c.project_id && folders.has(c.project_id)) byProject.set(c.project_id, [...(byProject.get(c.project_id) ?? []), c]);
      else alone.push(c);
    }
    return { byProject, alone };
  }, [list]);

  async function pick(c: ChatSummary) {
    if (busy) return;
    if (c.open) {
      setOpen(false);
      router.push(CHAT_PAGE);
      return;
    }
    setBusy(c.id);
    try {
      await openChat(c.id);
      setOpen(false);
      router.push(CHAT_PAGE);
    } catch {
      toast("That chat could not be opened", "err");
      load();
    } finally {
      setBusy(null);
    }
  }

  async function remove(c: ChatSummary) {
    if (busy) return;
    setBusy(c.id);
    try {
      await deleteChat(c.id);
      setList((l) => (l ? { ...l, chats: l.chats.filter((x) => x.id !== c.id) } : l));
      toast("Chat deleted");
    } catch {
      toast("That chat could not be deleted", "err");
    } finally {
      setBusy(null);
    }
  }

  function startNew() {
    requestNewSession();
    setOpen(false);
    toast("New session · the last one is kept");
    router.push(CHAT_PAGE);
  }

  if (!open) return null;

  const row = (c: ChatSummary, nested: boolean) => {
    const left = countdown(c.days_left);
    return (
      <li key={c.id} className={`ch-row${nested ? " nested" : ""}${c.open ? " is-open" : ""}`}>
        <button type="button" className="ch-pick" onClick={() => void pick(c)} disabled={busy === c.id}>
          <span className="ch-title">{c.title}</span>
          <span className="ch-meta">
            {c.open ? <span className="ch-now">● open now</span> : when(c.updated_at)}
            {left ? (
              <>
                {" · "}
                <span className="ch-left">{left}</span>
              </>
            ) : null}
          </span>
        </button>
        {!c.open ? (
          <button
            type="button"
            className="ch-del"
            onClick={() => void remove(c)}
            aria-label={`Delete “${c.title}”`}
            title="Delete this chat"
            disabled={busy === c.id}
          >
            <X size={13} strokeWidth={2} aria-hidden />
          </button>
        ) : null}
      </li>
    );
  };

  return (
    <div className="ch-layer">
      <button type="button" className="ch-scrim" aria-label="Close history" onClick={() => setOpen(false)} />
      <nav className="ch-drawer" aria-label="Chat history">
        <div className="ch-head">
          <b>History</b>
          <span className="spacer" />
          <button type="button" className="ch-new" onClick={startNew} aria-label="New session" title="New session">
            <Plus size={15} strokeWidth={2.4} aria-hidden />
          </button>
          <button type="button" className="ch-x" onClick={() => setOpen(false)} aria-label="Close history">
            <X size={16} strokeWidth={2} aria-hidden />
          </button>
        </div>
        <div className="ch-body">
          {failed ? (
            <p className="ch-empty">
              History could not be loaded.{" "}
              <button type="button" className="ch-retry" onClick={load}>
                Try again
              </button>
            </p>
          ) : !list || !groups ? (
            <p className="ch-empty">Loading…</p>
          ) : !list.chats.length && !list.projects.length ? (
            <p className="ch-empty">No chats yet. Start one in Create and it will be kept here.</p>
          ) : (
            <>
              {list.projects.length ? <p className="ch-label">Projects</p> : null}
              <ul className="ch-list">
                {list.projects.map((p) => {
                  const chats = groups.byProject.get(p.id) ?? [];
                  const holdsOpen = chats.some((c) => c.open);
                  const isOpen = folded[p.id] ?? holdsOpen;
                  const Chevron = isOpen ? ChevronDown : ChevronRight;
                  return (
                    <li key={p.id} className="ch-folder">
                      <button
                        type="button"
                        className="ch-fold"
                        aria-expanded={isOpen}
                        onClick={() => setFolded((f) => ({ ...f, [p.id]: !isOpen }))}
                      >
                        <Chevron size={13} strokeWidth={2.4} aria-hidden />
                        <span className="ch-fold-name">{p.title}</span>
                        <span className="ch-count">{chats.length + (p.messages ? 1 : 0)}</span>
                      </button>
                      {isOpen ? (
                        <ul className="ch-list">
                          {p.messages ? (
                            <li className="ch-row nested">
                              <Link className="ch-pick" href={workspaceHref(p.id)} onClick={() => setOpen(false)}>
                                <span className="ch-title">
                                  <MessageSquare size={12} strokeWidth={2} aria-hidden /> Project chat
                                </span>
                                <span className="ch-meta">{p.messages} messages · on the project page</span>
                              </Link>
                            </li>
                          ) : null}
                          {chats.map((c) => row(c, true))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
              {groups.alone.length ? <p className="ch-label">Chats</p> : null}
              <ul className="ch-list">{groups.alone.map((c) => row(c, false))}</ul>
            </>
          )}
        </div>
      </nav>
    </div>
  );
}
