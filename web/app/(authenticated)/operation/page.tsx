'use client';

/**
 * /operation redirect stub.
 *
 * Pre-launch rename history: /operation → /workspace (ADR-244) → /mandate
 * (ADR-297). Each iteration tightened the operator-facing target.
 * Current target: /mandate — the most-touched atomic governance surface
 * after the ADR-297 atomic-shell migration.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function OperationRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/mandate'); }, [router]);
  return null;
}
