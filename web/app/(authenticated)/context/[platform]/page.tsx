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
  Target,
  X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

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

interface TierLimits {
  tier: 'free' | 'pro' | 'enterprise';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendar_events: number;
    total_platforms: number;
  };
  usage: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendar_events: number;
    platforms_connected: number;
  };
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
  limitField: keyof TierLimits['limits'];
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
    limitField: 'calendar_events',
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
  const [recentMemories, setRecentMemories] = useState<PlatformMemory[]>([]);

  // ADR-050: Notion designated page state
  const [designatedPage, setDesignatedPage] = useState<{
    id: string | null;
    name: string | null;
  }>({ id: null, name: null });
  const [showPagePicker, setShowPagePicker] = useState(false);
  const [savingDesignatedPage, setSavingDesignatedPage] = useState(false);

  // ADR-050: Google/Calendar designated calendar state
  const [designatedCalendar, setDesignatedCalendar] = useState<{
    id: string | null;
    name: string | null;
  }>({ id: null, name: null });
  const [showCalendarPicker, setShowCalendarPicker] = useState(false);
  const [savingDesignatedCalendar, setSavingDesignatedCalendar] = useState(false);
  const [availableCalendars, setAvailableCalendars] = useState<Array<{ id: string; summary: string }>>([]);

  // Computed
  const limit = tierLimits?.limits[config?.limitField || 'slack_channels'] || 5;
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
      const [integrationResult, landscapeResult, sourcesResult, limitsResult, deliverablesResult, memoriesResult, designatedPageResult, googleSettingsResult, calendarsResult] = await Promise.all([
        api.integrations.get(apiProvider).catch(() => null),
        api.integrations.getLandscape(apiProvider).catch(() => ({ resources: [] })),
        api.integrations.getSources(apiProvider).catch(() => ({ sources: [] })),
        api.integrations.getLimits().catch(() => null),
        api.deliverables.list().catch(() => []),
        api.userMemories.list().catch(() => []),
        // ADR-050: Load designated page for Notion
        platform === 'notion' ? api.integrations.getNotionDesignatedPage().catch(() => null) : Promise.resolve(null),
        // ADR-050: Load designated settings for Calendar
        platform === 'calendar' ? api.integrations.getGoogleDesignatedSettings().catch(() => null) : Promise.resolve(null),
        // Load available calendars for Calendar platform
        platform === 'calendar' ? api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] })) : Promise.resolve({ calendars: [] }),
      ]);

      setIntegration(integrationResult);
      setResources(landscapeResult.resources || []);

      // ADR-050: Set designated page state for Notion
      if (platform === 'notion' && designatedPageResult) {
        setDesignatedPage({
          id: designatedPageResult.designated_page_id,
          name: designatedPageResult.designated_page_name,
        });
      }

      // ADR-050: Set designated calendar state for Calendar
      if (platform === 'calendar' && googleSettingsResult) {
        setDesignatedCalendar({
          id: googleSettingsResult.designated_calendar_id,
          name: googleSettingsResult.designated_calendar_name,
        });
      }

      // Set available calendars for picker
      if (platform === 'calendar' && calendarsResult?.calendars) {
        setAvailableCalendars(calendarsResult.calendars);
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

      // Filter memories from this platform (check all backend provider variants, most recent 10)
      const platformMemories = (memoriesResult || [])
        .filter((m: PlatformMemory) => backendProviders.includes(m.source_ref?.platform || ''))
        .slice(0, 10);
      setRecentMemories(platformMemories);

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

        // Start import job (ADR-046: use API provider)
        const apiProvider = getApiProvider(platform);
        const job = await api.integrations.startImport(apiProvider, {
          resource_id: sourceId,
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

  // ADR-050: Designated page handlers for Notion
  const handleSetDesignatedPage = async (pageId: string, pageName: string) => {
    setSavingDesignatedPage(true);
    try {
      const result = await api.integrations.setNotionDesignatedPage(pageId, pageName);
      if (result.success) {
        setDesignatedPage({
          id: result.designated_page_id,
          name: result.designated_page_name,
        });
        setShowPagePicker(false);
      } else {
        setError('Failed to set designated page');
      }
    } catch (err) {
      console.error('Failed to set designated page:', err);
      setError(err instanceof Error ? err.message : 'Failed to set designated page');
    } finally {
      setSavingDesignatedPage(false);
    }
  };

  const handleClearDesignatedPage = async () => {
    setSavingDesignatedPage(true);
    try {
      const result = await api.integrations.clearNotionDesignatedPage();
      if (result.success) {
        setDesignatedPage({ id: null, name: null });
      }
    } catch (err) {
      console.error('Failed to clear designated page:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear designated page');
    } finally {
      setSavingDesignatedPage(false);
    }
  };

  // ADR-050: Designated calendar handlers for Google Calendar
  const handleSetDesignatedCalendar = async (calendarId: string, calendarName: string) => {
    setSavingDesignatedCalendar(true);
    try {
      const result = await api.integrations.setGoogleDesignatedSettings(calendarId, calendarName);
      if (result.success) {
        setDesignatedCalendar({
          id: result.designated_calendar_id,
          name: result.designated_calendar_name,
        });
        setShowCalendarPicker(false);
      } else {
        setError('Failed to set designated calendar');
      }
    } catch (err) {
      console.error('Failed to set designated calendar:', err);
      setError(err instanceof Error ? err.message : 'Failed to set designated calendar');
    } finally {
      setSavingDesignatedCalendar(false);
    }
  };

  const handleClearDesignatedCalendar = async () => {
    setSavingDesignatedCalendar(true);
    try {
      const result = await api.integrations.clearGoogleDesignatedSettings();
      if (result.success) {
        setDesignatedCalendar({ id: null, name: null });
      }
    } catch (err) {
      console.error('Failed to clear designated calendar:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear designated calendar');
    } finally {
      setSavingDesignatedCalendar(false);
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
            onClick={() => router.push('/settings?tab=integrations')}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Manage connection
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-8">
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
                      <p className="text-sm font-medium">Sources saved</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Import recent context from {newlySelectedIds.length === 1 ? 'this channel' : `these ${newlySelectedIds.length} channels`}?
                        This lets TP understand your work right away.
                      </p>
                      <ul className="mt-2 text-xs text-muted-foreground space-y-0.5">
                        <li>• Last 7 days of messages</li>
                        <li>• Up to 100 items per {config.resourceLabelSingular}</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 mt-4">
                    <button
                      onClick={handleSkipImport}
                      className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                    >
                      Skip
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
                />
              ))}
            </div>
          )}
        </section>

        {/* ADR-050: Designated Output Page Section (Notion only) */}
        {platform === 'notion' && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Output Page
                </h2>
                <p className="text-sm text-muted-foreground">
                  Where TP will write outputs by default (like a YARNNN inbox)
                </p>
              </div>
            </div>

            {designatedPage.id ? (
              <div className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', config.bgColor)}>
                      <FileText className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{designatedPage.name || 'Unnamed Page'}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {designatedPage.id}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowPagePicker(true)}
                      className="text-sm text-muted-foreground hover:text-foreground"
                    >
                      Change
                    </button>
                    <button
                      onClick={handleClearDesignatedPage}
                      disabled={savingDesignatedPage}
                      className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded"
                    >
                      {savingDesignatedPage ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <X className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-border rounded-lg p-6 text-center">
                <Target className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-3">
                  No output page set. Choose a Notion page where TP will add comments and outputs.
                </p>
                <button
                  onClick={() => setShowPagePicker(true)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90"
                >
                  Choose Page
                </button>
              </div>
            )}

            {/* Page Picker Modal */}
            {showPagePicker && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md max-h-[60vh] overflow-hidden">
                  <div className="p-4 border-b border-border flex items-center justify-between">
                    <h3 className="font-semibold">Select Output Page</h3>
                    <button
                      onClick={() => setShowPagePicker(false)}
                      className="p-1 hover:bg-muted rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="p-4 overflow-y-auto max-h-[400px]">
                    <p className="text-sm text-muted-foreground mb-4">
                      Choose a page from your workspace. TP will add outputs as comments to this page.
                    </p>
                    {resources.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No pages found. Make sure Notion is connected and has accessible pages.
                      </p>
                    ) : (
                      <div className="space-y-1">
                        {resources.map((resource) => (
                          <button
                            key={resource.id}
                            onClick={() => handleSetDesignatedPage(resource.id, resource.name)}
                            disabled={savingDesignatedPage}
                            className={cn(
                              'w-full px-3 py-2 flex items-center gap-3 rounded-md text-left transition-colors',
                              resource.id === designatedPage.id
                                ? 'bg-primary/10 border border-primary'
                                : 'hover:bg-muted border border-transparent'
                            )}
                          >
                            <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                            <span className="text-sm truncate">{resource.name}</span>
                            {resource.id === designatedPage.id && (
                              <Check className="w-4 h-4 text-primary ml-auto shrink-0" />
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ADR-050: Designated Calendar Section (Calendar only) */}
        {platform === 'calendar' && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Default Calendar
                </h2>
                <p className="text-sm text-muted-foreground">
                  Where TP will create events by default
                </p>
              </div>
            </div>

            {designatedCalendar.id ? (
              <div className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', config.bgColor)}>
                      <Calendar className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{designatedCalendar.name || 'Primary Calendar'}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {designatedCalendar.id}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowCalendarPicker(true)}
                      className="text-sm text-muted-foreground hover:text-foreground"
                    >
                      Change
                    </button>
                    <button
                      onClick={handleClearDesignatedCalendar}
                      disabled={savingDesignatedCalendar}
                      className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded"
                    >
                      {savingDesignatedCalendar ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <X className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-border rounded-lg p-6 text-center">
                <Target className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-3">
                  No default calendar set. TP will use your primary calendar, or you can choose a specific one.
                </p>
                <button
                  onClick={() => setShowCalendarPicker(true)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90"
                >
                  Choose Calendar
                </button>
              </div>
            )}

            {/* Calendar Picker Modal */}
            {showCalendarPicker && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md max-h-[60vh] overflow-hidden">
                  <div className="p-4 border-b border-border flex items-center justify-between">
                    <h3 className="font-semibold">Select Default Calendar</h3>
                    <button
                      onClick={() => setShowCalendarPicker(false)}
                      className="p-1 hover:bg-muted rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="p-4 overflow-y-auto max-h-[400px]">
                    <p className="text-sm text-muted-foreground mb-4">
                      Choose a calendar. TP will create events here by default.
                    </p>
                    {availableCalendars.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No calendars found. Make sure Google Calendar is connected.
                      </p>
                    ) : (
                      <div className="space-y-1">
                        {availableCalendars.map((cal) => (
                          <button
                            key={cal.id}
                            onClick={() => handleSetDesignatedCalendar(cal.id, cal.summary)}
                            disabled={savingDesignatedCalendar}
                            className={cn(
                              'w-full px-3 py-2 flex items-center gap-3 rounded-md text-left transition-colors',
                              cal.id === designatedCalendar.id
                                ? 'bg-primary/10 border border-primary'
                                : 'hover:bg-muted border border-transparent'
                            )}
                          >
                            <Calendar className="w-4 h-4 text-muted-foreground shrink-0" />
                            <span className="text-sm truncate">{cal.summary}</span>
                            {cal.id === designatedCalendar.id && (
                              <Check className="w-4 h-4 text-primary ml-auto shrink-0" />
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

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
                onClick={() => router.push(`/context?source=facts`)}
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
                Select {config.resourceLabel.toLowerCase()} above, then import to build context.
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
}: {
  resource: LandscapeResource;
  config: typeof PLATFORM_CONFIG[PlatformProvider];
  isSelected: boolean;
  onToggle: () => void;
  disabled: boolean;
}) {
  const isPrivate = resource.metadata?.is_private as boolean | undefined;
  const memberCount = resource.metadata?.member_count as number | undefined;

  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        'w-full px-4 py-3 flex items-center justify-between transition-colors text-left',
        isSelected
          ? 'bg-primary/5'
          : disabled
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:bg-muted/50'
      )}
    >
      <div className="flex items-center gap-3">
        {/* Checkbox */}
        <div
          className={cn(
            'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0',
            isSelected
              ? 'bg-primary border-primary text-primary-foreground'
              : 'border-muted-foreground/30'
          )}
        >
          {isSelected && <Check className="w-3 h-3" />}
        </div>

        {/* Icon */}
        <span className="text-muted-foreground flex-shrink-0">{config.resourceIcon}</span>

        {/* Name and metadata */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{resource.name}</span>
            {isPrivate && (
              <Lock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
            )}
          </div>
          {(memberCount !== undefined || resource.items_extracted > 0) && (
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
          )}
        </div>
      </div>

      {/* Coverage badge */}
      <CoverageBadge state={resource.coverage_state} />
    </button>
  );
}

function CoverageBadge({ state }: { state: string }) {
  const stateConfig: Record<string, { color: string; bg: string; label: string }> = {
    covered: { color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Synced' },
    partial: { color: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Partial' },
    stale: { color: 'text-orange-700 dark:text-orange-400', bg: 'bg-orange-100 dark:bg-orange-900/30', label: 'Stale' },
    uncovered: { color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800', label: 'Not synced' },
    excluded: { color: 'text-gray-500 dark:text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900', label: 'Excluded' },
  };
  const { color, bg, label } = stateConfig[state] || stateConfig.uncovered;

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
