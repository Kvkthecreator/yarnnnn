/**
 * /sources → /settings?pane=sources redirect stub (ADR-340 P2).
 *
 * Sources is pane-grade — a Perception & transports pane inside the
 * System Settings window (the standing-watch drivers view, ADR-338
 * D4.1), no longer a window of its own. SourcesCard is unchanged; only
 * the surface tier moved. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function SourcesRedirect() {
  redirect('/settings?pane=sources');
}
