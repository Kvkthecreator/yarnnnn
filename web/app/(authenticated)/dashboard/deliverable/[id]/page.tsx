'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 *
 * Route redirect - opens deliverable detail surface via URL params.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { HOME_ROUTE } from '@/lib/routes';

export default function DeliverableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deliverableId = params.id as string;

  useEffect(() => {
    // Redirect to dashboard with surface params
    router.replace(`${HOME_ROUTE}?surface=deliverable-detail&deliverableId=${deliverableId}`);
  }, [deliverableId, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
