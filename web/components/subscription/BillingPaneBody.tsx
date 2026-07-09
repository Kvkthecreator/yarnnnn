"use client";

/**
 * BillingPaneBody — the workspace's plan · balance · top-ups.
 *
 * ADR-416 (2026-07-08): the WORKSPACE is the billing unit — `balance_usd` +
 * `subscription_tier` live on `workspaces`, and the checkout/portal routes
 * target the ACTING workspace (authorized by billing authority — owner-default,
 * ADR-416 D1). So Billing lives in the Workspace Settings door (the
 * workspace-content door), not the account door.
 *
 * Because it manages a *workspace's* money and the active workspace can be
 * switched, the pane names the workspace it is billing (the incoherence the
 * operator caught: the old account-door Billing showed no workspace identity
 * and swapped silently on switch). The name comes from the active membership
 * row's `label` (the single canonical source, same as the UserMenu switcher).
 *
 * `subscription=success` (?query, set by the LS checkout return) shows a
 * one-time "balance updated" confirmation — carried over with the pane.
 */

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { SubscriptionCard } from "@/components/subscription/SubscriptionCard";
import { useWorkspaceMemberships } from "@/lib/workspace/viewer";

export function BillingPaneBody() {
  const searchParams = useSearchParams();
  const { memberships } = useWorkspaceMemberships();
  const activeWorkspaceName =
    memberships.find((m) => m.is_active)?.label ?? null;

  const subscriptionSuccess = searchParams.get("subscription") === "success";
  const [showSuccess, setShowSuccess] = useState(subscriptionSuccess);
  useEffect(() => {
    if (!subscriptionSuccess) return;
    const t = setTimeout(() => setShowSuccess(false), 6000);
    return () => clearTimeout(t);
  }, [subscriptionSuccess]);

  return (
    <div className="space-y-4">
      {showSuccess && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-foreground">
          <Check className="h-4 w-4 text-primary shrink-0" />
          Balance updated — thanks for the top-up.
        </div>
      )}
      {/* ADR-429 §13.3 — the workspace name headlines the card itself now (passed
          in), so the redundant subtitle line is gone. The card makes the workspace
          the clear subject of every section. */}
      <SubscriptionCard workspaceName={activeWorkspaceName} />
    </div>
  );
}
