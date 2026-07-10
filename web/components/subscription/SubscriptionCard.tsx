"use client";

/**
 * Billing pane — ADR-396: Type-B subscription over the metered balance.
 *
 * The plan tier (Free / Starter / Pro) grants a monthly INCLUDED ALLOWANCE; a
 * dynamic top-up is the overage pool beneath it. Draw order: allowance → balance
 * → hard-stop at zero.
 *
 * Transparency contract (ADR-396): this customer surface shows ACTIVITY — the
 * plan + allowance consumed this cycle — NOT raw dollar figures. The one dollar
 * amount the operator sets is the top-up they choose to buy. The monthly spend
 * CEILING (an operator-set governance dial, not a bill) lives on the Budget
 * surface, not here.
 */

import { useEffect, useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Zap, ArrowUpCircle, Users, ShieldCheck } from "lucide-react";
import type { SubscriptionTier } from "@/types";
import { ByokSection } from "@/components/subscription/ByokSection";
import {
  deriveUsageMeter,
  tierPriceLabel,
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

// The upgrade ladder — the OFFERED tiers, low→high (ADR-429 §12.1). `pro` is
// DORMANT (hidden) at launch — the tier ladder collapsed to Free + one paid plan
// (`starter`); pro returns as the 2nd paid tier when the connector-capture lane
// ships. Mirrors billing_tiers.offered_paid_tiers() (backend source of truth);
// re-add 'pro' here when the backend un-hides it.
const TIER_ORDER: SubscriptionTier[] = ["free", "starter"];

export function SubscriptionCard({ workspaceName }: { workspaceName?: string | null }) {
  const { status, tier, isLoading, error, topup, subscribe, manageSubscription } = useSubscription();
  // ADR-429 §13.2 — the seat + comped state (already fetched by useSubscription's
  // getStatus). Seats show the COUNT (a legibility fact) while pricing is dormant;
  // an exempt workspace shows a "Comped" state instead of upgrade/top-up CTAs.
  const exempt = status?.billing_exempt ?? false;
  const humanSeats = status?.human_seats ?? 1;
  const includedSeats = status?.included_seats ?? 1;
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

  const currentIndex = TIER_ORDER.indexOf(tier);
  const upgradeTargets = TIER_ORDER.slice(currentIndex + 1).filter(
    (t): t is "starter" | "pro" => t === "starter" || t === "pro",
  );

  const overSeats = humanSeats > includedSeats;

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

        {/* ── PLAN CARD (reference layout, our model) ──────────────────────────
            Prominent: plan badge · cycle · seats front-and-center · Manage. */}
        <section className="border border-border rounded-lg p-4 space-y-4">
          {/* Plan name + badge + cycle + Manage (the reference's Business-Plan header) */}
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold">{TIER_LABEL[tier]} plan</span>
                <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {tier === "free" ? "Free" : "Monthly"}
                </span>
                {exempt && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/40 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
                    <ShieldCheck className="w-3 h-3" /> Comped
                  </span>
                )}
              </div>
              {tier !== "free" && nextRefill && (
                <p className="text-xs text-muted-foreground">
                  Current cycle: renews {new Date(nextRefill).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}
                </p>
              )}
              <p className="text-xs text-muted-foreground leading-relaxed">{tierDescriptor(tier)}</p>
            </div>
            {tier !== "free" && !exempt && (
              <button
                onClick={manageSubscription}
                className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border border-border hover:bg-muted/40 transition-colors"
              >
                Manage
              </button>
            )}
          </div>

          {/* SEATS — front-and-center (the reference's "14/13 seats in use").
              Count/legibility while pricing is dormant; the honest note names it. */}
          <div className="flex items-center justify-between gap-3 border-t border-border/60 pt-3">
            <div className="flex items-center gap-2.5">
              <Users className="w-4 h-4 text-muted-foreground shrink-0" />
              <div>
                <div className="text-sm font-medium">
                  {humanSeats} of {includedSeats} {includedSeats === 1 ? "seat" : "seats"} used
                  {overSeats && <span className="text-amber-600 dark:text-amber-400"> · over plan</span>}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {humanSeats === 1 ? "Just you" : `You + ${humanSeats - 1} ${humanSeats - 1 === 1 ? "member" : "members"}`}
                  {" · "}
                  {seatBillingActive
                    ? overSeats
                      ? `${humanSeats - includedSeats} extra billed at renewal`
                      : "included in your plan"
                    : "seats aren't billed yet"}
                  {" · AI connections are free"}
                </div>
              </div>
            </div>
            {tier === "free" && overSeats ? (
              <span className="text-[11px] text-muted-foreground shrink-0">Upgrade to add more</span>
            ) : null}
          </div>
        </section>

        {/* ── BALANCE / USAGE (the reference's "Credits balance" — but OUR model:
            included-usage %, no credits, no dollars per ADR-396). ───────────── */}
        <section className="border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">
              {meter?.mode === "overage" ? "Top-up balance" : meter?.mode === "balance" ? "Balance" : "Included usage"}
            </h3>
            {meter && <span className="text-sm font-medium tabular-nums">{meter.percent}% used</span>}
          </div>
          {meter ? (
            <>
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
          <section className="p-4 border border-border rounded-lg space-y-3">
            <div className="flex items-center gap-2">
              <ArrowUpCircle className="w-4 h-4 text-primary" />
              <h3 className="font-medium">Upgrade your plan</h3>
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
                    `${TIER_LABEL[t]} · ${tierPriceLabel(t)}`
                  )}
                </Button>
              ))}
            </div>
          </section>
        )}

        {/* Add balance (dynamic top-up) — hidden when comped. */}
        {!exempt && (
        <section className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="font-medium">Add balance</h3>
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
        <section className="p-4 border border-border rounded-lg space-y-2 text-sm text-muted-foreground leading-relaxed">
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
