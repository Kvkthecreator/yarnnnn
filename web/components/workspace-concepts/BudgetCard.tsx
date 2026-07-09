'use client';

/**
 * BudgetCard — the System Agent's PACE pane (ADR-433, reframing ADR-327/430).
 *
 * ADR-433 reversed ADR-430 D2: after the pooled-balance model (ADR-396/429), a
 * per-agent DOLLAR envelope is a second, fictional money number disconnected from
 * the operator's real money (the pooled balance on the billing door). So this
 * pane stops being a "spend envelope" dial and becomes Freddie's PACE surface:
 *   1. CONSUMPTION — a non-dollar draw-down (%) of the real pooled balance this
 *      window (ADR-396: dollars are not shown), framed as how hard Freddie is
 *      working, not as a budget.
 *   2. WINDOW — the measurement/reset window (Monthly/Weekly/Daily) over which
 *      consumption is read. Operator-editable (writes _budget.yaml::window).
 *   3. A pointer to the workspace BILLING door, where the actual money lives
 *      (ADR-416/391 D3 — money is the workspace's concern, not an agent dial).
 *
 * The dollar amount presets ($30/$50/$100/$200) are REMOVED (ADR-433 D1). The
 * `_budget.yaml::amount_usd` field survives as a backend runaway-safety envelope
 * (paired with per_wake_ceiling_usd), settable via chat as an escape hatch, but
 * is no longer a first-class operator dollar dial competing with the billing door.
 *
 * Variants:
 *   full    — the System Agent Budget pane (consumption + window + billing link)
 *   compact — context overlay (summary + consumption line)
 *   chip    — chat composer (read-only pace badge; deep-links to the pane)
 *
 * Substrate is operator-only per ADR-327 (governance/ root, locked from the
 * agent per ADR-320). The agent reads it; only the operator writes.
 */

import { useState } from 'react';
import { Wallet, ArrowRight } from 'lucide-react';
import {
  useCockpitBudget,
  budgetWindowLabel,
  BUDGET_WINDOWS,
  type BudgetWindow,
} from '@/lib/content-shapes/budget';
import { cn } from '@/lib/utils';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import type { WorkspaceRevisionSummary } from '@/types';
import { RevisionFootnote } from './RevisionFootnote';
import { ConfirmDialChange } from './ConfirmDialChange';

export type BudgetVariant = 'full' | 'compact' | 'chip';

interface BudgetCardProps {
  variant?: BudgetVariant;
  onOpen?: () => void;
  initialContent?: string | null;
  lastRevision?: WorkspaceRevisionSummary | null;
  className?: string;
}

const WINDOW_OPTIONS: {
  value: BudgetWindow;
  label: string;
  description: string;
}[] = [
  {
    value: 'monthly',
    label: 'Monthly',
    description: 'Read pace over a calendar month. Absorbs day-to-day variance — the default.',
  },
  {
    value: 'weekly',
    label: 'Weekly',
    description: 'Read pace over each week. A tighter, more frequent view.',
  },
  {
    value: 'daily',
    label: 'Daily',
    description: 'Read pace over each day. The tightest cadence view.',
  },
];

function pct(spend: number, amount: number): number {
  if (amount <= 0) return 0;
  return Math.min(100, Math.round((spend / amount) * 100));
}

// ADR-338 D4.4 — runway line. Frames observed draw-down as time remaining
// ("~12 days left at this pace"). Returns null when the backend has no burn
// signal yet (fresh window / zero spend) — runway only becomes honest once
// there's spend to project from. ADR-430/396: the DOLLAR burn figure is
// dropped — this door shows draw-down as time + %, never a running $ meter.
function runwayLine(u: {
  runway_days?: number | null;
  daily_burn_usd?: number | null;
}): React.ReactNode {
  if (u.runway_days == null || u.daily_burn_usd == null) return null;
  const days = u.runway_days;
  // Phrase the time horizon in the operator's terms.
  let horizon: string;
  if (days >= 999) horizon = 'plenty of runway at this pace';
  else if (days >= 60) horizon = `~${Math.round(days)} days left at this pace`;
  else if (days >= 1) horizon = `~${days.toFixed(days < 10 ? 1 : 0)} days left at this pace`;
  else horizon = 'less than a day left at this pace';
  const tone =
    days < 3
      ? 'text-destructive'
      : days < 14
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-muted-foreground/70';
  return <p className={cn('text-[11px]', tone)}>{horizon}</p>;
}

export function BudgetCard({
  variant = 'full',
  onOpen,
  initialContent,
  lastRevision,
  className,
}: BudgetCardProps) {
  const { meta, utilization, loading, setBudget } = useCockpitBudget({ initialContent });
  const { navigateToSurface } = useSurfacePreferences();
  const [pendingWindow, setPendingWindow] = useState<BudgetWindow | null>(null);

  const window = meta?.window ?? utilization?.window ?? null;

  // ---- chip ----
  // ADR-433 — the chip is a PACE badge, not a dollar figure. Shows how much of
  // the balance Freddie has drawn this window (%), never "$50/m".
  if (variant === 'chip') {
    if (loading || !utilization) return null;
    const chipPct = pct(
      utilization.window_spend_usd,
      utilization.effective_balance_usd != null
        ? utilization.window_spend_usd + utilization.effective_balance_usd
        : utilization.amount_usd,
    );
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
          'bg-muted/60 text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
        title="Pace — click to manage"
      >
        <Wallet className="w-3 h-3" />
        {chipPct}% drawn
      </button>
    );
  }

  // ---- consumption line (shared by compact + full) ----
  // ADR-433 D2 / ADR-396: draw-down shown as a PERCENT of the REAL pooled
  // balance drawn this window (never a dollar meter — the Claude-settings
  // transparency pattern). Denominator = window_spend + effective_balance (the
  // money that existed this window). Falls back to the envelope % only when the
  // balance signal is unavailable (a % is better than none), never to dollars.
  const consumptionBasis =
    utilization && utilization.effective_balance_usd != null
      ? utilization.window_spend_usd + utilization.effective_balance_usd
      : (utilization?.amount_usd ?? 0);
  const usedPct = utilization ? pct(utilization.window_spend_usd, consumptionBasis) : 0;
  const utilLine = utilization ? (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          {usedPct}% of balance drawn ({budgetWindowLabel(utilization.window)})
        </span>
        <span className="font-medium">{Math.max(0, 100 - usedPct)}% left</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            usedPct >= 90 ? 'bg-destructive' : usedPct >= 70 ? 'bg-amber-500' : 'bg-primary',
          )}
          style={{ width: `${usedPct}%` }}
        />
      </div>
      {/* ADR-338 D4.4 — runway: observed burn → time remaining. Null until
          there's enough spend this window to project. */}
      {runwayLine(utilization)}
      {utilization.queue_depth > 0 && (
        <p className="text-[11px] text-muted-foreground/70">
          {utilization.queue_depth} wake(s) pending in the queue
        </p>
      )}
    </div>
  ) : null;

  // ---- compact ----
  // ADR-433 — "Pace", not "Budget"; no dollar `summary` (that leaks $X/window).
  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <Wallet className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Pace</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium">
                {window ? `Read ${budgetWindowLabel(window)}` : 'Pace'}
              </span>
              {onOpen && (
                <button
                  type="button"
                  onClick={onOpen}
                  className="shrink-0 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Change <ArrowRight className="inline w-3 h-3" />
                </button>
              )}
            </div>
            {utilLine}
          </div>
        )}
      </div>
    );
  }

  // ---- full ----
  const pendingMeta = pendingWindow ? WINDOW_OPTIONS.find(o => o.value === pendingWindow) : null;
  const currentWindowMeta = window ? WINDOW_OPTIONS.find(o => o.value === window) : null;

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Pace</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            How hard your agent works — it allocates its own judgment wakes and
            decides how often to act. This shows how much of the workspace balance
            it&rsquo;s drawing over the window below. The money itself lives on the
            workspace&rsquo;s billing.
          </p>
        </div>
        <RevisionFootnote revision={lastRevision ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-32 rounded-md bg-muted/30 animate-pulse" />
      ) : (
        <div className="space-y-4">
          {/* Consumption hero — non-dollar draw-down of the pooled balance */}
          {utilLine && (
            <div className="rounded-lg border border-border/60 px-4 py-3">
              {utilLine}
            </div>
          )}

          {/* Measurement window — over what period Freddie's pace is read. */}
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Window
            </p>
            {WINDOW_OPTIONS.map(opt => {
              const isActive = window === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => { if (opt.value !== window) setPendingWindow(opt.value); }}
                  className={cn(
                    'w-full text-left rounded-lg border px-4 py-3 transition-colors',
                    isActive
                      ? 'border-primary/50 bg-primary/5'
                      : 'border-border/60 hover:border-border hover:bg-muted/20',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-3.5 w-3.5 rounded-full border-2 shrink-0 transition-colors',
                      isActive ? 'border-primary bg-primary' : 'border-border',
                    )} />
                    <span className="text-sm font-medium">{opt.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 ml-5.5">{opt.description}</p>
                </button>
              );
            })}
          </div>

          {/* ADR-433 D2 — the money lives on the billing door, not here. A
              pointer, not a second money surface (ADR-391 D3 / ADR-416). Uses
              the same committed target as AttentionCenter (settings → billing). */}
          <button
            type="button"
            onClick={() => navigateToSurface('settings', { pane: 'billing' })}
            className="flex w-full items-center justify-between rounded-lg border border-border/60 px-4 py-3 text-left transition-colors hover:border-border hover:bg-muted/20"
          >
            <span className="text-sm">
              <span className="font-medium">Workspace balance</span>
              <span className="text-muted-foreground"> — top up, plan, and spend</span>
            </span>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        </div>
      )}

      <ConfirmDialChange
        open={pendingWindow !== null && pendingMeta !== undefined}
        dialName="window"
        fromLabel={currentWindowMeta?.label ?? 'unset'}
        toLabel={pendingMeta?.label ?? ''}
        consequence={
          `Freddie's pace will be read ${pendingMeta ? budgetWindowLabel(pendingMeta.value) : ''}, ` +
          `resetting at the start of each ${pendingWindow ?? ''} window.`
        }
        onCancel={() => setPendingWindow(null)}
        onConfirm={async () => {
          if (!pendingWindow) return;
          const next = pendingWindow;
          setPendingWindow(null);
          await setBudget({ window: next });
        }}
      />
    </div>
  );
}
