'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Legacy /system route — redirects to Settings > System tab.
 * System content was absorbed into Settings page.
 */
export default function SystemRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/settings?tab=system');
  }, [router]);

  return null;
}
