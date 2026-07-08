/**
 * /identity → /workspace-settings redirect stub (bookmark safety only).
 *
 * ADR-421 (2026-07-08): a workspace has no persona of its own — the Identity
 * pane was removed (persona is the steward's kernel constant or a hired agent's
 * agents/{slug}/IDENTITY.md, surfaced on the agent detail via
 * AgentConstitutionBlock, ADR-419). The old URL resolves to the Settings door's
 * default pane, never a dead route. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function IdentityRedirect() {
  redirect('/workspace-settings');
}
