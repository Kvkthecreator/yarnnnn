'use client';

/**
 * ADR-066: Review Route Redirect
 *
 * Legacy route that previously opened review in a surface.
 * Now redirects to the deliverable detail page which has inline review.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function VersionReviewPage() {
  const params = useParams();
  const router = useRouter();
  const deliverableId = params.id as string;

  useEffect(() => {
    // Redirect to detail page with inline review
    router.replace(`/deliverables/${deliverableId}`);
  }, [deliverableId, router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
