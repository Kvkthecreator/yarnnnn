'use client';

/**
 * /identity — atomic Identity + Brand surface (ADR-297 D1).
 *
 * Renders /workspace/persona/IDENTITY.md + BRAND.md via the
 * kernel-library IdentityBrandCard (full variant; self-fetches per ADR-266
 * D8). Per ADR-297 D1's surface table, Identity and Brand are nominally
 * separate atomic concepts, but the existing card co-renders them — the
 * /identity surface serves both and /brand redirects here as a sibling
 * for now. Splitting is a follow-on if operator demand surfaces.
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { IdentityBrandCard } from '@/components/workspace-concepts/IdentityBrandCard';

export default function IdentityPage() {
  return (
    <SurfacePage
      iconKey="user-circle"
      title="Identity & Brand"
      summary="Operator persona and brand voice. Edit via chat."
    >
      <IdentityBrandCard variant="full" />
    </SurfacePage>
  );
}
