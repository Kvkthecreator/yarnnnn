/**
 * /radar → /files redirect stub (ADR-592).
 *
 * The Radar app is DELETED (ADR-486 withdrawn 2026-08-21) — its surface,
 * router, service and scheduler lane are gone. This stub preserves bookmarks
 * and, more importantly, keeps the path AUTHENTICATED: middleware derives its
 * protected set from the served surface roster, so a slug that leaves the
 * roster leaves the gate with it, and a route that still rendered would serve
 * 200 to logged-out visitors (the defect repaired 2026-08-20).
 *
 * Files is the destination because the briefs Radar authored remain there, as
 * ordinary attributed files under operation/{topic}/briefs/.
 *
 * Pure server transport per ADR-308 — `redirect()`, never a client-side
 * useEffect redirect (which would paint an orphaned frame inside the shell).
 */

import { redirect } from 'next/navigation';

export default function RadarRedirect() {
  redirect('/files');
}
