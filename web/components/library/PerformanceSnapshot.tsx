'use client';

/**
 * PerformanceSnapshot — system component library, ADR-225.
 *
 * Renders a portfolio performance snapshot from substrate file frontmatter
 * (rolling P&L, win rate, drawdown, Sharpe). Placeholder visual; the
 * Phase 2 implementation goal is the wiring (resolver → component dispatch
 * by `kind`), not visual polish.
 *
 * Binding: file (markdown with YAML frontmatter, e.g.
 * /workspace/context/portfolio/_performance.md per ADR-195 v2 + ADR-220).
 *
 * Pure reader. Surface compose mode (live binding). Document compose
 * embedding it would render the same shape from a frozen snapshot.
 */

import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { api } from '@/lib/api/client';

interface PerformanceSnapshotProps {
  /** Substrate path the resolver bound. Typically /workspace/context/{domain}/_performance.md. */
  source: string;
}

export function PerformanceSnapshot({ source }: PerformanceSnapshotProps) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const file = await api.workspace.getFile(source);
        if (!cancelled) setContent(file?.content ?? '');
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setContent('');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white p-4 text-sm text-neutral-500">
        <Activity className="h-4 w-4 animate-pulse" />
        Loading performance…
      </div>
    );
  }

  if (error || !content.trim()) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-4 text-sm text-neutral-500">
        <div className="flex items-center gap-2 font-medium">
          <Activity className="h-4 w-4" />
          Performance Snapshot
        </div>
        <div className="mt-1 text-xs">
          No performance data yet at <code className="text-neutral-700">{source}</code>.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
        <Activity className="h-4 w-4" />
        Performance Snapshot
      </div>
      <pre className="whitespace-pre-wrap font-mono text-xs text-neutral-700">{content}</pre>
    </div>
  );
}
