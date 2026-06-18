/**
 * /backend redirect stub — renamed to /activity per ADR-265, then folded
 * into the Recurrence window's Runs lens per ADR-340 D8.
 *
 * "Backend" was engineer vocabulary; the page's actual operator job is
 * activity audit. ADR-340 D8 (2026-06-18) folded that audit to pane-grade
 * under Recurrence (the Runs lens). Repointed straight at the canonical
 * destination — no double redirect through the now-stub /activity.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell. A client stub paints one orphaned frame in
 * SurfaceViewport before redirecting (the bimodality seam); server
 * redirect() fires before any layout mounts.
 */

import { redirect } from 'next/navigation';

export default function BackendRedirect() {
  redirect('/recurrence?pane=activity');
}
