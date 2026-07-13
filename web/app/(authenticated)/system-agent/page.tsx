/**
 * /system-agent → redirect stub (ADR-454 D4, 2026-07-13 — the ambient steward).
 *
 * The ADR-426 "Freddie System Agent" door is REVERSED: the steward's two dials
 * (Autonomy · Budget) re-homed to Workspace Settings as the unbranded System
 * group; the persona panes (About · Activity) are dormant-retained in
 * SystemAgentPanes pending the narrative-posture regroup. This route is pure
 * server transport (ADR-308) for bookmark safety — `redirect()`, never a
 * client useEffect. The target carries the window-namespaced pane param the
 * Workspace Settings window reads.
 */

import { redirect } from 'next/navigation';

export default function SystemAgentRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=autonomy');
}
