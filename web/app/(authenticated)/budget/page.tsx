/**
 * /budget → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Budget (Rhythm) is a governance/ GRANT — the spend ceiling the agent runs
 * under (ADR-366). Post-ADR-412 D5 it lives in Workspace Settings'
 * System Agent group (Freddie left the /agents roster). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=budget');
}
