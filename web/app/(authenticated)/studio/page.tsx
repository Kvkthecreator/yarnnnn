'use client';

/**
 * /studio — the Studio surface route (ADR-440).
 *
 * The first authoring app: a bound lane (left) authors one HTML artifact
 * while the canvas (right) renders it live. Thin wrapper — the surface
 * component owns everything; the window manager owns the frame
 * (window = surface, ADR-436).
 */

import { StudioSurface } from '@/components/studio/StudioSurface';

export default function StudioPage() {
  return <StudioSurface />;
}
