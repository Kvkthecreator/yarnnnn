'use client';

/**
 * TrackingMiddle — Detail middle band for `output_kind: accumulates_context`.
 *
 * ADR-180: Work is operational only. TrackingMiddle answers one question:
 *   "Is this task running correctly?"
 *
 * Shows: compact run receipts (date + summary), expandable last-run log,
 * data contract collapsible.
 *
 * "What has it accumulated?" now lives in Context — the domain folder is
 * linked from WorkDetail's OutputsLinkBlock, not embedded here.
 * FilesTab deleted (ADR-180).
 */

import { useState, useEffect } from 'react';
import {
  AlertCircle, ChevronDown, ChevronRight,
  Loader2, RefreshCw, Shield,
} from 'lucide-react';
import { useRecurrenceOutputs } from '@/hooks/useRecurrenceOutputs';
import { formatRelativeTime } from '@/lib/formatting';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { PlatformSourcesSection } from './PlatformSourcesSection';
import { cn } from '@/lib/utils';
import type { DeliverableSpec, Recurrence } from '@/types';

// ─── Data Contract panel ─────────────────────────────────────────────────────

function DataContractPanel({ spec }: { spec: DeliverableSpec }) {
  const [open, setOpen] = useState(false);
  const hasContent = spec.quality_criteria?.length || spec.expected_output;
  if (!hasContent) return null;

  return (
    <div className="px-6 pb-3">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-1.5 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
      >
        <Shield className="h-3 w-3" />
        <span className="uppercase tracking-wide font-medium">Data Contract</span>
        {open ? <ChevronDown className="h-3 w-3 ml-auto" /> : <ChevronRight className="h-3 w-3 ml-auto" />}
      </button>

      {open && (
        <div className="mt-2 rounded-md border border-border bg-muted/5 p-3 space-y-3 text-xs">
          {spec.expected_output && (
            <div>
              <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1">Context Structure</p>
              <div className="space-y-0.5 text-muted-foreground">
                {spec.expected_output.paths && <p>Paths: {spec.expected_output.paths}</p>}
                {spec.expected_output.format && <p>Output: {spec.expected_output.format}</p>}
              </div>
            </div>
          )}
          {spec.quality_criteria?.length ? (
            <div>
              <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1">Data Quality Criteria</p>
              <ul className="space-y-0.5 text-muted-foreground list-none">
                {spec.quality_criteria.map((c, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-muted-foreground/30 flex-shrink-0">–</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ─── Receipt line extractor ───────────────────────────────────────────────────

function extractReceiptLine(content: string): string {
  if (!content) return '';
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (line.startsWith('#')) continue;
    if (/^\*\*/.test(line)) continue;
    if (/^April|^Jan|^Feb|^Mar|^May|^Jun|^Jul|^Aug|^Sep|^Oct|^Nov|^Dec/.test(line)) continue;
    if (line.length < 10) continue;
    return line.length > 80 ? line.slice(0, 77) + '…' : line;
  }
  return '';
}

// ─── Activity tab ────────────────────────────────────────────────────────────

function ActivityTab({
  task,
  refreshKey,
  deliverableSpec,
}: {
  task: Recurrence;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
}) {
  const { latest, history: outputs, loading, error, reload } = useRecurrenceOutputs(task.slug, {
    includeLatest: true,
    historyLimit: 10,
    refreshKey,
  });

  const runEntries = [
    ...(latest ? [{ date: latest.date, content: latest.content ?? latest.md_content ?? '' }] : []),
    ...outputs
      .filter(o => o.date !== latest?.date)
      .map(o => ({ date: o.date, content: '' })),
  ].slice(0, 10);

  const [expandedDate, setExpandedDate] = useState<string | null>(null);

  return (
    <>
      {/* Data contract */}
      {deliverableSpec && (
        <div className="pt-3">
          <DataContractPanel spec={deliverableSpec} />
        </div>
      )}

      {/* Run receipts */}
      <div className="px-6 py-4">
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-3">Run history</h3>

        {loading ? (
          <div className="flex items-center gap-2 py-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Loading…</span>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 py-2">
            <AlertCircle className="w-3.5 h-3.5 text-destructive/70" />
            <span className="text-xs text-muted-foreground">{error}</span>
            <button
              onClick={() => void reload()}
              className="ml-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <RefreshCw className="h-3 w-3" /> Retry
            </button>
          </div>
        ) : runEntries.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">
            No runs yet. After the first run, you'll see what was collected here.
          </p>
        ) : (
          <ul className="space-y-0">
            {runEntries.map((entry, idx) => {
              const receiptLine = idx === 0 ? extractReceiptLine(entry.content) : '';
              const isExpanded = expandedDate === entry.date;
              const hasFullContent = idx === 0 && (latest?.content || latest?.md_content);

              return (
                <li key={entry.date ?? idx} className="border-b border-border/30 last:border-0">
                  <div className="flex items-start gap-3 py-2.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500/70 mt-1.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-foreground font-medium">
                          {entry.date ? formatRelativeTime(entry.date) : '—'}
                        </span>
                        {entry.date && (
                          <span className="text-[10px] text-muted-foreground/50">{entry.date}</span>
                        )}
                        {hasFullContent && (
                          <button
                            onClick={() => setExpandedDate(isExpanded ? null : (entry.date ?? null))}
                            className="ml-auto text-[10px] text-muted-foreground/50 hover:text-muted-foreground flex items-center gap-0.5"
                          >
                            {isExpanded
                              ? <><ChevronDown className="w-3 h-3" />Hide</>
                              : <><ChevronRight className="w-3 h-3" />Details</>
                            }
                          </button>
                        )}
                      </div>
                      {receiptLine && (
                        <p className="text-[11px] text-muted-foreground/70 mt-0.5 truncate">{receiptLine}</p>
                      )}
                    </div>
                  </div>

                  {isExpanded && hasFullContent && (
                    <div className="pb-3 pl-4.5">
                      <div className="rounded-md border border-border bg-muted/5 overflow-hidden">
                        <div className="max-h-[360px] overflow-auto p-4">
                          <div className="prose prose-sm max-w-none dark:prose-invert">
                            <MarkdownRenderer content={latest?.content ?? latest?.md_content ?? ''} />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </>
  );
}

// ─── Export ───────────────────────────────────────────────────────────────────
// ADR-180: single-purpose operational view — Activity only.
// "What has it accumulated?" is answered by Context (domain folder).
//
// Platform tasks (slack-digest, notion-digest, github-digest) additionally
// show a PlatformSourcesSection so the user can edit which channels/pages/repos
// the task reads from without leaving the Work surface.

export function TrackingMiddle({
  task,
  refreshKey,
  deliverableSpec,
  onSourcesUpdated,
}: {
  task: Recurrence;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
  onSourcesUpdated?: () => void;
}) {
  return (
    <>
      {/* Platform source picker — only shown for platform tasks */}
      <PlatformSourcesSection task={task} onSourcesUpdated={onSourcesUpdated} />
      <ActivityTab task={task} refreshKey={refreshKey} deliverableSpec={deliverableSpec} />
    </>
  );
}
