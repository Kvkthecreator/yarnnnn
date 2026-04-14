'use client';

/**
 * TrackingMiddle — Detail middle band for `output_kind: accumulates_context`.
 *
 * SURFACE-ARCHITECTURE.md v10.0 — two-tab health dashboard (2026-04-14).
 *
 * Two tabs answer the two questions users have about accumulating tasks:
 *
 *   Activity — "Is it running?" compact run receipts (date + summary),
 *               expandable to full last-run log. Data contract collapsible.
 *
 *   Files    — "What has it accumulated?" Domain entity listing pulled from
 *               /api/workspace/domain/{key}. Entity cards (name, file count,
 *               last updated) + synthesis files section. The key missing
 *               piece: users can see *what files* the task has been writing
 *               without leaving the detail page.
 *
 * Registry fallback: if TASK.md parsing fails to populate task.context_writes,
 * we infer the primary domain from task.type_key via TRACKING_TYPE_DOMAIN_MAP.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  AlertCircle, ChevronDown, ChevronRight,
  FileText, FolderOpen, Layers, Loader2, RefreshCw, Shield,
} from 'lucide-react';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import { CONTEXT_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { DeliverableSpec, Task } from '@/types';

// Fallback: infer primary context domain from type_key when context_writes
// is missing (TASK.md parsing failure).
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
  task: Task;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
}) {
  const { latest, history: outputs, loading, error, reload } = useTaskOutputs(task.slug, {
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

// ─── Files tab ───────────────────────────────────────────────────────────────

type DomainEntity = {
  slug: string;
  name: string;
  last_updated: string | null;
  preview: string | null;
  files: Array<{ name: string; path: string; updated_at: string | null }>;
};

type SynthesisFile = {
  name: string;
  filename: string;
  path: string;
  updated_at: string | null;
  preview: string | null;
};

function FilesTab({ task }: { task: Task }) {
  const primaryDomain = inferPrimaryDomain(task);
  const writes = task.context_writes ?? [];
  const otherDomains = writes.filter(d => d !== (primaryDomain ?? '') && d !== 'signals');

  const [entities, setEntities] = useState<DomainEntity[]>([]);
  const [synthFiles, setSynthFiles] = useState<SynthesisFile[]>([]);
  const [entityCount, setEntityCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);

  useEffect(() => {
    if (!primaryDomain) return;
    setLoading(true);
    setError(null);
    api.workspace.getDomainEntities(primaryDomain)
      .then(data => {
        setEntities(data.entities ?? []);
        setSynthFiles(data.synthesis_files ?? []);
        setEntityCount(data.entity_count ?? 0);
      })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load files'))
      .finally(() => setLoading(false));
  }, [primaryDomain]);

  if (!primaryDomain) {
    return (
      <div className="px-6 py-8 text-center">
        <FolderOpen className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
        <p className="text-xs text-muted-foreground/60">No context domain configured for this task.</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-4 space-y-4">
      {/* Domain header */}
      <div className="flex items-center justify-between">
        <Link
          href={`${CONTEXT_ROUTE}?domain=${primaryDomain}`}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <FolderOpen className="w-3.5 h-3.5" />
          /workspace/context/{primaryDomain}/
        </Link>
        {otherDomains.length > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/60">
            <Layers className="w-3 h-3" />
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

      {loading ? (
        <div className="flex items-center gap-2 py-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Loading files…</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 py-4">
          <AlertCircle className="w-3.5 h-3.5 text-destructive/70" />
          <span className="text-xs text-muted-foreground">{error}</span>
        </div>
      ) : entities.length === 0 && synthFiles.length === 0 ? (
        <div className="py-8 text-center">
          <FileText className="w-5 h-5 text-muted-foreground/20 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground/60">
            No files accumulated yet. Files appear here after the first run.
          </p>
        </div>
      ) : (
        <>
          {/* Synthesis / summary files */}
          {synthFiles.length > 0 && (
            <div>
              <h4 className="text-[10px] font-medium text-muted-foreground/40 uppercase tracking-wide mb-2">
                Summaries · {synthFiles.length}
              </h4>
              <div className="space-y-1">
                {synthFiles.map(f => (
                  <div key={f.path} className="flex items-center justify-between py-1.5 border-b border-border/20 last:border-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-3 h-3 text-muted-foreground/40 shrink-0" />
                      <span className="text-xs text-muted-foreground truncate">{f.name}</span>
                    </div>
                    {f.updated_at && (
                      <span className="text-[10px] text-muted-foreground/40 shrink-0 ml-3">
                        {formatRelativeTime(f.updated_at)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entities */}
          {entities.length > 0 && (
            <div>
              <h4 className="text-[10px] font-medium text-muted-foreground/40 uppercase tracking-wide mb-2">
                Entities · {entityCount}
              </h4>
              <div className="rounded-lg border border-border/50 divide-y divide-border/30 overflow-hidden">
                {entities.map(entity => {
                  const isExpanded = expandedEntity === entity.slug;
                  return (
                    <div key={entity.slug}>
                      <button
                        onClick={() => setExpandedEntity(isExpanded ? null : entity.slug)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/20 transition-colors"
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-foreground font-medium truncate">{entity.name}</p>
                          {entity.preview && (
                            <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5">{entity.preview}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {entity.last_updated && (
                            <span className="text-[10px] text-muted-foreground/40">
                              {formatRelativeTime(entity.last_updated)}
                            </span>
                          )}
                          <span className="text-[10px] text-muted-foreground/30">
                            {entity.files.length} {entity.files.length === 1 ? 'file' : 'files'}
                          </span>
                          {isExpanded
                            ? <ChevronDown className="w-3 h-3 text-muted-foreground/40" />
                            : <ChevronRight className="w-3 h-3 text-muted-foreground/40" />
                          }
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="bg-muted/10 border-t border-border/20 px-3 py-2 space-y-1">
                          {entity.files.map(f => (
                            <div key={f.path} className="flex items-center justify-between py-0.5">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <FileText className="w-3 h-3 text-muted-foreground/30 shrink-0" />
                                <span className="text-[11px] text-muted-foreground/70 truncate">{f.name}</span>
                              </div>
                              {f.updated_at && (
                                <span className="text-[10px] text-muted-foreground/40 shrink-0 ml-2">
                                  {formatRelativeTime(f.updated_at)}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Tab chrome ───────────────────────────────────────────────────────────────

type Tab = 'activity' | 'files';

export function TrackingMiddle({
  task,
  refreshKey,
  deliverableSpec,
}: {
  task: Task;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
}) {
  const [tab, setTab] = useState<Tab>('activity');

  return (
    <>
      {/* Tab strip */}
      <div className="flex items-center gap-0 border-b border-border/40 px-6 pt-2">
        {(['activity', 'files'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'px-3 py-2 text-xs font-medium capitalize border-b-2 -mb-px transition-colors',
              tab === t
                ? 'border-foreground text-foreground'
                : 'border-transparent text-muted-foreground/60 hover:text-muted-foreground',
            )}
          >
            {t === 'activity' ? 'Activity' : 'Files'}
          </button>
        ))}
      </div>

      {/* Tab body */}
      {tab === 'activity' ? (
        <ActivityTab task={task} refreshKey={refreshKey} deliverableSpec={deliverableSpec} />
      ) : (
        <FilesTab task={task} />
      )}
    </>
  );
}
