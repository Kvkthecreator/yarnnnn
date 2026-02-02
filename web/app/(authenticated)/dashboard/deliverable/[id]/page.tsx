'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Legacy route redirect - opens deliverable tab in the main dashboard.
 * This maintains URL compatibility while using the new tab-based UI.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTabs } from '@/contexts/TabContext';
import { Loader2 } from 'lucide-react';

export default function DeliverableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { openTab } = useTabs();
  const deliverableId = params.id as string;

  useEffect(() => {
    // Open the deliverable tab and redirect to dashboard
    openTab('deliverable', 'Loading...', deliverableId);
    router.replace('/dashboard');
  }, [deliverableId, openTab, router]);

  // Brief loading state while redirecting
  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
