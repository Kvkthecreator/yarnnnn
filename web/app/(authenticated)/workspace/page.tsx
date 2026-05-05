'use client';

/**
 * Workspace page — /workspace.
 *
 * The canonical home for workspace-level configuration. Accessible from
 * the user menu (between Settings and Billing). Replaces the
 * Settings › Workspace tab (ADR-244) and the Mandate/Autonomy/Principles
 * tabs on the YARNNN agent detail.
 *
 * Layout: ThreePanelLayout with the chat panel open — operator reads their
 * configuration on the left, asks YARNNN to edit it on the right.
 * No content is editable inline; chat is the edit surface (ADR-244 D7).
 */

import { useEffect } from 'react';
import { MessageCircle } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { WorkspaceConfigSection } from '@/components/workspace-config/WorkspaceConfigSection';

export default function WorkspaceConfigPage() {
  const { loadScopedHistory } = useTP();
  const { clearBreadcrumb } = useBreadcrumb();

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);
  useEffect(() => {
    clearBreadcrumb();
    return () => clearBreadcrumb();
  }, [clearBreadcrumb]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        Ask YARNNN to update your mandate, autonomy, principles, or identity.
      </p>
    </div>
  );

  return (
    <ThreePanelLayout
      chat={{
        placeholder: 'Ask YARNNN to update your workspace setup…',
        emptyState: chatEmptyState,
        defaultOpen: true,
        plusMenuActions: [],
      }}
    >
      <PageHeader defaultLabel="Workspace" />
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        <WorkspaceConfigSection />
      </div>
    </ThreePanelLayout>
  );
}
