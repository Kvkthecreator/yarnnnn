'use client';

/**
 * Legacy /chat route — redirects to /feed per ADR-259 (Feed Surface, 2026-05-08).
 *
 * Preserves query params so any deep-linked operator bookmarks survive the
 * vocabulary migration. The Chat → Feed rename is a singular implementation;
 * /chat URL existed before ADR-259 and any active operator tabs / external
 * bookmarks would land here. They get forwarded to /feed transparently.
 *
 * Stub follows the redirect-stub policy in lib/routes.ts:
 * thin client component, router.replace, query params preserved, removable
 * after one major release cycle of zero inbound traffic.
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FEED_ROUTE } from '@/lib/routes';

export default function ChatRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params = searchParams?.toString();
    router.replace(`${FEED_ROUTE}${params ? `?${params}` : ''}`);
  }, [router, searchParams]);

  return null;
}
