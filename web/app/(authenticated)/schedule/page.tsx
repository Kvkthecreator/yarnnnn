'use client';

/**
 * /schedule redirect stub — ADR-243 folded into /work.
 *
 * The Schedule surface was a top-level nav tab that grouped recurrences by
 * cadence (Recurring / Reactive / One-time). That view is now the "Schedule"
 * tab inside /work, keeping a 4-segment top nav (Chat | Work | Agents | Files).
 *
 * This stub preserves bookmark/deep-link continuity per ADR-236 Item 5.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ScheduleRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/work'); }, [router]);
  return null;
}
