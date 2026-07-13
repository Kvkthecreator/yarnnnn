/**
 * /budget → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Budget is a governance/ GRANT — the spend ceiling the agent runs under
 * (ADR-366). ADR-426 (2026-07-09) carved the System Agent group into its own
 * door; ADR-454 D4 (2026-07-13) reversed it — the dial lives in Workspace
 * Settings → System now, so this stub retargets there. Pure server transport
 * per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=budget');
}
