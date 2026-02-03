'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DeliverableReviewSurface - Review and edit a staged deliverable version
 */

import { useState, useEffect, useRef } from 'react';
import {
  Check,
  XCircle,
  Loader2,
  Copy,
  Download,
  Mail,
  CheckCircle2,
  Undo2,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { useContentRefinement } from '@/hooks/useContentRefinement';
import type { DeliverableVersion, Deliverable } from '@/types';

interface DeliverableReviewSurfaceProps {
  deliverableId: string;
  versionId: string;
}

export function DeliverableReviewSurface({
  deliverableId,
  versionId,
}: DeliverableReviewSurfaceProps) {
  const { attention, nextAttention, removeAttention, clearSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [version, setVersion] = useState<DeliverableVersion | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [copied, setCopied] = useState(false);
  const [contentHistory, setContentHistory] = useState<string[]>([]);
  const [lastAppliedLabel, setLastAppliedLabel] = useState<string | null>(null);

  const { refineContent, isRefining, error: refinementError } = useContentRefinement({
    deliverableId,
    deliverableTitle: deliverable?.title,
    deliverableType: deliverable?.deliverable_type,
  });

  // Load version data
  useEffect(() => {
    loadVersion();
  }, [deliverableId, versionId]);

  const loadVersion = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);

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

      // Remove from attention queue
      removeAttention(versionId);

      // Go to next or idle
      if (attention.length > 1) {
        nextAttention();
      } else {
        clearSurface();
      }
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
    } finally {
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

      removeAttention(versionId);

      if (attention.length > 1) {
        nextAttention();
      } else {
        clearSurface();
      }
    } catch (err) {
      console.error('Failed to discard:', err);
      alert('Failed to discard. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Handle skip (go to next without action)
  const handleSkip = () => {
    if (attention.length > 1) {
      // Move current to end of queue
      nextAttention();
    }
  };

  // Handle copy
  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Handle undo
  const handleUndo = () => {
    if (contentHistory.length === 0) return;
    const previousContent = contentHistory[contentHistory.length - 1];
    setEditedContent(previousContent);
    setContentHistory((prev) => prev.slice(0, -1));
    setLastAppliedLabel(null);
  };

  const hasEdits = version && editedContent !== version.draft_content;
  const canUndo = contentHistory.length > 0;
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div>
          <h1 className="font-medium">{deliverable.title}</h1>
          <p className="text-xs text-muted-foreground">Review draft v{version.version_number}</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Next indicator */}
          {hasNext && (
            <button
              onClick={handleSkip}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Export actions */}
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
          <button className="p-1.5 border border-border rounded-md hover:bg-muted">
            <Download className="w-3.5 h-3.5" />
          </button>
          <button className="p-1.5 border border-border rounded-md hover:bg-muted">
            <Mail className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          {/* Status messages */}
          {isRefining && (
            <div className="mb-4 px-3 py-2 bg-primary/10 border border-primary/20 rounded-md text-sm text-primary flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Refining content...
            </div>
          )}

          {lastAppliedLabel && !isRefining && (
            <div className="mb-4 px-3 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md text-sm flex items-center justify-between">
              <span>Applied: {lastAppliedLabel}</span>
              <button
                onClick={handleUndo}
                className="inline-flex items-center gap-1 text-xs hover:underline"
              >
                <Undo2 className="w-3.5 h-3.5" />
                Undo
              </button>
            </div>
          )}

          {hasEdits && !lastAppliedLabel && (
            <div className="mb-4 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm">
              You&apos;ve made edits. Your changes help improve future outputs.
            </div>
          )}

          {refinementError && (
            <div className="mb-4 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-800 dark:text-red-200">
              {refinementError}
            </div>
          )}

          {/* Refinement buttons */}
          <div className="mb-3 flex gap-2 flex-wrap">
            {[
              { label: 'Shorter', instruction: 'Make this more concise' },
              { label: 'More detail', instruction: 'Add more detail to this' },
              { label: 'More formal', instruction: 'Make the tone more formal' },
              { label: 'Simpler', instruction: 'Use simpler language' },
            ].map(({ label, instruction }) => (
              <button
                key={label}
                onClick={async () => {
                  setContentHistory((prev) => [...prev, editedContent]);
                  const refined = await refineContent(editedContent, instruction);
                  if (refined) {
                    setEditedContent(refined);
                    setLastAppliedLabel(label);
                  }
                }}
                disabled={isRefining || !editedContent.trim()}
                className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted hover:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {label}
              </button>
            ))}
          </div>

          {/* Editor */}
          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            disabled={isRefining}
            className="w-full min-h-[350px] px-4 py-4 border border-border rounded-lg bg-background text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y disabled:opacity-50"
            placeholder="Draft content..."
          />

          {/* Feedback notes */}
          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">Notes (required for discard)</label>
            <textarea
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              placeholder="Add notes about this version..."
              rows={2}
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {/* Undo helper */}
          {canUndo && !isRefining && (
            <div className="mt-3">
              <button
                onClick={handleUndo}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <Undo2 className="w-3.5 h-3.5" />
                Undo last change
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="shrink-0 h-16 border-t border-border flex items-center justify-between px-4">
        <button
          onClick={handleDiscard}
          disabled={saving || isRefining}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md disabled:opacity-50"
        >
          <XCircle className="w-4 h-4" />
          Discard
        </button>

        <div className="flex items-center gap-3">
          {hasNext && (
            <button
              onClick={handleSkip}
              disabled={isRefining}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              Skip
            </button>
          )}
          <button
            onClick={handleApprove}
            disabled={saving || isRefining}
            className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            {saving ? 'Saving...' : 'Mark as Done'}
          </button>
        </div>
      </div>
    </div>
  );
}
