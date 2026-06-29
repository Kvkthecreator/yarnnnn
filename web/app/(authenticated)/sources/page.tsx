/**
 * /sources → /channels?channels.pane=sources redirect stub.
 *
 * ADR-385 (2026-06-29): Perception leaves Workspace Settings entirely —
 * Sources (the operation's standing-watch transports, ADR-338 D4.1) is now a
 * pane on the Channels surface (the perception home). SourcesCard is unchanged;
 * only the door moved. Pure server transport per ADR-308.
 *
 * (Prior: ADR-341 routed /sources → Workspace-Settings → Perception pane.)
 */

import { redirect } from 'next/navigation';

export default function SourcesRedirect() {
  redirect('/channels?channels.pane=sources');
}
