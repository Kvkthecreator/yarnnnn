/**
 * /expected-output → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Expected Output is the contract/ CONTRACT — what the operator declares the
 * agent owes (ADR-345/366). Post-ADR-387 it lives on Freddie's pane (the agents
 * window), Contract group, not in Workspace Settings. Pure server transport per
 * ADR-308 — `redirect()`, never a client-side useEffect redirect.
 */

import { redirect } from 'next/navigation';

export default function ExpectedOutputRedirect() {
  redirect('/agents?agents.agent=freddie&agents.pane=expected-output');
}
