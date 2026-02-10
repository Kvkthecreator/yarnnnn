'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Dashboard now uses ChatFirstDesk - TP is the primary interface
 * Replaces the previous ADR-023 surface-first architecture
 */

import { ChatFirstDesk } from '@/components/desk/ChatFirstDesk';

export default function DashboardPage() {
  return <ChatFirstDesk />;
}
