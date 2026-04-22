'use client';

/**
 * BriefingStrip — Overview's Briefing content merged into /work (ADR-205 F2).
 *
 * ADR-205 dissolved the standalone /overview route. What survived of the cockpit
 * was the Briefing archetype (ADR-198 §3): pointer-based, non-embedding,
 * "what happened and what needs me" summaries. Those four panes now live here
 * and mount above the task list when /work is in list-mode.
 *
 * Composition follows the original OverviewSurface order:
 *   1. NeedsMePane — Queue (pending proposals + alerts)
 *   2. SinceLastLookPane — Briefing (temporal changes since last session)
 *   3. SnapshotPane — Dashboard-snippet tiles (linked, not embedded)
 *   4. IntelligenceCard — maintain-overview synthesis artifact (ADR-204)
 *
 * ADR-205 note: the workforce-health portion of ADR-204 IntelligenceCard no
 * longer has much to surface (signup scaffolds exactly one agent). What
 * remains meaningful is task-cycle intelligence — run history, deliverable
 * quality, workspace density. IntelligenceCard still serves that. Roster
 * intelligence dissolves because the roster itself dissolved.
 *
 * Invariants preserved from ADR-198 §3 (Briefing):
 *   - B2: composed by selection, not duplication
 *   - I2: no embedding of foreign substrate; links only
 *   - I1: no component holds state; substrate is authoritative
 */

import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { NeedsMePane } from './NeedsMePane';
import { SinceLastLookPane } from './SinceLastLookPane';
import { SnapshotPane } from './SnapshotPane';
import { IntelligenceCard } from './IntelligenceCard';

export interface BriefingStripProps {
  /**
   * When the operator clicks a chip inside NeedsMePane that seeds a chat
   * draft, this callback receives the text. The hosting page decides how
   * to surface it (seed rail composer, open full chat, etc.).
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function BriefingStrip({ onOpenChatDraft }: BriefingStripProps) {
  const handleOpenChatDraft = onOpenChatDraft ?? (() => { /* no-op */ });
  return (
    <div className="flex flex-col gap-6 px-6 pt-6">
      <NeedsMePane onOpenChatDraft={handleOpenChatDraft} />
      <SinceLastLookPane />
      <SnapshotPane isDayZero={false} />
      <IntelligenceCard />
    </div>
  );
}
