"use client";

/* Sending while signed out (2026-10-26, board 4 of the "Phantra Mobile
   Studio" canvas). It used to answer with a red "SIGN IN FIRST" pill over
   the headline and no way on; now the send opens this sheet: the prompt as
   typed, kept, and the doors to sign up. A Google or Discord tap goes
   straight to that provider (/signin?provider=, app/main.py); email opens
   the sign-up page.

   The prompt is held in this browser (localStorage, an hour) and put back
   in the box when the person lands in the studio signed in
   (takePendingPrompt). It is never sent on its own: the person presses
   Send again, which is the only thing that ever spends. */
import { useEffect } from "react";
import { ShellPortal } from "./portal";
import { Check, Gift } from "lucide-react";
import { goToSignIn } from "@/lib/api";
import { mascotSrc, DEFAULT_MASCOT } from "@/lib/mascot";
import { COMPOSE_HREF } from "./phone-chrome";
/* eslint-disable @next/next/no-img-element -- the mascot's own R2 frame */

const KEY = "phantra.pending.prompt";
const HOLD_MS = 60 * 60 * 1000;

export function keepPendingPrompt(text: string) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ text, at: Date.now() }));
  } catch {
    /* a private window: the box simply starts empty */
  }
}

/** The prompt a signed-out send kept, once; null when there is none or it
 *  is over an hour old. */
export function takePendingPrompt(): string | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    localStorage.removeItem(KEY);
    const v = JSON.parse(raw) as { text?: unknown; at?: unknown };
    if (typeof v.text !== "string" || !v.text.trim() || typeof v.at !== "number") return null;
    return Date.now() - v.at < HOLD_MS ? v.text : null;
  } catch {
    return null;
  }
}

export function SignupSheet({ prompt, onClose }: { prompt: string | null; onClose: () => void }) {
  useEffect(() => {
    if (prompt === null) return;
    if (prompt.trim()) keepPendingPrompt(prompt);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [prompt, onClose]);
  if (prompt === null) return null;
  const go = (provider?: "google" | "discord") => goToSignIn("signup", COMPOSE_HREF, provider);
  return (
    <ShellPortal>
      <div className="ph-sheet-wrap ph-signup">
        <button type="button" className="ph-scrim" aria-label="Close" onClick={onClose} />
        <section className="ph-sheet" role="dialog" aria-modal="true" aria-labelledby="ph-signup-h">
          <span className="ph-grab" aria-hidden />
          <div className="ph-signup-head">
            <img src={mascotSrc(DEFAULT_MASCOT, "talk", 128)} alt="" width={64} height={64} />
            <h2 id="ph-signup-h">Sign up to make this</h2>
          </div>
          {prompt.trim() ? (
            <div className="ph-signup-prompt">
              <span>{prompt.trim()}</span>
              <small>
                <Check strokeWidth={2.6} aria-hidden /> Saved. It&apos;ll be in the box when you&apos;re back.
              </small>
            </div>
          ) : null}
          <p className="ph-signup-gift">
            <Gift strokeWidth={2} aria-hidden /> Free credits when you sign up
          </p>
          <button type="button" className="ph-light" onClick={() => go("google")}>
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden>
              <path fill="#4285F4" d="M22.5 12.3c0-.8-.1-1.5-.2-2.2H12v4.2h5.9a5 5 0 0 1-2.2 3.3v2.7h3.6c2-1.9 3.2-4.7 3.2-8" />
              <path fill="#34A853" d="M12 23c3 0 5.5-1 7.3-2.7l-3.6-2.7c-1 .7-2.2 1.1-3.7 1.1-2.9 0-5.3-1.9-6.2-4.5H2.1v2.8A11 11 0 0 0 12 23" />
              <path fill="#FBBC05" d="M5.8 14.2a6.6 6.6 0 0 1 0-4.3V7.1H2.1a11 11 0 0 0 0 9.9z" />
              <path fill="#EA4335" d="M12 5.4c1.6 0 3.1.6 4.2 1.7l3.2-3.2A11 11 0 0 0 2.1 7.1l3.7 2.8C6.7 7.3 9.1 5.4 12 5.4" />
            </svg>
            Continue with Google
          </button>
          <button type="button" className="ph-ghost" onClick={() => go("discord")}>
            Continue with Discord
          </button>
          <button type="button" className="ph-ghost" onClick={() => go()}>
            Continue with email
          </button>
          <p className="ph-signup-foot">
            Have an account?{" "}
            <button type="button" onClick={() => goToSignIn(undefined, COMPOSE_HREF)}>
              Log in
            </button>
          </p>
        </section>
      </div>
    </ShellPortal>
  );
}
