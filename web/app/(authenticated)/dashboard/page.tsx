'use client';

/**
 * ADR-022: Chat-First Architecture
 *
 * Main dashboard page - chat is the primary surface.
 * Drawers open for detailed views (deliverables, reviews).
 */

import { ChatHeader } from '@/components/shell/ChatHeader';
import { ChatView } from '@/components/chat';

export default function DashboardPage() {
  return (
    <div className="h-screen flex flex-col">
      <ChatHeader />
      <ChatView />
    </div>
  );
}
