/**
 * /mandate → /workspace-settings redirect stub (bookmark safety only).
 *
 * ADR-421 (2026-07-08): a workspace has no constitution of its own — the
 * Mandate pane was removed (a mandate is a hired agent's declared intent,
 * surfaced on the agent detail via AgentConstitutionBlock, ADR-419). The old
 * URL resolves to the Settings door's default pane, never a dead route. Pure
 * server transport per ADR-308 — `redirect()`, never a client useEffect.
 */

import { redirect } from 'next/navigation';

export default function MandateRedirect() {
  redirect('/workspace-settings');
}
