/* The Explore / Make switch on a project, as it is drawn (2026-10-11; item
   13 of docs/tasks/task-studio-agent.md, lib/explore.ts).

   Two pieces:

   - ExploreSwitch is the control itself: two halves, one of them on. It
     sits on the project row above the composer's box and at the top of a
     workspace's project panel -- the setting is the project's, so it is
     drawn where the project is named, never on the box's settings line.
     No red: nothing here is live or spends.
   - SwitchCard is the card under the brain's answer when it was asked to
     make something while the project explores. It is built on the confirm
     card (.ccard) the thread already has. "Switch to Make" flips the
     project and sends the ask again; "Keep exploring" leaves it. Neither
     spends: what the ask makes after the switch waits on its own card. */
"use client";

import { Compass, Sparkle } from "lucide-react";

import {
  SWITCH_LABEL,
  SWITCH_SIDES,
  switchNote,
  switchState,
  switchTitle,
} from "@/lib/explore";

export function ExploreSwitch({
  exploring,
  busy,
  onChange,
}: {
  exploring: boolean;
  busy?: boolean;
  /** asked to go to Explore (true) or to Make (false); never the side it is on */
  onChange: (explore: boolean) => void;
}) {
  return (
    <span className="zex-switch" role="radiogroup" aria-label="What a send does in this project">
      {SWITCH_SIDES.map((s) => {
        const on = (s.id === "explore") === exploring;
        return (
          <button
            key={s.id}
            type="button"
            role="radio"
            className="zex-side"
            aria-checked={on}
            title={s.title}
            disabled={busy}
            onClick={() => {
              if (!on) onChange(s.id === "explore");
            }}
          >
            {s.id === "explore" ? <Compass strokeWidth={1.7} aria-hidden /> : <Sparkle strokeWidth={1.7} aria-hidden />}
            {s.label}
          </button>
        );
      })}
    </span>
  );
}

export function SwitchCard({
  kind,
  decided,
  busy,
  onDecide,
}: {
  /** what the person asked to have made (the proposal's `kind`) */
  kind: unknown;
  decided?: "done" | "skipped";
  busy: boolean;
  onDecide: (yes: boolean) => void;
}) {
  return (
    <div className={`ccard zex-card${decided ? ` ${decided}` : ""}`}>
      <span className="zex-label">{SWITCH_LABEL}</span>
      <b>{switchTitle(kind)}</b>
      {decided ? (
        <span className="ccard-state">{switchState(decided)}</span>
      ) : (
        <>
          <p className="zex-note">{switchNote(kind)}</p>
          <div className="ccard-actions">
            <button type="button" className="yes" disabled={busy} onClick={() => onDecide(true)}>
              <Sparkle strokeWidth={1.8} aria-hidden />
              Switch to Make
            </button>
            <button type="button" disabled={busy} onClick={() => onDecide(false)}>
              Keep exploring
            </button>
          </div>
        </>
      )}
    </div>
  );
}
