/**
 * /connectors → /context?context.pane=connections redirect stub.
 *
 * ADR-377 (2026-06-26): Connections re-homed to Context (the perception
 * home) — the canonical place for platform connections + their freshness.
 * Workspace Settings keeps only a thin pointer; the `connectors` door now
 * lands on Context's Connections pane. Pure server transport per ADR-308.
 *
 * (Prior: ADR-341 routed /connectors → Workspace-Settings → Perception pane.)
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/context?context.pane=connections');
}
