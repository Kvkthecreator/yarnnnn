'use client';

/**
 * TraderMoneyTruth — bundle component for alpha-trader's MoneyTruth face.
 *
 * Authored by ADR-242 Phase 2. Calls /api/cockpit/money-truth (the
 * live Alpaca account snapshot endpoint shipped in ADR-242 Phase 1).
 * Renders brokerage shape — equity headline, day Δ tile, buying
 * power, positions count.
 *
 * Graceful degradation: when the endpoint returns `live: false` (no
 * platform connection / no credentials / Alpaca unreachable), this
 * component renders a small inline notice and the operator sees the
 * substrate-fallback state via the face's fallthrough rendering.
 *
 * Per ADR-242 §"Singular Implementation discipline": this is the
 * singular live-snapshot consumer for cockpit. No parallel surface.
 *
 * Per the per-slot conventions in docs/architecture/compositor.md:
 * the component owns its visual semantics; the resolver only decides
 * which component renders.
 */

import { useEffect, useState } from 'react';
import { Activity, AlertCircle, Loader2, TrendingDown, TrendingUp } from 'lucide-react';
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
        const res = await api.cockpit.moneyTruth();
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

  // Live = false — let the face's fallthrough render the substrate
  // path. Returning null here is the cleanest signal; the face's
  // dispatch branch checks the binding and decides which component
  // mounts. But the dispatch happens at MoneyTruthFace level, not
  // here; if we got mounted with live=false, we render an inline
  // notice rather than null so the operator can see why.
  if (!data || !data.live) {
    const reasonText = (() => {
      switch (data?.fallback_reason) {
        case 'no_platform_connection':
          return 'Alpaca not connected — connect in Settings to see live equity.';
        case 'no_credentials':
          return 'Alpaca credentials missing — re-connect in Settings.';
        case 'alpaca_unreachable':
        default:
          return 'Alpaca unreachable — showing last reconciled substrate.';
      }
    })();
    return (
      <section
        aria-label="Money truth"
        className="rounded-lg border border-border bg-card p-5"
      >
        <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          <Activity className="h-3.5 w-3.5" />
          Money truth
        </div>
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{reasonText}</span>
        </div>
      </section>
    );
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
      <div className="grid grid-cols-3 gap-6">
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Equity
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatCurrency(data.equity)}
          </div>
          <div className={`mt-1 flex items-center gap-1 text-sm ${pnlColor}`}>
            <PnlIcon className="h-3.5 w-3.5" />
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
