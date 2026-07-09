/**
 * /sources → /home stub.
 *
 * ADR-425 D2 (2026-07-09): Sources is hidden from the operator surface — it has
 * no pane home. The bookmark-safe route lands on Home. The SourcesCard + GET
 * /api/sources substrate are retained for a future first-class home (ADR-425
 * OQ3). Pure server transport per ADR-308.
 *
 * (Lineage: ADR-341 → Workspace-Settings; ADR-385 → Channels; ADR-415 → back to
 * Workspace Settings; ADR-425 → hidden.)
 */

import { redirect } from 'next/navigation';

export default function SourcesRedirect() {
  redirect('/home');
}
