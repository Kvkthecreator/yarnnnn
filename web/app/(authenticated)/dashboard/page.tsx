'use client';

/**
 * ADR-018: Deliverables Dashboard
 * ADR-020: Primary landing view with floating chat context
 */

import { useState, useEffect } from 'react';
import { DeliverablesDashboard, OnboardingWizard } from '@/components/deliverables';
import { useFloatingChat } from '@/contexts/FloatingChatContext';

export default function DashboardPage() {
  const [showWizard, setShowWizard] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // ADR-020: Set floating chat context for deliverables dashboard
  const { setPageContext } = useFloatingChat();

  useEffect(() => {
    setPageContext({ type: 'deliverables-dashboard' });

    return () => {
      setPageContext({ type: 'global' });
    };
  }, [setPageContext]);

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
