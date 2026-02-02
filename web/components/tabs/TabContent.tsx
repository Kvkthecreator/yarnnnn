'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * TabContent - renders the appropriate content based on active tab type.
 * Each tab type has its own renderer component.
 */

import { useTabs } from '@/contexts/TabContext';
import { Loader2 } from 'lucide-react';

// Tab renderers
import { HomeTabContent } from './renderers/HomeTabContent';
import { DeliverableTabContent } from './renderers/DeliverableTabContent';
import { VersionReviewTabContent } from './renderers/VersionReviewTabContent';

export function TabContent() {
  const { activeTab, updateTabStatus, updateTabData, openTab, closeTab } = useTabs();

  if (!activeTab) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Common props for all tab renderers
  const commonProps = {
    tab: activeTab,
    updateStatus: (status: 'idle' | 'loading' | 'error' | 'unsaved') => updateTabStatus(activeTab.id, status),
    updateData: (data: Record<string, unknown>) => updateTabData(activeTab.id, data),
    openTab,
    closeTab,
  };

  // Render based on tab type
  switch (activeTab.type) {
    case 'home':
      return <HomeTabContent {...commonProps} />;

    case 'deliverable':
      return <DeliverableTabContent {...commonProps} />;

    case 'version-review':
      return <VersionReviewTabContent {...commonProps} />;

    case 'memory':
      // TODO: Implement
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Memory: {activeTab.title}
        </div>
      );

    case 'context':
      // TODO: Implement
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Context: {activeTab.title}
        </div>
      );

    case 'document':
      // TODO: Implement
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Document: {activeTab.title}
        </div>
      );

    case 'profile':
      // TODO: Implement
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          Profile Settings
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
