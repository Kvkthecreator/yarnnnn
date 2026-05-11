'use client';

/**
 * /backend redirect stub — renamed to /activity per ADR-265.
 *
 * "Backend" was engineer vocabulary; the page's actual operator job is
 * activity audit — workspace-wide structured ledger of every invocation
 * attempt. Renamed to /activity to match the operator's mental model.
 *
 * This stub preserves bookmark/deep-link continuity per ADR-236 Item 5.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function BackendRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/activity'); }, [router]);
  return null;
}
