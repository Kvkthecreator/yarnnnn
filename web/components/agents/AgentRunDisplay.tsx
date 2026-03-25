'use client';

/**
 * Run display components for the Agent Workspace panel.
 *
 * RunsPanel: lives in the right panel, two modes:
 * - List mode: compact run list, click to preview
 * - Preview mode: full markdown render of selected run, back to list
 *
 * Replaces the former InlineVersionCard (pinned above chat) with panel-based display.
 */

import { useState } from 'react';
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
  ArrowLeft,
  Download,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Agent, AgentRun, SourceSnapshot, RenderedOutput } from '@/types';

// =============================================================================
// Helpers
// =============================================================================

const PLATFORM_EMOJI: Record<string, string> = {
  slack: '\u{1F4AC}',
  email: '\u{1F4E7}',
  notion: '\u{1F4DD}',
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

function getTriggerLabel(version: AgentRun): string | null {
  const triggerType = version.metadata?.trigger_type;
  if (!triggerType) return null;
  if (triggerType === 'manual') return 'Manual';
  if (triggerType === 'schedule') return 'Scheduled';
  if (triggerType === 'event') return 'Event';
  if (triggerType === 'proactive_review') return 'Proactive Review';
  return triggerType.replace(/_/g, ' ');
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
// VersionPreviewFull — full-height version render for the panel
// =============================================================================

const FILE_TYPE_ICONS: Record<string, string> = {
  pdf: '\u{1F4C4}',
  docx: '\u{1F4DD}',
  pptx: '\u{1F4CA}',
  xlsx: '\u{1F4CA}',
  png: '\u{1F5BC}',
  svg: '\u{1F5BC}',
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '';
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function VersionPreviewFull({
  version,
  agent,
  onBack,
  onRunNow,
  running,
  renderedOutputs,
}: {
  version: AgentRun;
  agent: Agent;
  onBack: () => void;
  onRunNow: () => void;
  running: boolean;
  renderedOutputs?: RenderedOutput[];
}) {
  const [copied, setCopied] = useState(false);
  const content = version.final_content || version.draft_content || '';
  const triggerLabel = getTriggerLabel(version);

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
          title="Back to runs"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
        </button>
        <span className="text-xs font-medium">v{version.version_number}</span>
        {getStatusBadge(version)}
        <span className="text-xs text-muted-foreground">{getRunTimestamp(version)}</span>
        {triggerLabel && (
          <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {triggerLabel}
          </span>
        )}

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

        {/* ADR-118: Rendered output downloads */}
        {renderedOutputs && renderedOutputs.length > 0 && (
          <div className="px-4 py-3 border-t border-border">
            <p className="text-xs font-medium text-muted-foreground mb-2">Attachments</p>
            <div className="space-y-1.5">
              {renderedOutputs.map((ro, i) => {
                const ext = ro.filename.split('.').pop() || '';
                return (
                  <a
                    key={i}
                    href={ro.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-2 bg-muted/30 border border-border rounded-md hover:bg-muted/60 transition-colors group"
                  >
                    <span className="text-sm">{FILE_TYPE_ICONS[ext] || '\u{1F4CE}'}</span>
                    <span className="text-sm flex-1 truncate">{ro.filename}</span>
                    {ro.size_bytes > 0 && (
                      <span className="text-xs text-muted-foreground shrink-0">{formatFileSize(ro.size_bytes)}</span>
                    )}
                    <Download className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground shrink-0" />
                  </a>
                );
              })}
            </div>
          </div>
        )}

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

      </div>
    </div>
  );
}

// =============================================================================
// RunsPanel — panel tab with list + preview modes
// =============================================================================

export function RunsPanel({
  versions,
  agent,
  onRunNow,
  running,
  renderedOutputs,
}: {
  versions: AgentRun[];
  agent: Agent;
  onRunNow: () => void;
  running: boolean;
  renderedOutputs?: RenderedOutput[];
}) {
  // null = list mode, number = preview mode (index into versions)
  const [previewIdx, setPreviewIdx] = useState<number | null>(
    // Auto-show latest version if it exists
    versions.length > 0 ? 0 : null
  );

  const isGoalMode = agent.mode === 'goal';

  // Preview mode: show full version
  if (previewIdx !== null && versions[previewIdx]) {
    return (
      <VersionPreviewFull
        version={versions[previewIdx]}
        agent={agent}
        onBack={() => setPreviewIdx(null)}
        onRunNow={onRunNow}
        running={running}
        renderedOutputs={renderedOutputs}
      />
    );
  }

  // List mode
  if (versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center h-full">
        <FileText className="w-8 h-8 text-muted-foreground/30 mb-3" />
        <p className="text-sm text-muted-foreground mb-3">No runs yet</p>
        <button
          onClick={onRunNow}
          disabled={running || agent.status === 'archived'}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {isGoalMode ? 'Generate first run' : 'Run now'}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Run Now bar */}
      <div className="px-3 py-2 border-b border-border flex items-center justify-between shrink-0">
        <span className="text-xs text-muted-foreground">
          {versions.length} run{versions.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={onRunNow}
          disabled={running || agent.status === 'archived'}
          title={isGoalMode ? 'Generate' : 'Run Now'}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
          {isGoalMode ? 'Generate' : 'Run Now'}
        </button>
      </div>

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
