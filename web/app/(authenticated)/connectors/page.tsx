/**
 * /connectors → /reach?reach.pane=connected stub.
 *
 * ADR-645 D3 (2026-09-08): connection management moved to Reach → Connected,
 * the boundary's own surface. Three of the four connection decisions (which
 * sources this workspace reads, the per-tool aperture, agent scope) are
 * WORKSPACE decisions that were wearing a Settings costume; sending a member
 * out of the boundary surface to make a boundary decision institutionalised
 * that. Settings → Connectors is deleted, not mirrored (Singular
 * Implementation) — this stub is the only survivor, and it exists for
 * bookmarks and for the ADR-592 obligation (a slug off the roster keeps its
 * auth gate via the hand-listed middleware entry).
 *
 * Pure server transport per ADR-308 — `redirect()`, never a client useEffect.
 *
 * (Lineage: ADR-341 → Workspace-Settings; ADR-377/385 → Channels; ADR-415 →
 * back to Workspace Settings; ADR-425 → the account door; ADR-645 → Reach.)
 */

import { redirect } from 'next/navigation';

export default function ConnectorsRedirect() {
  redirect('/reach?reach.pane=connected');
}
