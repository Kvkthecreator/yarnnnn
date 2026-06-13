'use client';

/**
 * TraderMoneyTruth — alpha-trader program section (order: 3 post-ADR-273).
 *
 * Renders the live Alpaca brokerage state — equity headline + day Δ +
 * buying power + cash + open positions count.
 *
 * Data: api.programs.alphaTrader.moneyTruth() → /api/programs/alpha-trader/money-truth (Alpaca
 * /v2/account + /v2/positions, normalized for the FE).
 *
 * Scope split with TraderExpectancy (ADR-273 D4):
 *   - TraderMoneyTruth owns the LIVE brokerage headline (equity, buying
 *     power, cash, positions count, day Δ) — what's deployable right now.
 *   - TraderExpectancy owns the ACCUMULATED per-signal attribution
 *     (`by_signal` block from _money_truth.md frontmatter) — tenured
 *     intelligence about which signals work.
 *   Both can read the same money-truth surface; the split is which
 *   subset each one renders.
 *
 * Graceful degradation: when the endpoint returns `live: false`,
 * TraderPortfolio (the section above) is the canonical not-connected
 * surface for the whole alpha-trader stack. This component returns
 * null in that case to avoid duplicate messaging.
 */

import { useEffect, useState } from 'react';
import { Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api/client';

interface MoneyTruthData {
  live: boolean;
  provider?: string;
  paper?: boolean;
  equity?: number;
  cash?: number;
  buying_power?: number;
  day_pnl?: number;
  day_pnl_pct?: number;
  positions_count?: number;
  as_of?: string;
  fallback_reason?: string;
}

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '—';
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function formatPnlPct(pct: number | undefined): string {
  if (pct === undefined || pct === null) return '—';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

function formatRelativeAsOf(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 30) return 'live · just now';
  if (diffSec < 60) return `live · ${diffSec}s ago`;
  if (diffSec < 3600) return `live · ${Math.floor(diffSec / 60)}m ago`;
  return `live · ${Math.floor(diffSec / 3600)}h ago`;
}

export function TraderMoneyTruth() {
  const [data, setData] = useState<MoneyTruthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.programs.alphaTrader.moneyTruth();
        if (!cancelled) setData(res as MoneyTruthData);
      } catch {
        if (!cancelled) setData({ live: false, fallback_reason: 'alpaca_unreachable' });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section
        aria-label="Money truth"
        className="rounded-lg border border-border bg-card p-5"
      >
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  // Not connected / unreachable: TraderPortfolio (above) is the canonical
  // not-connected surface for the whole alpha-trader stack. Return null
  // here to avoid duplicate messaging per ADR-273 Phase 4 cleanup.
  if (!data || !data.live) {
    return null;
  }

  const dayPnl = data.day_pnl ?? 0;
  const pnlPositive = dayPnl >= 0;
  const pnlColor = pnlPositive ? 'text-emerald-600' : 'text-destructive';
  const PnlIcon = pnlPositive ? TrendingUp : TrendingDown;

  return (
    <section
      aria-label="Money truth"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Money truth
        </span>
        <span className="text-muted-foreground/60">
          {data.paper ? 'paper · ' : ''}
          {formatRelativeAsOf(data.as_of)}
        </span>
      </div>
      {/* Responsive metric grid: single column on phones (the text-2xl
          currency values overflow a 3-up grid below ~sm, colliding
          across cells), 3-up from sm+. Equity spans the full row on its
          own line on mobile so the day-Δ stays readable. */}
      <div className="grid grid-cols-1 gap-y-4 sm:grid-cols-3 sm:gap-6">
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Equity
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatCurrency(data.equity)}
          </div>
          <div className={`mt-1 flex items-center gap-1 text-sm ${pnlColor}`}>
            <PnlIcon className="h-3.5 w-3.5 shrink-0" />
            <span className="tabular-nums">
              {pnlPositive ? '+' : ''}
              {formatCurrency(dayPnl)} ({formatPnlPct(data.day_pnl_pct)})
            </span>
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Buying power
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatCurrency(data.buying_power)}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">
            {formatCurrency(data.cash)} cash
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Positions
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {data.positions_count ?? 0}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">open</div>
        </div>
      </div>
    </section>
  );
}
