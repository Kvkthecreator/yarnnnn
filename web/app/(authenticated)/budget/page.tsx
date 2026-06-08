'use client';

/**
 * /budget — atomic Budget surface (ADR-327).
 *
 * Renders /workspace/governance/_budget.yaml via the kernel-library
 * BudgetCard (full variant). Budget is the Trigger-dimension dial of the
 * Budget + Autonomy + Identity operator trifecta — the operation's dollar
 * spend envelope. Supersedes the /pace surface (ADR-300): pace retired;
 * "how often the agent works" is the Reviewer's allocation problem within
 * this budget, not an operator dial.
 *
 * The card shows the declared envelope (amount + window, editable) AND
 * window-to-date utilization from GET /api/budget (the execution_events
 * cost ledger) — the budget is only honest paired with where-it-went
 * (ADR-327 D8).
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { BudgetCard } from '@/components/workspace-concepts/BudgetCard';

export default function BudgetPage() {
  return (
    <SurfacePage
      iconKey="wallet"
      title="Budget"
      summary="The operation's dollar spend envelope. The Reviewer allocates wakes within it — it decides how often to work; you decide how much it costs."
    >
      <BudgetCard variant="full" />
    </SurfacePage>
  );
}
