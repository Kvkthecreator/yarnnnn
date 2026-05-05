'use client';

/**
 * /operation redirect stub → /workspace.
 * Renamed before launch; stub exists for bookmark safety.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function OperationRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/workspace'); }, [router]);
  return null;
}
