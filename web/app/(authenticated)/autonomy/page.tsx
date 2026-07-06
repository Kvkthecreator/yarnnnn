/**
 * /autonomy → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Autonomy (the Witness dial) is a governance/ GRANT — the delegation ceiling
 * the agent runs under (ADR-366). Post-ADR-412 D5 it lives in Workspace
 * Settings' System Agent group (Freddie left the /agents roster). This route is pure
 * server transport (ADR-308) — `redirect()`, never a client useEffect. The target carries the
 * window-namespaced pane param the Workspace Settings window reads.
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=autonomy');
}
