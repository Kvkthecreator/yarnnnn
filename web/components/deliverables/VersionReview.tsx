'use client';

/**
 * ADR-018: Version Review
 *
 * Interface for reviewing a staged deliverable version.
 * Allows editing, approving, rejecting, or providing feedback.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Check,
  XCircle,
  MessageSquare,
  Loader2,
  Copy,
  Download,
  ArrowLeft,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { DeliverableVersion, Deliverable } from '@/types';

interface VersionReviewProps {
  deliverableId: string;
  versionId?: string; // If not provided, loads the latest staged version
  onClose: () => void;
  onApproved: () => void;
}

export function VersionReview({
  deliverableId,
  versionId,
  onClose,
  onApproved,
}: VersionReviewProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [version, setVersion] = useState<DeliverableVersion | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadVersion();
  }, [deliverableId, versionId]);

  const loadVersion = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);

      // Find the version to review
      let targetVersion: DeliverableVersion | undefined;
      if (versionId) {
        targetVersion = detail.versions.find(v => v.id === versionId);
      } else {
        // Get the latest staged version
        targetVersion = detail.versions.find(v => v.status === 'staged');
      }

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

      onApproved();
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!version || !feedbackNotes.trim()) {
      setShowFeedback(true);
      return;
    }

    setSaving(true);
    try {
      await api.deliverables.updateVersion(deliverableId, version.id, {
        status: 'rejected',
        feedback_notes: feedbackNotes,
      });

      onClose();
    } catch (err) {
      console.error('Failed to reject:', err);
      alert('Failed to reject. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-background z-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!version || !deliverable) {
    return (
      <div className="fixed inset-0 bg-background z-50 flex flex-col items-center justify-center">
        <p className="text-muted-foreground mb-4">No staged version found</p>
        <button
          onClick={onClose}
          className="text-sm text-primary hover:underline"
        >
          Go back
        </button>
      </div>
    );
  }

  const hasEdits = editedContent !== version.draft_content;

  return (
    <div className="fixed inset-0 bg-background z-50 flex flex-col">
      {/* Header */}
      <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={onClose}
            className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-medium">{deliverable.title}</h1>
            <p className="text-xs text-muted-foreground">
              Version {version.version_number} · Review draft
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="container mx-auto max-w-4xl px-4 py-6">
          {/* Edit indicator */}
          {hasEdits && (
            <div className="mb-4 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm text-amber-800 dark:text-amber-200">
              You have unsaved edits. These will be captured as feedback when you approve.
            </div>
          )}

          {/* Editor */}
          <div className="mb-6">
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="w-full min-h-[400px] px-4 py-4 border border-border rounded-lg bg-background text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y"
              placeholder="Draft content..."
            />
          </div>

          {/* Feedback section */}
          <div className="mb-6">
            <button
              onClick={() => setShowFeedback(!showFeedback)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
            >
              <MessageSquare className="w-4 h-4" />
              {showFeedback ? 'Hide feedback' : 'Add feedback for next time'}
            </button>

            {showFeedback && (
              <div className="mt-3">
                <textarea
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="e.g., Include Q1 comparison numbers, keep the budget section shorter..."
                  rows={3}
                  className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  This feedback will help improve future versions.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="h-16 border-t border-border bg-background flex items-center justify-between px-4 shrink-0">
        <button
          onClick={handleReject}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
        >
          <XCircle className="w-4 h-4" />
          Reject
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Approve{hasEdits ? ' with edits' : ''}
              </>
            )}
          </button>
        </div>
      </footer>
    </div>
  );
}
