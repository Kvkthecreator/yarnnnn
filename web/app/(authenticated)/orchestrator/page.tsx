'use client';

/**
 * Orchestrator (TP) — Chat-First Surface
 *
 * The user-facing conversational agent with full primitive access.
 * Moved from /dashboard as part of the Supervision Dashboard restructure.
 *
 * Handles:
 * - ?create → pre-fills agent creation prompt
 * - ?provider=X&status=connected → post-OAuth bootstrap flow (ADR-110)
 */

import { ChatFirstDesk } from '@/components/desk/ChatFirstDesk';

export default function OrchestratorPage() {
  return <ChatFirstDesk />;
}
