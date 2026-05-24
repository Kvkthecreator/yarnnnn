'use client';

/**
 * /pace — atomic Pace surface (ADR-300).
 *
 * Renders /workspace/context/_shared/_pace.yaml via the kernel-library
 * PaceCard (full variant; self-fetches per ADR-266 D8). Pace is the
 * Trigger-dimension dial of the Pace + Delegation + Identity operator
 * trifecta (ADR-298 D11).
 *
 * Supersedes ADR-298 D5's "cockpit Schedule tab section" pace rendering
 * site — pace gets its own atomic surface per ADR-300. PaceBadge on the
 * Cockpit becomes a read-only deep-link to this surface.
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { PaceCard } from '@/components/workspace-concepts/PaceCard';

export default function PacePage() {
  return (
    <SurfacePage
      iconKey="gauge"
      title="Pace"
      summary="How often the Reviewer wakes through the paced lane. Kind editable here; complex fields via chat."
    >
      <PaceCard variant="full" />
    </SurfacePage>
  );
}
