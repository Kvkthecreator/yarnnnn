/**
 * /brand redirect stub.
 *
 * ADR-309 (2026-06-01): `brand` is no longer a kernel surface slug. The /brand
 * URL survives only as bookmark-safety transport.
 *
 * ADR-387 §6.4 (2026-06-30): Identity moved to Freddie's pane, but Brand
 * (operation/BRAND.md) STAYED in Workspace Settings (ADR-387 D3 — it is
 * operation/-rooted output styling, not the agent's reasoning-character). So
 * /brand now points at the Workspace-Settings Brand pane directly, no longer at
 * /identity (which goes to Freddie). Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function BrandRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=brand');
}
