"use client";

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { X, Sparkles, Loader2, Check } from "lucide-react";
import { SUBSCRIPTION_LIMITS, formatLimit } from "@/lib/subscription/limits";

interface UpgradePromptProps {
  /** What triggered the prompt */
  feature: "memories" | "sessions" | "agents" | "documents";
  /** Current usage count */
  currentUsage?: number;
  /** Whether to show as modal or inline banner */
  variant?: "modal" | "banner";
  /** Callback when user dismisses */
  onDismiss?: () => void;
  /** Custom title */
  title?: string;
  /** Custom description */
  description?: string;
}

const FEATURE_COPY = {
  memories: {
    title: "Store more memories",
    description: "You've reached the memory limit for this project. Upgrade to Pro for unlimited memories.",
    icon: "brain",
  },
  sessions: {
    title: "More chat sessions",
    description: "You've used all your chat sessions this month. Upgrade to Pro for unlimited conversations.",
    icon: "message",
  },
  agents: {
    title: "Unlock scheduled agents",
    description: "Scheduled agents are a Pro feature. Automate recurring work like reports and research.",
    icon: "calendar",
  },
  documents: {
    title: "Upload more documents",
    description: "You've reached the document limit. Upgrade to Pro for unlimited document uploads.",
    icon: "file",
  },
};

export function UpgradePrompt({
  feature,
  currentUsage,
  variant = "modal",
  onDismiss,
  title,
  description,
}: UpgradePromptProps) {
  const { upgrade, isLoading } = useSubscription();
  const [upgrading, setUpgrading] = useState(false);

  const copy = FEATURE_COPY[feature];
  const limit = SUBSCRIPTION_LIMITS.free[
    feature === "sessions" ? "dailyTokenBudget" :
    feature === "agents" ? "activeDeliverables" :
    feature === "memories" ? "documents" : // memories no longer have a dedicated limit
    feature
  ];

  const handleUpgrade = async () => {
    setUpgrading(true);
    // ADR-053: Default to Starter tier for upgrade prompts
    await upgrade("starter", "monthly");
  };

  const proFeatures = [
    "Unlimited sources",
    "Hourly sync",
    "Unlimited tokens",
    "Unlimited deliverables",
    "Signal processing",
  ];

  if (variant === "banner") {
    return (
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20 rounded-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="font-medium">{title || copy.title}</p>
            <p className="text-sm text-muted-foreground">
              {description || copy.description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleUpgrade}
            disabled={upgrading || isLoading}
            size="sm"
          >
            {upgrading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "Upgrade"
            )}
          </Button>
          {onDismiss && (
            <Button variant="ghost" size="sm" onClick={onDismiss}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Modal variant
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-xl max-w-md w-full shadow-xl">
        {/* Header */}
        <div className="p-6 pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-primary/10 rounded-xl">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">{title || copy.title}</h2>
                {currentUsage !== undefined && (
                  <p className="text-sm text-muted-foreground">
                    {currentUsage}/{formatLimit(limit)} used
                  </p>
                )}
              </div>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="p-1 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 pb-4">
          <p className="text-muted-foreground mb-6">
            {description || copy.description}
          </p>

          {/* Pro features list */}
          <div className="p-4 bg-muted/30 rounded-lg mb-6">
            <p className="text-sm font-medium mb-3">Pro includes:</p>
            <ul className="space-y-2">
              {proFeatures.map((feat) => (
                <li key={feat} className="flex items-center gap-2 text-sm">
                  <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                  {feat}
                </li>
              ))}
            </ul>
          </div>

          {/* Price */}
          <div className="text-center mb-6">
            <span className="text-3xl font-bold">$19</span>
            <span className="text-muted-foreground">/month</span>
          </div>
        </div>

        {/* Actions */}
        <div className="p-6 pt-0 flex flex-col gap-3">
          <Button
            onClick={handleUpgrade}
            disabled={upgrading || isLoading}
            className="w-full"
            size="lg"
          >
            {upgrading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Redirecting...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Upgrade to Pro
              </>
            )}
          </Button>
          {onDismiss && (
            <Button variant="ghost" onClick={onDismiss} className="w-full">
              Maybe later
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Inline usage indicator with optional upgrade prompt
 */
interface UsageIndicatorProps {
  current: number;
  limit: number;
  label: string;
  showUpgrade?: boolean;
  feature: UpgradePromptProps["feature"];
}

export function UsageIndicator({
  current,
  limit,
  label,
  showUpgrade = true,
  feature,
}: UsageIndicatorProps) {
  const [showPrompt, setShowPrompt] = useState(false);
  const isUnlimited = limit === -1;
  const percentUsed = isUnlimited ? 0 : Math.min((current / limit) * 100, 100);
  const isNearLimit = percentUsed >= 80;
  const isAtLimit = percentUsed >= 100;

  return (
    <>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{label}</span>
          <span className={isAtLimit ? "text-destructive font-medium" : ""}>
            {current}/{formatLimit(limit)}
          </span>
        </div>
        {!isUnlimited && (
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                isAtLimit
                  ? "bg-destructive"
                  : isNearLimit
                  ? "bg-yellow-500"
                  : "bg-primary"
              }`}
              style={{ width: `${percentUsed}%` }}
            />
          </div>
        )}
        {isAtLimit && showUpgrade && (
          <button
            onClick={() => setShowPrompt(true)}
            className="text-xs text-primary hover:underline"
          >
            Upgrade to get more
          </button>
        )}
      </div>

      {showPrompt && (
        <UpgradePrompt
          feature={feature}
          currentUsage={current}
          onDismiss={() => setShowPrompt(false)}
        />
      )}
    </>
  );
}
