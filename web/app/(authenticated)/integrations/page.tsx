'use client';

/**
 * ADR-039: Redirect to Context page (platforms filter)
 *
 * Legacy /integrations route now redirects to /context?section=platforms
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function IntegrationsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/context?section=platforms');
  }, [router]);

  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Redirecting to Context...</p>
      </div>
    </div>
  );
}
