"use client";

import { Sparkles } from "lucide-react";
import { useSubscription } from "@/hooks/useSubscription";
import Link from "next/link";

interface ProBadgeProps {
  /** Show "Free" badge for free users, or hide completely */
  showFree?: boolean;
  /** Size variant */
  size?: "sm" | "md";
  /** Make it a link to billing */
  linkToBilling?: boolean;
}

export function ProBadge({
  showFree = true,
  size = "sm",
  linkToBilling = true,
}: ProBadgeProps) {
  const { isPro, isLoading } = useSubscription();

  if (isLoading) {
    return (
      <div
        className={`animate-pulse bg-muted rounded-full ${
          size === "sm" ? "h-5 w-12" : "h-6 w-14"
        }`}
      />
    );
  }

  const badge = isPro ? (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 bg-primary text-primary-foreground rounded-full font-medium ${
        size === "sm" ? "text-xs" : "text-sm"
      }`}
    >
      <Sparkles className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      Pro
    </span>
  ) : showFree ? (
    <span
      className={`inline-flex items-center px-2 py-0.5 bg-muted text-muted-foreground rounded-full font-medium ${
        size === "sm" ? "text-xs" : "text-sm"
      }`}
    >
      Free
    </span>
  ) : null;

  if (!badge) return null;

  if (linkToBilling) {
    return (
      <Link
        href="/settings?tab=billing"
        className="hover:opacity-80 transition-opacity"
        title={isPro ? "Manage subscription" : "Upgrade to Pro"}
      >
        {badge}
      </Link>
    );
  }

  return badge;
}

/**
 * "Pro" label for feature cards/buttons
 */
interface ProLabelProps {
  className?: string;
}

export function ProLabel({ className = "" }: ProLabelProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 bg-primary/10 text-primary rounded text-xs font-medium ${className}`}
    >
      <Sparkles className="w-3 h-3" />
      Pro
    </span>
  );
}

/**
 * Wrapper for Pro-only features that shows overlay/message for free users
 */
interface ProFeatureProps {
  children: React.ReactNode;
  /** Feature name for the upgrade prompt */
  feature?: "memories" | "sessions" | "agents" | "documents";
  /** Show as disabled instead of hidden */
  showDisabled?: boolean;
  /** Custom message */
  message?: string;
}

export function ProFeature({
  children,
  feature = "agents",
  showDisabled = true,
  message,
}: ProFeatureProps) {
  const { isPro } = useSubscription();

  if (isPro) {
    return <>{children}</>;
  }

  if (!showDisabled) {
    return null;
  }

  return (
    <div className="relative">
      <div className="opacity-50 pointer-events-none select-none">
        {children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-[1px] rounded-lg">
        <Link
          href="/settings?tab=billing"
          className="flex flex-col items-center gap-2 p-4 text-center hover:opacity-80 transition-opacity"
        >
          <ProLabel />
          <span className="text-sm text-muted-foreground">
            {message || "Upgrade to unlock this feature"}
          </span>
        </Link>
      </div>
    </div>
  );
}
