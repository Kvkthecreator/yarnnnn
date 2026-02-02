'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 * ADR-018: Version Review
 * ADR-020: Inline TP-powered refinements
 *
 * Version review tab renderer - for reviewing staged deliverable versions.
 * Adapted from VersionReview.tsx but as a tab content renderer.
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
  Send,
  Undo2,
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { Tab, TabType } from '@/lib/tabs';
import { cn } from '@/lib/utils';
import { useContentRefinement } from '@/hooks/useContentRefinement';
import type { DeliverableVersion, Deliverable } from '@/types';

interface VersionReviewTabContentProps {
  tab: Tab;
  updateStatus: (status: 'idle' | 'loading' | 'error' | 'unsaved') => void;
  updateData: (data: Record<string, unknown>) => void;
  openTab: (type: TabType, title: string, resourceId?: string, data?: Record<string, unknown>) => void;
  closeTab: (tabId: string) => void;
}

// Quick refinement presets
const QUICK_REFINEMENTS = [
  { label: 'Shorter', instruction: 'Make this more concise - cut it down to the key points while keeping essential information.' },
  { label: 'More detail', instruction: 'Add more detail and specifics. Include concrete examples where appropriate.' },
  { label: 'More formal', instruction: 'Adjust the tone to be more professional and formal.' },
  { label: 'More casual', instruction: 'Adjust the tone to be more casual and conversational.' },
];

export function VersionReviewTabContent({
  tab,
  updateStatus,
  updateData,
  openTab,
  closeTab,
}: VersionReviewTabContentProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [version, setVersion] = useState<DeliverableVersion | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [copied, setCopied] = useState(false);

  // Inline refinement state
  const [customInstruction, setCustomInstruction] = useState('');
  const [contentHistory, setContentHistory] = useState<string[]>([]);
  const [lastAppliedLabel, setLastAppliedLabel] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get IDs from tab
  const deliverableId = tab.resourceId || '';
  const versionId = (tab.data?.versionId as string) || undefined;

  // Content refinement hook
  const { refineContent, isRefining, error: refinementError } = useContentRefinement({
    deliverableId: deliverableId,
    deliverableTitle: deliverable?.title,
    deliverableType: deliverable?.deliverable_type,
  });

  useEffect(() => {
    if (deliverableId) {
      loadVersion();
    }
  }, [deliverableId, versionId]);

  // Track unsaved changes
  useEffect(() => {
    if (version && editedContent !== version.draft_content) {
      updateStatus('unsaved');
    } else {
      updateStatus('idle');
    }
  }, [editedContent, version]);

  const loadVersion = async () => {
    if (!deliverableId) return;

    setLoading(true);
    updateStatus('loading');

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
        updateData({ deliverable: detail.deliverable, version: targetVersion });
      }
      updateStatus('idle');
    } catch (err) {
      console.error('Failed to load version:', err);
      updateStatus('error');
    } finally {
      setLoading(false);
    }
  };

  // Apply a refinement (quick preset or custom)
  const handleRefine = async (instruction: string, label?: string) => {
    if (!editedContent.trim() || isRefining) return;

    // Save current content for undo
    setContentHistory(prev => [...prev, editedContent]);
    setLastAppliedLabel(label || 'Custom');

    const refined = await refineContent(editedContent, instruction);
    if (refined) {
      setEditedContent(refined);
    } else {
      // Rollback if refinement failed
      setContentHistory(prev => prev.slice(0, -1));
      setLastAppliedLabel(null);
    }
  };

  // Handle custom instruction submit
  const handleCustomRefine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customInstruction.trim()) return;

    await handleRefine(customInstruction);
    setCustomInstruction('');
  };

  // Undo last refinement
  const handleUndo = () => {
    if (contentHistory.length === 0) return;

    const previousContent = contentHistory[contentHistory.length - 1];
    setEditedContent(previousContent);
    setContentHistory(prev => prev.slice(0, -1));
    setLastAppliedLabel(null);
  };

  const handleApprove = async () => {
    if (!version || !deliverableId) return;

    setSaving(true);
    try {
      const hasEdits = editedContent !== version.draft_content;

      await api.deliverables.updateVersion(deliverableId, version.id, {
        status: 'approved',
        final_content: hasEdits ? editedContent : undefined,
        feedback_notes: feedbackNotes || undefined,
      });

      // Close this tab and open the deliverable tab
      closeTab(tab.id);
      openTab('deliverable', deliverable?.title || 'Deliverable', deliverableId);
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Failed to approve. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = async () => {
    if (!version || !deliverableId) return;

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

      // Close this tab and open the deliverable tab
      closeTab(tab.id);
      openTab('deliverable', deliverable?.title || 'Deliverable', deliverableId);
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
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!version || !deliverable) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <p className="text-muted-foreground mb-4">No staged version found</p>
        <button
          onClick={() => {
            closeTab(tab.id);
            if (deliverableId) {
              openTab('deliverable', 'Deliverable', deliverableId);
            }
          }}
          className="text-sm text-primary hover:underline"
        >
          Go back to deliverable
        </button>
      </div>
    );
  }

  const hasEdits = editedContent !== version.draft_content;
  const canUndo = contentHistory.length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="shrink-0 px-6 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
        <div>
          <h1 className="font-medium">{deliverable.title}</h1>
          <p className="text-xs text-muted-foreground">{formatVersionPeriod()}</p>
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
            Email
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-3xl mx-auto px-6 py-6">
          {/* Status indicators */}
          {isRefining && (
            <div className="mb-4 px-3 py-2 bg-primary/10 border border-primary/20 rounded-md text-sm text-primary flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Refining content...
            </div>
          )}

          {lastAppliedLabel && !isRefining && (
            <div className="mb-4 px-3 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md text-sm text-green-800 dark:text-green-200 flex items-center justify-between">
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
            <div className="mb-4 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm text-amber-800 dark:text-amber-200">
              You've made edits. Your changes help improve future outputs.
            </div>
          )}

          {refinementError && (
            <div className="mb-4 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-800 dark:text-red-200">
              {refinementError}
            </div>
          )}

          {/* Editor */}
          <div className="mb-4">
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              disabled={isRefining}
              className="w-full min-h-[300px] px-4 py-4 border border-border rounded-lg bg-background text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="Draft content..."
            />
          </div>

          {/* Inline refinement controls */}
          <div className="mb-6 p-4 border border-border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Refine with AI</span>
            </div>

            {/* Quick refinement chips */}
            <div className="flex flex-wrap gap-2 mb-3">
              {QUICK_REFINEMENTS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => handleRefine(preset.instruction, preset.label)}
                  disabled={isRefining || !editedContent.trim()}
                  className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-background hover:border-primary/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {preset.label}
                </button>
              ))}
            </div>

            {/* Custom instruction input */}
            <form onSubmit={handleCustomRefine} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                disabled={isRefining}
                placeholder="Or tell me what to change..."
                className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isRefining || !customInstruction.trim()}
                className="px-3 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 transition-colors"
              >
                {isRefining ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>

            {/* Undo button when history exists */}
            {canUndo && !isRefining && (
              <div className="mt-3 pt-3 border-t border-border">
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

          {/* Feedback notes for rejection */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">
              Notes (required for discard)
            </label>
            <textarea
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              placeholder="Add notes about this version (e.g., what to improve next time)"
              rows={2}
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="shrink-0 h-14 border-t border-border bg-background flex items-center justify-between px-6">
        <button
          onClick={handleDiscard}
          disabled={saving || isRefining}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors disabled:opacity-50"
        >
          <XCircle className="w-4 h-4" />
          Discard
        </button>

        <button
          onClick={handleApprove}
          disabled={saving || isRefining}
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
    </div>
  );
}
