'use client';

/**
 * Activity Page — Temporal surface: Upcoming + Past
 *
 * Two sections:
 *   Upcoming: Active tasks with next scheduled run (compact schedule strip)
 *   Past:     Chronological activity feed (date-grouped, category-filtered, expandable)
 *
 * No TP chat panel — Activity is observational. Actions happen on the Tasks surface.
 * Navigation links in the Past feed take users to where they can act.
 */

import { useState, useEffect, useCallback } from 'react';
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
  MessageSquare,
  Link,
  Unlink,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  FileOutput,
  Sparkles,
  Pause,
  Zap,
  CalendarClock,
  Circle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format, isToday, isYesterday, startOfDay } from 'date-fns';
import { cn } from '@/lib/utils';
import { HOME_ROUTE } from '@/lib/routes';
import type { Task } from '@/types';

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
  task_executed: {
    label: 'Executed',
    icon: <FileOutput className="w-3.5 h-3.5" />,
    color: 'text-emerald-500',
    category: 'tasks',
  },
  task_created: {
    label: 'Created',
    icon: <Sparkles className="w-3.5 h-3.5" />,
    color: 'text-blue-500',
    category: 'tasks',
  },
  task_triggered: {
    label: 'Triggered',
    icon: <Zap className="w-3.5 h-3.5" />,
    color: 'text-amber-500',
    category: 'tasks',
  },
  task_paused: {
    label: 'Paused',
    icon: <Pause className="w-3.5 h-3.5" />,
    color: 'text-muted-foreground',
    category: 'tasks',
  },
  task_resumed: {
    label: 'Resumed',
    icon: <Play className="w-3.5 h-3.5" />,
    color: 'text-green-500',
    category: 'tasks',
  },
  agent_run: {
    label: 'Agent Run',
    icon: <Play className="w-3.5 h-3.5" />,
    color: 'text-blue-500',
    category: 'agents',
  },
  agent_bootstrapped: {
    label: 'Bootstrapped',
    icon: <Sparkles className="w-3.5 h-3.5" />,
    color: 'text-amber-500',
    category: 'agents',
  },
  agent_scheduled: {
    label: 'Scheduled',
    icon: <CalendarClock className="w-3.5 h-3.5" />,
    color: 'text-blue-500',
    category: 'agents',
  },
  agent_approved: {
    label: 'Approved',
    icon: <ThumbsUp className="w-3.5 h-3.5" />,
    color: 'text-green-500',
    category: 'agents',
  },
  agent_rejected: {
    label: 'Rejected',
    icon: <ThumbsDown className="w-3.5 h-3.5" />,
    color: 'text-red-500',
    category: 'agents',
  },
  memory_written: {
    label: 'Learned',
    icon: <Brain className="w-3.5 h-3.5" />,
    color: 'text-purple-500',
    category: 'memory',
  },
  session_summary_written: {
    label: 'Summary',
    icon: <FileText className="w-3.5 h-3.5" />,
    color: 'text-blue-500',
    category: 'memory',
  },
  platform_synced: {
    label: 'Synced',
    icon: <RefreshCw className="w-3.5 h-3.5" />,
    color: 'text-green-500',
    category: 'sync',
  },
  content_cleanup: {
    label: 'Cleanup',
    icon: <Trash2 className="w-3.5 h-3.5" />,
    color: 'text-muted-foreground',
    category: 'sync',
  },
  integration_connected: {
    label: 'Connected',
    icon: <Link className="w-3.5 h-3.5" />,
    color: 'text-green-500',
    category: 'sync',
  },
  integration_disconnected: {
    label: 'Disconnected',
    icon: <Unlink className="w-3.5 h-3.5" />,
    color: 'text-muted-foreground',
    category: 'sync',
  },
  chat_session: {
    label: 'Chat',
    icon: <MessageSquare className="w-3.5 h-3.5" />,
    color: 'text-amber-500',
    category: 'chat',
  },
};

const DEFAULT_EVENT_CONFIG = {
  label: 'Event',
  icon: <Activity className="w-3.5 h-3.5" />,
  color: 'text-muted-foreground',
  category: 'other',
};

const FILTER_CATEGORIES = [
  { key: 'tasks', label: 'Tasks' },
  { key: 'connections', label: 'Connections' },
  { key: 'system', label: 'System' },
] as const;

type FilterKey = 'all' | (typeof FILTER_CATEGORIES)[number]['key'];

const CATEGORY_EVENT_TYPES: Record<string, string[]> = {
  tasks: ['task_executed', 'task_created', 'task_triggered', 'task_paused', 'task_resumed'],
  connections: ['platform_synced', 'integration_connected', 'integration_disconnected'],
  system: ['memory_written', 'session_summary_written', 'content_cleanup', 'chat_session',
           'agent_run', 'agent_bootstrapped', 'agent_scheduled', 'agent_approved', 'agent_rejected'],
};

// "All" default excludes system housekeeping — memory extraction, session summaries,
// content cleanup, chat turns. These are accessible via the System filter.
const DEFAULT_VISIBLE_TYPES = new Set([
  // Task lifecycle — the core value
  'task_executed', 'task_created', 'task_triggered', 'task_paused', 'task_resumed',
  // Connections — user initiated, relevant
  'platform_synced', 'integration_connected', 'integration_disconnected',
]);

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
      if (isToday(itemDate)) label = 'Today';
      else if (isYesterday(itemDate)) label = 'Yesterday';
      else label = format(itemDate, 'MMM d');
      groups.set(key, { label, items: [] });
    }
    groups.get(key)!.items.push(item);
  }
  return Array.from(groups.values());
}

function getNavigationTarget(
  item: ActivityItem
): { href: string; label: string } | null {
  const metadata = item.metadata || {};
  switch (item.event_type) {
    case 'task_executed':
    case 'task_created':
    case 'task_triggered':
    case 'task_paused':
    case 'task_resumed':
      if (metadata.task_slug) return { href: `/tasks/${metadata.task_slug}`, label: 'View task' };
      return null;
    case 'agent_run':
    case 'agent_approved':
    case 'agent_rejected':
    case 'agent_bootstrapped':
    case 'agent_scheduled':
      if (metadata.agent_id) return { href: `/agents/${metadata.agent_id}`, label: 'View agent' };
      return null;
    case 'memory_written':
    case 'session_summary_written':
      return null;
    case 'platform_synced':
    case 'content_cleanup': {
      const p = (metadata.provider || metadata.platform) as string | undefined;
      if (p) return { href: `/context/${p}`, label: `View ${p}` };
      return null;
    }
    case 'integration_connected':
    case 'integration_disconnected':
      if (metadata.provider) return { href: `/context/${metadata.provider}`, label: `View ${metadata.provider}` };
      return null;
    case 'chat_session':
      return { href: HOME_ROUTE, label: 'Open chat' };
    default:
      return null;
  }
}

// =============================================================================
// Upcoming Section — compact task schedule strip
// =============================================================================

function UpcomingSection({ tasks }: { tasks: Task[] }) {
  const router = useRouter();
  const now = new Date();

  // All non-archived tasks, sorted: active with upcoming run first, then paused
  const scheduled = tasks
    .filter(t => t.status === 'active' && t.next_run_at)
    .map(t => ({ ...t, nextRun: new Date(t.next_run_at!) }))
    .filter(t => t.nextRun > now)
    .sort((a, b) => a.nextRun.getTime() - b.nextRun.getTime());

  const paused = tasks.filter(t => t.status === 'paused');

  if (scheduled.length === 0 && paused.length === 0) {
    return (
      <p className="text-sm text-muted-foreground/60">No scheduled tasks</p>
    );
  }

  return (
    <div className="space-y-0.5">
      {scheduled.map(task => (
        <button
          key={task.slug}
          onClick={() => router.push(`/tasks/${task.slug}`)}
          className="w-full flex items-center gap-2 py-1.5 text-left group hover:bg-muted/40 rounded px-2 -mx-2 transition-colors"
        >
          <Circle className="w-2 h-2 fill-emerald-500 text-emerald-500 shrink-0" />
          <span className="text-sm truncate flex-1">{task.title || task.slug}</span>
          <span className="text-[11px] text-muted-foreground/40 shrink-0">
            {formatDistanceToNow(task.nextRun, { addSuffix: true })}
          </span>
        </button>
      ))}
      {paused.map(task => (
        <button
          key={task.slug}
          onClick={() => router.push(`/tasks/${task.slug}`)}
          className="w-full flex items-center gap-2 py-1.5 text-left group hover:bg-muted/40 rounded px-2 -mx-2 transition-colors"
        >
          <Circle className="w-2 h-2 fill-muted-foreground/30 text-muted-foreground/30 shrink-0" />
          <span className="text-sm text-muted-foreground truncate flex-1">{task.title || task.slug}</span>
          <span className="text-[11px] text-muted-foreground/30 shrink-0">paused</span>
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// Metadata detail renderer — expanded section in Past feed
// =============================================================================

function MetadataDetails({ item }: { item: ActivityItem }) {
  const metadata = item.metadata || {};

  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-muted-foreground min-w-[80px] shrink-0">{label}</span>
      <span className="text-foreground">{value}</span>
    </div>
  );

  switch (item.event_type) {
    case 'agent_run':
      return (
        <>
          {metadata.strategy && <Row label="Strategy" value={String(metadata.strategy)} />}
          {metadata.role && <Row label="Role" value={String(metadata.role)} />}
          {metadata.version_number && <Row label="Run" value={`v${metadata.version_number}`} />}
          {metadata.final_status && <Row label="Status" value={String(metadata.final_status)} />}
          {metadata.delivery_error && (
            <Row label="Error" value={<span className="text-red-500">{String(metadata.delivery_error)}</span>} />
          )}
        </>
      );

    case 'agent_approved':
    case 'agent_rejected':
      return (
        <>
          {metadata.role && <Row label="Role" value={String(metadata.role)} />}
          {metadata.had_edits !== undefined && (
            <Row label="Edits" value={metadata.had_edits ? 'Edited before approving' : 'Approved as-is'} />
          )}
        </>
      );

    case 'platform_synced':
      return (
        <>
          {metadata.platform && <Row label="Platform" value={String(metadata.platform)} />}
          {metadata.items_synced !== undefined && <Row label="Items" value={String(metadata.items_synced)} />}
          {metadata.error && (
            <Row label="Error" value={<span className="text-red-500">{String(metadata.error)}</span>} />
          )}
        </>
      );

    case 'content_cleanup':
      return metadata.items_deleted !== undefined
        ? <Row label="Deleted" value={String(metadata.items_deleted)} />
        : null;

    case 'memory_written':
      return (
        <>
          {metadata.key && <Row label="Key" value={String(metadata.key)} />}
          {metadata.source && <Row label="Source" value={String(metadata.source)} />}
        </>
      );

    case 'session_summary_written':
      return (
        <>
          {metadata.summaries_written !== undefined && <Row label="Summaries" value={String(metadata.summaries_written)} />}
          {metadata.memories_extracted !== undefined && <Row label="Memories" value={String(metadata.memories_extracted)} />}
        </>
      );

    case 'chat_session':
      return (metadata.tools_used as string[] | undefined)?.length
        ? <Row label="Tools" value={(metadata.tools_used as string[]).join(', ')} />
        : null;

    case 'integration_connected':
    case 'integration_disconnected':
      return metadata.provider ? <Row label="Platform" value={String(metadata.provider)} /> : null;

    case 'task_executed':
      return (
        <>
          {metadata.task_slug && <Row label="Task" value={String(metadata.task_slug)} />}
          {metadata.agent_slug && <Row label="Agent" value={String(metadata.agent_slug)} />}
          {metadata.role && <Row label="Role" value={String(metadata.role)} />}
          {metadata.process_steps && <Row label="Steps" value={String(metadata.process_steps)} />}
          {metadata.duration_ms && <Row label="Duration" value={`${Math.round(Number(metadata.duration_ms) / 1000)}s`} />}
          {metadata.final_status && <Row label="Status" value={String(metadata.final_status)} />}
          {metadata.input_tokens && <Row label="Tokens" value={`${Number(metadata.input_tokens).toLocaleString()} in / ${Number(metadata.output_tokens || 0).toLocaleString()} out`} />}
        </>
      );

    case 'task_created':
    case 'task_triggered':
    case 'task_paused':
    case 'task_resumed':
      return (
        <>
          {metadata.task_slug && <Row label="Task" value={String(metadata.task_slug)} />}
          {metadata.reason && <Row label="Reason" value={String(metadata.reason)} />}
        </>
      );

    default: {
      const entries = Object.entries(metadata);
      return entries.length > 0 ? (
        <>
          {entries.map(([key, value]) => (
            <Row key={key} label={key} value={String(value)} />
          ))}
        </>
      ) : null;
    }
  }
}

// =============================================================================
// Main Component
// =============================================================================

export default function ActivityPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    setError(null);
    try {
      const [activityResult, taskList] = await Promise.all([
        api.activity.list({ limit: 500, days: 30 }),
        api.tasks.list(),
      ]);
      setActivities(activityResult.activities);
      setTasks(taskList);
    } catch (err) {
      console.error('Failed to load activity:', err);
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      if (initial) setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(true); }, [loadData]);

  useEffect(() => {
    const interval = setInterval(loadData, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') loadData(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleFilterChange = (newFilter: FilterKey) => {
    setFilter(newFilter);
    setVisibleCount(PAGE_SIZE);
    setExpandedIds(new Set());
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredActivities = filter === 'all'
    ? activities.filter((a) => DEFAULT_VISIBLE_TYPES.has(a.event_type))
    : activities.filter((a) => CATEGORY_EVENT_TYPES[filter]?.includes(a.event_type));

  const visibleActivities = filteredActivities.slice(0, visibleCount);
  const dateGroups = groupByDate(visibleActivities);
  const hasMore = visibleCount < filteredActivities.length;

  const getStatusIcon = (item: ActivityItem) => {
    const metadata = item.metadata || {};
    const status = metadata.status as string | undefined;
    if (status === 'failed') return <XCircle className="w-3.5 h-3.5 text-red-500" />;
    if (status === 'staged' || status === 'pending') return <Clock className="w-3.5 h-3.5 text-amber-500" />;
    if (status === 'approved' || status === 'completed' || status === 'published') {
      return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />;
    }
    const config = getConfig(item.event_type);
    return <span className={config.color}>{config.icon}</span>;
  };

  if (loading && activities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && activities.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-10 h-10 mx-auto mb-3 text-muted-foreground/20" />
          <p className="text-sm text-red-500">{error}</p>
          <button
            onClick={() => loadData(true)}
            className="mt-3 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-2xl mx-auto px-4 md:px-6 py-6">

        {/* Header — title + refresh */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold">Activity</h1>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 text-muted-foreground/50 hover:text-muted-foreground rounded-md hover:bg-muted transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
          </button>
        </div>

        {/* Upcoming — compact schedule strip */}
        <section className="mb-6 pb-6 border-b border-border">
          <h2 className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wide mb-2">Upcoming</h2>
          <UpcomingSection tasks={tasks} />
        </section>

        {/* Past — activity feed */}
        <section>
          {/* Header row: filter chips left, event count right */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => handleFilterChange('all')}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-full transition-colors",
                  filter === 'all'
                    ? "bg-foreground text-background"
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
                    "px-2.5 py-1 text-xs rounded-full transition-colors",
                    filter === cat.key
                      ? "bg-foreground text-background"
                      : "bg-muted text-muted-foreground hover:text-foreground"
                  )}
                >
                  {cat.label}
                </button>
              ))}
            </div>
            {filteredActivities.length > 0 && (
              <span className="text-[11px] text-muted-foreground/40 shrink-0 ml-2">
                {filteredActivities.length}
              </span>
            )}
          </div>

          {/* Feed */}
          {filteredActivities.length === 0 ? (
            <div className="py-12 text-center">
              <Activity className="w-8 h-8 mx-auto mb-2 text-muted-foreground/15" />
              <p className="text-sm text-muted-foreground">No activity yet</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {dateGroups.map((group) => (
                  <div key={group.label}>
                    <div className="sticky top-0 bg-background/95 backdrop-blur-sm z-10 py-1 mb-0.5">
                      <h3 className="text-[11px] font-medium text-muted-foreground/50 uppercase tracking-wide">
                        {group.label}
                      </h3>
                    </div>
                    <div className="space-y-px">
                      {group.items.map((item) => {
                        const metadata = item.metadata || {};
                        const isExpanded = expandedIds.has(item.id);
                        const nav = getNavigationTarget(item);
                        const failedStatus = (metadata.status as string) === 'failed' || (metadata.final_status as string) === 'failed';

                        return (
                          <div
                            key={item.id}
                            className={cn(
                              "rounded-lg overflow-hidden border transition-colors",
                              failedStatus
                                ? "border-red-200 dark:border-red-900/40"
                                : "border-transparent hover:border-border"
                            )}
                          >
                            <button
                              onClick={() => toggleExpanded(item.id)}
                              className={cn(
                                "w-full px-3 py-2 text-left transition-colors",
                                isExpanded ? "bg-muted/40" : "hover:bg-muted/30"
                              )}
                            >
                              <div className="flex items-center gap-2.5">
                                <div className="shrink-0">{getStatusIcon(item)}</div>
                                <span className="text-sm truncate flex-1">{item.summary}</span>
                                <span className="text-[11px] text-muted-foreground/40 shrink-0">
                                  {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                                </span>
                                <ChevronDown className={cn(
                                  "w-3 h-3 text-muted-foreground/25 shrink-0 transition-transform",
                                  isExpanded && "rotate-180"
                                )} />
                              </div>
                            </button>

                            {isExpanded && (
                              <div className="px-3 pb-2.5 pt-1 bg-muted/20">
                                <div className="ml-6 space-y-1">
                                  <MetadataDetails item={item} />
                                  <div className="text-[11px] text-muted-foreground/40 pt-1">
                                    {format(new Date(item.created_at), 'MMM d, yyyy h:mm a')}
                                  </div>
                                  {nav && (
                                    <button
                                      onClick={() => router.push(nav.href)}
                                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline pt-0.5"
                                    >
                                      {nav.label}
                                      <ArrowRight className="w-2.5 h-2.5" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {hasMore && (
                <div className="flex justify-center py-4">
                  <button
                    onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
                    className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
                  >
                    Load more ({filteredActivities.length - visibleCount} remaining)
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
