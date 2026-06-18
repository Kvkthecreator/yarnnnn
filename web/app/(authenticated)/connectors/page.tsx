/**
 * /connectors → /workspace-settings?pane=connectors redirect stub.
 *
 * ADR-341 (2026-06-18): Connectors is a Perception pane inside Workspace
 * Settings (the operation's transports), re-homed from System Settings
 * (ADR-340 P2). ConnectedIntegrationsSection is unchanged; only the door
 * moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/workspace-settings?pane=connectors');
}
