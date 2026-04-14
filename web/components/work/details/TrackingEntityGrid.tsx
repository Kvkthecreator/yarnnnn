'use client';

/**
 * TrackingEntityGrid — Work detail view for `output_kind: accumulates_context`.
 *
 * ADR-180: Work is operational. This component shows WHAT is being tracked
 * (entity catalog) + operational health (last run, next run).
 *
 * The entity grid is the centerpiece: domain entities displayed as icon
 * cards with last-updated timestamps and file counts. Clicking an entity
 * navigates to `/context?path=...` — feels like a section swap, not a
 * full page reload (uses router.replace, same surface layout).
 *
 * The run history strip is secondary — compact activity log below the grid.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Building2, FolderOpen, Layers, Loader2, RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { CONTEXT_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import type { Task } from '@/types';

// ─── Types ────────────────────────────────────────────────────────────────────

interface EntityEntry {
  slug: string;
  name: string;
  last_updated: string | null;
  preview: string | null;
  files: Array<{ name: string; path: string; updated_at: string | null }>;
}

interface SynthesisEntry {
  name: string;
  filename: string;
  path: string;
  updated_at: string | null;
  preview: string | null;
}

interface DomainData {
  domain_key: string;
  display_name: string;
  entity_type: string | null;
  synthesis_files: SynthesisEntry[];
  entities: EntityEntry[];
  entity_count: number;
}

// ─── Entity icon — generic grid card ─────────────────────────────────────────

function EntityCard({
  entity,
  domainKey,
  onClick,
}: {
  entity: EntityEntry;
  domainKey: string;
  onClick: (path: string) => void;
}) {
  const path = `/workspace/context/${domainKey}/${entity.slug}`;
  const fileCount = entity.files.length;

  return (
    <button
      onClick={() => onClick(path)}
      className={cn(
        'group flex flex-col gap-2 rounded-lg border border-border bg-muted/20 p-3',
        'text-left hover:bg-muted/40 hover:border-border/80 transition-colors',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
      )}
    >
      {/* Icon */}
      <div className="w-8 h-8 rounded-md bg-muted/60 flex items-center justify-center shrink-0">
        <Building2 className="w-4 h-4 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors" />
      </div>

      {/* Name */}
      <div className="min-w-0">
        <p className="text-xs font-medium text-foreground truncate leading-tight">
          {entity.name}
        </p>
        <p className="text-[10px] text-muted-foreground/50 mt-0.5">
          {fileCount} {fileCount === 1 ? 'file' : 'files'}
          {entity.last_updated ? (
            <> · {formatRelativeTime(entity.last_updated)}</>
          ) : null}
        </p>
      </div>
    </button>
  );
}

// ─── Synthesis file card ──────────────────────────────────────────────────────

function SynthesisCard({
  file,
  onClick,
}: {
  file: SynthesisEntry;
  onClick: (path: string) => void;
}) {
  return (
    <button
      onClick={() => onClick(file.path)}
      className={cn(
        'group flex items-center gap-2.5 rounded-lg border border-border bg-muted/10 px-3 py-2',
        'text-left hover:bg-muted/30 hover:border-border/80 transition-colors w-full',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
      )}
    >
      <Layers className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 group-hover:text-muted-foreground/70 transition-colors" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-foreground truncate">{file.name}</p>
        {file.preview && (
          <p className="text-[10px] text-muted-foreground/50 truncate">{file.preview}</p>
        )}
      </div>
      {file.updated_at && (
        <span className="text-[10px] text-muted-foreground/40 shrink-0">
          {formatRelativeTime(file.updated_at)}
        </span>
      )}
    </button>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ displayName }: { displayName: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-6 text-center">
      <FolderOpen className="w-8 h-8 text-muted-foreground/15 mb-3" />
      <p className="text-xs font-medium text-muted-foreground/60">
        No {displayName.toLowerCase()} tracked yet
      </p>
      <p className="text-[11px] text-muted-foreground/40 mt-1">
        Entities will appear here after the first run.
      </p>
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

export function TrackingEntityGrid({ task }: { task: Task }) {
  const router = useRouter();
  const writes = task.context_writes ?? [];
  const primaryDomain = writes.find(d => d !== 'signals') ?? writes[0] ?? null;

  const [domainData, setDomainData] = useState<DomainData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!primaryDomain) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.workspace.getDomainEntities(primaryDomain)
      .then(data => {
        if (!cancelled) setDomainData(data);
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [primaryDomain]);

  function handleNavigate(path: string) {
    router.replace(`${CONTEXT_ROUTE}?path=${encodeURIComponent(path)}`);
  }

  // No domain declared
  if (!primaryDomain) {
    return (
      <div className="px-6 py-5 text-xs text-muted-foreground/60">
        No context domain declared for this task.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-6 py-5">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Loading…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 px-6 py-5">
        <AlertCircle className="w-3.5 h-3.5 text-destructive/70 shrink-0" />
        <span className="text-xs text-muted-foreground">{error}</span>
        <button
          onClick={() => {
            setError(null);
            setLoading(true);
            api.workspace.getDomainEntities(primaryDomain!)
              .then(setDomainData)
              .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
              .finally(() => setLoading(false));
          }}
          className="ml-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="h-3 w-3" /> Retry
        </button>
      </div>
    );
  }

  // No data yet (domain exists but never run)
  if (!domainData || (domainData.entities.length === 0 && domainData.synthesis_files.length === 0)) {
    return <EmptyState displayName={domainData?.display_name ?? primaryDomain} />;
  }

  const { entities, synthesis_files, display_name } = domainData;

  return (
    <div className="px-6 py-4 space-y-5">
      {/* Entity icon grid */}
      {entities.length > 0 && (
        <div>
          <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-3 uppercase tracking-wide">
            {display_name}
            <span className="ml-1.5 text-muted-foreground/40 normal-case">
              {entities.length} tracked
            </span>
          </h3>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {entities.map(entity => (
              <EntityCard
                key={entity.slug}
                entity={entity}
                domainKey={primaryDomain}
                onClick={handleNavigate}
              />
            ))}
          </div>
        </div>
      )}

      {/* Synthesis files (cross-entity summaries) */}
      {synthesis_files.length > 0 && (
        <div>
          <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2 uppercase tracking-wide">
            Summaries
          </h3>
          <div className="space-y-1.5">
            {synthesis_files.map(file => (
              <SynthesisCard
                key={file.path}
                file={file}
                onClick={handleNavigate}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
