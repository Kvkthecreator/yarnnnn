/**
 * /principles → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Principles is the agent's persona/ judgment framework (persona/principles.md).
 * Post-ADR-387 it lives on Freddie's pane (the agents window), Persona group,
 * not in Workspace Settings. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function PrinciplesRedirect() {
  redirect('/agents?agents.agent=freddie&agents.pane=principles');
}
