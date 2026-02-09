'use client';

/**
 * ADR-033 Phase 5: Platform List Surface
 *
 * Full-page surface showing all connected platforms.
 * Accessed via navigation dropdown "Platforms" option.
 *
 * Clicking a platform card navigates directly to PlatformDetailSurface
 * (full page view) rather than opening a drawer - the content warrants
 * a dedicated page.
 */

import { PlatformCardGrid } from '@/components/ui/PlatformCardGrid';
import { useDesk } from '@/contexts/DeskContext';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

export function PlatformListSurface() {
  const { setSurface } = useDesk();

  const handlePlatformClick = (platform: PlatformSummary) => {
    // Navigate directly to full platform surface (no drawer)
    setSurface({
      type: 'platform-detail',
      platform: platform.provider as 'slack' | 'notion' | 'gmail' | 'google',
    });
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        <h1 className="text-lg font-semibold mb-6">Platforms</h1>
        <PlatformCardGrid onPlatformClick={handlePlatformClick} />
      </div>
    </div>
  );
}
