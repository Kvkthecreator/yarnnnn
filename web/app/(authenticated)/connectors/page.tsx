'use client';

/**
 * Connectors page — /connectors.
 *
 * Standalone surface for platform connections (Slack, Notion, GitHub,
 * Lemon Squeezy, Alpaca). Accessible from the user menu alongside
 * Workspace and Billing. Extracted from Settings › Connectors tab.
 */

import { useEffect } from 'react';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { PageHeader } from '@/components/shell/PageHeader';
import { ConnectedIntegrationsSection } from '@/components/settings/ConnectedIntegrationsSection';

export default function ConnectorsPage() {
  const { clearBreadcrumb } = useBreadcrumb();

  useEffect(() => {
    clearBreadcrumb();
    return () => clearBreadcrumb();
  }, [clearBreadcrumb]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
        <PageHeader defaultLabel="Connectors" />
        <ConnectedIntegrationsSection
          title="Connectors"
          description="Connect platforms to give your agents data. Platforms are infrastructure — connect once, agents read automatically."
          redirectTo="/connectors"
        />
      </div>
    </div>
  );
}
