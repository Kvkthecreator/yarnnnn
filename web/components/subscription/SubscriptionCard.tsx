"use client";

/**
 * Billing pane — pure pay-as-you-go (ADR-171/172).
 *
 * Balance is the single gate. The only purchase is a one-time top-up
 * ($10 / $25 / $50). The recurring Pro subscription was retired from the
 * billing surface (2026-06-24) to match the public pricing model ("no
 * subscription"): an idle workspace costs nothing, an active operation costs
 * the usage it draws, and a monthly spend ceiling is set on the dedicated
 * Budget surface — not here. This pane is about FUNDING; the Budget dial is
 * about the CEILING.
 */

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Zap } from "lucide-react";

const TOP_UP_OPTIONS: Array<{ amount: 10 | 25 | 50; label: string }> = [
  { amount: 10, label: "$10" },
  { amount: 25, label: "$25" },
  { amount: 50, label: "$50" },
];

export function SubscriptionCard() {
  const { isLoading, error, topup } = useSubscription();
  const [topupLoading, setTopupLoading] = useState<number | null>(null);

  const handleTopup = async (amount: 10 | 25 | 50) => {
    setTopupLoading(amount);
    await topup(amount);
    // topup() redirects to checkout on success; on failure it clears loading
    // via the hook's error path, so reset the local spinner here too.
    setTopupLoading(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        <CardDescription>
          Pay-as-you-go — your balance covers chat, recurrences, and web search. Only what you use is charged.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5 text-sm text-destructive">
            {error.message}
          </div>
        )}

        {/* Plan badge — always pay-as-you-go; there is no other plan */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Plan</span>
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
            Pay as you go
          </span>
        </div>

        {/* Add balance */}
        <section className="p-4 border border-border rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="font-medium">Add balance</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            One-time top-ups — no subscription. Your balance is drawn down only by the usage
            that actually runs, at transparent rates you can read line by line.
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

        {/* How it works — honest, matches the public pricing page */}
        <section className="p-4 border border-border rounded-lg space-y-2 text-sm text-muted-foreground leading-relaxed">
          <p>
            <strong className="text-foreground">Idle costs nothing.</strong> The workspace and
            every file are free — only a running operation draws usage.
          </p>
          <p>
            <strong className="text-foreground">Hard stop at zero.</strong> If your balance runs
            out, the operation pauses — nothing is lost. Top up to resume.
          </p>
          <p>
            <strong className="text-foreground">Cap your monthly spend</strong> per operation on
            the Budget surface — a ceiling you set, not a charge.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
