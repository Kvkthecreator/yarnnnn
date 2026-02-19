'use client';

/**
 * Platform Detail Page
 *
 * ADR-033 Phase 4: Full platform view with resources, coverage, and deliverables.
 * Route: /context/[platform] (e.g., /context/slack, /context/gmail)
 *
 * Shows:
 * - Connection status and workspace info
 * - Resources list with inline toggle for syncing (no modal)
 * - Tier-based limits with upgrade prompts
 * - Deliverables targeting this platform
 * - Recent context extracted from this platform
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  Plus,
  AlertCircle,
  Hash,
  Tag,
  FileText,
  Calendar,
  Slack,
  Mail,
  FileCode,
  Lock,
  Check,
  AlertTriangle,
  Sparkles,
  Clock,
  RefreshCw,
  Zap,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { ConnectionDetailsModal } from '@/components/context/ConnectionDetailsModal';

// =============================================================================
// Types
// =============================================================================

type PlatformProvider = 'slack' | 'gmail' | 'notion' | 'google' | 'calendar';

// ADR-046: Map frontend platform names to backend provider names
// Calendar is surfaced separately but uses the Google integration
const BACKEND_PROVIDER_MAP: Record<PlatformProvider, string[]> = {
  slack: ['slack'],
  gmail: ['gmail', 'google'],  // Gmail may be stored as 'google' with new OAuth
  notion: ['notion'],
  google: ['google', 'gmail'], // Google may be stored as 'gmail' for legacy users
  calendar: ['google', 'gmail'], // Calendar uses Google OAuth
};

// API provider type (matches what the API client expects)
type ApiProvider = "slack" | "notion" | "gmail" | "google" | "calendar";

// Get the provider to use for API calls
const getApiProvider = (platform: PlatformProvider): ApiProvider => {
  // For calendar, use 'google' for API calls since that's the OAuth provider
  if (platform === 'calendar') return 'google';
  return platform;
};

interface LandscapeResource {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: 'uncovered' | 'partial' | 'covered' | 'stale' | 'excluded';
  last_extracted_at: string | null;
  items_extracted: number;
  metadata: Record<string, unknown>;
}

interface SelectedSource {
  id: string;
  type: string;
  name: string;
  last_sync_at: string | null;
}

interface PlatformDeliverable {
  id: string;
  title: string;
  status: string;
  next_run_at?: string | null;
  deliverable_type: string;
  destination?: { platform?: string };
}

// ADR-058: Platform context items from filesystem_items table
interface PlatformContextItem {
  id: string;
  content: string;
  content_type: string | null;
  resource_id: string;
  resource_name: string | null;
  source_timestamp: string | null;
  synced_at: string;  // ADR-058: filesystem_items uses synced_at
  metadata: Record<string, unknown>;
}

interface IntegrationData {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  created_at: string;
  last_used_at: string | null;
  metadata?: {
    email?: string;
    [key: string]: unknown;
  };
}

// ADR-053: Updated tier limits with sync frequency and new tier
interface TierLimits {
  tier: 'free' | 'starter' | 'pro';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    total_platforms: number;
    sync_frequency: '2x_daily' | '4x_daily' | 'hourly';
    tp_conversations_per_month: number;
    active_deliverables: number;
  };
  usage: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    platforms_connected: number;
    tp_conversations_this_month: number;
    active_deliverables: number;
  };
  next_sync?: string | null;
}

// =============================================================================
// Platform Configuration
// =============================================================================

// ADR-053: Only numeric limit fields for resource counting
type NumericLimitField = 'slack_channels' | 'gmail_labels' | 'notion_pages' | 'calendars' | 'total_platforms';

const PLATFORM_CONFIG: Record<PlatformProvider, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
  resourceIcon: React.ReactNode;
  resourceLabel: string;
  resourceLabelSingular: string;
  limitField: NumericLimitField;
}> = {
  slack: {
    icon: <Slack className="w-6 h-6" />,
    label: 'Slack',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    resourceIcon: <Hash className="w-4 h-4" />,
    resourceLabel: 'Channels',
    resourceLabelSingular: 'channel',
    limitField: 'slack_channels',
  },
  gmail: {
    icon: <Mail className="w-6 h-6" />,
    label: 'Gmail',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    resourceIcon: <Tag className="w-4 h-4" />,
    resourceLabel: 'Labels',
    resourceLabelSingular: 'label',
    limitField: 'gmail_labels',
  },
  notion: {
    icon: <FileCode className="w-6 h-6" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    resourceIcon: <FileText className="w-4 h-4" />,
    resourceLabel: 'Pages',
    resourceLabelSingular: 'page',
    limitField: 'notion_pages',
  },
  google: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Google',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
    resourceLabelSingular: 'calendar',
    limitField: 'gmail_labels', // Google (non-calendar) uses Gmail limits
  },
  calendar: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Calendar',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    resourceIcon: <Calendar className="w-4 h-4" />,
    resourceLabel: 'Calendars',
    resourceLabelSingular: 'calendar',
    limitField: 'calendars', // ADR-053: Renamed from calendar_events
  },
};

// =============================================================================
// ADR-053: Sync Status Banner Component
// =============================================================================

const SYNC_FREQUENCY_LABELS: Record<string, { label: string; description: string; icon: React.ReactNode }> = {
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

function SyncStatusBanner({
  tier,
  syncFrequency,
  nextSync,
  selectedCount,
  syncedCount,
}: {
  tier: string;
  syncFrequency: string;
  nextSync?: string | null;
  selectedCount: number;
  syncedCount: number;
}) {
  const frequencyInfo = SYNC_FREQUENCY_LABELS[syncFrequency] || SYNC_FREQUENCY_LABELS['2x_daily'];

  // Format next sync time
  const formatNextSync = (isoString: string | null | undefined) => {
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
  };

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

  // Sources are selected but none have synced yet — show pending state
  if (selectedCount > 0 && syncedCount === 0) {
    return (
      <div className="p-4 bg-muted/50 border border-border rounded-lg">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-muted-foreground mt-0.5" />
          <div>
            <p className="text-sm font-medium">{selectedCount} source{selectedCount !== 1 ? 's' : ''} selected — pending first sync</p>
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
              {selectedCount} source{selectedCount !== 1 ? 's' : ''} syncing
            </p>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">
              {frequencyInfo.description}
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Import prompt state
  const [showImportPrompt, setShowImportPrompt] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{
    phase: string;
    current: number;
    total: number;
  } | null>(null);
  const [newlySelectedIds, setNewlySelectedIds] = useState<string[]>([]);

  // Data
  const [integration, setIntegration] = useState<IntegrationData | null>(null);
  const [resources, setResources] = useState<LandscapeResource[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [originalIds, setOriginalIds] = useState<Set<string>>(new Set());
  const [tierLimits, setTierLimits] = useState<TierLimits | null>(null);
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  // ADR-058: Platform context from filesystem_items table
  const [platformContext, setPlatformContext] = useState<PlatformContextItem[]>([]);

  // ADR-055: Expanded resources (for showing context within rows)
  const [expandedResourceIds, setExpandedResourceIds] = useState<Set<string>>(new Set());
  const [resourceContextCache, setResourceContextCache] = useState<Record<string, PlatformContextItem[]>>({});
  const [loadingResourceContext, setLoadingResourceContext] = useState<Record<string, boolean>>({});
  const [resourceContextTotalCount, setResourceContextTotalCount] = useState<Record<string, number>>({});
  const [loadingMoreContext, setLoadingMoreContext] = useState<Record<string, boolean>>({});

  // Connection details modal state
  const [showConnectionModal, setShowConnectionModal] = useState(false);

  // Computed
  // ADR-053: Cast to number since we only use numeric limit fields for resources
  const limitField = config?.limitField || 'slack_channels';
  const limit = (tierLimits?.limits[limitField] as number) || 5;
  const atLimit = selectedIds.size >= limit;
  const hasChanges = selectedIds.size !== originalIds.size ||
    !Array.from(selectedIds).every(id => originalIds.has(id));

  // =============================================================================
  // Data Loading
  // =============================================================================

  const loadData = useCallback(async () => {
    if (!isValidPlatform) return;

    try {
      setLoading(true);
      setError(null);

      // ADR-046: Use the API provider (e.g., 'google' for calendar)
      const apiProvider = getApiProvider(platform);
      const backendProviders = BACKEND_PROVIDER_MAP[platform];

      // Load all data in parallel
      // ADR-066: Removed designated output settings (email-first delivery)
      const [integrationResult, landscapeResult, sourcesResult, limitsResult, deliverablesResult, platformContextResult, calendarsResult] = await Promise.all([
        api.integrations.get(apiProvider).catch(() => null),
        // ADR-046: Calendar uses listGoogleCalendars instead of getLandscape
        // Gmail labels ≠ Calendar data, so we skip getLandscape for calendar platform
        platform === 'calendar'
          ? Promise.resolve({ resources: [] })
          : api.integrations.getLandscape(apiProvider).catch(() => ({ resources: [] })),
        api.integrations.getSources(apiProvider).catch(() => ({ sources: [] })),
        api.integrations.getLimits().catch(() => null),
        api.deliverables.list().catch(() => []),
        // ADR-058: Load platform context from filesystem_items table
        api.integrations.getPlatformContext(platform as "slack" | "notion" | "gmail" | "calendar", { limit: 10 })
          .catch(() => ({ items: [], total_count: 0, freshest_at: null, platform })),
        // Load available calendars for Calendar platform (for source selection, not output)
        platform === 'calendar' ? api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] })) : Promise.resolve({ calendars: [] }),
      ]);

      setIntegration(integrationResult);

      // ADR-046: For calendar, convert calendars list to resources format
      if (platform === 'calendar' && calendarsResult?.calendars) {
        const calendarResources = calendarsResult.calendars.map(cal => ({
          id: cal.id,
          name: cal.summary,
          resource_type: 'calendar',
          coverage_state: 'uncovered' as const,
          last_extracted_at: null,
          items_extracted: 0,
          metadata: { primary: cal.primary },
        }));
        setResources(calendarResources);
      } else {
        setResources(landscapeResult.resources || []);
      }

      setTierLimits(limitsResult);

      // Set selected IDs from sources endpoint
      const currentIds = new Set((sourcesResult.sources || []).map((s: SelectedSource) => s.id));
      setSelectedIds(currentIds);
      setOriginalIds(currentIds);

      // Filter deliverables targeting this platform (check all backend provider variants)
      const platformDeliverables = (deliverablesResult || []).filter(
        (d: PlatformDeliverable) => backendProviders.includes(d.destination?.platform || '')
      );
      setDeliverables(platformDeliverables);

      // ADR-058: Set platform context from filesystem_items
      setPlatformContext(platformContextResult?.items || []);

    } catch (err) {
      console.error('Failed to load platform data:', err);
      setError('Failed to load platform data');
    } finally {
      setLoading(false);
    }
  }, [platform, isValidPlatform]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // =============================================================================
  // Handlers
  // =============================================================================

  const handleToggleSource = (sourceId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else if (next.size < limit) {
        next.add(sourceId);
      }
      return next;
    });
  };

  const handleSaveChanges = async () => {
    setSaving(true);
    setError(null);

    try {
      // Track which sources are newly added (not in original selection)
      const addedIds = Array.from(selectedIds).filter(id => !originalIds.has(id));

      // ADR-046: Use API provider for backend calls
      const apiProvider = getApiProvider(platform);
      const result = await api.integrations.updateSources(apiProvider, Array.from(selectedIds));
      if (result.success) {
        // Update local state with the saved sources
        const savedIds = new Set(result.selected_sources.map(s => s.id));
        setSelectedIds(savedIds);
        setOriginalIds(savedIds);

        // Check if any newly added sources haven't been imported yet
        // (coverage_state === 'uncovered' means no context extracted)
        const uncoveredNewIds = addedIds.filter(id => {
          const resource = resources.find(r => r.id === id);
          return resource && resource.coverage_state === 'uncovered';
        });

        // Show import prompt if there are uncovered newly-selected sources
        if (uncoveredNewIds.length > 0) {
          setNewlySelectedIds(uncoveredNewIds);
          setShowImportPrompt(true);
        }
      } else {
        setError(result.message || 'Failed to save changes');
      }
    } catch (err) {
      console.error('Failed to save sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardChanges = () => {
    setSelectedIds(new Set(originalIds));
  };

  const handleImportSources = async () => {
    if (newlySelectedIds.length === 0) return;

    setImporting(true);
    setImportProgress({ phase: 'Starting...', current: 0, total: newlySelectedIds.length });

    try {
      // Import each newly selected source
      for (let i = 0; i < newlySelectedIds.length; i++) {
        const sourceId = newlySelectedIds[i];
        const resource = resources.find(r => r.id === sourceId);

        setImportProgress({
          phase: `Importing ${resource?.name || sourceId}...`,
          current: i,
          total: newlySelectedIds.length,
        });

        // Start import job (ADR-046: use API provider, ADR-055: label: prefix for Gmail)
        const apiProvider = getApiProvider(platform);
        // ADR-055: For Gmail labels, prefix with 'label:' for backend processing
        const resourceIdForImport = platform === 'gmail' ? `label:${sourceId}` : sourceId;
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
          await new Promise(resolve => setTimeout(resolve, 2000));
          const updated = await api.integrations.getImportJob(job.id);
          status = updated.status;
        }
      }

      setImportProgress({
        phase: 'Complete!',
        current: newlySelectedIds.length,
        total: newlySelectedIds.length,
      });

      // Reload data to get updated coverage states
      await loadData();

      // Hide prompt after short delay
      setTimeout(() => {
        setShowImportPrompt(false);
        setImporting(false);
        setImportProgress(null);
        setNewlySelectedIds([]);
      }, 1500);

    } catch (err) {
      console.error('Failed to import sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to import sources');
      setImporting(false);
      setImportProgress(null);
    }
  };

  const handleSkipImport = () => {
    setShowImportPrompt(false);
    setNewlySelectedIds([]);
  };

  const handleCreateDeliverable = () => {
    router.push(`/deliverables/new?platform=${platform}`);
  };

  const handleViewDeliverable = (id: string) => {
    router.push(`/deliverables/${id}`);
  };

  // ADR-066: Removed designated output handlers (email-first delivery)

  const handleConnectionDisconnect = () => {
    // Redirect to context page after disconnect
    router.push('/context');
  };

  // ADR-055: Toggle resource expansion and load context
  const handleToggleResourceExpand = async (resourceId: string) => {
    const isCurrentlyExpanded = expandedResourceIds.has(resourceId);

    if (isCurrentlyExpanded) {
      // Collapse
      setExpandedResourceIds(prev => {
        const next = new Set(prev);
        next.delete(resourceId);
        return next;
      });
    } else {
      // Expand and load context if not cached
      setExpandedResourceIds(prev => new Set(prev).add(resourceId));

      if (!resourceContextCache[resourceId]) {
        setLoadingResourceContext(prev => ({ ...prev, [resourceId]: true }));
        try {
          // ADR-055: For Gmail, use label: prefix for resource_id query
          const queryResourceId = platform === 'gmail' ? `label:${resourceId}` : resourceId;
          const result = await api.integrations.getPlatformContext(
            platform as "slack" | "notion" | "gmail" | "calendar",
            { limit: 10, resourceId: queryResourceId }
          );
          setResourceContextCache(prev => ({
            ...prev,
            [resourceId]: result.items || [],
          }));
          setResourceContextTotalCount(prev => ({
            ...prev,
            [resourceId]: result.total_count || 0,
          }));
        } catch (err) {
          console.error('Failed to load resource context:', err);
          setResourceContextCache(prev => ({
            ...prev,
            [resourceId]: [],
          }));
          setResourceContextTotalCount(prev => ({
            ...prev,
            [resourceId]: 0,
          }));
        } finally {
          setLoadingResourceContext(prev => ({ ...prev, [resourceId]: false }));
        }
      }
    }
  };

  // Load more context items for a resource
  const handleLoadMoreContext = async (resourceId: string) => {
    const currentItems = resourceContextCache[resourceId] || [];
    setLoadingMoreContext(prev => ({ ...prev, [resourceId]: true }));

    try {
      const queryResourceId = platform === 'gmail' ? `label:${resourceId}` : resourceId;
      const result = await api.integrations.getPlatformContext(
        platform as "slack" | "notion" | "gmail" | "calendar",
        { limit: 10, resourceId: queryResourceId, offset: currentItems.length }
      );

      setResourceContextCache(prev => ({
        ...prev,
        [resourceId]: [...currentItems, ...(result.items || [])],
      }));
    } catch (err) {
      console.error('Failed to load more context:', err);
    } finally {
      setLoadingMoreContext(prev => ({ ...prev, [resourceId]: false }));
    }
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
    const connectBenefits: Record<string, string[]> = {
      slack: ['Sync channels as context sources', 'Surface recent messages to TP', 'Send deliverables to channels or DMs'],
      gmail: ['Sync email labels as context', 'Surface recent emails to TP', 'Send draft emails as deliverables'],
      notion: ['Sync pages and databases', 'Surface Notion content to TP', 'Write AI outputs back to pages'],
      google: ['Sync calendar events', 'Understand your schedule context', 'Create events as deliverables'],
      calendar: ['Sync calendar events', 'Understand your schedule context', 'Create events as deliverables'],
    };
    const benefits = connectBenefits[platform] || [];

    return (
      <div className="h-full overflow-auto">
        <div className="border-b border-border px-6 py-4">
          <button
            onClick={() => router.push('/context')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Context
          </button>
        </div>
        <div className="p-6 max-w-lg">
          {/* Platform header */}
          <div className="flex items-center gap-4 mb-6">
            <div className={cn('w-14 h-14 rounded-xl flex items-center justify-center', config.bgColor)}>
              <span className={cn(config.color, 'scale-150')}>{config.icon}</span>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">{config.label}</h2>
              <p className="text-sm text-muted-foreground">Not connected</p>
            </div>
          </div>

          {/* Benefits */}
          {benefits.length > 0 && (
            <div className="mb-6 space-y-2">
              {benefits.map((benefit) => (
                <div key={benefit} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 shrink-0" />
                  {benefit}
                </div>
              ))}
            </div>
          )}

          <button
            onClick={async () => {
              try {
                const { authorization_url } = await api.integrations.getAuthorizationUrl(
                  platform === 'calendar' ? 'google' : platform
                );
                window.location.href = authorization_url;
              } catch {
                router.push('/settings?tab=integrations');
              }
            }}
            className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Connect {config.label}
          </button>
        </div>
      </div>
    );
  }

  // =============================================================================
  // Render: Main Content
  // =============================================================================

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
              <h1 className="text-lg font-semibold">{config.label}</h1>
            </div>
          </div>
          <button
            onClick={() => setShowConnectionModal(true)}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Connection details
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-8">
        {/* ADR-053: Sync Status Banner - communicates sync timing clearly */}
        {tierLimits && (
          <SyncStatusBanner
            tier={tierLimits.tier}
            syncFrequency={tierLimits.limits.sync_frequency}
            nextSync={tierLimits.next_sync}
            selectedCount={selectedIds.size}
            syncedCount={resources.filter(r => r.items_extracted > 0).length}
          />
        )}

        {/* Resources Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold">{config.resourceLabel}</h2>
                {integration.workspace_name && (
                  <span className="text-sm text-muted-foreground">
                    in {integration.workspace_name}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                Select which {config.resourceLabel.toLowerCase()} to include as context sources.
                {' '}{selectedIds.size} of {limit} selected ({tierLimits?.tier || 'free'} tier)
              </p>
            </div>
            {hasChanges && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDiscardChanges}
                  className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                >
                  Discard
                </button>
                <button
                  onClick={handleSaveChanges}
                  disabled={saving}
                  className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                  Save changes
                </button>
              </div>
            )}
          </div>

          {/* Import prompt - shown after saving new sources */}
          {showImportPrompt && (
            <div className="mb-4 p-4 bg-primary/5 border border-primary/20 rounded-lg">
              {importing ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span className="text-sm font-medium">{importProgress?.phase}</span>
                  </div>
                  {importProgress && importProgress.total > 1 && (
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${(importProgress.current / importProgress.total) * 100}%` }}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <div className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">Sources saved successfully</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Import recent context from {newlySelectedIds.length === 1 ? 'this source' : `these ${newlySelectedIds.length} sources`}?
                        This gives TP immediate context without waiting for the next scheduled sync.
                      </p>
                      <ul className="mt-2 text-xs text-muted-foreground space-y-0.5">
                        <li>• <strong>Import now</strong>: Get context immediately (last 7 days)</li>
                        <li>• <strong>Skip</strong>: Wait for next scheduled sync ({
                          tierLimits?.limits.sync_frequency === 'hourly' ? 'within 1 hour' :
                          tierLimits?.limits.sync_frequency === '4x_daily' ? 'within 6 hours' :
                          'at 8am or 6pm'
                        })</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 mt-4">
                    <button
                      onClick={handleSkipImport}
                      className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                    >
                      Wait for sync
                    </button>
                    <button
                      onClick={handleImportSources}
                      className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                    >
                      Import Now
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          )}

          {/* Limit warning */}
          {atLimit && !hasChanges && (
            <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-amber-800 dark:text-amber-300">
                    {config.resourceLabelSingular} limit reached
                  </p>
                  <p className="text-amber-700 dark:text-amber-400 mt-0.5">
                    Your {tierLimits?.tier || 'free'} plan allows {limit} {config.resourceLabel.toLowerCase()}.
                    {tierLimits?.tier === 'free' && (
                      <button className="ml-1 underline hover:no-underline inline-flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        Upgrade to Pro
                      </button>
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          {resources.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-8 text-center">
              <p className="text-sm text-muted-foreground">
                No {config.resourceLabel.toLowerCase()} found in this workspace.
              </p>
            </div>
          ) : (
            <div className="border border-border rounded-lg divide-y divide-border">
              {resources.map((resource) => (
                <ResourceRow
                  key={resource.id}
                  resource={resource}
                  config={config}
                  isSelected={selectedIds.has(resource.id)}
                  onToggle={() => handleToggleSource(resource.id)}
                  disabled={!selectedIds.has(resource.id) && atLimit}
                  platform={platform}
                  isExpanded={expandedResourceIds.has(resource.id)}
                  onToggleExpand={() => handleToggleResourceExpand(resource.id)}
                  contextItems={resourceContextCache[resource.id] || []}
                  loadingContext={loadingResourceContext[resource.id] || false}
                  totalCount={resourceContextTotalCount[resource.id] || 0}
                  loadingMore={loadingMoreContext[resource.id] || false}
                  onLoadMore={() => handleLoadMoreContext(resource.id)}
                />
              ))}
            </div>
          )}
        </section>

        {/* ADR-066: Removed Output sections (Email, Page, Calendar) - delivery destinations
            are now handled per-deliverable with email-first default */}

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

        {/* ADR-055: Recent Context section removed - context now shown inline within resource rows */}
      </div>

      {/* Connection Details Modal */}
      {integration && (
        <ConnectionDetailsModal
          isOpen={showConnectionModal}
          onClose={() => setShowConnectionModal(false)}
          integration={integration}
          platformLabel={config.label}
          platformIcon={config.icon}
          onDisconnect={handleConnectionDisconnect}
          tierInfo={tierLimits ? {
            tier: tierLimits.tier,
            sync_frequency: tierLimits.limits.sync_frequency,
            next_sync: tierLimits.next_sync,
          } : undefined}
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
  isSelected,
  onToggle,
  disabled,
  platform,
  isExpanded,
  onToggleExpand,
  contextItems,
  loadingContext,
  totalCount,
  loadingMore,
  onLoadMore,
}: {
  resource: LandscapeResource;
  config: typeof PLATFORM_CONFIG[PlatformProvider];
  isSelected: boolean;
  onToggle: () => void;
  disabled: boolean;
  platform: PlatformProvider;
  isExpanded: boolean;
  onToggleExpand: () => void;
  contextItems: PlatformContextItem[];
  loadingContext: boolean;
  totalCount: number;
  loadingMore: boolean;
  onLoadMore: () => void;
}) {
  const isPrivate = resource.metadata?.is_private as boolean | undefined;
  const memberCount = resource.metadata?.member_count as number | undefined;
  const isPrimary = resource.metadata?.primary as boolean | undefined;

  // ADR-051: Notion-specific metadata
  const parentType = resource.metadata?.parent_type as string | undefined;
  const isDatabase = resource.resource_type === 'database';

  // ADR-051: Calendar uses different terminology (no "sync" - events are queried on-demand)
  const isCalendar = platform === 'calendar';
  const isNotion = platform === 'notion';

  // ADR-055: Has synced content?
  const hasSyncedContent = resource.coverage_state === 'covered' || resource.coverage_state === 'partial' || resource.items_extracted > 0;

  return (
    <div className={cn(isSelected ? 'bg-primary/5' : '')}>
      {/* Main row */}
      <div
        className={cn(
          'w-full px-4 py-3 flex items-center justify-between transition-colors',
          disabled ? 'opacity-50' : ''
        )}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Checkbox */}
          <button
            onClick={onToggle}
            disabled={disabled}
            className={cn(
              'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0',
              isSelected
                ? 'bg-primary border-primary text-primary-foreground'
                : 'border-muted-foreground/30',
              disabled && !isSelected ? 'cursor-not-allowed' : 'cursor-pointer'
            )}
          >
            {isSelected && <Check className="w-3 h-3" />}
          </button>

          {/* Icon */}
          <span className="text-muted-foreground flex-shrink-0">{config.resourceIcon}</span>

          {/* Name and metadata */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{resource.name}</span>
              {isPrimary && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  Primary
                </span>
              )}
              {isDatabase && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                  Database
                </span>
              )}
              {isPrivate && (
                <Lock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
              )}
            </div>
            {/* ADR-051: Show different info based on platform */}
            {isCalendar ? (
              <div className="text-xs text-muted-foreground">
                Events queried on-demand
              </div>
            ) : isNotion ? (
              <div className="text-xs text-muted-foreground">
                {parentType && (
                  <span>
                    {parentType === 'workspace' && 'Top-level page'}
                    {parentType === 'page' && 'Nested page'}
                    {parentType === 'database' && 'Database item'}
                  </span>
                )}
                {parentType && resource.items_extracted > 0 && <span> • </span>}
                {resource.items_extracted > 0 && (
                  <span>
                    {resource.items_extracted} items
                    {resource.last_extracted_at && (
                      <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                    )}
                  </span>
                )}
              </div>
            ) : (
              (memberCount !== undefined || resource.items_extracted > 0) && (
                <div className="text-xs text-muted-foreground">
                  {memberCount !== undefined && <span>{memberCount.toLocaleString()} members</span>}
                  {memberCount !== undefined && resource.items_extracted > 0 && <span> • </span>}
                  {resource.items_extracted > 0 && (
                    <span>
                      {resource.items_extracted} items
                      {resource.last_extracted_at && (
                        <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
                      )}
                    </span>
                  )}
                </div>
              )
            )}
          </div>
        </div>

        {/* Right side: Coverage badge + expand button */}
        <div className="flex items-center gap-2 shrink-0">
          {!isCalendar && <CoverageBadge state={resource.coverage_state} itemsExtracted={resource.items_extracted} />}
          {/* ADR-055: Expand button - only show if has synced content */}
          {hasSyncedContent && !isCalendar && (
            <button
              onClick={onToggleExpand}
              className="p-1 hover:bg-muted rounded transition-colors"
              title={isExpanded ? 'Hide context' : 'Show context'}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* ADR-055: Expanded context section */}
      {isExpanded && hasSyncedContent && !isCalendar && (
        <div className="px-4 pb-3 pl-12">
          {loadingContext ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Loading context...</span>
            </div>
          ) : contextItems.length === 0 ? (
            <div className="text-xs text-muted-foreground py-2">
              No synced content found for this resource.
            </div>
          ) : (
            <div className="space-y-1.5">
              {contextItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-2 text-xs py-1.5 px-2 rounded bg-muted/50"
                >
                  <span className="text-muted-foreground shrink-0">└─</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-foreground/80 line-clamp-2">{item.content}</p>
                    <p className="text-muted-foreground mt-0.5">
                      {item.source_timestamp && formatDistanceToNow(new Date(item.source_timestamp), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}

              {/* Load More / Count Display */}
              {contextItems.length > 0 && (
                <div className="flex items-center justify-between ml-6 pt-2">
                  <span className="text-xs text-muted-foreground">
                    Showing {contextItems.length} of {totalCount} items
                  </span>
                  {contextItems.length < totalCount && (
                    <button
                      onClick={onLoadMore}
                      disabled={loadingMore}
                      className="text-xs text-primary hover:text-primary/80 disabled:opacity-50 flex items-center gap-1"
                    >
                      {loadingMore ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        <>Load more</>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CoverageBadge({ state, itemsExtracted }: { state: string; itemsExtracted?: number }) {
  const stateConfig: Record<string, { color: string; bg: string; label: string }> = {
    covered: { color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Synced' },
    partial: { color: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Partial' },
    stale: { color: 'text-orange-700 dark:text-orange-400', bg: 'bg-orange-100 dark:bg-orange-900/30', label: 'Stale' },
    uncovered: { color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800', label: 'Not synced' },
    excluded: { color: 'text-gray-500 dark:text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900', label: 'Excluded' },
  };

  // If state is uncovered but items were extracted, treat as synced
  const effectiveState = (state === 'uncovered' && itemsExtracted && itemsExtracted > 0) ? 'covered' : state;
  const { color, bg, label } = stateConfig[effectiveState] || stateConfig.uncovered;

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
