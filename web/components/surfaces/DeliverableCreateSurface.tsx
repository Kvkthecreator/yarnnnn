'use client';

/**
 * ADR-067: Simplified Deliverable Creation
 *
 * Two-step creation flow:
 * 1. Type selection (Platform Monitors vs Synthesis Work)
 * 2. Minimal config form (title, sources, destination, schedule)
 *
 * Key changes from previous 928-line version:
 * - 6 visible types (3 platform + 3 synthesis) instead of 12+
 * - Lazy resource loading (only after type selection)
 * - No eager API calls on mount
 * - Clear Platform Monitor vs Synthesis categorization
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  Check,
  Slack,
  Mail,
  FileText,
  BarChart3,
  Users,
  Sparkles,
  Calendar,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  DeliverableType,
  DeliverableCreate,
  Destination,
  DataSource,
  ScheduleConfig,
  ScheduleFrequency,
  TypeClassification,
  IntegrationProvider,
} from '@/types';

// =============================================================================
// Types
// =============================================================================

interface DeliverableCreateSurfaceProps {
  initialPlatform?: IntegrationProvider;
  onBack?: () => void;
}

interface TypeDefinition {
  id: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
  category: 'platform' | 'synthesis';
  primaryPlatform?: IntegrationProvider;
  classification: TypeClassification;
  defaultSchedule: Partial<ScheduleConfig>;
}

interface PlatformResource {
  id: string;
  name: string;
  type: string;
}

// =============================================================================
// Type Definitions (ADR-067: 6 visible types)
// =============================================================================

const DELIVERABLE_TYPES: TypeDefinition[] = [
  // Platform Monitors
  {
    id: 'slack_channel_digest',
    label: 'Slack Digest',
    description: 'Summarize what happened in your channels',
    icon: <Slack className="w-5 h-5" />,
    category: 'platform',
    primaryPlatform: 'slack',
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'slack',
      freshness_requirement_hours: 1,
    },
    defaultSchedule: { frequency: 'weekly', day: 'monday', time: '09:00' },
  },
  {
    id: 'gmail_inbox_brief',
    label: 'Gmail Brief',
    description: 'Daily inbox triage and priorities',
    icon: <Mail className="w-5 h-5" />,
    category: 'platform',
    primaryPlatform: 'gmail',
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'gmail',
      freshness_requirement_hours: 1,
    },
    defaultSchedule: { frequency: 'daily', time: '08:00' },
  },
  {
    id: 'research_brief',
    label: 'Notion Changelog',
    description: 'Track changes in your documents',
    icon: <FileText className="w-5 h-5" />,
    category: 'platform',
    primaryPlatform: 'notion',
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      primary_platform: 'notion',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
  },
  // Synthesis Work
  {
    id: 'weekly_status',
    label: 'Weekly Status',
    description: 'Cross-platform progress update',
    icon: <BarChart3 className="w-5 h-5" />,
    category: 'synthesis',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
  },
  {
    id: 'meeting_prep',
    label: 'Meeting Prep',
    description: 'Context brief for upcoming meetings',
    icon: <Users className="w-5 h-5" />,
    category: 'synthesis',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'reactive',
      primary_platform: 'calendar',
      freshness_requirement_hours: 1,
    },
    defaultSchedule: { frequency: 'daily', time: '08:00' },
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Define your own recurring output',
    icon: <Sparkles className="w-5 h-5" />,
    category: 'synthesis',
    classification: {
      binding: 'hybrid',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
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

// =============================================================================
// Main Component
// =============================================================================

export function DeliverableCreateSurface({ initialPlatform, onBack }: DeliverableCreateSurfaceProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const typeFromUrl = searchParams.get('type') as DeliverableType | null;

  // Step state
  const [selectedType, setSelectedType] = useState<TypeDefinition | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [destination, setDestination] = useState<Destination | null>(null);
  const [schedule, setSchedule] = useState<ScheduleConfig>({
    frequency: 'weekly',
    day: 'friday',
    time: '16:00',
  });

  // Data state
  const [resources, setResources] = useState<PlatformResource[]>([]);
  const [destinations, setDestinations] = useState<PlatformResource[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-select type from URL or initial platform
  useEffect(() => {
    if (typeFromUrl) {
      const type = DELIVERABLE_TYPES.find((t) => t.id === typeFromUrl);
      if (type) handleTypeSelect(type);
    } else if (initialPlatform) {
      const type = DELIVERABLE_TYPES.find((t) => t.primaryPlatform === initialPlatform);
      if (type) handleTypeSelect(type);
    }
  }, [typeFromUrl, initialPlatform]);

  // Load resources when type is selected (lazy loading)
  useEffect(() => {
    if (!selectedType) return;

    const platform = selectedType.primaryPlatform;
    if (!platform) return;

    loadResourcesForPlatform(platform);
  }, [selectedType]);

  const loadResourcesForPlatform = async (platform: IntegrationProvider) => {
    setLoadingResources(true);
    setError(null);

    try {
      let sources: PlatformResource[] = [];
      let dests: PlatformResource[] = [];

      if (platform === 'slack') {
        const result = await api.integrations.listSlackChannels();
        sources = (result.channels || []).map((ch) => ({
          id: ch.id,
          name: `#${ch.name}`,
          type: 'channel',
        }));
        dests = sources; // Slack destinations are also channels
      } else if (platform === 'notion') {
        const result = await api.integrations.listNotionPages();
        sources = (result.pages || []).slice(0, 20).map((p) => ({
          id: p.id,
          name: p.title || 'Untitled',
          type: 'page',
        }));
        dests = sources;
      } else if (platform === 'gmail') {
        // Gmail sources are labels, destination is draft
        sources = [{ id: 'inbox', name: 'Inbox', type: 'label' }];
        dests = [{ id: 'draft', name: 'Draft', type: 'draft' }];
      }

      setResources(sources);
      setDestinations(dests);

      // Auto-select first destination
      if (dests.length > 0 && !destination) {
        setDestination({
          platform,
          target: dests[0].id,
          format: platform === 'gmail' ? 'draft' : 'message',
        });
      }
    } catch (err) {
      console.error('Failed to load resources:', err);
      setError(`Failed to load ${platform} resources. Make sure ${platform} is connected.`);
    } finally {
      setLoadingResources(false);
    }
  };

  const handleTypeSelect = (type: TypeDefinition) => {
    setSelectedType(type);
    setTitle(type.label);
    setSchedule({
      frequency: type.defaultSchedule.frequency || 'weekly',
      day: type.defaultSchedule.day,
      time: type.defaultSchedule.time || '09:00',
    });
    setSelectedSources([]);
    setDestination(null);
    setResources([]);
    setDestinations([]);
  };

  const handleBack = () => {
    if (selectedType) {
      // Go back to type selection
      setSelectedType(null);
      setTitle('');
      setSelectedSources([]);
      setDestination(null);
      setResources([]);
      setDestinations([]);
    } else if (onBack) {
      onBack();
    } else {
      router.push('/deliverables');
    }
  };

  const toggleSource = (resourceId: string) => {
    setSelectedSources((prev) =>
      prev.includes(resourceId)
        ? prev.filter((id) => id !== resourceId)
        : [...prev, resourceId]
    );
  };

  const canCreate = useCallback(() => {
    if (!selectedType) return false;
    if (!title.trim()) return false;
    if (!schedule.frequency) return false;
    // Destination optional for some types
    return true;
  }, [selectedType, title, schedule]);

  const handleCreate = async () => {
    if (!canCreate() || !selectedType) return;

    setCreating(true);
    setError(null);

    try {
      // Build sources array
      const sources: DataSource[] = selectedSources.map((sourceId) => {
        const resource = resources.find((r) => r.id === sourceId);
        const platform = selectedType.primaryPlatform || 'slack';
        return {
          type: 'integration_import',
          value: `${platform}:${sourceId}`,
          label: resource?.name || sourceId,
          provider: platform,
          source: sourceId,
          scope: {
            mode: 'delta',
            fallback_days: 7,
            max_items: 200,
          },
        };
      });

      const createData: DeliverableCreate = {
        title: title.trim(),
        deliverable_type: selectedType.id,
        destination: destination || undefined,
        sources,
        schedule,
        governance: 'manual',
        type_classification: selectedType.classification,
      };

      const deliverable = await api.deliverables.create(createData);
      router.push(`/deliverables/${deliverable.id}`);
    } catch (err) {
      console.error('Failed to create deliverable:', err);
      setError('Failed to create deliverable. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const showDaySelector = schedule.frequency === 'weekly' || schedule.frequency === 'biweekly';

  // =============================================================================
  // Render: Type Selection (Step 1)
  // =============================================================================

  if (!selectedType) {
    const platformTypes = DELIVERABLE_TYPES.filter((t) => t.category === 'platform');
    const synthesisTypes = DELIVERABLE_TYPES.filter((t) => t.category === 'synthesis');

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
          <div>
            <h1 className="text-lg font-semibold">Create Deliverable</h1>
            <p className="text-sm text-muted-foreground">
              Choose what you want to create
            </p>
          </div>
        </div>

        {/* Type Selection */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-2xl mx-auto space-y-8">
            {/* Platform Monitors */}
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-1">
                Platform Monitors
              </h2>
              <p className="text-xs text-muted-foreground mb-4">
                Stay on top of a single platform
              </p>
              <div className="grid grid-cols-3 gap-3">
                {platformTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => handleTypeSelect(type)}
                    className="p-4 border border-border rounded-lg text-left hover:border-primary hover:bg-primary/5 transition-all"
                  >
                    <div className="text-primary mb-2">{type.icon}</div>
                    <div className="text-sm font-medium">{type.label}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {type.description}
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Synthesis Work */}
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-1">
                Synthesis Work
              </h2>
              <p className="text-xs text-muted-foreground mb-4">
                Combine context across platforms
              </p>
              <div className="grid grid-cols-3 gap-3">
                {synthesisTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => handleTypeSelect(type)}
                    className="p-4 border border-border rounded-lg text-left hover:border-primary hover:bg-primary/5 transition-all"
                  >
                    <div className="text-primary mb-2">{type.icon}</div>
                    <div className="text-sm font-medium">{type.label}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {type.description}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    );
  }

  // =============================================================================
  // Render: Config Form (Step 2)
  // =============================================================================

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-muted rounded-md text-muted-foreground"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="text-primary">{selectedType.icon}</div>
            <div>
              <h1 className="text-lg font-semibold">{selectedType.label}</h1>
              <p className="text-sm text-muted-foreground">
                {selectedType.description}
              </p>
            </div>
          </div>
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

      {/* Config Form */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-xl mx-auto space-y-6">
          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Name</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Engineering Digest"
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {/* Sources (for platform-bound types) */}
          {selectedType.primaryPlatform && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Source {selectedType.primaryPlatform === 'slack' ? 'channels' : selectedType.primaryPlatform === 'notion' ? 'pages' : 'labels'}
                <span className="text-muted-foreground font-normal ml-1">(optional)</span>
              </label>
              {loadingResources ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading...
                </div>
              ) : resources.length === 0 ? (
                <p className="text-sm text-muted-foreground py-2">
                  No resources found. Make sure {selectedType.primaryPlatform} is connected.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {resources.slice(0, 12).map((resource) => {
                    const isSelected = selectedSources.includes(resource.id);
                    return (
                      <button
                        key={resource.id}
                        type="button"
                        onClick={() => toggleSource(resource.id)}
                        className={cn(
                          'p-2 border rounded-md text-left text-sm transition-all',
                          isSelected
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-muted-foreground/50'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {isSelected && <Check className="w-3.5 h-3.5 text-primary shrink-0" />}
                          <span className={cn('truncate', !isSelected && 'ml-5')}>
                            {resource.name}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Destination (for platform-bound types) */}
          {selectedType.primaryPlatform && destinations.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-2">Deliver to</label>
              <select
                value={destination?.target || ''}
                onChange={(e) =>
                  setDestination({
                    platform: selectedType.primaryPlatform!,
                    target: e.target.value,
                    format: selectedType.primaryPlatform === 'gmail' ? 'draft' : 'message',
                  })
                }
                className="w-full px-3 py-2 border border-border rounded-md text-sm"
              >
                {destinations.map((dest) => (
                  <option key={dest.id} value={dest.id}>
                    {dest.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Schedule */}
          <div>
            <label className="block text-sm font-medium mb-2">
              <Calendar className="w-4 h-4 inline mr-1" />
              Schedule
            </label>
            <div className="flex gap-3">
              <select
                value={schedule.frequency}
                onChange={(e) =>
                  setSchedule({ ...schedule, frequency: e.target.value as ScheduleFrequency })
                }
                className="flex-1 px-3 py-2 border border-border rounded-md text-sm"
              >
                {FREQUENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              {showDaySelector && (
                <select
                  value={schedule.day || 'monday'}
                  onChange={(e) => setSchedule({ ...schedule, day: e.target.value })}
                  className="flex-1 px-3 py-2 border border-border rounded-md text-sm"
                >
                  {DAY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}

              <input
                type="time"
                value={schedule.time || '09:00'}
                onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
                className="w-28 px-3 py-2 border border-border rounded-md text-sm"
              />
            </div>
          </div>

          {/* Draft mode notice */}
          <div className="p-3 bg-muted/50 rounded-md text-sm text-muted-foreground">
            <Check className="w-4 h-4 inline mr-1 text-green-500" />
            Draft mode: You'll review outputs before they're sent
          </div>
        </div>
      </div>
    </div>
  );
}
