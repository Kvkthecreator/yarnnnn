'use client';

/**
 * BudgetStatusItem — the merged MONEY chip in the agent-OS menu-bar
 * status cluster (ADR-327, supersedes PaceStatusItem; ADR-340 P1,
 * absorbs BalanceStatusItem).
 *
 * One chip answers the operator's money question whole: the declared
 * spend envelope (budget window, observed burn, runway) PAIRED with the
 * account funds that back it (balance, spend to date). ADR-327 D8's own
 * logic ("the budget is only honest paired with where-it-went") extends
 * to funds — runway is only honest as envelope paired with balance.
 * Pre-ADR-340 these were two adjacent chips (wallet + credit card);
 * the redundancy was an operator-flagged finding in the ADR-340
 * discourse.
 *
 * Consumes api.budget() + api.integrations.getLimits(). Read-only
 * popover — a GLANCE (standing state), not a config hub. The ONE footer
 * link opens the /budget surface (the operation's envelope). Billing
 * (top-up, subscription) is account config — it lives on the Budget pane
 * itself (BudgetCard "Balance & billing →") and the UserMenu account
 * window, NOT on this menu-bar glance (2026-06-19; ADR-347 account/operation
 * split). A glance routes to one surface; it is not a settings map.
 *
 * Icon discipline (ADR-297 D20): the chip icon is the canonical /budget
 * surface icon resolved via `resolveSurfaceIcon('wallet')` — same glyph
 * as the Dock and Launcher. Singular Implementation: one icon per
 * surface; the CreditCard glyph retired with the absorbed chip.
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
  daily_burn_usd?: number | null;
  runway_days?: number | null;
}

interface BalanceState {
  balance_usd: number;
  spend_usd: number;
  is_subscriber: boolean;
  subscription_plan: string | null;
  next_refill: string | null;
}

const WINDOW_LABEL: Record<BudgetState['window'], string> = {
  monthly: 'this month',
  weekly: 'this week',
  daily: 'today',
};

const LOW_BALANCE_THRESHOLD_USD = 1.0;
const CRITICAL_BALANCE_THRESHOLD_USD = 0.25;

const REFRESH_INTERVAL_MS = 30_000;

export function BudgetStatusItem() {
  const [budget, setBudget] = useState<BudgetState | null>(null);
  const [balance, setBalance] = useState<BalanceState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchMoney = async () => {
      const [budgetResult, balanceResult] = await Promise.allSettled([
        api.budget(),
        api.integrations.getLimits(),
      ]);
      if (cancelled) return;
      if (budgetResult.status === 'fulfilled') setBudget(budgetResult.value as BudgetState);
      if (balanceResult.status === 'fulfilled') setBalance(balanceResult.value as BalanceState);
      setLoading(false);
    };

    fetchMoney();
    const interval = setInterval(fetchMoney, REFRESH_INTERVAL_MS);
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

  const pct = budget && budget.amount_usd > 0
    ? Math.min(100, Math.round((budget.window_spend_usd / budget.amount_usd) * 100))
    : 0;
  const balanceLow = balance != null && balance.balance_usd <= LOW_BALANCE_THRESHOLD_USD;
  const balanceCritical = balance != null && balance.balance_usd <= CRITICAL_BALANCE_THRESHOLD_USD;
  // Tone: balance trouble dominates (funds gate everything); then the
  // envelope filling; ok/muted otherwise.
  const tone: StatusTone = balanceCritical || balanceLow
    ? 'warn'
    : !budget
      ? 'muted'
      : pct >= 90
        ? 'warn'
        : pct >= 70
          ? 'ok'
          : 'muted';

  const balanceLabel = balance ? `$${balance.balance_usd.toFixed(2)}` : null;
  const tooltipParts: string[] = [];
  if (budget) {
    tooltipParts.push(
      `Budget: $${budget.window_spend_usd.toFixed(0)} / $${budget.amount_usd.toFixed(0)} ${WINDOW_LABEL[budget.window]}`,
    );
  }
  if (balanceLabel) {
    tooltipParts.push(`Balance: ${balanceLabel}${balance?.is_subscriber ? ' (Pro)' : ''}`);
  }
  const tooltip = tooltipParts.length > 0 ? tooltipParts.join(' · ') : 'Budget not set';

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <BudgetIcon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">
        {budget ? `$${budget.window_spend_usd.toFixed(2)} of $${budget.amount_usd.toFixed(2)}` : 'Budget not set'}
        {budget && <span className="text-muted-foreground"> {WINDOW_LABEL[budget.window]}</span>}
      </span>
      {balanceLabel && (
        <span className="ml-auto text-xs text-muted-foreground font-mono">{balanceLabel}</span>
      )}
    </div>
  );

  const popoverBody = (
    <div className="space-y-1.5 text-muted-foreground text-xs">
      {budget ? (
        <>
          <div className="h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
            <div
              className={pct >= 90 ? 'h-full rounded-full bg-destructive' : pct >= 70 ? 'h-full rounded-full bg-amber-500' : 'h-full rounded-full bg-primary'}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between pt-0.5">
            <span>Remaining {WINDOW_LABEL[budget.window]}</span>
            <span className="font-mono">${budget.remaining_usd.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Pending wakes</span>
            <span className="font-mono">{budget.queue_depth}</span>
          </div>
          {budget.runway_days != null && (
            <div className="flex justify-between">
              <span>Runway at observed burn</span>
              <span className="font-mono">~{Math.round(budget.runway_days)}d</span>
            </div>
          )}
        </>
      ) : (
        <p>Operator has not declared a budget yet (kernel default $50/monthly applies).</p>
      )}

      {balance && (
        <div className="pt-1.5 mt-1.5 border-t border-border/60 space-y-0.5">
          {balanceCritical ? (
            <p className="text-amber-600 dark:text-amber-400">
              Balance is critical. Workspace will hard-stop when it reaches $0.
            </p>
          ) : balanceLow ? (
            <p className="text-amber-600 dark:text-amber-400">
              Balance is low. Consider topping up or activating Pro.
            </p>
          ) : null}
          <div className="flex justify-between">
            <span>
              Balance
              {balance.is_subscriber && <span className="text-muted-foreground"> · Pro</span>}
            </span>
            <span className="font-mono">${balance.balance_usd.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Spend to date</span>
            <span className="font-mono">${balance.spend_usd.toFixed(2)}</span>
          </div>
          {balance.next_refill && (
            <div className="flex justify-between">
              <span>Next refill</span>
              <span className="font-mono text-[10px]">
                {new Date(balance.next_refill).toLocaleDateString([], { month: 'short', day: 'numeric' })}
              </span>
            </div>
          )}
        </div>
      )}

      <p className="pt-1">
        Balance funds Reviewer wakes + agent execution; the Reviewer
        allocates wakes within the declared envelope.
      </p>
    </div>
  );

  return (
    <StatusItemPopover
      icon={BudgetIcon}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Budget, balance, and wake queue"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'surface', slug: 'budget' }}
      footerLabel="Budget Settings"
    />
  );
}
