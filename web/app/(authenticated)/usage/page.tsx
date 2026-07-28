/**
 * /usage → Workspace Settings → Usage redirect stub (ADR-491 D1, 2026-07-28).
 * Usage is a pane-grade surface on the workspace door (member-visible
 * legibility; carries the dissolved Budget pane's runway line). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function UsageRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=usage');
}
