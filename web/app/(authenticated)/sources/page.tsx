/**
 * /sources → /workspace-settings?pane=sources redirect stub.
 *
 * ADR-341 (2026-06-18): Sources is a Perception pane inside Workspace
 * Settings (the operation's standing-watch transports, ADR-338 D4.1),
 * re-homed from System Settings (ADR-340 P2). SourcesCard is unchanged;
 * only the door moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function SourcesRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=sources');
}
