/**
 * /principles → Freddie's pane redirect stub (ADR-387 §6.4, 2026-06-30).
 *
 * Principles is the agent's persona/ judgment framework (persona/principles.md).
 * Post-ADR-412 D5 it lives in Workspace Settings' System Agent group
 * (Freddie left the /agents roster). Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function PrinciplesRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=principles');
}
