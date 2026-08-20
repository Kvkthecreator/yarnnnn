"use client";

/**
 * Billing pane — the TWO-AXIS pricing model (ADR-490, over ADR-396's meter).
 *
 * Two axes, both owner-paid:
 *   ① SEATS — the first TWO humans (owner + one teammate) are free; each
 *      additional human is a priced seat. The per-seat price IS the paid
 *      subscription (no base fee, no allowance). A ≤2-human workspace is free;
 *      a team pays (humans − 2) × the seat fee.
 *   ② USAGE — pure pay-as-you-go from one shared balance (signup grant +
 *      top-ups), hard-stop at zero. The monthly-allowance layer is retired
 *      (ADR-490 §1③).
 *
 * Transparency contract (ADR-396, as amended §10): CONSUMPTION stays
 * activity-shaped — per-member %-share, relative trend, runway in days, never a
 * running cost ticker. Dollars appear at the moment of purchase (seat price,
 * top-up amounts) AND as the prepaid BALANCE itself, which the operator tops up
 * in dollars and must be able to read to choose an amount.
 *
 * ADR-491 D2 — member gate: /subscription/status 403s a caller without billing
 * authority (ADR-416 D1); this card renders the calm member state instead of
 * dead verbs. The gate keys on the server's decision, never a role enum.
 */

import { useEffect, useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
// `Users` dropped 2026-07-22 — the reference's seat row leads with the COUNT at
// emphasis weight, no leading glyph; the icon competed with the numeral.
import {
  Loader2,
  Zap,
  ArrowUpCircle,
  ShieldCheck,
  CreditCard,
  CircleSlash,
  ExternalLink,
  X,
} from "lucide-react";
import { SeatPanel } from "@/components/subscription/SeatPanel";
import type { SubscriptionTier } from "@/types";
import { ByokSection } from "@/components/subscription/ByokSection";
import {
  deriveBalance,
  formatUsd,
  tierUpgradeLabel,
  tierDescriptor,
  type UsageLimits,
  type BalanceReadout,
  TOPUP_PRESETS,
  TOPUP_DEFAULT,
  TOPUP_MIN_USD,
  TOPUP_MAX_USD,
  TIER_SEAT_PRICE_USD,
} from "@/lib/subscription/usage";

// A price, not a meter reading — ADR-396 hides the running consumption figure,
// not what a plan costs (usage.ts states the same split at TIER_SEAT_PRICE_USD).
function money(n: number): string {
  return n % 1 === 0 ? `$${n}` : `$${n.toFixed(2)}`;
}

const TIER_LABEL: Record<SubscriptionTier, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",  // ADR-439 — sales-led; not a self-serve upgrade target
};

// The upgrade ladder — the OFFERED tiers, low→high (ADR-445). `pro` is DORMANT
// (hidden) at launch — the tier ladder is Free + one paid plan (`starter`); pro
// returns as the 2nd paid tier when the connector-capture lane ships. Mirrors
// billing_tiers.offered_paid_tiers() (backend source of truth); re-add 'pro' here
// when the backend un-hides it.
const TIER_ORDER: SubscriptionTier[] = ["free", "starter"];

export function SubscriptionCard({ workspaceName }: { workspaceName?: string | null }) {
  const { status, tier, isLoading, error, isForbidden, topup, subscribe, openPaymentMethods, cancel } =
    useSubscription();
  const { navigateToSurface } = useSurfacePreferences();
  // 2026-07-22 — the two misleading buttons become in-app panels. `seats` is the
  // per-person cost breakdown (was: a jump to the permissions roster); `plan` is
  // the tier/cancel panel (was: a bounce to the Lemon Squeezy portal).
  const [panel, setPanel] = useState<null | "seats" | "plan">(null);
  const [cancelled, setCancelled] = useState<string | null>(null);
  // ADR-445 — the seat + comped state (already fetched by useSubscription's
  // getStatus). `seatBillingActive` is now TRUE on paid tiers (seats are live):
  // it means the workspace has billable seats beyond the owner. An exempt
  // workspace shows a "Comped" state instead of upgrade/top-up CTAs.
  const exempt = status?.billing_exempt ?? false;
  const humanSeats = status?.human_seats ?? 1;
  const includedSeats = status?.included_seats ?? 2;
  const billableSeats = status?.billable_seats ?? 0;
  const seatBillingActive = status?.seat_billing_active ?? false;
  // Exempt-aware already (the backend forces it to 0 on a comped workspace).
  const seatFee = status?.seat_fee_usd ?? 0;
  // A seat change that never reached the invoice (null = healthy).
  const seatSyncIssue = status?.seat_sync_issue ?? null;
  const [usage, setUsage] = useState<UsageLimits | null>(null);
  const [nextRefill, setNextRefill] = useState<string | null>(null);
  // ADR-491 D3 — the runway ("~N days at this pace") is the dissolved Budget
  // pane's one surviving fact. It qualifies the balance figure, so it sits with
  // it. Served by GET /api/budget (effective balance ÷ observed daily burn).
  const [runwayDays, setRunwayDays] = useState<number | null>(null);
  // ONE selection model for the top-up chooser (2026-07-29). Previously the four
  // preset buttons and the always-visible number field were two competing inputs
  // driven off one string: typing a non-preset amount silently deselected every
  // chip and the UI went stateless. Now the chips ARE the control, and the field
  // exists only while "Custom" is the selection.
  const [topupChoice, setTopupChoice] = useState<number | "custom">(TOPUP_DEFAULT);
  const [customAmount, setCustomAmount] = useState<string>("");
  const [topupLoading, setTopupLoading] = useState(false);
  const [subscribeLoading, setSubscribeLoading] = useState<SubscriptionTier | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.integrations
      .getLimits()
      .then((d) => {
        if (!cancelled) {
          setUsage({
            balance_usd: d.balance_usd,
            spend_usd: d.spend_usd,
            raw_balance_usd: d.raw_balance_usd,
            allowance_usd: d.allowance_usd,
            topup_balance_usd: d.topup_balance_usd,
            tier: d.tier,
          });
          setNextRefill(d.next_refill);
        }
      })
      .catch(() => {});
    api
      .budget()
      .then((d) => {
        // 999 is the backend's "effectively unlimited" clamp — not worth a line.
        const days = (d as { runway_days?: number | null }).runway_days;
        if (!cancelled && typeof days === "number" && days > 0 && days < 999) {
          setRunwayDays(Math.round(days));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const balance: BalanceReadout | null = deriveBalance(usage);

  // The dollars a top-up would actually charge, or null when the custom entry is
  // absent/out of bounds. Validated HERE, at the boundary — the old handler only
  // rejected `<= 0`, so $3 and $9999 reached the API and failed there with a raw
  // error. WHOLE DOLLARS: the LS checkout prices in integer cents from a
  // whole-dollar amount, so offering cents would promise precision the charge
  // doesn't keep.
  const topupUsd: number | null = (() => {
    if (topupChoice !== "custom") return topupChoice;
    const raw = customAmount.trim();
    if (!raw) return null;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || !Number.isInteger(parsed)) return null;
    if (parsed < TOPUP_MIN_USD || parsed > TOPUP_MAX_USD) return null;
    return parsed;
  })();
  const customInvalid = topupChoice === "custom" && customAmount.trim() !== "" && topupUsd === null;

  const handleTopup = async () => {
    if (topupUsd === null) return;
    setTopupLoading(true);
    await topup(topupUsd);
    setTopupLoading(false);
  };

  const handleSubscribe = async (nextTier: "starter" | "pro") => {
    setSubscribeLoading(nextTier);
    await subscribe(nextTier);
    setSubscribeLoading(null);
  };

  // "Manage seats" — REWIRED 2026-07-22. It used to jump straight to the Members
  // pane: a permissions surface with no price on it, opened from a button inside
  // a billing card, which read as "take me to the payment screen" and delivered
  // access control. It now opens SeatPanel — who occupies a seat, what each one
  // costs, the seat total, and the priced invite action (the purchase, since in
  // our derived model the invite IS the buy). The roster stays one click on from
  // there, where the invite is actually authored.
  const onManageSeats = () => setPanel((p) => (p === "seats" ? null : "seats"));

  const currentIndex = TIER_ORDER.indexOf(tier);
  const upgradeTargets = TIER_ORDER.slice(currentIndex + 1).filter(
    (t): t is "starter" | "pro" => t === "starter" || t === "pro",
  );

  // ADR-491 D2 — a member without billing authority sees a calm pointer, not a
  // broken card. Rendered before anything else so no verb ever appears.
  if (isForbidden) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Billing</CardTitle>
          <CardDescription>
            {workspaceName ? (
              <>Billing for <span className="font-medium text-foreground">{workspaceName}</span> is managed by the workspace owner.</>
            ) : (
              <>Billing for this workspace is managed by the workspace owner.</>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            You draw the workspace&rsquo;s shared usage pool — see the Usage pane
            for what has been used and by whom. Plan changes, seats, and top-ups
            are the owner&rsquo;s verbs.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        {/* ADR-429 §13.3 — the WORKSPACE is the subject of this pane. Every section
            below is this workspace's; the account door is just the entry point. */}
        <CardDescription>
          {workspaceName ? (
            <>
              For <span className="font-medium text-foreground">{workspaceName}</span> — its plan,
              seats, and balance. Switch workspaces from the avatar menu to manage another.
            </>
          ) : (
            <>This workspace&rsquo;s plan, seats, and balance.</>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* ── UNRESOLVED SEAT SYNC (2026-07-29) ──────────────────────────────
            A member joined or left, but the change never reached the invoice —
            so the next bill is wrong in a direction the operator cannot see.
            The backend has recorded these `seat_sync_failed` rows since the
            reconciliation layer shipped and NOTHING read them: a live revoke's
            failure was found only by hand-querying the table. Best-effort
            billing is right; silent best-effort is not. */}
        {seatSyncIssue && (
          <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5 text-sm space-y-1">
            <p className="font-medium text-foreground">
              We couldn&rsquo;t update your seat count with the payment provider.
            </p>
            <p className="text-muted-foreground">
              Your workspace has{" "}
              {seatSyncIssue.human_seats !== null
                ? `${seatSyncIssue.human_seats} ${seatSyncIssue.human_seats === 1 ? "person" : "people"}`
                : "a new headcount"}
              , but the subscription still bills the old count, so your next
              invoice may be wrong. Nothing here is lost — open Payment method
              &amp; invoices to check, or contact support and we&rsquo;ll correct it.
              {seatSyncIssue.at && (
                <> (Last attempt {new Date(seatSyncIssue.at).toLocaleString([], {
                  month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
                })}.)</>
              )}
            </p>
          </div>
        )}

        {/* ── PLAN CARD ────────────────────────────────────────────────────────
            Reference layout (ChatGPT enterprise Billing → Plan), our model.
            The reference's shape, adopted 2026-07-22:
              · plan name at heading scale with a pill badge inline, cycle dates
                on the line beneath — the title block reads as one unit
              · a SEAT ROW as the card's body: "N/M seats in use" at emphasis
                weight on the left, its action as a PILL BUTTON hard right
              · a tinted FOOTER STRIP flush to the card's bottom edge carrying
                the billing-timing caveat + a repeated underlined action
            Ours differs from the reference where the MODEL differs, never where
            only the styling does: no "annual billing" pill (we bill monthly
            only), and the seat action leads to Manage access (our seats are
            member invites, not a seat-count purchase). */}
        <section className="border border-border rounded-xl overflow-hidden">
          <div className="p-5 space-y-5">
            {/* Plan name + badge + cycle (the reference's Business-Plan header) */}
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xl font-semibold tracking-tight">{TIER_LABEL[tier]} plan</span>
                  <span className="inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-950/40 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
                    {tier === "free" ? "Free" : "Monthly"}
                  </span>
                  {exempt && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/40 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
                      <ShieldCheck className="w-3 h-3" /> Comped
                    </span>
                  )}
                </div>
                {tier !== "free" && nextRefill && (
                  <p className="text-sm text-muted-foreground">
                    Current cycle: renews {new Date(nextRefill).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}
                  </p>
                )}
                <p className="text-xs text-muted-foreground leading-relaxed">{tierDescriptor(tier)}</p>
              </div>
              {tier !== "free" && !exempt && (
                <button
                  onClick={() => setPanel((p) => (p === "plan" ? null : "plan"))}
                  className="shrink-0 text-sm font-medium px-4 py-2 rounded-full border border-border hover:bg-muted/40 transition-colors"
                >
                  Manage plan
                </button>
              )}
            </div>

            {/* SEATS — Axis ① (ADR-490). The first TWO humans are free; each
                additional human is a priced seat. The line names the live billing
                honestly. Reference shape: the count reads as the row's headline,
                its action is a pill button hard right. */}
            <div className="flex items-center justify-between gap-4 border-t border-border/60 pt-4">
              <div className="min-w-0">
                <div className="text-base font-medium">
                  {humanSeats === 1
                    ? "1 seat in use"
                    : billableSeats > 0
                    ? `${humanSeats} people · ${billableSeats} ${billableSeats === 1 ? "seat" : "seats"} billed`
                    : `${humanSeats} people · no billed seats`}
                  {/* The seat TOTAL, on the headline row. `seat_fee_usd` has been
                      computed + returned by /subscription/status all along and
                      rendered nowhere — so a team could see "2 seats billed"
                      without ever being told what that costs. A price, not a
                      meter (ADR-396 governs the consumption figure). */}
                  {seatFee > 0 && (
                    <span className="ml-1.5 font-normal text-muted-foreground">
                      · {money(seatFee)}/mo
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {/* ADR-490 — two free seats. (The old paid-solo carve is gone
                      with the allowance: a ≤2-human workspace has no subscription
                      to buy, so "free" is simply true.) */}
                  {exempt
                    ? "Comped — no seat charge on this workspace."
                    : seatBillingActive
                      ? `The first two seats are free; ${billableSeats} additional ${billableSeats === 1 ? "person is a billed seat" : "people are billed seats"} at renewal.`
                      : humanSeats === 1
                        ? "Your seat is free, and a first teammate is too. From the 3rd person, each seat is paid."
                        : "Two seats are free. From the 3rd person, each additional seat is paid."}
                  {" · AI connections are free"}
                </div>
              </div>
              {tier === "free" && humanSeats >= includedSeats ? (
                <span className="text-xs text-muted-foreground shrink-0">Upgrade to add your team</span>
              ) : (
                <button
                  onClick={onManageSeats}
                  className="shrink-0 text-sm font-medium px-4 py-2 rounded-full border border-border hover:bg-muted/40 transition-colors"
                >
                  Manage seats
                </button>
              )}
            </div>
          </div>

          {/* Footer strip — the reference's tinted caveat band, flush to the card
              edge. Names WHEN a seat change reaches the bill (our seats bill at
              renewal, ADR-445), with the action repeated as an underlined link. */}
          {tier !== "free" && !exempt && (
            <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/40 px-5 py-3">
              <p className="text-xs text-muted-foreground">
                Seat changes take effect on your next renewal.
              </p>
              <button
                onClick={onManageSeats}
                className="shrink-0 text-xs font-medium underline underline-offset-2 hover:text-foreground transition-colors"
              >
                Manage seats
              </button>
            </div>
          )}
        </section>

        {/* ── SEATS PANEL (2026-07-22) — opened by "Manage seats". Renders in
            place, directly beneath the card whose seat row summoned it, so the
            operator keeps the plan in view while reading what it costs. */}
        {panel === "seats" && (
          <section className="border border-border rounded-xl p-5">
            <SeatPanel
              status={status}
              seatPriceUsd={TIER_SEAT_PRICE_USD[tier]}
              onClose={() => setPanel(null)}
            />
          </section>
        )}

        {/* ── PLAN PANEL (2026-07-22) — opened by "Manage plan". The verbs that
            are OURS (what this workspace runs on) stay in-app; the one that is
            genuinely the processor's (the payment instrument) is a labelled
            link out. */}
        {panel === "plan" && (
          <section className="border border-border rounded-xl p-5 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-medium">Manage plan</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {TIER_LABEL[tier]} · {money(TIER_SEAT_PRICE_USD[tier])}/person per month
                  {nextRefill && ` · renews ${new Date(nextRefill).toLocaleDateString([], { month: "short", day: "numeric" })}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPanel(null)}
                aria-label="Close plan panel"
                className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {cancelled ? (
              // Cancellation is at PERIOD END, never immediate — so the
              // confirmation names the date access actually stops. Saying
              // "cancelled" alone would imply the workspace lost its allowance
              // the moment it clicked, which is both wrong and alarming.
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2.5 text-sm">
                Plan cancelled. This workspace keeps its current plan until{" "}
                <span className="font-medium">
                  {new Date(cancelled).toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" })}
                </span>
                , then returns to Free. Nothing is deleted.
              </div>
            ) : (
              <div className="rounded-lg border border-border divide-y divide-border/60">
                {/* The payment INSTRUMENT — the one thing the processor owns.
                    Named for what it is, instead of a generic "Manage" that
                    promised plan control and delivered a store page. */}
                <button
                  type="button"
                  onClick={openPaymentMethods}
                  disabled={isLoading}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/40 disabled:opacity-60"
                >
                  <span className="flex items-center gap-2.5">
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Payment method &amp; invoices</span>
                  </span>
                  <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60" />
                </button>

                {/* Cancel — ours, because it decides what the WORKSPACE runs on. */}
                <button
                  type="button"
                  onClick={async () => {
                    if (!window.confirm(
                      "Cancel this plan? The workspace keeps its current plan until the end of the billing period, then returns to Free. Your files and history are not affected.",
                    )) return;
                    const res = await cancel();
                    if (res) setCancelled(res.ends_at ?? new Date().toISOString());
                  }}
                  disabled={isLoading}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/40 disabled:opacity-60"
                >
                  <span className="flex items-center gap-2.5">
                    <CircleSlash className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Cancel plan</span>
                  </span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">at period end</span>
                </button>
              </div>
            )}

            <p className="text-xs leading-relaxed text-muted-foreground">
              Cancelling stops the subscription only. Your workspace, files, and
              history stay exactly as they are — a Free workspace keeps everything
              it made.
            </p>
          </section>
        )}

        {/* ── BALANCE (the reference's "Credits balance" — our model: a prepaid
            pool, so the figure is WHAT'S LEFT). ─────────────────────────────────
            Rewritten 2026-07-29. This read "N% used" against `spend / (spend +
            topups)` — a denominator with no fixed meaning for a prepaid pool,
            since `spend` is anchored to `allowance_granted_at` and the banking
            cycle re-stamps that monthly. A workspace holding $37 with a fresh
            anchor rendered "0% used": arithmetically true, and it told the
            operator nothing about what they hold while asking them to choose
            between $5 and $50 below.

            Dollars here are ADR-396-legal (§10 amendment): the hide-$ contract
            governs the CONSUMPTION meter — no running cost ticker — and permits
            dollars at the moment of purchase. A prepaid balance topped up in
            dollars IS the purchase quantity. Consumption stays activity-shaped
            everywhere else (per-member %, relative trend, runway in days). */}
        <section className="border border-border rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-base font-medium">Balance</h3>
          </div>
          {balance ? (
            <>
              <div className="flex items-baseline gap-2 flex-wrap">
                <span
                  className={
                    balance.isExhausted
                      ? "text-5xl font-semibold tabular-nums leading-none tracking-tight text-destructive"
                      : "text-5xl font-semibold tabular-nums leading-none tracking-tight"
                  }
                >
                  {balance.remainingLabel}
                </span>
                <span className="text-lg text-muted-foreground">remaining</span>
              </div>
              {/* The qualifying facts, in one line: what's been drawn, and how
                  long the rest lasts at the observed pace (ADR-491 D3's runway,
                  re-homed from the dissolved Budget pane). */}
              {(balance.spentUsd > 0 || runwayDays !== null) && (
                <p className="text-sm text-muted-foreground">
                  {/* NOT "since your last top-up" (2026-08-20 audit): a top-up
                      does NOT move the spend anchor. `get_lifetime_spend_usd`
                      counts from the ALLOWANCE anchor — allowance_granted_at →
                      subscription_refill_at → created_at — which moves on the
                      billing cycle only (platform_limits.py). Naming a window
                      the number does not use is a money-visible lie. */}
                  {balance.spentUsd > 0 && <>{formatUsd(balance.spentUsd)} used this billing cycle</>}
                  {balance.spentUsd > 0 && runwayDays !== null && " · "}
                  {runwayDays !== null && <>about {runwayDays} {runwayDays === 1 ? "day" : "days"} left at this pace</>}
                </p>
              )}
              <p className="text-xs text-muted-foreground">{balance.detail}</p>
            </>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading balance…
            </div>
          )}
        </section>

        {/* Upgrade — ADR-490/491: the paid plan is SEATS ONLY, so the upgrade is
            offered only AT the seat boundary (the workspace's humans have used
            up the free seats). A 1-human free workspace sees no upsell — there
            is nothing the subscription would buy them. Hidden when comped. */}
        {!exempt && upgradeTargets.length > 0 && humanSeats >= includedSeats && (
          <section className="p-5 border border-border rounded-xl space-y-3">
            <div className="flex items-center gap-2">
              <ArrowUpCircle className="w-4 h-4 text-primary" />
              <h3 className="text-base font-medium">Add more seats</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Two seats are free. The paid plan adds seats for the rest of your
              team — each additional person from the 3rd onward.
            </p>
            <div className="flex gap-2">
              {upgradeTargets.map((t) => (
                <Button
                  key={t}
                  variant="default"
                  size="sm"
                  onClick={() => handleSubscribe(t)}
                  disabled={isLoading || subscribeLoading !== null}
                  className="flex-1"
                >
                  {subscribeLoading === t ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    `${TIER_LABEL[t]} · ${tierUpgradeLabel(t)}`
                  )}
                </Button>
              ))}
            </div>
          </section>
        )}

        {/* Add balance (dynamic top-up) — hidden when comped. */}
        {!exempt && (
        <section className="p-5 border border-border rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="text-base font-medium">Add balance</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            Usage is pay-as-you-go from this workspace&rsquo;s shared balance. A
            one-time top-up adds headroom; it never expires.
          </p>
          {/* The chooser (2026-07-29, re-shaped 2026-07-30): presets + Custom as
              ONE radio group, rendered as SELECTABLE CARDS — not pills.

              The first pass made them `Button`s, which put the amount options and
              the confirm CTA in the same object class: same pill radius, same
              family, sitting in one flow. The operator read a row of five similar
              pills where two of them meant entirely different things (pick an
              amount vs. charge my card). The reference (Claude → Billing → "Need
              more usage?") separates them by KIND: amounts are bordered cards
              with a ring on the selected one; the confirm is a dark pill, hard
              right, across a divider. Adopted here — a selection is a card, an
              action is a button. */}
          <div
            role="radiogroup"
            aria-label="Top-up amount"
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2"
          >
            {TOPUP_PRESETS.map((amt) => {
              const active = topupChoice === amt;
              return (
                <button
                  key={amt}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setTopupChoice(amt)}
                  disabled={topupLoading}
                  className={cn(
                    "rounded-lg border px-4 py-3 text-left transition-colors disabled:opacity-60",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    active
                      ? "border-primary ring-1 ring-primary bg-primary/5"
                      : "border-border hover:bg-muted/40",
                  )}
                >
                  <span className="block text-base font-medium tabular-nums">${amt}</span>
                </button>
              );
            })}
            <button
              type="button"
              role="radio"
              aria-checked={topupChoice === "custom"}
              onClick={() => setTopupChoice("custom")}
              disabled={topupLoading}
              className={cn(
                "rounded-lg border px-4 py-3 text-left transition-colors disabled:opacity-60",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                topupChoice === "custom"
                  ? "border-primary ring-1 ring-primary bg-primary/5"
                  : "border-border hover:bg-muted/40",
              )}
            >
              <span className="block text-base font-medium">Other</span>
            </button>
          </div>
          {topupChoice === "custom" && (
            <div className="space-y-1.5">
              <div
                className={cn(
                  "flex items-center gap-1 max-w-[12rem] rounded-lg border px-3 py-2",
                  customInvalid ? "border-destructive" : "border-border",
                )}
              >
                <span className="text-muted-foreground text-sm">$</span>
                <input
                  type="number"
                  inputMode="numeric"
                  step={1}
                  min={TOPUP_MIN_USD}
                  max={TOPUP_MAX_USD}
                  value={customAmount}
                  autoFocus
                  onChange={(e) => setCustomAmount(e.target.value)}
                  placeholder={String(TOPUP_DEFAULT)}
                  className="w-full bg-transparent text-sm outline-none"
                  aria-label="Custom top-up amount in whole dollars"
                  aria-invalid={customInvalid}
                />
              </div>
              <p className={customInvalid ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                Whole dollars, between {formatUsd(TOPUP_MIN_USD)} and {formatUsd(TOPUP_MAX_USD)}.
              </p>
            </div>
          )}
          {/* The confirm row — across a divider, hard right (the reference's
              separation). The amount cards above are a SELECTION; this is the
              CHARGE, and the two must not read as one row of similar pills. The
              button NAMES the amount ("Top up" alone asked for a real payment
              without stating it), and the line at left restates what happens so
              the commitment is legible before the click, not after. */}
          <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
            <p className="text-xs text-muted-foreground">
              {topupUsd !== null ? (
                <>
                  Adds <span className="font-medium text-foreground">{formatUsd(topupUsd)}</span> to
                  this workspace&rsquo;s balance
                  {balance && (
                    <> — {formatUsd(balance.remainingUsd + topupUsd)} available after</>
                  )}
                  .
                </>
              ) : (
                <>Choose an amount to continue.</>
              )}
            </p>
            <Button
              onClick={handleTopup}
              disabled={topupLoading || topupUsd === null}
              className="shrink-0"
            >
              {topupLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : topupUsd !== null ? (
                `Add ${formatUsd(topupUsd)}`
              ) : (
                "Add balance"
              )}
            </Button>
          </div>
        </section>
        )}

        {/* BYOK (ADR-439) — self-renders only on an enterprise workspace where
            tier_byok_available is true; a no-op card otherwise. */}
        <ByokSection />

        {/* How it works — ADR-429 §13.2 commons language, corrected 2026-07-29
            for ADR-490. Every "allowance" here named a layer this model retired,
            and the last line offered "Upgrade" as a remedy for an empty balance —
            false under ADR-490, where the paid plan buys SEATS and nothing else. */}
        <section className="p-5 border border-border rounded-xl space-y-2 text-sm text-muted-foreground leading-relaxed">
          <p>
            <strong className="text-foreground">Idle costs nothing.</strong> The workspace and every
            file are free — only work that runs draws on the balance.
          </p>
          <p>
            <strong className="text-foreground">One shared pool.</strong> Everyone in the workspace —
            you, your teammates, and any AI you connect — draws the same balance. Usage is
            attributed per member on the Usage tab.
          </p>
          <p>
            <strong className="text-foreground">Hard stop at zero.</strong> If the balance runs out,
            work pauses — nothing is lost. Top up to resume.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
