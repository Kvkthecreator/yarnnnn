/**
 * /autonomy → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Autonomy (the Witness dial) is a governance/ GRANT — the delegation ceiling
 * the agent runs under (ADR-366). ADR-426 (2026-07-09) carved the System Agent
 * group into its own door; ADR-454 D4 (2026-07-13) reversed it — the dial lives
 * in Workspace Settings → System now, so this stub retargets there. Pure server
 * transport (ADR-308) — `redirect()`, never a client useEffect. The target
 * carries the window-namespaced pane param the Workspace Settings window reads.
 */

import { redirect } from 'next/navigation';

export default function AutonomyRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=autonomy');
}
