'use client';

/**
 * Version display components for the Agent Workspace panel.
 *
 * VersionsPanel: lives in the right panel, two modes:
 * - List mode: compact version list, click to preview
 * - Preview mode: full markdown render of selected version, back to list
 *
 * Replaces the former InlineVersionCard (pinned above chat) with panel-based display.
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
  Database,
  MessageSquare,
  Send,
  ArrowLeft,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { Agent, AgentRun, SourceSnapshot } from '@/types';

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

export function getStatusBadge(version: AgentRun) {
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

export function getRunTimestamp(version: AgentRun): string {
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
// VersionFeedbackStrip — lightweight feedback on delivered versions
// =============================================================================

function VersionFeedbackStrip({
  agentId,
  version,
}: {
  agentId: string;
  version: AgentRun;
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
      await api.agents.updateRun(agentId, version.id, {
        feedback_notes: trimmed,
      });
      setSaved(true);
      setOpen(false);
    } catch {
      // Silently fail — user can retry
    } finally {
      setSaving(false);
    }
  }, [note, saving, agentId, version.id]);

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
// VersionPreviewFull — full-height version render for the panel
// =============================================================================

function VersionPreviewFull({
  version,
  agent,
  onBack,
  onRunNow,
  running,
}: {
  version: AgentRun;
  agent: Agent;
  onBack: () => void;
  onRunNow: () => void;
  running: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const content = version.final_content || version.draft_content || '';

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header: back + version info + actions */}
      <div className="px-3 py-2 border-b border-border flex items-center gap-2 shrink-0">
        <button
          onClick={onBack}
          className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
          title="Back to versions"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
        </button>
        <span className="text-xs font-medium">v{version.version_number}</span>
        {getStatusBadge(version)}
        <span className="text-xs text-muted-foreground">{getRunTimestamp(version)}</span>

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={onRunNow}
            disabled={running || agent.status === 'archived'}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            <span className="hidden sm:inline">{agent.mode === 'goal' ? 'Generate' : 'Run Now'}</span>
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
          {version.delivery_external_url && (
            <a
              href={version.delivery_external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
              title="View in destination"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Content: full-height scrollable markdown */}
      <div className="flex-1 overflow-y-auto">
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
        ) : content ? (
          <div className="px-4 py-3 prose prose-sm dark:prose-invert max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : null}

        {/* Meta: tokens, sources */}
        {content && (
          <div className="px-3 py-2 border-t border-border flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{wordCount(content).toLocaleString()} words</span>
            {version.metadata && (version.metadata.input_tokens || version.metadata.output_tokens) && (
              <>
                <span className="text-border">&middot;</span>
                <span title={`${(version.metadata.input_tokens || 0).toLocaleString()} in / ${(version.metadata.output_tokens || 0).toLocaleString()} out`}>
                  {formatTokens((version.metadata.input_tokens || 0) + (version.metadata.output_tokens || 0))} tokens
                </span>
              </>
            )}
            {version.source_snapshots && version.source_snapshots.length > 0 && (
              <>
                <span className="text-border">&middot;</span>
                <SourcePills snapshots={version.source_snapshots} />
              </>
            )}
          </div>
        )}

        {/* Feedback strip */}
        <VersionFeedbackStrip agentId={agent.id} version={version} />
      </div>
    </div>
  );
}

// =============================================================================
// VersionsPanel — panel tab with list + preview modes
// =============================================================================

export function VersionsPanel({
  versions,
  agent,
  onRunNow,
  running,
}: {
  versions: AgentRun[];
  agent: Agent;
  onRunNow: () => void;
  running: boolean;
}) {
  // null = list mode, number = preview mode (index into versions)
  const [previewIdx, setPreviewIdx] = useState<number | null>(
    // Auto-show latest version if it exists
    versions.length > 0 ? 0 : null
  );

  const isGoalMode = agent.mode === 'goal';
  const isPlatformBound = agent.type_classification?.binding === 'platform_bound';
  const hasSources = (agent.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;

  // Preview mode: show full version
  if (previewIdx !== null && versions[previewIdx]) {
    return (
      <VersionPreviewFull
        version={versions[previewIdx]}
        agent={agent}
        onBack={() => setPreviewIdx(null)}
        onRunNow={onRunNow}
        running={running}
      />
    );
  }

  // List mode
  if (versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center h-full">
        <FileText className="w-8 h-8 text-muted-foreground/30 mb-3" />
        <p className="text-sm text-muted-foreground mb-3">No deliveries yet</p>
        <button
          onClick={onRunNow}
          disabled={running || agent.status === 'archived' || missingSourcesWarning}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {isGoalMode ? 'Generate first version' : 'Run now'}
        </button>
        {missingSourcesWarning && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
            Add sources in Settings before running.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Run Now bar */}
      <div className="px-3 py-2 border-b border-border flex items-center justify-between shrink-0">
        <span className="text-xs text-muted-foreground">
          {versions.length} version{versions.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={onRunNow}
          disabled={running || agent.status === 'archived' || missingSourcesWarning}
          title={missingSourcesWarning ? 'Add sources in Settings before running' : (isGoalMode ? 'Generate' : 'Run Now')}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
          {isGoalMode ? 'Generate' : 'Run Now'}
        </button>
      </div>

      {missingSourcesWarning && (
        <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
          <span className="shrink-0">&#9888;</span>
          No sources configured — open Settings to select platform content.
        </div>
      )}

      {/* Version list */}
      <div className="divide-y divide-border flex-1 overflow-y-auto">
        {versions.slice(0, 20).map((version, idx) => (
          <button
            key={version.id}
            onClick={() => setPreviewIdx(idx)}
            className="w-full px-3 py-2.5 flex items-center justify-between hover:bg-muted/50 transition-colors text-left group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs text-muted-foreground shrink-0">v{version.version_number}</span>
              <span className="text-xs truncate">{getRunTimestamp(version)}</span>
              {getStatusBadge(version)}
            </div>
            <ChevronLeft className="w-3.5 h-3.5 text-muted-foreground -rotate-180 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
          </button>
        ))}
        {versions.length > 20 && (
          <div className="px-3 py-2 text-center">
            <span className="text-xs text-muted-foreground">Showing 20 of {versions.length}</span>
          </div>
        )}
      </div>
    </div>
  );
}
