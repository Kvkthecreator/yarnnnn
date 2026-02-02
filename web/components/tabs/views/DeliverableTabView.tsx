'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Full-page view for a deliverable tab.
 * Shows deliverable details with TP drawer available.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  User,
  Play,
  Pause,
  Loader2,
  Copy,
  Download,
  Mail,
  CheckCircle2,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  MessageSquare,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useTabs } from '@/contexts/TabContext';
import { useSurface } from '@/contexts/SurfaceContext';
import type { Deliverable, DeliverableVersion, VersionStatus } from '@/types';

interface DeliverableTabViewProps {
  deliverableId: string;
}

const VERSION_STATUS_CONFIG: Record<VersionStatus, { icon: React.ReactNode; label: string; color: string }> = {
  generating: {
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
    label: 'Generating',
    color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
  },
  staged: {
    icon: <AlertCircle className="w-4 h-4" />,
    label: 'Ready for review',
    color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30',
  },
  reviewing: {
    icon: <Clock className="w-4 h-4" />,
    label: 'In review',
    color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/30',
  },
  approved: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    label: 'Done',
    color: 'text-green-600 bg-green-50 dark:bg-green-900/30',
  },
  rejected: {
    icon: <AlertCircle className="w-4 h-4" />,
    label: 'Discarded',
    color: 'text-red-600 bg-red-50 dark:bg-red-900/30',
  },
};

export function DeliverableTabView({ deliverableId }: DeliverableTabViewProps) {
  const { updateTab, openVersionTab } = useTabs();
  const { openSurface } = useSurface();
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);

  useEffect(() => {
    loadDeliverable();
  }, [deliverableId]);

  const loadDeliverable = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      // Update tab title
      updateTab(`deliverable-${deliverableId}`, { title: detail.deliverable.title });
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;
    setIsRunning(true);
    try {
      await api.deliverables.run(deliverableId);
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run:', err);
    } finally {
      setIsRunning(false);
    }
  };

  const handlePauseResume = async () => {
    if (!deliverable) return;
    const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
    try {
      const updated = await api.deliverables.update(deliverableId, { status: newStatus });
      setDeliverable(updated);
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleCopy = async (content: string, versionId: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(versionId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleOpenReview = (version: DeliverableVersion) => {
    openVersionTab(deliverableId, version.id, `Review: ${deliverable?.title || 'Version'}`);
  };

  const handleOpenTPDrawer = () => {
    openSurface('context', { deliverableId });
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const { frequency, day, time } = schedule;
    let str = frequency.charAt(0).toUpperCase() + frequency.slice(1);
    if (day) str += ` on ${day}`;
    if (time) str += ` at ${time}`;
    return str;
  };

  const formatVersionPeriod = (version: DeliverableVersion, schedule: Deliverable['schedule']) => {
    const date = new Date(version.created_at);
    if (schedule.frequency === 'weekly') {
      const startOfWeek = new Date(date);
      startOfWeek.setDate(date.getDate() - date.getDay());
      return `Week of ${startOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
    }
    if (schedule.frequency === 'monthly') {
      return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    }
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
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

  const isPaused = deliverable.status === 'paused';
  const latestVersion = versions[0];

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold">{deliverable.title}</h1>
            {deliverable.description && (
              <p className="text-muted-foreground mt-1">{deliverable.description}</p>
            )}
            <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                {formatSchedule(deliverable.schedule)}
              </span>
              {deliverable.recipient_context?.name && (
                <span className="inline-flex items-center gap-1.5">
                  <User className="w-4 h-4" />
                  For {deliverable.recipient_context.name}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Ask TP button */}
            <button
              onClick={handleOpenTPDrawer}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-border rounded-md hover:bg-muted"
            >
              <MessageSquare className="w-4 h-4" />
              Ask TP
            </button>

            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run now
            </button>

            <button
              onClick={handlePauseResume}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
              {isPaused ? 'Resume' : 'Pause'}
            </button>
          </div>
        </div>

        {/* Paused banner */}
        {isPaused && (
          <div className="mb-6 px-4 py-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              This deliverable is paused. It won't run on schedule until resumed.
            </p>
          </div>
        )}

        {/* Latest Version */}
        {latestVersion ? (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-medium">
                  {formatVersionPeriod(latestVersion, deliverable.schedule)}
                </h2>
                <span className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium mt-1",
                  VERSION_STATUS_CONFIG[latestVersion.status].color
                )}>
                  {VERSION_STATUS_CONFIG[latestVersion.status].icon}
                  {VERSION_STATUS_CONFIG[latestVersion.status].label}
                </span>
              </div>

              {/* Actions */}
              {latestVersion.status === 'approved' && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleCopy(latestVersion.final_content || latestVersion.draft_content || '', latestVersion.id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
                  >
                    {copiedId === latestVersion.id ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedId === latestVersion.id ? 'Copied' : 'Copy'}
                  </button>
                  <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted">
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                  <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted">
                    <Mail className="w-3.5 h-3.5" />
                    Email
                  </button>
                </div>
              )}

              {(latestVersion.status === 'staged' || latestVersion.status === 'reviewing') && (
                <button
                  onClick={() => handleOpenReview(latestVersion)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90"
                >
                  Review & Approve
                </button>
              )}
            </div>

            {/* Content */}
            <div className="border border-border rounded-lg overflow-hidden">
              {latestVersion.status === 'generating' ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">Generating...</p>
                </div>
              ) : (
                <div className="p-6 bg-muted/30">
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                    {latestVersion.final_content || latestVersion.draft_content || 'No content yet'}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mb-8 text-center py-12 border border-dashed border-border rounded-lg">
            <p className="text-muted-foreground mb-4">No outputs yet</p>
            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Generate first output
            </button>
          </div>
        )}

        {/* Previous Versions */}
        {versions.length > 1 && (
          <div>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">
              Previous Outputs ({versions.length - 1})
            </h2>
            <div className="space-y-2">
              {versions.slice(1).map((version) => {
                const statusConfig = VERSION_STATUS_CONFIG[version.status];
                const content = version.final_content || version.draft_content;
                const isExpanded = expandedVersionId === version.id;

                return (
                  <div key={version.id} className="border border-border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpandedVersionId(isExpanded ? null : version.id)}
                      className="w-full flex items-center justify-between p-4 hover:bg-muted/30 text-left"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {formatVersionPeriod(version, deliverable.schedule)}
                        </span>
                        <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs", statusConfig.color)}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </span>
                      </div>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>

                    {isExpanded && content && (
                      <div className="border-t border-border p-4 bg-muted/20 max-h-96 overflow-y-auto">
                        <pre className="whitespace-pre-wrap font-sans text-sm">{content}</pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
