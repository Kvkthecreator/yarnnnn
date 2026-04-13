'use client';

/**
 * TrackingMiddle — Detail middle band for `output_kind: accumulates_context`.
 *
 * SURFACE-ARCHITECTURE.md v10.0 — health dashboard shape (2026-04-14).
 *
 * The mental model for accumulates_context tasks:
 *   "This is quietly building knowledge for me. Is it working?"
 *
 * The user wants:
 *   1. Is it running? (status visible in header strip above)
 *   2. Where does the context live? (domain link — already in header strip,
 *      repeated here for direct navigation)
 *   3. What has it been collecting? (compact run receipts — NOT a full document)
 *
 * Key change from v9: the last-run CHANGELOG was rendered as a full scrollable
 * document card, which looked like a deliverable. That was wrong. The document
 * IS the domain folder — this page is just the health dashboard. We now render
 * compact run receipts (date + brief summary line) instead.
 *
 * Registry fallback: if TASK.md parsing fails to populate task.context_writes,
 * we infer the primary domain from task.type_key via TRACKING_TYPE_DOMAIN_MAP.
 * This prevents the "No context domain configured" broken state.
 */

import { useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle, ChevronDown, ChevronRight,
  FolderOpen, Layers, Loader2, RefreshCw, Shield,
} from 'lucide-react';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import { CONTEXT_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { DeliverableSpec, Task } from '@/types';

// Fallback: infer primary context domain from type_key when context_writes
// is missing (TASK.md parsing failure). Keeps the domain link functional.
const TRACKING_TYPE_DOMAIN_MAP: Record<string, string> = {
  'track-competitors': 'competitors',
  'track-market': 'market',
  'track-relationships': 'relationships',
  'track-projects': 'projects',
  'slack-digest': 'slack',
  'notion-digest': 'notion',
  'github-digest': 'github',
  'research-topics': 'research',
};

function inferPrimaryDomain(task: Task): string | null {
  const writes = task.context_writes ?? [];
  const fromWrites = writes.find(d => d !== 'signals') ?? writes[0] ?? null;
  if (fromWrites) return fromWrites;
  if (task.type_key) return TRACKING_TYPE_DOMAIN_MAP[task.type_key] ?? null;
  return null;
}

// Data Contract panel — collapsible quality spec for context tasks
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

// Compact run receipt — parse the first heading + brief summary from output
function extractReceiptLine(content: string): string {
  if (!content) return '';
  // Try to find a summary line — first non-empty line that isn't a heading or date
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (line.startsWith('#')) continue;           // skip headings
    if (/^\*\*/.test(line)) continue;             // skip bold headers
    if (/^April|^Jan|^Feb|^Mar|^May|^Jun|^Jul|^Aug|^Sep|^Oct|^Nov|^Dec/.test(line)) continue; // skip dates
    if (line.length < 10) continue;               // skip very short lines
    // truncate to ~80 chars
    return line.length > 80 ? line.slice(0, 77) + '…' : line;
  }
  return '';
}

export function TrackingMiddle({
  task,
  refreshKey,
  deliverableSpec,
}: {
  task: Task;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
}) {
  const { latest, history: outputs, loading, error, reload } = useTaskOutputs(task.slug, {
    includeLatest: true,
    historyLimit: 10,
    refreshKey,
  });

  const primaryDomain = inferPrimaryDomain(task);
  const writes = task.context_writes ?? [];
  const otherDomains = writes.filter(d => d !== (primaryDomain ?? '') && d !== 'signals');

  // Build run receipt entries from outputs (most recent first)
  // latest + history give us the full picture
  const runEntries = [
    ...(latest ? [{ date: latest.date, content: latest.content ?? latest.md_content ?? '' }] : []),
    ...outputs
      .filter(o => o.date !== latest?.date)
      .map(o => ({ date: o.date, content: '' })),
  ].slice(0, 10);

  const [expandedDate, setExpandedDate] = useState<string | null>(null);

  return (
    <>
      {/* Domain section */}
      <div className="px-6 py-4 border-b border-border/40">
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">Context Domain</h3>
        {primaryDomain ? (
          <div className="space-y-1.5">
            <Link
              href={`${CONTEXT_ROUTE}?domain=${primaryDomain}`}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              <FolderOpen className="w-4 h-4" />
              /workspace/context/{primaryDomain}/
            </Link>
            {otherDomains.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                <Layers className="w-3 h-3" />
                <span>Also writes to:</span>
                {otherDomains.map(d => (
                  <Link
                    key={d}
                    href={`${CONTEXT_ROUTE}?domain=${d}`}
                    className="hover:text-foreground hover:underline"
                  >
                    {d}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground/60">No context domain configured for this task.</p>
        )}
      </div>

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
                    {/* Status dot */}
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500/70 mt-1.5 shrink-0" />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-foreground font-medium">
                          {entry.date ? formatRelativeTime(entry.date) : '—'}
                        </span>
                        {entry.date && (
                          <span className="text-[10px] text-muted-foreground/50">{entry.date}</span>
                        )}
                        {/* Expand toggle for latest run */}
                        {hasFullContent && (
                          <button
                            onClick={() => setExpandedDate(isExpanded ? null : entry.date)}
                            className="ml-auto text-[10px] text-muted-foreground/50 hover:text-muted-foreground flex items-center gap-0.5"
                          >
                            {isExpanded ? <><ChevronDown className="w-3 h-3" />Hide</> : <><ChevronRight className="w-3 h-3" />Details</>}
                          </button>
                        )}
                      </div>
                      {receiptLine && (
                        <p className="text-[11px] text-muted-foreground/70 mt-0.5 truncate">{receiptLine}</p>
                      )}
                    </div>
                  </div>

                  {/* Expandable full log for latest run */}
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
