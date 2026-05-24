/**
 * /delegation — redirect stub (2026-05-24 surface rename).
 *
 * The surface renamed to /autonomy to align with the substrate file
 * (_autonomy.yaml) and the operator's mental model. The schema field
 * `default_delegation` stays — it's the precise data-layer term for the
 * delegated level. At the operator surface the broader concept is Autonomy.
 *
 * This stub preserves existing bookmarks + deep-links pointing to
 * /delegation; the route itself is no longer part of the launcher /
 * surface registry (see web/components/shell/SurfaceRegistry.tsx +
 * api/services/kernel_surfaces.py).
 *
 * Same pattern as /overview, /workfloor, /orchestrator, /tasks legacy
 * stubs.
 */

import { redirect } from 'next/navigation';

export default function DelegationRedirect() {
  redirect('/autonomy');
}
