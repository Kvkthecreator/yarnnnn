'use client';

/**
 * BalanceStatusItem — workspace balance chip in the agent-OS menu-bar
 * status cluster (ADR-297 D20, slot 3).
 *
 * Consumes api.integrations.getLimits(). Read-only popover; mutations
 * (top-up, subscription) happen on /settings?tab=billing.
 *
 * Replaces the balance display in UserMenu's dropdown header — the
 * balance indicator moves from a click-to-see-it spot in the account
 * menu to an always-visible chip in kernel chrome. Macros (battery
 * analog): runway state is operator-critical, deserves persistent
 * visibility.
 */

import { useEffect, useState } from 'react';
import { Zap, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';

interface BalanceState {
  balance_usd: number;
  spend_usd: number;
  is_subscriber: boolean;
  subscription_plan: string | null;
  next_refill: string | null;
}

const LOW_BALANCE_THRESHOLD_USD = 1.0;
const CRITICAL_BALANCE_THRESHOLD_USD = 0.25;

export function BalanceStatusItem() {
  const [state, setState] = useState<BalanceState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.integrations
      .getLimits()
      .then((data) => {
        if (!cancelled) setState(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="w-8 h-8 flex items-center justify-center text-muted-foreground" aria-hidden>
        <Loader2 className="w-3 h-3 animate-spin" />
      </div>
    );
  }

  if (!state) {
    return <div className="w-8 h-8" aria-hidden />;
  }

  const balance = state.balance_usd;
  const tone: StatusTone =
    balance <= CRITICAL_BALANCE_THRESHOLD_USD
      ? 'warn'
      : balance <= LOW_BALANCE_THRESHOLD_USD
        ? 'warn'
        : 'ok';

  const balanceLabel = `$${balance.toFixed(2)}`;
  const tooltip = state.is_subscriber
    ? `Balance: ${balanceLabel} (Pro)`
    : `Balance: ${balanceLabel}`;

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <Zap className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">{balanceLabel}</span>
      {state.is_subscriber && (
        <span className="text-xs text-muted-foreground">· Pro</span>
      )}
    </div>
  );

  const popoverBody = (
    <div className="space-y-1 text-muted-foreground text-xs">
      {balance <= CRITICAL_BALANCE_THRESHOLD_USD ? (
        <p className="text-amber-600 dark:text-amber-400">
          Balance is critical. Workspace will hard-stop when it reaches $0.
        </p>
      ) : balance <= LOW_BALANCE_THRESHOLD_USD ? (
        <p className="text-amber-600 dark:text-amber-400">
          Balance is low. Consider topping up or activating Pro.
        </p>
      ) : (
        <p>Balance funds Reviewer wakes + agent execution.</p>
      )}
      <div className="pt-1 space-y-0.5">
        <div className="flex justify-between">
          <span>Spend to date</span>
          <span className="font-mono">${state.spend_usd.toFixed(2)}</span>
        </div>
        {state.next_refill && (
          <div className="flex justify-between">
            <span>Next refill</span>
            <span className="font-mono text-[10px]">
              {new Date(state.next_refill).toLocaleDateString([], { month: 'short', day: 'numeric' })}
            </span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <StatusItemPopover
      icon={Zap}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Workspace balance"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'route', href: '/settings?tab=billing' }}
      footerLabel="Billing Settings"
    />
  );
}
