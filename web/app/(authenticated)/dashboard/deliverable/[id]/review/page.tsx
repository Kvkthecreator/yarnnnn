'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Route redirect - opens latest staged version as review tab.
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTabs } from '@/contexts/TabContext';
import { api } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const { openVersionTab } = useTabs();
  const deliverableId = params.id as string;
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAndOpen() {
      try {
        // Get the latest staged version
        const detail = await api.deliverables.get(deliverableId);
        const stagedVersion = detail.versions.find(v => v.status === 'staged');

        if (stagedVersion) {
          openVersionTab(deliverableId, stagedVersion.id, `Review: ${detail.deliverable.title}`);
        } else {
          // No staged version, just open deliverable tab
          // (This shouldn't normally happen if accessed via proper flow)
        }
      } catch (err) {
        console.error('Failed to load:', err);
      }
      router.replace('/dashboard');
    }

    loadAndOpen();
  }, [deliverableId, openVersionTab, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
