"use client";

import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, Loader2, ExternalLink, Sparkles } from "lucide-react";

export function SubscriptionCard() {
  const { status, isPro, isLoading, error, upgrade, manageSubscription } = useSubscription();

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
        {isPro ? (
          /* Pro subscriber view */
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-full text-sm font-medium">
                <Sparkles className="w-4 h-4" />
                Pro
              </div>
              <span className="text-sm text-muted-foreground">Active</span>
            </div>

            {status?.expires_at && (
              <p className="text-sm text-muted-foreground">
                Your subscription renews on {formatDate(status.expires_at)}
              </p>
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
          /* Free tier view */
          <div className="space-y-6">
            {/* Plan comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Free plan */}
              <div className="p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">Free</h3>
                  <span className="text-xs px-2 py-0.5 bg-muted rounded-full">Current</span>
                </div>
                <ul className="text-sm text-muted-foreground space-y-2">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>1 project</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>50 memories per project</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <span>5 chat sessions per month</span>
                  </li>
                </ul>
              </div>

              {/* Pro plan */}
              <div className="p-4 border-2 border-primary rounded-lg relative">
                <div className="absolute -top-2.5 left-4 px-2 py-0.5 bg-primary text-primary-foreground text-xs font-medium rounded">
                  Recommended
                </div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">Pro</h3>
                  <span className="text-sm font-semibold">$19/mo</span>
                </div>
                <ul className="text-sm space-y-2">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited projects</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited memories</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Unlimited chat sessions</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Scheduled agents</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>Priority support</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Upgrade buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Button
                onClick={() => upgrade("monthly")}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                Upgrade to Pro
              </Button>
              <Button
                variant="outline"
                onClick={() => upgrade("yearly")}
                disabled={isLoading}
                className="flex-1"
              >
                Yearly (Save 16%)
              </Button>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Cancel anytime. Secure payment via Lemon Squeezy.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
