'use client';

/**
 * TraderSignalExpectancy — bundle component for alpha-trader's
 * Performance face.
 *
 * Authored by ADR-242 Phase 2. Reads `_performance.md` frontmatter
 * for trader-shaped expectancy-by-signal data and renders a compact
 * table.
 *
 * Per ADR-242 D2 the alpha-trader bundle declares this component in
 * SURFACES.yaml under `cockpit.performance.components`. PerformanceFace's
 * dispatch branch consults the binding and routes here.
 *
 * Substrate format (illustrative — operator-authored or accumulated
 * by the trader's reconciliation task):
 *
 *   ---
 *   expectancy_by_signal:
 *     mean_reversion: { trades: 47, win_rate: 0.61, expectancy_R: 0.34 }
 *     momentum: { trades: 23, win_rate: 0.48, expectancy_R: 0.12 }
 *   ---
 *
 * Falls back gracefully when the substrate file is empty / unreadable
 * — empty state with a one-line CTA pointing to Files.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, Loader2 } from 'lucide-react';
import type { LibraryComponentProps } from './registry';
import { api } from '@/lib/api/client';

interface SignalRow {
  signal: string;
  trades?: number;
  win_rate?: number;
  expectancy_R?: number;
}

/**
 * Lightweight YAML-block extraction for the `expectancy_by_signal`
 * key. Tolerant — missing fields render as "—"; malformed blocks
 * skipped silently. Same parser shape as MoneyTruthFace's
 * frontmatter walker (intentional consistency).
 */
function parseExpectancy(content: string): SignalRow[] {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return [];
  const body = fm[1];
  const rows: SignalRow[] = [];
  const blockMatch = body.match(/expectancy_by_signal:\s*\n([\s\S]*?)(\n[a-z_]+:|$)/);
  if (!blockMatch) return [];
  const block = blockMatch[1];
  for (const rawLine of block.split('\n')) {
    const line = rawLine.replace(/\s+$/, '');
    if (!line.trim()) continue;
    // Two valid shapes:
    //   mean_reversion: { trades: 47, win_rate: 0.61, expectancy_R: 0.34 }
    //   mean_reversion:
    //     trades: 47
    //     win_rate: 0.61
    const flatMatch = line.match(/^\s+([a-z_0-9]+):\s*\{\s*(.*)\s*\}\s*$/);
    if (flatMatch) {
      const signal = flatMatch[1];
      const fields = flatMatch[2];
      const row: SignalRow = { signal };
      for (const pair of fields.split(',')) {
        const m = pair.match(/\s*([a-z_]+):\s*([\d.-]+)\s*/);
        if (!m) continue;
        const k = m[1];
        const v = Number(m[2]);
        if (Number.isNaN(v)) continue;
        if (k === 'trades') row.trades = v;
        if (k === 'win_rate') row.win_rate = v;
        if (k === 'expectancy_R') row.expectancy_R = v;
      }
      rows.push(row);
    }
  }
  return rows;
}

function formatPct(v: number | undefined): string {
  if (v === undefined) return '—';
  return `${(v * 100).toFixed(0)}%`;
}

function formatR(v: number | undefined): string {
  if (v === undefined) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}R`;
}

export function TraderSignalExpectancy({ source }: LibraryComponentProps) {
  const [rows, setRows] = useState<SignalRow[] | null>(null);
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
          setRows(file?.content ? parseExpectancy(file.content) : []);
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
    const filesHref = source ? `/context?path=${encodeURIComponent(source)}` : '/context';
    return (
      <section className="rounded-lg border border-dashed border-border bg-muted/20 p-5">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          <Activity className="h-3.5 w-3.5" />
          Signal expectancy
        </div>
        <p className="text-sm text-muted-foreground">
          No signal expectancy data yet.{' '}
          <Link
            href={filesHref}
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Author or accumulate
          </Link>{' '}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">expectancy_by_signal</code>{' '}
          in <code className="rounded bg-muted px-1 py-0.5 text-[11px]">_performance.md</code>.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
        <Activity className="h-3.5 w-3.5" />
        Signal expectancy
      </div>
      <div className="space-y-1.5">
        <div className="grid grid-cols-4 gap-2 px-2 pb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 border-b border-border">
          <span>Signal</span>
          <span className="text-right tabular-nums">Trades</span>
          <span className="text-right tabular-nums">Win rate</span>
          <span className="text-right tabular-nums">Expectancy</span>
        </div>
        {rows.map((row) => (
          <div
            key={row.signal}
            className="grid grid-cols-4 gap-2 px-2 py-1 text-sm hover:bg-muted/30 rounded"
          >
            <span className="text-foreground capitalize">
              {row.signal.replace(/_/g, ' ')}
            </span>
            <span className="text-right tabular-nums text-muted-foreground">
              {row.trades ?? '—'}
            </span>
            <span className="text-right tabular-nums text-muted-foreground">
              {formatPct(row.win_rate)}
            </span>
            <span
              className={`text-right tabular-nums ${row.expectancy_R !== undefined && row.expectancy_R >= 0 ? 'text-emerald-600' : 'text-destructive'}`}
            >
              {formatR(row.expectancy_R)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
