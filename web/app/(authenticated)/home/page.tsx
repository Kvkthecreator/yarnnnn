'use client';

/**
 * /home — the Home surface (ADR-312 D1; renamed from /cockpit).
 *
 * The Home is a composition over the workspace's present constituents:
 * substrate-forward when empty, operation-forward when a program runs
 * (ADR-312 §1–2). Rendered via HomeRenderer.
 */

import { HomeRenderer } from '@/components/library/HomeRenderer';
import { useNarrative } from '@/contexts/NarrativeContext';

export default function HomePage() {
  const { sendMessage } = useNarrative();
  return (
    <div className="h-full overflow-y-auto">
      <HomeRenderer onOpenChatDraft={sendMessage} />
    </div>
  );
}
