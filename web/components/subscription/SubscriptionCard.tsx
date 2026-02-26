"use client";

/**
 * ADR-053: Billing surface with tier details, live limits usage, and billing actions.
 */

import { useEffect, useMemo, useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { api } from "@/lib/api/client";
import type { TierLimits } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard, Loader2, Sparkles, Zap } from "lucide-react";

type PlanTier = "free" | "starter" | "pro";
type BillingPeriod = "monthly" | "yearly";

const PLAN_ORDER: PlanTier[] = ["free", "starter", "pro"];

const PLAN_META: Record<PlanTier, {
  label: string;
  icon: "none" | "zap" | "sparkles";
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
  starter: {
    label: "Starter",
    icon: "zap",
    monthlyPrice: "$9/mo",
    yearlyPrice: "$90/yr",
    style: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  },
  pro: {
    label: "Pro",
    icon: "sparkles",
    monthlyPrice: "$19/mo",
    yearlyPrice: "$190/yr",
    style: "bg-primary text-primary-foreground",
  },
};

const FEATURE_ROWS: Array<{ label: string; values: Record<PlanTier, string> }> = [
  { label: "Platforms", values: { free: "4", starter: "4", pro: "4" } },
  { label: "Slack sources", values: { free: "5", starter: "15", pro: "Unlimited" } },
  { label: "Gmail labels", values: { free: "5", starter: "10", pro: "Unlimited" } },
  { label: "Notion pages", values: { free: "10", starter: "25", pro: "Unlimited" } },
  { label: "Calendars", values: { free: "Unlimited", starter: "Unlimited", pro: "Unlimited" } },
  { label: "Sync frequency", values: { free: "1x daily", starter: "4x daily", pro: "Hourly" } },
  { label: "Daily token budget", values: { free: "50k", starter: "250k", pro: "Unlimited" } },
  { label: "Active deliverables", values: { free: "2", starter: "5", pro: "Unlimited" } },
  { label: "Signal processing", values: { free: "No", starter: "Yes", pro: "Yes" } },
];

export function SubscriptionCard() {
  const { status, tier, isPaid, isLoading, error, upgrade, manageSubscription } = useSubscription();

  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>("monthly");
  const [limits, setLimits] = useState<TierLimits | null>(null);
  const [limitsLoading, setLimitsLoading] = useState(true);
  const [limitsError, setLimitsError] = useState<string | null>(null);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatUsage = (used: number, limit: number) =>
    limit === -1 ? `${used} / Unlimited` : `${used} / ${limit}`;

  const formatSyncFrequency = (value: string) => {
    const labels: Record<string, string> = {
      "1x_daily": "1x daily",
      "2x_daily": "2x daily",
      "4x_daily": "4x daily",
      "hourly": "Hourly",
    };
    return labels[value] || value;
  };

  useEffect(() => {
    const loadLimits = async () => {
      setLimitsLoading(true);
      setLimitsError(null);
      try {
        const data = await api.integrations.getLimits();
        setLimits(data);
      } catch (err) {
        setLimitsError(err instanceof Error ? err.message : "Failed to load limits");
      } finally {
        setLimitsLoading(false);
      }
    };

    loadLimits();
  }, []);

  const usageRows = useMemo(() => {
    if (!limits) return [];

    return [
      {
        label: "Slack sources",
        used: limits.usage.slack_channels,
        limit: limits.limits.slack_channels,
      },
      {
        label: "Gmail labels",
        used: limits.usage.gmail_labels,
        limit: limits.limits.gmail_labels,
      },
      {
        label: "Notion pages",
        used: limits.usage.notion_pages,
        limit: limits.limits.notion_pages,
      },
      {
        label: "Daily tokens",
        used: limits.usage.daily_tokens_used,
        limit: limits.limits.daily_token_budget,
      },
      {
        label: "Active deliverables",
        used: limits.usage.active_deliverables,
        limit: limits.limits.active_deliverables,
      },
    ];
  }, [limits]);

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
  const nextTier: PlanTier | null = currentTier === "free" ? "starter" : currentTier === "starter" ? "pro" : null;

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

        <section className="p-4 border border-border rounded-lg space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">Current plan</div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${PLAN_META[currentTier].style}`}>
                  {PLAN_META[currentTier].icon === "sparkles" && <Sparkles className="w-4 h-4" />}
                  {PLAN_META[currentTier].icon === "zap" && <Zap className="w-4 h-4" />}
                  {PLAN_META[currentTier].label}
                </span>
                <span className="text-sm text-muted-foreground">
                  {PLAN_META[currentTier][billingPeriod === "monthly" ? "monthlyPrice" : "yearlyPrice"]}
                </span>
              </div>
            </div>
          </div>

          {status?.expires_at && (
            <p className="text-sm text-muted-foreground">
              Subscription renews on {formatDate(status.expires_at)}.
            </p>
          )}

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

          {nextTier && (
            <div className="p-3 bg-muted/30 rounded-lg flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Upgrade path</p>
                <p className="text-sm text-muted-foreground">
                  {currentTier === "free"
                    ? "Starter unlocks broader sync and higher daily limits."
                    : "Pro unlocks unlimited sources and deliverables."}
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => upgrade(nextTier, billingPeriod)}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <>
                    {nextTier === "pro" ? <Sparkles className="w-4 h-4 mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
                  </>
                )}
                Upgrade to {PLAN_META[nextTier].label} ({PLAN_META[nextTier][billingPeriod === "monthly" ? "monthlyPrice" : "yearlyPrice"]})
              </Button>
            </div>
          )}
        </section>

        <section className="p-4 border border-border rounded-lg space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-medium">Current usage and limits</h3>
            {!limitsLoading && limits && (
              <span className="text-xs text-muted-foreground">
                Sync: {formatSyncFrequency(limits.limits.sync_frequency)}
              </span>
            )}
          </div>

          {limitsLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading limits...
            </div>
          ) : limits ? (
            <div className="space-y-3">
              {usageRows.map((row) => {
                const percent = row.limit === -1 ? 0 : Math.min(100, Math.round((row.used / Math.max(1, row.limit)) * 100));
                return (
                  <div key={row.label} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span>{row.label}</span>
                      <span className="text-muted-foreground">{formatUsage(row.used, row.limit)}</span>
                    </div>
                    {row.limit !== -1 && (
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Unable to load usage summary{limitsError ? `: ${limitsError}` : "."}
            </p>
          )}
        </section>

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
