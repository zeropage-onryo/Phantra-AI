"use client";

/* The out-of-credits popup (2026-11-10; lib/upgrade.ts says when it opens).
   Restyled 2026-11-12 after Higgsfield's pricing (Mike: "make the ui nicer
   looking like higgsfields"); upgrade-modal.css has the look.

   A workspace with no plan sees the three plans with a Monthly / Annual
   switch. Monthly carries the welcome offer (src/welcome_offer.py) struck
   through on the first month when the balance has one; Annual carries the
   yearly saving. Each button goes straight to Stripe Checkout, which applies
   the same discount server side, so the card and the charge agree. Every
   number is the catalog's (web/src/content/pricing.json): the prices, the
   credits, and what those credits buy. A workspace already on a plan is out
   of its month's credits, so it gets the top-up instead. */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { Check, Coins } from "lucide-react";
import { cardFonts } from "@/components/studio/card-fonts";
import { useShell } from "@/components/studio/shell";
import { CATALOG, MODELS, PLANS, TOPUP, discountPercent, num, type Interval, type Plan } from "@/lib/catalog";
import { startCheckout } from "@/lib/site-billing";
import {
  UPGRADE_EVENT,
  cardPrice,
  dollars,
  howMany,
  shouldOpen,
  type UpgradeReason,
  type WelcomeOffer,
} from "@/lib/upgrade";
import "@/components/studio/upgrade-modal.css";

// the card colour by plan: the popular plan is the signal, the top plan pink
const TIER: Record<string, "base" | "pro" | "max"> = { starter: "base", creator: "pro", studio: "max" };

// what a month's credits buy, named the way the model menu names them: the
// still on Nano Banana Pro, the clip on Seedance 2.5 (else the cheapest
// clip in the catalog, so a renamed row never prints a zero)
const STILL = { name: "Nano Banana Pro", credits: CATALOG.actions.still.pro };
const CLIP =
  MODELS.find((m) => m.name === "Seedance 2.5") ?? MODELS.reduce((a, b) => (a.credits <= b.credits ? a : b));

function features(plan: Plan): string[] {
  const talk = CATALOG.actions.talking_photo.max_seconds[plan.key];
  return [
    "Every AI video and image model",
    "No watermark, and past renders unmarked",
    ...(talk ? [`Talking photos up to ${talk}s`] : []),
    `${num(plan.storage_gb)} GB storage`,
    "Phantra in Claude and ChatGPT",
  ];
}

export function UpgradeModal() {
  const { balance, signedOut } = useShell();
  const [open, setOpen] = useState(false);
  const [interval, setBilling] = useState<Interval>("month");
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState("");
  const lastAuto = useRef<number | null>(null);
  // the popular plan's button takes focus, not the first one in the row
  const pick = useRef<HTMLButtonElement>(null);
  const balanceNow = useRef(balance);
  useEffect(() => {
    balanceNow.current = balance;
  }, [balance]);

  useEffect(() => {
    const onAsk = (e: Event) => {
      if (signedOut) return;
      const reason: UpgradeReason = (e as CustomEvent).detail?.reason === "clicked" ? "clicked" : "refused";
      const now = Date.now();
      if (!shouldOpen(reason, balanceNow.current, lastAuto.current, now)) return;
      if (reason === "refused") lastAuto.current = now;
      setFailed("");
      setBilling("month");
      setOpen(true);
    };
    window.addEventListener(UPGRADE_EVENT, onAsk);
    return () => window.removeEventListener(UPGRADE_EVENT, onAsk);
  }, [signedOut]);

  const buy = useCallback(async (item: string, at: Interval) => {
    setBusy(item);
    setFailed("");
    const out = await startCheckout(item, at);
    if (out.kind === "redirect") {
      window.location.href = out.url;
      return;
    }
    setBusy(null);
    setFailed(
      out.kind === "unconfigured"
        ? "Checkout isn't switched on yet. See the plans on the pricing page."
        : out.kind === "sign-in"
          ? "Your session ended. Sign in again to choose a plan."
          : out.message,
    );
  }, []);

  const onPlan = !!balance?.plan;
  const offer: WelcomeOffer | null = onPlan ? null : (balance?.welcome_offer ?? null);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o && !busy) setOpen(false);
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[950] bg-black/75 backdrop-blur-[2px]" />
        <Dialog.Popup
          // on a phone the focus would scroll the banner out of view
          initialFocus={() =>
            !onPlan && window.matchMedia("(min-width: 761px)").matches ? pick.current : false
          }
          className={`${cardFonts} upg fixed left-1/2 top-1/2 z-[951] -translate-x-1/2 -translate-y-1/2`}
        >
          <header className="upg-banner">
            <Dialog.Title render={<h2 />}>
              {onPlan ? (
                <>
                  <em>You&apos;re out of credits</em>
                  for this month
                </>
              ) : offer ? (
                <>
                  <em>Your free credits are used up</em>
                  Keep making with {offer.label}
                </>
              ) : (
                <>
                  <em>Your free credits are used up</em>
                  Pick a plan and keep making
                </>
              )}
            </Dialog.Title>
            <Dialog.Description render={<p />}>
              {onPlan
                ? `Top up ${num(TOPUP.credits)} credits now. They land on your balance right away, on top of your plan.`
                : "Every plan renders on every model with no watermark, and everything you've already made is unmarked once you pay."}
            </Dialog.Description>
          </header>

          {onPlan ? (
            <div className="upg-card" data-tier="pro">
              <div className="upg-head upg-topup">
                <div>
                  <div className="upg-name">{num(TOPUP.credits)} credits</div>
                  <div className="upg-note">
                    {dollars(Math.round(TOPUP.usd * 100))}, one time · ≈ {howMany(TOPUP.credits, CLIP.credits)} videos on{" "}
                    {CLIP.name}
                  </div>
                </div>
                <button type="button" className="upg-buy" disabled={!!busy} onClick={() => void buy(TOPUP.key, "month")}>
                  {busy ? "Opening checkout…" : "Buy credits"}
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="upg-bar">
                <div>
                  <h3>Choose your plan</h3>
                  <p>Cancel any time. Prices in US dollars.</p>
                </div>
                <div className="upg-switch" role="radiogroup" aria-label="Billing">
                  {(["month", "year"] as const).map((v) => (
                    <button
                      key={v}
                      type="button"
                      role="radio"
                      aria-checked={interval === v}
                      onClick={() => setBilling(v)}
                    >
                      {v === "month" ? "Monthly" : "Annual"}
                    </button>
                  ))}
                  <span className="upg-save">Save {discountPercent()}%</span>
                </div>
              </div>

              <div className="upg-grid">
                {PLANS.map((plan) => {
                  const price = cardPrice(plan, interval, offer);
                  const tier = TIER[plan.key] ?? (plan.popular ? "pro" : "base");
                  return (
                    <section key={plan.key} className="upg-card" data-tier={tier} aria-label={plan.name}>
                      <div className="upg-head">
                        <div className="upg-name">
                          {plan.name}
                          {plan.popular ? <span className="upg-badge">Most popular</span> : null}
                        </div>
                        <div className="upg-blurb">{plan.blurb}</div>
                        <div className="upg-price">
                          {price.wasCents ? <span className="upg-was">{dollars(price.wasCents)}</span> : null}
                          <span className="upg-now">{dollars(price.cents)}</span>
                          <span className="upg-per">/mo</span>
                        </div>
                        <div className="upg-note">{price.note}</div>
                        <button
                          ref={plan.popular ? pick : undefined}
                          type="button"
                          className="upg-buy"
                          disabled={!!busy}
                          onClick={() => void buy(plan.key, interval)}
                        >
                          {busy === plan.key ? "Opening checkout…" : `Get ${plan.name}`}
                          {price.chip && busy !== plan.key ? <span className="upg-chip">{price.chip}</span> : null}
                        </button>
                      </div>
                      <ul className="upg-gets">
                        <li className="upg-credits">
                          <Coins size={16} aria-hidden />
                          <b>{num(plan.credits)} credits</b> <span>/ month</span>
                        </li>
                        <li>
                          ≈ {num(howMany(plan.credits, STILL.credits))} images <span>{STILL.name}</span>
                        </li>
                        <li>
                          ≈ {num(howMany(plan.credits, CLIP.credits))} videos{" "}
                          <span>
                            {CLIP.name} · {CLIP.seconds}s
                          </span>
                        </li>
                      </ul>
                      <ul className="upg-feats">
                        <li className="upg-lab">Included in plan</li>
                        {features(plan).map((f) => (
                          <li key={f}>
                            <Check size={15} aria-hidden />
                            {f}
                          </li>
                        ))}
                      </ul>
                    </section>
                  );
                })}
              </div>
            </>
          )}

          {failed ? (
            <p className="upg-error" role="alert">
              {failed}
            </p>
          ) : null}
          <footer className="upg-foot">
            <Link href="/pricing" onClick={() => setOpen(false)}>
              {onPlan ? "Upgrade your plan instead" : "Compare all plans"}
            </Link>
            <Dialog.Close type="button" disabled={!!busy} className="upg-later">
              Not now
            </Dialog.Close>
          </footer>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
