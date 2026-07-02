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
import { Loader2, Zap, ArrowUpCircle } from "lucide-react";
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

// The upgrade ladder — the next tier(s) above the current one.
const TIER_ORDER: SubscriptionTier[] = ["free", "starter", "pro"];

export function SubscriptionCard() {
  const { tier, isLoading, error, topup, subscribe, manageSubscription } = useSubscription();
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
          Your plan includes a monthly allowance for the work your operation runs. Top up any time for extra headroom.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
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
        </section>

        {/* Upgrade */}
        {upgradeTargets.length > 0 && (
          <section className="p-4 border border-border rounded-lg space-y-3">
            <div className="flex items-center gap-2">
              <ArrowUpCircle className="w-4 h-4 text-primary" />
              <h3 className="font-medium">Upgrade your plan</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              A higher plan includes more monthly usage and a longer connector history window.
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

        {/* Add balance (dynamic top-up) */}
        <section className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="font-medium">Add balance</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            A one-time top-up gives your operation extra headroom beyond the monthly allowance. It never expires.
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

        {/* How it works */}
        <section className="p-4 border border-border rounded-lg space-y-2 text-sm text-muted-foreground leading-relaxed">
          <p>
            <strong className="text-foreground">Idle costs nothing.</strong> The workspace and every
            file are free — only a running operation draws on your allowance.
          </p>
          <p>
            <strong className="text-foreground">Hard stop when exhausted.</strong> If your allowance and
            balance run out, the operation pauses — nothing is lost. Upgrade or top up to resume.
          </p>
          <p>
            <strong className="text-foreground">Cap your monthly spend</strong> per operation on the
            Budget surface — a ceiling you set, not a charge.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
