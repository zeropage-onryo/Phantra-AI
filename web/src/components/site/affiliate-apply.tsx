"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AUTH_ORIGIN } from "@/lib/api";
import { applyAffiliate, dollars, loadAffiliate, type AffiliateSummary } from "@/lib/affiliate";

import { MARIGOLD } from "@/components/site/marigold";

const OPEN = "phantra:affiliate-apply";

/** Any "Apply now" on the page: it asks the one modal below to open. */
export function ApplyButton({ children = "Apply now", className = "" }: { children?: ReactNode; className?: string }) {
  return (
    <button type="button" className={className} onClick={() => window.dispatchEvent(new Event(OPEN))}>
      {children}
    </button>
  );
}

type View = { phase: "loading" } | { phase: "sign-in" } | { phase: "error"; message: string } | { phase: "ok"; summary: AffiliateSummary };

const field =
  "w-full rounded-[10px] bg-secondary px-4 py-3 text-[16px] text-foreground placeholder:text-[#6f6f6f] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--mari,#FFC800)]";
const label = "mb-2 block text-[15px] text-foreground";
const body = "text-[16px] leading-relaxed text-[#afafaf]";

function signIn() {
  const next = encodeURIComponent(`${window.location.origin}/affiliates?apply=1`);
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `${AUTH_ORIGIN}/signin?next=${next}`;
}

/** The application, then the partner's link and numbers, in one dialog. */
export function AffiliateModal() {
  const ref = useRef<HTMLDialogElement>(null);
  const [view, setView] = useState<View>({ phase: "loading" });
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({ first: "", last: "", channel_url: "", country: "", accept_terms: false });

  const open = useCallback(() => {
    const d = ref.current;
    if (!d) return;
    if (!d.open) d.showModal();
    setView({ phase: "loading" });
    loadAffiliate().then((r) => {
      if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
      else if (r.kind === "sign-in") setView({ phase: "sign-in" });
      else setView({ phase: "error", message: r.message });
    });
  }, []);

  useEffect(() => {
    window.addEventListener(OPEN, open);
    // back from sign-in: /affiliates?apply=1 reopens the dialog
    const url = new URL(window.location.href);
    if (url.searchParams.get("apply") === "1") {
      url.searchParams.delete("apply");
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      open();
    }
    return () => window.removeEventListener(OPEN, open);
  }, [open]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNote("");
    const r = await applyAffiliate({
      channel_url: form.channel_url,
      accept_terms: form.accept_terms,
      full_name: `${form.first} ${form.last}`.trim(),
      country: form.country,
    });
    setBusy(false);
    if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
    else if (r.kind === "sign-in") setView({ phase: "sign-in" });
    else setNote(r.message);
  }

  function copy(text: string) {
    navigator.clipboard?.writeText(text).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {},
    );
  }

  let content: ReactNode;
  const s = view.phase === "ok" ? view.summary : null;

  if (view.phase === "loading") {
    content = <p className={body}>One moment…</p>;
  } else if (view.phase === "error") {
    content = <p className={body}>{view.message}</p>;
  } else if (view.phase === "sign-in") {
    content = (
      <div className="space-y-5">
        <p className={body}>Sign in, or create a free account, to apply. Your Phantra account is where your link, your referrals and your earnings live.</p>
        <button type="button" onClick={signIn} className={`h-12 w-full rounded-[10px] text-[16px] font-medium transition ${MARIGOLD}`}>
          Sign in to apply
        </button>
      </div>
    );
  } else if (s && s.status === "approved") {
    const e = s.earnings;
    content = (
      <div className="space-y-6">
        <div>
          <p className={label}>Your affiliate link</p>
          <div className="flex items-center gap-2 rounded-[10px] bg-secondary p-1.5 pl-4">
            <span className="min-w-0 flex-1 truncate font-mono text-[15px] text-foreground">{s.link}</span>
            <button
              type="button"
              onClick={() => copy(s.link ?? "")}
              className={`h-10 shrink-0 rounded-lg px-4 text-[15px] font-medium transition ${MARIGOLD}`}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>

        <div className="rounded-[14px] border border-border p-5">
          <p className="text-[17px] text-foreground">
            {s.tier?.label}: {s.tier?.percent}% for {s.tier?.months} months
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-[16px]">
            <dt className="text-[#afafaf]">Signed up</dt>
            <dd className="text-right tabular-nums text-foreground">{s.signups ?? 0}</dd>
            <dt className="text-[#afafaf]">Paying</dt>
            <dd className="text-right tabular-nums text-foreground">{s.paying_referrals ?? 0}</dd>
            {e && (
              <>
                <dt className="text-[#afafaf]">Waiting out the hold</dt>
                <dd className="text-right tabular-nums text-foreground">{dollars(e.held_cents)}</dd>
                <dt className="text-[#afafaf]">Paid to you</dt>
                <dd className="text-right tabular-nums text-foreground">{dollars(e.paid_cents)}</dd>
              </>
            )}
          </dl>
          {s.next_tier && s.next_tier.needs > 0 && (
            <p className="mt-4 text-[15px] leading-relaxed text-[#afafaf]">
              {s.next_tier.needs} more paying referral{s.next_tier.needs === 1 ? "" : "s"} unlocks {s.next_tier.label}: {s.next_tier.percent}% for{" "}
              {s.next_tier.months} months.
            </p>
          )}
        </div>

        <div className="flex items-center justify-between gap-4 rounded-[14px] border border-border p-5">
          <div>
            <p className="text-[16px] text-foreground">Have a large audience?</p>
            <p className="mt-1 text-[15px] text-[#afafaf]">Talk to us about a better rate.</p>
          </div>
          <Link href="/support" className="inline-flex h-10 shrink-0 items-center rounded-lg bg-foreground px-4 text-[15px] font-medium text-background">
            Contact us
          </Link>
        </div>
      </div>
    );
  } else if (s && s.status === "pending") {
    content = <p className={body}>Your application is in. We’ll email you once it’s reviewed.</p>;
  } else if (s && s.status === "rejected") {
    content = <p className={body}>We couldn’t approve this application. If you think we got it wrong, write to us from the Support page.</p>;
  } else if (s && s.status === "suspended") {
    content = <p className={body}>Your partner account is paused. Write to us from the Support page and we’ll sort it out.</p>;
  } else {
    content = (
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className={label}>First name</span>
            <input className={field} autoComplete="given-name" placeholder="Ana" value={form.first} onChange={(e) => setForm({ ...form, first: e.target.value })} />
          </label>
          <label className="block">
            <span className={label}>Last name</span>
            <input className={field} autoComplete="family-name" placeholder="Ruiz" value={form.last} onChange={(e) => setForm({ ...form, last: e.target.value })} />
          </label>
        </div>
        <label className="block">
          <span className={label}>Link to your main platform</span>
          <input
            className={field}
            type="url"
            required
            placeholder="https://youtube.com/@you"
            value={form.channel_url}
            onChange={(e) => setForm({ ...form, channel_url: e.target.value })}
          />
        </label>
        <label className="block">
          <span className={label}>Your country or region</span>
          <input className={field} autoComplete="country-name" placeholder="Start typing your country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
        </label>

        <div className="border-l border-border pl-4 text-[15px] leading-relaxed text-[#afafaf]">
          <p>
            <span className="text-foreground">Allowed:</span> organic promotion in your own content, like videos, posts, newsletters and communities. Say it’s an
            affiliate link wherever you share it.
          </p>
          <p className="mt-3">
            <span className="text-foreground">Not allowed:</span> paid ads pointing to Phantra, bidding on “Phantra” in search, posing as Phantra, advertising
            offers we haven’t given you, posting your link to coupon sites, referring yourself, and spam. Breaking these rules can mean withheld or reversed
            commission and a closed account.
          </p>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-border p-4 text-[15px] text-foreground">
          <input
            type="checkbox"
            className="mt-1 size-4 accent-[var(--mari,#FFC800)]"
            checked={form.accept_terms}
            onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })}
          />
          <span>I’ve read the affiliate program rules and agree to follow them.</span>
        </label>

        {note && (
          <p role="alert" className="text-[15px] text-[#f0a9a9]">
            {note}
          </p>
        )}
        <button
          type="submit"
          disabled={busy || !form.accept_terms || !form.channel_url}
          className={`h-12 w-full rounded-[10px] text-[16px] font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${MARIGOLD}`}
        >
          {busy ? "Creating your link…" : "Get my link"}
        </button>
      </form>
    );
  }

  const title = s && s.status === "approved" ? "You’re in" : "Affiliate program application";

  return (
    <dialog
      ref={ref}
      aria-labelledby="affiliate-modal-title"
      onClick={(e) => {
        if (e.target === ref.current) ref.current?.close();
      }}
      className="m-auto max-h-[92vh] w-[min(92vw,520px)] overflow-y-auto rounded-[20px] border border-border bg-card p-0 text-foreground shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)] backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <div className="p-6 sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <h2 id="affiliate-modal-title" className="serif text-[26px]">
            {title}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={() => ref.current?.close()}
            className="grid size-10 shrink-0 place-items-center rounded-full bg-secondary text-[20px] text-[#afafaf] transition hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground"
          >
            <span aria-hidden>×</span>
          </button>
        </div>
        {content}
      </div>
    </dialog>
  );
}
