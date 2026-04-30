'use client';

/**
 * TraderPortfolio — program section component for alpha-trader (order: 1).
 *
 * ADR-243 Phase C. Renders the portfolio equity headline + time-series
 * sparkline, matching the Alpaca brokerage dashboard aesthetic per the
 * COCKPIT-COMPONENT-DESIGN.md design reference.
 *
 * Data: api.cockpit.portfolioHistory() → /api/cockpit/portfolio-history
 *       api.cockpit.moneyTruth()        → equity headline + day Δ
 *
 * Chart: minimal SVG sparkline. Recharts-style line chart kept intentionally
 * lightweight — the full Recharts bundle adds ~200KB; a path-based sparkline
 * handles the brokerage-history shape cleanly with no dependency.
 *
 * Graceful degradation: when Alpaca is unreachable or disconnected, renders
 * a substrate-based empty state with a message pointing to Settings.
 */

import { useEffect, useMemo, useState } from 'react';
import { RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Period = '1D' | '1M' | '1Y' | 'All';
type Timeframe = '1Min' | '1H' | '1D';

const PERIOD_CONFIG: Record<Period, { alpacaPeriod: string; alpacaTimeframe: Timeframe }> = {
  '1D':  { alpacaPeriod: '1D',  alpacaTimeframe: '1H' },
  '1M':  { alpacaPeriod: '1M',  alpacaTimeframe: '1D' },
  '1Y':  { alpacaPeriod: '1A',  alpacaTimeframe: '1D' },
  'All': { alpacaPeriod: 'all', alpacaTimeframe: '1D' },
};

function formatCurrency(v: number | undefined | null): string {
  if (v == null) return '$—';
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
}

function formatPct(v: number | undefined | null): string {
  if (v == null) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

/** Minimal SVG sparkline — draws a path over normalized equity values. */
function Sparkline({ values, positive }: { values: number[]; positive: boolean }) {
  const w = 480;
  const h = 80;
  const path = useMemo(() => {
    if (values.length < 2) return '';
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const pts = values.map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return pts.join(' ');
  }, [values]);

  if (!path) return null;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" preserveAspectRatio="none">
      <path d={path} fill="none" stroke={positive ? '#16a34a' : '#dc2626'} strokeWidth={2} />
    </svg>
  );
}

export function TraderPortfolio() {
  const [period, setPeriod] = useState<Period>('1M');
  const [history, setHistory] = useState<{
    timestamps: number[];
    equity: number[];
    profit_loss_pct: number[];
  } | null>(null);
  const [account, setAccount] = useState<{
    equity?: number; day_pnl?: number; day_pnl_pct?: number;
    paper?: boolean; as_of?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [noConnection, setNoConnection] = useState(false);

  const fetchHistory = async (p: Period) => {
    setLoading(true);
    const cfg = PERIOD_CONFIG[p];
    const [histRes, accountRes] = await Promise.allSettled([
      api.cockpit.portfolioHistory(cfg.alpacaPeriod, cfg.alpacaTimeframe),
      api.cockpit.moneyTruth(),
    ]);
    if (
      histRes.status === 'fulfilled' && !histRes.value.live &&
      histRes.value.fallback_reason === 'no_platform_connection'
    ) {
      setNoConnection(true);
      setLoading(false);
      return;
    }
    setNoConnection(false);
    if (histRes.status === 'fulfilled' && histRes.value.data) {
      setHistory(histRes.value.data as any);
    }
    if (accountRes.status === 'fulfilled' && accountRes.value.live) {
      setAccount(accountRes.value);
    }
    setLoading(false);
  };

  useEffect(() => { fetchHistory(period); }, [period]);

  const equityValues = history?.equity ?? [];
  const currentEquity = account?.equity ?? (equityValues.length ? equityValues[equityValues.length - 1] : null);
  const dayPnl = account?.day_pnl;
  const dayPnlPct = account?.day_pnl_pct;
  const pnlPositive = (dayPnl ?? 0) >= 0;

  if (noConnection) {
    return (
      <section className="rounded-lg border border-dashed border-border bg-muted/20 p-5">
        <p className="text-sm text-muted-foreground">
          Alpaca not connected.{' '}
          <a href="/settings?tab=connectors" className="underline underline-offset-4 hover:text-foreground">
            Connect in Settings
          </a>{' '}
          to see live portfolio data.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70 mb-1">
            Your portfolio
            {account?.paper && (
              <span className="ml-2 text-[9px] font-semibold uppercase tracking-widest text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                paper
              </span>
            )}
          </div>
          {loading ? (
            <div className="h-7 w-32 rounded bg-muted/40 animate-pulse" />
          ) : (
            <div className="text-2xl font-semibold tabular-nums">
              {formatCurrency(currentEquity)}
              {dayPnl != null && (
                <span className={cn('ml-2 text-sm font-normal', pnlPositive ? 'text-emerald-600' : 'text-destructive')}>
                  {pnlPositive ? <TrendingUp className="inline h-3.5 w-3.5 mr-0.5" /> : <TrendingDown className="inline h-3.5 w-3.5 mr-0.5" />}
                  {formatPct(dayPnlPct)}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {(['1D', '1M', '1Y', 'All'] as Period[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={cn(
                'px-2 py-0.5 text-[11px] font-medium rounded transition-colors',
                period === p
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {p}
            </button>
          ))}
          <button
            type="button"
            onClick={() => fetchHistory(period)}
            className="ml-1 p-1 text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Sparkline */}
      <div className="h-20 w-full">
        {loading ? (
          <div className="h-full w-full rounded bg-muted/30 animate-pulse" />
        ) : equityValues.length > 1 ? (
          <Sparkline values={equityValues} positive={pnlPositive} />
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
            No history data available
          </div>
        )}
      </div>
    </section>
  );
}
