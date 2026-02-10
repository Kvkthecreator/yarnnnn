'use client';

/**
 * ADR-037: Activity Page (Route-based)
 *
 * Audit trail page showing what happened, when, and provenance.
 * Shows recent work, exports, imports, and deliverable runs.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Activity,
  FileText,
  Upload,
  Download,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Mail,
  MessageSquare,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';

interface ActivityItem {
  id: string;
  type: 'deliverable_run' | 'export' | 'import' | 'work';
  title: string;
  status: string;
  timestamp: string;
  metadata?: {
    deliverable_id?: string;
    version_id?: string;
    provider?: string;
    external_url?: string;
    resource_name?: string;
  };
}

export default function ActivityPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  useEffect(() => {
    loadActivity();
  }, []);

  const loadActivity = async () => {
    setLoading(true);
    try {
      // Aggregate activity from multiple sources
      const [deliverables, exportHistory, importJobs] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.integrations.getHistory().catch(() => ({ exports: [] })),
        api.integrations.listImportJobs({ limit: 20 }).catch(() => ({ jobs: [] })),
      ]);

      const items: ActivityItem[] = [];

      // Add recent deliverable versions as activity
      for (const d of deliverables.slice(0, 10)) {
        if (d.last_run_at) {
          items.push({
            id: `deliverable-${d.id}`,
            type: 'deliverable_run',
            title: d.title,
            status: d.latest_version_status || 'completed',
            timestamp: d.last_run_at,
            metadata: {
              deliverable_id: d.id,
            },
          });
        }
      }

      // Add exports
      for (const exp of exportHistory.exports.slice(0, 10)) {
        items.push({
          id: `export-${exp.id}`,
          type: 'export',
          title: `Export to ${exp.provider}`,
          status: exp.status,
          timestamp: exp.created_at,
          metadata: {
            provider: exp.provider,
            external_url: exp.external_url || undefined,
          },
        });
      }

      // Add imports
      for (const job of importJobs.jobs.slice(0, 10)) {
        items.push({
          id: `import-${job.id}`,
          type: 'import',
          title: `Import from ${job.provider}`,
          status: job.status,
          timestamp: job.created_at,
          metadata: {
            provider: job.provider,
            resource_name: job.resource_name || undefined,
          },
        });
      }

      // Sort by timestamp descending
      items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      setActivities(items.slice(0, 50));
    } catch (err) {
      console.error('Failed to load activity:', err);
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type: string, status: string) => {
    if (status === 'failed') return <XCircle className="w-4 h-4 text-red-500" />;
    if (status === 'staged' || status === 'pending') return <Clock className="w-4 h-4 text-amber-500" />;
    if (status === 'approved' || status === 'completed') return <CheckCircle2 className="w-4 h-4 text-green-500" />;

    switch (type) {
      case 'deliverable_run':
        return <Play className="w-4 h-4 text-primary" />;
      case 'export':
        return <Upload className="w-4 h-4 text-blue-500" />;
      case 'import':
        return <Download className="w-4 h-4 text-purple-500" />;
      default:
        return <Activity className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getPlatformIcon = (provider?: string) => {
    switch (provider) {
      case 'slack':
        return <MessageSquare className="w-3 h-3" />;
      case 'gmail':
        return <Mail className="w-3 h-3" />;
      case 'notion':
        return <FileText className="w-3 h-3" />;
      default:
        return null;
    }
  };

  const handleActivityClick = (activity: ActivityItem) => {
    if (activity.type === 'deliverable_run' && activity.metadata?.deliverable_id) {
      router.push(`/deliverables/${activity.metadata.deliverable_id}`);
    } else if (activity.metadata?.external_url) {
      window.open(activity.metadata.external_url, '_blank');
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Activity className="w-6 h-6" />
          <h1 className="text-2xl font-bold">Activity</h1>
        </div>
        <p className="text-muted-foreground mb-6">
          Recent actions, exports, imports, and deliverable runs.
        </p>

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
          <div className="space-y-1">
            {activities.map((activity) => (
              <button
                key={activity.id}
                onClick={() => handleActivityClick(activity)}
                className="w-full p-4 border border-border rounded-lg text-left hover:bg-muted transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{getActivityIcon(activity.type, activity.status)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{activity.title}</span>
                      {activity.metadata?.provider && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          {getPlatformIcon(activity.metadata.provider)}
                          {activity.metadata.resource_name && (
                            <span className="truncate max-w-[150px]">{activity.metadata.resource_name}</span>
                          )}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                      <span className="capitalize">{activity.status}</span>
                      <span>·</span>
                      <span>{formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}</span>
                    </div>
                  </div>
                  {activity.metadata?.external_url ? (
                    <ExternalLink className="w-4 h-4 text-muted-foreground shrink-0" />
                  ) : activity.metadata?.deliverable_id ? (
                    <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" />
                  ) : null}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
