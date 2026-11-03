"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AUTH_ORIGIN } from "@/lib/api";
import { applyCreator, loadCreator, type CreatorSummary } from "@/lib/creators";
import { MARIGOLD } from "@/components/site/marigold";

const OPEN = "phantra:creator-apply";

/** Any "Apply" on the page: it asks the one dialog below to open. */
export function CreatorApplyButton({ children = "Apply", className = "" }: { children?: ReactNode; className?: string }) {
  return (
    <button type="button" className={className} onClick={() => window.dispatchEvent(new Event(OPEN))}>
      {children}
    </button>
  );
}

type View = { phase: "loading" } | { phase: "sign-in" } | { phase: "error"; message: string } | { phase: "ok"; summary: CreatorSummary };

const field =
  "w-full rounded-[10px] bg-secondary px-4 py-3 text-[16px] text-foreground placeholder:text-[#6f6f6f] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--mari,#F3F48B)]";
const label = "mb-2 block text-[15px] text-foreground";
const body = "text-[16px] leading-relaxed text-[#afafaf]";

function signIn() {
  const next = encodeURIComponent(`${window.location.origin}/creators?apply=1`);
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `${AUTH_ORIGIN}/signin?next=${next}`;
}

/** The application, and then where it stands, in one dialog. */
export function CreatorModal() {
  const ref = useRef<HTMLDialogElement>(null);
  const [view, setView] = useState<View>({ phase: "loading" });
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [form, setForm] = useState({
    first: "",
    last: "",
    country: "",
    channel_url: "",
    more_links: "",
    what_you_make: "",
    contribute: "",
    accept_terms: false,
  });

  const open = useCallback(() => {
    const d = ref.current;
    if (!d) return;
    if (!d.open) d.showModal();
    setView({ phase: "loading" });
    loadCreator().then((r) => {
      if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
      else if (r.kind === "sign-in") setView({ phase: "sign-in" });
      else setView({ phase: "error", message: r.message });
    });
  }, []);

  useEffect(() => {
    window.addEventListener(OPEN, open);
    // back from sign-in: /creators?apply=1 reopens the dialog
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
    const r = await applyCreator({
      channel_url: form.channel_url,
      what_you_make: form.what_you_make,
      accept_terms: form.accept_terms,
      full_name: `${form.first} ${form.last}`.trim(),
      country: form.country,
      more_links: form.more_links,
      contribute: form.contribute,
    });
    setBusy(false);
    if (r.kind === "ok") setView({ phase: "ok", summary: r.summary });
    else if (r.kind === "sign-in") setView({ phase: "sign-in" });
    else setNote(r.message);
  }

  let content: ReactNode;
  const s = view.phase === "ok" ? view.summary : null;
  let title = "Apply to Phantra Creators";

  if (view.phase === "loading") {
    content = <p className={body}>One moment…</p>;
  } else if (view.phase === "error") {
    content = <p className={body}>{view.message}</p>;
  } else if (view.phase === "sign-in") {
    content = (
      <div className="space-y-5">
        <p className={body}>
          Sign in, or create a free account, to apply. Creators work inside Phantra, so your application is tied to your account.
        </p>
        <button type="button" onClick={signIn} className={`h-12 w-full rounded-[10px] text-[16px] font-medium transition ${MARIGOLD}`}>
          Sign in to apply
        </button>
      </div>
    );
  } else if (s && s.status === "approved") {
    title = "You’re in";
    content = (
      <p className={body}>
        Welcome to Phantra Creators. We’ll email you with how to claim your credits and early access, and where the creator space is.
      </p>
    );
  } else if (s && s.status === "pending") {
    title = "Application received";
    content = (
      <p className={body}>
        We read every application and pick a small group. If there’s a fit, we’ll email you. Meanwhile, the open{" "}
        <Link href="/affiliates" className="text-foreground underline underline-offset-4">
          affiliate program
        </Link>{" "}
        is open to everyone.
      </p>
    );
  } else if (s && s.status === "rejected") {
    title = "Not this time";
    content = (
      <p className={body}>
        We aren’t able to offer a place right now. The open{" "}
        <Link href="/affiliates" className="text-foreground underline underline-offset-4">
          affiliate program
        </Link>{" "}
        is still yours to join, and you’re welcome to write to us from the Support page.
      </p>
    );
  } else {
    content = (
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className={label}>First name</span>
            <input className={field} autoComplete="given-name" value={form.first} onChange={(e) => setForm({ ...form, first: e.target.value })} />
          </label>
          <label className="block">
            <span className={label}>Last name</span>
            <input className={field} autoComplete="family-name" value={form.last} onChange={(e) => setForm({ ...form, last: e.target.value })} />
          </label>
        </div>
        <label className="block">
          <span className={label}>Where you share your work</span>
          <input
            className={field}
            type="url"
            required
            placeholder="https://instagram.com/you"
            value={form.channel_url}
            onChange={(e) => setForm({ ...form, channel_url: e.target.value })}
          />
        </label>
        <label className="block">
          <span className={label}>Other links (optional)</span>
          <input
            className={field}
            placeholder="A portfolio, a reel, another channel"
            value={form.more_links}
            onChange={(e) => setForm({ ...form, more_links: e.target.value })}
          />
        </label>
        <label className="block">
          <span className={label}>What do you make?</span>
          <textarea
            className={`${field} min-h-[110px] resize-y`}
            required
            minLength={20}
            placeholder="A sentence or two on your work and what you use AI for."
            value={form.what_you_make}
            onChange={(e) => setForm({ ...form, what_you_make: e.target.value })}
          />
        </label>
        <label className="block">
          <span className={label}>How would you use Phantra? (optional)</span>
          <textarea
            className={`${field} min-h-[88px] resize-y`}
            placeholder="A project you have in mind, or what you’d want to test first."
            value={form.contribute}
            onChange={(e) => setForm({ ...form, contribute: e.target.value })}
          />
        </label>
        <label className="block">
          <span className={label}>Your country or region (optional)</span>
          <input className={field} autoComplete="country-name" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
        </label>

        <div className="border-l border-border pl-4 text-[15px] leading-relaxed text-[#afafaf]">
          <p>
            Creators share work they make with Phantra in public, say when it’s part of the program, and give us honest feedback. We pick a small group and may
            end a place if these aren’t followed.
          </p>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-border p-4 text-[15px] text-foreground">
          <input
            type="checkbox"
            className="mt-1 size-4 accent-[var(--mari,#F3F48B)]"
            checked={form.accept_terms}
            onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })}
          />
          <span>I agree to the above, and that applying doesn’t guarantee a place.</span>
        </label>

        {note && (
          <p role="alert" className="text-[15px] text-[#f0a9a9]">
            {note}
          </p>
        )}
        <button
          type="submit"
          disabled={busy || !form.accept_terms || !form.channel_url || form.what_you_make.trim().length < 20}
          className={`h-12 w-full rounded-[10px] text-[16px] font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${MARIGOLD}`}
        >
          {busy ? "Sending…" : "Send application"}
        </button>
      </form>
    );
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby="creator-modal-title"
      onClick={(e) => {
        if (e.target === ref.current) ref.current?.close();
      }}
      className="m-auto max-h-[92vh] w-[min(92vw,540px)] overflow-y-auto rounded-[20px] border border-border bg-card p-0 text-foreground shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)] backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <div className="p-6 sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <h2 id="creator-modal-title" className="serif text-[26px]">
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
