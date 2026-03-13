"use client";

/**
 * ADR-100: Billing surface with 2-tier display (Free/Pro).
 * Split views: Free users see upgrade card with radio pricing. Pro users see plan summary + billing portal.
 */

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard, Loader2, Sparkles, Check, ChevronDown, ChevronUp } from "lucide-react";

type PricingOption = "monthly" | "yearly" | "early_bird";

const PRICING_OPTIONS: Array<{
  id: PricingOption;
  label: string;
  price: string;
  detail?: string;
}> = [
  { id: "monthly", label: "Monthly", price: "$19/mo" },
  { id: "yearly", label: "Yearly", price: "$180/yr", detail: "Save ~17%" },
  { id: "early_bird", label: "Early Bird", price: "$9/mo", detail: "Limited" },
];

const PRO_FEATURES = [
  "Unlimited messages",
  "10 active agents",
  "Hourly sync",
  "Unlimited sources",
  "Priority support",
];

const COMPARE_ROWS: Array<{ label: string; free: string; pro: string }> = [
  { label: "Platforms", free: "4", pro: "4" },
  { label: "Slack sources", free: "5", pro: "Unlimited" },
  { label: "Gmail labels", free: "5", pro: "Unlimited" },
  { label: "Notion pages", free: "10", pro: "Unlimited" },
  { label: "Calendars", free: "Unlimited", pro: "Unlimited" },
  { label: "Sync frequency", free: "1x daily", pro: "Hourly" },
  { label: "Monthly messages", free: "50", pro: "Unlimited" },
  { label: "Active agents", free: "2", pro: "10" },
  { label: "Priority support", free: "No", pro: "Yes" },
];

function getPlanPriceLabel(plan: string | null | undefined): string {
  if (plan === "pro_early_bird") return "$9/mo";
  if (plan === "pro_yearly") return "$180/yr";
  return "$19/mo";
}

export function SubscriptionCard() {
  const { status, isPaid, isEarlyBird, isLoading, error, upgrade, manageSubscription } = useSubscription();

  const [selectedPricing, setSelectedPricing] = useState<PricingOption>("early_bird");
  const [showCompare, setShowCompare] = useState(false);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const handleUpgrade = () => {
    if (selectedPricing === "early_bird") {
      upgrade("monthly", true);
    } else {
      upgrade(selectedPricing === "yearly" ? "yearly" : "monthly");
    }
  };

  const selectedOption = PRICING_OPTIONS.find((o) => o.id === selectedPricing)!;

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

  // ── Pro User View ──────────────────────────────────────────────
  if (isPaid) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Subscription</CardTitle>
          <CardDescription>Manage your yarnnn subscription and billing</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
              {error.message}
            </div>
          )}

          <section className="p-4 border border-border rounded-lg space-y-4">
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-primary text-primary-foreground">
                <Sparkles className="w-4 h-4" />
                Pro
              </span>
              {isEarlyBird && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                  Early Bird
                </span>
              )}
              <span className="text-sm text-muted-foreground">
                {getPlanPriceLabel(status?.plan)}
              </span>
            </div>

            {status?.expires_at && (
              <p className="text-sm text-muted-foreground">
                Renews on {formatDate(status.expires_at)}.
              </p>
            )}

            <div className="grid grid-cols-2 gap-2 pt-1">
              {PRO_FEATURES.map((feat) => (
                <div key={feat} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Check className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                  {feat}
                </div>
              ))}
            </div>
          </section>

          <div>
            <Button variant="outline" onClick={manageSubscription} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CreditCard className="w-4 h-4 mr-2" />
              )}
              Manage Billing
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Free User View ─────────────────────────────────────────────
  return (
    <Card>
      <CardHeader>
        <CardTitle>Subscription</CardTitle>
        <CardDescription>Manage your yarnnn subscription and billing</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* Current plan indicator */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Current plan</span>
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
            Free
          </span>
        </div>

        {/* Upgrade card */}
        <section className="p-4 border border-primary/20 bg-primary/5 rounded-lg space-y-5">
          <div>
            <h3 className="font-medium flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              Upgrade to Pro
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Unlimited messages, 10 agents, hourly sync, unlimited sources.
            </p>
          </div>

          {/* Radio pricing options */}
          <div className="space-y-2">
            {PRICING_OPTIONS.map((option) => (
              <label
                key={option.id}
                className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedPricing === option.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/40"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
                      selectedPricing === option.id ? "border-primary" : "border-muted-foreground/40"
                    }`}
                  >
                    {selectedPricing === option.id && (
                      <div className="w-2 h-2 rounded-full bg-primary" />
                    )}
                  </div>
                  <span className="text-sm font-medium">{option.label}</span>
                  {option.detail && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                      {option.detail}
                    </span>
                  )}
                </div>
                <span className="text-sm font-medium">{option.price}</span>
                <input
                  type="radio"
                  name="pricing"
                  value={option.id}
                  checked={selectedPricing === option.id}
                  onChange={() => setSelectedPricing(option.id)}
                  className="sr-only"
                />
              </label>
            ))}
          </div>

          <Button onClick={handleUpgrade} disabled={isLoading} className="w-full">
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 mr-2" />
            )}
            Upgrade — {selectedOption.price}
          </Button>
        </section>

        {/* Collapsible plan comparison */}
        <button
          onClick={() => setShowCompare(!showCompare)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {showCompare ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          Compare plans
        </button>

        {showCompare && (
          <section className="p-4 border border-border rounded-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 pr-3 font-medium text-muted-foreground">Feature</th>
                    <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        Free
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-foreground">Current</span>
                      </span>
                    </th>
                    <th className="text-left py-2 px-2 font-medium text-foreground">Pro</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARE_ROWS.map((row) => (
                    <tr key={row.label} className="border-b border-border last:border-b-0">
                      <td className="py-2 pr-3 text-muted-foreground">{row.label}</td>
                      <td className="py-2 px-2">{row.free}</td>
                      <td className="py-2 px-2">{row.pro}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}