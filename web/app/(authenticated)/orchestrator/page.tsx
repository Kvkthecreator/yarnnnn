'use client';

/**
 * Legacy /orchestrator route — redirects to /tasks
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function OrchestratorRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Preserve query params (e.g. ?provider=slack&status=connected)
    const params = searchParams?.toString();
    router.replace(`/agents${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return null;
}
