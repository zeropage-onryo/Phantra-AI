"use client";

/* Connect an editing app (2026-10-22, app/plugin_api.py). The panel shows a
   code like KDPX-7QHR and opens this page; the person TYPES the code, sees
   which app is asking and which workspace it will reach, and presses
   Connect. Nothing here spends: a connected panel still prices every render
   and waits for its own Approve.

   THE CODE IS NEVER TAKEN FROM THE ADDRESS (security review, 2026-10-22).
   A link with the code in it lets anyone start a pairing, send the link,
   and have a signed-in person connect THEIR panel with one click. Typing
   what your own panel shows is the proof that the panel is yours.

   Signed out, the page asks for a sign-in that comes straight back here. */
import { useState, type FormEvent } from "react";
import { ApiError, goToSignIn } from "@/lib/api";
import { approvePluginLink, getPluginLink, type PluginLinkPreview } from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { Button, Field, Notice, SettingsCard } from "@/components/studio/settings/ui";

type State =
  | { step: "enter" }
  | { step: "checking" }
  | { step: "confirm"; preview: PluginLinkPreview }
  | { step: "connecting"; preview: PluginLinkPreview }
  | { step: "done"; client: string }
  | { step: "error"; message: string };

const CODE_SHAPE = /^[A-Z0-9]{4}-?[A-Z0-9]{4}$/;

function tidy(raw: string): string {
  const text = raw.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
  return text.length > 4 ? `${text.slice(0, 4)}-${text.slice(4)}` : text;
}

export function LinkApp() {
  const { me, signedOut } = useShell();
  const [code, setCode] = useState("");
  const [state, setState] = useState<State>({ step: "enter" });

  const failed = (err: unknown, fallback: string) =>
    setState({ step: "error", message: err instanceof ApiError ? err.message : fallback });

  const check = async (value: string) => {
    if (!CODE_SHAPE.test(value)) {
      setState({ step: "error", message: "A code is 8 letters and numbers, like KDPX-7QHR." });
      return;
    }
    setState({ step: "checking" });
    try {
      setState({ step: "confirm", preview: await getPluginLink(value) });
    } catch (err) {
      failed(err, "Couldn't check that code. Try again.");
    }
  };

  const connect = async (preview: PluginLinkPreview) => {
    setState({ step: "connecting", preview });
    try {
      const made = await approvePluginLink(preview.code);
      setConnectedTo(preview.workspace || null);
      setState({ step: "done", client: made.connection.client });
    } catch (err) {
      failed(err, "Couldn't connect. Get a new code from the panel.");
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void check(code);
  };

  const workspace = state.step === "confirm" || state.step === "connecting" ? state.preview.workspace : null;
  const [connectedTo, setConnectedTo] = useState<string | null>(null);
  const here = "/studio/link";

  return (
    /* .zset: the settings pieces (buttons, fields, notices) are scoped under it */
    <main className="zset mx-auto w-full max-w-[600px]">
      <h1 className="text-xl font-semibold">Connect an app</h1>
      <p className="mt-1 text-sm opacity-70">
        Sign an editing app in to your Phantra studio, like the Phantra panel in Premiere Pro.
      </p>

      <div className="mt-6">
        {signedOut ? (
          <SettingsCard pad>
            <p className="text-sm">Sign in to Phantra first, then you&apos;ll come straight back here to connect.</p>
            <div className="mt-4">
              <Button variant="primary" onClick={() => goToSignIn(undefined, here)}>
                Sign in
              </Button>
            </div>
          </SettingsCard>
        ) : state.step === "done" ? (
          <SettingsCard pad>
            <Notice tone="ok">
              {state.client} is connected{connectedTo ? ` to ${connectedTo}` : ""}. Go back to it; it signs in on
              its own in a few seconds. You can close this page.
            </Notice>
          </SettingsCard>
        ) : state.step === "confirm" || state.step === "connecting" ? (
          <SettingsCard pad>
            <p className="text-sm opacity-70">Code</p>
            <p className="mt-1 font-mono text-2xl tracking-widest">{state.preview.code}</p>
            <p className="mt-4 text-sm">
              <b>{state.preview.client}</b>
              {state.preview.device ? ` (it says it's on ${state.preview.device})` : ""} wants to use your studio
              {workspace ? (
                <>
                  {" "}
                  <b>{workspace}</b>
                </>
              ) : null}
              : your Library, projects and elements, and making images and video on your credits. Every render
              still shows its price and waits for you to press Approve in the panel.
            </p>
            <div className="mt-4">
              <Notice>
                Only connect a code your own Premiere panel is showing you right now. If someone sent you a
                code or asked you to enter one, don&apos;t connect it: it would give them your studio.
              </Notice>
            </div>
            <div className="mt-4 flex gap-2">
              <Button
                variant="primary"
                disabled={state.step === "connecting"}
                onClick={() => void connect(state.preview)}
              >
                {state.step === "connecting" ? "Connecting…" : `Connect ${state.preview.client}`}
              </Button>
              <Button onClick={() => setState({ step: "enter" })}>Cancel</Button>
            </div>
          </SettingsCard>
        ) : (
          <SettingsCard pad>
            <form onSubmit={submit}>
              <label htmlFor="link-code" className="text-sm">
                The code your panel shows
              </label>
              <div className="mt-2 flex gap-2">
                <Field
                  id="link-code"
                  value={code}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="KDPX-7QHR"
                  onChange={(e) => setCode(tidy(e.target.value))}
                  className="font-mono tracking-widest"
                />
                <Button type="submit" variant="primary" disabled={state.step === "checking" || !me?.account}>
                  {state.step === "checking" ? "Checking…" : "Continue"}
                </Button>
              </div>
            </form>
            {state.step === "error" ? (
              <div className="mt-4">
                <Notice tone="err">{state.message}</Notice>
              </div>
            ) : null}
          </SettingsCard>
        )}
      </div>
    </main>
  );
}
