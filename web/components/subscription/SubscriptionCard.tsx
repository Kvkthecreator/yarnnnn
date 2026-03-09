"use client";

/**
 * ADR-100: Billing surface with 2-tier display (Free/Pro), Early Bird option, and billing actions.
 * Usage/limits moved to the Usage tab in settings.
 */

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard, Loader2, Sparkles } from "lucide-react";

type PlanTier = "free" | "pro";
type BillingPeriod = "monthly" | "yearly";

const PLAN_ORDER: PlanTier[] = ["free", "pro"];

const PLAN_META: Record<PlanTier, {
  label: string;
  icon: "none" | "sparkles";
  monthlyPrice: string;
  yearlyPrice: string;
  style: string;
}> = {
  free: {
    label: "Free",
    icon: "none",
    monthlyPrice: "$0/mo",
    yearlyPrice: "$0/yr",
    style: "bg-muted text-muted-foreground",
  },
  pro: {
    label: "Pro",
    icon: "sparkles",
    monthlyPrice: "$19/mo",
    yearlyPrice: "$180/yr",
    style: "bg-primary text-primary-foreground",
  },
};

const FEATURE_ROWS: Array<{ label: string; values: Record<PlanTier, string> }> = [
  { label: "Platforms", values: { free: "4", pro: "4" } },
  { label: "Slack sources", values: { free: "5", pro: "Unlimited" } },
  { label: "Gmail labels", values: { free: "5", pro: "Unlimited" } },
  { label: "Notion pages", values: { free: "10", pro: "Unlimited" } },
  { label: "Calendars", values: { free: "Unlimited", pro: "Unlimited" } },
  { label: "Sync frequency", values: { free: "1x daily", pro: "Hourly" } },
  { label: "Monthly messages", values: { free: "50", pro: "Unlimited" } },
  { label: "Active deliverables", values: { free: "2", pro: "10" } },
  { label: "Priority support", values: { free: "No", pro: "Yes" } },
];

export function SubscriptionCard() {
  const { status, tier, isPaid, isLoading, error, upgrade, manageSubscription } = useSubscription();

  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>("monthly");

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading && !status) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!status && error) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-sm text-destructive text-center">
            Failed to load subscription status. Please refresh the page.
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentTier = (tier as PlanTier) || "free";
  const canUpgrade = currentTier === "free";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subscription</CardTitle>
        <CardDescription>
          Manage your yarnnn subscription and billing
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* Current Plan */}
        <section className="p-4 border border-border rounded-lg space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">Current plan</div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${PLAN_META[currentTier].style}`}>
                  {PLAN_META[currentTier].icon === "sparkles" && <Sparkles className="w-4 h-4" />}
                  {PLAN_META[currentTier].label}
                </span>
                {isPaid && (
                  <span className="text-sm text-muted-foreground">
                    {PLAN_META[currentTier][billingPeriod === "monthly" ? "monthlyPrice" : "yearlyPrice"]}
                  </span>
                )}
              </div>
            </div>
          </div>

          {status?.expires_at && (
            <p className="text-sm text-muted-foreground">
              Subscription renews on {formatDate(status.expires_at)}.
            </p>
          )}

          {canUpgrade && (
            <>
              <div className="inline-flex rounded-md border border-border p-1">
                <button
                  onClick={() => setBillingPeriod("monthly")}
                  className={`px-3 py-1.5 text-sm rounded ${
                    billingPeriod === "monthly" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingPeriod("yearly")}
                  className={`px-3 py-1.5 text-sm rounded ${
                    billingPeriod === "yearly" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Yearly
                </button>
              </div>

              {/* Standard Pro */}
              <div className="p-3 bg-muted/30 rounded-lg flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Upgrade to Pro</p>
                  <p className="text-sm text-muted-foreground">
                    Unlimited messages, 10 deliverables, hourly sync, unlimited sources.
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => upgrade(billingPeriod)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Upgrade to Pro ({PLAN_META.pro[billingPeriod === "monthly" ? "monthlyPrice" : "yearlyPrice"]})
                </Button>
              </div>

              {/* Early Bird — monthly only */}
              {billingPeriod === "monthly" && (
                <div className="p-3 border border-primary/20 bg-primary/5 rounded-lg flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium flex items-center gap-2">
                      Early Bird Beta Pricing
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">Limited</span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Same Pro features, $9/mo — locked in while available.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => upgrade("monthly", true)}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4 mr-2" />
                    )}
                    Get Early Bird ($9/mo)
                  </Button>
                </div>
              )}
            </>
          )}
        </section>

        {/* Plan Feature Matrix */}
        <section className="p-4 border border-border rounded-lg space-y-4">
          <h3 className="font-medium">Plan feature matrix</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-3 font-medium text-muted-foreground">Feature</th>
                  {PLAN_ORDER.map((plan) => (
                    <th
                      key={plan}
                      className={`text-left py-2 px-2 font-medium ${currentTier === plan ? "text-foreground" : "text-muted-foreground"}`}
                    >
                      <span className="inline-flex items-center gap-1">
                        {PLAN_META[plan].label}
                        {currentTier === plan && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-foreground">Current</span>
                        )}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FEATURE_ROWS.map((row) => (
                  <tr key={row.label} className="border-b border-border last:border-b-0">
                    <td className="py-2 pr-3 text-muted-foreground">{row.label}</td>
                    {PLAN_ORDER.map((plan) => (
                      <td key={`${row.label}-${plan}`} className="py-2 px-2">
                        {row.values[plan]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Billing Operations */}
        <section className="p-4 border border-border rounded-lg space-y-3">
          <h3 className="font-medium">Billing operations</h3>
          <p className="text-sm text-muted-foreground">
            Payment method, invoices, and cancellation are managed in the secure customer portal.
          </p>
          {isPaid ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={manageSubscription} disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4 mr-2" />
                )}
                Open Billing Portal
              </Button>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Billing portal becomes available after starting a paid plan.
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Annual billing includes ~17% savings versus monthly.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
