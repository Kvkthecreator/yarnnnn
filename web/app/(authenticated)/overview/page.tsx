/**
 * /overview — redirect stub (ADR-205 F2).
 *
 * The Overview surface dissolved into /work's cockpit zone (ADR-205 F2);
 * since ADR-225 Phase 3 the cockpit panes flow through the compositor
 * via web/components/library/CockpitRenderer.tsx. This stub preserves
 * existing bookmarks and deep-links that still point to /overview; the
 * route itself is no longer part of the nav (see
 * web/components/shell/ToggleBar.tsx).
 *
 * Follows the same pattern as /workfloor, /orchestrator, /tasks legacy stubs
 * documented in web/lib/supabase/middleware.ts.
 */

import { redirect } from 'next/navigation';
import { WORK_ROUTE } from '@/lib/routes';

export default function OverviewRedirect() {
  redirect(WORK_ROUTE);
}
