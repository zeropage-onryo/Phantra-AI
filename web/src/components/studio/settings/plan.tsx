"use client";

/* Settings → Plan & credits (2026-10-11): the page people actually come to
   on Runway and Higgsfield, so the balance gets real weight -- one big
   number, the plan beside it, every lot with what is left of it.

   Everything is GET /api/billing/balance (src/billing.balance) and the
   generated catalog (lib/catalog.ts, the file /pricing renders). Three
   rules it keeps:

   - CREDITS, never dollars. The one dollar figure in the studio is a
     plan's PRICE, printed here as /pricing prints it (lib/catalog `usd`);
     tests/test_studio_shows_credits.py holds that it is the only one.
   - NOTHING HERE SPENDS. Choosing a plan and topping up open Stripe
     Checkout; changing or cancelling one opens Stripe's portal.
   - A workspace that already has a plan changes it IN THE PORTAL, never
     through a second checkout: Checkout would start a second subscription
     beside the first, and Stripe would bill both. */
import { useState } from "react";
import { ArrowUpRight, Check, CircleSlash, Clapperboard, Image as ImageIcon, PenLine } from "lucide-react";
import {
  CATALOG,
  MODELS,
  PLANS,
  TOPUP,
  clipsPerMonth,
  discountPercent,
  monthlyAt,
  usd,
  type Interval,
} from "@/lib/catalog";
import {
  countedElsewhere,
  creditsText,
  dayText,
  expiringSoon,
  expiry,
  lotLabel,
  lotLeft,
  nextRelease,
  num,
} from "@/lib/credits";
import { SECTIONS } from "@/lib/settings-sections";
import { openPortal, startCheckout } from "@/lib/site-billing";
import type { Balance } from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { useBalance } from "@/components/studio/settings/use-balance";
import {
  Badge,
  Button,
  EmptyState,
  Notice,
  Row,
  SectionHeader,
  Segmented,
  SettingsCard,
  Skeleton,
  SkeletonRows,
  Stat,
  buttonClass,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "plan")!;
const NO_CHECKOUT = "Checkout isn’t set up on this server yet, so plans and top-ups can’t be bought from here.";

/** the cheapest model, for "about N clips a month" -- every plan renders
 *  every model since 2026-10-20 */
const cheapestFor = () => MODELS.reduce((a, b) => (a.credits <= b.credits ? a : b));

function Hero({ balance }: { balance: Balance }) {
  const { me } = useShell();
  // somebody in two workspaces, with the other one open
  const elsewhere = countedElsewhere(balance.account, me?.account);
  const left = Math.max(balance.available, 0);
  const empty = !balance.exempt && balance.available <= 0;
  const soon = expiringSoon(balance.lots);
  const release = nextRelease(balance.schedules, (key) => PLANS.find((p) => p.key === key)?.credits);
  return (
    <div className="zset-hero">
      <div className="zset-hero-top">
        {balance.exempt ? (
          <div className="zset-stat">
            <span className="zset-hero-words">Not charged</span>
            <span className="zset-stat-label">operator account</span>
          </div>
        ) : (
          <Stat size="hero" tone={empty ? "signal" : undefined} value={num(left)} label="credits available" />
        )}
        <div className="zset-hero-plan">
          {balance.plan ? (
            <>
              <Badge tone="signal">{balance.plan.name} plan</Badge>
              <Badge>Every model</Badge>
            </>
          ) : balance.exempt ? (
            <Badge>Operator</Badge>
          ) : (
            <Badge>No plan</Badge>
          )}
        </div>
      </div>
      <ul className="zset-hero-lines">
        {elsewhere ? (
          <li>
            These credits belong to <b>{elsewhere.counted}</b>, the first workspace you joined. You have{" "}
            <b>{elsewhere.open}</b> open.
          </li>
        ) : null}
        {balance.exempt ? <li>Renders on this workspace take no hold and are never charged.</li> : null}
        {balance.outstanding > 0 ? (
          <li>
            <b>{num(balance.outstanding)}</b> held by renders in progress
          </li>
        ) : null}
        {release ? (
          <li>
            <b>{creditsText(release.credits)}</b> on {release.on}
            {release.left > 1 ? ` · ${release.left} monthly releases left this year` : " · the last release of this year"}
          </li>
        ) : null}
        {soon > 0 ? (
          <li className="warn">
            <b>{num(soon)}</b> expire within a week
          </li>
        ) : null}
        {empty ? <li>At zero, rendering a scene is refused until you add credits.</li> : null}
      </ul>
    </div>
  );
}

function Lots({ balance }: { balance: Balance }) {
  const lots = balance.lots;
  if (!lots.length)
    return (
      <EmptyState icon={CircleSlash} title="No credits on this workspace yet">
        {balance.exempt
          ? "An operator account renders without them."
          : "Credits arrive with a plan, a top-up or a trial, and each lot is listed here with what is left of it."}
      </EmptyState>
    );
  return (
    <table className="zset-table">
      <caption className="sr-only">Your credit lots, the soonest to expire first</caption>
      <thead>
        <tr>
          <th scope="col">Lot</th>
          <th scope="col">Left</th>
          <th scope="col">Expires</th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => {
          const ends = expiry(lot.expires_at);
          return (
            <tr key={lot.id}>
              <th scope="row">
                {lotLabel(lot.kind)}
                <span className="zset-table-sub">Added {dayText(lot.granted_at)}</span>
              </th>
              <td>
                <span className="zset-meter" aria-hidden>
                  <span style={{ width: `${Math.round(lotLeft(lot) * 100)}%` }} />
                </span>
                <span className="zset-table-num">
                  {num(lot.remaining)} <i>of {num(lot.credits)}</i>
                </span>
              </td>
              <td>
                {lot.expires_at ? (
                  <>
                    <span title={dayText(lot.expires_at)}>{ends.text}</span>
                    {ends.soon && lot.remaining > 0 ? <Badge tone="warn">Expires soon</Badge> : null}
                  </>
                ) : (
                  "Never"
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function PlanSection() {
  const { toast } = useShell();
  const { balance, loading, error, reload } = useBalance();
  const [interval, setInterval] = useState<Interval>("month");
  // which Stripe door is opening ("portal", "topup" or a plan's key)
  const [busy, setBusy] = useState<string | null>(null);

  const leave = async (key: string, go: () => ReturnType<typeof startCheckout>) => {
    setBusy(key);
    const out = await go();
    if (out.kind === "redirect") {
      window.location.href = out.url;
      return;
    }
    setBusy(null);
    toast(
      out.kind === "sign-in" ? "Sign in again to continue" : out.kind === "unconfigured" ? NO_CHECKOUT : out.message,
      "err",
    );
  };
  const portal = () => leave("portal", openPortal);
  const checkout = (item: string, at: Interval = "month") => leave(item, () => startCheckout(item, at));

  if (!balance) {
    return (
      <>
        <SectionHeader title={SECTION.label} description={SECTION.description} />
        {error ? (
          <Notice tone="err">
            {error}{" "}
            <button type="button" className="zset-link" onClick={reload}>
              Try again
            </button>
          </Notice>
        ) : (
          <>
            <SettingsCard pad>
              <div style={{ display: "grid", gap: 14 }} aria-busy={loading} aria-label="Loading your credits">
                <Skeleton width={120} height={10} />
                <Skeleton width={220} height={54} />
                <Skeleton width="46%" height={10} />
              </div>
            </SettingsCard>
            <SettingsCard title="Your plan">
              <SkeletonRows rows={2} />
            </SettingsCard>
          </>
        )}
      </>
    );
  }

  const plan = balance.plan;
  const mine = plan ? PLANS.find((p) => p.key === plan.key) : undefined;
  const yearly = balance.schedules.length > 0;
  const canBuy = balance.checkout_configured;
  const yearlyOffered = balance.yearly_configured && !plan;
  const at: Interval = yearlyOffered ? interval : "month";

  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />

      <SettingsCard>
        <Hero balance={balance} />
      </SettingsCard>

      {!canBuy ? <Notice>{NO_CHECKOUT}</Notice> : null}

      <SettingsCard title="Your plan">
        <Row
          label={plan ? `${plan.name}` : "No plan"}
          hint={
            plan ? (
              <>
                {creditsText(plan.credits)} a month ·{" "}
                {yearly && mine ? `${usd(mine.yearly_usd)} a year` : `${usd(plan.monthly_usd)} a month`}
                {yearly ? " · released month by month" : ""}
              </>
            ) : balance.exempt ? (
              "This workspace renders without a plan."
            ) : (
              "You are on trial or top-up credits. A plan adds credits every month."
            )
          }
          control={
            <a className={buttonClass} data-variant={plan || balance.exempt ? undefined : "primary"} href="#plans">
              {plan ? "Change plan" : "Choose a plan"}
            </a>
          }
        />
        <Row
          label="Top up"
          hint={
            plan
              ? `${TOPUP.name} for when the month runs out. The price is shown at checkout.`
              : "Top-ups are for workspaces on a plan. Choose a plan first."
          }
          control={
            plan ? (
              <Button variant="primary" onClick={() => checkout(TOPUP.key)} disabled={!canBuy || busy !== null}>
                {busy === TOPUP.key ? "Opening checkout…" : `Add ${num(TOPUP.credits)} credits`}
              </Button>
            ) : null
          }
        />
        {balance.portal ? (
          <Row
            label="Billing"
            hint="Invoices, your payment method and cancelling are kept by Stripe. Nothing is stored here."
            control={
              <Button onClick={portal} disabled={busy !== null}>
                {busy === "portal" ? "Opening…" : "Manage billing"} <ArrowUpRight strokeWidth={1.7} aria-hidden />
              </Button>
            }
          />
        ) : null}
      </SettingsCard>

      <section className="zset-group" id="plans" aria-labelledby="plans-title">
        <div className="zset-group-head zset-group-head-split">
          <h3 id="plans-title">Plans</h3>
          {yearlyOffered ? (
            <Segmented
              label="Billing interval"
              value={interval}
              options={[
                { id: "month", label: "Monthly" },
                { id: "year", label: `Yearly −${discountPercent()}%` },
              ]}
              onChange={setInterval}
            />
          ) : null}
        </div>
        <div className="zset-plans">
          {PLANS.map((p) => {
            const current = p.key === plan?.key;
            const cheapest = cheapestFor();
            return (
              <article key={p.key} className="zset-plan" data-current={current ? "1" : undefined}>
                <header>
                  <h4>{p.name}</h4>
                  {current ? <Badge tone="signal">Current plan</Badge> : p.popular ? <Badge>Popular</Badge> : null}
                </header>
                <p className="zset-plan-price">
                  <b>{usd(monthlyAt(p, at))}</b> a month
                </p>
                <p className="zset-plan-sub">
                  {at === "year" ? `Billed yearly, ${usd(p.yearly_usd)}.` : p.blurb}
                </p>
                <ul>
                  <li>
                    <Check strokeWidth={2} aria-hidden />
                    {creditsText(p.credits)} a month
                  </li>
                  <li>
                    <Check strokeWidth={2} aria-hidden />
                    About {clipsPerMonth(p, cheapest)} clips of {CATALOG.clip_seconds}s on {cheapest.name}
                  </li>
                  <li>
                    <Check strokeWidth={2} aria-hidden />
                    {num(p.storage_gb)} GB storage
                  </li>
                  {p.mcp ? (
                    <li>
                      <Check strokeWidth={2} aria-hidden />
                      Phantra MCP for Claude and ChatGPT
                    </li>
                  ) : null}
                </ul>
                {current ? (
                  <Button disabled>Your plan</Button>
                ) : plan ? (
                  // a second checkout would be a second subscription: an
                  // existing plan changes in Stripe's portal
                  balance.portal ? (
                    <Button onClick={portal} disabled={busy !== null}>
                      {busy === "portal" ? "Opening…" : `Switch to ${p.name}`}
                    </Button>
                  ) : null
                ) : (
                  <Button
                    variant={p.popular ? "primary" : "ghost"}
                    onClick={() => checkout(p.key, at)}
                    disabled={!canBuy || busy !== null}
                  >
                    {busy === p.key ? "Opening checkout…" : `Choose ${p.name}`}
                  </Button>
                )}
              </article>
            );
          })}
        </div>
        <p className="zset-note zset-plans-note">
          Credits expire {CATALOG.expiry_months} months after they land. Paying, changing and cancelling all happen on
          Stripe.{" "}
          <a href="/pricing" target="_blank" rel="noopener">
            Compare plans in full
          </a>
        </p>
      </section>

      <SettingsCard title="Your credits" description="soonest to expire first, the order they are spent in">
        <Lots balance={balance} />
      </SettingsCard>

      <SettingsCard title="What things cost">
        <div className="zset-tiles">
          <div className="zset-tile">
            <PenLine strokeWidth={1.5} aria-hidden />
            <b>Writing a scene</b>
            <span>Included with your plan or trial</span>
          </div>
          <div className="zset-tile">
            <ImageIcon strokeWidth={1.5} aria-hidden />
            <b>A still</b>
            <span>
              {balance.prices?.still != null ? creditsText(balance.prices.still) : "Priced on its button"}
              {balance.exempt ? " · not charged here" : ""}
            </span>
          </div>
          <a className="zset-tile" href="/pricing#models" target="_blank" rel="noopener">
            <Clapperboard strokeWidth={1.5} aria-hidden />
            <b>
              A clip <ArrowUpRight strokeWidth={1.7} aria-hidden />
            </b>
            <span>By model and length. See every model’s credits</span>
          </a>
        </div>
      </SettingsCard>
    </>
  );
}
