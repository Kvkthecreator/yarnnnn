'use client';

/**
 * ADR-018: Review Page (latest staged version)
 */

import { useRouter, useParams } from 'next/navigation';
import { VersionReview } from '@/components/deliverables';

export default function ReviewPage() {
  const router = useRouter();
  const params = useParams();
  const deliverableId = params.id as string;

  const handleClose = () => {
    router.push(`/dashboard/deliverable/${deliverableId}`);
  };

  const handleApproved = () => {
    router.push(`/dashboard/deliverable/${deliverableId}`);
  };

  return (
    <VersionReview
      deliverableId={deliverableId}
      onClose={handleClose}
      onApproved={handleApproved}
    />
  );
}
