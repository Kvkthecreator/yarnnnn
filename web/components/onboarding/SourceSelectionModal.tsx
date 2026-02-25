'use client';

/**
 * ADR-057: Source Selection Modal
 *
 * Shows after OAuth callback to let user pick which sources to sync.
 * Enforces tier limits and triggers foreground import.
 */

import { useState, useEffect } from 'react';
import { Loader2, Check, Hash, Tag, FileText, Calendar, X, Sparkles, Lock, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Provider = 'slack' | 'gmail' | 'notion' | 'calendar';

interface LandscapeResource {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: string;
  metadata: Record<string, unknown>;
}

interface TierLimits {
  tier: 'free' | 'starter' | 'pro';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
  };
}

const PROVIDER_CONFIG: Record<Provider, {
  label: string;
  resourceLabel: string;
  resourceIcon: React.ReactNode;
  color: string;
  bgColor: string;
  limitField: keyof TierLimits['limits'];
}> = {
  slack: {
    label: 'Slack',
    resourceLabel: 'channels',
    resourceIcon: <Hash className="w-4 h-4" />,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    limitField: 'slack_channels',
  },
  gmail: {
    label: 'Gmail',
    resourceLabel: 'labels',
    resourceIcon: <Tag className="w-4 h-4" />,
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    limitField: 'gmail_labels',
  },
  notion: {
    label: 'Notion',
    resourceLabel: 'pages',
    resourceIcon: <FileText className="w-4 h-4" />,
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    limitField: 'notion_pages',
  },
  calendar: {
    label: 'Calendar',
    resourceLabel: 'calendars',
    resourceIcon: <Calendar className="w-4 h-4" />,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    limitField: 'calendars',
  },
};

interface SourceSelectionModalProps {
  provider: Provider;
  isOpen: boolean;
  onClose: () => void;
  onComplete: (selectedCount: number) => void;
}

export function SourceSelectionModal({
  provider,
  isOpen,
  onClose,
  onComplete,
}: SourceSelectionModalProps) {
  const config = PROVIDER_CONFIG[provider];

  const [loading, setLoading] = useState(true);
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [tierLimits, setTierLimits] = useState<TierLimits | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const limit = tierLimits?.limits[config.limitField] || 1;
  const atLimit = selectedIds.size >= limit;

  // Load resources and limits when modal opens
  useEffect(() => {
    if (!isOpen) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        const apiProvider = provider;

        // Load landscape and limits in parallel
        const [landscapeResult, limitsResult, calendarsResult] = await Promise.all([
          provider === 'calendar'
            ? Promise.resolve({ resources: [] })
            : api.integrations.getLandscape(apiProvider, true).catch(() => ({ resources: [] })),
          api.integrations.getLimits().catch(() => null),
          provider === 'calendar'
            ? api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] }))
            : Promise.resolve({ calendars: [] }),
        ]);

        // For calendar, convert to resource format
        if (provider === 'calendar' && calendarsResult?.calendars) {
          const calendarResources = calendarsResult.calendars.map(cal => ({
            id: cal.id,
            name: cal.summary,
            resource_type: 'calendar',
            coverage_state: 'uncovered',
            metadata: { primary: cal.primary },
          }));
          setResources(calendarResources);
        } else {
          // Sort by member count or relevance (most active first)
          const sorted = (landscapeResult.resources || []).sort((a, b) => {
            const aCount = (a.metadata?.member_count as number) || 0;
            const bCount = (b.metadata?.member_count as number) || 0;
            return bCount - aCount;
          });
          // Show top 10 for quick selection
          setResources(sorted.slice(0, 10));
        }

        setTierLimits(limitsResult);
      } catch (err) {
        console.error('Failed to load resources:', err);
        setError('Failed to load available sources');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [isOpen, provider]);

  const handleToggle = (resourceId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(resourceId)) {
        next.delete(resourceId);
      } else if (next.size < limit) {
        next.add(resourceId);
      }
      return next;
    });
  };

  const handleStartSync = async () => {
    if (selectedIds.size === 0) return;

    setSyncing(true);
    setError(null);

    try {
      const apiProvider = provider;

      // Save selected sources
      setSyncProgress('Saving selections...');
      await api.integrations.updateSources(apiProvider, Array.from(selectedIds));

      // Import each source
      for (const sourceId of Array.from(selectedIds)) {
        const resource = resources.find(r => r.id === sourceId);
        setSyncProgress(`Importing ${resource?.name || sourceId}...`);

        // For Gmail, prefix with 'label:'
        const resourceIdForImport = provider === 'gmail' ? `label:${sourceId}` : sourceId;

        // Start import job
        const job = await api.integrations.startImport(apiProvider, {
          resource_id: resourceIdForImport,
          resource_name: resource?.name,
          scope: {
            recency_days: 7,
            max_items: 100,
          },
        });

        // Poll for completion
        let status = job.status;
        while (status === 'pending' || status === 'fetching' || status === 'processing') {
          await new Promise(resolve => setTimeout(resolve, 1500));
          const updated = await api.integrations.getImportJob(job.id);
          status = updated.status;
        }
      }

      setSyncProgress('Done!');

      // Small delay to show completion
      await new Promise(resolve => setTimeout(resolve, 800));

      onComplete(selectedIds.size);
    } catch (err) {
      console.error('Sync failed:', err);
      setError(err instanceof Error ? err.message : 'Sync failed');
      setSyncing(false);
    }
  };

  const handleSkip = async () => {
    // Still save any selected sources (they'll sync on schedule)
    if (selectedIds.size > 0) {
      const apiProvider = provider;
      await api.integrations.updateSources(apiProvider, Array.from(selectedIds)).catch(() => {});
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', config.bgColor)}>
                <span className={config.color}>{config.resourceIcon}</span>
              </div>
              <div>
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  {config.label} Connected
                  <Check className="w-5 h-5 text-green-500" />
                </h2>
              </div>
            </div>
            {!syncing && (
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-muted rounded-md transition-colors"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-5">
          {syncing ? (
            <div className="text-center py-8">
              <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
              <p className="text-sm font-medium">{syncProgress}</p>
              <p className="text-xs text-muted-foreground mt-2">
                Building your context...
              </p>
            </div>
          ) : loading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mx-auto" />
              <p className="text-sm text-muted-foreground mt-2">Loading {config.resourceLabel}...</p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Close
              </button>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                Pick {limit === 1 ? `1 ${config.resourceLabel.slice(0, -1)}` : `up to ${limit} ${config.resourceLabel}`} to start building context:
              </p>

              {/* Resource list */}
              <div className="max-h-[280px] overflow-y-auto border border-border rounded-lg divide-y divide-border">
                {resources.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No {config.resourceLabel} found in this workspace.
                  </div>
                ) : (
                  resources.map((resource) => {
                    const isSelected = selectedIds.has(resource.id);
                    const isDisabled = !isSelected && atLimit;
                    const memberCount = resource.metadata?.member_count as number | undefined;
                    const isPrivate = resource.metadata?.is_private as boolean | undefined;
                    const isPrimary = resource.metadata?.primary as boolean | undefined;

                    return (
                      <button
                        key={resource.id}
                        onClick={() => handleToggle(resource.id)}
                        disabled={isDisabled}
                        className={cn(
                          'w-full px-3 py-2.5 flex items-center gap-3 text-left transition-colors',
                          isSelected ? 'bg-primary/5' : 'hover:bg-muted/50',
                          isDisabled && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {/* Checkbox */}
                        <div className={cn(
                          'w-5 h-5 rounded border-2 flex items-center justify-center shrink-0',
                          isSelected
                            ? 'bg-primary border-primary text-primary-foreground'
                            : 'border-muted-foreground/30'
                        )}>
                          {isSelected && <Check className="w-3 h-3" />}
                        </div>

                        {/* Icon */}
                        <span className="text-muted-foreground shrink-0">
                          {config.resourceIcon}
                        </span>

                        {/* Name and metadata */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium truncate">{resource.name}</span>
                            {isPrimary && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                Primary
                              </span>
                            )}
                            {isPrivate && (
                              <Lock className="w-3 h-3 text-muted-foreground" />
                            )}
                          </div>
                          {memberCount !== undefined && (
                            <span className="text-xs text-muted-foreground">
                              {memberCount.toLocaleString()} members
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Tier info */}
              {tierLimits && (
                <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-start gap-2 text-xs text-muted-foreground">
                    {tierLimits.tier === 'free' ? (
                      <>
                        <Sparkles className="w-3.5 h-3.5 mt-0.5 shrink-0 text-primary" />
                        <span>
                          Free tier: 1 {config.resourceLabel.slice(0, -1)}.
                          <button className="text-primary hover:underline ml-1">
                            Upgrade to Starter
                          </button>
                          {' '}for {config.limitField === 'slack_channels' ? 5 : config.limitField === 'gmail_labels' ? 5 : config.limitField === 'notion_pages' ? 5 : 3}.
                        </span>
                      </>
                    ) : (
                      <span>
                        {tierLimits.tier.charAt(0).toUpperCase() + tierLimits.tier.slice(1)} tier: {limit} {config.resourceLabel}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Actions */}
        {!syncing && !loading && !error && (
          <div className="p-5 pt-0 flex gap-3">
            <button
              onClick={handleSkip}
              className="flex-1 px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip for now
            </button>
            <button
              onClick={handleStartSync}
              disabled={selectedIds.size === 0}
              className="flex-1 px-4 py-2.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              Start Syncing
            </button>
          </div>
        )}
      </div>
    </div>
  );
}