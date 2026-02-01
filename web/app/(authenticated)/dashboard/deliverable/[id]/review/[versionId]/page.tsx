'use client';

/**
 * ADR-018: Review Page (specific version)
 */

import { useRouter, useParams } from 'next/navigation';
import { VersionReview } from '@/components/deliverables';

export default function VersionReviewPage() {
  const router = useRouter();
  const params = useParams();
  const deliverableId = params.id as string;
  const versionId = params.versionId as string;

  const handleClose = () => {
    router.push(`/dashboard/deliverable/${deliverableId}`);
  };

  const handleApproved = () => {
    router.push(`/dashboard/deliverable/${deliverableId}`);
  };

  return (
    <VersionReview
      deliverableId={deliverableId}
      versionId={versionId}
      onClose={handleClose}
      onApproved={handleApproved}
    />
  );
}
