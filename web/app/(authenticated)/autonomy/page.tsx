/**
 * /autonomy → /workspace-settings?pane=autonomy redirect stub (ADR-347).
 *
 * Autonomy (Witness dial) is pane-grade — a Contract pane inside the ONE
 * Settings door (the operation's settings). ADR-347 moved it out of the
 * dissolved System Settings door into workspace-settings. AutonomyCard
 * rendering (confirm-gated mutations) is unchanged; only the parent door
 * moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=autonomy');
}
