'use client';

/**
 * MoneyTruthFace — face #2 of the four-face cockpit (ADR-228).
 *
 * Renders money-truth for the operator: rolling P&L windows + per-signal
 * attribution (when present). Reads `_money_truth_summary.md` (cross-domain
 * rollup) by default; bundles can override with a specific per-domain
 * `_money_truth.md`.
 *
 * P&L unification (2026-05-12): rewritten to consume the new
 * `MoneyTruthMeta` JSON-frontmatter shape from `money-truth.ts`. Surfaces
 * gross (and net once cost-truth lands) + per-signal attribution table.
 * Replaces the prior implementation that read flat YAML keys the backend
 * never emitted (the FE was rendering an empty face on every workspace
 * before this commit).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useComposition } from '@/lib/compositor';
import {
  parse,
  formatCents,
  deriveNetMetrics,
  winRate,
  signalEntries,
  type MoneyTruthMeta,
  type RollingWindow,
} from '@/lib/content-shapes/money-truth';

const DEFAULT_FALLBACK = '/workspace/context/_money_truth_summary.md';

function readMoneyTruthSource(composition: ReturnType<typeof useComposition>['data']): string {
  const cockpit = composition.composition.tabs?.work?.list as { cockpit?: { money_truth?: { substrate_fallback?: string } } } | undefined;
  return cockpit?.cockpit?.money_truth?.substrate_fallback ?? DEFAULT_FALLBACK;
}

/**
 * Resolve the rolling-window dict for the meta, regardless of whether it's
 * a per-domain `_money_truth.md` (top-level rolling_30d) or a cross-domain
 * summary (`aggregate.rolling_30d`).
 */
function pickWindow(meta: MoneyTruthMeta, days: 7 | 30 | 90): RollingWindow | undefined {
  const key = `rolling_${days}d` as const;
  if (meta.aggregate?.[key]) return meta.aggregate[key];
  return meta[key];
}

export function MoneyTruthFace() {
  const { data: composition } = useComposition();
  const path = readMoneyTruthSource(composition);

  const [meta, setMeta] = useState<MoneyTruthMeta | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (!cancelled) {
          setMeta(file?.content ? parse(file.content) : {});
        }
      } catch {
        if (!cancelled) setMeta({});
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [path]);

  if (!loaded) return null;

  const window30d = pickWindow(meta ?? {}, 30);
  const window7d = pickWindow(meta ?? {}, 7);
  const window90d = pickWindow(meta ?? {}, 90);
  const isEmpty = !window30d || window30d.count === 0;
  const linkPath = `/context?path=${encodeURIComponent(path)}`;

  if (isEmpty) {
    return (
      <section
        aria-label="Money truth"
        className="rounded-lg border border-dashed border-border bg-muted/20 p-5"
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          <Minus className="h-3.5 w-3.5" />
          Money truth
        </div>
        <p className="text-sm text-muted-foreground">
          No realized outcomes yet.{' '}
          <Link
            href="/work"
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Run a tracking task
          </Link>{' '}
          and reconciliation will accumulate here.
        </p>
      </section>
    );
  }

  const net30 = deriveNetMetrics(window30d);
  const net30Positive = net30.net_cents >= 0;
  const netColor = net30Positive ? 'text-emerald-600' : 'text-destructive';
  const NetIcon = net30Positive ? TrendingUp : TrendingDown;

  const signals = signalEntries(meta ?? {});

  return (
    <section
      aria-label="Money truth"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Money truth
        </span>
        {(meta?.last_reconciled_at || meta?.generated_at) && (
          <Link
            href={linkPath}
            className="text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
          >
            last reconciled {formatGeneratedAt(meta?.last_reconciled_at ?? meta?.generated_at ?? '')}
          </Link>
        )}
      </div>

      {/* Rolling windows: 7d / 30d / 90d with gross+net (net = gross until
          cost-truth integration lands). When cost arrives, the third row
          shows `cost` and a fourth shows `net`. */}
      <div className="grid grid-cols-3 gap-6 mb-5">
        <Stat
          label="Net (30d)"
          value={formatCents(net30.net_cents)}
          target={
            window30d
              ? `${window30d.wins}W · ${window30d.losses}L · ${window30d.count} events`
              : null
          }
          color={netColor}
          Icon={NetIcon}
        />
        <Stat
          label="Net (7d)"
          value={formatCents(window7d?.value_cents)}
          target={window7d ? `${window7d.count} events` : null}
          color={(window7d?.value_cents ?? 0) >= 0 ? 'text-foreground' : 'text-destructive'}
        />
        <Stat
          label="Net (90d)"
          value={formatCents(window90d?.value_cents)}
          target={window90d ? `${window90d.count} events` : null}
          color={(window90d?.value_cents ?? 0) >= 0 ? 'text-foreground' : 'text-destructive'}
        />
      </div>

      {/* Per-signal attribution table. Renders only when by_signal has
          entries (commerce / manual-only workspaces naturally skip this). */}
      {signals.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60 mb-2">
            Per-signal attribution
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground/60 text-[10px] uppercase tracking-wide">
                <th className="text-left font-medium pb-1">Signal</th>
                <th className="text-right font-medium pb-1">Net</th>
                <th className="text-right font-medium pb-1">Win rate</th>
                <th className="text-right font-medium pb-1">30d</th>
              </tr>
            </thead>
            <tbody>
              {signals.map(([signalId, state]) => {
                const wr = winRate(state);
                const sigColor =
                  (state.value_cents ?? 0) > 0
                    ? 'text-emerald-600'
                    : (state.value_cents ?? 0) < 0
                    ? 'text-destructive'
                    : 'text-foreground';
                return (
                  <tr key={signalId} className="border-t border-border/50">
                    <td className="py-1.5 font-medium">{signalId}</td>
                    <td className={`py-1.5 text-right tabular-nums ${sigColor}`}>
                      {formatCents(state.value_cents)}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                      {wr !== undefined ? `${(wr * 100).toFixed(0)}%` : '—'}
                      <span className="text-muted-foreground/60 ml-1">
                        ({state.wins}/{state.wins + state.losses})
                      </span>
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                      {formatCents(state.rolling_30d?.value_cents)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Stat({
  label, value, target, color, Icon,
}: {
  label: string;
  value: string;
  target: string | null;
  color: string;
  Icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div>
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
        {label}
      </div>
      <div className={`mt-1 flex items-baseline gap-1 text-2xl font-semibold tabular-nums ${color}`}>
        {Icon && <Icon className="h-4 w-4" />}
        <span>{value}</span>
      </div>
      {target && (
        <div className="mt-0.5 text-[11px] text-muted-foreground/70">{target}</div>
      )}
    </div>
  );
}

function formatGeneratedAt(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
