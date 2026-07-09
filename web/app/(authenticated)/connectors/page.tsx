/**
 * /connectors → /settings?settings.pane=connectors stub.
 *
 * ADR-425 (2026-07-09): a platform credential is a human's ACCOUNT object, so
 * the Connectors pane lives in the account door (the `settings` window the
 * UserMenu opens), not Workspace Settings. Pure server transport per ADR-308.
 *
 * (Lineage: ADR-341 → Workspace-Settings; ADR-377/385 → Channels; ADR-415 →
 * back to Workspace Settings; ADR-425 → the account door.)
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/settings?settings.pane=connectors');
}
