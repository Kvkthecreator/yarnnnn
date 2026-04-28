'use client';

/**
 * MoneyTruthFace — face #2 of the four-face cockpit (ADR-228).
 *
 * Renders the live state of the operator's account: balance/equity, buying
 * power, day delta, drawdown, key constraints. The visual shape is the
 * brokerage / commerce dashboard summary an operator would expect — not a
 * card grid, not a placeholder.
 *
 * Source resolution (ADR-228 D5):
 *   - Bundle declares `cockpit.money_truth.live_source` — for trader, an
 *     Alpaca account snapshot; for commerce, a Lemon Squeezy snapshot.
 *   - When live source is unavailable or undeclared, falls back to substrate
 *     (`cockpit.money_truth.substrate_fallback`, typically a `_performance.md`)
 *     and renders a `· last reconciled {ts}` suffix so the operator knows
 *     it's not live.
 *   - When both are absent (true cold start), renders an empty state with
 *     a one-line action pointer.
 *
 * Phase 1 (this commit) renders the substrate-fallback path only. The
 * platform-live binding ships in Commit 3 of the ADR-228 plan, after the
 * `/api/cockpit/money-truth/{workspace_id}` endpoint lands. The face's
 * structural shape is preserved across both paths.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useComposition } from '@/lib/compositor';

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

const DEFAULT_FALLBACK = '/workspace/context/_performance_summary.md';

function readMoneyTruthSource(composition: ReturnType<typeof useComposition>['data']): string {
  const cockpit = composition.composition.tabs?.work?.list as { cockpit?: { money_truth?: { substrate_fallback?: string } } } | undefined;
  return cockpit?.cockpit?.money_truth?.substrate_fallback ?? DEFAULT_FALLBACK;
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
          setMeta(file?.content ? parseFrontmatter(file.content) : {});
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

  const isEmpty = !meta || Object.keys(meta).length === 0 || meta.pnl_30d_pct === undefined;
  const linkPath = `/files?path=${encodeURIComponent(path)}`;

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
          No performance data yet.{' '}
          <Link
            href="/work"
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Run a tracking task
          </Link>{' '}
          to begin accumulation.
        </p>
      </section>
    );
  }

  const pnl = meta.pnl_30d_pct ?? 0;
  const pnlPositive = pnl >= 0;
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
        {meta.generated_at && (
          <Link
            href={linkPath}
            className="text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
          >
            last reconciled {formatGeneratedAt(meta.generated_at)}
          </Link>
        )}
      </div>
      <div className="grid grid-cols-3 gap-6">
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
      <div className={`mt-1 flex items-baseline gap-1 text-2xl font-semibold ${color}`}>
        {Icon && <Icon className="h-4 w-4" />}
        <span>{value}</span>
      </div>
      {target && (
        <div className="mt-0.5 text-[11px] text-muted-foreground/70">{target}</div>
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
