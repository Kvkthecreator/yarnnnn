'use client';

/**
 * /mandate — atomic Mandate surface (ADR-297 D1).
 *
 * Renders /workspace/context/_shared/MANDATE.md via the kernel-library
 * MandateCard (full variant; self-fetches per ADR-266 D8).
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { MandateCard } from '@/components/workspace-concepts/MandateCard';

export default function MandatePage() {
  return (
    <SurfacePage
      iconKey="target"
      title="Mandate"
      summary="Your standing intent — the Primary Action this workspace is built around. Edit via chat."
    >
      <MandateCard variant="full" />
    </SurfacePage>
  );
}
