'use client';

/**
 * Review Page — Reviewer destination (ADR-200).
 *
 * The fourth cockpit destination per ADR-198 v2. Surfaces the Reviewer
 * layer's substrate for operator supervision:
 *   - Reviewer identity (/workspace/review/IDENTITY.md)
 *   - Principles / review framework (/workspace/review/principles.md)
 *   - Decisions chronicle (/workspace/review/decisions.md)
 *
 * Ambient YARNNN rail available via ThreePanelLayout. All substrate reads
 * flow through the existing /api/workspace/file endpoint — no new backend
 * APIs needed.
 *
 * Design invariants (ADR-198):
 *   I1 — No surface state (substrate is authoritative)
 *   I2 — No foreign substrate embedding (principles edits route through
 *        YARNNN rail, not inline forms)
 *   I3 — Primary consumer: operator supervising the Reviewer layer
 */

import { useState } from 'react';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { ReviewSurface } from '@/components/review/ReviewSurface';

export default function ReviewPage() {
  const [chatDraftSeed, setChatDraftSeed] = useState<{ id: string; text: string } | null>(null);
  const [chatOpenSignal, setChatOpenSignal] = useState(0);

  const plusMenuActions: PlusMenuAction[] = [];

  const handleOpenChatDraft = (prompt: string) => {
    setChatDraftSeed({ id: crypto.randomUUID(), text: prompt });
    setChatOpenSignal((n) => n + 1);
  };

  return (
    <ThreePanelLayout
      chat={{
        draftSeed: chatDraftSeed,
        plusMenuActions,
        placeholder: 'Ask YARNNN about your review principles or decisions...',
        defaultOpen: false,
        openSignal: chatOpenSignal,
      }}
    >
      <PageHeader defaultLabel="Review" />
      <ReviewSurface onOpenChatDraft={handleOpenChatDraft} />
    </ThreePanelLayout>
  );
}
