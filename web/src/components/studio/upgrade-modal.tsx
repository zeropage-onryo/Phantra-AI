"use client";

/* The out-of-credits popup (2026-11-10; lib/upgrade.ts says when it opens).

   A workspace with no plan sees the three plans, monthly, with the welcome
   offer (src/welcome_offer.py) struck through on the first month when the
   balance carries one, and each button goes straight to Stripe Checkout,
   which applies the same coupon server side. A workspace already on a plan
   is out of its month's credits, so it gets the top-up instead. Yearly and
   the full comparison stay on /pricing, one link away. */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Dialog } from "@base-ui/react/dialog";
import { cardFonts } from "@/components/studio/card-fonts";
import { useShell } from "@/components/studio/shell";
import { PLANS, TOPUP, discountPercent, num } from "@/lib/catalog";
import { startCheckout } from "@/lib/site-billing";
import { UPGRADE_EVENT, dollars, firstMonthCents, shouldOpen, type UpgradeReason } from "@/lib/upgrade";

export function UpgradeModal() {
  const { balance, signedOut } = useShell();
  const [open, setOpen] = useState(false);
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
      setOpen(true);
    };
    window.addEventListener(UPGRADE_EVENT, onAsk);
    return () => window.removeEventListener(UPGRADE_EVENT, onAsk);
  }, [signedOut]);

  const buy = useCallback(async (item: string) => {
    setBusy(item);
    setFailed("");
    const out = await startCheckout(item, "month");
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
  const offer = onPlan ? null : (balance?.welcome_offer ?? null);
  const popular = PLANS.find((p) => p.popular)?.key;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o && !busy) setOpen(false);
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[950] bg-black/70" />
        <Dialog.Popup
          // the popular plan takes focus on a wide screen; on a phone the
          // focus would scroll the headline and the offer out of view
          initialFocus={() =>
            !onPlan && window.matchMedia("(min-width: 640px)").matches ? pick.current : false
          }
          className={`${cardFonts} fixed left-1/2 top-1/2 z-[951] flex max-h-[90vh] w-[760px] max-w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-[10px] border border-noir-line bg-noir-panel p-6 font-tight text-sm leading-normal text-bone outline-none max-sm:p-4`}
        >
          {offer ? (
            <div className="self-start rounded-full bg-noir-red px-3 py-1 font-plex text-[11px] font-semibold tracking-[0.12em] text-black uppercase">
              New member offer · {offer.label}
            </div>
          ) : null}
          <div className="flex flex-col gap-1.5">
            <Dialog.Title className="m-0 font-bebas text-[34px] font-normal leading-none tracking-[0.02em]">
              {onPlan ? "You're out of credits this month" : "Keep making. Pick a plan."}
            </Dialog.Title>
            <Dialog.Description className="m-0 text-[14.5px] text-bone2">
              {onPlan
                ? `Top up ${num(TOPUP.credits)} credits now. They land on your balance right away, on top of your plan.`
                : offer
                  ? `Your free credits are used up. Choose a plan today and get ${offer.label}. Every model, no watermark, and everything you've already made gets unmarked.`
                  : "Your free credits are used up. Every plan gets every model, no watermark, and everything you've already made gets unmarked."}
            </Dialog.Description>
          </div>

          {onPlan ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-noir-line p-4">
              <div>
                <div className="font-bebas text-[26px] leading-none">{num(TOPUP.credits)} credits</div>
                <div className="text-bone2">{dollars(Math.round(TOPUP.usd * 100))}, one time</div>
              </div>
              <button type="button" className="btn pri" disabled={!!busy} onClick={() => void buy(TOPUP.key)}>
                {busy ? "OPENING CHECKOUT…" : "BUY CREDITS"}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1 max-sm:gap-2">
              {PLANS.map((plan) => {
                const now = firstMonthCents(plan.monthly_usd, offer);
                const full = Math.round(plan.monthly_usd * 100);
                const best = plan.key === popular;
                return (
                  <div
                    key={plan.key}
                    className={`flex flex-col gap-3 rounded-[10px] border p-4 max-sm:grid max-sm:grid-cols-[1fr_auto] max-sm:items-center max-sm:gap-x-3 max-sm:gap-y-1 max-sm:p-3 ${best ? "border-noir-red shadow-[0_0_0_1px_var(--signal)]" : "border-noir-line"}`}
                  >
                    <div className="flex items-center justify-between max-sm:col-span-2 max-sm:justify-start max-sm:gap-3">
                      <span className="font-bebas text-[24px] leading-none">{plan.name}</span>
                      {best ? (
                        <span className="font-plex text-[10px] tracking-[0.12em] text-noir-red2">MOST POPULAR</span>
                      ) : null}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="font-bebas text-[34px] leading-none max-sm:text-[28px]">{dollars(now)}</span>
                      {now < full ? <span className="text-bone3 line-through">{dollars(full)}</span> : null}
                      <span className="text-bone3">/mo</span>
                    </div>
                    <div className="text-[13px] text-bone2 max-sm:col-start-1">
                      {num(plan.credits)} credits a month
                      {now < full ? <span className="block text-bone3">first month, then {dollars(full)}/mo</span> : null}
                    </div>
                    <button
                      ref={best ? pick : undefined}
                      type="button"
                      className={`${best ? "btn pri" : "btn"} mt-auto max-sm:col-start-2 max-sm:row-start-2 max-sm:row-span-2 max-sm:mt-0`}
                      disabled={!!busy}
                      onClick={() => void buy(plan.key)}
                    >
                      {busy === plan.key ? "OPENING…" : `GET ${plan.name.toUpperCase()}`}
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {failed ? (
            <p className="m-0 text-noir-danger" role="alert">
              {failed}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2 text-[13px] text-bone3">
            <Link href="/pricing" className="underline hover:text-bone" onClick={() => setOpen(false)}>
              {onPlan ? "See plans and yearly pricing" : `Compare plans, or save ${discountPercent()}% yearly`}
            </Link>
            <Dialog.Close
              type="button"
              disabled={!!busy}
              className="h-10 rounded-[8px] border border-noir-line bg-transparent px-4 font-plex! text-xs! tracking-[0.08em] text-bone! hover:enabled:border-bone"
            >
              NOT NOW
            </Dialog.Close>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
