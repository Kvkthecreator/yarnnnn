'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DeliverableReviewSurface - Review and edit a staged deliverable version
 *
 * Simplified: Content editor + approve/discard actions
 * Refinements handled via TP chat
 */

import { useState, useEffect } from 'react';
import {
  Check,
  XCircle,
  Loader2,
  Copy,
  CheckCircle2,
  ChevronRight,
  ArrowLeft,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { cacheEntity } from '@/lib/entity-cache';
import { ExportActionBar } from '@/components/desk/ExportActionBar';
import { DraftStatusIndicator } from '@/components/ui/DraftStatusIndicator';
import type { DeliverableVersion, Deliverable } from '@/types';

interface DeliverableReviewSurfaceProps {
  deliverableId: string;
  versionId: string;
}

export function DeliverableReviewSurface({
  deliverableId,
  versionId,
}: DeliverableReviewSurfaceProps) {
  const { attention, nextAttention, removeAttention, clearSurface, setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [version, setVersion] = useState<DeliverableVersion | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [copied, setCopied] = useState(false);
  const [approvalResult, setApprovalResult] = useState<'approved' | 'discarded' | null>(null);

  // Load version data
  useEffect(() => {
    loadVersion();
  }, [deliverableId, versionId]);

  const loadVersion = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);

      // Cache the deliverable name for TPBar display
      if (detail.deliverable?.title) {
        cacheEntity(deliverableId, detail.deliverable.title, 'deliverable');
      }

      const targetVersion = detail.versions.find((v) => v.id === versionId);
      if (targetVersion) {
        setVersion(targetVersion);
        setEditedContent(targetVersion.draft_content || '');
      }
    } catch (err) {
      console.error('Failed to load version:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle approval
  const handleApprove = async () => {
    if (!version) return;

    setSaving(true);
    try {
      const hasEdits = editedContent !== version.draft_content;
      await api.deliverables.updateVersion(deliverableId, version.id, {
        status: 'approved',
        final_content: hasEdits ? editedContent : undefined,
        feedback_notes: feedbackNotes || undefined,
      });

      // Show approval feedback briefly, then navigate
      setApprovalResult('approved');

      // Remove from attention queue AFTER API success
      removeAttention(versionId);

      // Brief delay to show feedback, then navigate
      setTimeout(() => {
        if (attention.length > 1) {
          nextAttention();
        } else {
          clearSurface();
        }
      }, 1500);
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
      setSaving(false);
    }
  };

  // Handle discard
  const handleDiscard = async () => {
    if (!version) return;

    if (!feedbackNotes.trim()) {
      alert("Please add a note explaining why you're discarding this version.");
      return;
    }

    setSaving(true);
    try {
      await api.deliverables.updateVersion(deliverableId, version.id, {
        status: 'rejected',
        feedback_notes: feedbackNotes,
      });

      // Show discard feedback briefly, then navigate
      setApprovalResult('discarded');

      // Remove from attention queue AFTER API success
      removeAttention(versionId);

      // Brief delay to show feedback, then navigate
      setTimeout(() => {
        if (attention.length > 1) {
          nextAttention();
        } else {
          clearSurface();
        }
      }, 1500);
    } catch (err) {
      console.error('Failed to discard:', err);
      alert('Failed to discard. Please try again.');
      setSaving(false);
    }
  };

  // Navigate back to deliverable detail
  const handleBack = () => {
    setSurface({ type: 'deliverable-detail', deliverableId });
  };

  // Handle skip (go to next without action)
  const handleSkip = () => {
    if (attention.length > 1) {
      nextAttention();
    }
  };

  // Handle copy
  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasEdits = version && editedContent !== version.draft_content;
  const hasNext = attention.length > 1;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!version || !deliverable) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Version not found
      </div>
    );
  }

  // Show approval/discard result feedback
  if (approvalResult) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full mb-4 ${
            approvalResult === 'approved' ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'
          }`}>
            {approvalResult === 'approved' ? (
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            ) : (
              <XCircle className="w-6 h-6 text-red-600" />
            )}
          </div>
          <h2 className="text-lg font-medium mb-1">
            {approvalResult === 'approved' ? 'Approved' : 'Discarded'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {approvalResult === 'approved'
              ? `${deliverable.title} v${version.version_number} is ready`
              : `${deliverable.title} v${version.version_number} was discarded`}
          </p>

          {/* ADR-032: Show draft status after approval */}
          {approvalResult === 'approved' && version && deliverable.destination && (
            <div className="mt-4 w-full max-w-sm">
              <DraftStatusIndicator
                version={version}
                destination={deliverable.destination}
              />
            </div>
          )}

          {/* Export option for approved versions (fallback if no destination) */}
          {approvalResult === 'approved' && version && !deliverable.destination && (
            <div className="mt-4">
              <ExportActionBar
                deliverableVersionId={version.id}
                deliverableTitle={deliverable.title}
              />
            </div>
          )}

          {attention.length > 1 && (
            <p className="text-xs text-muted-foreground mt-2">
              Moving to next item...
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Inline header: back button + title + copy action */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              className="p-1.5 -ml-1.5 hover:bg-muted rounded-md"
              title="Back to deliverable"
            >
              <ArrowLeft className="w-4 h-4 text-muted-foreground" />
            </button>
            <div>
              <h1 className="text-lg font-medium">{deliverable.title}</h1>
              <p className="text-sm text-muted-foreground">
                Review draft v{version.version_number}
                {hasEdits && <span className="text-amber-600 ml-2">• Edited</span>}
              </p>
            </div>
          </div>
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            {copied ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>

        {/* Content editor */}
        <textarea
          value={editedContent}
          onChange={(e) => setEditedContent(e.target.value)}
          className="w-full min-h-[400px] px-4 py-4 border border-border rounded-lg bg-background text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y"
          placeholder="Draft content..."
        />

        {/* Feedback notes */}
        <div className="mt-4">
          <label className="block text-sm text-muted-foreground mb-2">
            Notes (required for discard)
          </label>
          <textarea
            value={feedbackNotes}
            onChange={(e) => setFeedbackNotes(e.target.value)}
            placeholder="Add notes about this version..."
            rows={2}
            className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Actions */}
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={handleDiscard}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            Discard
          </button>

          <div className="flex items-center gap-3">
            {hasNext && (
              <button
                onClick={handleSkip}
                className="inline-flex items-center gap-1 px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Skip
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={handleApprove}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {saving ? 'Saving...' : 'Approve'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
