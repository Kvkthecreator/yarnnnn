'use client';

/**
 * ADR-018: Version Review
 *
 * Interface for reviewing a staged deliverable version.
 * - Edit content inline
 * - Simple thumbs up/down feedback
 * - Approve (mark as sent) or discard
 * - No recipient delivery - user controls sending manually
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Check,
  XCircle,
  Loader2,
  Copy,
  Download,
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  Mail,
  CheckCircle2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useFloatingChat } from '@/contexts/FloatingChatContext';
import { MessageSquare } from 'lucide-react';
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
  const [feedback, setFeedback] = useState<'good' | 'needs_work' | null>(null);
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [copied, setCopied] = useState(false);

  // ADR-020: Set floating chat context and enable TP-powered refinements
  const { setPageContext, open: openChat, openWithPrompt } = useFloatingChat();

  useEffect(() => {
    loadVersion();
  }, [deliverableId, versionId]);

  // ADR-020: Update floating chat context when reviewing
  useEffect(() => {
    if (deliverable && version) {
      setPageContext({
        type: 'deliverable-review',
        deliverable,
        deliverableId,
        currentVersion: version,
      });
    }

    // Cleanup: reset to global when unmounting
    return () => {
      setPageContext({ type: 'global' });
    };
  }, [deliverable, version, deliverableId, setPageContext]);

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

      // Build feedback notes with thumbs rating
      let notes = feedbackNotes;
      if (feedback === 'good' && !notes) {
        notes = 'Approved as-is - good quality';
      } else if (feedback === 'needs_work' && !notes) {
        notes = 'Approved with edits - needs improvement';
      }

      await api.deliverables.updateVersion(deliverableId, version.id, {
        status: 'approved',
        final_content: hasEdits ? editedContent : undefined,
        feedback_notes: notes || undefined,
      });

      onApproved();
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = async () => {
    if (!version) return;

    if (!feedbackNotes.trim()) {
      alert('Please add a note explaining why you\'re discarding this version.');
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
      console.error('Failed to discard:', err);
      alert('Failed to discard. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([editedContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${deliverable?.title || 'deliverable'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleEmailToSelf = () => {
    const subject = encodeURIComponent(deliverable?.title || 'Deliverable');
    const body = encodeURIComponent(editedContent);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  // Format version period
  const formatVersionPeriod = () => {
    if (!version || !deliverable) return '';
    const date = new Date(version.created_at);
    const { frequency } = deliverable.schedule;

    if (frequency === 'weekly') {
      const startOfWeek = new Date(date);
      startOfWeek.setDate(date.getDate() - date.getDay());
      return `Week of ${startOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
    }
    if (frequency === 'monthly') {
      return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    }
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
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
              {formatVersionPeriod()} · Review draft
            </p>
          </div>
        </div>

        {/* Export options */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
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
      </header>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="container mx-auto max-w-4xl px-4 py-6">
          {/* Edit indicator */}
          {hasEdits && (
            <div className="mb-4 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm text-amber-800 dark:text-amber-200">
              You've made edits. Your changes help improve future outputs.
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

          {/* Quick feedback - TP-powered refinements */}
          <div className="mb-6 p-4 border border-border rounded-lg">
            <p className="text-sm font-medium mb-3">How was this draft?</p>
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <button
                onClick={() => setFeedback(feedback === 'good' ? null : 'good')}
                className={cn(
                  "inline-flex items-center gap-2 px-4 py-2 text-sm rounded-md border transition-colors",
                  feedback === 'good'
                    ? "border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300"
                    : "border-border hover:bg-muted"
                )}
              >
                <ThumbsUp className="w-4 h-4" />
                Good
              </button>
              <button
                onClick={() => setFeedback(feedback === 'needs_work' ? null : 'needs_work')}
                className={cn(
                  "inline-flex items-center gap-2 px-4 py-2 text-sm rounded-md border transition-colors",
                  feedback === 'needs_work'
                    ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300"
                    : "border-border hover:bg-muted"
                )}
              >
                <ThumbsDown className="w-4 h-4" />
                Needs work
              </button>
            </div>

            {/* Quick refinement actions - opens chat with prompt */}
            {feedback === 'needs_work' && (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">Quick refinements:</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => openWithPrompt("Make this draft more concise - cut it down to the key points while keeping the essential information.")}
                    className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    Make it shorter
                  </button>
                  <button
                    onClick={() => openWithPrompt("Add more detail and specifics to this draft. Include concrete examples where appropriate.")}
                    className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    More detail
                  </button>
                  <button
                    onClick={() => openWithPrompt("Adjust the tone of this draft to be more professional and formal.")}
                    className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    More formal
                  </button>
                  <button
                    onClick={() => openWithPrompt("Adjust the tone of this draft to be more casual and conversational.")}
                    className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
                  >
                    More casual
                  </button>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <button
                    onClick={() => openChat()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-primary hover:underline"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Tell me what to change...
                  </button>
                </div>

                <textarea
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Or add a note for the record (e.g., Include Q1 numbers next time)"
                  rows={2}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="text-xs text-muted-foreground">
                  Notes are saved with your feedback to improve future outputs.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="h-16 border-t border-border bg-background flex items-center justify-between px-4 shrink-0">
        <button
          onClick={handleDiscard}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
        >
          <XCircle className="w-4 h-4" />
          Discard
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
                Mark as Done
              </>
            )}
          </button>
        </div>
      </footer>
    </div>
  );
}
