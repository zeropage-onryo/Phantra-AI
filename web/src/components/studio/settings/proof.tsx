"use client";

/* The proof block every password and email write shares (2026-10-03).

   A password or email change has to be made AS the person against
   Supabase, and the API keeps no token of theirs -- so each write first
   re-proves them, and this offers the two proofs the API takes: the
   current password (when they have one) or a code mailed to the address on
   file. Somebody who signed up with Google or a sign-in code has no
   current password, and takes the code.

   The contract is `Proof` ({current_password} or {code}); only the look
   changes here. */
import { useId, useState } from "react";
import type { Proof, Security } from "@/lib/studio-api";
import { Button, Field } from "@/components/studio/settings/ui";

export function ProofFields({
  security,
  proof,
  onChange,
  onSendCode,
  sending,
  codeSentTo,
}: {
  security: Security;
  proof: Proof;
  onChange: (p: Proof) => void;
  onSendCode: () => void;
  sending: boolean;
  codeSentTo: string | null;
}) {
  const id = useId();
  // no password on file = the code is the only proof; with one, the
  // person picks (the password by default)
  const [pickedCode, setPickedCode] = useState(false);
  const useCode = security.has_password ? pickedCode : true;
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {security.has_password ? (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }} className="zset-note">
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="radio" checked={!useCode} onChange={() => setPickedCode(false)} />
            with my current password
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="radio" checked={useCode} onChange={() => setPickedCode(true)} />
            with a code from my email
          </label>
        </div>
      ) : null}
      {!useCode ? (
        <div>
          <label className="zset-label" htmlFor={`${id}-current`}>
            Current password
          </label>
          <Field
            id={`${id}-current`}
            type="password"
            autoComplete="current-password"
            value={proof.current_password ?? ""}
            onChange={(e) => onChange({ current_password: e.target.value })}
          />
        </div>
      ) : (
        <div>
          <label className="zset-label" htmlFor={`${id}-code`}>
            Code from your email
          </label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Field
              id={`${id}-code`}
              style={{ maxWidth: 180, letterSpacing: "0.3em" }}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              maxLength={10}
              value={proof.code ?? ""}
              onChange={(e) => onChange({ code: e.target.value.replace(/\D/g, "") })}
            />
            <Button disabled={sending} onClick={onSendCode}>
              {sending ? "Sending…" : codeSentTo ? "Send again" : "Email me a code"}
            </Button>
          </div>
          <p className="zset-note" style={{ marginTop: 6 }}>
            {codeSentTo
              ? `Sent to ${codeSentTo} — type the 6-digit code from that email.`
              : `We’ll mail a code to ${security.email ?? "your address"} to confirm it’s you.`}
          </p>
        </div>
      )}
    </div>
  );
}
