'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Legacy /system route — redirects to /settings?tab=system.
 *
 * System diagnostics (back-office task health, render usage, balance
 * audit) were absorbed into the Settings surface as a tab; the
 * standalone /system route was retired alongside that absorption.
 *
 * Bookmark-safety stub. See ADR-236 Item 5 + web/lib/routes.ts for the
 * redirect-stub policy.
 */
export default function SystemRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/settings?tab=system');
  }, [router]);

  return null;
}
