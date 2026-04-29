'use client';

/**
 * AgentDashboard — Data tab: compact explorer view with work signals.
 *
 * SURFACE-ARCHITECTURE.md v7.2: Windows Explorer-style compact listing
 * of domain entities and synthesis files. Emphasizes what's been worked on
 * with freshness indicators. Not a file browser — links to Context page.
 *
 * Used by the Data tab in AgentContentView.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Loader2,
  FolderOpen,
  FolderClosed,
  FileText,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { formatShort, getFreshness } from '@/lib/formatting';
import type { Agent, Recurrence } from '@/types';

interface AgentDashboardProps {
  agent: Agent;
  tasks: Recurrence[];
}

export function AgentDashboard({ agent, tasks }: AgentDashboardProps) {
  const domain = agent.context_domain;

  const [loading, setLoading] = useState(true);
  const [domainData, setDomainData] = useState<{
    entities: Array<{
      slug: string; name: string; last_updated: string | null;
      preview: string | null;
      files: Array<{ name: string; path: string; updated_at: string | null }>;
    }>;
    synthesis_files: Array<{
      name: string; filename: string; path: string;
      updated_at: string | null; preview: string | null;
    }>;
    entity_count: number;
  } | null>(null);

  useEffect(() => {
    if (!domain) { setLoading(false); return; }
    setLoading(true);
    api.workspace.getDomainEntities(domain)
      .then(data => setDomainData(data))
      .catch(() => setDomainData(null))
      .finally(() => setLoading(false));
  }, [domain]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!domain) {
    return (
      <div className="px-5 py-12 text-center">
        <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No context domain</p>
      </div>
    );
  }

  const entities = domainData?.entities || [];
  const synthFiles = domainData?.synthesis_files || [];
  const entityCount = domainData?.entity_count || entities.length;

  // Sort: entities by most recently updated first
  const sortedEntities = [...entities].sort((a, b) => {
    const aTime = a.last_updated ? new Date(a.last_updated).getTime() : 0;
    const bTime = b.last_updated ? new Date(b.last_updated).getTime() : 0;
    return bTime - aTime;
  });

  // All timestamps for summary
  const allUpdates = entities.map(e => e.last_updated).filter(Boolean).sort().reverse();

  if (entityCount === 0 && synthFiles.length === 0) {
    return (
      <div className="px-5 py-12 text-center">
        <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No data yet</p>
        <p className="text-xs text-muted-foreground/50 mt-1">
          Context will accumulate as tasks run.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      {/* Summary bar */}
      <div className="px-5 py-2.5 border-b border-border/50 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {entityCount} {entityCount === 1 ? 'entity' : 'entities'}
          {allUpdates[0] && <> · Last updated {formatShort(allUpdates[0])}</>}
        </span>
        <Link
          href={`/context?domain=${domain}`}
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          Explore
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[minmax(0,1fr)_80px_90px] gap-3 px-5 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground/40 border-b border-border/30">
        <span>Name</span>
        <span className="text-right">Files</span>
        <span className="text-right">Modified</span>
      </div>

      {/* Synthesis files */}
      {synthFiles.map(file => {
        const freshness = getFreshness(file.updated_at || undefined);
        return (
          <div
            key={file.path}
            className="grid grid-cols-[minmax(0,1fr)_80px_90px] gap-3 px-5 py-2 text-sm border-b border-border/20 hover:bg-muted/20"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <FileText className="w-4 h-4 text-muted-foreground/40 shrink-0" />
              <span className="truncate">{file.name || file.filename}</span>
              <span className="text-[10px] text-muted-foreground/40 shrink-0">synthesis</span>
            </div>
            <div className="text-xs text-muted-foreground/40 text-right self-center">—</div>
            <div className={cn(
              'text-[11px] text-right self-center tabular-nums',
              freshness === 'new' ? 'text-green-600/70' : freshness === 'recent' ? 'text-muted-foreground/60' : 'text-muted-foreground/35'
            )}>
              {file.updated_at ? formatShort(file.updated_at) : '—'}
            </div>
          </div>
        );
      })}

      {/* Entity rows */}
      {sortedEntities.map(entity => {
        const freshness = getFreshness(entity.last_updated || undefined);
        return (
          <div
            key={entity.slug}
            className="grid grid-cols-[minmax(0,1fr)_80px_90px] gap-3 px-5 py-2 text-sm border-b border-border/20 hover:bg-muted/20"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {freshness === 'new' ? (
                <FolderOpen className="w-4 h-4 text-green-600/60 shrink-0" />
              ) : (
                <FolderClosed className="w-4 h-4 text-sky-600/60 shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="truncate font-medium">{entity.name}</span>
                  {freshness === 'new' && (
                    <span className="shrink-0 text-[9px] font-medium text-green-600 bg-green-500/10 px-1 py-0.5 rounded">new</span>
                  )}
                </div>
                {entity.preview && (
                  <p className="text-[11px] text-muted-foreground/50 truncate">{entity.preview}</p>
                )}
              </div>
            </div>
            <div className="text-xs text-muted-foreground/40 text-right self-center">
              {entity.files?.length || 0} files
            </div>
            <div className={cn(
              'text-[11px] text-right self-center tabular-nums',
              freshness === 'new' ? 'text-green-600/70' : freshness === 'recent' ? 'text-muted-foreground/60' : 'text-muted-foreground/35'
            )}>
              {entity.last_updated ? formatShort(entity.last_updated) : '—'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
