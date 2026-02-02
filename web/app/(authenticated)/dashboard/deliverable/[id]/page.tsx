'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Route redirect - opens deliverable as a tab in the main dashboard.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTabs } from '@/contexts/TabContext';
import { Loader2 } from 'lucide-react';

export default function DeliverableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { openDeliverableTab } = useTabs();
  const deliverableId = params.id as string;

  useEffect(() => {
    // Open as tab and redirect to dashboard
    openDeliverableTab(deliverableId, 'Loading...');
    router.replace('/dashboard');
  }, [deliverableId, openDeliverableTab, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
