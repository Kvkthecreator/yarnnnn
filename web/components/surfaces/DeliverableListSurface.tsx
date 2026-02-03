'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DeliverableListSurface - List of user's recurring deliverables
 */

import { useState, useEffect } from 'react';
import { Loader2, Play, Pause, Calendar, Clock, FileText } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable, DeliverableStatus } from '@/types';

interface DeliverableListSurfaceProps {
  status?: 'active' | 'paused' | 'archived';
}

export function DeliverableListSurface({ status: initialStatus }: DeliverableListSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [currentFilter, setCurrentFilter] = useState<DeliverableStatus | 'all'>(initialStatus || 'all');

  useEffect(() => {
    loadDeliverables();
  }, [currentFilter]);

  const loadDeliverables = async () => {
    setLoading(true);
    try {
      const statusParam = currentFilter !== 'all' ? currentFilter : undefined;
      const data = await api.deliverables.list(statusParam);
      setDeliverables(data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: DeliverableStatus) => {
    switch (status) {
      case 'active':
        return <Play className="w-4 h-4 text-green-600" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-amber-500" />;
      case 'archived':
        return <FileText className="w-4 h-4 text-muted-foreground" />;
      default:
        return <Calendar className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const freq = schedule.frequency;
    const day = schedule.day;
    const time = schedule.time || '09:00';

    // Parse time for display
    let timeStr = time;
    try {
      const [hour, minute] = time.split(':').map(Number);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const h12 = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
      timeStr = `${h12}:${minute.toString().padStart(2, '0')} ${ampm}`;
    } catch {
      // Keep original
    }

    switch (freq) {
      case 'daily':
        return `Daily at ${timeStr}`;
      case 'weekly':
        return `Weekly on ${day ? day.charAt(0).toUpperCase() + day.slice(1) : 'Monday'} at ${timeStr}`;
      case 'biweekly':
        return `Every 2 weeks on ${day ? day.charAt(0).toUpperCase() + day.slice(1) : 'Monday'}`;
      case 'monthly':
        return `Monthly on the ${day || '1st'} at ${timeStr}`;
      default:
        return freq;
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Inline header with count and filters */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-muted-foreground">
            {loading ? 'Loading...' : `${deliverables.length} deliverable${deliverables.length === 1 ? '' : 's'}`}
          </p>
          <div className="flex items-center gap-2">
            {(['all', 'active', 'paused'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setCurrentFilter(f)}
                className={`px-3 py-1.5 text-xs rounded-full border ${
                  currentFilter === f
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
        ) : deliverables.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No deliverables found</p>
            <p className="text-sm text-muted-foreground mt-2">
              Ask TP to help you create a recurring deliverable
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {deliverables.map((d) => (
              <button
                key={d.id}
                onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
                className="w-full p-4 border border-border rounded-lg text-left hover:bg-muted cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(d.status)}
                    <div>
                      <span className="text-sm font-medium">{d.title}</span>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{d.deliverable_type.replace(/_/g, ' ')}</span>
                        <span>•</span>
                        <span>{formatSchedule(d.schedule)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {d.next_run_at && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>Next: {formatDistanceToNow(new Date(d.next_run_at), { addSuffix: true })}</span>
                      </div>
                    )}
                    <span className="text-xs text-muted-foreground">
                      Created {formatDistanceToNow(new Date(d.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
