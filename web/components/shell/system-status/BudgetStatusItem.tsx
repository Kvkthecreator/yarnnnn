'use client';

/**
 * BudgetStatusItem — spend-envelope + wake-queue depth chip in the agent-OS
 * menu-bar status cluster (ADR-327, supersedes PaceStatusItem).
 *
 * Consumes api.budget(). Read-only popover; mutations happen on the /budget
 * atomic surface. Shows window-to-date spend against the declared envelope
 * (the budget is only honest paired with where-it-went, ADR-327 D8) + the
 * live queue depth.
 *
 * Icon discipline (ADR-297 D20): the chip icon is the canonical /budget
 * surface icon resolved via `resolveSurfaceIcon('wallet')` — same glyph as
 * the Dock and Launcher. Singular Implementation: one icon per surface.
 */

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';

interface BudgetState {
  amount_usd: number;
  window: 'monthly' | 'weekly' | 'daily';
  window_spend_usd: number;
  remaining_usd: number;
  per_wake_ceiling_usd: number;
  queue_depth: number;
}

const WINDOW_LABEL: Record<BudgetState['window'], string> = {
  monthly: 'this month',
  weekly: 'this week',
  daily: 'today',
};

const REFRESH_INTERVAL_MS = 30_000;

export function BudgetStatusItem() {
  const [state, setState] = useState<BudgetState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchBudget = async () => {
      try {
        const data = await api.budget();
        if (!cancelled) setState(data as BudgetState);
      } catch {
        // Soft-fail; popover shows skeleton-state
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchBudget();
    const interval = setInterval(fetchBudget, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="w-8 h-8 flex items-center justify-center text-muted-foreground" aria-hidden>
        <Loader2 className="w-3 h-3 animate-spin" />
      </div>
    );
  }

  const BudgetIcon = resolveSurfaceIcon('wallet');

  const pct = state && state.amount_usd > 0
    ? Math.min(100, Math.round((state.window_spend_usd / state.amount_usd) * 100))
    : 0;
  // Tone: warn as the envelope fills; ok otherwise.
  const tone: StatusTone = !state ? 'muted' : pct >= 90 ? 'warn' : pct >= 70 ? 'ok' : 'muted';

  const tooltip = state
    ? `Budget: $${state.window_spend_usd.toFixed(0)} / $${state.amount_usd.toFixed(0)} ${WINDOW_LABEL[state.window]}`
    : 'Budget not set';

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <BudgetIcon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">
        {state ? `$${state.window_spend_usd.toFixed(2)} of $${state.amount_usd.toFixed(2)}` : 'Not set'}
        {state && <span className="text-muted-foreground"> {WINDOW_LABEL[state.window]}</span>}
      </span>
    </div>
  );

  const popoverBody = state ? (
    <div className="space-y-1.5 text-muted-foreground text-xs">
      <div className="h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
        <div
          className={pct >= 90 ? 'h-full rounded-full bg-destructive' : pct >= 70 ? 'h-full rounded-full bg-amber-500' : 'h-full rounded-full bg-primary'}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between pt-0.5">
        <span>Remaining {WINDOW_LABEL[state.window]}</span>
        <span className="font-mono">${state.remaining_usd.toFixed(2)}</span>
      </div>
      <div className="flex justify-between">
        <span>Pending wakes</span>
        <span className="font-mono">{state.queue_depth}</span>
      </div>
      <p className="pt-1">
        The Reviewer allocates judgment wakes within this envelope — it decides
        how often to work; you decide how much it costs.
      </p>
    </div>
  ) : (
    <p className="text-muted-foreground text-xs">Operator has not declared a budget yet (kernel default $50/monthly applies).</p>
  );

  return (
    <StatusItemPopover
      icon={BudgetIcon}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Budget and wake queue"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'surface', slug: 'budget' }}
      footerLabel="Budget Settings"
    />
  );
}
