'use client';

/**
 * /autonomy — atomic Autonomy surface (ADR-297 D1).
 *
 * Renamed from /delegation (2026-05-24) to align with the substrate file
 * (_autonomy.yaml) and the operator's mental model. The schema field
 * `default_delegation` stays — it's the precise data-layer term for the
 * delegated level. At the operator surface the broader concept is Autonomy.
 *
 * Renders /workspace/context/_shared/_autonomy.yaml via the kernel-library
 * AutonomyCard (full variant; self-fetches per ADR-266 D8). Per the
 * 2026-05-24 design polish, the full variant gates every mutation behind
 * a confirm modal (see docs/design/WORKSPACE-COMPONENTS.md §2).
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';

export default function AutonomyPage() {
  return (
    <SurfacePage
      iconKey="shield-check"
      title="Autonomy"
      summary="How much the Reviewer can execute without operator approval. Switching levels requires confirmation."
    >
      <AutonomyCard variant="full" />
    </SurfacePage>
  );
}
