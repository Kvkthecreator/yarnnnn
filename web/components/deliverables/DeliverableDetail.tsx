'use client';

/**
 * ADR-018: Deliverable Detail View
 *
 * Content-first view of a deliverable:
 * - Latest version content displayed prominently
 * - Version history as dated archive (Week of X, not v1/v2)
 * - Export options (copy, PDF, DOCX)
 * - Simple thumbs up/down feedback instead of quality %
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  User,
  Play,
  Pause,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  ChevronDown,
  FileText,
  RefreshCw,
  Copy,
  Download,
  ThumbsUp,
  ThumbsDown,
  Mail,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Deliverable, DeliverableVersion, VersionStatus } from '@/types';

interface DeliverableDetailProps {
  deliverableId: string;
  onBack: () => void;
  onReview: (versionId: string) => void;
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

export function DeliverableDetail({
  deliverableId,
  onBack,
  onReview,
}: DeliverableDetailProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showAllVersions, setShowAllVersions] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    loadDeliverable();
  }, [deliverableId]);

  const loadDeliverable = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
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

  const handleDownload = (content: string, format: 'txt' | 'md') => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${deliverable?.title || 'deliverable'}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleEmailToSelf = () => {
    // Open default mail client with content
    const latestContent = latestVersion?.final_content || latestVersion?.draft_content || '';
    const subject = encodeURIComponent(deliverable?.title || 'Deliverable');
    const body = encodeURIComponent(latestContent);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  // Format version date as period label
  const formatVersionPeriod = (version: DeliverableVersion, schedule: Deliverable['schedule']) => {
    const date = new Date(version.created_at);

    if (schedule.frequency === 'weekly') {
      // Get start of week
      const startOfWeek = new Date(date);
      startOfWeek.setDate(date.getDate() - date.getDay());
      return `Week of ${startOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
    }
    if (schedule.frequency === 'monthly') {
      return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    }
    if (schedule.frequency === 'daily') {
      return date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
    }
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const { frequency, day, time } = schedule;
    let str = frequency.charAt(0).toUpperCase() + frequency.slice(1);
    if (day) str += ` on ${day}`;
    if (time) str += ` at ${time}`;
    return str;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!deliverable) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-muted-foreground mb-4">Deliverable not found</p>
        <button onClick={onBack} className="text-sm text-primary hover:underline">
          Go back
        </button>
      </div>
    );
  }

  const isPaused = deliverable.status === 'paused';
  const latestVersion = versions[0];
  const olderVersions = versions.slice(1);
  const displayedOlderVersions = showAllVersions ? olderVersions : olderVersions.slice(0, 3);

  return (
    <div className="h-full overflow-auto">
      <div className="container mx-auto max-w-4xl px-4 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-start gap-4">
            <button
              onClick={onBack}
              className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted mt-0.5"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
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
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run now
            </button>
            <button
              onClick={handlePauseResume}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
            >
              {isPaused ? (
                <>
                  <Play className="w-4 h-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="w-4 h-4" />
                  Pause
                </>
              )}
            </button>
          </div>
        </div>

        {/* Status banner */}
        {isPaused && (
          <div className="mb-6 px-4 py-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              This deliverable is paused. It won't run on schedule until resumed.
            </p>
          </div>
        )}

        {/* Latest Version - Content Front and Center */}
        {latestVersion ? (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-medium">
                  {formatVersionPeriod(latestVersion, deliverable.schedule)}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn(
                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                    VERSION_STATUS_CONFIG[latestVersion.status].color
                  )}>
                    {VERSION_STATUS_CONFIG[latestVersion.status].icon}
                    {VERSION_STATUS_CONFIG[latestVersion.status].label}
                  </span>
                  {latestVersion.feedback_notes && (
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      {latestVersion.edit_distance_score !== undefined && latestVersion.edit_distance_score < 0.1 ? (
                        <ThumbsUp className="w-3 h-3 text-green-600" />
                      ) : (
                        <ThumbsDown className="w-3 h-3 text-amber-600" />
                      )}
                      Feedback given
                    </span>
                  )}
                </div>
              </div>

              {/* Export actions for approved versions */}
              {latestVersion.status === 'approved' && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleCopy(latestVersion.final_content || latestVersion.draft_content || '', latestVersion.id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
                  >
                    {copiedId === latestVersion.id ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        Copy
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleDownload(latestVersion.final_content || latestVersion.draft_content || '', 'md')}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                  <button
                    onClick={handleEmailToSelf}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
                  >
                    <Mail className="w-3.5 h-3.5" />
                    Email to me
                  </button>
                </div>
              )}

              {/* Review CTA for staged versions */}
              {(latestVersion.status === 'staged' || latestVersion.status === 'reviewing') && (
                <button
                  onClick={() => onReview(latestVersion.id)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90"
                >
                  Review & Approve
                </button>
              )}
            </div>

            {/* Content display */}
            <div className="border border-border rounded-lg overflow-hidden">
              {latestVersion.status === 'generating' ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">Generating your deliverable...</p>
                  <p className="text-xs text-muted-foreground mt-1">This may take a minute or two</p>
                </div>
              ) : (
                <div className="p-6 bg-muted/30">
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed bg-transparent p-0 m-0">
                      {latestVersion.final_content || latestVersion.draft_content || 'No content yet'}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mb-8 text-center py-12 border border-dashed border-border rounded-lg">
            <FileText className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
            <p className="text-muted-foreground mb-4">No outputs yet</p>
            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Generate first output
                </>
              )}
            </button>
          </div>
        )}

        {/* Previous Versions / Archive */}
        {olderVersions.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                Previous Outputs
              </h2>
              <button
                onClick={loadDeliverable}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2">
              {displayedOlderVersions.map((version) => {
                const statusConfig = VERSION_STATUS_CONFIG[version.status];
                const content = version.final_content || version.draft_content;

                return (
                  <div
                    key={version.id}
                    className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {formatVersionPeriod(version, deliverable.schedule)}
                        </span>
                        <span className={cn(
                          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                          statusConfig.color
                        )}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </span>
                      </div>
                      {content && (
                        <p className="text-xs text-muted-foreground mt-1 truncate max-w-md">
                          {content.slice(0, 100)}...
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-1 ml-4">
                      {version.status === 'approved' && content && (
                        <button
                          onClick={() => handleCopy(content, version.id)}
                          className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
                          title="Copy"
                        >
                          {copiedId === version.id ? (
                            <CheckCircle2 className="w-4 h-4 text-green-600" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      )}
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </div>
                );
              })}
            </div>

            {olderVersions.length > 3 && (
              <button
                onClick={() => setShowAllVersions(!showAllVersions)}
                className="w-full mt-3 py-2 text-sm text-muted-foreground hover:text-foreground flex items-center justify-center gap-1"
              >
                {showAllVersions ? (
                  <>Show less</>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show {olderVersions.length - 3} more
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
