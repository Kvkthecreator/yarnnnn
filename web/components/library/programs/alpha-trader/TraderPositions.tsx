'use client';

/**
 * TraderPositions — alpha-trader program section (order: 5 post-ADR-273).
 *
 * Renders open Alpaca positions merged with per-ticker accumulated
 * indicators from the TrackUniverse substrate. The merge closes the
 * gap between "live brokerage state" and "what the system has
 * accumulated about each instrument."
 *
 * Live data: `api.programs.alphaTrader.positions()` → /api/programs/alpha-trader/positions
 *            → Alpaca /v2/positions for the operator's account
 *
 * Substrate: `api.programs.alphaTrader.indicators({ticker})` → /workspace/operation/trading/{TICKER}.yaml
 *            → SMA/RSI/ATR/volume from the TrackUniverse mechanical mirror
 *
 * Per-row enrichment:
 *   - Trend regime — derived from SMA50 vs SMA200 (golden cross → bullish,
 *     death cross → bearish, otherwise neutral)
 *   - Suggested stop — current price minus 2× ATR(14), a common volatility-
 *     based stop placement; null when ATR unavailable
 *
 * Graceful degradation per ADR-273 D6:
 *   - no Alpaca connection: empty state with "Connect Alpaca" link
 *   - no indicators for a ticker: row renders without enrichment columns
 *     (substrate is best-effort, position row is authoritative)
 *
 * Replaces the pre-ADR-273 substrate-only path (`source` from a deleted
 * binding) that always rendered empty in production. Single live path now.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Briefcase, Loader2, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface AlpacaPosition {
  symbol: string;
  qty: string;
  side: string;
  market_value: string;
  cost_basis: string;
  avg_entry_price: string;
  current_price: string;
  unrealized_pl: string;
  unrealized_plpc: string;
  change_today: string;
}

interface IndicatorContext {
  price?: number;
  sma_50?: number;
  sma_200?: number;
  rsi_14?: number;
  atr_14?: number;
}

type TrendRegime = 'bullish' | 'bearish' | 'neutral' | 'unknown';

function deriveTrend(ind: IndicatorContext): TrendRegime {
  if (ind.sma_50 == null || ind.sma_200 == null) return 'unknown';
  if (ind.sma_50 > ind.sma_200) return 'bullish';
  if (ind.sma_50 < ind.sma_200) return 'bearish';
  return 'neutral';
}

function deriveSuggestedStop(ind: IndicatorContext, currentPrice: number): number | null {
  if (ind.atr_14 == null) return null;
  return currentPrice - 2 * ind.atr_14;
}

function fmtCurrency(v: number | undefined | null, digits = 0): string {
  if (v == null) return '—';
  return v.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtPct(v: number | undefined | null): string {
  if (v == null) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(2)}%`;
}

const TREND_BADGE: Record<TrendRegime, { label: string; cls: string; Icon: typeof TrendingUp }> = {
  bullish: { label: 'Bull', cls: 'text-emerald-600 bg-emerald-50', Icon: TrendingUp },
  bearish: { label: 'Bear', cls: 'text-destructive bg-red-50', Icon: TrendingDown },
  neutral: { label: 'Neutral', cls: 'text-muted-foreground bg-muted/40', Icon: Minus },
  unknown: { label: '—', cls: 'text-muted-foreground/40', Icon: Minus },
};

export function TraderPositions() {
  const [positions, setPositions] = useState<AlpacaPosition[] | null>(null);
  const [indicators, setIndicators] = useState<Record<string, IndicatorContext>>({});
  const [loading, setLoading] = useState(true);
  const [noConnection, setNoConnection] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.programs.alphaTrader.positions();
        if (cancelled) return;
        if (!res.live && res.fallback_reason === 'no_platform_connection') {
          setNoConnection(true);
          setLoading(false);
          return;
        }
        setPositions(res.positions);
        // Kick off indicator reads in parallel, one per ticker. Each is
        // best-effort — failures leave that ticker's row un-enriched.
        const tickers = res.positions.map(p => p.symbol);
        if (tickers.length > 0) {
          const indResults = await Promise.allSettled(
            tickers.map(t => api.programs.alphaTrader.indicators(t))
          );
          if (cancelled) return;
          const indMap: Record<string, IndicatorContext> = {};
          indResults.forEach((r, i) => {
            if (r.status === 'fulfilled' && r.value.live) {
              indMap[tickers[i]] = {
                price: r.value.price,
                sma_50: r.value.sma_50,
                sma_200: r.value.sma_200,
                rsi_14: r.value.rsi_14,
                atr_14: r.value.atr_14,
              };
            }
          });
          setIndicators(indMap);
        }
      } catch {
        if (!cancelled) setPositions([]);
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

  // TraderPortfolio already surfaces the not-connected state at the top
  // of the stack — render nothing here to avoid duplicate messaging.
  if (noConnection) return null;

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <Briefcase className="mr-1 inline h-3 w-3" />
          Positions {positions && positions.length > 0 && `· ${positions.length}`}
        </h3>
      </div>

      {!positions || positions.length === 0 ? (
        <p className="text-sm text-muted-foreground py-3 text-center">
          No open positions. Place a trade via the API or Alpaca dashboard.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                <th className="pb-2 text-left">Symbol</th>
                <th className="pb-2 text-right tabular-nums">Qty</th>
                <th className="pb-2 text-right tabular-nums">Market value</th>
                <th className="pb-2 text-right tabular-nums">Unrealized</th>
                <th className="pb-2 text-center">Trend</th>
                <th className="pb-2 text-right tabular-nums">Sug. stop</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {positions.map((p) => {
                const ind = indicators[p.symbol];
                const currentPrice = parseFloat(p.current_price);
                const mktVal = parseFloat(p.market_value);
                const unrealizedPl = parseFloat(p.unrealized_pl);
                const unrealizedPlpc = parseFloat(p.unrealized_plpc);
                const stop = ind ? deriveSuggestedStop(ind, currentPrice) : null;
                const trend = ind ? deriveTrend(ind) : 'unknown';
                const trendCfg = TREND_BADGE[trend];
                const TrendIcon = trendCfg.Icon;

                return (
                  <tr key={p.symbol} className="hover:bg-muted/20 transition-colors">
                    <td className="py-1.5 font-mono font-medium">{p.symbol}</td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                      {p.qty}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">
                      {fmtCurrency(mktVal)}
                    </td>
                    <td className={cn(
                      'py-1.5 text-right tabular-nums',
                      unrealizedPl >= 0 ? 'text-emerald-600' : 'text-destructive',
                    )}>
                      {fmtCurrency(unrealizedPl, 2)}{' '}
                      <span className="text-[10px]">({fmtPct(unrealizedPlpc)})</span>
                    </td>
                    <td className="py-1.5 text-center">
                      <span className={cn(
                        'inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium',
                        trendCfg.cls,
                      )}>
                        <TrendIcon className="h-2.5 w-2.5" />
                        {trendCfg.label}
                      </span>
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-muted-foreground/80">
                      {stop != null ? fmtCurrency(stop, 2) : <span className="text-muted-foreground/30">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-[10px] text-muted-foreground/40">
            Trend: SMA50 vs SMA200 from TrackUniverse mirror. Sug. stop:
            current price − 2× ATR(14). Both null when indicators absent —
            mirror runs on a cadence; recent additions may not have data
            yet.
          </p>
        </div>
      )}
    </section>
  );
}
