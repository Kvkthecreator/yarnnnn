"use client";

/**
 * Billing pane — the TWO-AXIS pricing model (ADR-445, over ADR-396's meter).
 *
 * Two axes, both owner-paid:
 *   ① SEATS — seat 1 (the owner) is free; each additional human is a priced seat.
 *      The per-seat price IS the paid subscription (no separate base fee). A solo
 *      workspace is free; a team is paid at (humans − 1) × the seat fee.
 *   ② METERED USAGE — the plan grants a monthly pooled ALLOWANCE the whole
 *      workspace draws; a dynamic top-up is the overage pool beneath it. Draw
 *      order: allowance → balance → hard-stop at zero.
 *
 * Transparency contract (ADR-396): this customer surface shows ACTIVITY — the plan
 * + seats + allowance consumed this cycle — NOT raw dollar figures. The monthly
 * spend CEILING (a governance dial, not a bill) lives on the Budget surface.
 */

import { useEffect, useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
// `Users` dropped 2026-07-22 — the reference's seat row leads with the COUNT at
// emphasis weight, no leading glyph; the icon competed with the numeral.
import { Loader2, Zap, ArrowUpCircle, ShieldCheck } from "lucide-react";
import type { SubscriptionTier } from "@/types";
import { ByokSection } from "@/components/subscription/ByokSection";
import {
  deriveUsageMeter,
  tierUpgradeLabel,
  tierDescriptor,
  type UsageLimits,
  type UsageMeter,
  TOPUP_PRESETS,
  TOPUP_DEFAULT,
  TOPUP_MIN_USD,
  TOPUP_MAX_USD,
} from "@/lib/subscription/usage";

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
  const { status, tier, isLoading, error, topup, subscribe, manageSubscription } = useSubscription();
  const { navigateToSurface } = useSurfacePreferences();
  // ADR-445 — the seat + comped state (already fetched by useSubscription's
  // getStatus). `seatBillingActive` is now TRUE on paid tiers (seats are live):
  // it means the workspace has billable seats beyond the owner. An exempt
  // workspace shows a "Comped" state instead of upgrade/top-up CTAs.
  const exempt = status?.billing_exempt ?? false;
  const humanSeats = status?.human_seats ?? 1;
  const includedSeats = status?.included_seats ?? 1;
  const billableSeats = status?.billable_seats ?? 0;
  const seatBillingActive = status?.seat_billing_active ?? false;
  const [usage, setUsage] = useState<UsageLimits | null>(null);
  const [nextRefill, setNextRefill] = useState<string | null>(null);
  const [topupAmount, setTopupAmount] = useState<string>(String(TOPUP_DEFAULT));
  const [topupLoading, setTopupLoading] = useState(false);
  const [subscribeLoading, setSubscribeLoading] = useState<SubscriptionTier | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.integrations
      .getLimits()
      .then((d) => {
        if (!cancelled) {
          setUsage({
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
    return () => {
      cancelled = true;
    };
  }, []);

  const meter: UsageMeter | null = deriveUsageMeter(usage);

  const handleTopup = async () => {
    const amount = parseInt(topupAmount, 10);
    if (!Number.isFinite(amount) || amount <= 0) return;
    setTopupLoading(true);
    await topup(amount);
    setTopupLoading(false);
  };

  const handleSubscribe = async (nextTier: "starter" | "pro") => {
    setSubscribeLoading(nextTier);
    await subscribe(nextTier);
    setSubscribeLoading(null);
  };

  // "Manage seats" — in OUR model a seat is a human member (ADR-445 Axis ①), so
  // managing seats IS managing workspace access. The reference opens a seat-count
  // purchase dialog; we open the Members pane, where a seat is added by inviting
  // a person (the count follows the roster, it is never bought directly).
  const onManageSeats = () => navigateToSurface("workspace-settings", { pane: "members" });

  const currentIndex = TIER_ORDER.indexOf(tier);
  const upgradeTargets = TIER_ORDER.slice(currentIndex + 1).filter(
    (t): t is "starter" | "pro" => t === "starter" || t === "pro",
  );

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
                  onClick={manageSubscription}
                  className="shrink-0 text-sm font-medium px-4 py-2 rounded-full border border-border hover:bg-muted/40 transition-colors"
                >
                  Manage
                </button>
              )}
            </div>

            {/* SEATS — Axis ① (ADR-445). Seat 1 (the owner) is free; each additional
                human is a priced seat. Solo = free; a team is billed per extra head.
                The line names the live billing honestly (no "not billed yet").
                Reference shape: the count reads as the row's headline, its action
                is a pill button hard right. */}
            <div className="flex items-center justify-between gap-4 border-t border-border/60 pt-4">
              <div className="min-w-0">
                <div className="text-base font-medium">
                  {humanSeats === 1
                    ? "1 seat in use"
                    : `${humanSeats} people · ${billableSeats} ${billableSeats === 1 ? "seat" : "seats"} billed`}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {/* A solo owner on a PAID plan is paying — telling them "your seat
                      is free" contradicts the charge on the same card. What their $20
                      buys is the pooled allowance + gates, not a second seat. */}
                  {humanSeats === 1 && tier !== "free" && !exempt
                    ? "Your plan covers this workspace's shared usage. Teammates you invite are billed seats."
                    : humanSeats === 1
                    ? "Your seat is free. Invite a teammate and each extra person is a paid seat."
                    : exempt
                      ? "Comped — no seat charge on this workspace."
                      : seatBillingActive
                        ? `Seat 1 (you) is free; ${billableSeats} additional ${billableSeats === 1 ? "person is a billed seat" : "people are billed seats"} at renewal.`
                        : "Seat 1 (you) is free; additional people are billed seats on a paid plan."}
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

        {/* ── BALANCE / USAGE (the reference's "Credits balance" — but OUR model:
            included-usage %, no credits, no dollars per ADR-396). ───────────── */}
        <section className="border border-border rounded-xl p-5 space-y-4">
          {/* Reference shape: section title left, its primary action as a pill
              button hard right, then the FIGURE at display scale beneath. Ours
              shows the % used (ADR-396: activity, never dollars) where the
              reference shows a credit count — the numeral is the same visual
              anchor, carrying a figure our transparency contract permits. */}
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-base font-medium">
              {meter?.mode === "overage" ? "Top-up balance" : meter?.mode === "balance" ? "Balance" : "Included usage"}
            </h3>
          </div>
          {meter ? (
            <>
              <div className="flex items-baseline gap-1.5">
                <span className="text-5xl font-semibold tabular-nums leading-none tracking-tight">
                  {meter.percent}
                </span>
                <span className="text-lg text-muted-foreground">% used</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted/50 overflow-hidden">
                <div
                  className={meter.isCritical ? "h-full rounded-full bg-destructive" : meter.isWarn ? "h-full rounded-full bg-amber-500" : "h-full rounded-full bg-primary"}
                  style={{ width: `${meter.percent}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">{meter.detail}</p>
            </>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading usage…
            </div>
          )}
        </section>

        {/* Upgrade — hidden when comped (no bill to change). ADR-429 §13.2 copy:
            a paid plan unlocks a bigger shared allowance + a team, not connector
            history (which gates the dormant capture lane). */}
        {!exempt && upgradeTargets.length > 0 && (
          <section className="p-5 border border-border rounded-xl space-y-3">
            <div className="flex items-center gap-2">
              <ArrowUpCircle className="w-4 h-4 text-primary" />
              <h3 className="text-base font-medium">Upgrade your plan</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              A paid plan includes a monthly usage allowance your whole workspace draws from, and lets you invite your team.
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
            A one-time top-up gives this workspace extra headroom beyond the monthly allowance. It never expires.
          </p>
          <div className="flex gap-2">
            {TOPUP_PRESETS.map((amt) => (
              <Button
                key={amt}
                type="button"
                variant={topupAmount === String(amt) ? "secondary" : "outline"}
                size="sm"
                onClick={() => setTopupAmount(String(amt))}
                disabled={topupLoading}
              >
                ${amt}
              </Button>
            ))}
          </div>
          <div className="flex gap-2 items-center">
            <div className="flex items-center gap-1 flex-1 rounded-md border border-border px-3 py-1.5">
              <span className="text-muted-foreground text-sm">$</span>
              <input
                type="number"
                min={TOPUP_MIN_USD}
                max={TOPUP_MAX_USD}
                value={topupAmount}
                onChange={(e) => setTopupAmount(e.target.value)}
                className="w-full bg-transparent text-sm outline-none"
                aria-label="Top-up amount in dollars"
              />
            </div>
            <Button size="sm" onClick={handleTopup} disabled={topupLoading}>
              {topupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Top up"}
            </Button>
          </div>
        </section>
        )}

        {/* BYOK (ADR-439) — self-renders only on an enterprise workspace where
            tier_byok_available is true; a no-op card otherwise. */}
        <ByokSection />

        {/* How it works — ADR-429 §13.2 commons language. */}
        <section className="p-5 border border-border rounded-xl space-y-2 text-sm text-muted-foreground leading-relaxed">
          <p>
            <strong className="text-foreground">Idle costs nothing.</strong> The workspace and every
            file are free — only work that runs draws on the allowance.
          </p>
          <p>
            <strong className="text-foreground">One shared pool.</strong> Everyone in the workspace —
            you, your teammates, and any AI you connect — draws the same allowance. Usage is
            attributed per member on the Usage tab.
          </p>
          <p>
            <strong className="text-foreground">Hard stop when exhausted.</strong> If the allowance and
            balance run out, work pauses — nothing is lost. Upgrade or top up to resume.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
