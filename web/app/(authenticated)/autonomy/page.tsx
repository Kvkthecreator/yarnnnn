/**
 * /autonomy → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Autonomy (the Witness dial) is a governance/ GRANT — the delegation ceiling
 * the agent runs under (ADR-366). Post-ADR-387 it lives on Freddie's pane (the
 * agents window), Grant group, not in Workspace Settings. This route is pure
 * server transport (ADR-308) — `redirect()`, never a client useEffect. The
 * target carries the window-namespaced params the agents window reads
 * (agents.agent selects Freddie; agents.pane selects the pane).
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/agents?agents.agent=freddie&agents.pane=autonomy');
}
