'use client';

/**
 * /slides — the Slides surface route (ADR-440 Studio → ADR-599 the full
 * evolve: the dedicated deck app; the `web` type and the Docs sibling are
 * deleted, the deck is the one medium).
 *
 * Thin wrapper — the surface component owns everything; the window manager
 * owns the frame (window = surface, ADR-436). The component keeps its
 * internal Studio name per ADR-599 D6 (kernel-internal names follow in a
 * dedicated pass; the member-facing identity is Slides).
 */

import { StudioSurface } from '@/components/authoring/StudioSurface';

export default function SlidesPage() {
  return <StudioSurface />;
}
