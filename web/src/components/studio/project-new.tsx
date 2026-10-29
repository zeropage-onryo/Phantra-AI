"use client";

/* New project (2026-10-22, Mike: "there should be a create project button").
   The Projects board's own door beside the Guide's: a name and, if the person
   has one, a brief. Everything else (look, memory, scenes) starts empty and
   is filled by working inside the project. Posts POST /projects and hands the
   new project back so the board can open it. */
import { useEffect, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { createProject, type Project } from "@/lib/studio-api";
import { cardFonts } from "@/components/studio/card-fonts";

export function NewProjectDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (project: Project) => void;
}) {
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState("");
  const name = useRef<HTMLInputElement>(null);

  // a fresh form every time it opens
  useEffect(() => {
    if (open) {
      setTitle("");
      setBrief("");
      setFailed("");
    }
  }, [open]);

  const go = async () => {
    const t = title.trim();
    if (!t || busy) return;
    setBusy(true);
    setFailed("");
    try {
      onCreated(await createProject({ title: t, brief: brief.trim() }));
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "That did not go through");
    } finally {
      setBusy(false);
    }
  };

  const field =
    "w-full rounded-[8px] border border-noir-line bg-transparent px-3 text-[15px] text-bone outline-none placeholder:text-bone3 focus:border-bone";

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o && !busy) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[950] bg-black/70" />
        <Dialog.Popup
          initialFocus={name}
          className={`${cardFonts} fixed left-1/2 top-1/2 z-[951] flex max-h-[85vh] w-[520px] max-w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-[10px] border border-noir-line bg-noir-panel p-6 font-tight text-sm leading-normal text-bone outline-none max-sm:p-4`}
        >
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              void go();
            }}
          >
            <Dialog.Title className="m-0 font-bebas text-[34px] font-normal leading-none tracking-[0.02em]">
              New project
            </Dialog.Title>
            <Dialog.Description className="m-0 text-[14.5px] text-bone2">
              A project holds the scenes for one piece of work — an ad, a short, a launch — and remembers its brief and
              look so every render stays consistent.
            </Dialog.Description>
            <label className="flex flex-col gap-1.5">
              <span className="font-plex text-[11px] tracking-[0.12em] text-bone3">NAME</span>
              <input
                ref={name}
                value={title}
                maxLength={120}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Spring launch ad"
                className={`${field} h-11`}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-plex text-[11px] tracking-[0.12em] text-bone3">BRIEF (OPTIONAL)</span>
              <textarea
                value={brief}
                maxLength={8000}
                rows={5}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="Who it is for, the look, what to always include, what to never do. You can leave this empty and let the assistant build it with you."
                className={`${field} resize-y py-2.5`}
              />
            </label>
            {failed ? (
              <p className="m-0 text-noir-danger" role="alert">
                {failed}
              </p>
            ) : null}
            <div className="flex flex-wrap justify-end gap-2">
              <Dialog.Close
                type="button"
                disabled={busy}
                className="h-11 rounded-[8px] border border-noir-line bg-transparent px-4 font-plex! text-xs! tracking-[0.08em] text-bone! hover:enabled:border-bone"
              >
                CANCEL
              </Dialog.Close>
              <button type="submit" disabled={busy || !title.trim()} className="btn pri">
                {busy ? "CREATING…" : "CREATE PROJECT"}
              </button>
            </div>
          </form>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
