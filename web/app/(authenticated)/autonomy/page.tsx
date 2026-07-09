/**
 * /autonomy → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Autonomy (the Witness dial) is a governance/ GRANT — the delegation ceiling
 * the agent runs under (ADR-366). ADR-426 (2026-07-09): the System Agent group
 * carved out of Workspace Settings into its own door (/system-agent), so this
 * stub retargets there. This route is pure server transport (ADR-308) —
 * `redirect()`, never a client useEffect. The target carries the
 * window-namespaced pane param the Freddie System Agent window reads.
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/system-agent?system-agent.pane=autonomy');
}
