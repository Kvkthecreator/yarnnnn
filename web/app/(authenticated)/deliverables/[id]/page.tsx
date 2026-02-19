'use client';

/**
 * ADR-066: Deliverable Detail Page — Output-First with Inline Review
 *
 * Shows the latest generated output with inline approve/reject actions.
 * Configuration lives in settings modal; this page is for reviewing work.
 *
 * Replaces the previous metadata-heavy page and merges in the review functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  Loader2,
  Play,
  Pause,
  Settings,
  Clock,
  Check,
  X,
  Copy,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Mail,
  FileText,
  Download,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import { SourceSnapshotsSummary } from '@/components/deliverables/SourceSnapshotsSummary';
import type { Deliverable, DeliverableVersion } from '@/types';

// =============================================================================
// Platform Config
// =============================================================================

const PLATFORM_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  gmail: Mail,
  slack: MessageSquare,
  notion: FileText,
  download: Download,
};

const PLATFORM_LABELS: Record<string, string> = {
  gmail: 'Gmail',
  slack: 'Slack',
  notion: 'Notion',
  download: 'Download',
};

// =============================================================================
// Main Component
// =============================================================================

export default function DeliverableDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data state
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Review state
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);

  // Version history state
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);

  // Load deliverable data
  const loadDeliverable = useCallback(async () => {
    try {
      const detail = await api.deliverables.get(id);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);

      // Initialize editor with latest pending version
      const latestPending = detail.versions.find(
        (v) => v.status === 'staged' || v.status === 'reviewing' || v.status === 'draft'
      );
      if (latestPending) {
        setEditedContent(latestPending.draft_content || latestPending.final_content || '');
      }
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDeliverable();
  }, [loadDeliverable]);

  // Get the latest version that needs review (staged/reviewing/draft)
  const latestVersion = versions[0];
  const pendingVersion = versions.find(
    (v) => v.status === 'staged' || v.status === 'reviewing' || v.status === 'draft'
  );
  const hasPendingReview = !!pendingVersion;

  // =============================================================================
  // Actions
  // =============================================================================

  const handleApprove = async () => {
    if (!pendingVersion) return;

    setSaving(true);
    try {
      const hasEdits = editedContent !== (pendingVersion.draft_content || pendingVersion.final_content);
      await api.deliverables.updateVersion(id, pendingVersion.id, {
        status: 'approved',
        final_content: hasEdits ? editedContent : undefined,
        feedback_notes: feedbackNotes || undefined,
      });

      // Reload to get updated state
      await loadDeliverable();
      setFeedbackNotes('');
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!pendingVersion) return;

    if (!feedbackNotes.trim()) {
      alert("Please add feedback explaining why you're rejecting this version.");
      return;
    }

    setSaving(true);
    try {
      await api.deliverables.updateVersion(id, pendingVersion.id, {
        status: 'rejected',
        feedback_notes: feedbackNotes,
      });

      await loadDeliverable();
      setFeedbackNotes('');
    } catch (err) {
      console.error('Failed to reject:', err);
      alert('Failed to reject. Please try again.');
    } finally {
      setSaving(false);
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

  const handleRunNow = async () => {
    if (!deliverable) return;

    setRunning(true);
    try {
      await api.deliverables.run(id);
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run deliverable:', err);
      alert('Failed to run. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  const handleCopy = async () => {
    const content = pendingVersion?.draft_content || pendingVersion?.final_content || editedContent;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSettingsSaved = (updated: Deliverable) => {
    setDeliverable(updated);
  };

  // =============================================================================
  // Helpers
  // =============================================================================

  const formatSchedule = () => {
    if (!deliverable?.schedule) return 'No schedule';
    const s = deliverable.schedule;
    const time = s.time || '09:00';
    const day = s.day
      ? s.day.charAt(0).toUpperCase() + s.day.slice(1)
      : s.frequency === 'monthly' ? '1st' : 'Monday';

    switch (s.frequency) {
      case 'daily': return `Daily at ${time}`;
      case 'weekly': return `Weekly on ${day} at ${time}`;
      case 'biweekly': return `Every 2 weeks on ${day} at ${time}`;
      case 'monthly': return `Monthly on the ${day} at ${time}`;
      default: return s.frequency || 'Custom';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" />Approved</span>;
      case 'rejected':
        return <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 dark:bg-red-900/30 px-2 py-0.5 rounded-full"><XCircle className="w-3 h-3" />Rejected</span>;
      case 'staged':
      case 'reviewing':
      case 'draft':
        return <span className="inline-flex items-center gap-1 text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/30 px-2 py-0.5 rounded-full"><Clock className="w-3 h-3" />Pending Review</span>;
      case 'generating':
        return <span className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full"><Loader2 className="w-3 h-3 animate-spin" />Generating</span>;
      default:
        return <span className="text-xs text-muted-foreground">{status}</span>;
    }
  };

  // =============================================================================
  // Render
  // =============================================================================

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
        <FileText className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Deliverable not found</p>
        <button onClick={() => router.push('/deliverables')} className="text-sm text-primary hover:underline">
          Back to Deliverables
        </button>
      </div>
    );
  }

  const DestIcon = deliverable.destination ? PLATFORM_ICONS[deliverable.destination.platform] : null;
  const destLabel = deliverable.destination ? PLATFORM_LABELS[deliverable.destination.platform] : null;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push('/deliverables')}
              className="p-2 -ml-2 hover:bg-muted rounded-lg transition-colors"
              title="Back to Deliverables"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold">{deliverable.title}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-0.5">
                <Clock className="w-3.5 h-3.5" />
                <span>{formatSchedule()}</span>
                {DestIcon && destLabel && (
                  <>
                    <span>→</span>
                    <span className="flex items-center gap-1">
                      <DestIcon className="w-3.5 h-3.5" />
                      {destLabel}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleTogglePause}
              className={cn(
                "p-2 border border-border rounded-md hover:bg-muted transition-colors",
                deliverable.status === 'paused' && "text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-900/20"
              )}
              title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
            >
              {deliverable.status === 'paused' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-2 border border-border rounded-md hover:bg-muted transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Latest Output Section */}
        {hasPendingReview && pendingVersion ? (
          <div className="border border-border rounded-lg mb-6 overflow-hidden">
            {/* Version Header */}
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-medium">Latest Output</h2>
                {getStatusBadge(pendingVersion.status)}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>v{pendingVersion.version_number}</span>
                <span>·</span>
                <span>{format(new Date(pendingVersion.created_at), 'MMM d, h:mm a')}</span>
                <button
                  onClick={handleCopy}
                  className="ml-2 p-1.5 hover:bg-muted rounded transition-colors"
                  title="Copy content"
                >
                  {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Source Snapshots */}
            {pendingVersion.source_snapshots && pendingVersion.source_snapshots.length > 0 && (
              <div className="px-4 py-3 border-b border-border bg-muted/20">
                <SourceSnapshotsSummary snapshots={pendingVersion.source_snapshots} compact />
              </div>
            )}

            {/* Content Editor */}
            <div className="p-4">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="w-full min-h-[300px] px-4 py-3 border border-border rounded-lg bg-background text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y font-mono"
                placeholder="Generated content..."
              />
            </div>

            {/* Feedback Input */}
            <div className="px-4 pb-4">
              <input
                type="text"
                value={feedbackNotes}
                onChange={(e) => setFeedbackNotes(e.target.value)}
                placeholder="Add feedback (required for reject)..."
                className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            {/* Review Actions */}
            <div className="px-4 py-3 border-t border-border bg-muted/20 flex items-center justify-between">
              <button
                onClick={handleReject}
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md disabled:opacity-50 transition-colors"
              >
                <X className="w-4 h-4" />
                Reject
              </button>
              <button
                onClick={handleApprove}
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {saving ? 'Saving...' : 'Approve'}
              </button>
            </div>
          </div>
        ) : latestVersion ? (
          /* No pending review - show last version status */
          <div className="border border-border rounded-lg mb-6 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-medium">Latest Output</h2>
                {getStatusBadge(latestVersion.status)}
              </div>
              <span className="text-xs text-muted-foreground">
                v{latestVersion.version_number} · {format(new Date(latestVersion.created_at), 'MMM d, h:mm a')}
              </span>
            </div>
            {latestVersion.final_content && (
              <p className="mt-3 text-sm text-muted-foreground line-clamp-3">
                {latestVersion.final_content.slice(0, 200)}...
              </p>
            )}
          </div>
        ) : (
          /* No versions yet */
          <div className="border border-dashed border-border rounded-lg mb-6 p-8 text-center">
            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">No output generated yet</p>
            <button
              onClick={handleRunNow}
              disabled={running || deliverable.status === 'archived'}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {running ? 'Generating...' : 'Run Now'}
            </button>
          </div>
        )}

        {/* Previous Versions */}
        {versions.length > 1 && (
          <div className="border border-border rounded-lg mb-6">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Previous Versions</h2>
            </div>
            <div className="divide-y divide-border">
              {versions.slice(1, 10).map((version) => (
                <div key={version.id}>
                  <button
                    onClick={() => setExpandedVersionId(expandedVersionId === version.id ? null : version.id)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {expandedVersionId === version.id ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="text-sm font-medium">v{version.version_number}</span>
                      {getStatusBadge(version.status)}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(version.created_at), 'MMM d, h:mm a')}
                    </span>
                  </button>
                  {expandedVersionId === version.id && (
                    <div className="px-4 pb-4 pl-11">
                      {version.source_snapshots && version.source_snapshots.length > 0 && (
                        <div className="mb-3">
                          <SourceSnapshotsSummary snapshots={version.source_snapshots} compact />
                        </div>
                      )}
                      <pre className="text-xs text-muted-foreground bg-muted/50 rounded-md p-3 overflow-auto max-h-[200px] whitespace-pre-wrap">
                        {version.final_content || version.draft_content || 'No content'}
                      </pre>
                      {version.feedback_notes && (
                        <p className="mt-2 text-xs text-muted-foreground italic">
                          Feedback: "{version.feedback_notes}"
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
            {versions.length > 10 && (
              <div className="px-4 py-2 text-center border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing 9 of {versions.length - 1} previous versions
                </span>
              </div>
            )}
          </div>
        )}

        {/* Schedule Section */}
        <div className="border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <h2 className="text-sm font-medium">Schedule</h2>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              {deliverable.next_run_at ? (
                <>
                  <p className="text-sm">
                    Next run: <span className="font-medium">{format(new Date(deliverable.next_run_at), 'EEE, MMM d')} at {format(new Date(deliverable.next_run_at), 'h:mm a')}</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No scheduled runs</p>
              )}
            </div>
            {!hasPendingReview && (
              <button
                onClick={handleRunNow}
                disabled={running || deliverable.status === 'archived'}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
              >
                {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Run Now
              </button>
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
        onArchived={() => router.push('/deliverables')}
      />
    </div>
  );
}
