"use client";

/* Settings → Account (2026-10-03, Mike: "Supabase didn't send a code or
   allow a new user to create a password ... we need to build out settings
   and password change etc"; laid out as rows 2026-10-11).

   Who the person is (the name the shell shows, the address) and how they
   sign in (set a first password, or change it). Every password or email
   write re-proves them first -- proof.tsx says why -- and the two forms
   open in place, one at a time. Nothing here spends.

   Not here on purpose: an avatar upload, "sign out everywhere" and
   deleting an account (docs/tasks/task-settings-page.md, task 9: each is
   its own decision). */
/* eslint-disable @next/next/no-img-element -- the provider's own avatar, already small */
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { signOut } from "@/lib/api";
import {
  changeEmail,
  getSecurity,
  sendSecurityCode,
  setPassword,
  updateMe,
  type Proof,
  type Security,
} from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { ProofFields, proven } from "@/components/studio/settings/proof";
import {
  Badge,
  Button,
  Field,
  Notice,
  Row,
  SectionHeader,
  SettingsCard,
  Skeleton,
  SkeletonRows,
  errorText,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "account")!;

const initialsOf = (who: string) =>
  who
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

const dayOf = (iso: string | null) => {
  const d = iso ? new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`) : null;
  return d && !Number.isNaN(d.getTime())
    ? d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "";
};

export function AccountSection() {
  const { me, refreshMe, toast } = useShell();
  const [security, setSecurity] = useState<Security | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // the two forms open in place, one at a time
  const [open, setOpen] = useState<"email" | "password" | null>(null);

  // profile
  const [name, setName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // the one code send serves both writes
  const [sending, setSending] = useState(false);
  const [codeSentTo, setCodeSentTo] = useState<string | null>(null);

  // password
  const [pw, setPw] = useState({ password: "", password2: "" });
  const [pwProof, setPwProof] = useState<Proof>({});
  const [pwBusy, setPwBusy] = useState(false);

  // email
  const [newEmail, setNewEmail] = useState("");
  const [emailProof, setEmailProof] = useState<Proof>({});
  const [emailBusy, setEmailBusy] = useState(false);
  const [pending, setPending] = useState<{ email: string; note: string } | null>(null);

  const load = useCallback(() => {
    getSecurity()
      .then((s) => {
        setSecurity(s);
        setLoadError(null);
      })
      .catch((err) => setLoadError(errorText(err, "Could not read your settings")));
  }, []);
  useEffect(() => {
    if (me) load();
  }, [me, load]);

  const current = me?.user.display_name ?? "";
  const displayName = name ?? current;
  const dirty = name !== null && name.trim() !== current;
  const email = security?.email ?? me?.user.email ?? null;

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    if (!dirty) return;
    setSaving(true);
    try {
      // the answer IS the new /api/me: the shell takes it, so the rail and
      // the avatar say the new name with this card, not after a reload
      await refreshMe(await updateMe(displayName));
      setName(null);
      toast("Name saved");
    } catch (err) {
      toast(errorText(err, "Could not save the name"), "err");
    } finally {
      setSaving(false);
    }
  };

  const sendCode = async () => {
    setSending(true);
    try {
      const res = await sendSecurityCode();
      setCodeSentTo(res.email);
      toast(`Code sent to ${res.email}`);
    } catch (err) {
      toast(errorText(err, "Could not send a code"), "err");
    } finally {
      setSending(false);
    }
  };

  const shut = () => {
    setOpen(null);
    setPw({ password: "", password2: "" });
    setPwProof({});
    setNewEmail("");
    setEmailProof({});
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!security) return;
    if (pw.password !== pw.password2) return toast("The two passwords don’t match", "err");
    if (pw.password.length < security.min_password_len)
      return toast(`A password needs at least ${security.min_password_len} characters`, "err");
    setPwBusy(true);
    try {
      const had = security.has_password;
      const res = await setPassword(pw.password, pw.password2, pwProof);
      setSecurity({ ...security, ...res });
      setCodeSentTo(null);
      shut();
      toast(had ? "Password changed" : "Password set — you can log in with it now");
    } catch (err) {
      toast(errorText(err, "Could not save the password"), "err");
    } finally {
      setPwBusy(false);
    }
  };

  const saveEmail = async (e: FormEvent) => {
    e.preventDefault();
    setEmailBusy(true);
    try {
      const res = await changeEmail(newEmail, emailProof);
      setPending({ email: res.pending, note: res.note });
      setCodeSentTo(null);
      shut();
      toast("Confirmation email sent");
    } catch (err) {
      toast(errorText(err, "Could not change the email"), "err");
    } finally {
      setEmailBusy(false);
    }
  };

  const label = current || email || "";

  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />

      {loadError ? (
        <Notice tone="err">
          {loadError}{" "}
          <button type="button" className="zset-link" onClick={load}>
            Try again
          </button>
        </Notice>
      ) : null}

      <SettingsCard title="Profile">
        <div className="zset-id">
          <span
            className="zset-avatar"
            style={me?.account?.accent ? { borderColor: me.account.accent } : undefined}
            aria-hidden
          >
            {me?.user.avatar_url ? <img src={me.user.avatar_url} alt="" /> : initialsOf(label) || "ZP"}
          </span>
          <div className="zset-id-text">
            {me ? (
              <>
                <b>{label || "—"}</b>
                <span>
                  {me.account ? `${me.account.label} · ${me.account.role || "member"}` : "No workspace yet"}
                </span>
              </>
            ) : (
              <>
                <Skeleton width={140} />
                <Skeleton width={190} height={10} />
              </>
            )}
          </div>
        </div>

        <form onSubmit={saveName}>
          <Row
            label="Name"
            htmlFor="display-name"
            hint="What the studio calls you."
            control={
              <>
                <Field
                  id="display-name"
                  className="zset-field-md"
                  value={displayName}
                  maxLength={80}
                  placeholder={email?.split("@")[0] ?? ""}
                  onChange={(e) => setName(e.target.value)}
                />
                {dirty ? (
                  <>
                    <Button type="submit" variant="primary" disabled={saving}>
                      {saving ? "Saving…" : "Save"}
                    </Button>
                    <Button variant="quiet" disabled={saving} onClick={() => setName(null)}>
                      Cancel
                    </Button>
                  </>
                ) : null}
              </>
            }
          />
        </form>

        <Row
          label="Email"
          hint={
            pending ? (
              <>
                Waiting on <b>{pending.email}</b>: {pending.note}.
              </>
            ) : (
              "Where codes and receipts go."
            )
          }
          control={
            <>
              <span className="zset-value">{email ?? <Skeleton width={150} />}</span>
              {pending ? <Badge tone="warn">Change pending</Badge> : null}
              {security?.can_change && open !== "email" ? (
                <Button
                  onClick={() => {
                    shut();
                    setOpen("email");
                  }}
                >
                  Change
                </Button>
              ) : null}
            </>
          }
        />
        {open === "email" && security ? (
          <form onSubmit={saveEmail} className="zset-sub">
            <div>
              <label className="zset-label" htmlFor="new-email">
                New address
              </label>
              <Field
                id="new-email"
                type="email"
                autoComplete="email"
                required
                autoFocus
                placeholder="you@example.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </div>
            <ProofFields
              security={security}
              proof={emailProof}
              onChange={setEmailProof}
              onSendCode={sendCode}
              sending={sending}
              codeSentTo={codeSentTo}
            />
            <p className="zset-note">
              You’ll get a confirmation email at the new address (and the old one). The change takes effect once it’s
              confirmed and you sign in again.
            </p>
            <div className="zset-actions">
              <Button type="submit" variant="primary" disabled={emailBusy || !newEmail || !proven(emailProof)}>
                {emailBusy ? "Sending…" : "Send confirmation"}
              </Button>
              <Button variant="quiet" disabled={emailBusy} onClick={shut}>
                Cancel
              </Button>
            </div>
          </form>
        ) : null}
      </SettingsCard>

      <SettingsCard title="Sign-in">
        {!security ? (
          loadError ? (
            <Row label="Sign-in methods" hint="Could not be read just now." />
          ) : (
            <SkeletonRows rows={2} />
          )
        ) : (
          <>
            <Row
              label="Sign-in methods"
              hint="A code to your email always works. A password is optional."
              control={
                <>
                  {security.has_password ? <Badge tone="ok">Password</Badge> : <Badge>No password</Badge>}
                  {security.can_change ? <Badge tone="ok">Emailed code</Badge> : null}
                </>
              }
            />
            <Row
              label="Password"
              hint={
                !security.can_change
                  ? "Sign-in isn’t configured on this server, so passwords can’t be changed here."
                  : security.has_password
                    ? `Set${dayOf(security.password_set_at) ? ` on ${dayOf(security.password_set_at)}` : ""}.`
                    : "None yet. Add one to log in with your email and a password too."
              }
              control={
                security.can_change && open !== "password" ? (
                  <Button
                    onClick={() => {
                      shut();
                      setOpen("password");
                    }}
                  >
                    {security.has_password ? "Change password" : "Set a password"}
                  </Button>
                ) : null
              }
            />
            {open === "password" ? (
              <form onSubmit={savePassword} className="zset-sub">
                <div className="zset-pair">
                  <div>
                    <label className="zset-label" htmlFor="new-password">
                      New password
                    </label>
                    <Field
                      id="new-password"
                      type="password"
                      autoComplete="new-password"
                      minLength={security.min_password_len}
                      required
                      autoFocus
                      aria-describedby="new-password-hint"
                      value={pw.password}
                      onChange={(e) => setPw({ ...pw, password: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="zset-label" htmlFor="new-password-2">
                      New password, again
                    </label>
                    <Field
                      id="new-password-2"
                      type="password"
                      autoComplete="new-password"
                      minLength={security.min_password_len}
                      required
                      value={pw.password2}
                      onChange={(e) => setPw({ ...pw, password2: e.target.value })}
                    />
                  </div>
                </div>
                <p className="zset-note" id="new-password-hint">
                  At least {security.min_password_len} characters.
                </p>
                <ProofFields
                  security={security}
                  proof={pwProof}
                  onChange={setPwProof}
                  onSendCode={sendCode}
                  sending={sending}
                  codeSentTo={codeSentTo}
                />
                <div className="zset-actions">
                  <Button type="submit" variant="primary" disabled={pwBusy || !proven(pwProof)}>
                    {pwBusy ? "Saving…" : security.has_password ? "Change password" : "Set password"}
                  </Button>
                  <Button variant="quiet" disabled={pwBusy} onClick={shut}>
                    Cancel
                  </Button>
                </div>
              </form>
            ) : null}
          </>
        )}
      </SettingsCard>

      <SettingsCard title="Sessions">
        <Row
          label="This device"
          hint="Signing out here leaves your other browsers signed in."
          control={<Button onClick={signOut}>Sign out of this device</Button>}
        />
      </SettingsCard>
    </>
  );
}
