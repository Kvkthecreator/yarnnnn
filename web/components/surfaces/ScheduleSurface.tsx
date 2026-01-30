'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Schedule Surface - displays scheduled/recurring work
 *
 * Note: ADR-009 Phase 3 (Scheduling) is not yet implemented.
 * This surface is forward-looking and will be functional once
 * the work_schedules table and cron infrastructure are built.
 */

import { useEffect, useState } from 'react';
import {
  Calendar,
  Clock,
  Loader2,
  Plus,
  Pause,
  Play,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { useProjectContext } from '@/contexts/ProjectContext';
import type { SurfaceData } from '@/types/surfaces';

interface ScheduleSurfaceProps {
  data: SurfaceData | null;
}

// Placeholder type until ADR-009 Phase 3 is implemented
interface ScheduledWork {
  id: string;
  name: string;
  agent_type: 'research' | 'content' | 'reporting';
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  next_run_at: string;
  last_run_at?: string;
  enabled: boolean;
}

export function ScheduleSurface({ data }: ScheduleSurfaceProps) {
  const { activeProject } = useProjectContext();
  const [schedules, setSchedules] = useState<ScheduledWork[]>([]);
  const [loading, setLoading] = useState(true);

  const projectId = data?.projectId || activeProject?.id;

  useEffect(() => {
    loadSchedules();
  }, [projectId]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      // TODO: Implement once ADR-009 Phase 3 is ready
      // const data = await api.schedules.list(projectId);
      // setSchedules(data);

      // For now, show empty state
      setSchedules([]);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (scheduleId: string, enabled: boolean) => {
    // TODO: Implement once ADR-009 Phase 3 is ready
    console.log('Toggle schedule:', scheduleId, enabled);
  };

  const handleDelete = async (scheduleId: string) => {
    // TODO: Implement once ADR-009 Phase 3 is ready
    console.log('Delete schedule:', scheduleId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const formatFrequency = (freq: string) => {
    const labels: Record<string, string> = {
      daily: 'Daily',
      weekly: 'Weekly',
      biweekly: 'Every 2 weeks',
      monthly: 'Monthly',
    };
    return labels[freq] || freq;
  };

  const formatNextRun = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Less than an hour';
    if (diffHours < 24) return `In ${diffHours} hour${diffHours > 1 ? 's' : ''}`;
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays < 7) return `In ${diffDays} days`;
    return date.toLocaleDateString();
  };

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">
          Scheduled Work
        </h3>
        <button
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 rounded transition-colors"
          onClick={() => {
            // TODO: Open create schedule modal
            console.log('Create new schedule');
          }}
        >
          <Plus className="w-3 h-3" />
          New Schedule
        </button>
      </div>

      {/* Schedules list */}
      {schedules.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm font-medium">No scheduled work yet</p>
          <p className="text-xs mt-1 mb-4">
            Set up recurring research, reports, or content generation.
          </p>
          <p className="text-xs text-muted-foreground/70 italic">
            Coming soon — ADR-009 Phase 3
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((schedule) => (
            <div
              key={schedule.id}
              className={`p-3 border rounded-lg transition-colors group ${
                schedule.enabled
                  ? 'border-border hover:border-muted-foreground/30'
                  : 'border-border/50 bg-muted/30'
              }`}
            >
              <div className="flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  {/* Name and status */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-medium ${!schedule.enabled && 'text-muted-foreground'}`}>
                      {schedule.name}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 text-xs rounded ${
                        schedule.agent_type === 'research'
                          ? 'bg-blue-100 text-blue-700'
                          : schedule.agent_type === 'content'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {schedule.agent_type}
                    </span>
                  </div>

                  {/* Frequency and timing */}
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <RefreshCw className="w-3 h-3" />
                      {formatFrequency(schedule.frequency)}
                    </span>
                    {schedule.enabled && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatNextRun(schedule.next_run_at)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleToggle(schedule.id, !schedule.enabled)}
                    className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                    title={schedule.enabled ? 'Pause schedule' : 'Resume schedule'}
                  >
                    {schedule.enabled ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(schedule.id)}
                    className="p-1 text-muted-foreground hover:text-destructive transition-colors"
                    title="Delete schedule"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
