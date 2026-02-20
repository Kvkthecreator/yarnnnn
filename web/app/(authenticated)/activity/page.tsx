'use client';

/**
 * ADR-063: Activity Page — Four-Layer Model
 *
 * Audit trail page showing what YARNNN has done.
 * Reads from activity_log table (unified activity layer).
 *
 * Event types:
 *   - deliverable_run: Automated content generation
 *   - deliverable_approved: User approved a version
 *   - deliverable_rejected: User rejected a version
 *   - memory_written: TP learned something about user
 *   - platform_synced: Platform data synced
 *   - integration_connected: User connected a platform
 *   - integration_disconnected: User disconnected a platform
 *   - chat_session: TP conversation ended
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
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

// Activity event types stored in database (ADR-063)
// All valid event types that can be filtered via API
type ApiEventType =
  | 'deliverable_run'
  | 'deliverable_approved'
  | 'deliverable_rejected'
  | 'memory_written'
  | 'platform_synced'
  | 'integration_connected'
  | 'integration_disconnected'
  | 'chat_session';

// Alias for consistency
type EventType = ApiEventType;

interface ActivityItem {
  id: string;
  event_type: EventType;
  event_ref: string | null;
  summary: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

const EVENT_CONFIG: Record<EventType, {
  label: string;
  icon: React.ReactNode;
  color: string;
}> = {
  deliverable_run: {
    label: 'Deliverable',
    icon: <Play className="w-4 h-4" />,
    color: 'text-blue-500',
  },
  deliverable_approved: {
    label: 'Approved',
    icon: <ThumbsUp className="w-4 h-4" />,
    color: 'text-green-500',
  },
  deliverable_rejected: {
    label: 'Rejected',
    icon: <ThumbsDown className="w-4 h-4" />,
    color: 'text-red-500',
  },
  memory_written: {
    label: 'Learned',
    icon: <Brain className="w-4 h-4" />,
    color: 'text-purple-500',
  },
  platform_synced: {
    label: 'Synced',
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-green-500',
  },
  integration_connected: {
    label: 'Connected',
    icon: <Link className="w-4 h-4" />,
    color: 'text-green-500',
  },
  integration_disconnected: {
    label: 'Disconnected',
    icon: <Unlink className="w-4 h-4" />,
    color: 'text-muted-foreground',
  },
  chat_session: {
    label: 'Chat',
    icon: <MessageSquare className="w-4 h-4" />,
    color: 'text-amber-500',
  },
};

// Event types shown as filter chips — ADR-063 unified event types
const FILTER_TYPES: ApiEventType[] = [
  'deliverable_run',
  'memory_written',
  'platform_synced',
  'chat_session',
  'integration_connected',
];

export default function ActivityPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<ApiEventType | 'all'>('all');

  useEffect(() => {
    loadActivity();
  }, [filter]);

  const loadActivity = async () => {
    setLoading(true);
    try {
      const result = await api.activity.list({
        limit: 50,
        days: 30,
        eventType: filter === 'all' ? undefined : filter,
      });
      setActivities(result.activities);
      setTotal(result.total);
    } catch (err) {
      console.error('Failed to load activity:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (item: ActivityItem) => {
    const metadata = item.metadata || {};
    const status = metadata.status as string | undefined;

    if (status === 'failed') return <XCircle className="w-4 h-4 text-red-500" />;
    if (status === 'staged' || status === 'pending') return <Clock className="w-4 h-4 text-amber-500" />;
    if (status === 'approved' || status === 'completed' || status === 'published') {
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    }

    // Default: use event type icon
    const config = EVENT_CONFIG[item.event_type];
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
      case 'google':
        return <Calendar className="w-3 h-3" />;
      default:
        return null;
    }
  };

  const handleActivityClick = (item: ActivityItem) => {
    const metadata = item.metadata || {};

    // Navigate based on event type
    switch (item.event_type) {
      case 'deliverable_run':
      case 'deliverable_approved':
      case 'deliverable_rejected':
        if (metadata.deliverable_id) {
          router.push(`/deliverables/${metadata.deliverable_id}`);
        }
        break;
      case 'memory_written':
        // Navigate to context entries
        router.push('/context?section=entries');
        break;
      case 'platform_synced':
        if (metadata.provider) {
          const provider = metadata.provider === 'google' ? 'calendar' : metadata.provider;
          router.push(`/context/${provider}`);
        }
        break;
      case 'integration_connected':
      case 'integration_disconnected':
        if (metadata.provider) {
          router.push(`/context/${metadata.provider}`);
        }
        break;
      case 'chat_session':
        // Navigate to dashboard (chat)
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
              Deliverables, approvals, integrations, syncs, and learnings
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

        {/* Filter */}
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
          {FILTER_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={cn(
                "px-3 py-1.5 text-sm rounded-full transition-colors flex items-center gap-1.5",
                filter === type
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {EVENT_CONFIG[type].label}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : activities.length === 0 ? (
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
              Showing {activities.length} of {total} events
            </p>
            <div className="space-y-1">
              {activities.map((item) => {
                const config = EVENT_CONFIG[item.event_type];
                const metadata = item.metadata || {};
                const provider = metadata.provider as string | undefined;
                const source = metadata.source as string | undefined;
                const deliverableTitle = metadata.deliverable_title as string | undefined;
                const versionNumber = metadata.version_number as number | undefined;
                const origin = metadata.origin as string | undefined;
                const itemCount = metadata.item_count as number | undefined;

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
                          {/* Source badge for memory_written */}
                          {item.event_type === 'memory_written' && source && (
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
                          {(item.event_type === 'deliverable_run' || item.event_type === 'deliverable_approved') && origin === 'signal_emergent' && (
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
                              <span>·</span>
                              <span>v{versionNumber}</span>
                            </>
                          )}
                          {/* Item count for platform syncs */}
                          {item.event_type === 'platform_synced' && itemCount !== undefined && (
                            <>
                              <span>·</span>
                              <span>{itemCount} items</span>
                            </>
                          )}
                          <span>·</span>
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
