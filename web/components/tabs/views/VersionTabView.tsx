'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Full-page view for reviewing/editing a version.
 * This is where users refine and approve deliverable outputs.
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
  MessageSquare,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useTabs } from '@/contexts/TabContext';
import { useSurface } from '@/contexts/SurfaceContext';
import { useContentRefinement } from '@/hooks/useContentRefinement';
import type { DeliverableVersion, Deliverable } from '@/types';

interface VersionTabViewProps {
  deliverableId: string;
  versionId: string;
}

// Quick refinement presets
const QUICK_REFINEMENTS = [
  { label: 'Shorter', instruction: 'Make this more concise - cut it down to the key points.' },
  { label: 'More detail', instruction: 'Add more detail and specifics.' },
  { label: 'More formal', instruction: 'Adjust the tone to be more professional.' },
  { label: 'More casual', instruction: 'Adjust the tone to be more conversational.' },
];

export function VersionTabView({ deliverableId, versionId }: VersionTabViewProps) {
  const { updateTab, closeTab, goToChat } = useTabs();
  const { openSurface } = useSurface();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [version, setVersion] = useState<DeliverableVersion | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [copied, setCopied] = useState(false);

  // Inline refinement
  const [customInstruction, setCustomInstruction] = useState('');
  const [contentHistory, setContentHistory] = useState<string[]>([]);
  const [lastAppliedLabel, setLastAppliedLabel] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { refineContent, isRefining, error: refinementError } = useContentRefinement({
    deliverableId,
    deliverableTitle: deliverable?.title,
    deliverableType: deliverable?.deliverable_type,
  });

  useEffect(() => {
    loadVersion();
  }, [deliverableId, versionId]);

  const loadVersion = async () => {
    setLoading(true);
    try {
      const detail = await api.deliverables.get(deliverableId);
      setDeliverable(detail.deliverable);

      const targetVersion = detail.versions.find(v => v.id === versionId);
      if (targetVersion) {
        setVersion(targetVersion);
        setEditedContent(targetVersion.draft_content || '');
        // Update tab title
        updateTab(`version-${versionId}`, { title: `Review: ${detail.deliverable.title}` });
      }
    } catch (err) {
      console.error('Failed to load version:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefine = async (instruction: string, label?: string) => {
    if (!editedContent.trim() || isRefining) return;

    setContentHistory(prev => [...prev, editedContent]);
    setLastAppliedLabel(label || 'Custom');

    const refined = await refineContent(editedContent, instruction);
    if (refined) {
      setEditedContent(refined);
      // Mark tab as dirty
      updateTab(`version-${versionId}`, { isDirty: true });
    } else {
      setContentHistory(prev => prev.slice(0, -1));
      setLastAppliedLabel(null);
    }
  };

  const handleCustomRefine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customInstruction.trim()) return;
    await handleRefine(customInstruction);
    setCustomInstruction('');
  };

  const handleUndo = () => {
    if (contentHistory.length === 0) return;
    const previousContent = contentHistory[contentHistory.length - 1];
    setEditedContent(previousContent);
    setContentHistory(prev => prev.slice(0, -1));
    setLastAppliedLabel(null);
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

      // Close this tab and go back to chat
      closeTab(`version-${versionId}`);
      goToChat();
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

      closeTab(`version-${versionId}`);
      goToChat();
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

  const handleOpenTPDrawer = () => {
    openSurface('context', { deliverableId, versionId });
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
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Version not found
      </div>
    );
  }

  const hasEdits = editedContent !== version.draft_content;
  const canUndo = contentHistory.length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div>
          <h1 className="font-medium">{deliverable.title}</h1>
          <p className="text-xs text-muted-foreground">Review draft</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Ask TP */}
          <button
            onClick={handleOpenTPDrawer}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Ask TP
          </button>

          {/* Export */}
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted">
            <Download className="w-3.5 h-3.5" />
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted">
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
              <button onClick={handleUndo} className="inline-flex items-center gap-1 text-xs hover:underline">
                <Undo2 className="w-3.5 h-3.5" />
                Undo
              </button>
            </div>
          )}

          {hasEdits && !lastAppliedLabel && (
            <div className="mb-4 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md text-sm">
              You've made edits. Your changes help improve future outputs.
            </div>
          )}

          {refinementError && (
            <div className="mb-4 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-800 dark:text-red-200">
              {refinementError}
            </div>
          )}

          {/* Editor */}
          <textarea
            value={editedContent}
            onChange={(e) => {
              setEditedContent(e.target.value);
              updateTab(`version-${versionId}`, { isDirty: true });
            }}
            disabled={isRefining}
            className="w-full min-h-[350px] px-4 py-4 border border-border rounded-lg bg-background text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-y disabled:opacity-50"
            placeholder="Draft content..."
          />

          {/* Refinement controls */}
          <div className="mt-4 p-4 border border-border rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Refine with AI</span>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              {QUICK_REFINEMENTS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => handleRefine(preset.instruction, preset.label)}
                  disabled={isRefining || !editedContent.trim()}
                  className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-background hover:border-primary/50 disabled:opacity-50"
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <form onSubmit={handleCustomRefine} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                disabled={isRefining}
                placeholder="Or tell me what to change..."
                className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isRefining || !customInstruction.trim()}
                className="px-3 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
              >
                {isRefining ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>

            {canUndo && !isRefining && (
              <div className="mt-3 pt-3 border-t border-border">
                <button onClick={handleUndo} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
                  <Undo2 className="w-3.5 h-3.5" />
                  Undo last change
                </button>
              </div>
            )}
          </div>

          {/* Feedback notes */}
          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">
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
          <button
            onClick={() => closeTab(`version-${versionId}`)}
            disabled={isRefining}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={saving || isRefining}
            className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Mark as Done'}
          </button>
        </div>
      </div>
    </div>
  );
}
