"use client";

/* Vesper behind the Create box (2026-10-27, Mike: "when you click on him it
   takes you to the create chat box with him small behind it ready to help").
   Everywhere else he sits small in the header's top left corner
   (assistant-pill.tsx); on Create the box is where he is talked to, so he
   peeks over its top edge, head and lantern showing, the rest hidden by the
   box. The "behind" is a clip, not a z-index: the wrapper ends exactly at
   the box's top edge, so it reads the same whether the box sits in the
   middle of the page or is docked under a conversation.

   Interactive (same day, Mike: "can he be interactive sometimes?"):
   - reacts: listens while you type, nods when you send, thinks while a
     turn is out, works while a make runs, hops when it lands, looks worried
     when a send fails;
   - follows the pointer with his gaze when it comes near;
   - speaks sometimes (lib/vesper-voice.ts): a hello once per tab, a line
     when a make lands or fails, and after a while of an empty, untouched
     box, one tip from what he remembers -- your newest projects and
     renders -- that a tap drops into the box (or opens the project).
   Nothing he says spends; a tip only fills the box, the send stays yours. */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AssistantAvatar, type AvatarState } from "@/components/studio/assistant-avatar";
import { useAssistantThread } from "@/components/studio/assistant-thread";
import { useShell } from "@/components/studio/shell";
import { PERSONA_EVENT, loadPersona, type Persona } from "@/lib/assistant";
import { DEFAULT_AVATAR, decodeMascot, nameOf } from "@/lib/mascot";
import { workspaceHref } from "@/lib/studio-api";
import { TIP_IDLE_MS, failed as failedLine, greeting, landed, tips, type Line } from "@/lib/vesper-voice";
import { VoiceBubble, useGaze, useRecentWork, useVoice } from "@/components/studio/vesper-voice";

const GREETED_KEY = "phantra.assistant.greeted";
const FLASH_MS = 1600;

export function VesperPeek({
  busy,
  making,
  typing,
  failed,
  kind,
  onFill,
  onWake,
}: {
  /** a turn is out */
  busy: boolean;
  /** a make (still, scene, clip) is running */
  making: boolean;
  /** there are words in the box */
  typing: boolean;
  /** the newest send did not go through */
  failed: boolean;
  /** what the box makes now, for the line when a make lands */
  kind: "image" | "video";
  /** a tip was tapped: these words go in the box */
  onFill: (text: string) => void;
  /** he was clicked: the cursor goes in the box */
  onWake: () => void;
}) {
  const router = useRouter();
  const { me } = useShell();
  const { account } = useAssistantThread();
  const [persona, setPersona] = useState<Persona | null>(null);
  useEffect(() => {
    if (!account) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is only readable after mount
    setPersona(loadPersona(account));
    const follow = () => setPersona(loadPersona(account));
    window.addEventListener(PERSONA_EVENT, follow);
    return () => window.removeEventListener(PERSONA_EVENT, follow);
  }, [account]);
  const avatar = persona?.avatar ?? DEFAULT_AVATAR;
  const name = persona?.name ?? nameOf(decodeMascot(avatar));

  const recent = useRecentWork(account);
  const { line, say, hush, said } = useVoice();
  const look = useRef<HTMLSpanElement>(null);
  useGaze(look);

  // a short reaction on top of the steady face: a nod on send, a hop when
  // a make lands, a wince when a send fails
  const [flash, setFlash] = useState<"nod" | "hop" | "wince" | null>(null);
  const [cheer, setCheer] = useState(false);
  const was = useRef({ busy, making, failed });
  useEffect(() => {
    const before = was.current;
    was.current = { busy, making, failed };
    let next: typeof flash = null;
    if (busy && !before.busy) next = "nod";
    else if (failed && !before.failed) {
      next = "wince";
      say(failedLine(), true);
    } else if (before.making && !making && !failed) {
      next = "hop";
      setCheer(true);
      say(landed(kind), true);
    }
    if (!next) return;
    setFlash(next);
    const t = setTimeout(() => {
      setFlash(null);
      setCheer(false);
    }, FLASH_MS);
    return () => clearTimeout(t);
  }, [busy, making, failed, kind, say]);

  // the hello, once per tab (the corner shares the key, so he says it once)
  useEffect(() => {
    if (!me) return;
    try {
      if (sessionStorage.getItem(GREETED_KEY)) return;
      sessionStorage.setItem(GREETED_KEY, "1");
    } catch {
      return;
    }
    const t = setTimeout(() => say(greeting(me.user.display_name, recent), true), 1200);
    return () => clearTimeout(t);
    // the newest project is worth waiting a beat for, not re-greeting over
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me]);

  // a tip, after a while of an empty box nobody is touching
  useEffect(() => {
    if (busy || typing || line) return;
    const t = setTimeout(() => {
      const pick = tips(recent, said())[0];
      if (pick) say(pick);
    }, TIP_IDLE_MS);
    return () => clearTimeout(t);
  }, [busy, typing, line, recent, say, said]);

  // what you do comes first: typing quiets him
  useEffect(() => {
    if (typing && line && !line.id.startsWith("landed") && line.id !== "failed") hush();
  }, [typing, line, hush]);

  // his mouth moves for the first moment of a line, not the whole time it shows
  const [chatty, setChatty] = useState(false);
  useEffect(() => {
    if (!line) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- a new line starts the mouth
    setChatty(true);
    const t = setTimeout(() => setChatty(false), FLASH_MS);
    return () => clearTimeout(t);
  }, [line]);

  const state: AvatarState = failed
    ? "error"
    : cheer
      ? "success"
      : making
        ? "working"
        : busy
          ? "thinking"
          : line && chatty
            ? "talking"
            : typing
              ? "listening"
              : "idle";

  const act = (l: Line) => {
    hush();
    if (l.project) router.push(workspaceHref(l.project));
    else if (l.fill) onFill(l.fill);
  };

  return (
    <>
      <span className="zc-vesper" data-state={state} data-flash={flash ?? undefined}>
        <button type="button" onClick={onWake} title={`${name} is here — type below to talk`} aria-label={`Talk to ${name}`}>
          <span className="vv-look" ref={look}>
            <AssistantAvatar avatar={avatar} state={state} size="lg" />
          </span>
        </button>
      </span>
      <VoiceBubble line={line} onAct={act} onClose={hush} className="vv-peek" />
    </>
  );
}
