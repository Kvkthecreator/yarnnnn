'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Main dashboard with IDE-like tabs:
 * - Chat tab is home (always present)
 * - Output tabs open when viewing deliverables, versions
 * - Each tab is a full-page view
 */

import { ChatHeader } from '@/components/shell/ChatHeader';
import { TabBar, TabContent } from '@/components/tabs';

export default function DashboardPage() {
  return (
    <div className="h-screen flex flex-col">
      <ChatHeader />
      <TabBar />
      <div className="flex-1 overflow-hidden">
        <TabContent />
      </div>
    </div>
  );
}
