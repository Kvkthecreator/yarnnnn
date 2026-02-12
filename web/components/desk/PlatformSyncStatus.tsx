'use client';

/**
 * ADR-049: Platform Sync Status
 *
 * Shows connected platforms and their sync freshness on the welcome screen.
 * Helps users understand what data is available for deliverables.
 */

import { useEffect, useState } from 'react';
import { MessageSquare, Mail, FileText, RefreshCw, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name?: string | null;
  last_used_at?: string | null;
  created_at?: string;
}

interface SyncResource {
  resource_id: string;
  resource_name: string;
  last_synced: string | null;
  freshness_status: 'fresh' | 'recent' | 'stale' | 'unknown';
  items_synced: number;
}

interface SyncStatus {
  platform: string;
  synced_resources: SyncResource[];
  stale_count: number;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
}> = {
  slack: {
    icon: MessageSquare,
    label: 'Slack',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
  },
  gmail: {
    icon: Mail,
    label: 'Gmail',
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
  notion: {
    icon: FileText,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
  },
};

interface PlatformSyncStatusProps {
  className?: string;
}

export function PlatformSyncStatus({ className }: PlatformSyncStatusProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [syncStatuses, setSyncStatuses] = useState<Record<string, SyncStatus>>({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    setLoading(true);
    try {
      const data = await api.integrations.list();
      const activeIntegrations = data.integrations.filter((i: Integration) => i.status === 'active');
      setIntegrations(activeIntegrations);

      // Load sync status for each platform
      for (const integration of activeIntegrations) {
        try {
          const status = await api.integrations.getSyncStatus(integration.provider);
          setSyncStatuses((prev) => ({
            ...prev,
            [integration.provider]: status,
          }));
        } catch (err) {
          console.error(`Failed to get sync status for ${integration.provider}:`, err);
        }
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (provider: string) => {
    setSyncing(provider);
    try {
      // Trigger sync for all resources of this platform
      await api.integrations.syncPlatform(provider);
      // Refresh status after sync starts
      setTimeout(loadIntegrations, 2000);
    } catch (err) {
      console.error(`Failed to sync ${provider}:`, err);
    } finally {
      setSyncing(null);
    }
  };

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center gap-2 text-muted-foreground text-sm', className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Loading platforms...</span>
      </div>
    );
  }

  if (integrations.length === 0) {
    return (
      <div className={cn('text-center', className)}>
        <p className="text-sm text-muted-foreground mb-2">
          No platforms connected yet
        </p>
        <a
          href="/settings/integrations"
          className="text-sm text-primary hover:underline"
        >
          Connect Slack, Gmail, or Notion
        </a>
      </div>
    );
  }

  return (
    <div className={cn('max-w-md mx-auto', className)}>
      <p className="text-xs text-muted-foreground mb-3">Connected platforms</p>
      <div className="flex flex-wrap justify-center gap-2">
        {integrations.map((integration) => {
          const config = PLATFORM_CONFIG[integration.provider] || {
            icon: FileText,
            label: integration.provider,
            color: 'text-gray-600',
            bgColor: 'bg-gray-100',
          };
          const Icon = config.icon;
          const status = syncStatuses[integration.provider];
          const hasStale = status?.stale_count > 0;
          const resourceCount = status?.synced_resources?.length || 0;
          const isSyncing = syncing === integration.provider;

          // Find most recent sync
          const mostRecentSync = status?.synced_resources?.reduce((latest, r) => {
            if (!r.last_synced) return latest;
            if (!latest) return r.last_synced;
            return new Date(r.last_synced) > new Date(latest) ? r.last_synced : latest;
          }, null as string | null);

          return (
            <div
              key={integration.id}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg',
                config.bgColor,
                hasStale && 'ring-1 ring-amber-400'
              )}
            >
              <Icon className={cn('w-4 h-4', config.color)} />
              <div className="text-left">
                <span className="text-sm font-medium">{config.label}</span>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {resourceCount > 0 ? (
                    <>
                      {hasStale ? (
                        <AlertCircle className="w-3 h-3 text-amber-500" />
                      ) : (
                        <CheckCircle2 className="w-3 h-3 text-green-500" />
                      )}
                      <span>
                        {resourceCount} source{resourceCount !== 1 ? 's' : ''}
                        {mostRecentSync && (
                          <span className="ml-1">
                            · {formatDistanceToNow(new Date(mostRecentSync), { addSuffix: true })}
                          </span>
                        )}
                      </span>
                    </>
                  ) : (
                    <span>No data synced</span>
                  )}
                </div>
              </div>
              {(hasStale || resourceCount === 0) && (
                <button
                  onClick={() => handleSync(integration.provider)}
                  disabled={isSyncing}
                  className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
                  title="Sync now"
                >
                  <RefreshCw className={cn('w-3.5 h-3.5', isSyncing && 'animate-spin')} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PlatformSyncStatus;
