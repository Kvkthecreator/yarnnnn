'use client';

/**
 * Legacy /team route — redirects to /agents (ADR-214, 2026-04-23).
 *
 * Reverses ADR-201 at the URL level. Kept as a bookmark-safety redirect
 * mirroring the old /agents → /team stub. Query params preserved.
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AGENTS_ROUTE } from '@/lib/routes';

export default function TeamRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params = searchParams?.toString();
    router.replace(`${AGENTS_ROUTE}${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-sm text-muted-foreground">Redirecting...</p>
    </div>
  );
}
