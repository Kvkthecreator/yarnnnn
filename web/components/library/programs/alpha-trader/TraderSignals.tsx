'use client';

/**
 * TraderSignals — alpha-trader program section (order: 6 post-ADR-273).
 *
 * Renders the trade signals the system has evaluated, with the Reviewer's
 * decision trail correlated from /workspace/review/decisions.md. Closes
 * the gap between "signal evaluator fires a proposal" and "operator sees
 * what was evaluated and what the Reviewer said about it."
 *
 * Data: api.cockpit.signals(limit=10) → /workspace/context/trading/signals/*.yaml
 *       listed newest-first + best-effort reviewer-decision correlation.
 *
 * Each row shows: ticker · direction · expectancy · reviewer verdict
 * (approved / rejected / deferred) with a short excerpt of the
 * Reviewer's reasoning.
 *
 * Correlation is intentionally loose per ADR-273 D3 (backend route docs)
 * — text-match on signal slug. When no Reviewer decision matches, the
 * row renders without a verdict badge (signals can exist without a
 * Reviewer pass; the trail surfaces if and when it correlates).
 *
 * Empty state per ADR-273 D6: "No signals evaluated yet. Signal
 * evaluator runs at market open."
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Radar, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type SignalsResponse = Awaited<ReturnType<typeof api.cockpit.signals>>;
type SignalRow = SignalsResponse['signals'][number];

function formatExpectancy(v: SignalRow['expectancy']): string {
  if (v == null) return '—';
  if (typeof v === 'number') {
    const sign = v >= 0 ? '+' : '';
    return `${sign}${v.toFixed(2)}`;
  }
  return String(v);
}

function formatTimestamp(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const diff = Math.floor((Date.now() - d.getTime()) / 60_000);
  if (diff < 60) return `${diff}m ago`;
  if (diff < 60 * 24) return `${Math.floor(diff / 60)}h ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const VERDICT_BADGE: Record<NonNullable<NonNullable<SignalRow['reviewer_decision']>['verdict']>, string> = {
  approved: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  rejected: 'text-red-700 bg-red-50 border-red-200',
  deferred: 'text-amber-700 bg-amber-50 border-amber-200',
};

export function TraderSignals() {
  const [data, setData] = useState<SignalsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.cockpit.signals(10);
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setData({ live: false, fallback_reason: 'read_failed', signals: [] });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  const signals = data?.signals ?? [];
  const isEmpty = !data?.live || signals.length === 0;

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <Radar className="mr-1 inline h-3 w-3" /> Today's signals
          {signals.length > 0 && ` · ${signals.length}`}
        </h3>
        <Link
          href="/context?path=%2Fworkspace%2Fcontext%2Ftrading%2Fsignals%2F"
          className="text-[11px] text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
        >
          View all →
        </Link>
      </div>

      {isEmpty ? (
        <p className="text-sm text-muted-foreground py-3 text-center">
          No signals evaluated yet. Signal evaluator runs at market open.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {signals.map((s) => {
            const verdict = s.reviewer_decision?.verdict;
            const isExpanded = expandedSlug === s.slug;
            const directionIcon = s.direction === 'long' ? TrendingUp
              : s.direction === 'short' ? TrendingDown
              : null;
            const DirectionIcon = directionIcon;

            return (
              <li key={s.slug} className="rounded-md border border-border/60 hover:border-border transition-colors">
                <button
                  type="button"
                  onClick={() => setExpandedSlug(isExpanded ? null : s.slug)}
                  className="w-full flex items-center gap-3 px-3 py-1.5 text-left"
                >
                  <span className="font-mono text-[13px] font-medium text-foreground min-w-0">
                    {s.ticker ?? s.slug}
                  </span>
                  {DirectionIcon && (
                    <span className={cn(
                      'flex items-center gap-0.5 text-[11px] font-medium',
                      s.direction === 'long' ? 'text-emerald-600' : 'text-destructive',
                    )}>
                      <DirectionIcon className="h-3 w-3" />
                      {s.direction}
                    </span>
                  )}
                  <span className="text-[11px] tabular-nums text-muted-foreground">
                    exp {formatExpectancy(s.expectancy)}
                  </span>
                  <span className="flex-1" />
                  {verdict && (
                    <span className={cn(
                      'text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border font-medium',
                      VERDICT_BADGE[verdict],
                    )}>
                      {verdict}
                    </span>
                  )}
                  {!verdict && s.status && (
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                      {s.status}
                    </span>
                  )}
                  <span className="text-[10px] text-muted-foreground/40 tabular-nums shrink-0">
                    {formatTimestamp(s.updated_at)}
                  </span>
                </button>
                {isExpanded && (
                  <div className="px-3 pb-2 pt-1 border-t border-border/40 space-y-2">
                    {s.rationale && (
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 mb-0.5">
                          Signal rationale
                        </div>
                        <p className="text-[12px] text-foreground/80 whitespace-pre-wrap">
                          {s.rationale}
                        </p>
                      </div>
                    )}
                    {s.reviewer_decision && (
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground/50 mb-0.5">
                          Reviewer decision
                        </div>
                        <p className="text-[12px] text-muted-foreground whitespace-pre-wrap">
                          {s.reviewer_decision.excerpt}
                        </p>
                      </div>
                    )}
                    {!s.reviewer_decision && !s.rationale && (
                      <p className="text-[11px] text-muted-foreground/50 italic">
                        No additional context available.
                      </p>
                    )}
                    <Link
                      href={`/context?path=${encodeURIComponent(s.path)}`}
                      className="inline-block text-[10px] text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
                    >
                      View source file →
                    </Link>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
