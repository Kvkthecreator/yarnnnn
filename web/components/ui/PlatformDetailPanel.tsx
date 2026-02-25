'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import {
  X,
  Mail,
  Slack,
  FileCode,
  Calendar,
  Loader2,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
  Hash,
  FileText,
  Tag,
  Plus,
  Settings2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import api from '@/lib/api/client';
import type { PlatformSummary } from './PlatformCard';
import { SourceSelectionModal } from '@/components/platforms/SourceSelectionModal';

/**
 * ADR-033 Phase 2: Platform Detail Panel
 *
 * Slide-out drawer showing platform details:
 * - Connection info
 * - Resources list (channels/labels/pages)
 * - Deliverables targeting this platform
 * - Recent context snippets
 */

interface PlatformDetailPanelProps {
  platform: PlatformSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onResourceClick?: (resourceId: string, resourceName: string) => void;
  onDeliverableClick?: (deliverableId: string) => void;
  onFullViewClick?: () => void;
  /** ADR-032: Create deliverable targeting this platform */
  onCreateDeliverableClick?: () => void;
}

interface LandscapeResource {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: 'uncovered' | 'partial' | 'covered' | 'stale' | 'excluded';
  last_extracted_at: string | null;
  items_extracted: number;
  metadata: Record<string, unknown>;
}

interface PlatformDeliverable {
  id: string;
  title: string;
  status: string;
  next_run_at?: string | null;
  deliverable_type: string;
  destination?: { platform?: string };
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
  resourceIcon: React.ReactNode;
  resourceLabel: string;
}> = {
  gmail: {
    icon: <Mail className="w-5 h-5" />,
    label: 'Gmail',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    resourceIcon: <Tag className="w-4 h-4" />,
    resourceLabel: 'Labels',
  },
  slack: {
    icon: <Slack className="w-5 h-5" />,
    label: 'Slack',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    resourceIcon: <Hash className="w-4 h-4" />,
    resourceLabel: 'Channels',
  },
  notion: {
    icon: <FileCode className="w-5 h-5" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    resourceIcon: <FileText className="w-4 h-4" />,
    resourceLabel: 'Pages',
  },
  google: {
    icon: <Calendar className="w-5 h-5" />,
    label: 'Google',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
  },
  calendar: {
    icon: <Calendar className="w-5 h-5" />,
    label: 'Calendar',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Events',
  },
};

function CoverageIndicator({ state }: { state: string }) {
  const config: Record<string, { color: string; label: string }> = {
    covered: { color: 'bg-green-500', label: 'Synced' },
    partial: { color: 'bg-yellow-500', label: 'Partial' },
    stale: { color: 'bg-orange-500', label: 'Stale' },
    uncovered: { color: 'bg-gray-300 dark:bg-gray-600', label: 'Not synced' },
    excluded: { color: 'bg-gray-200 dark:bg-gray-700', label: 'Excluded' },
  };
  const { color, label } = config[state] || config.uncovered;

  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className={cn('w-2 h-2 rounded-full', color)} />
      {label}
    </span>
  );
}

export function PlatformDetailPanel({
  platform,
  isOpen,
  onClose,
  onResourceClick,
  onDeliverableClick,
  onFullViewClick,
  onCreateDeliverableClick,
}: PlatformDetailPanelProps) {
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // ADR-043: Source selection modal state
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [sourceLimit, setSourceLimit] = useState<{ current: number; max: number } | null>(null);

  const config = platform
    ? PLATFORM_CONFIG[platform.provider] || {
      icon: <FileCode className="w-5 h-5" />,
      label: platform.provider,
      color: 'text-gray-500',
      bgColor: 'bg-gray-50 dark:bg-gray-800/50',
      resourceIcon: <FileText className="w-4 h-4" />,
      resourceLabel: 'Resources',
    }
    : null;

  useEffect(() => {
    if (isOpen && platform) {
      loadPlatformDetails();
    }
  }, [isOpen, platform?.provider]);

  const loadPlatformDetails = async (refresh = false) => {
    if (!platform) return;

    try {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Load landscape (resources), deliverables, and limits in parallel
      const [landscapeResult, deliverablesResult, limitsResult] = await Promise.all([
        api.integrations.getLandscape(
          platform.provider as 'slack' | 'notion' | 'gmail' | 'calendar',
          refresh
        ),
        api.deliverables.list(),
        api.integrations.getLimits(),
      ]);

      setResources(landscapeResult.resources || []);

      // Filter deliverables targeting this platform
      const platformDeliverables = (deliverablesResult || []).filter(
        (d: { destination?: { platform?: string } }) =>
          d.destination?.platform === platform.provider
      );
      setDeliverables(platformDeliverables);

      // ADR-053: Set source limits for this provider
      // Only use numeric limit fields (excludes sync_frequency)
      type NumericLimitKey = 'slack_channels' | 'gmail_labels' | 'notion_pages' | 'calendars' | 'total_platforms';
      const providerLimitMap: Record<string, NumericLimitKey> = {
        slack: 'slack_channels',
        gmail: 'gmail_labels',
        notion: 'notion_pages',
        google: 'gmail_labels',
        calendar: 'calendars',
      };
      type NumericUsageKey = 'slack_channels' | 'gmail_labels' | 'notion_pages' | 'calendars' | 'platforms_connected';
      const providerUsageMap: Record<string, NumericUsageKey> = {
        slack: 'slack_channels',
        gmail: 'gmail_labels',
        notion: 'notion_pages',
        google: 'gmail_labels',
        calendar: 'calendars',
      };
      const limitKey = providerLimitMap[platform.provider];
      const usageKey = providerUsageMap[platform.provider];
      if (limitKey && usageKey) {
        setSourceLimit({
          current: limitsResult.usage[usageKey],
          max: limitsResult.limits[limitKey],
        });
      }
    } catch (err) {
      console.error('Failed to load platform details:', err);
      setError('Failed to load details');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadPlatformDetails(true);
  };

  if (!isOpen || !platform || !config) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed right-0 top-0 bottom-0 w-full max-w-md bg-background border-l border-border shadow-xl z-50',
          'transform transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', config.bgColor, config.color)}>
              {config.icon}
            </div>
            <div>
              <h2 className="font-semibold">{config.label}</h2>
              {platform.workspace_name && (
                <p className="text-xs text-muted-foreground">
                  {platform.workspace_name}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={cn(
                'p-2 rounded-lg hover:bg-muted transition-colors',
                refreshing && 'opacity-50 cursor-not-allowed'
              )}
              title="Refresh"
            >
              <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-64px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">{error}</p>
              <button
                onClick={() => loadPlatformDetails()}
                className="text-sm text-primary hover:underline mt-2"
              >
                Try again
              </button>
            </div>
          ) : (
            <div className="p-4 space-y-6">
              {/* Connection Status */}
              <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                <div className="flex items-center gap-2">
                  {platform.status === 'active' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : platform.status === 'error' ? (
                    <AlertCircle className="w-4 h-4 text-red-500" />
                  ) : (
                    <Clock className="w-4 h-4 text-amber-500" />
                  )}
                  <span className="text-sm">
                    {platform.status === 'active'
                      ? 'Connected'
                      : platform.status === 'error'
                        ? 'Connection Error'
                        : 'Token Expired'}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  Since {formatDistanceToNow(new Date(platform.connected_at), { addSuffix: true })}
                </span>
              </div>

              {/* Resources Section */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium flex items-center gap-2">
                    {config.resourceIcon}
                    {config.resourceLabel}
                  </h3>
                  <div className="flex items-center gap-2">
                    {/* ADR-043: Show source count with limit */}
                    {sourceLimit && (
                      <span className="text-xs text-muted-foreground">
                        {sourceLimit.current}/{sourceLimit.max}
                      </span>
                    )}
                    {/* ADR-043: Manage Sources button */}
                    <button
                      onClick={() => setShowSourceModal(true)}
                      className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                    >
                      <Settings2 className="w-3 h-3" />
                      Manage
                    </button>
                  </div>
                </div>

                {resources.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No {config.resourceLabel.toLowerCase()} discovered yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {resources.slice(0, 10).map((resource) => (
                      <button
                        key={resource.id}
                        onClick={() => onResourceClick?.(resource.id, resource.name)}
                        className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium truncate">
                            {resource.name}
                          </span>
                          <CoverageIndicator state={resource.coverage_state} />
                        </div>
                        {resource.items_extracted > 0 && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {resource.items_extracted} items extracted
                            {resource.last_extracted_at && (
                              <> · {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                            )}
                          </p>
                        )}
                      </button>
                    ))}

                    {resources.length > 10 && (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        +{resources.length - 10} more
                      </p>
                    )}
                  </div>
                )}
              </section>

              {/* Deliverables Section */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium">Deliverables</h3>
                  <span className="text-xs text-muted-foreground">
                    {deliverables.length} targeting {config.label}
                  </span>
                </div>

                {deliverables.length === 0 ? (
                  <div className="text-center py-4">
                    <p className="text-sm text-muted-foreground mb-3">
                      No deliverables target {config.label} yet
                    </p>
                    {onCreateDeliverableClick && (
                      <button
                        onClick={onCreateDeliverableClick}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        Create deliverable
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {deliverables.slice(0, 5).map((deliverable) => (
                      <button
                        key={deliverable.id}
                        onClick={() => onDeliverableClick?.(deliverable.id)}
                        className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">
                            {deliverable.title}
                          </span>
                          <span
                            className={cn(
                              'text-xs px-2 py-0.5 rounded',
                              deliverable.status === 'active'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-muted text-muted-foreground'
                            )}
                          >
                            {deliverable.status}
                          </span>
                        </div>
                        {deliverable.next_run_at && (
                          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Next: {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
                          </p>
                        )}
                      </button>
                    ))}

                    {deliverables.length > 5 && (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        +{deliverables.length - 5} more
                      </p>
                    )}

                    {/* ADR-032: Create deliverable action */}
                    {onCreateDeliverableClick && (
                      <button
                        onClick={onCreateDeliverableClick}
                        className="w-full p-3 border-2 border-dashed border-primary/30 rounded-lg hover:border-primary/50 hover:bg-primary/5 text-left transition-colors"
                      >
                        <div className="flex items-center gap-2 text-sm text-primary">
                          <Plus className="w-4 h-4" />
                          Create another deliverable
                        </div>
                      </button>
                    )}
                  </div>
                )}
              </section>

              {/* Activity Summary */}
              {platform.activity_7d > 0 && (
                <section className="p-3 bg-muted/30 rounded-lg">
                  <h3 className="text-sm font-medium mb-1">Recent Activity</h3>
                  <p className="text-xs text-muted-foreground">
                    {platform.activity_7d} items captured in the last 7 days
                  </p>
                </section>
              )}

              {/* Full View Link */}
              {onFullViewClick && (
                <button
                  onClick={onFullViewClick}
                  className="w-full p-3 border border-dashed border-border rounded-lg hover:bg-muted text-center transition-colors group"
                >
                  <span className="text-sm text-muted-foreground group-hover:text-foreground flex items-center justify-center gap-2">
                    View all {config.label} details
                    <ExternalLink className="w-4 h-4" />
                  </span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ADR-043: Source Selection Modal */}
      {platform && (
        <SourceSelectionModal
          isOpen={showSourceModal}
          onClose={() => setShowSourceModal(false)}
          onSuccess={() => {
            setShowSourceModal(false);
            loadPlatformDetails(true); // Refresh after source changes
          }}
          provider={platform.provider as 'slack' | 'gmail' | 'notion'}
        />
      )}
    </>
  );
}
