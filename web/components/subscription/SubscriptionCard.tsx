"use client";

/**
 * ADR-053: Subscription card with 3-tier pricing (Free/Starter/Pro)
 */

import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, Loader2, ExternalLink, Sparkles, Zap } from "lucide-react";

export function SubscriptionCard() {
  const { status, tier, isPaid, isLoading, error, upgrade, manageSubscription } = useSubscription();

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

  if (error) {
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
        <CardTitle>Subscription</CardTitle>
        <CardDescription>
          Manage your yarnnn subscription and billing
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {isPaid ? (
          /* Paid subscriber view (Starter or Pro) */
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                tier === "pro"
                  ? "bg-primary text-primary-foreground"
                  : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              }`}>
                {tier === "pro" ? (
                  <Sparkles className="w-4 h-4" />
                ) : (
                  <Zap className="w-4 h-4" />
                )}
                {tier === "pro" ? "Pro" : "Starter"}
              </div>
              <span className="text-sm text-muted-foreground">Active</span>
            </div>

            {status?.expires_at && (
              <p className="text-sm text-muted-foreground">
                Your subscription renews on {formatDate(status.expires_at)}
              </p>
            )}

            {/* Upgrade prompt for Starter users */}
            {tier === "starter" && (
              <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
                <p className="text-sm font-medium mb-2">Want more?</p>
                <p className="text-sm text-muted-foreground mb-3">
                  Upgrade to Pro for hourly sync, unlimited conversations, and unlimited deliverables.
                </p>
                <Button
                  size="sm"
                  onClick={() => upgrade("pro", "monthly")}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Upgrade to Pro ($19/mo)
                </Button>
              </div>
            )}

            <div className="pt-2">
              <Button
                variant="outline"
                onClick={manageSubscription}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ExternalLink className="w-4 h-4 mr-2" />
                )}
                Manage Subscription
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                Update payment method, cancel, or view invoices
              </p>
            </div>
          </div>
        ) : (
          /* Free tier view - 3-tier comparison */
          <div className="space-y-6">
            {/* Plan comparison */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Free plan */}
              <div className="p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">Free</h3>
                  <span className="text-xs px-2 py-0.5 bg-muted rounded-full">Current</span>
                </div>
                <p className="text-2xl font-bold mb-3">$0</p>
                <ul className="text-sm text-muted-foreground space-y-2">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>All 4 platforms</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>5 sources per platform</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>1x/day sync</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>50k tokens/day</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>2 active deliverables</span>
                  </li>
                </ul>
              </div>

              {/* Starter plan - highlighted */}
              <div className="p-4 border-2 border-blue-500 rounded-lg relative">
                <div className="absolute -top-2.5 left-4 px-2 py-0.5 bg-blue-500 text-white text-xs font-medium rounded">
                  Best Value
                </div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">Starter</h3>
                </div>
                <p className="text-2xl font-bold mb-3">$9<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <span>All 4 platforms</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <span>15 sources per platform</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <span>4x/day sync</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <span>250k tokens/day</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <span>5 active deliverables</span>
                  </li>
                </ul>
              </div>

              {/* Pro plan */}
              <div className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">Pro</h3>
                </div>
                <p className="text-2xl font-bold mb-3">$19<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
                <ul className="text-sm space-y-2">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>All 4 platforms</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited sources</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Hourly sync</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited tokens</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited deliverables</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Upgrade buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Button
                onClick={() => upgrade("starter", "monthly")}
                disabled={isLoading}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4 mr-2" />
                )}
                Get Starter ($9/mo)
              </Button>
              <Button
                variant="outline"
                onClick={() => upgrade("pro", "monthly")}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                Get Pro ($19/mo)
              </Button>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Save 17% with yearly billing. Cancel anytime.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
