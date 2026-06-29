/**
 * /connectors → /channels?channels.pane=connectors redirect stub.
 *
 * ADR-377 (2026-06-26): Connections re-homed to the perception surface (the
 * canonical place for platform connections + their freshness). ADR-385
 * (2026-06-29): that surface renamed `context` → `channels`. Workspace
 * Settings no longer carries connections at all (ADR-385 D4); the `connectors`
 * door lands on Channels' Connections pane. Pure server transport per ADR-308.
 *
 * (Prior: ADR-341 routed /connectors → Workspace-Settings → Perception pane.)
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/channels?channels.pane=connectors');
}
