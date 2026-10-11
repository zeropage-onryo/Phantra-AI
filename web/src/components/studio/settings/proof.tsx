"use client";

/* The proof block every password and email write shares (2026-10-03).

   A password or email change has to be made AS the person against
   Supabase, and the API keeps no token of theirs -- so each write first
   re-proves them, and this offers the two proofs the API takes: the
   current password (when they have one) or a code mailed to the address on
   file. Somebody who signed up with Google or a sign-in code has no
   current password, and takes the code.

   The contract is `Proof` -- {current_password} or {code}, never both --
   and it has not changed; since 2026-10-11 the choice between the two is a
   segmented control instead of two radios. */
import { useId, useState } from "react";
import type { Proof, Security } from "@/lib/studio-api";
import { Button, Field, Segmented } from "@/components/studio/settings/ui";

type Way = "password" | "code";
const WAYS: { id: Way; label: string }[] = [
  { id: "password", label: "Current password" },
  { id: "code", label: "Email me a code" },
];

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
  const [picked, setPicked] = useState<Way>("password");
  const way: Way = security.has_password ? picked : "code";
  const pick = (next: Way) => {
    if (next === way) return;
    setPicked(next);
    // one proof at a time: what was typed for the other way is dropped,
    // so the form can never send a proof the person is no longer looking at
    onChange({});
  };

  return (
    <div className="zset-proof">
      <div className="zset-proof-head">
        <span className="zset-label" id={`${id}-how`}>
          Confirm it’s you
        </span>
        {security.has_password ? (
          <Segmented label="How to confirm it’s you" value={way} options={WAYS} onChange={pick} />
        ) : null}
      </div>
      {way === "password" ? (
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
          <div className="zset-proof-code">
            <Field
              id={`${id}-code`}
              className="zset-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              maxLength={10}
              aria-describedby={`${id}-code-hint`}
              value={proof.code ?? ""}
              onChange={(e) => onChange({ code: e.target.value.replace(/\D/g, "") })}
            />
            <Button disabled={sending} onClick={onSendCode}>
              {sending ? "Sending…" : codeSentTo ? "Send again" : "Send code"}
            </Button>
          </div>
          <p className="zset-note" id={`${id}-code-hint`} style={{ marginTop: 6 }}>
            {codeSentTo
              ? `Sent to ${codeSentTo} — type the 6-digit code from that email.`
              : `We’ll mail a code to ${security.email ?? "your address"} to confirm it’s you.`}
          </p>
        </div>
      )}
    </div>
  );
}

/** whether a proof has been offered at all (the submit button's gate) */
export const proven = (proof: Proof) => !!(proof.current_password || proof.code);
