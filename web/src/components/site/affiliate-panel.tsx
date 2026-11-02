"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { AUTH_ORIGIN } from "@/lib/api";
import { AFFILIATE_TERMS, applyAffiliate, dollars, loadAffiliate, type AffiliateSummary } from "@/lib/affiliate";

type View = { phase: "loading" } | { phase: "sign-in" } | { phase: "error"; message: string } | { phase: "ok"; summary: AffiliateSummary };

const field =
  "w-full rounded-md border border-border bg-transparent px-3 py-2.5 text-[15px] text-foreground placeholder:text-[#6f6f6f] focus:outline-none focus:ring-1 focus:ring-foreground/40";

function signIn() {
  const next = encodeURIComponent(`${window.location.origin}/affiliates`);
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `${AUTH_ORIGIN}/signin?next=${next}`;
}

// The page's live half: apply when signed in and not yet a partner, the
// link and the numbers once approved. Every number shown is the server's.
export function AffiliatePanel() {
  const [view, setView] = useState<View>({ phase: "loading" });
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [form, setForm] = useState({ channel_url: "", audience: "", plan: "", accept_terms: false });

  useEffect(() => {
    let live = true;
    loadAffiliate().then((r) => {
      if (!live) return;
      if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
      else if (r.kind === "sign-in") setView({ phase: "sign-in" });
      else setView({ phase: "error", message: r.message });
    });
    return () => {
      live = false;
    };
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNote("");
    const r = await applyAffiliate(form);
    setBusy(false);
    if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
    else if (r.kind === "sign-in") setView({ phase: "sign-in" });
    else setNote(r.message);
  }

  if (view.phase === "loading") return <p className="text-[#afafaf]">Loading…</p>;
  if (view.phase === "error") return <p className="text-[#afafaf]">{view.message}</p>;

  if (view.phase === "sign-in") {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-[17px] leading-relaxed text-[#afafaf]">
          Sign in (or create a free account) to apply. Your Phantra account is where your link, your referrals and your
          earnings live.
        </p>
        <Button onClick={signIn}>Sign in to apply</Button>
      </div>
    );
  }

  const s = view.summary;
  if (s.status === "pending") {
    return (
      <p className="text-[17px] leading-relaxed text-[#afafaf]">
        Your application is in. A person reads every one and replies by email, usually within two working days.
      </p>
    );
  }
  if (s.status === "rejected") {
    return (
      <p className="text-[17px] leading-relaxed text-[#afafaf]">
        We couldn’t approve this application. If you think we got it wrong, write to us from the Support page.
      </p>
    );
  }
  if (s.status === "suspended") {
    return (
      <p className="text-[17px] leading-relaxed text-[#afafaf]">
        Your partner account is paused. Write to us from the Support page and we’ll sort it out.
      </p>
    );
  }
  if (s.status === "approved") {
    const e = s.earnings;
    return (
      <div className="space-y-6 text-[17px] leading-relaxed text-[#afafaf]">
        <div>
          <p className="eyebrow">Your link</p>
          <p className="mt-2 break-all font-mono text-foreground">{s.link}</p>
        </div>
        <p>
          You’re on <span className="text-foreground">{s.tier?.label}</span> — {s.tier?.percent}% for {s.tier?.months} months of each
          referral’s payments. {s.signups} signed up, {s.paying_referrals} paying.
          {s.next_tier && s.next_tier.needs > 0 && (
            <> {s.next_tier.needs} more paying referral{s.next_tier.needs === 1 ? "" : "s"} unlocks {s.next_tier.label} ({s.next_tier.percent}% for {s.next_tier.months} months).</>
          )}
        </p>
        {e && (
          <p>
            Waiting out the {AFFILIATE_TERMS.hold_days}-day hold: <span className="text-foreground">{dollars(e.held_cents)}</span>. Paid:{" "}
            <span className="text-foreground">{dollars(e.paid_cents)}</span>
            {e.payable_cash_cents > 0 && <>. Cash ready to send: {dollars(e.payable_cash_cents)}</>}. Paid as{" "}
            {s.payout_mode === "cash" ? "cash" : "credits"}.
          </p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <label className="block">
        <span className="eyebrow">Your channel or profile</span>
        <input className={`${field} mt-2`} type="url" required placeholder="https://youtube.com/@you" value={form.channel_url}
          onChange={(e) => setForm({ ...form, channel_url: e.target.value })} />
      </label>
      <label className="block">
        <span className="eyebrow">Who watches you?</span>
        <textarea className={`${field} mt-2`} rows={3} required maxLength={600} placeholder="Filmmakers, bartenders, small brands… and roughly how many."
          value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} />
      </label>
      <label className="block">
        <span className="eyebrow">How would you share Phantra?</span>
        <textarea className={`${field} mt-2`} rows={3} required maxLength={600} placeholder="A tutorial, a workflow video, a newsletter, your bio link…"
          value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })} />
      </label>
      <label className="flex items-start gap-3 text-[15px] text-[#afafaf]">
        <input type="checkbox" className="mt-1" checked={form.accept_terms}
          onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })} />
        <span>I’ve read the program terms above and I’ll follow them.</span>
      </label>
      {note && <p role="alert" className="text-[15px] text-[#e8a3a3]">{note}</p>}
      <Button type="submit" disabled={busy || !form.accept_terms}>{busy ? "Sending…" : "Apply"}</Button>
    </form>
  );
}
