/**
 * /program → /workspace-settings redirect stub (bookmark-safety).
 *
 * ADR-432 D2d (2026-07-09): the operator-facing Program PANE is RETIRED (zero
 * hired-program grants exist; activation has never fired). The `program` surface
 * is DORMANT (kernel_surfaces.py — no route/pane_of, like ADR-421's constitution
 * surfaces). This stub survives only for bookmark-safety and now lands on the
 * bare Workspace-Settings door (the ?pane=program target no longer exists). The
 * hire machinery is untouched; activation re-surfaces on /agents under ADR-382.
 * Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function ProgramRedirect() {
  redirect('/workspace-settings');
}
