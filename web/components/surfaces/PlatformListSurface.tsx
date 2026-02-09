'use client';

/**
 * ADR-033 Phase 5: Platform List Surface
 *
 * Full-page surface showing all connected platforms.
 * Accessed via navigation dropdown "Platforms" option.
 */

import { useState } from 'react';
import { PlatformCardGrid } from '@/components/ui/PlatformCardGrid';
import { PlatformDetailPanel } from '@/components/ui/PlatformDetailPanel';
import { useDesk } from '@/contexts/DeskContext';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

export function PlatformListSurface() {
  const { setSurface } = useDesk();
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformSummary | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const handlePlatformClick = (platform: PlatformSummary) => {
    setSelectedPlatform(platform);
    setPanelOpen(true);
  };

  const handleClosePanel = () => {
    setPanelOpen(false);
    setSelectedPlatform(null);
  };

  const handleAddPlatform = () => {
    window.location.href = '/settings';
  };

  const handleFullView = () => {
    if (selectedPlatform) {
      setSurface({
        type: 'platform-detail',
        platform: selectedPlatform.provider as 'slack' | 'notion' | 'gmail' | 'google',
      });
    }
    handleClosePanel();
  };

  const handleDeliverableClick = (deliverableId: string) => {
    setSurface({ type: 'deliverable-detail', deliverableId });
    handleClosePanel();
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        <PlatformCardGrid
          onPlatformClick={handlePlatformClick}
          onAddPlatformClick={handleAddPlatform}
        />
      </div>

      <PlatformDetailPanel
        platform={selectedPlatform}
        isOpen={panelOpen}
        onClose={handleClosePanel}
        onFullViewClick={handleFullView}
        onDeliverableClick={handleDeliverableClick}
      />
    </div>
  );
}
