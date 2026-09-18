'use client';

/**
 * /supervisor — the Supervisor app (ADR-656).
 *
 * Thin wrapper — the surface component owns everything; the window manager owns
 * the frame (window = surface, ADR-436). The route is a deep-link transport:
 * the real render happens in the viewport.
 */

import { SupervisorSurface } from '@/components/supervisor/SupervisorSurface';

export default function SupervisorPage() {
  return <SupervisorSurface />;
}
