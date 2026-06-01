/**
 * /operation redirect stub.
 *
 * Pre-launch rename history: /operation → /workspace (ADR-244) → /mandate
 * (ADR-297). Current target: /mandate — the most-touched atomic governance
 * surface after the ADR-297 atomic-shell migration.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect().
 */

import { redirect } from 'next/navigation';

export default function OperationRedirect() {
  redirect('/mandate');
}
