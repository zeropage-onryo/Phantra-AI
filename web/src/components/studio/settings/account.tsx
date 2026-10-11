"use client";

/* Settings → Account (2026-10-03, Mike: "Supabase didn't send a code or
   allow a new user to create a password ... we need to build out settings
   and password change etc").

   Who the person is (the name the shell shows, the address) and how they
   sign in (set a first password, or change it). Every password or email
   write re-proves them first -- proof.tsx says why. Nothing here spends. */
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { signOut } from "@/lib/api";
import {
  changeEmail,
  getSecurity,
  sendSecurityCode,
  setPassword,
  updateMe,
  type Me,
  type Proof,
  type Security,
} from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { ProofFields } from "@/components/studio/settings/proof";
import {
  Button,
  Field,
  Notice,
  Row,
  SectionHeader,
  SettingsCard,
  SkeletonRows,
  errorText,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "account")!;

export function AccountSection() {
  const { me, toast } = useShell();
  const [security, setSecurity] = useState<Security | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // profile
  const [name, setName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<Me | null>(null);

  // the one code send serves both writes
  const [sending, setSending] = useState(false);
  const [codeSentTo, setCodeSentTo] = useState<string | null>(null);

  // password
  const [pw, setPw] = useState({ password: "", password2: "" });
  const [pwProof, setPwProof] = useState<Proof>({});
  const [pwBusy, setPwBusy] = useState(false);
  const [pwDone, setPwDone] = useState<string | null>(null);

  // email
  const [newEmail, setNewEmail] = useState("");
  const [emailProof, setEmailProof] = useState<Proof>({});
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailNote, setEmailNote] = useState<string | null>(null);

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

  const who = saved ?? me;
  const displayName = name ?? who?.user.display_name ?? "";

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const next = await updateMe(displayName);
      setSaved(next);
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

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!security) return;
    if (pw.password !== pw.password2) return toast("The two passwords don’t match", "err");
    if (pw.password.length < security.min_password_len)
      return toast(`A password needs at least ${security.min_password_len} characters`, "err");
    setPwBusy(true);
    try {
      const res = await setPassword(pw.password, pw.password2, pwProof);
      setSecurity({ ...security, ...res });
      setPw({ password: "", password2: "" });
      setPwProof({});
      setCodeSentTo(null);
      setPwDone(security.has_password ? "Password changed." : "Password set — you can log in with it now.");
      toast("Password saved");
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
      setEmailNote(`Confirmation sent for ${res.pending}: ${res.note}.`);
      setNewEmail("");
      setEmailProof({});
      setCodeSentTo(null);
      toast("Confirmation email sent");
    } catch (err) {
      toast(errorText(err, "Could not change the email"), "err");
    } finally {
      setEmailBusy(false);
    }
  };

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

      <SettingsCard title="Profile" description="what the studio calls you">
        <form onSubmit={saveName}>
          <Row
            label="Name"
            htmlFor="display-name"
            hint={
              <>
                Signed in as <b>{who?.user.email ?? "—"}</b>
              </>
            }
            control={
              <>
                <Field
                  id="display-name"
                  style={{ width: 220 }}
                  value={displayName}
                  maxLength={80}
                  placeholder={who?.user.email?.split("@")[0] ?? ""}
                  onChange={(e) => setName(e.target.value)}
                />
                <Button type="submit" variant="primary" disabled={saving || name === null}>
                  {saving ? "Saving…" : "Save"}
                </Button>
              </>
            }
          />
        </form>
      </SettingsCard>

      <SettingsCard
        title={security?.has_password ? "Change password" : "Set a password"}
        description={
          security
            ? security.has_password
              ? "you log in with a password"
              : "add a password to log in with it too"
            : undefined
        }
      >
        {security && !security.can_change ? (
          <Row
            label="Password"
            hint="Sign-in isn’t configured on this server, so passwords can’t be changed here."
          />
        ) : security ? (
          <form onSubmit={savePassword} className="zset-card-pad" style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
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
            <ProofFields
              security={security}
              proof={pwProof}
              onChange={setPwProof}
              onSendCode={sendCode}
              sending={sending}
              codeSentTo={codeSentTo}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <Button type="submit" variant="primary" disabled={pwBusy || !(pwProof.current_password || pwProof.code)}>
                {pwBusy ? "Saving…" : security.has_password ? "Change password" : "Set password"}
              </Button>
              {pwDone ? <span className="zset-note">{pwDone}</span> : null}
            </div>
          </form>
        ) : !loadError ? (
          <SkeletonRows rows={2} />
        ) : null}
      </SettingsCard>

      <SettingsCard title="Email" description="where codes and receipts go">
        {security?.can_change ? (
          <form onSubmit={saveEmail} className="zset-card-pad" style={{ display: "grid", gap: 14 }}>
            <div>
              <label className="zset-label" htmlFor="new-email">
                New address
              </label>
              <Field
                id="new-email"
                type="email"
                autoComplete="email"
                required
                placeholder={security.email ?? ""}
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
            <div>
              <Button
                type="submit"
                variant="primary"
                disabled={emailBusy || !newEmail || !(emailProof.current_password || emailProof.code)}
              >
                {emailBusy ? "Sending…" : "Change email"}
              </Button>
            </div>
            <p className="zset-note">
              {emailNote ??
                "You’ll get a confirmation email at the new address (and the old one). The change takes effect once it’s confirmed and you sign in again."}
            </p>
          </form>
        ) : security ? (
          <Row label="Address" hint={security.email ?? "—"} />
        ) : !loadError ? (
          <SkeletonRows rows={1} />
        ) : null}
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
