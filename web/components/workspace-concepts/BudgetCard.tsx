'use client';

/**
 * BudgetCard — L3 component for /workspace/governance/_budget.yaml (ADR-327).
 *
 * Supersedes PaceCard. Pace retired — "how often the agent works" is the
 * Reviewer's allocation problem within the dollar budget, not an operator
 * dial. This card shows TWO things:
 *   1. The declared spend envelope (amount + window) — operator-editable.
 *   2. Window-to-date utilization ("$12 of $50 used, on pace") — read-only,
 *      from GET /api/budget (the execution_events cost ledger). The budget
 *      concept is only honest paired with the utilization view (ADR-327 D8).
 *
 * Window selection mutates via setBudget() (writeShape → governance file).
 * Amount edits route through chat (the escape hatch — V1 surface offers
 * window presets + a few amount presets; precise dollar amounts via chat).
 *
 * Variants:
 *   full    — /budget atomic surface (window control + amount presets + utilization)
 *   compact — context overlay (summary + utilization line)
 *   chip    — chat composer (amount badge only, read-only; deep-links to /budget)
 *
 * Budget is operator-only substrate per ADR-327 (governance/ root, locked
 * from the Reviewer per ADR-320). The Reviewer reads it; only the operator writes.
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
    description: 'The budget covers a calendar month. Absorbs day-to-day variance — the default.',
  },
  {
    value: 'weekly',
    label: 'Weekly',
    description: 'The budget resets each week. Tighter control; more frequent reset.',
  },
  {
    value: 'daily',
    label: 'Daily',
    description: 'The budget resets each day. Strictest cadence-cost control.',
  },
];

// Amount presets per window — operator picks one or edits precisely via chat.
const AMOUNT_PRESETS: Record<BudgetWindow, number[]> = {
  monthly: [30, 50, 100, 200],
  weekly: [10, 25, 50],
  daily: [2, 5, 10],
};

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
  const { meta, utilization, loading, summary, setBudget } = useCockpitBudget({ initialContent });
  const [pendingWindow, setPendingWindow] = useState<BudgetWindow | null>(null);

  const amount = meta?.amount_usd ?? utilization?.amount_usd ?? null;
  const window = meta?.window ?? utilization?.window ?? null;

  // ---- chip ----
  if (variant === 'chip') {
    if (loading || amount == null) return null;
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
          'bg-muted/60 text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
        title="Budget — click to manage"
      >
        <Wallet className="w-3 h-3" />
        ${amount}{window ? `/${window[0]}` : ''}
      </button>
    );
  }

  // ---- utilization line (shared by compact + full) ----
  // ADR-430/396: draw-down shown as a PERCENT of the declared envelope, never a
  // running dollar meter (the Claude-settings transparency pattern — activity is
  // legible, dollars are not surfaced here). The envelope itself is set in
  // dollars (declaring a budget is a dollar act); the SPEND is shown as %.
  const usedPct = utilization ? pct(utilization.window_spend_usd, utilization.amount_usd) : 0;
  const utilLine = utilization ? (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          {usedPct}% used ({budgetWindowLabel(utilization.window)})
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
  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <Wallet className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Budget</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium">{summary}</span>
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
          <p className="text-sm font-semibold">Allocation</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            The spend envelope for your agent over the window below. It allocates
            its own judgment wakes within this envelope — it decides how often to
            work; you decide how much it may cost (ADR-327).
          </p>
        </div>
        <RevisionFootnote revision={lastRevision ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-32 rounded-md bg-muted/30 animate-pulse" />
      ) : (
        <div className="space-y-4">
          {/* Utilization hero */}
          {utilLine && (
            <div className="rounded-lg border border-border/60 px-4 py-3">
              {utilLine}
            </div>
          )}

          {/* Amount presets for the current window */}
          {window && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Amount ({budgetWindowLabel(window)})
              </p>
              <div className="flex flex-wrap gap-2">
                {AMOUNT_PRESETS[window].map(a => (
                  <button
                    key={a}
                    type="button"
                    onClick={() => { if (a !== amount) void setBudget({ amount_usd: a }); }}
                    className={cn(
                      'rounded-md border px-3 py-1.5 text-sm transition-colors',
                      a === amount
                        ? 'border-primary/50 bg-primary/5 font-medium'
                        : 'border-border/60 hover:border-border hover:bg-muted/20',
                    )}
                  >
                    ${a}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground/60">
                Need a precise amount? Set it via chat — “set my budget to $X {budgetWindowLabel(window)}”.
              </p>
            </div>
          )}

          {/* Window selection */}
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

          {amount == null && (
            <p className="text-[11px] text-muted-foreground/60 px-1">
              No allocation declared — the kernel default ($50/monthly) applies until you set one.
            </p>
          )}

          {/* ADR-430 (2026-07-09): the "Balance & billing" link is REMOVED.
              Balance is the workspace's money (Layer ①, ADR-391 D3 — "not an
              agent concern") and lives on the Workspace Settings billing door
              (ADR-416), not on the steward's allocation dial. This pane is the
              allocation envelope alone. */}
        </div>
      )}

      <ConfirmDialChange
        open={pendingWindow !== null && pendingMeta !== undefined}
        dialName="budget window"
        fromLabel={currentWindowMeta?.label ?? 'unset'}
        toLabel={pendingMeta?.label ?? ''}
        consequence={
          `Spend will be measured ${pendingMeta ? budgetWindowLabel(pendingMeta.value) : ''} ` +
          `and reset at the start of each ${pendingWindow ?? ''} window. Your amount preset may need adjusting.`
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
