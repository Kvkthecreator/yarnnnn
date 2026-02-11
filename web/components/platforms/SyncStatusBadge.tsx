"use client";

import { differenceInHours, differenceInMinutes, differenceInDays, formatDistanceToNow } from "date-fns";
import { RefreshCw, CheckCircle2, Clock, AlertTriangle, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

type SyncLevel = "fresh" | "stale" | "old" | "never";

interface SyncStatus {
  level: SyncLevel;
  label: string;
  showRefresh: boolean;
}

/**
 * ADR-043: Calculate sync status from last sync timestamp
 */
function getSyncStatus(lastSyncAt: string | null): SyncStatus {
  if (!lastSyncAt) {
    return { level: "never", label: "Never synced", showRefresh: true };
  }

  const lastSync = new Date(lastSyncAt);
  const now = new Date();
  const hoursSince = differenceInHours(now, lastSync);
  const minutesSince = differenceInMinutes(now, lastSync);
  const daysSince = differenceInDays(now, lastSync);

  if (hoursSince < 1) {
    return { level: "fresh", label: `${minutesSince}m ago`, showRefresh: false };
  }
  if (hoursSince < 24) {
    return { level: "stale", label: `${hoursSince}h ago`, showRefresh: false };
  }
  return { level: "old", label: `${daysSince}d ago`, showRefresh: true };
}

interface SyncStatusBadgeProps {
  lastSyncAt: string | null;
  onRefresh?: () => void;
  refreshing?: boolean;
  showLabel?: boolean;
  size?: "sm" | "md";
  className?: string;
}

/**
 * ADR-043: Sync Status Badge
 *
 * Shows sync freshness indicator with optional refresh button.
 *
 * States:
 * - Fresh (< 1 hour): Green dot, "Xm ago"
 * - Stale (1-24 hours): Yellow dot, "Xh ago"
 * - Old (> 24 hours): Orange dot with warning, "Xd ago", shows refresh
 * - Never: Gray dot, "Never synced", shows refresh
 */
export function SyncStatusBadge({
  lastSyncAt,
  onRefresh,
  refreshing = false,
  showLabel = true,
  size = "sm",
  className,
}: SyncStatusBadgeProps) {
  const status = getSyncStatus(lastSyncAt);

  const config: Record<SyncLevel, { color: string; icon: React.ReactNode; textColor: string }> = {
    fresh: {
      color: "bg-green-500",
      icon: <CheckCircle2 className={size === "sm" ? "w-3 h-3" : "w-4 h-4"} />,
      textColor: "text-green-600 dark:text-green-400",
    },
    stale: {
      color: "bg-yellow-500",
      icon: <Clock className={size === "sm" ? "w-3 h-3" : "w-4 h-4"} />,
      textColor: "text-yellow-600 dark:text-yellow-400",
    },
    old: {
      color: "bg-orange-500",
      icon: <AlertTriangle className={size === "sm" ? "w-3 h-3" : "w-4 h-4"} />,
      textColor: "text-orange-600 dark:text-orange-400",
    },
    never: {
      color: "bg-gray-400 dark:bg-gray-600",
      icon: <Circle className={size === "sm" ? "w-3 h-3" : "w-4 h-4"} />,
      textColor: "text-muted-foreground",
    },
  };

  const { color, icon, textColor } = config[status.level];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5",
        size === "sm" ? "text-xs" : "text-sm",
        textColor,
        className
      )}
    >
      {/* Dot indicator */}
      <span className={cn("w-2 h-2 rounded-full", color)} />

      {/* Label */}
      {showLabel && <span>{status.label}</span>}

      {/* Refresh button */}
      {status.showRefresh && onRefresh && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRefresh();
          }}
          disabled={refreshing}
          className={cn(
            "p-1 rounded hover:bg-muted transition-colors",
            refreshing && "opacity-50 cursor-not-allowed"
          )}
          title="Refresh now"
        >
          <RefreshCw
            className={cn(
              size === "sm" ? "w-3 h-3" : "w-4 h-4",
              refreshing && "animate-spin"
            )}
          />
        </button>
      )}
    </span>
  );
}

/**
 * Inline variant for use within lists/cards
 */
export function SyncStatusInline({
  lastSyncAt,
  className,
}: {
  lastSyncAt: string | null;
  className?: string;
}) {
  const status = getSyncStatus(lastSyncAt);

  const dotColor: Record<SyncLevel, string> = {
    fresh: "bg-green-500",
    stale: "bg-yellow-500",
    old: "bg-orange-500",
    never: "bg-gray-400 dark:bg-gray-600",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs text-muted-foreground",
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", dotColor[status.level])} />
      {lastSyncAt ? (
        <span>Synced {formatDistanceToNow(new Date(lastSyncAt), { addSuffix: true })}</span>
      ) : (
        <span>Not synced</span>
      )}
    </span>
  );
}

/**
 * Compact dot-only variant
 */
export function SyncStatusDot({
  lastSyncAt,
  size = "sm",
  className,
}: {
  lastSyncAt: string | null;
  size?: "xs" | "sm" | "md";
  className?: string;
}) {
  const status = getSyncStatus(lastSyncAt);

  const dotColor: Record<SyncLevel, string> = {
    fresh: "bg-green-500",
    stale: "bg-yellow-500",
    old: "bg-orange-500",
    never: "bg-gray-400 dark:bg-gray-600",
  };

  const sizeClasses = {
    xs: "w-1.5 h-1.5",
    sm: "w-2 h-2",
    md: "w-2.5 h-2.5",
  };

  return (
    <span
      className={cn(
        "inline-block rounded-full",
        sizeClasses[size],
        dotColor[status.level],
        className
      )}
      title={status.label}
    />
  );
}

export default SyncStatusBadge;
