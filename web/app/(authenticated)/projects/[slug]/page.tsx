'use client';

/**
 * Project Detail Page — ADR-119 Phase 4
 *
 * Shows project info, contributors, assemblies, and activity timeline.
 * Data from GET /projects/{slug} + GET /projects/{slug}/activity.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Loader2,
  ChevronLeft,
  FolderKanban,
  Users,
  Package,
  FileText,
  HeartPulse,
  AlertTriangle,
  FastForward,
  TrendingUp,
  Archive,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format, isToday, isYesterday, startOfDay } from 'date-fns';
import { cn } from '@/lib/utils';
import type { ProjectDetail, ProjectActivityItem } from '@/types';

// =============================================================================
// Activity event rendering — personified language
// =============================================================================

const ACTIVITY_EVENT_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
}> = {
  project_heartbeat: {
    label: 'Check-in',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-purple-500',
  },
  project_assembled: {
    label: 'Assembly',
    icon: <Package className="w-4 h-4" />,
    color: 'text-green-500',
  },
  project_escalated: {
    label: 'Needs attention',
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-amber-500',
  },
  project_contributor_advanced: {
    label: 'Early run',
    icon: <FastForward className="w-4 h-4" />,
    color: 'text-blue-500',
  },
  duty_promoted: {
    label: 'Promotion',
    icon: <TrendingUp className="w-4 h-4" />,
    color: 'text-green-500',
  },
};

function formatActivitySummary(item: ProjectActivityItem): string {
  const meta = item.metadata || {};
  switch (item.event_type) {
    case 'project_heartbeat': {
      const fresh = meta.contributors_fresh ?? '?';
      const stale = Number(meta.contributors_stale) || 0;
      return stale > 0
        ? `PM checked on contributors — ${fresh} fresh, ${stale} overdue`
        : `PM checked on contributors — all ${fresh} fresh`;
    }
    case 'project_assembled':
      return item.summary || 'Assembled outputs and delivered';
    case 'project_escalated':
      return `PM flagged an issue${meta.reason ? ` — ${meta.reason}` : ''}`;
    case 'project_contributor_advanced':
      return `PM asked ${meta.target_agent_slug || 'a contributor'} to run early${meta.reason ? ` — ${meta.reason}` : ''}`;
    case 'duty_promoted':
      return item.summary || 'Agent earned a new duty';
    default:
      return item.summary || item.event_type;
  }
}

function groupByDay(items: ProjectActivityItem[]): { label: string; items: ProjectActivityItem[] }[] {
  const groups: Map<string, ProjectActivityItem[]> = new Map();
  for (const item of items) {
    const date = new Date(item.created_at);
    const key = startOfDay(date).toISOString();
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }

  return Array.from(groups.entries()).map(([key, groupItems]) => {
    const date = new Date(key);
    let label: string;
    if (isToday(date)) label = 'Today';
    else if (isYesterday(date)) label = 'Yesterday';
    else label = format(date, 'MMM d, yyyy');
    return { label, items: groupItems };
  });
}

// =============================================================================
// Main Component
// =============================================================================

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
  const [archiving, setArchiving] = useState(false);

  const loadProject = useCallback(async () => {
    try {
      const [detail, activityData] = await Promise.all([
        api.projects.get(slug),
        api.projects.getActivity(slug, 30).catch(() => ({ activities: [], total: 0 })),
      ]);
      setProject(detail);
      setActivities(activityData.activities);
    } catch (err) {
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  const handleArchive = async () => {
    if (!confirm('Archive this project? This will hide it from the active list.')) return;
    setArchiving(true);
    try {
      await api.projects.archive(slug);
      router.push('/projects');
    } catch (err) {
      console.error('Failed to archive project:', err);
      setArchiving(false);
    }
  };

  // Loading
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not found
  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FolderKanban className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Project not found</p>
        <button onClick={() => router.push('/projects')} className="text-sm text-primary hover:underline">
          Back to Projects
        </button>
      </div>
    );
  }

  const { project: meta, contributions, assemblies } = project;
  const title = meta.title || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const intent = meta.intent;
  const contributors = meta.contributors || [];
  const activityGroups = groupByDay(activities);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Breadcrumb */}
        <Link
          href="/projects"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Projects
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">{title}</h1>
            {intent && (
              <div className="flex flex-wrap gap-2 mt-2">
                {intent.deliverable && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {intent.deliverable}
                  </span>
                )}
                {intent.audience && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    For {intent.audience}
                  </span>
                )}
                {intent.format && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {intent.format}
                  </span>
                )}
              </div>
            )}
            {intent?.purpose && (
              <p className="text-sm text-muted-foreground mt-2">{intent.purpose}</p>
            )}
          </div>
          <button
            onClick={handleArchive}
            disabled={archiving}
            className="text-xs text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1"
            title="Archive project"
          >
            {archiving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Archive className="w-3 h-3" />}
            Archive
          </button>
        </div>

        {/* Contributors */}
        {contributors.length > 0 && (
          <section className="mb-6">
            <h2 className="text-sm font-medium flex items-center gap-1.5 mb-3">
              <Users className="w-4 h-4 text-muted-foreground" />
              Contributors
            </h2>
            <div className="border border-border rounded-lg divide-y divide-border overflow-hidden">
              {contributors.map((c) => {
                const contribFiles = contributions[c.agent_slug] || [];
                return (
                  <div key={c.agent_slug} className="p-3 flex items-center justify-between">
                    <div>
                      <Link
                        href={c.agent_id ? `/agents/${c.agent_id}` : '#'}
                        className={cn(
                          'text-sm font-medium',
                          c.agent_id && 'text-primary hover:underline'
                        )}
                      >
                        {c.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                      </Link>
                      {c.expected_contribution && (
                        <p className="text-xs text-muted-foreground mt-0.5">{c.expected_contribution}</p>
                      )}
                    </div>
                    {contribFiles.length > 0 && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {contribFiles.length} file{contribFiles.length === 1 ? '' : 's'}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Assemblies */}
        {assemblies.length > 0 && (
          <section className="mb-6">
            <h2 className="text-sm font-medium flex items-center gap-1.5 mb-3">
              <Package className="w-4 h-4 text-muted-foreground" />
              Assemblies
            </h2>
            <div className="border border-border rounded-lg divide-y divide-border overflow-hidden">
              {assemblies.map((path) => {
                // Extract meaningful label from assembly path
                const parts = path.split('/');
                const label = parts[parts.length - 1] || path;
                return (
                  <div key={path} className="p-3 text-sm text-muted-foreground flex items-center gap-2">
                    <FileText className="w-4 h-4 shrink-0" />
                    <span className="truncate">{label}</span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Activity Timeline */}
        <section>
          <h2 className="text-sm font-medium flex items-center gap-1.5 mb-3">
            <HeartPulse className="w-4 h-4 text-muted-foreground" />
            Activity
          </h2>
          {activityGroups.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">No activity yet — the PM will start checking in soon.</p>
          ) : (
            <div className="space-y-4">
              {activityGroups.map((group) => (
                <div key={group.label}>
                  <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                    {group.label}
                  </h3>
                  <div className="space-y-1.5">
                    {group.items.map((item) => {
                      const config = ACTIVITY_EVENT_CONFIG[item.event_type] || {
                        label: item.event_type,
                        icon: <FileText className="w-4 h-4" />,
                        color: 'text-muted-foreground',
                      };
                      return (
                        <div key={item.id} className="flex items-start gap-2 py-1.5">
                          <span className={cn('mt-0.5 shrink-0', config.color)}>
                            {config.icon}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm">{formatActivitySummary(item)}</p>
                            <p className="text-xs text-muted-foreground">
                              {format(new Date(item.created_at), 'h:mm a')}
                            </p>
                          </div>
                        </div>
                      );
                    })}
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
