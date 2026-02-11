'use client';

/**
 * ADR-035: Platform-First Deliverable Type System
 * ADR-032: Destination-First Flow
 *
 * Full-screen surface for creating deliverables with platform-first types.
 * Replaces the modal wizard with better context visibility.
 *
 * Layout:
 * - Left: Form steps (destination, type, sources, schedule)
 * - Right: Platform context panel (resources, stats)
 */

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  Check,
  Send,
  Clock,
  Database,
  CheckCircle2,
  Slack,
  Mail,
  FileText,
  Download,
  BarChart3,
  MessageSquare,
  Zap,
  BookOpen,
  Users,
  Sparkles,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useDesk } from '@/contexts/DeskContext';
import type {
  Deliverable,
  DeliverableCreate,
  DeliverableType,
  TypeClassification,
  ContextBinding,
  Destination,
  DataSource,
  ScheduleConfig,
  ScheduleFrequency,
  IntegrationProvider,
} from '@/types';

// =============================================================================
// Types
// =============================================================================

interface DeliverableCreateSurfaceProps {
  initialPlatform?: 'slack' | 'gmail' | 'notion';
}

// Destination platforms include 'download' which isn't an integration
type DestinationPlatform = IntegrationProvider | 'download';

interface PlatformTypeDefinition {
  id: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
  flow: string;
  sourceplatforms: IntegrationProvider[];
  destinationPlatforms: DestinationPlatform[];
  wave: 1 | 2 | 3;
  enabled: boolean;
  defaultScope: {
    recencyDays: number;
    maxItems: number;
  };
  // ADR-044: Type classification
  classification: TypeClassification;
}

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name?: string | null;
  last_used_at?: string | null;
  created_at?: string;
}

interface PlatformResource {
  id: string;
  name: string;
  type: string;
  provider: IntegrationProvider;
}

// =============================================================================
// Platform-First Type Registry (ADR-035)
// =============================================================================

const PLATFORM_TYPES: PlatformTypeDefinition[] = [
  // Wave 1: Internal Single-Platform (ADR-044: platform_bound)
  {
    id: 'slack_channel_digest',
    label: 'Channel Digest',
    description: 'Summarize busy channels to a quieter destination',
    icon: <Slack className="w-5 h-5" />,
    flow: 'Slack → Slack',
    sourceplatforms: ['slack'],
    destinationPlatforms: ['slack'],
    wave: 1,
    enabled: true,
    defaultScope: { recencyDays: 7, maxItems: 200 },
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'slack',
      freshness_requirement_hours: 1,
    },
  },
  {
    id: 'slack_standup',
    label: 'Daily Standup',
    description: 'Auto-generate standup from Slack activity',
    icon: <MessageSquare className="w-5 h-5" />,
    flow: 'Slack → Slack',
    sourceplatforms: ['slack'],
    destinationPlatforms: ['slack'],
    wave: 1,
    enabled: true,
    defaultScope: { recencyDays: 1, maxItems: 100 },
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'slack',
      freshness_requirement_hours: 1,
    },
  },
  {
    id: 'gmail_inbox_brief',
    label: 'Inbox Brief',
    description: 'Daily triage of what needs attention',
    icon: <Mail className="w-5 h-5" />,
    flow: 'Gmail → Draft',
    sourceplatforms: ['gmail'],
    destinationPlatforms: ['gmail'],
    wave: 1,
    enabled: true,
    defaultScope: { recencyDays: 1, maxItems: 50 },
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'gmail',
      freshness_requirement_hours: 1,
    },
  },
  // Wave 2: Cross-Platform Internal (ADR-044: cross_platform)
  {
    id: 'weekly_status',
    label: 'Weekly Status',
    description: 'Cross-platform synthesis for status updates',
    icon: <BarChart3 className="w-5 h-5" />,
    flow: 'Multi → Email',
    sourceplatforms: ['slack', 'gmail', 'notion'],
    destinationPlatforms: ['gmail', 'slack'],
    wave: 2,
    enabled: true,
    defaultScope: { recencyDays: 7, maxItems: 300 },
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
  },
  {
    id: 'one_on_one_prep',
    label: 'Meeting Prep',
    description: 'Context brief before important meetings',
    icon: <Users className="w-5 h-5" />,
    flow: 'Multi → Draft',
    sourceplatforms: ['slack', 'gmail'],
    destinationPlatforms: ['gmail', 'slack'],
    wave: 2,
    enabled: true,
    defaultScope: { recencyDays: 14, maxItems: 100 },
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 1,
    },
  },
  {
    id: 'research_brief',
    label: 'Decision Capture',
    description: 'Capture decisions from Slack to Notion',
    icon: <BookOpen className="w-5 h-5" />,
    flow: 'Slack → Notion',
    sourceplatforms: ['slack'],
    destinationPlatforms: ['notion'],
    wave: 2,
    enabled: true,
    defaultScope: { recencyDays: 7, maxItems: 50 },
    classification: {
      binding: 'research',
      temporal_pattern: 'on_demand',
      freshness_requirement_hours: 24,
    },
  },
  // Wave 3: External-Facing (Coming Soon)
  {
    id: 'stakeholder_update',
    label: 'Stakeholder Brief',
    description: 'Executive summary for leadership',
    icon: <Zap className="w-5 h-5" />,
    flow: 'Internal → Email',
    sourceplatforms: ['slack', 'gmail', 'notion'],
    destinationPlatforms: ['gmail'],
    wave: 3,
    enabled: false,
    defaultScope: { recencyDays: 7, maxItems: 200 },
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
  },
  // Custom escape hatch (ADR-044: hybrid)
  {
    id: 'custom',
    label: 'Custom',
    description: 'Define your own workflow',
    icon: <Sparkles className="w-5 h-5" />,
    flow: 'Any → Any',
    sourceplatforms: ['slack', 'gmail', 'notion'],
    destinationPlatforms: ['slack', 'gmail', 'notion', 'download'],
    wave: 1,
    enabled: true,
    defaultScope: { recencyDays: 7, maxItems: 200 },
    classification: {
      binding: 'hybrid',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
  },
];

const FREQUENCY_OPTIONS: { value: ScheduleFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Every 2 weeks' },
  { value: 'monthly', label: 'Monthly' },
];

const DAY_OPTIONS = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
];

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  slack: <Slack className="w-4 h-4" />,
  gmail: <Mail className="w-4 h-4" />,
  notion: <FileText className="w-4 h-4" />,
  download: <Download className="w-4 h-4" />,
};

// =============================================================================
// Main Component
// =============================================================================

export function DeliverableCreateSurface({ initialPlatform }: DeliverableCreateSurfaceProps) {
  const router = useRouter();
  const { setSurface } = useDesk();

  // Form state
  const [selectedType, setSelectedType] = useState<PlatformTypeDefinition | null>(null);
  const [title, setTitle] = useState('');
  const [destination, setDestination] = useState<Destination | null>(null);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [schedule, setSchedule] = useState<ScheduleConfig>({
    frequency: 'weekly',
    day: 'friday',
    time: '16:00',
  });

  // Data state
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [resources, setResources] = useState<PlatformResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load integrations and resources
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load integrations
      const integrationsResult = await api.integrations.list();
      const activeIntegrations = (integrationsResult.integrations || []).filter(
        (i) => i.status === 'active' || i.status === 'connected'
      ) as Integration[];
      setIntegrations(activeIntegrations);

      // Load platform resources
      const allResources: PlatformResource[] = [];

      // Slack channels
      try {
        const slackResult = await api.integrations.listSlackChannels();
        if (slackResult.channels) {
          allResources.push(
            ...slackResult.channels.map((ch: { id: string; name: string }) => ({
              id: ch.id,
              name: `#${ch.name}`,
              type: 'channel',
              provider: 'slack' as IntegrationProvider,
            }))
          );
        }
      } catch {
        // Not connected
      }

      // Notion pages
      try {
        const notionResult = await api.integrations.listNotionPages();
        if (notionResult.pages) {
          allResources.push(
            ...notionResult.pages.slice(0, 20).map((p: { id: string; title: string }) => ({
              id: p.id,
              name: p.title || 'Untitled',
              type: 'page',
              provider: 'notion' as IntegrationProvider,
            }))
          );
        }
      } catch {
        // Not connected
      }

      // Gmail inbox
      const hasGmail = activeIntegrations.some((i: Integration) => i.provider === 'gmail');
      if (hasGmail) {
        allResources.push({
          id: 'inbox',
          name: 'Inbox',
          type: 'label',
          provider: 'gmail' as IntegrationProvider,
        });
      }

      setResources(allResources);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load platform data');
    } finally {
      setLoading(false);
    }
  };

  // Auto-select type based on initial platform
  useEffect(() => {
    if (initialPlatform && !selectedType) {
      const matchingType = PLATFORM_TYPES.find(
        (t) => t.enabled && t.sourceplatforms.includes(initialPlatform)
      );
      if (matchingType) {
        setSelectedType(matchingType);
      }
    }
  }, [initialPlatform, selectedType]);

  const handleBack = () => {
    setSurface({ type: 'idle' });
  };

  const canCreate = useCallback(() => {
    return (
      selectedType &&
      title.trim().length > 0 &&
      destination &&
      schedule.frequency
    );
  }, [selectedType, title, destination, schedule]);

  const handleCreate = async () => {
    if (!canCreate() || !selectedType || !destination) return;

    setCreating(true);
    setError(null);

    try {
      // ADR-044: Use the actual type ID (now a valid DeliverableType) and pass classification
      const createData: DeliverableCreate = {
        title: title.trim(),
        deliverable_type: selectedType.id,
        destination,
        sources,
        schedule,
        governance: 'manual', // ADR-032: Default to draft mode
        type_classification: selectedType.classification, // ADR-044
      };

      const deliverable = await api.deliverables.create(createData);

      // Navigate to the new deliverable (ADR-037: route)
      router.push(`/deliverables/${deliverable.id}`);
    } catch (err) {
      console.error('Failed to create deliverable:', err);
      setError('Failed to create deliverable. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const handleTypeSelect = (type: PlatformTypeDefinition) => {
    if (!type.enabled) return;
    setSelectedType(type);

    // Auto-set destination platform based on type
    if (type.destinationPlatforms.length === 1) {
      const platform = type.destinationPlatforms[0];
      const hasIntegration = integrations.some((i) => i.provider === platform);
      if (hasIntegration || platform === 'download') {
        setDestination({
          platform,
          format: platform === 'gmail' ? 'draft' : 'message',
        });
      }
    }

    // Set default title based on type
    if (!title) {
      setTitle(type.label);
    }
  };

  const toggleSource = (resource: PlatformResource) => {
    const isSelected = sources.some(
      (s) => s.provider === resource.provider && s.source === resource.id
    );

    if (isSelected) {
      setSources(
        sources.filter(
          (s) => !(s.provider === resource.provider && s.source === resource.id)
        )
      );
    } else {
      const newSource: DataSource = {
        type: 'integration_import',
        value: `${resource.provider}:${resource.id}`,
        label: `${resource.provider} - ${resource.name}`,
        provider: resource.provider,
        source: resource.id,
        scope: {
          mode: 'delta',
          fallback_days: selectedType?.defaultScope.recencyDays || 7,
          max_items: selectedType?.defaultScope.maxItems || 200,
        },
      };
      setSources([...sources, newSource]);
    }
  };

  // Group resources by platform
  const resourcesByPlatform = resources.reduce(
    (acc, r) => {
      if (!acc[r.provider]) acc[r.provider] = [];
      acc[r.provider].push(r);
      return acc;
    },
    {} as Record<string, PlatformResource[]>
  );

  const showDaySelector = schedule.frequency === 'weekly' || schedule.frequency === 'biweekly';

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-border">
        <button
          onClick={handleBack}
          className="p-2 hover:bg-muted rounded-md text-muted-foreground"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold">Create Deliverable</h1>
          <p className="text-sm text-muted-foreground">
            Set up recurring content generation
          </p>
        </div>
        <button
          onClick={handleCreate}
          disabled={!canCreate() || creating}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {creating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          Create
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Form */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-2xl space-y-8">
            {/* Error */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {/* Step 1: Type Selection */}
            <section>
              <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs">
                  1
                </span>
                What do you want to create?
              </h2>

              <div className="grid grid-cols-2 gap-3">
                {PLATFORM_TYPES.filter((t) => t.wave <= 2 || t.id === 'custom').map((type) => (
                  <button
                    key={type.id}
                    onClick={() => handleTypeSelect(type)}
                    disabled={!type.enabled}
                    className={cn(
                      'p-4 rounded-lg border text-left transition-all relative',
                      selectedType?.id === type.id
                        ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                        : type.enabled
                          ? 'border-border hover:border-muted-foreground/50 hover:bg-muted/30'
                          : 'border-border opacity-50 cursor-not-allowed'
                    )}
                  >
                    {!type.enabled && (
                      <span className="absolute top-2 right-2 text-[10px] font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                        Coming Soon
                      </span>
                    )}
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          'shrink-0 mt-0.5',
                          selectedType?.id === type.id
                            ? 'text-primary'
                            : 'text-muted-foreground'
                        )}
                      >
                        {type.icon}
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{type.label}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {type.description}
                        </div>
                        <div className="text-[10px] text-muted-foreground/70 mt-1">
                          {type.flow}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Step 2: Title */}
            {selectedType && (
              <section>
                <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs">
                    2
                  </span>
                  Give it a name
                </h2>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Weekly Engineering Digest"
                  className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </section>
            )}

            {/* Step 3: Destination */}
            {selectedType && title && (
              <section>
                <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs">
                    3
                  </span>
                  Where should it go?
                </h2>
                <div className="grid grid-cols-2 gap-2">
                  {selectedType.destinationPlatforms.map((platform) => {
                    const hasIntegration =
                      platform === 'download' ||
                      integrations.some((i) => i.provider === platform);
                    const isSelected = destination?.platform === platform;

                    return (
                      <button
                        key={platform}
                        onClick={() => {
                          if (hasIntegration) {
                            setDestination({
                              platform,
                              format: platform === 'gmail' ? 'draft' : 'message',
                            });
                          }
                        }}
                        disabled={!hasIntegration}
                        className={cn(
                          'p-3 rounded-md border text-left transition-all flex items-center gap-3',
                          isSelected
                            ? 'border-primary bg-primary/5'
                            : hasIntegration
                              ? 'border-border hover:border-muted-foreground/50'
                              : 'border-border opacity-50 cursor-not-allowed'
                        )}
                      >
                        <div className={cn(isSelected ? 'text-primary' : 'text-muted-foreground')}>
                          {PLATFORM_ICONS[platform]}
                        </div>
                        <div>
                          <div className="text-sm font-medium capitalize">{platform}</div>
                          {!hasIntegration && (
                            <div className="text-xs text-red-500">Not connected</div>
                          )}
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-primary ml-auto" />}
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Step 4: Sources */}
            {destination && (
              <section>
                <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs">
                    4
                  </span>
                  What should inform it?
                  <span className="text-xs text-muted-foreground font-normal ml-1">
                    (optional)
                  </span>
                </h2>

                {Object.entries(resourcesByPlatform)
                  .filter(([provider]) =>
                    selectedType?.sourceplatforms.includes(provider as IntegrationProvider)
                  )
                  .map(([provider, providerResources]) => (
                    <div key={provider} className="mb-4">
                      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
                        {PLATFORM_ICONS[provider]}
                        <span className="capitalize">{provider}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {providerResources.slice(0, 8).map((resource) => {
                          const isSelected = sources.some(
                            (s) => s.provider === resource.provider && s.source === resource.id
                          );
                          return (
                            <button
                              key={`${resource.provider}-${resource.id}`}
                              onClick={() => toggleSource(resource)}
                              className={cn(
                                'p-2 rounded-md border text-left text-sm transition-all',
                                isSelected
                                  ? 'border-primary bg-primary/5'
                                  : 'border-border hover:border-muted-foreground/50'
                              )}
                            >
                              <div className="flex items-center gap-2">
                                {isSelected && (
                                  <Check className="w-3.5 h-3.5 text-primary shrink-0" />
                                )}
                                <span className={cn('truncate', !isSelected && 'ml-5')}>
                                  {resource.name}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                {sources.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {sources.length} source{sources.length !== 1 ? 's' : ''} selected
                  </p>
                )}
              </section>
            )}

            {/* Step 5: Schedule */}
            {destination && (
              <section>
                <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs">
                    5
                  </span>
                  When should it run?
                </h2>

                <div className="space-y-4">
                  <div className="grid grid-cols-4 gap-2">
                    {FREQUENCY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setSchedule({ ...schedule, frequency: opt.value })}
                        className={cn(
                          'p-2 rounded-md border text-sm transition-all',
                          schedule.frequency === opt.value
                            ? 'border-primary bg-primary/5 text-primary font-medium'
                            : 'border-border hover:border-muted-foreground/50'
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>

                  <div className="flex gap-4">
                    {showDaySelector && (
                      <div className="flex-1">
                        <label className="block text-xs text-muted-foreground mb-1">Day</label>
                        <select
                          value={schedule.day || 'friday'}
                          onChange={(e) => setSchedule({ ...schedule, day: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-md text-sm"
                        >
                          {DAY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className={showDaySelector ? 'flex-1' : 'w-32'}>
                      <label className="block text-xs text-muted-foreground mb-1">Time</label>
                      <input
                        type="time"
                        value={schedule.time || '16:00'}
                        onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
                        className="w-full px-3 py-2 border border-border rounded-md text-sm"
                      />
                    </div>
                  </div>

                  <div className="p-3 bg-muted/50 rounded-md flex items-center gap-2 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    Draft mode: You'll review before it's sent
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>

        {/* Right: Context Panel */}
        <div className="w-80 border-l border-border bg-muted/20 overflow-y-auto hidden lg:block">
          <div className="p-4">
            <h3 className="text-sm font-medium mb-4">Platform Resources</h3>

            {integrations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No platforms connected</p>
                <button
                  onClick={() => (window.location.href = '/settings')}
                  className="text-xs text-primary hover:underline mt-2"
                >
                  Connect platforms →
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {integrations.map((integration) => {
                  const platformResources = resources.filter(
                    (r) => r.provider === integration.provider
                  );
                  return (
                    <div
                      key={integration.id}
                      className="p-3 bg-background rounded-lg border border-border"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {PLATFORM_ICONS[integration.provider]}
                        <span className="text-sm font-medium capitalize">
                          {integration.provider}
                        </span>
                        {integration.workspace_name && (
                          <span className="text-xs text-muted-foreground">
                            ({integration.workspace_name})
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {platformResources.length} resources available
                      </div>
                      {platformResources.slice(0, 3).map((r) => (
                        <div
                          key={`${r.provider}-${r.id}`}
                          className="text-xs text-muted-foreground truncate mt-1"
                        >
                          • {r.name}
                        </div>
                      ))}
                      {platformResources.length > 3 && (
                        <div className="text-xs text-muted-foreground mt-1">
                          +{platformResources.length - 3} more
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Selection Summary */}
            {selectedType && (
              <div className="mt-6 pt-4 border-t border-border">
                <h4 className="text-xs font-medium text-muted-foreground mb-2">
                  Creating
                </h4>
                <div className="p-3 bg-background rounded-lg border border-border">
                  <div className="flex items-center gap-2 mb-1">
                    {selectedType.icon}
                    <span className="text-sm font-medium">{title || selectedType.label}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{selectedType.flow}</div>
                  {destination && (
                    <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <ChevronRight className="w-3 h-3" />
                      To {destination.platform}
                    </div>
                  )}
                  {sources.length > 0 && (
                    <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      {sources.length} source{sources.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
