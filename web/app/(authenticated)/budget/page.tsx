/**
 * /budget → /workspace-settings?pane=budget redirect stub (ADR-347).
 *
 * Budget (Rhythm) is pane-grade — a Contract pane inside the ONE Settings
 * door (the operation's settings). ADR-347 moved it out of the dissolved
 * System Settings door into workspace-settings. BudgetCard rendering is
 * unchanged; only the parent door moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BudgetRedirect() {
  redirect('/workspace-settings?pane=budget');
}
