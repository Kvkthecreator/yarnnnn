/**
 * /identity → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Identity is the agent's persona/ reasoning-character (persona/IDENTITY.md —
 * the operator-identity already collapsed here per ADR-320 D2b). Post-ADR-387
 * it lives on Freddie's pane (the agents window), Persona group, not in
 * Workspace Settings. Pure server transport per ADR-308.
 *
 * NOTE: /brand no longer redirects here — Brand (operation/BRAND.md) stayed in
 * Workspace Settings (ADR-387 D3), so /brand points there directly.
 */

import { redirect } from 'next/navigation';

export default function IdentityRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=identity');
}
