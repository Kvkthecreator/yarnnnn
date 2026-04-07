'use client';

/**
 * Legacy /orchestrator route — redirects to HOME_ROUTE (ADR-163: /chat).
 * Preserves query params so OAuth callbacks land on the briefing dashboard
 * with the newly-connected platform reflected in working memory.
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

export default function OrchestratorRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Preserve query params (e.g. ?provider=slack&status=connected)
    const params = searchParams?.toString();
    router.replace(`${HOME_ROUTE}${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return null;
}
