'use client';

/**
 * ADR-037: Integrations Page (Route-based)
 *
 * Standalone page for managing connected integrations.
 * Core feature page - connects to Slack, Notion, Gmail, etc.
 */

import { useRouter } from 'next/navigation';
import { Link2 } from 'lucide-react';
import { PlatformCardGrid } from '@/components/ui/PlatformCardGrid';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

export default function IntegrationsPage() {
  const router = useRouter();

  const handlePlatformClick = (platform: PlatformSummary) => {
    router.push(`/integrations/${platform.provider}`);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Link2 className="w-6 h-6" />
          <h1 className="text-2xl font-bold">Integrations</h1>
        </div>
        <p className="text-muted-foreground mb-6">
          Connect integrations to import context and export deliverables.
        </p>
        <PlatformCardGrid onPlatformClick={handlePlatformClick} />
      </div>
    </div>
  );
}
