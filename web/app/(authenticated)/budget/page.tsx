/**
 * /budget → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Budget (Rhythm) is a governance/ GRANT — the spend ceiling the agent runs
 * under (ADR-366). Post-ADR-387 it lives on Freddie's pane (the agents window),
 * Grant group, not in Workspace Settings. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/agents?agents.agent=freddie&agents.pane=budget');
}
