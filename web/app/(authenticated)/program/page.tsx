/**
 * /program → /workspace-settings?pane=program redirect stub.
 *
 * ADR-341 (2026-06-18): Program is the Operation pane inside Workspace
 * Settings (lifecycle + re-run-setup door), re-homed from System
 * Settings (ADR-340 P2). ProgramLifecycleDrawer + the workspace-state
 * fetch live in the pane body (workspace-settings/page.tsx). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ProgramRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=program');
}
