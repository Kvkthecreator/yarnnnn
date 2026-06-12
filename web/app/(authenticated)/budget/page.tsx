/**
 * /budget → /settings?pane=budget redirect stub (ADR-340 P2).
 *
 * Budget is pane-grade — a Governance pane inside the System Settings
 * window (the macOS one-door shape), no longer a window of its own. The
 * BudgetCard substrate rendering is unchanged; only the surface tier
 * moved. Pure server transport per ADR-308 — `redirect()`, never a
 * client-side useEffect redirect.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/settings?pane=budget');
}
