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
};

// The upgrade ladder — the OFFERED tiers, low→high (ADR-429 §12.1). `pro` is
// DORMANT (hidden) at launch — the tier ladder collapsed to Free + one paid plan
// (`starter`); pro returns as the 2nd paid tier when the connector-capture lane
// ships. Mirrors billing_tiers.offered_paid_tiers() (backend source of truth);
// re-add 'pro' here when the backend un-hides it.
const TIER_ORDER: SubscriptionTier[] = ["free", "starter"];

export function SubscriptionCard() {
  const { status, tier, isLoading, error, topup, subscribe, manageSubscription } = useSubscription();
  // ADR-429 §13.2 — the seat + comped state (already fetched by useSubscription's
  // getStatus). Seats show the COUNT (a legibility fact) while pricing is dormant;
  // an exempt workspace shows a "Comped" state instead of upgrade/top-up CTAs.
  const exempt = status?.billing_exempt ?? false;
  const humanSeats = status?.human_seats ?? 1;
  const includedSeats = status?.included_seats ?? 1;
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        <CardDescription>
          This workspace&rsquo;s plan includes a monthly allowance that everyone in the
          workspace draws from. Top up any time for extra headroom.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* ADR-429 §13.2 — comped state. An exempt workspace pays nothing; show it
            plainly and suppress the upgrade/top-up CTAs below (no bill to manage). */}
        {exempt && (
          <div className="p-3 rounded-lg border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50 dark:bg-emerald-950/30 text-sm flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>
              <span className="font-medium text-foreground">Comped</span> — this
              workspace has no charges. Usage still draws its allowance and balance
              normally.
            </span>
          </div>
        )}

        {/* Current plan — a prominent header: what plan you're on, what it gives
            you, and when it renews (the reference "Max plan" pattern). */}
        <section className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-semibold">{TIER_LABEL[tier]} plan</span>
                <span className="text-sm text-muted-foreground">{tierPriceLabel(tier)}</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {tierDescriptor(tier)}
              </p>
              {tier !== "free" && nextRefill && (
                <p className="text-xs text-muted-foreground">
                  Renews {new Date(nextRefill).toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" })}
                </p>
              )}
            </div>
            {tier !== "free" && (
              <button
                onClick={manageSubscription}
                className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border border-border hover:bg-muted/40 transition-colors"
              >
                Manage
              </button>
            )}
          </div>
          {meter && (
            <div className="space-y-1.5">
              <div className="h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
                <div
                  className={meter.isCritical ? "h-full rounded-full bg-destructive" : meter.isWarn ? "h-full rounded-full bg-amber-500" : "h-full rounded-full bg-primary"}
                  style={{ width: `${meter.percent}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">{meter.primaryLabel}.</p>
            </div>
          )}
          {/* ADR-429 §13.2 — the seats row. Shows the COUNT (who's on the workspace),
              a legibility fact; seat PRICING stays invisible while dormant
              (seat_billing_active false). "you + K members" reads the commons. */}
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground border-t border-border/60">
            <Users className="w-3.5 h-3.5 shrink-0" />
            <span>
              {humanSeats === 1
                ? "1 person — just you"
                : `${humanSeats} people — you + ${humanSeats - 1} ${humanSeats - 1 === 1 ? "member" : "members"}`}
              {includedSeats > humanSeats && tier !== "free" && (
                <> · {includedSeats} included in your plan</>
              )}
              {tier === "free" && (
                <> · Free includes up to {includedSeats}</>
              )}
            </span>
          </div>
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
