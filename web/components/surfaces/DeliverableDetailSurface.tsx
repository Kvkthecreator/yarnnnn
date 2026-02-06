'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DeliverableDetailSurface - Deliverable mini-dashboard
 *
 * Shows:
 * - Status cards: Next run, Quality score, Status
 * - What it generates: Type, config summary, recipient
 * - Data sources: URLs and descriptions feeding the deliverable
 * - Version history: Recent versions with status and feedback
 * - Learned preferences: What YARNNN has learned from edits
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
  Link as LinkIcon,
  FileText,
  User,
  Sparkles,
  AlertTriangle,
  FolderOpen,
  ChevronRight,
  Eye,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow, format } from 'date-fns';
import { cacheEntity } from '@/lib/entity-cache';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import { ExportActionBar } from '@/components/desk/ExportActionBar';
import type { Deliverable, DeliverableVersion, FeedbackSummary } from '@/types';

interface DeliverableDetailSurfaceProps {
  deliverableId: string;
}

const DELIVERABLE_TYPE_LABELS: Record<string, string> = {
  status_report: 'Status Report',
  stakeholder_update: 'Stakeholder Update',
  research_brief: 'Research Brief',
  meeting_summary: 'Meeting Summary',
  custom: 'Custom',
  client_proposal: 'Client Proposal',
  performance_self_assessment: 'Performance Self-Assessment',
  newsletter_section: 'Newsletter Section',
  changelog: 'Changelog',
  one_on_one_prep: '1:1 Prep',
  board_update: 'Board Update',
};

export function DeliverableDetailSurface({ deliverableId }: DeliverableDetailSurfaceProps) {
  const { setSurface, refreshAttention, setSelectedProject } = useDesk();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

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

      // Auto-sync project context to match deliverable's project
      // This ensures TP uses the correct project context when viewing a deliverable
      if (detail.deliverable?.project_id && detail.deliverable?.project_name) {
        setSelectedProject({
          id: detail.deliverable.project_id,
          name: detail.deliverable.project_name,
        });
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
        await loadDeliverable();
        await refreshAttention();

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
    // Allow viewing any version that has content
    if (version.draft_content || version.final_content) {
      setSurface({
        type: 'deliverable-review',
        deliverableId,
        versionId: version.id,
      });
    }
  };

  const handleSettingsSaved = (updated: Deliverable) => {
    setDeliverable(updated);
    if (updated.title) {
      cacheEntity(deliverableId, updated.title, 'deliverable');
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

  // Calculate rejection streak
  const recentRejections = versions.filter((v) => v.status === 'rejected').length;
  const lastApproved = versions.find((v) => v.status === 'approved');
  const allRejected = versions.length > 0 && !lastApproved;

  // Quality score display
  const qualityPercent =
    deliverable.quality_score !== undefined
      ? Math.round((1 - deliverable.quality_score) * 100)
      : null;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-border px-4 py-3">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="font-medium text-lg truncate">{deliverable.title}</h1>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
              {deliverable.project_name && (
                <span className="flex items-center gap-1">
                  <FolderOpen className="w-3 h-3" />
                  {deliverable.project_name}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatSchedule()}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleTogglePause}
              className={cn(
                "p-1.5 border border-border rounded-md hover:bg-muted",
                deliverable.status === 'paused' && "text-amber-600 border-amber-300 bg-amber-50 hover:bg-amber-100"
              )}
              title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
            >
              {deliverable.status === 'paused' ? (
                <Play className="w-4 h-4" />
              ) : (
                <Pause className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-1.5 border border-border rounded-md hover:bg-muted"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-3xl mx-auto px-4 py-5 space-y-5">
          {/* Status Banner - show if paused or all rejected */}
          {(deliverable.status === 'paused' || allRejected) && (
            <div
              className={cn(
                'p-3 rounded-lg border flex items-start gap-3',
                deliverable.status === 'paused'
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-red-50 border-red-200 text-red-800'
              )}
            >
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="text-sm">
                {deliverable.status === 'paused' ? (
                  <>
                    <p className="font-medium">Deliverable is paused</p>
                    <p className="text-xs opacity-80 mt-0.5">
                      Scheduled runs are skipped. You can still run manually.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium">
                      Last {recentRejections} version{recentRejections !== 1 ? 's were' : ' was'}{' '}
                      rejected
                    </p>
                    <p className="text-xs opacity-80 mt-0.5">
                      YARNNN will incorporate your feedback in the next run.
                    </p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Status Cards */}
          <div className="grid grid-cols-3 gap-3">
            {/* Next Run */}
            <div className="p-3 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Next Run</p>
              {deliverable.next_run_at ? (
                <>
                  <p className="font-medium">
                    {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: false })}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {format(new Date(deliverable.next_run_at), 'EEE, MMM d')}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Not scheduled</p>
              )}
            </div>

            {/* Quality Score */}
            <div className="p-3 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Quality</p>
              {qualityPercent !== null ? (
                <div className="flex items-center gap-2">
                  <span className="font-medium text-lg">{qualityPercent}%</span>
                  {getTrendIcon()}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No data yet</p>
              )}
            </div>

            {/* Status */}
            <div className="p-3 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Status</p>
              <div className="flex items-center gap-1.5">
                <span
                  className={cn(
                    'w-2 h-2 rounded-full',
                    deliverable.status === 'active'
                      ? 'bg-green-500'
                      : deliverable.status === 'paused'
                        ? 'bg-amber-500'
                        : 'bg-gray-400'
                  )}
                />
                <span className="font-medium capitalize">{deliverable.status}</span>
              </div>
              <p className="text-xs text-muted-foreground">{versions.length} versions</p>
            </div>
          </div>

          {/* Run Now Button */}
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

          {/* Latest Output Preview */}
          {(() => {
            // Find latest version with content (approved > staged > other)
            const latestWithContent = versions.find(
              (v) =>
                (v.status === 'approved' && v.final_content) ||
                (v.status === 'staged' && v.draft_content) ||
                v.draft_content ||
                v.final_content
            );

            if (!latestWithContent) return null;

            const content =
              latestWithContent.final_content || latestWithContent.draft_content || '';
            const truncated = content.length > 500 ? content.slice(0, 500) + '...' : content;

            return (
              <div className="border border-border rounded-lg">
                <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
                  <h2 className="text-sm font-medium">Latest Output</h2>
                  <button
                    onClick={() => openVersionReview(latestWithContent)}
                    className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                  >
                    View full
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                    <span className="capitalize">{latestWithContent.status}</span>
                    <span>•</span>
                    <span>v{latestWithContent.version_number}</span>
                  </div>
                  <div className="prose prose-sm dark:prose-invert max-w-none text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {truncated}
                  </div>
                  {content.length > 500 && (
                    <button
                      onClick={() => openVersionReview(latestWithContent)}
                      className="mt-3 text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" />
                      Read more
                    </button>
                  )}
                </div>

                {/* Export option for approved versions */}
                {latestWithContent.status === 'approved' && (
                  <div className="px-4 pb-4">
                    <ExportActionBar
                      deliverableVersionId={latestWithContent.id}
                      deliverableTitle={deliverable.title}
                    />
                  </div>
                )}
              </div>
            );
          })()}

          {/* What It Generates */}
          <div className="border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">What It Generates</h2>
            </div>
            <div className="p-4 space-y-3 text-sm">
              <div className="flex items-start gap-3">
                <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium">
                    {DELIVERABLE_TYPE_LABELS[deliverable.deliverable_type] ||
                      deliverable.deliverable_type}
                  </p>
                  {deliverable.description && (
                    <p className="text-muted-foreground text-xs mt-0.5">{deliverable.description}</p>
                  )}
                </div>
              </div>

              {deliverable.recipient_context?.name && (
                <div className="flex items-start gap-3">
                  <User className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div>
                    <p>
                      For{' '}
                      <span className="font-medium">{deliverable.recipient_context.name}</span>
                      {deliverable.recipient_context.role && (
                        <span className="text-muted-foreground">
                          {' '}
                          ({deliverable.recipient_context.role})
                        </span>
                      )}
                    </p>
                    {deliverable.recipient_context.notes && (
                      <p className="text-muted-foreground text-xs mt-0.5">
                        {deliverable.recipient_context.notes}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Data Sources */}
          {deliverable.sources && deliverable.sources.length > 0 && (
            <div className="border border-border rounded-lg">
              <div className="px-4 py-3 border-b border-border bg-muted/30">
                <h2 className="text-sm font-medium">Data Sources</h2>
              </div>
              <div className="p-4">
                <div className="space-y-2">
                  {deliverable.sources.map((source, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
                      {source.type === 'url' ? (
                        <LinkIcon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                      ) : source.type === 'document' ? (
                        <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                      ) : (
                        <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                      )}
                      <span className="break-all">
                        {source.type === 'url' ? (
                          <a
                            href={source.value}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            {source.label || source.value}
                          </a>
                        ) : (
                          source.value
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Learned Preferences */}
          {feedbackSummary?.learned_preferences &&
            feedbackSummary.learned_preferences.length > 0 && (
              <div className="border border-border rounded-lg">
                <div className="px-4 py-3 border-b border-border bg-muted/30">
                  <h2 className="text-sm font-medium flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4" />
                    Learned From Your Edits
                  </h2>
                </div>
                <div className="p-4">
                  <ul className="space-y-1.5 text-sm">
                    {feedbackSummary.learned_preferences.map((pref, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{pref}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

          {/* Version History */}
          <div className="border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Version History</h2>
            </div>
            <div className="divide-y divide-border">
              {versions.length === 0 ? (
                <p className="px-4 py-6 text-sm text-muted-foreground text-center">
                  No versions yet. Run now to generate the first one.
                </p>
              ) : (
                versions.slice(0, 5).map((version) => {
                  const hasContent = version.draft_content || version.final_content;
                  return (
                  <button
                    key={version.id}
                    onClick={() => openVersionReview(version)}
                    disabled={!hasContent}
                    className={cn(
                      'w-full px-4 py-3 text-left',
                      hasContent
                        ? 'hover:bg-muted cursor-pointer'
                        : 'cursor-default opacity-60'
                    )}
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
                      <p className="mt-1 text-xs text-muted-foreground">
                        {version.edit_distance_score < 0.1
                          ? 'Approved as-is'
                          : version.edit_distance_score < 0.3
                            ? 'Minor edits made'
                            : 'Significant edits made'}
                      </p>
                    )}

                    {version.feedback_notes && (
                      <p className="mt-1 text-xs text-muted-foreground truncate">
                        "{version.feedback_notes}"
                      </p>
                    )}

                    {/* Visual indicator for clickable versions */}
                    {hasContent && (
                      <div className="flex items-center gap-1 mt-1.5 text-xs text-muted-foreground">
                        <Eye className="w-3 h-3" />
                        <span>View output</span>
                      </div>
                    )}
                  </button>
                  );
                })
              )}
            </div>
            {versions.length > 5 && (
              <div className="px-4 py-2 text-center border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing 5 of {versions.length} versions
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={handleSettingsSaved}
      />
    </div>
  );
}
