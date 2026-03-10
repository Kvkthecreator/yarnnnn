'use client';

/**
 * Version display components for the Deliverable Workspace page.
 *
 * Extracted from deliverables/[id]/page.tsx for maintainability.
 * Includes: InlineVersionCard, VersionsPanel, VersionPreview, SourcePills, helpers
 */

import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  Play,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  FileText,
  ExternalLink,
  Copy,
  Clock,
  Database,
  MessageSquare,
  Send,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { Deliverable, DeliverableVersion, SourceSnapshot } from '@/types';

// =============================================================================
// Helpers
// =============================================================================

const PLATFORM_EMOJI: Record<string, string> = {
  slack: '\u{1F4AC}',
  gmail: '\u{1F4E7}',
  email: '\u{1F4E7}',
  notion: '\u{1F4DD}',
  calendar: '\u{1F4C5}',
  synthesis: '\u{1F4CA}',
};

export function getStatusBadge(version: DeliverableVersion) {
  const status = version.delivery_status || version.status;
  if (status === 'delivered') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
        <CheckCircle2 className="w-3 h-3" />
        Delivered
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-2 py-0.5 rounded-full">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    );
  }
  if (status === 'generating') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
        <Loader2 className="w-3 h-3 animate-spin" />
        Generating
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">{status}</span>;
}

export function getVersionTimestamp(version: DeliverableVersion): string {
  const ts = version.delivered_at || version.created_at;
  return format(new Date(ts), 'MMM d, h:mm a');
}

export function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function SourcePills({ snapshots }: { snapshots: SourceSnapshot[] }) {
  if (!snapshots || snapshots.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Database className="w-3 h-3" />
      {snapshots.map((s, i) => (
        <span key={i} className="inline-flex items-center gap-0.5">
          {i > 0 && <span className="text-border">&middot;</span>}
          <span>{PLATFORM_EMOJI[s.platform] || '\u{1F4C4}'}</span>
          <span>{s.resource_name || s.resource_id}</span>
          {(s.items_used != null || s.item_count != null) && (
            <span className="text-muted-foreground/60">({s.items_used ?? s.item_count})</span>
          )}
        </span>
      ))}
    </span>
  );
}

// =============================================================================
// VersionsPanel (drawer tab)
// =============================================================================

export function VersionsPanel({
  versions,
  selectedIdx,
  onSelect,
}: {
  versions: DeliverableVersion[];
  selectedIdx: number;
  onSelect: (idx: number) => void;
}) {
  if (versions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <FileText className="w-8 h-8 text-muted-foreground/30 mb-3" />
        <p className="text-sm text-muted-foreground">No deliveries yet</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {versions.slice(0, 10).map((version, idx) => (
        <button
          key={version.id}
          onClick={() => onSelect(idx)}
          className={cn(
            'w-full px-3 py-2.5 flex items-center justify-between hover:bg-muted/50 transition-colors text-left',
            idx === selectedIdx && 'bg-primary/5 border-l-2 border-l-primary'
          )}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs text-muted-foreground shrink-0">v{version.version_number}</span>
            <span className="text-xs truncate">{getVersionTimestamp(version)}</span>
            {getStatusBadge(version)}
          </div>
          {version.delivery_external_url && (
            <a
              href={version.delivery_external_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1 hover:bg-muted rounded transition-colors text-primary shrink-0"
              title="View in destination"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </button>
      ))}
      {versions.length > 10 && (
        <div className="px-3 py-2 text-center">
          <span className="text-xs text-muted-foreground">Showing 10 of {versions.length}</span>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// VersionPreview (drawer version content)
// =============================================================================

export function VersionPreview({ version }: { version: DeliverableVersion }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const content = version.final_content || version.draft_content || '';

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!content && version.status !== 'generating') return null;

  return (
    <div className="border-b border-border">
      {version.status === 'generating' ? (
        <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          Generating content...
        </div>
      ) : (version.status === 'failed' || version.delivery_status === 'failed') ? (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 flex items-center gap-2">
          <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-xs text-red-700 dark:text-red-400">
            {version.delivery_error || 'Delivery failed'}
          </span>
        </div>
      ) : (
        <>
          <div
            className={cn(
              'px-3 py-3 prose prose-sm dark:prose-invert max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0',
              !expanded && 'max-h-48 overflow-hidden relative'
            )}
          >
            {!expanded && (
              <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
            )}
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
          <div className="px-3 py-1.5 border-t border-border flex items-center gap-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded ? 'Collapse' : 'Expand'}
            </button>
            <span className="text-border text-xs">&middot;</span>
            <button
              onClick={handleCopy}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
            >
              {copied ? <CheckCircle2 className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            {content && (
              <>
                <span className="text-border text-xs">&middot;</span>
                <span className="text-xs text-muted-foreground">{wordCount(content).toLocaleString()} words</span>
              </>
            )}
            {version.metadata && (version.metadata.input_tokens || version.metadata.output_tokens) && (
              <>
                <span className="text-border text-xs">&middot;</span>
                <span className="text-xs text-muted-foreground" title={`${(version.metadata.input_tokens || 0).toLocaleString()} in / ${(version.metadata.output_tokens || 0).toLocaleString()} out`}>
                  {formatTokens((version.metadata.input_tokens || 0) + (version.metadata.output_tokens || 0))} tokens
                </span>
              </>
            )}
            {version.source_snapshots && version.source_snapshots.length > 0 && (
              <>
                <span className="text-border text-xs">&middot;</span>
                <SourcePills snapshots={version.source_snapshots} />
              </>
            )}
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                <Clock className="w-3 h-3 inline mr-0.5" />
                {getVersionTimestamp(version)}
              </span>
              {getStatusBadge(version)}
              {version.delivery_external_url && (
                <a
                  href={version.delivery_external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  View
                </a>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// =============================================================================
// VersionFeedbackStrip — lightweight feedback on delivered versions
// =============================================================================

function VersionFeedbackStrip({
  deliverableId,
  version,
}: {
  deliverableId: string;
  version: DeliverableVersion;
}) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState(version.feedback_notes || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(!!version.feedback_notes);

  const handleSubmit = useCallback(async () => {
    const trimmed = note.trim();
    if (!trimmed || saving) return;
    setSaving(true);
    try {
      await api.deliverables.updateVersion(deliverableId, version.id, {
        feedback_notes: trimmed,
      });
      setSaved(true);
      setOpen(false);
    } catch {
      // Silently fail — user can retry
    } finally {
      setSaving(false);
    }
  }, [note, saving, deliverableId, version.id]);

  // Only show for delivered/approved versions with content
  const hasContent = !!(version.final_content || version.draft_content);
  const isDelivered = version.delivery_status === 'delivered' || version.status === 'approved';
  if (!hasContent || !isDelivered) return null;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full px-3 py-1.5 border-t border-border text-xs text-muted-foreground hover:text-foreground transition-colors text-left flex items-center gap-1.5"
      >
        <MessageSquare className="w-3 h-3" />
        {saved ? 'Feedback saved' : 'Leave feedback for future versions'}
      </button>
    );
  }

  return (
    <div className="border-t border-border px-3 py-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="e.g. &quot;Less about competitors, more customer signals&quot;"
          className="flex-1 text-xs bg-transparent border border-border rounded px-2 py-1 placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          autoFocus
        />
        <button
          onClick={handleSubmit}
          disabled={!note.trim() || saving}
          className="p-1 text-primary hover:text-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Save feedback"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="p-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          <XCircle className="w-3.5 h-3.5" />
        </button>
      </div>
      <p className="text-[10px] text-muted-foreground mt-1">
        This shapes future autonomous runs — the agent learns from your feedback.
      </p>
    </div>
  );
}

// =============================================================================
// InlineVersionCard (shown above chat messages, full chat width)
// =============================================================================

export function InlineVersionCard({
  versions,
  selectedIdx,
  onSelectIdx,
  deliverable,
  onRunNow,
  running,
}: {
  versions: DeliverableVersion[];
  selectedIdx: number;
  onSelectIdx: (idx: number) => void;
  deliverable: Deliverable;
  onRunNow: () => void;
  running: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showOlderVersions, setShowOlderVersions] = useState(false);
  const [copied, setCopied] = useState(false);

  const isGoalMode = deliverable.mode === 'goal';
  const isPlatformBound = deliverable.type_classification?.binding === 'platform_bound';
  const hasSources = (deliverable.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;
  const selectedVersion = versions[selectedIdx] || null;
  const content = selectedVersion?.final_content || selectedVersion?.draft_content || '';
  const olderVersions = versions.slice(1);

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (versions.length === 0) return null;

  const scheduleText = deliverable.mode !== 'recurring'
    ? `${deliverable.mode} mode`
    : deliverable.next_run_at
      ? `Next: ${format(new Date(deliverable.next_run_at), 'EEE, MMM d')}`
      : 'No scheduled runs';

  return (
    <div className="max-w-3xl mx-auto w-full mb-4">
      <div className="border border-border rounded-lg bg-muted/20">
        {/* Single compact summary line: version info + schedule + actions */}
        <div className="px-3 py-1.5 flex items-center gap-2 text-sm">
          <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          {selectedVersion && (
            <>
              <span className="text-xs font-medium">v{selectedVersion.version_number}</span>
              <span className="text-border text-xs">&middot;</span>
              {getStatusBadge(selectedVersion)}
              <span className="text-border text-xs">&middot;</span>
              <span className="text-xs text-muted-foreground">{getVersionTimestamp(selectedVersion)}</span>
              {selectedVersion.metadata && (selectedVersion.metadata.input_tokens || selectedVersion.metadata.output_tokens) && (
                <>
                  <span className="text-border text-xs hidden sm:inline">&middot;</span>
                  <span className="text-xs text-muted-foreground hidden sm:inline" title={`${(selectedVersion.metadata.input_tokens || 0).toLocaleString()} in / ${(selectedVersion.metadata.output_tokens || 0).toLocaleString()} out`}>
                    {formatTokens((selectedVersion.metadata.input_tokens || 0) + (selectedVersion.metadata.output_tokens || 0))} tok
                  </span>
                </>
              )}
            </>
          )}
          <span className="text-border text-xs hidden sm:inline">&middot;</span>
          <span className="text-xs text-muted-foreground hidden sm:inline">{scheduleText}</span>

          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={onRunNow}
              disabled={running || deliverable.status === 'archived' || missingSourcesWarning}
              title={missingSourcesWarning ? 'Add sources in Settings before running' : (isGoalMode ? 'Generate' : 'Run Now')}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              <span className="hidden sm:inline">{isGoalMode ? 'Generate' : 'Run Now'}</span>
            </button>
            {content && (
              <button
                onClick={handleCopy}
                className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={copied ? 'Copied!' : 'Copy content'}
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
            {selectedVersion?.delivery_external_url && (
              <a
                href={selectedVersion.delivery_external_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
                title="View in destination"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
            {content && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={expanded ? 'Collapse' : 'Expand preview'}
              >
                <ChevronLeft className={cn('w-3.5 h-3.5 transition-transform', expanded ? 'rotate-90' : '-rotate-90')} />
              </button>
            )}
          </div>
        </div>

        {/* Expanded content */}
        {expanded && content && (
          <div className="border-t border-border">
            {(selectedVersion?.status === 'generating') ? (
              <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                Generating content...
              </div>
            ) : (selectedVersion?.status === 'failed' || selectedVersion?.delivery_status === 'failed') ? (
              <div className="p-3 flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0" />
                <span className="text-xs text-red-700 dark:text-red-400">
                  {selectedVersion?.delivery_error || 'Delivery failed'}
                </span>
              </div>
            ) : (
              <div className="px-4 py-3 prose prose-sm dark:prose-invert max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0 max-h-96 overflow-y-auto">
                <ReactMarkdown>{content}</ReactMarkdown>
              </div>
            )}
            {selectedVersion?.source_snapshots && selectedVersion.source_snapshots.length > 0 && (
              <div className="px-3 py-1.5 border-t border-border">
                <SourcePills snapshots={selectedVersion.source_snapshots} />
              </div>
            )}
          </div>
        )}

        {/* Feedback strip for delivered versions */}
        {selectedVersion && (
          <VersionFeedbackStrip deliverableId={deliverable.id} version={selectedVersion} />
        )}

        {missingSourcesWarning && (
          <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border-t border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-1.5 rounded-b-lg">
            <span className="shrink-0">&#9888;</span>
            No sources configured — open Settings to select platform content.
          </div>
        )}

        {/* Older versions toggle */}
        {olderVersions.length > 0 && (
          <>
            <button
              onClick={() => setShowOlderVersions(!showOlderVersions)}
              className="w-full px-3 py-1.5 border-t border-border text-xs text-muted-foreground hover:text-foreground transition-colors text-left"
            >
              {showOlderVersions ? 'Hide' : `${olderVersions.length} older version${olderVersions.length !== 1 ? 's' : ''}`}
              <ChevronLeft className={cn('w-3 h-3 inline ml-1 transition-transform', showOlderVersions ? 'rotate-90' : '-rotate-90')} />
            </button>
            {showOlderVersions && (
              <div className="border-t border-border divide-y divide-border">
                {olderVersions.slice(0, 9).map((version, idx) => (
                  <button
                    key={version.id}
                    onClick={() => onSelectIdx(idx + 1)}
                    className={cn(
                      'w-full px-3 py-2 flex items-center justify-between hover:bg-muted/50 transition-colors text-left',
                      idx + 1 === selectedIdx && 'bg-primary/5 border-l-2 border-l-primary'
                    )}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs text-muted-foreground shrink-0">v{version.version_number}</span>
                      <span className="text-xs truncate">{getVersionTimestamp(version)}</span>
                      {getStatusBadge(version)}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
