'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Legacy /memory route — redirects to Settings > Memory tab.
 * Memory content was absorbed into Settings page.
 */
export default function MemoryRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/settings?tab=memory');
  }, [router]);

  return null;
}
