'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Route redirect - opens specific version as review tab.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTabs } from '@/contexts/TabContext';
import { Loader2 } from 'lucide-react';

export default function VersionReviewPage() {
  const params = useParams();
  const router = useRouter();
  const { openVersionTab } = useTabs();
  const deliverableId = params.id as string;
  const versionId = params.versionId as string;

  useEffect(() => {
    openVersionTab(deliverableId, versionId, 'Review');
    router.replace('/dashboard');
  }, [deliverableId, versionId, openVersionTab, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
