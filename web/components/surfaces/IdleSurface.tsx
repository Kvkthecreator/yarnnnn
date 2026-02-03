'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * IdleSurface - Empty state when nothing is on the desk
 */

import { useState, useEffect } from 'react';
import { CheckCircle2, Clock, Plus, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable } from '@/types';

export function IdleSurface() {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);

  useEffect(() => {
    loadDeliverables();
  }, []);

  const loadDeliverables = async () => {
    try {
      // api.deliverables.list takes optional status string
      const data = await api.deliverables.list();
      setDeliverables(data.slice(0, 10));
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setLoading(false);
    }
  };

  const hasDeliverables = deliverables.length > 0;
  const activeDeliverables = deliverables.filter((d) => d.status === 'active');

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        {hasDeliverables ? (
          <>
            {/* All caught up state */}
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            </div>
            <h1 className="text-xl font-semibold mb-2">All caught up</h1>
            <p className="text-muted-foreground mb-6">No deliverables need review right now.</p>

            {/* Upcoming deliverables */}
            {activeDeliverables.length > 0 && (
              <div className="text-left">
                <h2 className="text-sm font-medium mb-3 text-center">Upcoming</h2>
                <div className="space-y-2">
                  {activeDeliverables.slice(0, 3).map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
                      className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{d.title}</span>
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
              </div>
            )}
          </>
        ) : (
          <>
            {/* Onboarding state */}
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
          </>
        )}
      </div>
    </div>
  );
}
