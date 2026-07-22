'use client';

/**
 * /chat — the chat workbench (ADR-412 D3). The slug's THIRD life:
 * ADR-259 pointed it at /feed; ADR-385's follow-ons bounced it through
 * /channels to /notifications (the narrative's home). ADR-412 reclaims it
 * as a real windowed surface — the member's conversations with their
 * colleagues (ADR-411), distinct from the steward rail (the chat drawer)
 * and the Agents roster (who they are, /agents).
 *
 * The "Altitude 1/2/3" ordinals this header carried were retired by ADR-460
 * D1 (§6.10d) — configuration is a vector, not a rung.
 *
 * Old narrative bookmarks now land here instead of Notifications →
 * Activity — the accepted minor break recorded in ADR-412 D3.
 */

import { ChatSurface } from '@/components/chat-surface/ChatSurface';

export default function ChatPage() {
  return <ChatSurface />;
}
