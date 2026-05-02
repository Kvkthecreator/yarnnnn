'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Legacy /system route — redirects to /settings.
 *
 * System tab removed (2026-05-02): the only content was Scheduler Heartbeat,
 * which is already visible on the admin page. Bookmark-safety stub per
 * ADR-236 Item 5 + web/lib/routes.ts redirect-stub policy.
 */
export default function SystemRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/settings');
  }, [router]);

  return null;
}
