'use client';

/**
 * ADR-018: Deliverables Dashboard
 * Primary landing view - replaces chat-first experience.
 */

import { useState, useRef } from 'react';
import { DeliverablesDashboard, OnboardingWizard } from '@/components/deliverables';

export default function DashboardPage() {
  const [showWizard, setShowWizard] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreateNew = () => {
    setShowWizard(true);
  };

  const handleWizardClose = () => {
    setShowWizard(false);
  };

  const handleWizardComplete = (_deliverableId: string) => {
    setShowWizard(false);
    // Trigger dashboard refresh to show new deliverable
    setRefreshKey(k => k + 1);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <main className="flex-1 overflow-hidden">
        <DeliverablesDashboard key={refreshKey} onCreateNew={handleCreateNew} />
      </main>

      {showWizard && (
        <OnboardingWizard
          onClose={handleWizardClose}
          onComplete={handleWizardComplete}
        />
      )}
    </div>
  );
}
