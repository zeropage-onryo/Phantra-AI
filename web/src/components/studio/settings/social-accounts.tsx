"use client";

/* Settings → Connections → Social accounts (2026-10-22, docs/tasks/
   task-social-connections.md): the person's own Instagram account and
   Discord channel (TikTok, YouTube, Facebook, LinkedIn, Reddit follow),
   connected through the platform's OWN consent screen.

   Connect is a top-level navigation to the API origin, the way sign-in
   goes (lib/api.ts): the platform redirects to one registered address and
   it has to be the server holding the app secret. The person comes back
   here with ?connected=<provider> (a toast), ?error=<words> (a toast, the
   provider's refusal in plain words) or ?pick=<id> (Discord: the server is
   connected, the channel is still to choose -- the picker opens on that
   row). No token ever reaches this page; a card shows a status word and
   the platform's own name for the account. Nothing here spends. */
/* eslint-disable @next/next/no-img-element -- the platform's own avatar, already small */
import { useCallback, useEffect, useState, type KeyboardEvent } from "react";
import { Link2 } from "lucide-react";
import { AUTH_ORIGIN } from "@/lib/api";
import {
  disconnectSocial,
  getSocialConnections,
  getSocialOptions,
  getSocialProviders,
  pickSocialOption,
  type SocialConnection,
  type SocialOption,
  type SocialProvider,
} from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { PostingTimesEditor } from "@/components/studio/settings/posting-times";
import { UrlParams } from "@/components/studio/url-params";
import {
  Badge,
  Button,
  EmptyState,
  Notice,
  SettingsCard,
  SkeletonRows,
  errorText,
  type Tone,
} from "@/components/studio/settings/ui";

const initialOf = (name: string) => (name.trim()[0] || "?").toUpperCase();

const STATUS: Record<SocialConnection["status"], { word: string; tone: Tone }> = {
  connected: { word: "Connected", tone: "ok" },
  pending: { word: "Pick a channel", tone: "warn" },
  reconnect: { word: "Reconnect", tone: "signal" },
  expired: { word: "Expired", tone: "signal" },
};

/** The verb on a provider's button: Discord adds a channel, the rest an account. */
const connectWord = (p: SocialProvider) => (p.pending_step === "channel" ? `Add a ${p.name} channel` : `Connect ${p.name}`);

/** The in-between step's words: Discord picks a channel, a LinkedIn Page connect picks a Page. */
const STEP_WORDS: Record<string, { noun: string; plural: string; none: string }> = {
  channel: {
    noun: "channel",
    plural: "channels",
    none: "The bot can post to no channel on this server yet. Give it a text channel it can see, then try again.",
  },
  page: { noun: "Page", plural: "Pages", none: "You hold no posting role on a LinkedIn Page yet." },
};
const stepWords = (step: string | null) => STEP_WORDS[step ?? ""] ?? STEP_WORDS.channel;

export function connectHref(p: Pick<SocialProvider, "start_url">) {
  return `${AUTH_ORIGIN}${p.start_url}`;
}

export function SocialAccounts() {
  const [timing, setTiming] = useState<number | null>(null);
  const { toast } = useShell();
  const [providers, setProviders] = useState<SocialProvider[] | null>(null);
  const [vaultReady, setVaultReady] = useState(true);
  const [rows, setRows] = useState<SocialConnection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picking, setPicking] = useState<number | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);

  const reload = useCallback(() => {
    getSocialConnections()
      .then((r) => {
        setRows(r.connections);
        setError(null);
      })
      .catch((err) => setError(errorText(err, "Could not read the connected accounts")));
  }, []);

  useEffect(() => {
    let gone = false;
    getSocialProviders()
      .then((r) => {
        if (gone) return;
        setProviders(r.providers);
        setVaultReady(r.vault_ready);
      })
      .catch((err) => !gone && setError(errorText(err, "Could not read the providers")));
    reload();
    return () => {
      gone = true;
    };
  }, [reload]);

  // what the API origin said on the way back, then a clean address
  const onParams = useCallback(
    (params: URLSearchParams) => {
      const connected = params.get("connected");
      const err = params.get("error");
      const pick = params.get("pick");
      if (!connected && !err && !pick) return;
      if (err) toast(err, "err");
      else if (connected && !pick) toast(`${providerName(connected)} connected`, "ok");
      if (pick && /^\d+$/.test(pick)) setPicking(Number(pick));
      if (connected || err) reload();
      const url = new URL(window.location.href);
      ["connected", "error", "pick", "id"].forEach((k) => url.searchParams.delete(k));
      window.history.replaceState(null, "", url.pathname + (url.search || ""));
    },
    [reload, toast],
  );

  const disconnect = (c: SocialConnection) => {
    if (confirming !== c.id) {
      setConfirming(c.id);
      return;
    }
    setConfirming(null);
    disconnectSocial(c.id)
      .then(() => {
        toast(`${c.provider_name} disconnected`, "ok");
        reload();
      })
      .catch((err) => toast(errorText(err, "Could not disconnect"), "err"));
  };

  const configured = (providers ?? []).filter((p) => p.configured);
  const unconfigured = (providers ?? []).filter((p) => !p.configured);

  return (
    <>
      <UrlParams onParams={onParams} />
      <SettingsCard
        title="Social accounts"
        description="where a finished clip can be posted from the studio, as you, once you say so"
      >
        {error ? (
          <div className="zset-card-pad">
            <Notice tone="err">{error}</Notice>
          </div>
        ) : rows === null ? (
          <SkeletonRows rows={2} />
        ) : rows.length === 0 ? (
          <EmptyState icon={Link2} title="No account connected yet">
            Connect one below. You sign in on the platform&apos;s own screen and choose what it may do; the
            studio keeps the key it hands back and never your password.
          </EmptyState>
        ) : (
          <ul className="zset-members">
            {rows.map((c) => (
              <li key={c.id}>
                <span className="zset-member-face" aria-hidden>
                  {c.avatar_url ? <img src={c.avatar_url} alt="" /> : initialOf(c.display_name || c.provider_name)}
                </span>
                <span className="zset-member-who">
                  <b>
                    {c.label || c.display_name}
                    <Badge tone={STATUS[c.status].tone}>
                      {c.status === "pending" ? `Pick a ${stepWords(c.pending).noun}` : STATUS[c.status].word}
                    </Badge>
                  </b>
                  <span>
                    {c.provider_name}
                    {c.handle ? ` · @${c.handle}` : ""}
                    {c.status === "connected" && c.expires_at ? ` · renews ${until(c.expires_at)}` : ""}
                  </span>
                  {timing === c.id ? (
                    <PostingTimesEditor
                      connection={c}
                      toast={toast}
                      onSaved={() => {
                        setTiming(null);
                        reload();
                      }}
                      onCancel={() => setTiming(null)}
                    />
                  ) : null}
                  {picking === c.id && c.status === "pending" ? (
                    <Picker
                      connection={c}
                      onDone={(done) => {
                        setPicking(null);
                        toast(`${done.label} connected`, "ok");
                        reload();
                      }}
                      onCancel={() => setPicking(null)}
                    />
                  ) : null}
                </span>
                <span className="zset-member-tags">
                  {c.status === "pending" && picking !== c.id ? (
                    <Button size="sm" variant="primary" onClick={() => setPicking(c.id)}>
                      Pick a {stepWords(c.pending).noun}
                    </Button>
                  ) : null}
                  {c.status !== "pending" && timing !== c.id ? (
                    <Button size="sm" onClick={() => setTiming(c.id)} title="The hours this account likes to post; the calendar's empty slots">
                      {Object.values(c.posting_times?.days ?? {}).flat().length ? "Posting times" : "Set posting times"}
                    </Button>
                  ) : null}
                  {c.status === "reconnect" || c.status === "expired" ? (
                    <Button size="sm" onClick={() => go(providers, c.provider)}>
                      Reconnect
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    variant={confirming === c.id ? "danger" : "quiet"}
                    onClick={() => disconnect(c)}
                    onBlur={() => confirming === c.id && setConfirming(null)}
                  >
                    {confirming === c.id ? "Disconnect for sure" : "Disconnect"}
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </SettingsCard>

      <SettingsCard title="Connect an account" pad>
        {providers === null ? (
          <SkeletonRows rows={2} />
        ) : (
          <>
            {!vaultReady ? (
              <Notice tone="err">This server has no secret to keep a token under yet (SOCIAL_TOKEN_SECRET).</Notice>
            ) : null}
            <div className="zset-social-grid">
              {configured.map((p) => (
                <a key={p.id} className="zset-social-tile" href={vaultReady ? connectHref(p) : undefined} aria-disabled={!vaultReady}>
                  <b>{connectWord(p)}</b>
                  <span>{p.connects}</span>
                </a>
              ))}
              {unconfigured.map((p) => (
                <span key={p.id} className="zset-social-tile" aria-disabled>
                  <b>{p.name}</b>
                  <span>not set up on this server yet</span>
                </span>
              ))}
            </div>
            <p className="zset-note zset-foot">
              Each platform asks you, on its own screen, what the studio may do. Posting still happens only
              from the review page, on your press.
            </p>
          </>
        )}
      </SettingsCard>
    </>
  );
}

function go(providers: SocialProvider[] | null, provider: string) {
  const p = providers?.find((x) => x.id === provider);
  if (p) window.location.href = connectHref(p);
}

function providerName(id: string) {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

function until(iso: string) {
  const days = Math.round((new Date(iso).getTime() - Date.now()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

/** The in-between step: Discord's server is connected, now which channel;
    a LinkedIn member is connected, now which Page. */
function Picker({
  connection,
  onDone,
  onCancel,
}: {
  connection: SocialConnection;
  onDone: (c: SocialConnection) => void;
  onCancel: () => void;
}) {
  const [options, setOptions] = useState<SocialOption[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [choice, setChoice] = useState("");
  const [saving, setSaving] = useState(false);
  const words = stepWords(connection.pending);

  useEffect(() => {
    let gone = false;
    getSocialOptions(connection.id)
      .then((r) => {
        if (gone) return;
        setOptions(r.options);
        if (r.options[0]) setChoice(r.options[0].id);
      })
      .catch((err) => !gone && setError(errorText(err, `Could not list the ${words.plural}`)));
    return () => {
      gone = true;
    };
  }, [connection.id, words.plural]);

  const save = () => {
    if (!choice) return;
    setSaving(true);
    pickSocialOption(connection.id, choice)
      .then(onDone)
      .catch((err) => {
        setSaving(false);
        setError(errorText(err, `Could not pick that ${words.noun}`));
      });
  };

  return (
    <div className="zset-social-pick">
      {error ? (
        <>
          <Notice tone="err">{error}</Notice>
          <Button variant="quiet" size="sm" onClick={onCancel}>
            Later
          </Button>
        </>
      ) : null}
      {options === null && !error ? (
        <SkeletonRows rows={1} />
      ) : options && options.length === 0 ? (
        <Notice>{words.none}</Notice>
      ) : options ? (
        <>
          <PickTiles options={options} value={choice} onChange={setChoice} label={words.noun} />
          <Button variant="primary" size="sm" onClick={save} disabled={saving || !choice}>
            {saving ? "Saving…" : `Use this ${words.noun}`}
          </Button>
          <Button variant="quiet" size="sm" onClick={onCancel} disabled={saving}>
            Later
          </Button>
        </>
      ) : null}
    </div>
  );
}

/** The choices as picture cards (a Page's logo, a channel's "#"), one
    radio group: arrows move the choice, as in a native radio group. */
function PickTiles({
  options,
  value,
  onChange,
  label,
}: {
  options: SocialOption[];
  value: string;
  onChange: (id: string) => void;
  label: string;
}) {
  const move = (e: KeyboardEvent<HTMLDivElement>) => {
    const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!delta) return;
    e.preventDefault();
    const at = options.findIndex((o) => o.id === value);
    const next = options[(at + delta + options.length) % options.length];
    onChange(next.id);
    e.currentTarget.querySelectorAll<HTMLButtonElement>("button")[options.indexOf(next)]?.focus();
  };
  return (
    <div className="zset-pick-tiles" role="radiogroup" aria-label={label} onKeyDown={move}>
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={o.id === value}
          tabIndex={o.id === value ? 0 : -1}
          className="zset-pick-tile"
          onClick={() => onChange(o.id)}
        >
          <span className="zset-pick-face" aria-hidden>
            {o.picture ? <img src={o.picture} alt="" /> : o.label.startsWith("#") ? "#" : initialOf(o.label)}
          </span>
          <b>{o.label.replace(/^#/, "")}</b>
          {o.hint ? <span>{o.hint}</span> : null}
        </button>
      ))}
    </div>
  );
}
