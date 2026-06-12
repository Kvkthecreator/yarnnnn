/**
 * /connectors → /settings?pane=connectors redirect stub (ADR-340 P2).
 *
 * Connectors is pane-grade — a Perception & transports pane inside the
 * System Settings window (the drivers view, ADR-338 D2), no longer a
 * window of its own. ConnectedIntegrationsSection is unchanged; only
 * the surface tier moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/settings?pane=connectors');
}
