'use client';

/**
 * ADR-039: Redirect to unified Context page
 *
 * Legacy /integrations/[provider] route now redirects to /context?source=[provider]
 */

import { useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function IntegrationProviderRedirect({
  params,
}: {
  params: Promise<{ provider: string }>;
}) {
  const { provider } = use(params);
  const router = useRouter();

  useEffect(() => {
    router.replace(`/context?source=${provider}`);
  }, [router, provider]);

  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Redirecting to Context...</p>
      </div>
    </div>
  );
}
