'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DeliverableDetailSurface - View deliverable details and history
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  Play,
  Pause,
  Settings,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow, format } from 'date-fns';
import { cacheEntity } from '@/lib/entity-cache';
import type { Deliverable, DeliverableVersion, FeedbackSummary } from '@/types';

interface DeliverableDetailSurfaceProps {
  deliverableId: string;
}

export function DeliverableDetailSurface({ deliverableId }: DeliverableDetailSurfaceProps) {
  const { setSurface, refreshAttention } = useDesk();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);

  useEffect(() => {
    loadDeliverable();
  }, [deliverableId]);

  const loadDeliverable = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setFeedbackSummary(detail.feedback_summary || null);

      // Cache the deliverable name for TPBar display
      if (detail.deliverable?.title) {
        cacheEntity(deliverableId, detail.deliverable.title, 'deliverable');
      }
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;

    setRunning(true);
    try {
      const result = await api.deliverables.run(deliverableId);
      if (result.success && result.version_id) {
        // Refresh to show new version
        await loadDeliverable();
        await refreshAttention();

        // If version is already staged, open review
        if (result.status === 'staged') {
          setSurface({
            type: 'deliverable-review',
            deliverableId,
            versionId: result.version_id,
          });
        }
      }
    } catch (err) {
      console.error('Failed to run deliverable:', err);
      alert('Failed to run. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  const handleTogglePause = async () => {
    if (!deliverable) return;

    try {
      const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
      await api.deliverables.update(deliverableId, { status: newStatus });
      setDeliverable({ ...deliverable, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const openVersionReview = (version: DeliverableVersion) => {
    if (version.status === 'staged' || version.status === 'reviewing') {
      setSurface({
        type: 'deliverable-review',
        deliverableId,
        versionId: version.id,
      });
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!deliverable) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Deliverable not found
      </div>
    );
  }

  const formatSchedule = () => {
    const s = deliverable.schedule;
    if (!s) return 'No schedule';

    const time = s.time || '09:00';
    const day = s.day
      ? s.day.charAt(0).toUpperCase() + s.day.slice(1)
      : s.frequency === 'monthly'
      ? '1st'
      : 'Monday';

    switch (s.frequency) {
      case 'daily':
        return `Daily at ${time}`;
      case 'weekly':
        return `Weekly on ${day} at ${time}`;
      case 'biweekly':
        return `Every 2 weeks on ${day} at ${time}`;
      case 'monthly':
        return `Monthly on the ${day} at ${time}`;
      default:
        return s.frequency || 'Custom';
    }
  };

  const getTrendIcon = () => {
    switch (deliverable.quality_trend) {
      case 'improving':
        return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'declining':
        return <TrendingDown className="w-4 h-4 text-red-600" />;
      default:
        return <Minus className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getVersionStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle2 className="w-4 h-4 text-green-600" />;
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'staged':
      case 'reviewing':
        return <AlertCircle className="w-4 h-4 text-amber-500" />;
      case 'generating':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div>
          <h1 className="font-medium">{deliverable.title}</h1>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            {formatSchedule()}
            {deliverable.next_run_at && (
              <span className="text-muted-foreground">
                • Next: {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTogglePause}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            {deliverable.status === 'paused' ? (
              <>
                <Play className="w-3.5 h-3.5" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5" />
                Pause
              </>
            )}
          </button>
          <button className="p-1.5 border border-border rounded-md hover:bg-muted">
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          {/* Quality metrics */}
          {deliverable.quality_score !== undefined && (
            <div className="mb-6 p-4 border border-border rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Quality Score</span>
                <div className="flex items-center gap-2">
                  {getTrendIcon()}
                  <span className="text-lg font-semibold">
                    {Math.round((1 - deliverable.quality_score) * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {deliverable.quality_trend === 'improving'
                  ? 'Outputs are requiring fewer edits over time.'
                  : deliverable.quality_trend === 'declining'
                  ? 'Recent outputs have needed more edits.'
                  : 'Quality has been consistent.'}
              </p>

              {feedbackSummary?.learned_preferences &&
                feedbackSummary.learned_preferences.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs font-medium mb-1">Learned preferences:</p>
                    <ul className="text-xs text-muted-foreground space-y-0.5">
                      {feedbackSummary.learned_preferences.slice(0, 3).map((pref, i) => (
                        <li key={i}>• {pref}</li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          )}

          {/* Run now button */}
          <div className="mb-6">
            <button
              onClick={handleRunNow}
              disabled={running || deliverable.status === 'archived'}
              className="w-full py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Now
                </>
              )}
            </button>
          </div>

          {/* Version history */}
          <div>
            <h2 className="text-sm font-medium mb-3">Version History</h2>
            <div className="space-y-2">
              {versions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No versions yet</p>
              ) : (
                versions.map((version) => (
                  <button
                    key={version.id}
                    onClick={() => openVersionReview(version)}
                    disabled={version.status !== 'staged' && version.status !== 'reviewing'}
                    className={`
                      w-full p-3 border border-border rounded-lg text-left
                      ${
                        version.status === 'staged' || version.status === 'reviewing'
                          ? 'hover:bg-muted cursor-pointer'
                          : 'opacity-60 cursor-default'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getVersionStatusIcon(version.status)}
                        <span className="text-sm font-medium">v{version.version_number}</span>
                        <span className="text-xs text-muted-foreground capitalize">
                          {version.status}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(version.created_at), 'MMM d, h:mm a')}
                      </span>
                    </div>

                    {version.edit_distance_score !== undefined && version.status === 'approved' && (
                      <div className="mt-1.5 text-xs text-muted-foreground">
                        {version.edit_distance_score < 0.1
                          ? 'Approved as-is'
                          : version.edit_distance_score < 0.3
                          ? 'Minor edits made'
                          : 'Significant edits made'}
                      </div>
                    )}

                    {version.feedback_notes && (
                      <div className="mt-1.5 text-xs text-muted-foreground truncate">
                        Note: {version.feedback_notes}
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
