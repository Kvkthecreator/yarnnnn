'use client';

/**
 * BriefingStrip — Overview's Briefing content merged into /work (ADR-205 F2 + ADR-206).
 *
 * ADR-205 dissolved the standalone /overview route. What survived of the cockpit
 * was the Briefing archetype (ADR-198 §3): pointer-based, non-embedding,
 * "what happened and what needs me" summaries. Those four panes now live here
 * and mount above the task list when /work is in list-mode.
 *
 * Composition ordered for ADR-206 Deliverables-first priority:
 *   1. NeedsMePane — Queue (pending proposals awaiting approval — the operator's
 *      most urgent surface under ADR-206, the point of the loop)
 *   2. SnapshotPane — Dashboard-snippet tiles including the money-truth tile
 *      (book / _performance.md headline — first-class under ADR-195 + ADR-206)
 *   3. SinceLastLookPane — Briefing (temporal changes since last session)
 *   4. IntelligenceCard — synthesis artifact (ADR-204 maintain-overview, still
 *      informative even though the source task dissolves per ADR-206)
 *
 * ADR-206 principle: Deliverables are first-class to the operator. Proposals
 * awaiting review are the deliverable that is also an action surface — they
 * land first. Money-truth (`_performance.md`) is the deliverable that is also
 * the scoreboard — it lands second. Temporal changes (since-last-look) and
 * synthesis (IntelligenceCard) are secondary.
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
      {/* ADR-206 Deliverables-first ordering: proposals → money-truth → since-last-look → synthesis */}
      <NeedsMePane onOpenChatDraft={handleOpenChatDraft} />
      <SnapshotPane isDayZero={false} />
      <SinceLastLookPane />
      <IntelligenceCard />
    </div>
  );
}
