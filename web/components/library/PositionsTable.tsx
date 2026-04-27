'use client';

/**
 * PositionsTable — system component library, ADR-225.
 *
 * Renders open positions from substrate (typically
 * /workspace/context/portfolio/_positions.md). Placeholder visual.
 */

import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { api } from '@/lib/api/client';

interface PositionsTableProps {
  source: string;
}

export function PositionsTable({ source }: PositionsTableProps) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const file = await api.workspace.getFile(source);
        if (!cancelled) setContent(file?.content ?? '');
      } catch {
        if (!cancelled) setContent('');
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
      <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm text-neutral-500">
        Loading positions…
      </div>
    );
  }

  if (!content.trim()) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-4 text-sm text-neutral-500">
        <div className="flex items-center gap-2 font-medium">
          <TrendingUp className="h-4 w-4" />
          Positions
        </div>
        <div className="mt-1 text-xs">
          No open positions at <code className="text-neutral-700">{source}</code>.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
        <TrendingUp className="h-4 w-4" />
        Positions
      </div>
      <pre className="whitespace-pre-wrap font-mono text-xs text-neutral-700">{content}</pre>
    </div>
  );
}
