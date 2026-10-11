"use client";

/* "Connect to Claude": the address to paste, the steps, and a way to the
   page on claude.ai where they happen. It connects nothing itself --
   claude.ai does that, and our consent page is where the person says yes.
   What it shows is lib/connect-claude's plan over /api/me, and -- once the
   person has pressed Allow, or Claude has used the connection -- the line
   GET /api/mcp/connection answers.

   ONE body, two frames (2026-10-11): `ConnectClaudeBody` is what the panel
   says, drawn by the dialog the account menus open (`ConnectClaude`) and
   by Settings → Connections. Disconnecting is claude.ai's, so the body
   says where and deletes nothing. */
import { useEffect, useId, useRef, useState } from "react";
import { Check, CircleCheck, Copy, ExternalLink, X } from "lucide-react";
import {
  CLAUDE_CONNECTORS_URL,
  CONNECTOR_NAME,
  MANUAL_STEPS,
  connectPlan,
  connectedLine,
} from "@/lib/connect-claude";
import { getMcpConnection, type McpConnection, type Me } from "@/lib/studio-api";

type Toast = (text: string, kind?: "ok" | "err") => void;

export function ConnectClaudeBody({ me, toast }: { me: Me | null; toast: Toast }) {
  const plan = connectPlan(me);
  const id = useId();
  const field = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);
  const [status, setStatus] = useState<McpConnection | null>(null);
  const live = plan.mode !== "off";

  useEffect(() => {
    if (!live) return;
    let gone = false;
    getMcpConnection()
      .then((s) => !gone && setStatus(s))
      // unknown is not "not connected": the line just stays away
      .catch(() => {});
    return () => {
      gone = true;
    };
  }, [live]);
  const line = connectedLine(status);

  async function copy() {
    if (plan.mode === "off") return;
    try {
      await navigator.clipboard.writeText(plan.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // no clipboard (an http origin, a refused permission): select the
      // address so the person's own copy takes it
      field.current?.select();
      toast("Press ⌘C to copy the address", "err");
    }
  }

  return (
    <div className="ccbody">
      <p className="cclede">
        Use your studio from Claude: read the board, write scenes, price and approve renders, with your yes before
        anything spends.
      </p>

      {plan.mode === "off" ? (
        <p className="ccnote">The Claude connector isn&apos;t switched on for this studio yet.</p>
      ) : (
        <>
          {line ? (
            <p className="ccstatus" role="status">
              <CircleCheck strokeWidth={1.8} /> {line}
            </p>
          ) : null}
          <div className="zfield">
            <label className="m" htmlFor={`${id}-url`}>
              Connector address
            </label>
            <div className="ccurl">
              <input
                id={`${id}-url`}
                ref={field}
                className="zin"
                value={plan.url}
                readOnly
                onFocus={(e) => e.currentTarget.select()}
              />
              <button type="button" className="zbtn" onClick={() => void copy()}>
                {copied ? <Check strokeWidth={1.8} /> : <Copy strokeWidth={1.8} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </div>

          {plan.mode === "directory" ? (
            <a className="zbtn pri ccgo" href={plan.listing} target="_blank" rel="noopener noreferrer">
              Add {CONNECTOR_NAME} in Claude <ExternalLink strokeWidth={1.8} />
            </a>
          ) : (
            <>
              <ol className="ccsteps">
                {MANUAL_STEPS.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <a className="zbtn pri ccgo" href={CLAUDE_CONNECTORS_URL} target="_blank" rel="noopener noreferrer">
                Open Claude connectors <ExternalLink strokeWidth={1.8} />
              </a>
            </>
          )}

          <p className="ccnote">
            Already connected? To disconnect, remove {CONNECTOR_NAME} in claude.ai under{" "}
            <a href={CLAUDE_CONNECTORS_URL} target="_blank" rel="noopener noreferrer">
              Customize → Connectors
            </a>
            .
          </p>
        </>
      )}
    </div>
  );
}

/** the panel as a dialog, opened from either account menu */
export function ConnectClaude({ me, onClose, toast }: { me: Me | null; onClose: () => void; toast: Toast }) {
  return (
    <div className="zmodal" onClick={onClose}>
      <div
        className="zdialog ccdialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cc-title"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
      >
        <div className="zdhead">
          <h3 id="cc-title">Connect to Claude</h3>
          <span className="spacer" />
          <button type="button" className="zdx" onClick={onClose} aria-label="Close" autoFocus>
            <X strokeWidth={1.8} />
          </button>
        </div>
        <div className="zdbody">
          <ConnectClaudeBody me={me} toast={toast} />
        </div>
      </div>
    </div>
  );
}
