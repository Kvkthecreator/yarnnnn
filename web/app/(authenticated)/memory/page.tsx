'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Legacy /memory route — redirects to /context with IDENTITY.md preselected.
 *
 * ADR-215 R3 (2026-04-24): identity/brand/profile are substrate; the
 * canonical edit surface is the Files tab (/context). The old Settings >
 * Memory tab is retired; this route redirects to the Files tab with
 * IDENTITY.md already open.
 *
 * Bookmark-safety stub. See ADR-236 Item 5 + web/lib/routes.ts for the
 * redirect-stub policy.
 */
export default function MemoryRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/context?path=%2Fworkspace%2Fcontext%2F_shared%2FIDENTITY.md');
  }, [router]);

  return null;
}
