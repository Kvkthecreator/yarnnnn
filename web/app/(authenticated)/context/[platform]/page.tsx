'use client';

/**
 * Platform Detail Page
 *
 * ADR-033 Phase 4: Full platform view with resources, coverage, and deliverables.
 * Route: /context/[platform] (e.g., /context/slack, /context/gmail)
 *
 * Shows:
 * - Connection status and workspace info
 * - Resources list (channels/labels/pages/calendars) with coverage state
 * - Sync timestamps and item counts
 * - Deliverables targeting this platform
 * - Recent context extracted from this platform
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  Settings2,
  Plus,
  CheckCircle2,
  AlertCircle,
  Clock,
  XCircle,
  ExternalLink,
  Hash,
  Tag,
  FileText,
  Calendar,
  Slack,
  Mail,
  FileCode,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { SourceSelectionModal } from '@/components/platforms/SourceSelectionModal';

// =============================================================================
// Types
// =============================================================================

type PlatformProvider = 'slack' | 'gmail' | 'notion' | 'google' | 'calendar';

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

interface PlatformMemory {
  id: string;
  content: string;
  tags: string[];
  source_ref?: {
    platform?: string;
    resource_id?: string;
    resource_name?: string;
  };
  created_at: string;
}

interface IntegrationData {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  created_at: string;
  last_used_at: string | null;
}

// =============================================================================
// Platform Configuration
// =============================================================================

const PLATFORM_CONFIG: Record<PlatformProvider, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
  resourceIcon: React.ReactNode;
  resourceLabel: string;
  resourceLabelSingular: string;
}> = {
  slack: {
    icon: <Slack className="w-6 h-6" />,
    label: 'Slack',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    resourceIcon: <Hash className="w-4 h-4" />,
    resourceLabel: 'Channels',
    resourceLabelSingular: 'channel',
  },
  gmail: {
    icon: <Mail className="w-6 h-6" />,
    label: 'Gmail',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    resourceIcon: <Tag className="w-4 h-4" />,
    resourceLabel: 'Labels',
    resourceLabelSingular: 'label',
  },
  notion: {
    icon: <FileCode className="w-6 h-6" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    resourceIcon: <FileText className="w-4 h-4" />,
    resourceLabel: 'Pages',
    resourceLabelSingular: 'page',
  },
  google: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Google',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
    resourceLabelSingular: 'calendar',
  },
  calendar: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Calendar',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
    resourceLabelSingular: 'calendar',
  },
};

// =============================================================================
// Main Component
// =============================================================================

export default function PlatformDetailPage() {
  const params = useParams();
  const router = useRouter();
  const platform = params.platform as PlatformProvider;

  // Validate platform
  const config = PLATFORM_CONFIG[platform];
  const isValidPlatform = !!config;

  // State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data
  const [integration, setIntegration] = useState<IntegrationData | null>(null);
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [coverageSummary, setCoverageSummary] = useState<{
    total_resources: number;
    covered_count: number;
    coverage_percentage: number;
  } | null>(null);
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  const [recentMemories, setRecentMemories] = useState<PlatformMemory[]>([]);
  const [sourceLimit, setSourceLimit] = useState<{ current: number; max: number } | null>(null);

  // Modal state
  const [showSourceModal, setShowSourceModal] = useState(false);

  // =============================================================================
  // Data Loading
  // =============================================================================

  const loadData = useCallback(async (refresh = false) => {
    if (!isValidPlatform) return;

    try {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Load all data in parallel
      const [integrationResult, landscapeResult, deliverablesResult, memoriesResult, limitsResult] = await Promise.all([
        api.integrations.get(platform).catch(() => null),
        api.integrations.getLandscape(platform, refresh).catch(() => ({ resources: [], coverage_summary: null })),
        api.deliverables.list().catch(() => []),
        api.userMemories.list().catch(() => []),
        api.integrations.getLimits().catch(() => ({ limits: {} })),
      ]);

      setIntegration(integrationResult);
      setResources(landscapeResult.resources || []);
      setCoverageSummary(landscapeResult.coverage_summary || null);

      // Filter deliverables targeting this platform
      const platformDeliverables = (deliverablesResult || []).filter(
        (d: PlatformDeliverable) => d.destination?.platform === platform
      );
      setDeliverables(platformDeliverables);

      // Filter memories from this platform (most recent 10)
      const platformMemories = (memoriesResult || [])
        .filter((m: PlatformMemory) => m.source_ref?.platform === platform)
        .slice(0, 10);
      setRecentMemories(platformMemories);

      // Get source limits
      const limitField = platform === 'slack' ? 'slack_channels' :
                        platform === 'gmail' ? 'gmail_labels' :
                        platform === 'notion' ? 'notion_pages' :
                        'gmail_labels'; // fallback for google/calendar
      const limits = limitsResult.limits as Record<string, number> | undefined;
      const maxLimit = limits?.[limitField] || 5;
      const currentCount = (landscapeResult.resources || []).filter(
        (r: LandscapeResource) => r.coverage_state === 'covered' || r.coverage_state === 'partial'
      ).length;
      setSourceLimit({ current: currentCount, max: maxLimit });

    } catch (err) {
      console.error('Failed to load platform data:', err);
      setError('Failed to load platform data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [platform, isValidPlatform]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // =============================================================================
  // Handlers
  // =============================================================================

  const handleCreateDeliverable = () => {
    router.push(`/deliverables/new?platform=${platform}`);
  };

  const handleViewDeliverable = (id: string) => {
    router.push(`/deliverables/${id}`);
  };

  const handleSourceModalSuccess = () => {
    setShowSourceModal(false);
    loadData(true);
  };

  // =============================================================================
  // Render: Invalid Platform
  // =============================================================================

  if (!isValidPlatform) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <h2 className="text-lg font-medium mb-2">Unknown Platform</h2>
          <p className="text-sm text-muted-foreground mb-4">
            The platform "{platform}" is not recognized.
          </p>
          <button
            onClick={() => router.push('/context')}
            className="text-sm text-primary hover:underline"
          >
            Back to Context
          </button>
        </div>
      </div>
    );
  }

  // =============================================================================
  // Render: Loading
  // =============================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // =============================================================================
  // Render: Not Connected
  // =============================================================================

  if (!integration) {
    return (
      <div className="h-full">
        <div className="border-b border-border px-6 py-4">
          <button
            onClick={() => router.push('/context')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Context
          </button>
        </div>
        <div className="flex items-center justify-center h-[calc(100%-60px)]">
          <div className="text-center max-w-md">
            <div className={cn('w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center', config.bgColor)}>
              <span className={config.color}>{config.icon}</span>
            </div>
            <h2 className="text-xl font-medium mb-2">{config.label} Not Connected</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Connect {config.label} to import context from your {config.resourceLabel.toLowerCase()}.
            </p>
            <button
              onClick={() => router.push('/settings?tab=integrations')}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90"
            >
              Connect {config.label}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =============================================================================
  // Render: Main Content
  // =============================================================================

  const syncedCount = resources.filter(r => r.coverage_state === 'covered' || r.coverage_state === 'partial').length;
  const totalItems = resources.reduce((sum, r) => sum + r.items_extracted, 0);

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/context')}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4" />
              Context
            </button>
            <div className="flex items-center gap-3">
              <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', config.bgColor)}>
                <span className={config.color}>{config.icon}</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold">{config.label}</h1>
                {integration.workspace_name && (
                  <p className="text-sm text-muted-foreground">{integration.workspace_name}</p>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="p-2 rounded-md hover:bg-muted transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
            </button>
            <button
              onClick={() => router.push('/settings?tab=integrations')}
              className="p-2 rounded-md hover:bg-muted transition-colors"
              title="Settings"
            >
              <Settings2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-8">
        {/* Connection Status */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            {integration.status === 'connected' ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : integration.status === 'error' ? (
              <XCircle className="w-4 h-4 text-red-500" />
            ) : (
              <Clock className="w-4 h-4 text-yellow-500" />
            )}
            <span className="capitalize">{integration.status}</span>
          </div>
          <div className="text-muted-foreground">
            Connected {formatDistanceToNow(new Date(integration.created_at), { addSuffix: true })}
          </div>
          {totalItems > 0 && (
            <div className="text-muted-foreground">
              {totalItems.toLocaleString()} items synced
            </div>
          )}
        </div>

        {/* Resources Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold">{config.resourceLabel}</h2>
              {sourceLimit && (
                <p className="text-sm text-muted-foreground">
                  {syncedCount} of {sourceLimit.max} {config.resourceLabel.toLowerCase()} synced
                </p>
              )}
            </div>
            <button
              onClick={() => setShowSourceModal(true)}
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              Manage sources
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>

          {resources.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-8 text-center">
              <p className="text-sm text-muted-foreground mb-3">
                No {config.resourceLabel.toLowerCase()} discovered yet.
              </p>
              <button
                onClick={() => loadData(true)}
                className="text-sm text-primary hover:underline"
              >
                Refresh to discover
              </button>
            </div>
          ) : (
            <div className="border border-border rounded-lg divide-y divide-border">
              {resources.map((resource) => (
                <ResourceRow key={resource.id} resource={resource} config={config} />
              ))}
            </div>
          )}
        </section>

        {/* Deliverables Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Deliverables → {config.label}</h2>
            <button
              onClick={handleCreateDeliverable}
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              <Plus className="w-3 h-3" />
              New deliverable
            </button>
          </div>

          {deliverables.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-8 text-center">
              <p className="text-sm text-muted-foreground mb-3">
                No deliverables targeting {config.label} yet.
              </p>
              <button
                onClick={handleCreateDeliverable}
                className="text-sm text-primary hover:underline"
              >
                Create your first
              </button>
            </div>
          ) : (
            <div className="border border-border rounded-lg divide-y divide-border">
              {deliverables.map((deliverable) => (
                <button
                  key={deliverable.id}
                  onClick={() => handleViewDeliverable(deliverable.id)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors text-left"
                >
                  <div>
                    <p className="text-sm font-medium">{deliverable.title}</p>
                    <p className="text-xs text-muted-foreground capitalize">{deliverable.deliverable_type.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={deliverable.status} />
                    {deliverable.next_run_at && (
                      <span className="text-xs text-muted-foreground">
                        Next: {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Recent Context Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Recent Context from {config.label}</h2>
            {recentMemories.length > 0 && (
              <button
                onClick={() => router.push(`/context?source=${platform}`)}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                View all
              </button>
            )}
          </div>

          {recentMemories.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-8 text-center">
              <p className="text-sm text-muted-foreground">
                No context extracted from {config.label} yet.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Import from a {config.resourceLabelSingular} to start building context.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentMemories.map((memory) => (
                <div
                  key={memory.id}
                  className="p-3 border border-border rounded-lg text-sm"
                >
                  <p className="text-foreground line-clamp-2">{memory.content}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {memory.source_ref?.resource_name && (
                      <span className="text-xs text-muted-foreground">
                        {memory.source_ref.resource_name}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Source Selection Modal */}
      {showSourceModal && (
        <SourceSelectionModal
          isOpen={showSourceModal}
          onClose={() => setShowSourceModal(false)}
          provider={platform as 'slack' | 'gmail' | 'notion' | 'google' | 'calendar'}
          onSuccess={handleSourceModalSuccess}
        />
      )}
    </div>
  );
}

// =============================================================================
// Sub-Components
// =============================================================================

function ResourceRow({
  resource,
  config,
}: {
  resource: LandscapeResource;
  config: typeof PLATFORM_CONFIG[PlatformProvider];
}) {
  return (
    <div className="px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-muted-foreground">{config.resourceIcon}</span>
        <div>
          <p className="text-sm font-medium">{resource.name}</p>
          {resource.items_extracted > 0 && (
            <p className="text-xs text-muted-foreground">
              {resource.items_extracted} items
              {resource.last_extracted_at && (
                <> • {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
              )}
            </p>
          )}
        </div>
      </div>
      <CoverageBadge state={resource.coverage_state} />
    </div>
  );
}

function CoverageBadge({ state }: { state: string }) {
  const config: Record<string, { color: string; bg: string; label: string }> = {
    covered: { color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Synced' },
    partial: { color: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Partial' },
    stale: { color: 'text-orange-700 dark:text-orange-400', bg: 'bg-orange-100 dark:bg-orange-900/30', label: 'Stale' },
    uncovered: { color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800', label: 'Not synced' },
    excluded: { color: 'text-gray-500 dark:text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900', label: 'Excluded' },
  };
  const { color, bg, label } = config[state] || config.uncovered;

  return (
    <span className={cn('px-2 py-0.5 rounded text-xs font-medium', color, bg)}>
      {label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
        Active
      </span>
    );
  }
  if (status === 'paused') {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
        Paused
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
      {status}
    </span>
  );
}
