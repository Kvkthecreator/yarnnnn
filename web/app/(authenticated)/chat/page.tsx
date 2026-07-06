'use client';

/**
 * /chat — the lanes workbench (ADR-412 D3). The slug's THIRD life:
 * ADR-259 pointed it at /feed; ADR-385's follow-ons bounced it through
 * /channels to /notifications (the narrative's home). ADR-412 reclaims it
 * as a real windowed surface — Altitude 2's chrome home (the member's
 * model-pinned helper lanes, ADR-411), distinct from the steward rail
 * (Altitude 1, chat drawer) and the Agents roster (Altitude 3).
 *
 * Old narrative bookmarks now land here instead of Notifications →
 * Activity — the accepted minor break recorded in ADR-412 D3.
 */

import { ChatSurface } from '@/components/chat-surface/ChatSurface';

export default function ChatPage() {
  return <ChatSurface />;
}
