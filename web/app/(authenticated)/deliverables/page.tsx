'use client';

/**
 * ADR-067: Deliverables List Page — Platform-Grouped with Visual Emphasis
 * ADR-066: Delivery-First, No Governance
 *
 * Layer 4: Work — What YARNNN produces
 *
 * Deliverables are grouped by platform with visual emphasis:
 * - Platform badges on every card (not just group headers)
 * - Delivery status (delivered/failed) not governance status
 * - Schedule status (Active/Paused) independent from delivery
 * - Destination visibility (where outputs go)
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Play,
  Pause,
  Calendar,
  FileText,
  Plus,
  Mail,
  MessageSquare,
  Sparkles,
  Check,
  X,
  BarChart3,
  CheckCircle2,
  XCircle,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable, DeliverableStatus, SuggestedVersion } from '@/types';

// =============================================================================
// Types
// =============================================================================

type PlatformGroup = 'slack' | 'email' | 'notion' | 'synthesis';

interface GroupedDeliverables {
  slack: Deliverable[];
  email: Deliverable[];
  notion: Deliverable[];
  synthesis: Deliverable[];
}

// =============================================================================
// Helpers
// =============================================================================

function groupDeliverables(deliverables: Deliverable[]): GroupedDeliverables {
  const groups: GroupedDeliverables = {
    slack: [],
    email: [],
    notion: [],
    synthesis: [],
  };

  for (const d of deliverables) {
    const binding = d.type_classification?.binding;
    const platform = d.type_classification?.primary_platform;
    const destPlatform = d.destination?.platform;

    // Email destination goes to email group (platform-agnostic delivery)
    if (destPlatform === 'email') {
      groups.email.push(d);
      continue;
    }

    // Platform-bound deliverables go under their platform
    if (binding === 'platform_bound' && platform) {
      if (platform === 'slack') groups.slack.push(d);
      else if (platform === 'gmail') groups.email.push(d);
      else if (platform === 'notion') groups.notion.push(d);
      else groups.synthesis.push(d);
    }
    // Cross-platform, hybrid, research → synthesis
    else if (binding === 'cross_platform' || binding === 'hybrid' || binding === 'research') {
      groups.synthesis.push(d);
    }
    // Fallback: try to infer from destination
    else if (destPlatform) {
      if (destPlatform === 'slack') groups.slack.push(d);
      else if (destPlatform === 'gmail') groups.email.push(d);
      else if (destPlatform === 'notion') groups.notion.push(d);
      else groups.synthesis.push(d);
    }
    // Default to synthesis
    else {
      groups.synthesis.push(d);
    }
  }

  return groups;
}

const PLATFORM_CONFIG: Record<PlatformGroup, { emoji: string; label: string }> = {
  slack: { emoji: '💬', label: 'SLACK' },
  email: { emoji: '📧', label: 'EMAIL' },
  notion: { emoji: '📝', label: 'NOTION' },
  synthesis: { emoji: '📊', label: 'SYNTHESIS' },
};

function getPlatformEmoji(deliverable: Deliverable): string {
  const binding = deliverable.type_classification?.binding;
  if (binding === 'cross_platform' || binding === 'hybrid' || binding === 'research') {
    return '📊';
  }
  const platform = deliverable.type_classification?.primary_platform || deliverable.destination?.platform;
  if (platform === 'slack') return '💬';
  if (platform === 'gmail' || platform === 'email') return '📧';
  if (platform === 'notion') return '📝';
  return '📊';
}

function formatScheduleShort(schedule: Deliverable['schedule']): string {
  const freq = schedule.frequency;
  const day = schedule.day;
  const time = schedule.time || '09:00';

  let timeStr = time;
  try {
    const [hour, minute] = time.split(':').map(Number);
    const ampm = hour >= 12 ? 'pm' : 'am';
    const h12 = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
    timeStr = `${h12}:${minute.toString().padStart(2, '0')}${ampm}`;
  } catch {
    // Keep original
  }

  switch (freq) {
    case 'daily':
      return `Daily ${timeStr}`;
    case 'weekly':
      return `${day ? day.charAt(0).toUpperCase() + day.slice(1, 3) : 'Mon'} ${timeStr}`;
    case 'biweekly':
      return `Biweekly`;
    case 'monthly':
      return `Monthly`;
    default:
      return freq || 'Custom';
  }
}

function formatDestination(deliverable: Deliverable): string | null {
  const dest = deliverable.destination;
  if (!dest) return null;
  const target = dest.target;
  if (target === 'dm') return 'Slack DM';
  if (target?.includes('@')) return target;
  if (target?.startsWith('#')) return target;
  if (target?.startsWith('C')) return `#${target.slice(0, 8)}`;
  return dest.platform;
}

// =============================================================================
// Components
// =============================================================================

function DeliverableCard({
  deliverable,
  onClick,
}: {
  deliverable: Deliverable;
  onClick: () => void;
}) {
  const emoji = getPlatformEmoji(deliverable);
  const destination = formatDestination(deliverable);
  // Use latest_version_status from API (not full version object)
  const latestStatus = deliverable.latest_version_status;

  // ADR-068: Origin badge for signal-emergent and analyst-suggested deliverables
  const getOriginBadge = () => {
    if (deliverable.origin === 'signal_emergent') {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
          <Sparkles className="w-2.5 h-2.5" />
          Signal
        </span>
      );
    }
    if (deliverable.origin === 'analyst_suggested') {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
          <BarChart3 className="w-2.5 h-2.5" />
          Suggested
        </span>
      );
    }
    return null;
  };

  // ADR-066: Delivery status (not governance)
  const getDeliveryStatus = () => {
    if (!latestStatus) return null;
    // Map to delivery-first model
    if (latestStatus === 'delivered' || latestStatus === 'approved' || latestStatus === 'staged') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-600">
          <CheckCircle2 className="w-3 h-3" />
          Delivered
        </span>
      );
    }
    if (latestStatus === 'failed' || latestStatus === 'rejected') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-red-600">
          <XCircle className="w-3 h-3" />
          Failed
        </span>
      );
    }
    if (latestStatus === 'generating') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-blue-600">
          <Loader2 className="w-3 h-3 animate-spin" />
          Generating
        </span>
      );
    }
    return null;
  };

  // Schedule status (independent from delivery)
  const getScheduleStatus = () => {
    if (deliverable.status === 'paused') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-amber-600">
          <Pause className="w-3 h-3" />
          Paused
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600">
        <Play className="w-3 h-3" />
        Active
      </span>
    );
  };

  // Use last_run_at from deliverable (not version timestamps)
  const lastDeliveryTime = deliverable.last_run_at
    ? formatDistanceToNow(new Date(deliverable.last_run_at), { addSuffix: true })
    : null;

  return (
    <button
      onClick={onClick}
      className="w-full p-4 hover:bg-muted/50 transition-colors text-left"
    >
      <div className="flex items-start gap-3">
        {/* Platform badge on every card */}
        <span className="text-xl mt-0.5">{emoji}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium truncate">{deliverable.title}</h3>
            {getOriginBadge()}
          </div>

          {/* Schedule + destination */}
          <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
            <span>{formatScheduleShort(deliverable.schedule)}</span>
            {destination && (
              <>
                <ArrowRight className="w-3 h-3" />
                <span>{destination}</span>
              </>
            )}
          </p>

          {/* Last delivery + statuses */}
          <div className="flex items-center gap-3 mt-2">
            {lastDeliveryTime && (
              <span className="text-xs text-muted-foreground">
                Last: {lastDeliveryTime}
              </span>
            )}
            {getDeliveryStatus()}
            {getScheduleStatus()}
          </div>
        </div>
      </div>
    </button>
  );
}

function DeliverableGroup({
  platform,
  deliverables,
  onDeliverableClick,
}: {
  platform: PlatformGroup;
  deliverables: Deliverable[];
  onDeliverableClick: (id: string) => void;
}) {
  if (deliverables.length === 0) return null;

  const config = PLATFORM_CONFIG[platform];

  return (
    <div className="mb-8">
      {/* Group header with uppercase label and separator line */}
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border">
        <span className="text-lg">{config.emoji}</span>
        <h2 className="text-xs font-semibold text-muted-foreground tracking-wider">
          {config.label}
        </h2>
      </div>
      <div className="border border-border rounded-lg divide-y divide-border overflow-hidden">
        {deliverables.map((d) => (
          <DeliverableCard
            key={d.id}
            deliverable={d}
            onClick={() => onDeliverableClick(d.id)}
          />
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Main Page
// =============================================================================

export default function DeliverablesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [currentFilter, setCurrentFilter] = useState<DeliverableStatus | 'all'>('all');

  // ADR-060: Suggested deliverables from Conversation Analyst
  const [suggestions, setSuggestions] = useState<SuggestedVersion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [actioningId, setActioningId] = useState<string | null>(null);

  useEffect(() => {
    loadDeliverables();
    loadSuggestions();
  }, [currentFilter]);

  const loadDeliverables = async () => {
    setLoading(true);
    try {
      const statusParam = currentFilter !== 'all' ? currentFilter : undefined;
      const data = await api.deliverables.list(statusParam);
      setDeliverables(data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const data = await api.deliverables.listSuggested();
      setSuggestions(data);
    } catch (err) {
      console.error('Failed to load suggestions:', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleEnableSuggestion = useCallback(async (suggestion: SuggestedVersion) => {
    setActioningId(suggestion.version_id);
    try {
      await api.deliverables.enableSuggested(suggestion.deliverable_id, suggestion.version_id);
      setSuggestions((prev) => prev.filter((s) => s.version_id !== suggestion.version_id));
      loadDeliverables();
    } catch (err) {
      console.error('Failed to enable suggestion:', err);
    } finally {
      setActioningId(null);
    }
  }, []);

  const handleDismissSuggestion = useCallback(async (suggestion: SuggestedVersion) => {
    setActioningId(suggestion.version_id);
    try {
      await api.deliverables.dismissSuggested(suggestion.deliverable_id, suggestion.version_id);
      setSuggestions((prev) => prev.filter((s) => s.version_id !== suggestion.version_id));
    } catch (err) {
      console.error('Failed to dismiss suggestion:', err);
    } finally {
      setActioningId(null);
    }
  }, []);

  // ADR-067: Group deliverables by platform
  const grouped = useMemo(() => groupDeliverables(deliverables), [deliverables]);

  const handleDeliverableClick = (deliverableId: string) => {
    router.push(`/deliverables/${deliverableId}`);
  };

  const handleCreateNew = () => {
    router.push('/deliverables/new');
  };

  const totalCount = deliverables.length;
  const hasDeliverables = totalCount > 0;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Deliverables</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Scheduled automations that generate and deliver content
            </p>
          </div>
          <button
            onClick={handleCreateNew}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Plus className="w-4 h-4" />
            New
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mb-6">
          {(['all', 'active', 'paused'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setCurrentFilter(f)}
              className={`px-3 py-1.5 text-xs rounded-full border ${
                currentFilter === f
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          {!loading && (
            <span className="text-xs text-muted-foreground ml-2">
              {totalCount} deliverable{totalCount === 1 ? '' : 's'}
            </span>
          )}
        </div>

        {/* ADR-060: Suggested Deliverables */}
        {!loadingSuggestions && suggestions.length > 0 && (
          <div className="mb-6 p-4 border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span className="text-sm font-medium text-purple-900 dark:text-purple-100">
                Suggested for you
              </span>
              <span className="text-xs text-purple-600 dark:text-purple-400">
                Based on your conversations
              </span>
            </div>
            <div className="space-y-2">
              {suggestions.map((suggestion) => (
                <div
                  key={suggestion.version_id}
                  className="flex items-center justify-between p-3 bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 rounded-md"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{suggestion.deliverable_title}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {suggestion.deliverable_type && (
                        <span className="capitalize">
                          {suggestion.deliverable_type.replace(/_/g, ' ')}
                        </span>
                      )}
                      {suggestion.analyst_metadata?.confidence && (
                        <>
                          <span>·</span>
                          <span>
                            {Math.round(suggestion.analyst_metadata.confidence * 100)}% confidence
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-3">
                    <button
                      onClick={() => handleEnableSuggestion(suggestion)}
                      disabled={actioningId === suggestion.version_id}
                      className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-950/30 rounded-md transition-colors disabled:opacity-50"
                      title="Enable"
                    >
                      {actioningId === suggestion.version_id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={() => handleDismissSuggestion(suggestion)}
                      disabled={actioningId === suggestion.version_id}
                      className="p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-md transition-colors disabled:opacity-50"
                      title="Dismiss"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : !hasDeliverables ? (
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">No deliverables yet</p>
            <button
              onClick={handleCreateNew}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              <Plus className="w-4 h-4" />
              Create your first deliverable
            </button>
          </div>
        ) : (
          <div>
            {/* ADR-067: Platform-grouped list with visual emphasis */}
            <DeliverableGroup
              platform="slack"
              deliverables={grouped.slack}
              onDeliverableClick={handleDeliverableClick}
            />
            <DeliverableGroup
              platform="email"
              deliverables={grouped.email}
              onDeliverableClick={handleDeliverableClick}
            />
            <DeliverableGroup
              platform="notion"
              deliverables={grouped.notion}
              onDeliverableClick={handleDeliverableClick}
            />
            <DeliverableGroup
              platform="synthesis"
              deliverables={grouped.synthesis}
              onDeliverableClick={handleDeliverableClick}
            />
          </div>
        )}
      </div>
    </div>
  );
}
