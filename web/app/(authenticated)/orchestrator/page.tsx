'use client';

/**
 * Legacy /orchestrator route — redirects to /workfloor (ADR-139)
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function OrchestratorRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Preserve query params (e.g. ?provider=slack&status=connected)
    const params = searchParams?.toString();
    router.replace(`/workfloor${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return null;
}
