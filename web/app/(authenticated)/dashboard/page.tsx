'use client';

/**
 * ADR-018: Deliverables Dashboard
 * Primary landing view - replaces chat-first experience.
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DeliverablesDashboard, OnboardingWizard } from '@/components/deliverables';

export default function DashboardPage() {
  const router = useRouter();
  const [showWizard, setShowWizard] = useState(false);

  const handleCreateNew = () => {
    setShowWizard(true);
  };

  const handleWizardClose = () => {
    setShowWizard(false);
  };

  const handleWizardComplete = (deliverableId: string) => {
    setShowWizard(false);
    router.push(`/dashboard/deliverable/${deliverableId}`);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <main className="flex-1 overflow-hidden">
        <DeliverablesDashboard onCreateNew={handleCreateNew} />
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
