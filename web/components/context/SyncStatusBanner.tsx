'use client';

import { Check, Clock, RefreshCw, Sparkles, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const SYNC_FREQUENCY_LABELS: Record<string, { label: string; description: string; icon: React.ReactNode }> = {
  '1x_daily': {
    label: 'Daily',
    description: 'Syncs once per day at 8am in your timezone',
    icon: <Clock className="w-4 h-4" />,
  },
  '2x_daily': {
    label: '2x daily',
    description: 'Syncs at 8am and 6pm in your timezone',
    icon: <Clock className="w-4 h-4" />,
  },
  '4x_daily': {
    label: '4x daily',
    description: 'Syncs every 6 hours',
    icon: <RefreshCw className="w-4 h-4" />,
  },
  'hourly': {
    label: 'Hourly',
    description: 'Syncs every hour for near real-time context',
    icon: <Zap className="w-4 h-4" />,
  },
};

function formatNextSync(isoString: string | null | undefined): string | null {
  if (!isoString) return null;
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();

    if (diffMs < 0) return 'Soon';

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffHours === 0) {
      return `in ${diffMins} min`;
    } else if (diffHours < 24) {
      return `in ${diffHours}h ${diffMins}m`;
    } else {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  } catch {
    return null;
  }
}

interface SyncStatusBannerProps {
  tier: string;
  syncFrequency: string;
  nextSync?: string | null;
  selectedCount: number;
  syncedCount: number;
  lastSyncedAt?: string | null;
}

export function SyncStatusBanner({
  tier,
  syncFrequency,
  nextSync,
  selectedCount,
  syncedCount,
  lastSyncedAt,
}: SyncStatusBannerProps) {
  const frequencyInfo = SYNC_FREQUENCY_LABELS[syncFrequency] || SYNC_FREQUENCY_LABELS['2x_daily'];
  const nextSyncFormatted = formatNextSync(nextSync);

  // No sources selected AND no synced content — prompt to select
  if (selectedCount === 0 && syncedCount === 0) {
    return (
      <div className="p-4 bg-muted/50 border border-border rounded-lg">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-muted-foreground mt-0.5" />
          <div>
            <p className="text-sm font-medium">No sources selected</p>
            <p className="text-sm text-muted-foreground mt-1">
              Select sources below to start syncing context. Your {tier} plan syncs {frequencyInfo.label.toLowerCase()}.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Sources selected but none synced yet — pending state
  if (selectedCount > 0 && syncedCount === 0) {
    return (
      <div className="p-4 bg-muted/50 border border-border rounded-lg">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-muted-foreground mt-0.5" />
          <div>
            <p className="text-sm font-medium">{selectedCount} selected — awaiting first sync</p>
            <p className="text-sm text-muted-foreground mt-1">
              Your {tier} plan syncs {frequencyInfo.label.toLowerCase()}.
              {nextSyncFormatted && ` Next sync ${nextSyncFormatted}.`}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
            <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Syncing {selectedCount} source{selectedCount !== 1 ? 's' : ''} · {frequencyInfo.label}
            </p>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">
              {lastSyncedAt
                ? `Last synced ${formatDistanceToNow(new Date(lastSyncedAt), { addSuffix: true })}`
                : frequencyInfo.description}
            </p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-300">
            {frequencyInfo.icon}
            <span className="font-medium">{frequencyInfo.label}</span>
          </div>
          {nextSyncFormatted && (
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              Next sync {nextSyncFormatted}
            </p>
          )}
        </div>
      </div>

      {/* Upgrade prompt for free tier */}
      {tier === 'free' && (
        <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-800">
          <p className="text-xs text-green-700 dark:text-green-300">
            <Sparkles className="w-3 h-3 inline mr-1" />
            Upgrade to <span className="font-medium">Starter</span> for 4x/day sync or{' '}
            <span className="font-medium">Pro</span> for hourly sync
          </p>
        </div>
      )}
      {tier === 'starter' && (
        <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-800">
          <p className="text-xs text-green-700 dark:text-green-300">
            <Zap className="w-3 h-3 inline mr-1" />
            Upgrade to <span className="font-medium">Pro</span> for hourly sync
          </p>
        </div>
      )}
    </div>
  );
}
