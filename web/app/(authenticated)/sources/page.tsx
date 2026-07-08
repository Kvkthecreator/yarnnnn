/**
 * /sources → /workspace-settings?workspace-settings.pane=sources stub.
 *
 * ADR-415 (2026-07-08): the Channels surface dissolved; Perception (Connectors
 * · Sources) re-homed to Workspace Settings → Perception (a management pane,
 * always-present). The `sources` door lands there. Pure server transport per
 * ADR-308.
 *
 * (Lineage: ADR-341 → Workspace-Settings; ADR-385 → Channels; ADR-415 → back
 * to Workspace Settings.)
 */

import { redirect } from 'next/navigation';

export default function SourcesRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=sources');
}
