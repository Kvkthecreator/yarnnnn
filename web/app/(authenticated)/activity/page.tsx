'use client';

/**
 * ADR-063: Activity Page — Unified Activity Log
 *
 * Audit trail showing what YARNNN has done.
 * Reads from activity_log table (unified activity layer).
 *
 * Groups event types into user-meaningful categories:
 *   - Deliverables: deliverable_run, deliverable_approved, deliverable_rejected,
 *                   deliverable_generated, deliverable_scheduled
 *   - Memory: memory_written, session_summary_written, pattern_detected,
 *             conversation_analyzed
 *   - Sync: platform_synced, content_cleanup
 *   - Signals: signal_processed
 *   - Connections: integration_connected, integration_disconnected
 *   - Chat: chat_session
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
  Mail,
  MessageSquare,
  Calendar,
  Filter,
  Link,
  Unlink,
  ThumbsUp,
  ThumbsDown,
  Zap,
  TrendingUp,
  Trash2,
  FileOutput,
  CalendarClock,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

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
  // Deliverables
  deliverable_run: {
    label: 'Deliverable',
    icon: <Play className="w-4 h-4" />,
    color: 'text-blue-500',
    category: 'deliverables',
  },
  deliverable_approved: {
    label: 'Approved',
    icon: <ThumbsUp className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'deliverables',
  },
  deliverable_rejected: {
    label: 'Rejected',
    icon: <ThumbsDown className="w-4 h-4" />,
    color: 'text-red-500',
    category: 'deliverables',
  },
  deliverable_generated: {
    label: 'Generated',
    icon: <FileOutput className="w-4 h-4" />,
    color: 'text-emerald-500',
    category: 'deliverables',
  },
  deliverable_scheduled: {
    label: 'Scheduled',
    icon: <CalendarClock className="w-4 h-4" />,
    color: 'text-blue-400',
    category: 'deliverables',
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
  pattern_detected: {
    label: 'Pattern',
    icon: <TrendingUp className="w-4 h-4" />,
    color: 'text-orange-500',
    category: 'memory',
  },
  conversation_analyzed: {
    label: 'Analysis',
    icon: <MessageSquare className="w-4 h-4" />,
    color: 'text-cyan-500',
    category: 'memory',
  },
  // Sync & Signals
  platform_synced: {
    label: 'Synced',
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-green-500',
    category: 'sync',
  },
  signal_processed: {
    label: 'Signal',
    icon: <Zap className="w-4 h-4" />,
    color: 'text-amber-500',
    category: 'signals',
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
};

const DEFAULT_EVENT_CONFIG = {
  label: 'Event',
  icon: <Activity className="w-4 h-4" />,
  color: 'text-muted-foreground',
  category: 'other',
};

// Filter categories shown as chips — user-meaningful groupings
const FILTER_CATEGORIES = [
  { key: 'deliverables', label: 'Deliverables' },
  { key: 'memory', label: 'Memory' },
  { key: 'sync', label: 'Sync' },
  { key: 'signals', label: 'Signals' },
  { key: 'chat', label: 'Chat' },
] as const;

type FilterKey = 'all' | (typeof FILTER_CATEGORIES)[number]['key'];

// Map category filters to the event_type values they include
const CATEGORY_EVENT_TYPES: Record<string, string[]> = {
  deliverables: ['deliverable_run', 'deliverable_approved', 'deliverable_rejected', 'deliverable_generated', 'deliverable_scheduled'],
  memory: ['memory_written', 'session_summary_written', 'pattern_detected', 'conversation_analyzed'],
  sync: ['platform_synced', 'content_cleanup'],
  signals: ['signal_processed'],
  chat: ['chat_session'],
};

// =============================================================================
// Helpers
// =============================================================================

function getConfig(eventType: string) {
  return EVENT_CONFIG[eventType] || DEFAULT_EVENT_CONFIG;
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

  useEffect(() => {
    loadActivity();
  }, [filter]);

  const loadActivity = async () => {
    setLoading(true);
    setError(null);
    try {
      // The backend supports single event_type filter — for category filters,
      // we fetch all and filter client-side (backend doesn't support IN queries on event_type)
      const result = await api.activity.list({
        limit: 100,
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

  // Client-side category filter
  const filteredActivities = filter === 'all'
    ? activities.filter((a) => {
        // Hide scheduler_heartbeat and system events from "All" view
        const cfg = getConfig(a.event_type);
        return cfg.category !== 'system';
      })
    : activities.filter((a) => {
        const eventTypes = CATEGORY_EVENT_TYPES[filter];
        return eventTypes?.includes(a.event_type);
      });

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

  const handleActivityClick = (item: ActivityItem) => {
    const metadata = item.metadata || {};

    switch (item.event_type) {
      case 'deliverable_run':
      case 'deliverable_approved':
      case 'deliverable_rejected':
      case 'deliverable_generated':
      case 'deliverable_scheduled':
        if (metadata.deliverable_id) {
          router.push(`/deliverables/${metadata.deliverable_id}`);
        }
        break;
      case 'memory_written':
      case 'session_summary_written':
      case 'pattern_detected':
      case 'conversation_analyzed':
        router.push('/memory?section=entries');
        break;
      case 'platform_synced':
      case 'content_cleanup':
        if (metadata.provider || metadata.platform) {
          const p = (metadata.provider || metadata.platform) as string;
          router.push(`/context/${p}`);
        } else {
          router.push('/system');
        }
        break;
      case 'signal_processed':
        router.push('/system');
        break;
      case 'integration_connected':
      case 'integration_disconnected':
        if (metadata.provider) {
          router.push(`/context/${metadata.provider}`);
        }
        break;
      case 'chat_session':
        router.push('/dashboard');
        break;
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
            onClick={() => setFilter('all')}
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
              onClick={() => setFilter(cat.key)}
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
              Showing {filteredActivities.length} of {total} events (last 30 days)
            </p>
            <div className="space-y-1">
              {filteredActivities.map((item) => {
                const config = getConfig(item.event_type);
                const metadata = item.metadata || {};
                const provider = (metadata.provider || metadata.platform) as string | undefined;
                const source = metadata.source as string | undefined;
                const deliverableTitle = metadata.deliverable_title as string | undefined;
                const versionNumber = metadata.version_number as number | undefined;
                const origin = metadata.origin as string | undefined;
                const itemCount = (metadata.item_count ?? metadata.items_synced) as number | undefined;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleActivityClick(item)}
                    className="w-full p-4 border border-border rounded-lg text-left hover:bg-muted transition-colors"
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
                          {/* Source badge for memory events */}
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
                          {/* Origin badge for signal-emergent deliverables */}
                          {config.category === 'deliverables' && origin === 'signal_emergent' && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                              signal
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 flex-wrap">
                          <span className={config.color}>{config.label}</span>
                          {/* Version number for deliverable events */}
                          {versionNumber && (
                            <>
                              <span>&middot;</span>
                              <span>v{versionNumber}</span>
                            </>
                          )}
                          {/* Item count for sync/signal events */}
                          {(item.event_type === 'platform_synced' || item.event_type === 'signal_processed') && itemCount !== undefined && (
                            <>
                              <span>&middot;</span>
                              <span>{itemCount} items</span>
                            </>
                          )}
                          {/* Deliverable title for generated events */}
                          {deliverableTitle && item.event_type === 'deliverable_generated' && (
                            <>
                              <span>&middot;</span>
                              <span className="truncate max-w-[200px]">{deliverableTitle}</span>
                            </>
                          )}
                          <span>&middot;</span>
                          <span>{formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}</span>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" />
                    </div>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
