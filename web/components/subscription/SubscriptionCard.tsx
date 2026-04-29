"use client";

/**
 * ADR-172: Usage-first billing surface.
 * Balance is the single gate. Top-ups available for all users.
 * Pro subscription = $20/month auto-refill.
 */

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard, Loader2, Sparkles, Check, Zap } from "lucide-react";

const TOP_UP_OPTIONS = [
  { amount: 10, label: "$10" },
  { amount: 25, label: "$25" },
  { amount: 50, label: "$50" },
];

const COMPARE_ROWS: Array<{ label: string; free: string; pro: string }> = [
  { label: "Starter balance", free: "$3 one-time", pro: "$20/month included" },
  { label: "Top-ups", free: "$10 / $25 / $50", pro: "$10 / $25 / $50" },
  { label: "Auto-refill", free: "No", pro: "Yes — $20/month" },
  { label: "Chat, recurrences, agents", free: "All features", pro: "All features" },
];

export function SubscriptionCard() {
  const { status, isPaid, isLoading, error, upgrade, manageSubscription } = useSubscription();

  const [topupLoading, setTopupLoading] = useState<number | null>(null);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  const handleTopup = async (amount: number) => {
    setTopupLoading(amount);
    // Top-up uses same upgrade flow with topup checkout type
    await upgrade("monthly");
    setTopupLoading(null);
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        <CardDescription>Usage-based — your balance covers chat, recurrences, and web search</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* Current plan badge */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Plan</span>
          {isPaid ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-primary text-primary-foreground">
              <Sparkles className="w-3.5 h-3.5" />
              Pro
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
              Pay as you go
            </span>
          )}
          {isPaid && status?.expires_at && (
            <span className="text-xs text-muted-foreground">
              · Refills on {formatDate(status.expires_at)}
            </span>
          )}
        </div>

        {/* Top-up section */}
        <section className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="font-medium">Add balance</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            One-time top-ups, no subscription required.
          </p>
          <div className="flex gap-2">
            {TOP_UP_OPTIONS.map(({ amount, label }) => (
              <Button
                key={amount}
                variant="outline"
                size="sm"
                onClick={() => handleTopup(amount)}
                disabled={isLoading || topupLoading !== null}
                className="flex-1"
              >
                {topupLoading === amount ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  label
                )}
              </Button>
            ))}
          </div>
        </section>

        {/* Pro subscription section */}
        {!isPaid ? (
          <section className="p-4 border border-primary/20 bg-primary/5 rounded-lg space-y-4">
            <div>
              <h3 className="font-medium flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary" />
                Subscribe to Pro
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                $20/month balance auto-refill — never run out mid-workflow.
              </p>
            </div>

            <div className="space-y-1.5">
              {["$20 usage included every month", "Auto-refills on billing date", "Manage or cancel anytime"].map((feat) => (
                <div key={feat} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Check className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                  {feat}
                </div>
              ))}
            </div>

            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold">$19</span>
              <span className="text-muted-foreground text-sm">/month</span>
            </div>

            <div className="flex gap-2">
              <Button onClick={() => upgrade("monthly")} disabled={isLoading} className="flex-1">
                {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                Subscribe monthly
              </Button>
              <Button onClick={() => upgrade("yearly")} variant="outline" disabled={isLoading} className="flex-1">
                Yearly · $180
              </Button>
            </div>
          </section>
        ) : (
          <div>
            <Button variant="outline" onClick={manageSubscription} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CreditCard className="w-4 h-4 mr-2" />
              )}
              Manage Subscription
            </Button>
          </div>
        )}

        {/* Plan comparison */}
        <section className="p-4 border border-border rounded-lg">
          <p className="text-xs font-medium text-muted-foreground mb-3">Compare plans</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-3 font-medium text-muted-foreground"></th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">Pay as you go</th>
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
      </CardContent>
    </Card>
  );
}
