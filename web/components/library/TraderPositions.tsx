'use client';

/**
 * TraderPositions — bundle component for alpha-trader's Tracking face's
 * operational state region.
 *
 * Authored by ADR-242 Phase 2. Reads `_positions.md` (or whatever
 * substrate path the bundle declares in
 * `cockpit.tracking.operational_state.source`) and renders the
 * positions table — symbol, quantity, market value, unrealized P&L.
 *
 * Per ADR-242 D2 alpha-trader's SURFACES.yaml declares this component
 * under `cockpit.tracking.operational_state`. TrackingFace's
 * `OperationalState` region's dispatch branch consults the binding
 * and routes here.
 *
 * Substrate format (illustrative — typically accumulated by the
 * trader's portfolio-review task; can also be operator-authored):
 *
 *   ---
 *   positions:
 *     - { symbol: AAPL, qty: 100, market_value: 19500, unrealized_pl: 234, unrealized_plpc: 0.0121 }
 *     - { symbol: MSFT, qty: 50, market_value: 21000, unrealized_pl: -45, unrealized_plpc: -0.0021 }
 *   ---
 *
 * Empty state honors the cold-workspace case (R6 in ADR-242 Risks)
 * — `_positions.md` may not exist yet for fresh workspaces.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Briefcase, Loader2 } from 'lucide-react';
import type { LibraryComponentProps } from './registry';
import { api } from '@/lib/api/client';

interface PositionRow {
  symbol: string;
  qty?: number;
  market_value?: number;
  unrealized_pl?: number;
  unrealized_plpc?: number;
}

function parsePositions(content: string): PositionRow[] {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return [];
  const body = fm[1];
  const blockMatch = body.match(/positions:\s*\n([\s\S]*?)(\n[a-z_]+:|$)/);
  if (!blockMatch) return [];
  const rows: PositionRow[] = [];
  for (const rawLine of blockMatch[1].split('\n')) {
    const line = rawLine.trimEnd();
    if (!line.trim()) continue;
    const m = line.match(/^\s*-\s*\{(.*)\}\s*$/);
    if (!m) continue;
    const fields = m[1];
    const row: PositionRow = { symbol: '' };
    for (const pair of fields.split(',')) {
      const fm2 = pair.match(/\s*([a-z_]+):\s*([A-Za-z0-9.\-]+)\s*/);
      if (!fm2) continue;
      const k = fm2[1];
      const v = fm2[2];
      if (k === 'symbol') row.symbol = v;
      else {
        const num = Number(v);
        if (Number.isNaN(num)) continue;
        if (k === 'qty') row.qty = num;
        if (k === 'market_value') row.market_value = num;
        if (k === 'unrealized_pl') row.unrealized_pl = num;
        if (k === 'unrealized_plpc') row.unrealized_plpc = num;
      }
    }
    if (row.symbol) rows.push(row);
  }
  return rows;
}

function formatCurrency(v: number | undefined): string {
  if (v === undefined) return '—';
  return v.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function formatPnlPct(pct: number | undefined): string {
  if (pct === undefined) return '—';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${(pct * 100).toFixed(2)}%`;
}

export function TraderPositions({ source }: LibraryComponentProps) {
  const [rows, setRows] = useState<PositionRow[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!source) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(source);
        if (!cancelled) {
          setRows(file?.content ? parsePositions(file.content) : []);
        }
      } catch {
        if (!cancelled) setRows([]);
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
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="mb-5">
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <Briefcase className="mr-1 inline h-3 w-3" /> Operational state
        </h3>
        <div className="rounded-md border border-dashed border-border bg-muted/20 px-3 py-3">
          <p className="text-sm text-muted-foreground">
            No positions tracked yet.{' '}
            <Link
              href="/work?task=portfolio-review"
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              Run portfolio-review
            </Link>{' '}
            to populate.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-5">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        <Briefcase className="mr-1 inline h-3 w-3" /> Positions · {rows.length}
      </h3>
      <div className="rounded-md border border-border bg-card">
        <div className="grid grid-cols-4 gap-2 border-b border-border px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
          <span>Symbol</span>
          <span className="text-right tabular-nums">Qty</span>
          <span className="text-right tabular-nums">Market value</span>
          <span className="text-right tabular-nums">Unrealized</span>
        </div>
        {rows.map((row) => (
          <div
            key={row.symbol}
            className="grid grid-cols-4 gap-2 px-3 py-1.5 text-sm border-b border-border/30 last:border-b-0 hover:bg-muted/30"
          >
            <span className="font-mono font-medium text-foreground">{row.symbol}</span>
            <span className="text-right tabular-nums text-muted-foreground">
              {row.qty ?? '—'}
            </span>
            <span className="text-right tabular-nums text-foreground">
              {formatCurrency(row.market_value)}
            </span>
            <span
              className={`text-right tabular-nums ${row.unrealized_pl !== undefined && row.unrealized_pl >= 0 ? 'text-emerald-600' : 'text-destructive'}`}
            >
              {formatCurrency(row.unrealized_pl)} ({formatPnlPct(row.unrealized_plpc)})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
