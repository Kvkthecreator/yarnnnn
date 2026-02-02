'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Renders the content for the active tab.
 * Each tab type has its own full-page view component.
 */

import { useTabs } from '@/contexts/TabContext';
import { Loader2 } from 'lucide-react';

// Tab content views
import { ChatView } from '@/components/chat/ChatView';
import { DeliverableTabView } from './views/DeliverableTabView';
import { VersionTabView } from './views/VersionTabView';

export function TabContent() {
  const { activeTab } = useTabs();

  if (!activeTab) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Render based on tab type
  switch (activeTab.type) {
    case 'chat':
      return <ChatView />;

    case 'deliverable':
      return (
        <DeliverableTabView
          deliverableId={activeTab.resourceId!}
        />
      );

    case 'version':
      return (
        <VersionTabView
          deliverableId={activeTab.data?.deliverableId as string}
          versionId={activeTab.resourceId!}
        />
      );

    case 'document':
      // TODO: Implement document view
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Document: {activeTab.title}
        </div>
      );

    default:
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Unknown tab type
        </div>
      );
  }
}
