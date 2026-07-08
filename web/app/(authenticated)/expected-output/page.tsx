/**
 * /expected-output → Workspace Settings redirect stub.
 *
 * History: ADR-387 §6.4 homed this on Freddie's roster pane; ADR-412 D5 moved
 * it to Workspace Settings' System Agent group. ADR-418 (2026-07-08) made the
 * surface DORMANT — post ADR-414 D2/D6 the output contract is a HIRED
 * Altitude-3 agent's concern (ADR-408 D2 / ADR-382 §3), not the steward's, and
 * unlike identity/principles it has no constitution-band door, so it left the
 * navigable surface set (registry route="", off the FE allowlist). The
 * per-agent contract pane returns with the Altitude-3 FE (ADR-382 / ADR-414 §9b).
 *
 * This file stays only for BOOKMARK SAFETY: the old /expected-output URL resolves
 * to the one Settings door (landing on its default pane), never a dead route.
 * Pure server transport per ADR-308 — `redirect()`, never a client useEffect.
 */

import { redirect } from 'next/navigation';

export default function ExpectedOutputRedirect() {
  redirect('/workspace-settings');
}
