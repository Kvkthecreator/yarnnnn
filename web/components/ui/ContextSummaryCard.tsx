'use client';

/**
 * ADR-032 Phase 3: Context Summary Card
 *
 * Shows aggregate stats of cross-platform context available for a project.
 * "142 messages, 23 emails in last 7 days"
 */

import {
  Mail,
  Slack,
  FileText,
  Calendar,
  MessageSquare,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import type { ContextSummaryItem } from '@/types';

interface ContextSummaryCardProps {
  summary: ContextSummaryItem[];
  stats: {
    totalItems: number;
    platformCount: number;
    resourceCount: number;
    hasData: boolean;
  };
  isLoading?: boolean;
  days?: number;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  itemLabel: string;
}> = {
  slack: {
    icon: Slack,
    label: 'Slack',
    color: 'text-purple-600',
    itemLabel: 'messages',
  },
  gmail: {
    icon: Mail,
    label: 'Gmail',
    color: 'text-red-600',
    itemLabel: 'emails',
  },
  notion: {
    icon: FileText,
    label: 'Notion',
    color: 'text-gray-700',
    itemLabel: 'pages',
  },
  calendar: {
    icon: Calendar,
    label: 'Calendar',
    color: 'text-blue-600',
    itemLabel: 'events',
  },
};

export function ContextSummaryCard({
  summary,
  stats,
  isLoading,
  days = 7,
}: ContextSummaryCardProps) {
  if (isLoading) {
    return (
      <div className="p-4 border border-border rounded-lg bg-muted/30">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Loading context...</span>
        </div>
      </div>
    );
  }

  if (!stats.hasData) {
    return (
      <div className="p-4 border border-border rounded-lg bg-muted/30">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">No context yet</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Context from linked resources will appear here after syncing
        </p>
      </div>
    );
  }

  // Group by platform and sum items
  const platformStats = summary.reduce((acc, item) => {
    const platform = item.platform;
    if (!acc[platform]) {
      acc[platform] = { count: 0, latest: null as string | null };
    }
    acc[platform].count += item.item_count;
    if (item.latest_item && (!acc[platform].latest || item.latest_item > acc[platform].latest)) {
      acc[platform].latest = item.latest_item;
    }
    return acc;
  }, {} as Record<string, { count: number; latest: string | null }>);

  return (
    <div className="p-4 border border-border rounded-lg bg-gradient-to-br from-primary/5 to-transparent">
      {/* Header with total */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Context Available</span>
        </div>
        <span className="text-xs text-muted-foreground">Last {days} days</span>
      </div>

      {/* Total stat */}
      <div className="mb-4">
        <div className="text-2xl font-bold">{stats.totalItems.toLocaleString()}</div>
        <p className="text-xs text-muted-foreground">
          items from {stats.resourceCount} resource{stats.resourceCount !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Platform breakdown */}
      <div className="space-y-2">
        {Object.entries(platformStats).map(([platform, data]) => {
          const config = PLATFORM_CONFIG[platform];
          if (!config || data.count === 0) return null;

          const Icon = config.icon;

          return (
            <div
              key={platform}
              className="flex items-center justify-between py-1.5"
            >
              <div className="flex items-center gap-2">
                <Icon className={cn("w-4 h-4", config.color)} />
                <span className="text-sm">{config.label}</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-medium">{data.count.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground ml-1">{config.itemLabel}</span>
                {data.latest && (
                  <p className="text-[10px] text-muted-foreground">
                    Latest: {formatDistanceToNow(new Date(data.latest), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Compact version for inline use
 */
export function ContextSummaryBadge({
  stats,
  isLoading,
}: {
  stats: { totalItems: number; platformCount: number };
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
        <Loader2 className="w-3 h-3 animate-spin" />
        Loading...
      </span>
    );
  }

  if (stats.totalItems === 0) {
    return (
      <span className="text-xs text-muted-foreground">No context</span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <MessageSquare className="w-3 h-3 text-primary" />
      <span className="font-medium">{stats.totalItems.toLocaleString()}</span>
      <span className="text-muted-foreground">
        items from {stats.platformCount} platform{stats.platformCount !== 1 ? 's' : ''}
      </span>
    </span>
  );
}
