/**
 * /billing → Workspace Settings → Billing redirect stub (ADR-491 D1,
 * 2026-07-28). Billing is a pane-grade surface on the workspace door
 * (authority-gated workspace governance); this stub gives it a bookmarkable
 * route, matching the /autonomy pattern. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BillingRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=billing');
}
