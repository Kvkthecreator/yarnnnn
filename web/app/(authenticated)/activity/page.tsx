'use client';

/**
 * ADR-063: Activity Page — Unified Activity Log
 *
 * Audit trail showing what YARNNN has done.
 * Reads from activity_log table (unified activity layer).
 *
 * Groups event types into user-meaningful categories:
 *   - Agents: agent_run, agent_approved, agent_rejected,
 *            agent_generated, agent_scheduled, agent_bootstrapped
 *   - Memory: memory_written, session_summary_written
 *   - Sync: platform_synced, content_cleanup
 *   - Connections: integration_connected, integration_disconnected
 *   - Chat: chat_session
 *   - System: scheduler_heartbeat, composer_heartbeat
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Activity,
  FileText,
  Brain,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  ChevronDown,
  Mail,
  MessageSquare,
  Calendar,
  Filter,
  Link,
  Unlink,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  FileOutput,
  CalendarClock,
  HeartPulse,
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format, isToday, isYesterday, startOfDay } from 'date-fns';
import { cn } from '@/lib/utils';
import { HOME_ROUTE } from '@/lib/routes';

// =============================================================================
// Types
// =============================================================================

interface ActivityItem {
  id: string;
  event_type: string;
  event_ref: string | null;
  summary: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

// =============================================================================
// Event Configuration — covers ALL backend event types
// =============================================================================

const EVENT_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
  category: string;
}> = {
  // Agents
  agent_run: {
    label: 'Agent',
    icon: <Play className="w-4 h-4" />,
    color: 'text-blue-500',
    category: 'agents',
  },
  agent_approved: {
    label: 'Approved',
    icon: <ThumbsUp className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'agents',
  },
  agent_rejected: {
    label: 'Rejected',
    icon: <ThumbsDown className="w-4 h-4" />,
    color: 'text-red-500',
    category: 'agents',
  },
  agent_generated: {
    label: 'Generated',
    icon: <FileOutput className="w-4 h-4" />,
    color: 'text-emerald-500',
    category: 'agents',
  },
  agent_scheduled: {
    label: 'Scheduled',
    icon: <CalendarClock className="w-4 h-4" />,
    color: 'text-blue-400',
    category: 'agents',
  },
  // Memory & Analysis
  memory_written: {
    label: 'Learned',
    icon: <Brain className="w-4 h-4" />,
    color: 'text-purple-500',
    category: 'memory',
  },
  session_summary_written: {
    label: 'Summary',
    icon: <FileText className="w-4 h-4" />,
    color: 'text-blue-500',
    category: 'memory',
  },
  // Sync & Signals
  platform_synced: {
    label: 'Synced',
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'sync',
  },
  content_cleanup: {
    label: 'Cleanup',
    icon: <Trash2 className="w-4 h-4" />,
    color: 'text-muted-foreground',
    category: 'sync',
  },
  // Connections
  integration_connected: {
    label: 'Connected',
    icon: <Link className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'connections',
  },
  integration_disconnected: {
    label: 'Disconnected',
    icon: <Unlink className="w-4 h-4" />,
    color: 'text-muted-foreground',
    category: 'connections',
  },
  // Chat
  chat_session: {
    label: 'Chat',
    icon: <MessageSquare className="w-4 h-4" />,
    color: 'text-amber-500',
    category: 'chat',
  },
  // System (hidden from filters but renders gracefully)
  scheduler_heartbeat: {
    label: 'System',
    icon: <Activity className="w-4 h-4" />,
    color: 'text-muted-foreground',
    category: 'system',
  },
  composer_heartbeat: {
    label: 'Composer',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-muted-foreground',
    category: 'system',
  },
  agent_bootstrapped: {
    label: 'Bootstrapped',
    icon: <Sparkles className="w-4 h-4" />,
    color: 'text-amber-500',
    category: 'agents',
  },
  // ADR-126: Agent Pulse — autonomous sense→decide events
  agent_pulsed: {
    label: 'Pulse',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-cyan-500',
    category: 'agents',
  },
  pm_pulsed: {
    label: 'PM Pulse',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-purple-500',
    category: 'projects',
  },
  // ADR-117/119: Project activity + duty promotion
  project_heartbeat: {
    label: 'Project check-in',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-purple-500',
    category: 'projects',
  },
  project_assembled: {
    label: 'Assembly',
    icon: <FileOutput className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'projects',
  },
  project_escalated: {
    label: 'Needs attention',
    icon: <Play className="w-4 h-4" />,
    color: 'text-amber-500',
    category: 'projects',
  },
  project_contributor_advanced: {
    label: 'Early run',
    icon: <Clock className="w-4 h-4" />,
    color: 'text-blue-500',
    category: 'projects',
  },
  duty_promoted: {
    label: 'Promoted',
    icon: <ArrowRight className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'agents',
  },
};

const DEFAULT_EVENT_CONFIG = {
  label: 'Event',
  icon: <Activity className="w-4 h-4" />,
  color: 'text-muted-foreground',
  category: 'other',
};

// Filter categories shown as chips — user-meaningful groupings
const FILTER_CATEGORIES = [
  { key: 'agents', label: 'Agents' },
  { key: 'projects', label: 'Projects' },
  { key: 'memory', label: 'Memory' },
  { key: 'sync', label: 'Sync' },
  { key: 'chat', label: 'Chat' },
] as const;

type FilterKey = 'all' | (typeof FILTER_CATEGORIES)[number]['key'];

// Map category filters to the event_type values they include
const CATEGORY_EVENT_TYPES: Record<string, string[]> = {
  agents: ['agent_run', 'agent_approved', 'agent_rejected', 'agent_generated', 'agent_scheduled', 'agent_bootstrapped', 'duty_promoted', 'agent_pulsed'],
  projects: ['project_heartbeat', 'project_assembled', 'project_escalated', 'project_contributor_advanced', 'pm_pulsed'],
  memory: ['memory_written', 'session_summary_written'],
  sync: ['platform_synced', 'content_cleanup'],
  chat: ['chat_session'],
};

// =============================================================================
// Constants
// =============================================================================

const PAGE_SIZE = 50;

// =============================================================================
// Helpers
// =============================================================================

function getConfig(eventType: string) {
  return EVENT_CONFIG[eventType] || DEFAULT_EVENT_CONFIG;
}

interface DateGroup {
  label: string;
  items: ActivityItem[];
}

function groupByDate(items: ActivityItem[]): DateGroup[] {
  const groups: Map<string, DateGroup> = new Map();

  for (const item of items) {
    const itemDate = startOfDay(new Date(item.created_at));
    const key = itemDate.toISOString();

    if (!groups.has(key)) {
      let label: string;
      if (isToday(itemDate)) {
        label = 'Today';
      } else if (isYesterday(itemDate)) {
        label = 'Yesterday';
      } else {
        label = format(itemDate, 'MMM d');
      }
      groups.set(key, { label, items: [] });
    }

    groups.get(key)!.items.push(item);
  }

  return Array.from(groups.values());
}

/** Build a navigation target from an activity item's event type and metadata. */
function getNavigationTarget(
  item: ActivityItem
): { href: string; label: string } | null {
  const metadata = item.metadata || {};
  switch (item.event_type) {
    case 'agent_run':
    case 'agent_approved':
    case 'agent_rejected':
    case 'agent_generated':
    case 'agent_scheduled':
      if (metadata.agent_id) {
        return { href: `/agents/${metadata.agent_id}`, label: 'View agent' };
      }
      return null;
    case 'memory_written':
    case 'session_summary_written':
    case 'platform_synced':
    case 'content_cleanup': {
      const p = (metadata.provider || metadata.platform) as string | undefined;
      if (p) return { href: `/context/${p}`, label: `View ${p} context` };
      return { href: '/settings?tab=system', label: 'View system' };
    }
    case 'integration_connected':
    case 'integration_disconnected':
      if (metadata.provider) return { href: `/context/${metadata.provider}`, label: `View ${metadata.provider} context` };
      return null;
    case 'chat_session':
      return { href: HOME_ROUTE, label: 'Open Agent' };
    case 'project_heartbeat':
    case 'project_assembled':
    case 'project_escalated':
    case 'project_contributor_advanced': {
      const projectSlug = (metadata.project_slug || item.event_ref) as string | undefined;
      if (projectSlug) return { href: `/projects/${projectSlug}`, label: 'View project' };
      return null;
    }
    case 'agent_bootstrapped':
    case 'duty_promoted':
    case 'agent_pulsed':
      if (metadata.agent_id) return { href: `/agents/${metadata.agent_id}`, label: 'View agent' };
      return null;
    case 'pm_pulsed': {
      const pmProjectSlug = (metadata.project_slug || item.event_ref) as string | undefined;
      if (pmProjectSlug) return { href: `/projects/${pmProjectSlug}`, label: 'View project' };
      if (metadata.agent_id) return { href: `/agents/${metadata.agent_id}`, label: 'View agent' };
      return null;
    }
    default:
      return null;
  }
}

// =============================================================================
// Main Component
// =============================================================================

export default function ActivityPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadActivity();
  }, []);

  const handleFilterChange = (newFilter: FilterKey) => {
    setFilter(newFilter);
    setVisibleCount(PAGE_SIZE);
    setExpandedIds(new Set());
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const loadActivity = async () => {
    setLoading(true);
    setError(null);
    try {
      // The backend supports single event_type filter — for category filters,
      // we fetch all and filter client-side (backend doesn't support IN queries on event_type)
      const result = await api.activity.list({
        limit: 500,
        days: 30,
      });
      setActivities(result.activities);
      setTotal(result.total);
    } catch (err) {
      console.error('Failed to load activity:', err);
      setError(err instanceof Error ? err.message : 'Failed to load activity');
    } finally {
      setLoading(false);
    }
  };

  // Client-side category filter → visible slice → date groups
  const filteredActivities = filter === 'all'
    ? activities.filter((a) => {
        const cfg = getConfig(a.event_type);
        return cfg.category !== 'system';
      })
    : activities.filter((a) => {
        const eventTypes = CATEGORY_EVENT_TYPES[filter];
        return eventTypes?.includes(a.event_type);
      });

  const visibleActivities = filteredActivities.slice(0, visibleCount);
  const dateGroups = groupByDate(visibleActivities);
  const hasMore = visibleCount < filteredActivities.length;

  const getStatusIcon = (item: ActivityItem) => {
    const metadata = item.metadata || {};
    const status = metadata.status as string | undefined;

    if (status === 'failed') return <XCircle className="w-4 h-4 text-red-500" />;
    if (status === 'staged' || status === 'pending') return <Clock className="w-4 h-4 text-amber-500" />;
    if (status === 'approved' || status === 'completed' || status === 'published') {
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    }

    const config = getConfig(item.event_type);
    return <span className={config.color}>{config.icon}</span>;
  };

  const getPlatformIcon = (provider?: string) => {
    switch (provider) {
      case 'slack':
        return <MessageSquare className="w-3 h-3" />;
      case 'gmail':
        return <Mail className="w-3 h-3" />;
      case 'notion':
        return <FileText className="w-3 h-3" />;
      case 'calendar':
        return <Calendar className="w-3 h-3" />;
      default:
        return null;
    }
  };

  // =========================================================================
  // Metadata detail renderer — shows rich info in the expanded section
  // =========================================================================

  const renderMetadataDetails = (item: ActivityItem) => {
    const metadata = item.metadata || {};

    const DetailRow = ({ label, value }: { label: string; value: React.ReactNode }) => (
      <div className="flex items-start gap-2 text-sm">
        <span className="text-muted-foreground min-w-[100px] shrink-0">{label}</span>
        <span className="text-foreground">{value}</span>
      </div>
    );

    switch (item.event_type) {
      case 'agent_run':
        return (
          <>
            {metadata.strategy && <DetailRow label="Strategy" value={String(metadata.strategy)} />}
            {metadata.role && <DetailRow label="Role" value={String(metadata.role)} />}
            {metadata.version_number && <DetailRow label="Run" value={`v${metadata.version_number}`} />}
            {metadata.final_status && <DetailRow label="Status" value={String(metadata.final_status)} />}
            {metadata.delivery_error && (
              <DetailRow label="Error" value={<span className="text-red-500">{String(metadata.delivery_error)}</span>} />
            )}
          </>
        );

      case 'agent_approved':
      case 'agent_rejected':
        return (
          <>
            {metadata.role && <DetailRow label="Role" value={String(metadata.role)} />}
            {metadata.had_edits !== undefined && (
              <DetailRow label="Edits" value={metadata.had_edits ? 'User edited before approving' : 'Approved as-is'} />
            )}
            {metadata.final_length && metadata.draft_length && (
              <DetailRow label="Length" value={`${metadata.draft_length} → ${metadata.final_length} chars`} />
            )}
          </>
        );

      case 'agent_generated':
        return (
          <>
            {metadata.role && <DetailRow label="Role" value={String(metadata.role)} />}
            {metadata.agent_title && <DetailRow label="Title" value={String(metadata.agent_title)} />}
          </>
        );

      case 'agent_scheduled':
        return (
          <>
            {metadata.role && <DetailRow label="Role" value={String(metadata.role)} />}
            {metadata.trigger_reason && <DetailRow label="Trigger" value={String(metadata.trigger_reason)} />}
            {metadata.scheduled_for && (
              <DetailRow label="Scheduled for" value={format(new Date(String(metadata.scheduled_for)), 'MMM d, h:mm a')} />
            )}
            {metadata.mode && <DetailRow label="Mode" value={String(metadata.mode)} />}
          </>
        );

      case 'platform_synced':
        return (
          <>
            {metadata.platform && <DetailRow label="Platform" value={String(metadata.platform)} />}
            {metadata.items_synced !== undefined && <DetailRow label="Items synced" value={String(metadata.items_synced)} />}
            {metadata.error && (
              <DetailRow label="Error" value={<span className="text-red-500">{String(metadata.error)}</span>} />
            )}
          </>
        );

      case 'content_cleanup':
        return metadata.items_deleted !== undefined
          ? <DetailRow label="Items deleted" value={String(metadata.items_deleted)} />
          : null;

      case 'memory_written':
        return (
          <>
            {metadata.key && <DetailRow label="Key" value={String(metadata.key)} />}
            {metadata.source && <DetailRow label="Source" value={String(metadata.source)} />}
            {metadata.note && <DetailRow label="Note" value={String(metadata.note)} />}
          </>
        );

      case 'session_summary_written':
        return (
          <>
            {metadata.summaries_written !== undefined && <DetailRow label="Summaries" value={String(metadata.summaries_written)} />}
            {metadata.memories_extracted !== undefined && <DetailRow label="Memories" value={String(metadata.memories_extracted)} />}
            {metadata.sessions_processed !== undefined && <DetailRow label="Sessions" value={String(metadata.sessions_processed)} />}
          </>
        );

      case 'chat_session':
        return (metadata.tools_used as string[] | undefined)?.length
          ? <DetailRow label="Tools used" value={(metadata.tools_used as string[]).join(', ')} />
          : null;

      case 'integration_connected':
      case 'integration_disconnected':
        return metadata.provider ? <DetailRow label="Platform" value={String(metadata.provider)} /> : null;

      case 'agent_pulsed':
        return (
          <>
            {metadata.action && <DetailRow label="Decision" value={String(metadata.action)} />}
            {metadata.tier && <DetailRow label="Tier" value={`Tier ${metadata.tier}`} />}
            {metadata.role && <DetailRow label="Role" value={String(metadata.role)} />}
            {metadata.reason && <DetailRow label="Reason" value={String(metadata.reason)} />}
          </>
        );

      case 'pm_pulsed':
        return (
          <>
            {metadata.action && <DetailRow label="Decision" value={String(metadata.action)} />}
            {metadata.project_slug && <DetailRow label="Project" value={String(metadata.project_slug)} />}
            {metadata.reason && <DetailRow label="Reason" value={String(metadata.reason)} />}
          </>
        );

      default: {
        const entries = Object.entries(metadata);
        return entries.length > 0 ? (
          <>
            {entries.map(([key, value]) => (
              <DetailRow key={key} label={key} value={String(value)} />
            ))}
          </>
        ) : null;
      }
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Activity</h1>
            <p className="text-sm text-muted-foreground mt-1">
              What YARNNN has been doing in the background
            </p>
          </div>
          <button
            onClick={() => loadActivity()}
            disabled={loading}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            Refresh
          </button>
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <button
            onClick={() => handleFilterChange('all')}
            className={cn(
              "px-3 py-1.5 text-sm rounded-full transition-colors",
              filter === 'all'
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            All
          </button>
          {FILTER_CATEGORIES.map((cat) => (
            <button
              key={cat.key}
              onClick={() => handleFilterChange(cat.key)}
              className={cn(
                "px-3 py-1.5 text-sm rounded-full transition-colors",
                filter === cat.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 mx-auto mb-4 text-red-400" />
            <p className="text-red-500 font-medium">Failed to load activity</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
            <button
              onClick={() => loadActivity()}
              className="mt-4 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        ) : filteredActivities.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">No activity yet</p>
            <p className="text-sm text-muted-foreground mt-1">
              Activity will appear here as you use YARNNN.
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-4">
              Showing {visibleActivities.length} of {filteredActivities.length} events (last 30 days)
            </p>

            {/* Date-grouped activity list */}
            <div className="space-y-6">
              {dateGroups.map((group) => (
                <div key={group.label}>
                  <div className="sticky top-0 bg-background/95 backdrop-blur-sm z-10 py-2 mb-2">
                    <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {group.label}
                    </h3>
                  </div>
                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const config = getConfig(item.event_type);
                      const metadata = item.metadata || {};
                      const provider = (metadata.provider || metadata.platform) as string | undefined;
                      const source = metadata.source as string | undefined;
                      const versionNumber = metadata.version_number as number | undefined;
                      const origin = metadata.origin as string | undefined;
                      const itemCount = (metadata.item_count ?? metadata.items_synced) as number | undefined;
                      const isExpanded = expandedIds.has(item.id);
                      const nav = getNavigationTarget(item);

                      return (
                        <div key={item.id} className="border border-border rounded-lg overflow-hidden">
                          {/* Summary row — click to expand */}
                          <button
                            onClick={() => toggleExpanded(item.id)}
                            className={cn(
                              "w-full p-4 text-left hover:bg-muted transition-colors",
                              isExpanded && "bg-muted/50"
                            )}
                          >
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5">{getStatusIcon(item)}</div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-sm font-medium truncate">{item.summary}</span>
                                  {provider && (
                                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                      {getPlatformIcon(provider)}
                                    </span>
                                  )}
                                  {config.category === 'memory' && source && (
                                    <span className={cn(
                                      "text-xs px-1.5 py-0.5 rounded",
                                      source === 'conversation' && "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
                                      source === 'feedback' && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
                                      source === 'pattern' && "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
                                    )}>
                                      {source}
                                    </span>
                                  )}
                                  {config.category === 'agents' && origin && origin !== 'user_configured' && (
                                    <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                                      Auto
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 flex-wrap">
                                  <span className={config.color}>{config.label}</span>
                                  {versionNumber && (
                                    <>
                                      <span>&middot;</span>
                                      <span>v{versionNumber}</span>
                                    </>
                                  )}
                                  {item.event_type === 'platform_synced' && itemCount !== undefined && (
                                    <>
                                      <span>&middot;</span>
                                      <span>{itemCount} items</span>
                                    </>
                                  )}
                                  <span>&middot;</span>
                                  <span>{formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}</span>
                                </div>
                              </div>
                              <ChevronDown className={cn(
                                "w-4 h-4 text-muted-foreground shrink-0 transition-transform",
                                isExpanded && "rotate-180"
                              )} />
                            </div>
                          </button>

                          {/* Expanded detail panel */}
                          {isExpanded && (
                            <div className="px-4 pb-4 pt-2 border-t border-border bg-muted/30">
                              <div className="space-y-1.5">
                                {renderMetadataDetails(item)}
                              </div>
                              <div className="text-xs text-muted-foreground mt-2">
                                {format(new Date(item.created_at), 'MMM d, yyyy h:mm a')}
                              </div>
                              {nav && (
                                <button
                                  onClick={() => router.push(nav.href)}
                                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                                >
                                  {nav.label}
                                  <ArrowRight className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div className="flex justify-center py-6">
                <button
                  onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
                >
                  Load more ({filteredActivities.length - visibleCount} remaining)
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
