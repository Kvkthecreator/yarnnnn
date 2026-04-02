'use client';

/**
 * Workfloor — Legacy redirect to /tasks (new home)
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

export default function WorkfloorRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace(HOME_ROUTE);
  }, [router]);

  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-sm text-muted-foreground">Redirecting...</p>
    </div>
  );
}
