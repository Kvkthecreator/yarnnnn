'use client';

/**
 * TraderExpectancy — alpha-trader program section (order: 4 post-ADR-273).
 *
 * Renders per-signal cumulative attribution + rolling-window expectancy
 * from the `by_signal` block of `_money_truth.md` frontmatter. Surfaces
 * the tenured intelligence the system has accumulated about which signals
 * generate P&L — the "are we getting better?" question.
 *
 * Data: api.cockpit.moneyTruth() → /api/cockpit/money-truth
 *       Reads the `by_signal` field of the response payload (written by
 *       services/outcomes/ledger.py per ADR-195). Reuses the existing
 *       money-truth route — no new endpoint per ADR-273 D3.
 *
 * Scope split with TraderMoneyTruth (ADR-273 D4):
 *   - TraderMoneyTruth shows LIVE brokerage state (equity, buying power).
 *   - TraderExpectancy shows ACCUMULATED per-signal stats.
 *   Both can read the same response; this is the canonical surface for
 *   the `by_signal` subfield.
 *
 * Recovers signal that was rendered in the deleted MoneyTruthFace kernel
 * fallback but never reached alpha-trader operators (alpha-trader's
 * SURFACES.yaml declared program_sections, so the four kernel faces
 * never ran). Now the surface that's always present.
 *
 * Visual: table of signals sorted by absolute cumulative value. Per-row:
 * signal name · trade count · win rate · cumulative P&L · 30d trend
 * indicator (positive/negative).
 *
 * Empty state per ADR-273 D6: "No reconciled outcomes yet — reconciliation
 * runs daily at 05:00 UTC."
 */

import { useEffect, useState } from 'react';
import { Loader2, BarChart3 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface RollingWindow {
  count: number;
  value_cents: number;
  wins: number;
  losses: number;
}

interface SignalState extends RollingWindow {
  rolling_7d?: RollingWindow;
  rolling_30d?: RollingWindow;
  rolling_90d?: RollingWindow;
}

// The money-truth endpoint shape per the api client. The by_signal field
// is not in the FE type today (it lives in the substrate file the route
// reads), so we widen the response shape at this consumer to expose it.
interface MoneyTruthWithSignals {
  live: boolean;
  by_signal?: Record<string, SignalState>;
  fallback_reason?: string;
}

function formatCents(cents: number | undefined | null): string {
  if (cents == null) return '$0.00';
  const sign = cents > 0 ? '+' : cents < 0 ? '−' : '';
  const abs = Math.abs(cents) / 100;
  return `${sign}$${abs.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function winRatePct(w: RollingWindow): number | null {
  const decided = w.wins + w.losses;
  if (decided === 0) return null;
  return (w.wins / decided) * 100;
}

export function TraderExpectancy() {
  const [bySignal, setBySignal] = useState<Record<string, SignalState> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Widen the response shape at the consumer — the money-truth route
        // surfaces by_signal in its raw substrate body but the typed FE
        // client today only exposes the balances subset. Cast through unknown
        // to access the substrate field without altering the shared client
        // type contract.
        const res = (await api.cockpit.moneyTruth()) as unknown as MoneyTruthWithSignals;
        if (!cancelled) setBySignal(res.by_signal ?? null);
      } catch {
        if (!cancelled) setBySignal(null);
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

  const entries = bySignal
    ? Object.entries(bySignal).sort(
        ([, a], [, b]) => Math.abs(b.value_cents ?? 0) - Math.abs(a.value_cents ?? 0),
      )
    : [];

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <BarChart3 className="mr-1 inline h-3 w-3" /> Expectancy by signal
          {entries.length > 0 && ` · ${entries.length}`}
        </h3>
        <span className="text-[10px] text-muted-foreground/50">
          From outcome reconciliation (daily 05:00 UTC)
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground py-3 text-center">
          No reconciled outcomes yet — reconciliation runs daily at 05:00 UTC.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                <th className="pb-2 text-left">Signal</th>
                <th className="pb-2 text-right tabular-nums">Count</th>
                <th className="pb-2 text-right tabular-nums">Win rate</th>
                <th className="pb-2 text-right tabular-nums">Cumulative</th>
                <th className="pb-2 text-right tabular-nums">7d</th>
                <th className="pb-2 text-right tabular-nums">30d</th>
                <th className="pb-2 text-right tabular-nums">90d</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {entries.map(([slug, s]) => {
                const wr = winRatePct(s);
                const cumPos = (s.value_cents ?? 0) >= 0;
                const r7 = s.rolling_7d?.value_cents;
                const r30 = s.rolling_30d?.value_cents;
                const r90 = s.rolling_90d?.value_cents;

                return (
                  <tr key={slug} className="hover:bg-muted/20 transition-colors">
                    <td className="py-1.5 font-mono font-medium text-foreground">{slug}</td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                      {s.count ?? 0}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                      {wr != null ? `${wr.toFixed(0)}%` : '—'}
                    </td>
                    <td className={cn(
                      'py-1.5 text-right tabular-nums font-medium',
                      cumPos ? 'text-emerald-600' : 'text-destructive',
                    )}>
                      {formatCents(s.value_cents)}
                    </td>
                    <td className={cn(
                      'py-1.5 text-right tabular-nums text-[11px]',
                      r7 == null ? 'text-muted-foreground/30'
                        : r7 >= 0 ? 'text-emerald-600/80' : 'text-destructive/80',
                    )}>
                      {r7 == null ? '—' : formatCents(r7)}
                    </td>
                    <td className={cn(
                      'py-1.5 text-right tabular-nums text-[11px]',
                      r30 == null ? 'text-muted-foreground/30'
                        : r30 >= 0 ? 'text-emerald-600/80' : 'text-destructive/80',
                    )}>
                      {r30 == null ? '—' : formatCents(r30)}
                    </td>
                    <td className={cn(
                      'py-1.5 text-right tabular-nums text-[11px]',
                      r90 == null ? 'text-muted-foreground/30'
                        : r90 >= 0 ? 'text-emerald-600/80' : 'text-destructive/80',
                    )}>
                      {r90 == null ? '—' : formatCents(r90)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-[10px] text-muted-foreground/40">
            Per-signal P&L from realized outcomes. Cumulative is all-time;
            7d/30d/90d are rolling windows. Trades without signal_id
            (manual / pre-attribution) contribute to total P&L but not to
            this attribution table.
          </p>
        </div>
      )}
    </section>
  );
}
