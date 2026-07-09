/**
 * /budget → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Budget is a governance/ GRANT — the spend ceiling the agent runs under
 * (ADR-366). ADR-426 (2026-07-09): the System Agent group carved out of
 * Workspace Settings into its own door (/system-agent), so this stub retargets
 * there. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/system-agent?system-agent.pane=budget');
}
