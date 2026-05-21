'use client';

/**
 * /principles — atomic Principles surface (ADR-297 D1).
 *
 * Renders /workspace/review/principles.md + /workspace/review/_principles.yaml
 * via the kernel-library PrinciplesCard (full variant; self-fetches per
 * ADR-266 D8). Principles are the Reviewer's judgment framework.
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';

export default function PrinciplesPage() {
  return (
    <SurfacePage
      iconKey="scale"
      title="Principles"
      summary="The Reviewer's judgment framework and decision thresholds. Edit via chat."
    >
      <PrinciplesCard variant="full" />
    </SurfacePage>
  );
}
