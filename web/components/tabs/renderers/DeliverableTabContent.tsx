'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Deliverable tab renderer - shows deliverable detail.
 * Adapted from DeliverableDetail.tsx but as a tab content renderer.
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  Calendar,
  User,
  Play,
  Pause,
  Clock,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { Tab, TabType } from '@/lib/tabs';
import { cn } from '@/lib/utils';
import type { Deliverable, DeliverableVersion, VersionStatus, FeedbackSummary } from '@/types';

interface DeliverableTabContentProps {
  tab: Tab;
  updateStatus: (status: 'idle' | 'loading' | 'error' | 'unsaved') => void;
  updateData: (data: Record<string, unknown>) => void;
  openTab: (type: TabType, title: string, resourceId?: string, data?: Record<string, unknown>) => void;
  closeTab: (tabId: string) => void;
}

const VERSION_STATUS_CONFIG: Record<VersionStatus, { icon: React.ReactNode; label: string; color: string }> = {
  generating: { icon: <Loader2 className="w-3 h-3 animate-spin" />, label: 'Generating', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  staged: { icon: <AlertCircle className="w-3 h-3" />, label: 'Ready for review', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  reviewing: { icon: <Clock className="w-3 h-3" />, label: 'In review', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  approved: { icon: <CheckCircle2 className="w-3 h-3" />, label: 'Approved', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  rejected: { icon: <AlertCircle className="w-3 h-3" />, label: 'Rejected', color: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
};

export function DeliverableTabContent({
  tab,
  updateStatus,
  updateData,
  openTab,
}: DeliverableTabContentProps) {
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [showAllVersions, setShowAllVersions] = useState(false);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const deliverableId = tab.resourceId;

  useEffect(() => {
    if (deliverableId) {
      loadDeliverable();
    }
  }, [deliverableId]);

  const loadDeliverable = async () => {
    if (!deliverableId) return;

    setLoading(true);
    updateStatus('loading');

    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setFeedbackSummary(detail.feedback_summary || null);
      updateData({ deliverable: detail.deliverable, versions: detail.versions });
      updateStatus('idle');
    } catch (err) {
      console.error('Failed to load deliverable:', err);
      updateStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    if (!deliverableId || isRunning) return;

    setIsRunning(true);
    try {
      await api.deliverables.run(deliverableId);
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run deliverable:', err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleTogglePause = async () => {
    if (!deliverable || !deliverableId) return;

    const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
    try {
      await api.deliverables.update(deliverableId, { status: newStatus });
      setDeliverable(prev => prev ? { ...prev, status: newStatus } : null);
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    }
  };

  const handleCopy = async (content: string, versionId: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(versionId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const { frequency, day, time } = schedule;
    let str = frequency.charAt(0).toUpperCase() + frequency.slice(1);
    if (day) str += ` on ${day}`;
    if (time) str += ` at ${time}`;
    return str;
  };

  const formatQualityScore = (score: number | undefined): string => {
    if (score === undefined || score === null) return '';
    const quality = Math.round((1 - score) * 100);
    return `${quality}%`;
  };

  const getQualityIndicator = (score: number | undefined) => {
    if (score === undefined || score === null) return null;
    if (score < 0.1) return { icon: <TrendingUp className="w-3 h-3" />, color: 'text-green-600', label: 'Excellent' };
    if (score < 0.3) return { icon: <Minus className="w-3 h-3" />, color: 'text-muted-foreground', label: 'Good' };
    return { icon: <TrendingDown className="w-3 h-3" />, color: 'text-amber-600', label: 'Needs work' };
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

  const latestVersion = versions[0];
  const olderVersions = versions.slice(1);
  const displayedOlderVersions = showAllVersions ? olderVersions : olderVersions.slice(0, 3);
  const isPaused = deliverable.status === 'paused';

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-medium">{deliverable.title}</h1>
            <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                {formatSchedule(deliverable.schedule)}
              </span>
              {deliverable.recipient_context?.name && (
                <span className="flex items-center gap-1.5">
                  <User className="w-4 h-4" />
                  {deliverable.recipient_context.name}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunNow}
              disabled={isRunning || isPaused}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run now
            </button>
            <button
              onClick={handleTogglePause}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted"
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
              {isPaused ? 'Resume' : 'Pause'}
            </button>
          </div>
        </div>

        {/* Paused notice */}
        {isPaused && (
          <div className="mb-6 px-4 py-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              This deliverable is paused. It won't run on schedule until resumed.
            </p>
          </div>
        )}

        {/* Feedback Summary */}
        {feedbackSummary?.has_feedback && (
          <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-800/50 rounded-lg">
                <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-purple-900 dark:text-purple-100 mb-1">
                  YARNNN is learning your preferences
                </h3>
                {feedbackSummary.avg_quality !== undefined && (
                  <p className="text-xs text-purple-700 dark:text-purple-300 mb-2">
                    Average quality: {feedbackSummary.avg_quality}% match across {feedbackSummary.approved_versions} approved versions
                  </p>
                )}
                {feedbackSummary.learned_preferences.length > 0 && (
                  <ul className="text-xs text-purple-800 dark:text-purple-200 space-y-1">
                    {feedbackSummary.learned_preferences.map((pref, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-purple-500 mt-0.5">•</span>
                        <span>{pref}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Latest Version */}
        {latestVersion && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-medium">Latest Version</h2>
              <span className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                VERSION_STATUS_CONFIG[latestVersion.status].color
              )}>
                {VERSION_STATUS_CONFIG[latestVersion.status].icon}
                {VERSION_STATUS_CONFIG[latestVersion.status].label}
              </span>
            </div>

            {latestVersion.status === 'staged' && (
              <button
                onClick={() => openTab('version-review', `Review: ${deliverable.title}`, latestVersion.id)}
                className="w-full p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-amber-800 dark:text-amber-200">Ready for review</div>
                    <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                      {(latestVersion.draft_content || '').slice(0, 100)}...
                    </div>
                  </div>
                  <span className="text-amber-600 dark:text-amber-400">Review →</span>
                </div>
              </button>
            )}

            {latestVersion.status === 'approved' && latestVersion.final_content && (
              <div className="p-4 border border-border rounded-lg">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed max-h-48 overflow-y-auto">
                  {latestVersion.final_content.slice(0, 500)}
                  {latestVersion.final_content.length > 500 && '...'}
                </pre>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
                  <button
                    onClick={() => handleCopy(latestVersion.final_content!, latestVersion.id)}
                    className="inline-flex items-center gap-1.5 px-2 py-1 text-xs border border-border rounded-md hover:bg-muted"
                  >
                    {copiedId === latestVersion.id ? (
                      <><CheckCircle2 className="w-3 h-3 text-green-600" /> Copied</>
                    ) : (
                      <><Copy className="w-3 h-3" /> Copy</>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Version History */}
        {olderVersions.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">
              Previous Versions ({olderVersions.length})
            </h2>

            <div className="space-y-2">
              {displayedOlderVersions.map((version) => {
                const statusConfig = VERSION_STATUS_CONFIG[version.status];
                const qualityIndicator = getQualityIndicator(version.edit_distance_score);

                return (
                  <div
                    key={version.id}
                    className="p-3 border border-border rounded-lg hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                          statusConfig.color
                        )}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </span>
                        {version.status === 'approved' && qualityIndicator && (
                          <span className={cn("inline-flex items-center gap-1 text-xs", qualityIndicator.color)}>
                            {qualityIndicator.icon}
                            {formatQualityScore(version.edit_distance_score)} match
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(version.created_at).toLocaleDateString()}
                      </span>
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
                  <><ChevronUp className="w-4 h-4" /> Show less</>
                ) : (
                  <><ChevronDown className="w-4 h-4" /> Show {olderVersions.length - 3} more</>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
