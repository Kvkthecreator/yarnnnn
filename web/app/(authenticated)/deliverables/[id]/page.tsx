'use client';

/**
 * ADR-037: Deliverable Detail Page (Route-based)
 *
 * Standalone page for viewing a specific deliverable's details.
 * Shows status, versions, sources, and links to review in chat.
 */

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
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
  ChevronRight,
  Eye,
  Mail,
  Download,
  ChevronLeft,
  Calendar,
  MessageSquare,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import type { Deliverable, DeliverableVersion, FeedbackSummary } from '@/types';
import { SourceSnapshotsBadge } from '@/components/deliverables/SourceSnapshotsSummary';

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
  inbox_summary: 'Inbox Summary',
  reply_draft: 'Reply Draft',
  follow_up_tracker: 'Follow-up Tracker',
  thread_summary: 'Thread Summary',
};

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
}> = {
  gmail: { icon: Mail, label: 'Gmail', color: 'text-red-600' },
  slack: { icon: MessageSquare, label: 'Slack', color: 'text-purple-600' },
  notion: { icon: FileText, label: 'Notion', color: 'text-gray-700' },
  download: { icon: Download, label: 'Download', color: 'text-blue-600' },
};

export default function DeliverableDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    loadDeliverable();
  }, [id]);

  const loadDeliverable = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(id);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setFeedbackSummary(detail.feedback_summary || null);
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
      const result = await api.deliverables.run(id);
      if (result.success && result.version_id) {
        await loadDeliverable();
        // Navigate to review in dashboard
        if (result.status === 'staged') {
          router.push(`/dashboard/deliverable/${id}/review/${result.version_id}`);
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
      await api.deliverables.update(id, { status: newStatus });
      setDeliverable({ ...deliverable, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const openVersionReview = (version: DeliverableVersion) => {
    if (version.draft_content || version.final_content) {
      router.push(`/dashboard/deliverable/${id}/review/${version.id}`);
    }
  };

  const handleSettingsSaved = (updated: Deliverable) => {
    setDeliverable(updated);
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
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <Calendar className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Deliverable not found</p>
        <button onClick={() => router.push('/deliverables')} className="text-sm text-primary hover:underline">
          Back to Deliverables
        </button>
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

  const recentRejections = versions.filter((v) => v.status === 'rejected').length;
  const lastApproved = versions.find((v) => v.status === 'approved');
  const allRejected = versions.length > 0 && !lastApproved;
  const qualityPercent =
    deliverable.quality_score !== undefined
      ? Math.round((1 - deliverable.quality_score) * 100)
      : null;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/deliverables')}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Back to Deliverables"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold">{deliverable.title}</h1>
              <div className="flex items-center gap-3 text-sm text-muted-foreground mt-0.5">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatSchedule()}
                </span>
                {deliverable.destination && (() => {
                  const config = PLATFORM_CONFIG[deliverable.destination.platform];
                  if (!config) return null;
                  const Icon = config.icon;
                  return (
                    <span className={cn("flex items-center gap-1", config.color)}>
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </span>
                  );
                })()}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleTogglePause}
              className={cn(
                "p-2 border border-border rounded-md hover:bg-muted",
                deliverable.status === 'paused' && "text-amber-600 border-amber-300 bg-amber-50"
              )}
              title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
            >
              {deliverable.status === 'paused' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-2 border border-border rounded-md hover:bg-muted"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status Banner */}
        {(deliverable.status === 'paused' || allRejected) && (
          <div
            className={cn(
              'p-3 rounded-lg border flex items-start gap-3 mb-6',
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
                    Last {recentRejections} version{recentRejections !== 1 ? 's were' : ' was'} rejected
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
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 border border-border rounded-lg">
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

          <div className="p-4 border border-border rounded-lg">
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

          <div className="p-4 border border-border rounded-lg">
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
          className="w-full py-3 mb-6 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
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

        {/* What It Generates */}
        <div className="border border-border rounded-lg mb-6">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <h2 className="text-sm font-medium">What It Generates</h2>
          </div>
          <div className="p-4 space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">
                  {DELIVERABLE_TYPE_LABELS[deliverable.deliverable_type] || deliverable.deliverable_type}
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
                    For <span className="font-medium">{deliverable.recipient_context.name}</span>
                    {deliverable.recipient_context.role && (
                      <span className="text-muted-foreground"> ({deliverable.recipient_context.role})</span>
                    )}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Data Sources */}
        {deliverable.sources && deliverable.sources.length > 0 && (
          <div className="border border-border rounded-lg mb-6">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Data Sources</h2>
            </div>
            <div className="p-4">
              <div className="space-y-2">
                {deliverable.sources.map((source, index) => (
                  <div key={index} className="flex items-start gap-2 text-sm">
                    {source.type === 'url' ? (
                      <LinkIcon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
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
        {feedbackSummary?.learned_preferences && feedbackSummary.learned_preferences.length > 0 && (
          <div className="border border-border rounded-lg mb-6">
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
                    <span className="text-muted-foreground">·</span>
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
              versions.slice(0, 10).map((version) => {
                const hasContent = version.draft_content || version.final_content;
                return (
                  <button
                    key={version.id}
                    onClick={() => openVersionReview(version)}
                    disabled={!hasContent}
                    className={cn(
                      'w-full px-4 py-3 text-left',
                      hasContent ? 'hover:bg-muted cursor-pointer' : 'cursor-default opacity-60'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getVersionStatusIcon(version.status)}
                        <span className="text-sm font-medium">v{version.version_number}</span>
                        <span className="text-xs text-muted-foreground capitalize">{version.status}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(version.created_at), 'MMM d, h:mm a')}
                      </span>
                    </div>

                    {version.feedback_notes && (
                      <p className="mt-1 text-xs text-muted-foreground truncate">"{version.feedback_notes}"</p>
                    )}

                    {/* ADR-049: Show source snapshots badge */}
                    {version.source_snapshots && version.source_snapshots.length > 0 && (
                      <div className="mt-1.5">
                        <SourceSnapshotsBadge snapshots={version.source_snapshots} />
                      </div>
                    )}

                    {hasContent && (
                      <div className="flex items-center gap-1 mt-1.5 text-xs text-muted-foreground">
                        <Eye className="w-3 h-3" />
                        <span>View output</span>
                        <ChevronRight className="w-3 h-3" />
                      </div>
                    )}
                  </button>
                );
              })
            )}
          </div>
          {versions.length > 10 && (
            <div className="px-4 py-2 text-center border-t border-border">
              <span className="text-xs text-muted-foreground">Showing 10 of {versions.length} versions</span>
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={handleSettingsSaved}
        onArchived={() => router.push('/deliverables')}
      />
    </div>
  );
}
