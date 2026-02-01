'use client';

/**
 * ADR-018: Deliverable Detail Page
 */

import { useRouter, useParams } from 'next/navigation';
import { DeliverableDetail } from '@/components/deliverables';

export default function DeliverableDetailPage() {
  const router = useRouter();
  const params = useParams();
  const deliverableId = params.id as string;

  const handleBack = () => {
    router.push('/dashboard');
  };

  const handleReview = (versionId: string) => {
    router.push(`/dashboard/deliverable/${deliverableId}/review/${versionId}`);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <main className="flex-1 overflow-hidden">
        <DeliverableDetail
          deliverableId={deliverableId}
          onBack={handleBack}
          onReview={handleReview}
        />
      </main>
    </div>
  );
}
