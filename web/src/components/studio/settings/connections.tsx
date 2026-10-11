"use client";

/* Settings → Connections (2026-10-11): what is connected to this studio
   from outside it.

   - Claude: the connector (the studio as tools inside Claude). The same
     body the account menus' dialog draws -- components/studio/
     connect-claude.tsx is the one source. Connecting and disconnecting
     both happen on claude.ai; this says where and deletes nothing.
   - Your own model logins: a person's ChatGPT or Claude plan, signed in on
     the studio server (app/model_connections.py). Listed, signed in and
     disconnected with the calls the classic studio's Guide makes.

   WHAT A MODEL LOGIN DOES TODAY is said on the card, because it is
   narrower than the card might suggest: only the classic studio's Guide
   can answer with one. Create and the assistant here always run on the
   studio's own model. Nothing on this page spends. */
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { ExternalLink, Plug } from "lucide-react";
import {
  getModelConnection,
  getModelConnections,
  modelDisconnect,
  modelSignIn,
  type ModelConnection,
  type ModelProvider,
} from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { ConnectClaudeBody } from "@/components/studio/connect-claude";
import {
  Badge,
  Button,
  EmptyState,
  Notice,
  Row,
  SectionHeader,
  SettingsCard,
  SkeletonRows,
  buttonClass,
  errorText,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "connections")!;

const PROVIDERS: { id: ModelProvider; name: string }[] = [
  { id: "chatgpt", name: "ChatGPT" },
  { id: "claude", name: "Claude" },
];
const POLL_MS = 2500;
const WAIT_MS = 5 * 60_000;

/** The provider's own sign-in page, or null: only an https address on the
 *  one host a ChatGPT device sign-in lives on is ever made a link. */
function challengeOf(login: ModelConnection["login"]): { url: string; code: string } | null {
  if (!login || typeof login !== "object") return null;
  try {
    const url = new URL(login.url);
    return url.protocol === "https:" && url.hostname === "auth.openai.com"
      ? { url: url.href, code: login.code || "" }
      : null;
  } catch {
    return null;
  }
}

function ModelLogins() {
  const { toast } = useShell();
  const [conns, setConns] = useState<Record<ModelProvider, ModelConnection> | null>(null);
  const [error, setError] = useState<string | null>(null);
  // a sign-in or a disconnect is on its way to the server
  const [busy, setBusy] = useState<ModelProvider | null>(null);
  // a sign-in was started and this page is watching for it to finish
  const [waiting, setWaiting] = useState<ModelProvider | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Watch a sign-in that was started: ask every POLL_MS until the provider
  // says connected, for at most WAIT_MS. One watch at a time.
  const watch = useCallback(
    (provider: ModelProvider, name: string) => {
      if (timer.current) clearInterval(timer.current);
      let left = Math.ceil(WAIT_MS / POLL_MS);
      const stop = () => {
        if (timer.current) clearInterval(timer.current);
        timer.current = null;
        setWaiting(null);
      };
      timer.current = setInterval(async () => {
        left -= 1;
        try {
          const status = await getModelConnection(provider);
          setConns((all) => (all ? { ...all, [provider]: status } : all));
          if (status.connected) {
            stop();
            toast(`${name} connected`);
          } else if (left <= 0) {
            stop();
            toast(`${name} sign-in has not finished. Start it again when you are ready.`, "err");
          }
        } catch (err) {
          stop();
          toast(errorText(err, `Could not check the ${name} sign-in`), "err");
        }
      }, POLL_MS);
    },
    [toast],
  );

  const load = useCallback(() => {
    getModelConnections()
      .then((all) => {
        setConns(all);
        setError(null);
        // a sign-in started earlier (another tab, a reload) is still under way
        const under = PROVIDERS.find((p) => all[p.id]?.login && !all[p.id]?.connected);
        if (under && !timer.current) {
          setWaiting(under.id);
          watch(under.id, under.name);
        }
      })
      .catch((err) => setError(errorText(err, "Could not read your model logins")));
  }, [watch]);
  useEffect(() => {
    load();
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [load]);

  const signIn = async (provider: ModelProvider, name: string) => {
    setBusy(provider);
    try {
      const started = await modelSignIn(provider);
      const login = started.url ? { url: started.url, code: started.code || "" } : true;
      if (started.url && !challengeOf(login)) throw new Error("The provider returned an unexpected sign-in address.");
      setConns((all) => (all ? { ...all, [provider]: { ...all[provider], login, message: started.message } } : all));
      setWaiting(provider);
      watch(provider, name);
    } catch (err) {
      toast(errorText(err, `Could not start the ${name} sign-in`), "err");
    } finally {
      setBusy(null);
    }
  };

  const disconnect = async (provider: ModelProvider, name: string) => {
    setBusy(provider);
    try {
      await modelDisconnect(provider);
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
      setWaiting(null);
      toast(`${name} disconnected`);
      load();
    } catch (err) {
      toast(errorText(err, `Could not disconnect ${name}`), "err");
    } finally {
      setBusy(null);
    }
  };

  if (error && !conns)
    return (
      <div className="zset-card-pad">
        <Notice tone="err">
          {error}{" "}
          <button type="button" className="zset-link" onClick={load}>
            Try again
          </button>
        </Notice>
      </div>
    );
  if (!conns) return <SkeletonRows rows={2} />;
  if (PROVIDERS.every((p) => conns[p.id]?.available === false))
    return (
      <EmptyState icon={Plug} title="No model logins on this studio">
        This studio answers with its own model. Signing in with your own ChatGPT or Claude plan is not set up here.
      </EmptyState>
    );

  return (
    <>
      {PROVIDERS.map(({ id, name }) => {
        const c = conns[id] ?? { available: false, connected: false };
        const challenge = challengeOf(c.login);
        const pending = !!c.login && !c.connected;
        const canSignIn = c.available && c.can_sign_in !== false;
        return (
          <Fragment key={id}>
            <Row
              label={
                <span className="zset-ws">
                  {name}
                  {c.connected ? (
                    <Badge tone="ok">Connected</Badge>
                  ) : pending ? (
                    <Badge tone="warn">Signing in</Badge>
                  ) : !c.available ? (
                    <Badge>Not available</Badge>
                  ) : null}
                </span>
              }
              hint={
                c.connected
                  ? `${c.plan ? `On your ${c.plan} plan. ` : ""}${c.billing ?? ""}`.trim() || "Signed in."
                  : !c.available
                    ? `${name} sign-in is not set up on this studio.`
                    : c.message || c.billing || "Not connected."
              }
              control={
                <>
                  {!c.connected && c.available ? (
                    <Button
                      variant={pending ? "ghost" : "primary"}
                      disabled={!canSignIn || busy !== null || (waiting !== null && waiting !== id)}
                      onClick={() => signIn(id, name)}
                    >
                      {busy === id ? "Starting…" : pending ? "Start again" : "Sign in"}
                    </Button>
                  ) : null}
                  {c.connected || pending ? (
                    <Button disabled={busy !== null} onClick={() => disconnect(id, name)}>
                      {c.connected ? "Disconnect" : "Cancel"}
                    </Button>
                  ) : null}
                </>
              }
            />
            {pending && challenge ? (
              <div className="zset-sub">
                <div className="zset-proof" role="status">
                  <span className="zset-label">Finish on {name}’s own page</span>
                  <p className="zset-note">
                    Open the sign-in page, enter this code, and approve. This page updates when it is done.
                  </p>
                  <div className="zset-actions">
                    <code className="zset-codebox">{challenge.code}</code>
                    <a
                      className={buttonClass}
                      data-variant="primary"
                      href={challenge.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open the sign-in page <ExternalLink strokeWidth={1.7} aria-hidden />
                    </a>
                  </div>
                </div>
              </div>
            ) : null}
          </Fragment>
        );
      })}
      <p className="zset-note zset-foot">
        Optional. A login here is used by the Guide in the classic studio, which can answer with your own plan. Create
        and the assistant on these pages run on the studio’s own model and do not use it.
      </p>
    </>
  );
}

export function ConnectionsSection() {
  const { me, toast } = useShell();
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard title="Claude" description="your studio, as tools inside Claude" pad>
        <ConnectClaudeBody me={me} toast={toast} />
      </SettingsCard>
      <SettingsCard title="Your own model logins" description="your ChatGPT or Claude plan">
        <ModelLogins />
      </SettingsCard>
    </>
  );
}
