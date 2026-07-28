/**
 * /budget → Usage redirect stub (ADR-491 D3, 2026-07-28).
 *
 * The Budget pane is DISSOLVED (completing ADR-433): its numbers — % of
 * balance drawn + runway — live on Workspace Settings → Usage now, beside the
 * meter they qualify. governance/_budget.yaml stays the machine-owned runaway
 * envelope (services/budget.py), not an operator dial. This stub keeps
 * /budget (and the /pace → /budget chain) bookmark-safe. Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=usage');
}
