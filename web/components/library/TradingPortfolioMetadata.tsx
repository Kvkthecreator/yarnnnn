'use client';

/**
 * TradingPortfolioMetadata — alpha-trader bundle component (ADR-225 Phase 3).
 *
 * Bundle-supplied chrome metadata for `portfolio-review` (the matched
 * task in alpha-trader's SURFACES.yaml). Where the kernel-default
 * KernelDeliverableMetadata reads `task.last_run_at` ("Last output:
 * 3h ago"), this trader-flavored variant reads
 * `/workspace/context/portfolio/_performance.md` substrate freshness
 * — a more meaningful operational signal for a Dashboard middle that
 * regenerates substrate on every run.
 *
 * The asymmetry between this and the kernel default is exactly the
 * pressure point that motivated ADR-225 Phase 3: chrome belongs with
 * the middle, not next to it.
 *
 * Binding: defaults to `/workspace/context/portfolio/_performance.md`
 * but reads any path the bundle threads via `source`.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useWorkDetailActions } from './WorkDetailActionsContext';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { AGENTS_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';

const DEFAULT_SOURCE = '/workspace/context/portfolio/_performance.md';

interface TradingPortfolioMetadataProps {
  source?: string;
}

interface PerformanceMeta {
  generated_at?: string;
  positions_count?: number;
}

function parseFrontmatterMeta(content: string): PerformanceMeta {
  // Lightweight YAML frontmatter parse — not loading a YAML lib for
  // two scalar fields. Per ADR-220 sys_manifest convention the file
  // has --- frontmatter at top.
  const match = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!match) return {};
  const meta: PerformanceMeta = {};
  for (const line of match[1].split('\n')) {
    const m = line.match(/^([a-z_]+):\s*(.*)$/);
    if (!m) continue;
    const key = m[1].trim();
    const value = m[2].trim().replace(/^['"]|['"]$/g, '');
    if (key === 'generated_at') meta.generated_at = value;
    if (key === 'positions_count') meta.positions_count = Number(value);
  }
  return meta;
}

export function TradingPortfolioMetadata({ source }: TradingPortfolioMetadataProps) {
  const path = source ?? DEFAULT_SOURCE;
  const { task, assignedAgent } = useWorkDetailActions();
  const [meta, setMeta] = useState<PerformanceMeta | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (!cancelled) setMeta(parseFrontmatterMeta(file?.content ?? ''));
      } catch {
        if (!cancelled) setMeta(null);
      }
    })();
    return () => { cancelled = true; };
  }, [path]);

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge schedule={task.schedule} />
      <span className="text-muted-foreground/30">·</span>
      <span className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-primary/70">
        <Activity className="w-3 h-3" />
        Portfolio
      </span>
      {assignedAgent && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <Link
            href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
            className="hover:text-foreground hover:underline"
          >
            {assignedAgent.title}
          </Link>
        </>
      )}
      {meta?.generated_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last sync: {formatRelativeTime(meta.generated_at)}</span>
        </>
      ) : task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last sync: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Awaiting first sync</span>
        </>
      )}
      {typeof meta?.positions_count === 'number' && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>{meta.positions_count} positions</span>
        </>
      )}
    </div>
  );
}
