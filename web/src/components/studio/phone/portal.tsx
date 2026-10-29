"use client";

/* The phone's sheets are drawn at the shell's root (.zps), not inside the
   page: inside the page's stacking context the fixed tab bar sat over
   their bottom edge. The shell root, not <body>, so the studio's font
   variables (set on its wrapper) still reach them. */
import { useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";

const none = () => () => {};
export function ShellPortal({ children }: { children: ReactNode }) {
  const root = useSyncExternalStore(
    none,
    () => document.querySelector<HTMLElement>(".zps"),
    () => null,
  );
  return root ? createPortal(children, root) : <>{children}</>;
}
