'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * IdleSurface - Home view showing all deliverables
 */

import { useState, useEffect } from 'react';
import { Clock, Plus, Loader2, Pause, Archive } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable, ScheduleConfig } from '@/types';

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

type FilterType = 'all' | 'active' | 'paused';

export function IdleSurface() {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [filter, setFilter] = useState<FilterType>('all');

  useEffect(() => {
    loadDeliverables();
  }, []);

  const loadDeliverables = async () => {
    try {
      const data = await api.deliverables.list();
      setDeliverables(data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredDeliverables = deliverables.filter((d) => {
    if (filter === 'all') return true;
    if (filter === 'active') return d.status === 'active';
    if (filter === 'paused') return d.status === 'paused';
    return true;
  });

  const getStatusIndicator = (status: string) => {
    switch (status) {
      case 'active':
        return <span className="w-2 h-2 rounded-full bg-green-500" />;
      case 'paused':
        return <Pause className="w-3 h-3 text-amber-500" />;
      case 'archived':
        return <Archive className="w-3 h-3 text-muted-foreground" />;
      default:
        return null;
    }
  };

  // Show onboarding if no deliverables
  if (!loading && deliverables.length === 0) {
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

          <div className="mt-8 pt-6 border-t border-border">
            <button className="inline-flex items-center gap-2 text-sm text-primary hover:underline">
              <Plus className="w-4 h-4" />
              Create your first deliverable
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Inline header with count and filters */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-muted-foreground">
            {loading ? 'Loading...' : `${filteredDeliverables.length} deliverable${filteredDeliverables.length === 1 ? '' : 's'}`}
          </p>
          <div className="flex items-center gap-2">
            {(['all', 'active', 'paused'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs rounded-full border ${
                  filter === f
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'border-border hover:bg-muted'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredDeliverables.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No deliverables match this filter</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredDeliverables.map((d) => (
              <button
                key={d.id}
                onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
                className="w-full p-4 border border-border rounded-lg hover:bg-muted text-left"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIndicator(d.status)}
                    <div>
                      <span className="text-sm font-medium">{d.title}</span>
                      {formatSchedule(d.schedule) && (
                        <p className="text-xs text-muted-foreground">{formatSchedule(d.schedule)}</p>
                      )}
                    </div>
                  </div>
                  {d.next_run_at && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(d.next_run_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
