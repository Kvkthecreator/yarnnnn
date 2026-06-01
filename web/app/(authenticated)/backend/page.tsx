/**
 * /backend redirect stub — renamed to /activity per ADR-265.
 *
 * "Backend" was engineer vocabulary; the page's actual operator job is
 * activity audit. Renamed to /activity to match the operator's mental model.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell. A client stub paints one orphaned frame in
 * SurfaceViewport before redirecting (the bimodality seam); server
 * redirect() fires before any layout mounts.
 */

import { redirect } from 'next/navigation';

export default function BackendRedirect() {
  redirect('/activity');
}
