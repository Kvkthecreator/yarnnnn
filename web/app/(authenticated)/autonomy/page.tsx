/**
 * /autonomy → /settings?pane=autonomy redirect stub (ADR-340 P2).
 *
 * Autonomy is pane-grade — a Governance pane inside the System Settings
 * window, no longer a window of its own. The AutonomyCard substrate
 * rendering (confirm-gated mutations per the 2026-05-24 design polish)
 * is unchanged; only the surface tier moved. Pure server transport per
 * ADR-308.
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/settings?pane=autonomy');
}
