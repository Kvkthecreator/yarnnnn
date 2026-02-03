'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 *
 * Route redirect - finds latest staged version and opens review surface.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const deliverableId = params.id as string;

  useEffect(() => {
    async function loadAndOpen() {
      try {
        // Get the latest staged version
        const detail = await api.deliverables.get(deliverableId);
        const stagedVersion = detail.versions.find((v: { status: string }) => v.status === 'staged');

        if (stagedVersion) {
          router.replace(
            `/dashboard?surface=deliverable-review&deliverableId=${deliverableId}&versionId=${stagedVersion.id}`
          );
        } else {
          // No staged version, open deliverable detail instead
          router.replace(`/dashboard?surface=deliverable-detail&deliverableId=${deliverableId}`);
        }
      } catch (err) {
        console.error('Failed to load:', err);
        router.replace('/dashboard');
      }
    }

    loadAndOpen();
  }, [deliverableId, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
