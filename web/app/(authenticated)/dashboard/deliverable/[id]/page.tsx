'use client';

/**
 * ADR-091: Legacy route redirect → /deliverables/[id] workspace
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function DeliverableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deliverableId = params.id as string;

  useEffect(() => {
    router.replace(`/deliverables/${deliverableId}`);
  }, [deliverableId, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
