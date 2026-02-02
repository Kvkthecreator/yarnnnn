'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Home tab renderer - the dashboard/overview view.
 * Shows: items needing attention, upcoming deliverables, recent activity.
 */

import { useState, useEffect } from 'react';
import { Loader2, Plus, Calendar, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { Tab, TabType } from '@/lib/tabs';
import type { Deliverable } from '@/types';

interface HomeTabContentProps {
  tab: Tab;
  updateStatus: (status: 'idle' | 'loading' | 'error' | 'unsaved') => void;
  updateData: (data: Record<string, unknown>) => void;
  openTab: (type: TabType, title: string, resourceId?: string, data?: Record<string, unknown>) => void;
  closeTab: (tabId: string) => void;
}

export function HomeTabContent({
  tab,
  updateStatus,
  updateData,
  openTab,
}: HomeTabContentProps) {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDeliverables();
  }, []);

  const loadDeliverables = async () => {
    setLoading(true);
    updateStatus('loading');
    setError(null);

    try {
      const data = await api.deliverables.list();
      setDeliverables(data);
      updateData({ deliverables: data });
      updateStatus('idle');
    } catch (err) {
      console.error('Failed to load deliverables:', err);
      setError('Failed to load deliverables');
      updateStatus('error');
    } finally {
      setLoading(false);
    }
  };

  // Separate deliverables by status
  const stagedDeliverables = deliverables.filter(d => d.latest_version_status === 'staged');
  const activeDeliverables = deliverables.filter(d => d.status === 'active' && d.latest_version_status !== 'staged');
  const recentlyApproved = deliverables
    .filter(d => d.latest_version_status === 'approved')
    .slice(0, 3);

  const handleOpenDeliverable = (deliverable: Deliverable) => {
    openTab('deliverable', deliverable.title, deliverable.id);
  };

  const handleOpenReview = (deliverable: Deliverable) => {
    openTab('version-review', `Review: ${deliverable.title}`, deliverable.id);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <button
          onClick={loadDeliverables}
          className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (deliverables.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 p-8">
        <div className="text-center max-w-md">
          <h2 className="text-lg font-medium mb-2">Welcome to YARNNN</h2>
          <p className="text-muted-foreground mb-6">
            Set up your first recurring deliverable and YARNNN will produce it on schedule,
            improving every cycle.
          </p>
          <div className="text-sm text-muted-foreground mb-4">
            Use the input below to tell TP what you need, or describe your first deliverable.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto p-6 space-y-8">
        {/* Greeting */}
        <div>
          <h1 className="text-xl font-medium">
            {getGreeting()}
          </h1>
          <p className="text-muted-foreground text-sm">
            {getSummary(stagedDeliverables.length, activeDeliverables.length)}
          </p>
        </div>

        {/* Needs attention */}
        {stagedDeliverables.length > 0 && (
          <section>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Needs attention
            </h2>
            <div className="space-y-2">
              {stagedDeliverables.map(deliverable => (
                <button
                  key={deliverable.id}
                  onClick={() => handleOpenReview(deliverable)}
                  className="w-full flex items-center gap-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors text-left"
                >
                  <div className="p-2 bg-amber-100 dark:bg-amber-800/50 rounded-lg">
                    <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{deliverable.title}</div>
                    <div className="text-sm text-amber-700 dark:text-amber-300">
                      Ready for review
                    </div>
                  </div>
                  <span className="text-sm text-amber-600 dark:text-amber-400">
                    Review →
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* All caught up */}
        {stagedDeliverables.length === 0 && (
          <section className="p-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400" />
              <div>
                <div className="font-medium text-green-800 dark:text-green-200">All caught up!</div>
                <div className="text-sm text-green-700 dark:text-green-300">
                  No deliverables need review right now.
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Upcoming */}
        {activeDeliverables.length > 0 && (
          <section>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Upcoming
            </h2>
            <div className="space-y-2">
              {activeDeliverables.slice(0, 5).map(deliverable => (
                <button
                  key={deliverable.id}
                  onClick={() => handleOpenDeliverable(deliverable)}
                  className="w-full flex items-center gap-4 p-3 border border-border rounded-lg hover:bg-muted/50 transition-colors text-left"
                >
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{deliverable.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatSchedule(deliverable.schedule)}
                    </div>
                  </div>
                  {deliverable.quality_score !== undefined && (
                    <span className="text-xs text-muted-foreground">
                      {Math.round((1 - deliverable.quality_score) * 100)}% match
                    </span>
                  )}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Recent */}
        {recentlyApproved.length > 0 && (
          <section>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Recently completed
            </h2>
            <div className="space-y-1">
              {recentlyApproved.map(deliverable => (
                <button
                  key={deliverable.id}
                  onClick={() => handleOpenDeliverable(deliverable)}
                  className="w-full flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 transition-colors text-left"
                >
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span className="text-sm">{deliverable.title}</span>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// Helper functions
function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function getSummary(staged: number, active: number): string {
  if (staged > 0) {
    return `You have ${staged} ${staged === 1 ? 'deliverable' : 'deliverables'} ready for review.`;
  }
  if (active > 0) {
    return `${active} active ${active === 1 ? 'deliverable' : 'deliverables'} running on schedule.`;
  }
  return 'Get started by creating your first deliverable.';
}

function formatSchedule(schedule: { frequency: string; day?: string; time?: string }): string {
  const { frequency, day, time } = schedule;
  let str = frequency.charAt(0).toUpperCase() + frequency.slice(1);
  if (day) str += ` on ${day}`;
  if (time) str += ` at ${time}`;
  return str;
}
