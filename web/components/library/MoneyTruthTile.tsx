'use client';

/**
 * MoneyTruthTile — Cockpit pane #3 in the six-question cockpit framing
 * (2026-04-28 reshape). The pane that answers "where does the money stand?"
 *
 * Universal in shape across delegation products; the actual numeric source
 * varies by program. The kernel-default reads
 * `/workspace/context/_performance_summary.md` (workspace-wide rollup per
 * ADR-195). Bundles override the binding to point at program-specific
 * money-truth substrate (alpha-trader: `/workspace/context/portfolio/_performance.md`;
 * alpha-commerce when active: `/workspace/context/revenue/_performance.md`).
 *
 * Visual discipline: three numbers, one tile, two-second scan. Net P&L
 * vs target, drawdown vs limit, exposure vs limit. No charts in cockpit —
 * the operator opens the relevant tracking task for charts.
 *
 * Empty state: when the source file is absent (workspace hasn't generated
 * a performance summary yet — typical on day 1 of a program), render a
 * dim placeholder pointing the operator at where the data will appear.
 */

import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';

interface MoneyTruthMeta {
  pnl_30d_pct?: number;
  pnl_30d_target_pct?: number;
  drawdown_30d_pct?: number;
  drawdown_limit_pct?: number;
  exposure_pct?: number;
  exposure_limit_pct?: number;
  win_rate?: number;
  generated_at?: string;
}

function parseFrontmatter(content: string): MoneyTruthMeta {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return {};
  const meta: MoneyTruthMeta = {};
  for (const line of fm[1].split('\n')) {
    const m = line.match(/^([a-z_0-9]+):\s*(.*)$/);
    if (!m) continue;
    const k = m[1].trim();
    const v = m[2].trim().replace(/^['"]|['"]$/g, '');
    const num = Number(v);
    if (!Number.isNaN(num)) {
      // Only assign known numeric fields
      if (k === 'pnl_30d_pct') meta.pnl_30d_pct = num;
      if (k === 'pnl_30d_target_pct') meta.pnl_30d_target_pct = num;
      if (k === 'drawdown_30d_pct' || k === 'max_drawdown_30d_pct') meta.drawdown_30d_pct = num;
      if (k === 'drawdown_limit_pct') meta.drawdown_limit_pct = num;
      if (k === 'exposure_pct') meta.exposure_pct = num;
      if (k === 'exposure_limit_pct') meta.exposure_limit_pct = num;
      if (k === 'win_rate') meta.win_rate = num;
    } else if (k === 'generated_at') {
      meta.generated_at = v;
    }
  }
  return meta;
}

interface MoneyTruthTileProps {
  source?: string;
}

const DEFAULT_SOURCE = '/workspace/context/_performance_summary.md';

export function MoneyTruthTile({ source }: MoneyTruthTileProps) {
  const path = source ?? DEFAULT_SOURCE;
  const [meta, setMeta] = useState<MoneyTruthMeta | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (!cancelled) setMeta(file?.content ? parseFrontmatter(file.content) : {});
      } catch {
        if (!cancelled) setMeta({});
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
  }, [path]);

  if (!loaded) return null;

  const isEmpty = !meta || Object.keys(meta).length === 0 || meta.pnl_30d_pct === undefined;
  const linkPath = `/context?path=${encodeURIComponent(path)}`;

  if (isEmpty) {
    return (
      <Link
        href={linkPath}
        className="block rounded-lg border border-dashed border-border bg-muted/20 p-4 text-xs text-muted-foreground hover:bg-muted/30"
      >
        <div className="mb-1 flex items-center gap-2 font-medium text-foreground/70">
          <Minus className="h-3.5 w-3.5" />
          Money truth
        </div>
        <p>No performance data yet. Refreshes when your tracking + reporting tasks have run at least once.</p>
      </Link>
    );
  }

  const pnl = meta.pnl_30d_pct ?? 0;
  const pnlPositive = pnl >= 0;
  const pnlColor = pnlPositive ? 'text-emerald-600' : 'text-destructive';
  const PnlIcon = pnlPositive ? TrendingUp : TrendingDown;

  return (
    <Link
      href={linkPath}
      className="block rounded-lg border border-border bg-card p-4 hover:border-foreground/20"
    >
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Money truth
        </span>
        {meta.generated_at && (
          <span className="text-muted-foreground/50">
            as of {formatGeneratedAt(meta.generated_at)}
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Stat
          label="P&L (30d)"
          value={`${pnlPositive ? '+' : ''}${pnl.toFixed(1)}%`}
          target={meta.pnl_30d_target_pct !== undefined ? `vs +${meta.pnl_30d_target_pct.toFixed(1)}% target` : null}
          color={pnlColor}
          Icon={PnlIcon}
        />
        <Stat
          label="Drawdown"
          value={meta.drawdown_30d_pct !== undefined ? `${meta.drawdown_30d_pct.toFixed(1)}%` : '—'}
          target={meta.drawdown_limit_pct !== undefined ? `cap ${meta.drawdown_limit_pct.toFixed(0)}%` : null}
          color={drawdownColor(meta.drawdown_30d_pct, meta.drawdown_limit_pct)}
        />
        <Stat
          label="Win rate"
          value={meta.win_rate !== undefined ? `${(meta.win_rate * 100).toFixed(0)}%` : '—'}
          target={null}
          color="text-foreground"
        />
      </div>
    </Link>
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
      <div className={`mt-0.5 flex items-baseline gap-1 text-lg font-semibold ${color}`}>
        {Icon && <Icon className="h-3.5 w-3.5" />}
        <span>{value}</span>
      </div>
      {target && (
        <div className="text-[10px] text-muted-foreground/60">{target}</div>
      )}
    </div>
  );
}

function drawdownColor(dd?: number, limit?: number): string {
  if (dd === undefined) return 'text-foreground';
  const abs = Math.abs(dd);
  if (limit !== undefined && abs >= Math.abs(limit) * 0.8) return 'text-destructive';
  if (limit !== undefined && abs >= Math.abs(limit) * 0.5) return 'text-amber-600';
  return 'text-foreground';
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
