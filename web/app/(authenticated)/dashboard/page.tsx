'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Main dashboard page using the tab-based supervision UI.
 * TabShell provides: Header, TabBar, Content Area, PersistentTP
 * TabContent renders the appropriate view based on active tab.
 */

import { TabShell, TabContent } from '@/components/tabs';
import { TabHeader } from '@/components/shell/TabHeader';

export default function DashboardPage() {
  return (
    <TabShell header={<TabHeader />}>
      <TabContent />
    </TabShell>
  );
}
