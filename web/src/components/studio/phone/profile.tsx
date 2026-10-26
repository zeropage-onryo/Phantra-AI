"use client";

/* The Profile tab (/studio/me, 2026-10-26): who you are, your credits and
   the account doors, in one column. It is the phone's home for what the
   desktop keeps in the header (the credit pill, the avatar menu); on a
   desktop the page works the same, centred. Nothing here spends: Add
   credits opens the plan page, where Stripe does. */
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { goToSignIn, signOut } from "@/lib/api";
import { TOP_UP_HREF } from "@/lib/out-of-credits";
import { SETTINGS_ROOT } from "@/lib/settings-sections";
/* eslint-disable @next/next/no-img-element -- the person's own avatar, any host their sign-in gave */

const ROWS: [string, string][] = [
  [`${SETTINGS_ROOT}/plan`, "Plan and billing"],
  [`${SETTINGS_ROOT}/usage`, "Usage"],
  [`${SETTINGS_ROOT}/connections`, "Connections"],
  [`${SETTINGS_ROOT}/workspace`, "Workspace"],
  [`${SETTINGS_ROOT}/account`, "Settings"],
  ["/faq", "Help"],
];

export function ProfilePage() {
  const { me, signedOut, balance } = useShell();

  if (signedOut) {
    return (
      <section className="view ph-me">
        <h1 className="ph-me-h">Your studio</h1>
        <p className="ph-me-line">Sign in to see your work, your credits and your plan.</p>
        <button type="button" className="ph-go" onClick={() => goToSignIn("signup", "/studio/me")}>
          Sign up free
        </button>
        <button type="button" className="ph-ghost" onClick={() => goToSignIn(undefined, "/studio/me")}>
          Log in
        </button>
      </section>
    );
  }

  const who = me?.user.display_name || me?.user.email || "";
  const initial = (who.trim()[0] || "P").toUpperCase();
  const plan = balance?.plan?.name ? `${balance.plan.name} plan` : balance ? "Free trial" : "";
  const credits = balance ? (balance.exempt ? "Not charged" : Math.max(balance.available, 0).toLocaleString("en-US")) : "—";

  return (
    <section className="view ph-me">
      <div className="ph-me-who">
        <span className="ph-me-avatar" aria-hidden>
          {me?.user.avatar_url ? <img src={me.user.avatar_url} alt="" /> : initial}
        </span>
        <span className="ph-me-name">
          <b>{who || " "}</b>
          {plan ? <span>{plan}</span> : null}
        </span>
      </div>

      <div className="ph-me-credits">
        <span>
          <span className="ph-me-label">Credits</span>
          <b>{credits}</b>
        </span>
        <Link href={TOP_UP_HREF} className="ph-me-add">
          Add credits
        </Link>
      </div>

      <nav className="ph-me-list" aria-label="Account">
        {ROWS.map(([href, label]) => (
          <Link key={href} href={href}>
            {label}
            <ChevronRight strokeWidth={2.2} aria-hidden />
          </Link>
        ))}
      </nav>

      <button type="button" className="ph-me-out" onClick={signOut}>
        Log out
      </button>
    </section>
  );
}
