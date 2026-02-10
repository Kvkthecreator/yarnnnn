'use client';

/**
 * ADR-037: Integration Detail Page (Route-based)
 *
 * Standalone page for a specific integration's details.
 * Shows resources, deliverables targeting this integration, and context.
 */

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Mail,
  FileCode,
  Calendar,
  ChevronLeft,
  Loader2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Hash,
  FileText,
  Tag,
  Play,
  Pause,
  Settings,
  RotateCcw,
  Link2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import api from '@/lib/api/client';

type PlatformProvider = 'slack' | 'notion' | 'gmail' | 'google';

interface IntegrationInfo {
  id: string;
  provider: string;
  status: 'active' | 'error' | 'expired';
  workspace_name?: string;
  connected_at: string;
  last_sync_at?: string;
  error_message?: string;
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
  destination?: { platform?: string; target?: string };
  schedule?: { frequency: string };
}

interface PlatformMemory {
  id: string;
  content: string;
  created_at: string;
  source_ref?: {
    platform?: string;
    resource_name?: string;
  };
  tags?: string[];
}

// Slack icon component
function SlackIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
    </svg>
  );
}

const PLATFORM_CONFIG: Record<
  PlatformProvider,
  {
    icon: React.ReactNode;
    label: string;
    color: string;
    bgColor: string;
    resourceIcon: React.ReactNode;
    resourceLabel: string;
  }
> = {
  gmail: {
    icon: <Mail className="w-6 h-6" />,
    label: 'Gmail',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    resourceIcon: <Tag className="w-4 h-4" />,
    resourceLabel: 'Labels',
  },
  slack: {
    icon: <SlackIcon className="w-6 h-6" />,
    label: 'Slack',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    resourceIcon: <Hash className="w-4 h-4" />,
    resourceLabel: 'Channels',
  },
  notion: {
    icon: <FileCode className="w-6 h-6" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    resourceIcon: <FileText className="w-4 h-4" />,
    resourceLabel: 'Pages',
  },
  google: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Google Calendar',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
  },
};

const COVERAGE_CONFIG: Record<string, { color: string; bgColor: string; label: string }> = {
  covered: { color: 'text-green-600', bgColor: 'bg-green-100 dark:bg-green-900/30', label: 'Synced' },
  partial: { color: 'text-yellow-600', bgColor: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Partial' },
  stale: { color: 'text-orange-600', bgColor: 'bg-orange-100 dark:bg-orange-900/30', label: 'Stale' },
  uncovered: { color: 'text-gray-500', bgColor: 'bg-gray-100 dark:bg-gray-800', label: 'Not synced' },
  excluded: { color: 'text-gray-400', bgColor: 'bg-gray-50 dark:bg-gray-900', label: 'Excluded' },
};

function CoverageBadge({ state }: { state: string }) {
  const config = COVERAGE_CONFIG[state] || COVERAGE_CONFIG.uncovered;
  return (
    <span className={cn('px-2 py-0.5 text-xs rounded-full', config.bgColor, config.color)}>
      {config.label}
    </span>
  );
}

function ResourceCard({
  resource,
  platformConfig,
}: {
  resource: LandscapeResource;
  platformConfig: typeof PLATFORM_CONFIG[PlatformProvider];
}) {
  return (
    <div className="w-full p-4 border border-border rounded-lg">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className={cn('p-2 rounded-lg', platformConfig.bgColor, platformConfig.color)}>
            {platformConfig.resourceIcon}
          </div>
          <div className="min-w-0">
            <p className="font-medium truncate">{resource.name}</p>
            <p className="text-xs text-muted-foreground">
              {resource.items_extracted > 0 ? (
                <>
                  {resource.items_extracted} items
                  {resource.last_extracted_at && (
                    <> · Last sync {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                  )}
                </>
              ) : (
                'No items extracted yet'
              )}
            </p>
          </div>
        </div>
        <CoverageBadge state={resource.coverage_state} />
      </div>
    </div>
  );
}

function DeliverableCard({
  deliverable,
  onClick,
}: {
  deliverable: PlatformDeliverable;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left transition-colors"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {deliverable.status === 'active' ? (
            <Play className="w-4 h-4 text-green-500" />
          ) : (
            <Pause className="w-4 h-4 text-amber-500" />
          )}
          <div>
            <p className="text-sm font-medium">{deliverable.title}</p>
            <p className="text-xs text-muted-foreground">
              {deliverable.schedule?.frequency} · {deliverable.destination?.target || 'No target'}
            </p>
          </div>
        </div>
        {deliverable.next_run_at && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </button>
  );
}

function ContextCard({ memory }: { memory: PlatformMemory }) {
  return (
    <div className="p-3 border border-border rounded-lg">
      <p className="text-sm line-clamp-2">{memory.content}</p>
      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        {memory.source_ref?.resource_name && (
          <span className="px-1.5 py-0.5 bg-muted rounded">{memory.source_ref.resource_name}</span>
        )}
        <span>{formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}</span>
      </div>
    </div>
  );
}

export default function IntegrationDetailPage({
  params,
}: {
  params: Promise<{ provider: string }>;
}) {
  const { provider } = use(params);
  const router = useRouter();
  const platform = provider as PlatformProvider;
  const config = PLATFORM_CONFIG[platform];

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [integration, setIntegration] = useState<IntegrationInfo | null>(null);
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  const [memories, setMemories] = useState<PlatformMemory[]>([]);

  const [activeTab, setActiveTab] = useState<'resources' | 'deliverables' | 'context'>('resources');

  const loadPlatformData = useCallback(
    async (refresh = false) => {
      try {
        if (refresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        // Load all data in parallel
        const [summaryResult, landscapeResult, deliverablesResult, memoriesResult] = await Promise.all([
          api.integrations.getSummary(),
          api.integrations.getLandscape(platform as 'slack' | 'notion' | 'gmail', refresh),
          api.deliverables.list(),
          api.userMemories.list(),
        ]);

        // Find this platform's integration info
        const platformInfo = summaryResult.platforms.find((p) => p.provider === platform);
        if (platformInfo) {
          setIntegration({
            id: platform,
            provider: platform,
            status: platformInfo.status as 'active' | 'error' | 'expired',
            workspace_name: platformInfo.workspace_name || undefined,
            connected_at: platformInfo.connected_at,
          });
        }

        setResources(landscapeResult.resources || []);

        // Filter deliverables targeting this platform
        const platformDeliverables = (deliverablesResult || []).filter(
          (d: { destination?: { platform?: string } }) => d.destination?.platform === platform
        );
        setDeliverables(platformDeliverables);

        // Filter memories from this platform
        const platformMemories = (memoriesResult || []).filter(
          (m: { source_type?: string; source_ref?: { platform?: string } }) =>
            m.source_type === 'import' && m.source_ref?.platform === platform
        );
        setMemories(platformMemories.slice(0, 20));
      } catch (err) {
        console.error('Failed to load platform data:', err);
        setError('Failed to load platform details');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [platform]
  );

  useEffect(() => {
    if (config) {
      loadPlatformData();
    }
  }, [loadPlatformData, config]);

  const handleBack = () => {
    router.push('/integrations');
  };

  const handleRefresh = () => {
    loadPlatformData(true);
  };

  // Coverage stats
  const coverageStats = useMemo(() => {
    const stats = { covered: 0, partial: 0, stale: 0, uncovered: 0, excluded: 0 };
    resources.forEach((r) => {
      if (r.coverage_state in stats) {
        stats[r.coverage_state as keyof typeof stats]++;
      }
    });
    return stats;
  }, [resources]);

  const totalItems = useMemo(() => {
    return resources.reduce((sum, r) => sum + r.items_extracted, 0);
  }, [resources]);

  // Invalid provider
  if (!config) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <Link2 className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Unknown platform: {provider}</p>
        <button onClick={() => router.push('/integrations')} className="text-sm text-primary hover:underline">
          Back to Integrations
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">{error}</p>
        <button onClick={() => loadPlatformData()} className="text-sm text-primary hover:underline">
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBack}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Back to Integrations"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className={cn('p-3 rounded-xl', config.bgColor, config.color)}>{config.icon}</div>
              <div>
                <h1 className="text-xl font-semibold">{config.label}</h1>
                {integration?.workspace_name && (
                  <p className="text-sm text-muted-foreground">{integration.workspace_name}</p>
                )}
              </div>
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
              <RefreshCw className={cn('w-5 h-5', refreshing && 'animate-spin')} />
            </button>
            <button
              onClick={() => router.push('/settings?tab=integrations')}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title="Manage Integration"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Connection Status Card */}
        <div className="p-4 border border-border rounded-lg mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {integration?.status === 'active' ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : integration?.status === 'error' ? (
                <AlertCircle className="w-5 h-5 text-red-500" />
              ) : (
                <Clock className="w-5 h-5 text-amber-500" />
              )}
              <div>
                <p className="font-medium">
                  {integration?.status === 'active'
                    ? 'Connected'
                    : integration?.status === 'error'
                      ? 'Connection Error'
                      : 'Token Expired'}
                </p>
                {integration?.connected_at && (
                  <p className="text-sm text-muted-foreground">
                    Connected {formatDistanceToNow(new Date(integration.connected_at), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
            <div className="text-right text-sm text-muted-foreground">
              <p>
                {resources.length} {config.resourceLabel.toLowerCase()}
              </p>
              <p>{totalItems} items extracted</p>
            </div>
          </div>

          {/* Coverage Bar */}
          {resources.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Coverage</span>
                <span className="text-xs text-muted-foreground">
                  {coverageStats.covered + coverageStats.partial} / {resources.length} synced
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden flex">
                {coverageStats.covered > 0 && (
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${(coverageStats.covered / resources.length) * 100}%` }}
                  />
                )}
                {coverageStats.partial > 0 && (
                  <div
                    className="h-full bg-yellow-500"
                    style={{ width: `${(coverageStats.partial / resources.length) * 100}%` }}
                  />
                )}
                {coverageStats.stale > 0 && (
                  <div
                    className="h-full bg-orange-500"
                    style={{ width: `${(coverageStats.stale / resources.length) * 100}%` }}
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-border">
          <button
            onClick={() => setActiveTab('resources')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'resources'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {config.resourceLabel}
            <span className="ml-1.5 text-xs text-muted-foreground">({resources.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('deliverables')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'deliverables'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Deliverables
            <span className="ml-1.5 text-xs text-muted-foreground">({deliverables.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('context')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'context'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Context
            <span className="ml-1.5 text-xs text-muted-foreground">({memories.length})</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="min-h-[300px]">
          {activeTab === 'resources' && (
            <div className="space-y-3">
              {resources.length === 0 ? (
                <div className="text-center py-12">
                  <div className={cn('w-12 h-12 mx-auto mb-4 rounded-xl flex items-center justify-center', config.bgColor)}>
                    {config.resourceIcon}
                  </div>
                  <p className="text-muted-foreground mb-2">No {config.resourceLabel.toLowerCase()} discovered</p>
                  <button onClick={handleRefresh} className="text-sm text-primary hover:underline flex items-center gap-1 mx-auto">
                    <RotateCcw className="w-3 h-3" />
                    Refresh landscape
                  </button>
                </div>
              ) : (
                resources.map((resource) => (
                  <ResourceCard
                    key={resource.id}
                    resource={resource}
                    platformConfig={config}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === 'deliverables' && (
            <div className="space-y-2">
              {deliverables.length === 0 ? (
                <div className="text-center py-12">
                  <Play className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground mb-2">No deliverables target {config.label}</p>
                  <p className="text-sm text-muted-foreground">
                    Create a deliverable and set {config.label} as the destination
                  </p>
                </div>
              ) : (
                deliverables.map((deliverable) => (
                  <DeliverableCard
                    key={deliverable.id}
                    deliverable={deliverable}
                    onClick={() => router.push('/dashboard')}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === 'context' && (
            <div className="space-y-3">
              {memories.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground mb-2">No context from {config.label} yet</p>
                  <p className="text-sm text-muted-foreground">
                    Import data from {config.label} to see context here
                  </p>
                </div>
              ) : (
                memories.map((memory) => (
                  <ContextCard key={memory.id} memory={memory} />
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
