'use client';

/**
 * Legacy /agents route — redirects to /team (ADR-201).
 *
 * The Team destination replaced /agents as part of the cockpit nav per
 * ADR-198 v2. This redirect preserves bookmark safety during rollout;
 * scheduled for deletion in a future cleanup once external links have
 * caught up.
 *
 * Query params are preserved so deep-links like `/agents?agent=<slug>`
 * land correctly on `/team?agent=<slug>`.
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { TEAM_ROUTE } from '@/lib/routes';

export default function AgentsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params = searchParams?.toString();
    router.replace(`${TEAM_ROUTE}${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-sm text-muted-foreground">Redirecting...</p>
    </div>
  );
}
