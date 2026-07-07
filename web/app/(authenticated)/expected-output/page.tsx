/**
 * /expected-output → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Expected Output is the contract/ CONTRACT — what the operator declares the
 * agent owes (ADR-345/366). Post-ADR-412 D5 it lives in Workspace Settings'
 * System Agent group (Freddie left the /agents roster). Pure server transport
 * per ADR-308 — `redirect()`, never a client-side useEffect redirect.
 */

import { redirect } from 'next/navigation';

export default function ExpectedOutputRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=expected-output');
}
