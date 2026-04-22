/**
 * /overview — redirect stub (ADR-205 F2).
 *
 * The Overview surface dissolved into /work as a BriefingStrip component
 * (see web/components/work/briefing/BriefingStrip.tsx). This stub preserves
 * existing bookmarks and deep-links that still point to /overview; the route
 * itself is no longer part of the nav (see web/components/shell/ToggleBar.tsx).
 *
 * Follows the same pattern as /workfloor, /orchestrator, /tasks legacy stubs
 * documented in web/lib/supabase/middleware.ts.
 */

import { redirect } from 'next/navigation';
import { WORK_ROUTE } from '@/lib/routes';

export default function OverviewRedirect() {
  redirect(WORK_ROUTE);
}
