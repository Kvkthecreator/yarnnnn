'use client';

/**
 * ADR-022: Chat-First Architecture
 *
 * Route redirect - opens deliverable drawer in the main dashboard.
 * This maintains URL compatibility while using the drawer-based UI.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSurface } from '@/contexts/SurfaceContext';
import { Loader2 } from 'lucide-react';

export default function DeliverableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { openSurface } = useSurface();
  const deliverableId = params.id as string;

  useEffect(() => {
    // Open the deliverable drawer and redirect to dashboard
    openSurface('output', { deliverableId });
    router.replace('/dashboard');
  }, [deliverableId, openSurface, router]);

  // Brief loading state while redirecting
  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
