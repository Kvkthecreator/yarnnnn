'use client';

/**
 * TraderRegime — alpha-trader program section (order: 1 post-ADR-273).
 *
 * Thin one-line headline at the top of the program section stack —
 * tells the operator what the tape is doing today. Single sentence,
 * high signal-to-pixel.
 *
 * Data: api.cockpit.regime() → /workspace/context/trading/_regime.yaml
 *       (written by the TrackRegime primitive per ADR-271 Thread A).
 *
 * The regime predicate has two axes:
 *   - trend_regime — 'uptrend' | 'downtrend' | 'chop' from SPY SMAs
 *   - vix_regime_active — bool from VIXY threshold
 *
 * Visual: borderless thin strip; one line; no card chrome. Two color
 * tones depending on tape posture (uptrend + vix-quiet → muted green;
 * downtrend or vix-active → muted amber; otherwise muted slate).
 *
 * Empty state per ADR-273 D6: "Regime tracker hasn't fired yet — paused
 * or first run pending" with a deep-link to the recurrence detail.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Regime = Awaited<ReturnType<typeof api.cockpit.regime>>;

function describeRegime(r: Regime): { headline: string; tone: 'risk-on' | 'risk-off' | 'neutral' } {
  if (!r.trend_regime) return { headline: 'No regime read', tone: 'neutral' };
  const trend = r.trend_regime;
  const vixActive = !!r.vix_regime_active;

  if (trend === 'uptrend' && !vixActive) {
    return { headline: 'Risk-on · SPY uptrend, VIX quiet', tone: 'risk-on' };
  }
  if (trend === 'downtrend' || vixActive) {
    const parts: string[] = [];
    if (trend === 'downtrend') parts.push('SPY downtrend');
    if (vixActive) parts.push('VIX elevated');
    return { headline: `Risk-off · ${parts.join(', ')}`, tone: 'risk-off' };
  }
  return { headline: `Neutral · SPY ${trend}, VIX quiet`, tone: 'neutral' };
}

function formatTimestamp(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diff = Math.floor((Date.now() - d.getTime()) / 60_000);
  if (diff < 60) return `${diff}m ago`;
  if (diff < 60 * 24) return `${Math.floor(diff / 60)}h ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const TONE_CLS: Record<'risk-on' | 'risk-off' | 'neutral', string> = {
  'risk-on':  'border-emerald-200 bg-emerald-50/40 text-emerald-900',
  'risk-off': 'border-amber-200 bg-amber-50/40 text-amber-900',
  'neutral':  'border-border bg-card text-foreground',
};

export function TraderRegime() {
  const [data, setData] = useState<Regime | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.cockpit.regime();
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setData({ live: false, fallback_reason: 'read_failed' });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <section className="rounded-md border border-border bg-card px-3 py-2 flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        <span className="text-[11px] text-muted-foreground">Reading regime…</span>
      </section>
    );
  }

  if (!data || !data.live) {
    return (
      <section className="rounded-md border border-dashed border-border bg-muted/20 px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <AlertCircle className="h-3 w-3" />
          <span>
            Regime tracker hasn't fired yet — paused or first run pending.
          </span>
        </div>
        <Link
          href="/cadence?task=track-regime"
          className="text-[11px] text-muted-foreground/70 underline-offset-4 hover:text-foreground hover:underline"
        >
          View tracker →
        </Link>
      </section>
    );
  }

  const { headline, tone } = describeRegime(data);
  const stale = data.data_stale;

  return (
    <section className={cn(
      'rounded-md border px-3 py-2 flex items-center justify-between gap-3',
      TONE_CLS[tone],
    )}>
      <div className="flex items-center gap-2 text-[13px] font-medium">
        <Activity className="h-3.5 w-3.5" />
        <span>{headline}</span>
        {stale && (
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 text-amber-900">
            stale
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground/70">
        {data.spy_close != null && (
          <span className="tabular-nums">SPY ${data.spy_close.toFixed(2)}</span>
        )}
        {data.vixy_close != null && (
          <span className="tabular-nums">VIXY ${data.vixy_close.toFixed(2)}</span>
        )}
        <span>{formatTimestamp(data.as_of)}</span>
      </div>
    </section>
  );
}
