/**
 * /program → /settings?pane=program redirect stub (ADR-340 P2).
 *
 * Program is pane-grade — the Program pane inside the System Settings
 * window (lifecycle + re-run-setup door), no longer a window of its
 * own. ProgramLifecycleDrawer + the workspace-state fetch moved into
 * the pane body (settings/page.tsx::ProgramPaneBody). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ProgramRedirect() {
  redirect('/settings?pane=program');
}
