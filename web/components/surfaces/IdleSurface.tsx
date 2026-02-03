'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * IdleSurface - Dashboard view showing all domains
 */

import { useState, useEffect } from 'react';
import { Clock, Loader2, Pause, AlertCircle, Briefcase, Brain, FileText, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable, ScheduleConfig, Work, Document as DocType } from '@/types';

// Format schedule to human readable string
function formatSchedule(schedule?: ScheduleConfig): string | null {
  if (!schedule) return null;
  const { frequency, day, time } = schedule;
  if (frequency === 'daily') return `Daily${time ? ` at ${time}` : ''}`;
  if (frequency === 'weekly') return `Weekly${day ? ` on ${day}` : ''}`;
  if (frequency === 'biweekly') return `Every 2 weeks${day ? ` on ${day}` : ''}`;
  if (frequency === 'monthly') return `Monthly${day ? ` on ${day}` : ''}`;
  if (frequency === 'custom') return 'Custom schedule';
  return frequency;
}

interface DashboardData {
  deliverables: Deliverable[];
  recentWork: Work[];
  memoryCount: number;
  recentDocs: DocType[];
}

export function IdleSurface() {
  const { setSurface, attention } = useDesk();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [deliverables, workResult, memories, docsResult] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.work.listAll({ limit: 5 }).catch(() => ({ work: [] })),
        api.userMemories.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setData({
        deliverables: deliverables || [],
        recentWork: (workResult.work || []).slice(0, 5),
        memoryCount: memories?.length || 0,
        recentDocs: (docsResult.documents || []).slice(0, 3),
      });
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  // Show onboarding if no deliverables
  if (!loading && (!data?.deliverables || data.deliverables.length === 0)) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <h1 className="text-xl font-semibold mb-2">Welcome to YARNNN</h1>
          <p className="text-muted-foreground mb-6">
            Tell me what recurring work you produce, and I&apos;ll help you automate it.
          </p>

          <div className="space-y-2">
            <p className="text-sm text-muted-foreground mb-3">Common examples:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Weekly status report',
                'Monthly client update',
                'Team meeting notes',
                'Competitive research',
              ].map((example) => (
                <button
                  key={example}
                  className="px-3 py-1.5 text-sm border border-border rounded-full hover:bg-muted hover:border-primary/50"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const activeDeliverables = data?.deliverables.filter((d) => d.status === 'active') || [];
  const pausedDeliverables = data?.deliverables.filter((d) => d.status === 'paused') || [];

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-8">
        {/* Needs Attention */}
        {attention.length > 0 && (
          <DashboardSection
            icon={<AlertCircle className="w-4 h-4 text-amber-500" />}
            title={`Needs Attention (${attention.length})`}
          >
            {attention.map((item) => (
              <button
                key={item.versionId}
                onClick={() =>
                  setSurface({
                    type: 'deliverable-review',
                    deliverableId: item.deliverableId,
                    versionId: item.versionId,
                  })
                }
                className="w-full p-3 border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-950/50 text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{item.title}</span>
                  <span className="text-xs text-muted-foreground">
                    staged {formatDistanceToNow(new Date(item.stagedAt), { addSuffix: false })} ago
                  </span>
                </div>
              </button>
            ))}
          </DashboardSection>
        )}

        {/* Deliverables */}
        <DashboardSection
          icon={<Briefcase className="w-4 h-4" />}
          title="Deliverables"
          action={
            data && data.deliverables.length > 3 ? (
              <button
                onClick={() => setSurface({ type: 'idle' })}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View all ({data.deliverables.length})
                <ChevronRight className="w-3 h-3" />
              </button>
            ) : undefined
          }
        >
          {activeDeliverables.slice(0, 5).map((d) => (
            <DeliverableCard
              key={d.id}
              deliverable={d}
              onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
            />
          ))}
          {pausedDeliverables.length > 0 && (
            <p className="text-xs text-muted-foreground pt-2">
              + {pausedDeliverables.length} paused
            </p>
          )}
        </DashboardSection>

        {/* Recent Work */}
        {data?.recentWork && data.recentWork.length > 0 && (
          <DashboardSection
            icon={<Briefcase className="w-4 h-4" />}
            title="Recent Work"
            action={
              <button
                onClick={() => setSurface({ type: 'work-list' })}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View all
                <ChevronRight className="w-3 h-3" />
              </button>
            }
          >
            {data.recentWork.slice(0, 3).map((w) => (
              <button
                key={w.id}
                onClick={() => setSurface({ type: 'work-output', workId: w.id })}
                disabled={w.status !== 'completed'}
                className={`w-full p-3 border border-border rounded-lg text-left ${
                  w.status === 'completed' ? 'hover:bg-muted' : 'opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{w.task}</span>
                    <p className="text-xs text-muted-foreground">{w.agent_type}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(w.created_at), { addSuffix: true })}
                  </span>
                </div>
              </button>
            ))}
          </DashboardSection>
        )}

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-4">
          {/* Context */}
          <button
            onClick={() => setSurface({ type: 'context-browser', scope: 'user' })}
            className="p-4 border border-border rounded-lg hover:bg-muted text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <Brain className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Context</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.memoryCount || 0} memories
            </p>
          </button>

          {/* Documents */}
          <button
            onClick={() => setSurface({ type: 'document-list' })}
            className="p-4 border border-border rounded-lg hover:bg-muted text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Documents</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.recentDocs?.length || 0} uploaded
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function DashboardSection({
  icon,
  title,
  action,
  children,
}: {
  icon?: React.ReactNode;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium flex items-center gap-2">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function DeliverableCard({
  deliverable,
  onClick,
}: {
  deliverable: Deliverable;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {deliverable.status === 'paused' ? (
            <Pause className="w-3 h-3 text-amber-500" />
          ) : (
            <span className="w-2 h-2 rounded-full bg-green-500" />
          )}
          <div>
            <span className="text-sm font-medium">{deliverable.title}</span>
            {formatSchedule(deliverable.schedule) && (
              <p className="text-xs text-muted-foreground">{formatSchedule(deliverable.schedule)}</p>
            )}
          </div>
        </div>
        {deliverable.next_run_at && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </button>
  );
}
