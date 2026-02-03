'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 *
 * Route redirect - opens specific version as review surface.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function VersionReviewPage() {
  const params = useParams();
  const router = useRouter();
  const deliverableId = params.id as string;
  const versionId = params.versionId as string;

  useEffect(() => {
    router.replace(
      `/dashboard?surface=deliverable-review&deliverableId=${deliverableId}&versionId=${versionId}`
    );
  }, [deliverableId, versionId, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
