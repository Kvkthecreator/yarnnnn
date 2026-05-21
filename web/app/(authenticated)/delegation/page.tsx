'use client';

/**
 * /delegation — atomic Delegation surface (ADR-297 D1).
 *
 * Renders /workspace/context/_shared/_autonomy.yaml via the kernel-library
 * DelegationCard (full variant; self-fetches per ADR-266 D8). Delegation
 * is what was historically called "Autonomy" on the Reviewer page tab —
 * the operator-authored governance ceiling.
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { DelegationCard } from '@/components/workspace-concepts/DelegationCard';

export default function DelegationPage() {
  return (
    <SurfacePage
      iconKey="shield-check"
      title="Delegation"
      summary="How much the Reviewer can execute without operator approval. Edit via chat."
    >
      <DelegationCard variant="full" />
    </SurfacePage>
  );
}
