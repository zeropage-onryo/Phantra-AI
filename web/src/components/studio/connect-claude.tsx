"use client";

/* "Connect MCP": the addresses to paste, the steps, and a way to the
   page on claude.ai where they happen. It connects nothing itself --
   claude.ai does that, and our consent page is where the person says yes.
   What it shows is lib/connect-claude's plan over /api/me, and -- once the
   person has pressed Allow, or Claude has used the connection -- the line
   GET /api/mcp/connection answers.

   ONE body, two frames (2026-10-11): `ConnectMcpBody` is what the panel
   says, drawn by the dialog the account menus open (`ConnectClaude`) and
   by Settings → Connections. Disconnecting is claude.ai's, so the body
   says where and deletes nothing. */
import { useEffect, useId, useState } from "react";
import { Check, CircleCheck, Copy, ExternalLink, X } from "lucide-react";
import {
  CLAUDE_CONNECTORS_URL,
  CONNECTOR_NAME,
  DESKTOP_COMMAND,
  claudeUrl,
  MANUAL_STEPS,
  connectPlan,
  connectedLine,
} from "@/lib/connect-claude";
import { getMcpConnection, type McpConnection, type Me } from "@/lib/studio-api";

type Toast = (text: string, kind?: "ok" | "err") => void;

export function ConnectMcpBody({ me, toast }: { me: Me | null; toast: Toast }) {
  const plan = connectPlan(me);
  const id = useId();
  const [copied, setCopied] = useState("");
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

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied((k) => (k === key ? "" : k)), 2000);
    } catch {
      // no clipboard (an http origin, a refused permission): the field is
      // selectable, so the person's own copy takes it
      toast("Select the text and press ⌘C", "err");
    }
  }

  const row = (key: string, name: string, badge: string, hint: string, text: string) => (
    <div className="zfield" key={key}>
      <label className="m" htmlFor={`${id}-${key}`}>
        {name} <span className="ccbadge">{badge}</span>
      </label>
      <p className="ccnote">{hint}</p>
      <div className="ccurl">
        <input
          id={`${id}-${key}`}
          className="zin"
          value={text}
          readOnly
          onFocus={(e) => e.currentTarget.select()}
        />
        <button type="button" className="zbtn" onClick={() => void copy(text, key)}>
          {copied === key ? <Check strokeWidth={1.8} /> : <Copy strokeWidth={1.8} />}
          {copied === key ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );

  return (
    <div className="ccbody">
      <p className="cclede">
        Use your studio from any app that speaks MCP: open your projects, write scenes, price renders, with your yes
        before anything spends.
      </p>

      {plan.mode === "off" ? (
        <p className="ccnote">MCP isn&apos;t switched on for this studio yet.</p>
      ) : (
        <>
          {line ? (
            <p className="ccstatus" role="status">
              <CircleCheck strokeWidth={1.8} /> {line}
            </p>
          ) : null}

          {row(
            "claude",
            "Claude",
            "writes and prices",
            "Renders are approved in the studio, through the link Claude gives you.",
            claudeUrl(plan.url),
          )}
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

          {row(
            "render",
            "ChatGPT and other MCP apps",
            "can render",
            "Also draws stills and approves renders from chat, always after a price in credits and your yes.",
            plan.url,
          )}

          {row(
            "desktop",
            "Claude Desktop",
            "runs on this Mac",
            "Quit Claude Desktop with ⌘Q first; the script registers the studio server and reopens it.",
            DESKTOP_COMMAND,
          )}

          <p className="ccnote">
            To disconnect, remove {CONNECTOR_NAME} in the app you added it to (in Claude:{" "}
            <a href={CLAUDE_CONNECTORS_URL} target="_blank" rel="noopener noreferrer">
              Customize → Connectors
            </a>
            ). Nothing here deletes a connection.
          </p>
        </>
      )}
    </div>
  );
}

/** the panel as a dialog, opened from either account menu */
export function ConnectMcp({ me, onClose, toast }: { me: Me | null; onClose: () => void; toast: Toast }) {
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
          <h3 id="cc-title">Connect MCP</h3>
          <span className="spacer" />
          <button type="button" className="zdx" onClick={onClose} aria-label="Close" autoFocus>
            <X strokeWidth={1.8} />
          </button>
        </div>
        <div className="zdbody">
          <ConnectMcpBody me={me} toast={toast} />
        </div>
      </div>
    </div>
  );
}
