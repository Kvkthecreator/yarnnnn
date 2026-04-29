'use client';

/**
 * ChatFilterBar — ADR-219 Commit 5.
 *
 * Three filter chip rows on /chat that narrow the messages.map render:
 *   - Weight:   material | routine | housekeeping (multi-select)
 *   - Identity: yarnnn | user | agent | reviewer | system | external (multi-select)
 *   - Task:     a single task slug (set via deep-link or "filter on this task")
 *
 * Each filter is a query-param so the URL is the source of truth and
 * deep-links round-trip cleanly. Per ADR-219 D5: "filter affordances on
 * /chat ... each filter is a query-param on /chat; deep-linkable."
 *
 * Time-range and pulse filters are deferred — they need richer UI (date
 * picker / multi-select with semantics) and weren't gated on Commit 5.
 *
 * The bar is hidden by default — operators see it via a subtle toggle
 * in the surface header. When any filter is set, a clear-all chip
 * appears so the operator never gets stranded with hidden messages.
 */

import { useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import type { NarrativeFilter } from '@/components/tp/ChatPanel';

const WEIGHTS: Array<'material' | 'routine' | 'housekeeping'> = [
  'material',
  'routine',
  'housekeeping',
];

const IDENTITIES: Array<{ id: string; label: string }> = [
  { id: 'user', label: 'You' },
  { id: 'assistant', label: 'YARNNN' },
  { id: 'agent', label: 'Agent' },
  { id: 'reviewer', label: 'Reviewer' },
  { id: 'system', label: 'System' },
  { id: 'external', label: 'External' },
];


/**
 * Parse the filter URL params into a NarrativeFilter for ChatPanel.
 * Exported so /chat/page can drive ChatPanel's filter prop without
 * re-implementing the parse.
 */
export function parseChatFilterFromSearch(
  searchParams: URLSearchParams,
): NarrativeFilter | null {
  const weights = searchParams.get('weight')?.split(',').filter(Boolean) ?? [];
  const identities = searchParams.get('identity')?.split(',').filter(Boolean) ?? [];
  const taskSlug = searchParams.get('task');

  if (weights.length === 0 && identities.length === 0 && !taskSlug) {
    return null;
  }

  return {
    ...(weights.length > 0 && {
      weights: new Set(
        weights.filter(w => WEIGHTS.includes(w as typeof WEIGHTS[number])) as Array<
          'material' | 'routine' | 'housekeeping'
        >,
      ),
    }),
    ...(identities.length > 0 && { identities: new Set(identities) }),
    ...(taskSlug && { taskSlug }),
  };
}


export function ChatFilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activeWeights = useMemo(() => {
    return new Set(searchParams.get('weight')?.split(',').filter(Boolean) ?? []);
  }, [searchParams]);

  const activeIdentities = useMemo(() => {
    return new Set(searchParams.get('identity')?.split(',').filter(Boolean) ?? []);
  }, [searchParams]);

  const activeTaskSlug = searchParams.get('task');

  const hasAnyFilter =
    activeWeights.size > 0 || activeIdentities.size > 0 || !!activeTaskSlug;

  const setMultiParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    const existing = new Set(params.get(key)?.split(',').filter(Boolean) ?? []);
    if (existing.has(value)) {
      existing.delete(value);
    } else {
      existing.add(value);
    }
    if (existing.size === 0) {
      params.delete(key);
    } else {
      params.set(key, Array.from(existing).join(','));
    }
    router.replace(`/chat${params.toString() ? '?' + params.toString() : ''}`);
  };

  const clearAll = () => {
    router.replace('/chat');
  };

  const clearTaskSlug = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('task');
    router.replace(`/chat${params.toString() ? '?' + params.toString() : ''}`);
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 sm:px-4 py-1.5 text-[11px] border-b border-border/40">
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 mr-1">
        Show
      </span>

      {/* Weight chips */}
      {WEIGHTS.map(w => (
        <button
          key={w}
          type="button"
          onClick={() => setMultiParam('weight', w)}
          className={cn(
            'px-2 py-0.5 rounded border transition-colors',
            activeWeights.has(w)
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'border-border/40 text-muted-foreground/70 hover:border-border hover:text-foreground',
          )}
        >
          {w}
        </button>
      ))}

      <span className="text-muted-foreground/30 mx-1">·</span>

      {/* Identity chips */}
      {IDENTITIES.map(id => (
        <button
          key={id.id}
          type="button"
          onClick={() => setMultiParam('identity', id.id)}
          className={cn(
            'px-2 py-0.5 rounded border transition-colors',
            activeIdentities.has(id.id)
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'border-border/40 text-muted-foreground/70 hover:border-border hover:text-foreground',
          )}
        >
          {id.label}
        </button>
      ))}

      {/* Task slug — set externally (deep-link / row click); shown as a clearable pill. */}
      {activeTaskSlug && (
        <>
          <span className="text-muted-foreground/30 mx-1">·</span>
          <button
            type="button"
            onClick={clearTaskSlug}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 hover:bg-primary/15"
            title="Clear recurrence filter"
          >
            <span>recurrence: {activeTaskSlug}</span>
            <X className="w-2.5 h-2.5" />
          </button>
        </>
      )}

      {/* Clear-all escape hatch */}
      {hasAnyFilter && (
        <button
          type="button"
          onClick={clearAll}
          className="ml-auto text-[10px] text-muted-foreground/60 hover:text-foreground transition-colors"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
