'use client';

/**
 * BriefingStrip — /work list-mode cockpit zone (ADR-205 F2 + ADR-206 + ADR-215 Phase 4).
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
 *   4. IntelligenceCard — synthesis artifact (ADR-204 maintain-overview)
 *
 * ADR-206 principle: Deliverables are first-class to the operator. Proposals
 * awaiting review are the deliverable that is also an action surface — they
 * land first. Money-truth (`_performance.md`) is the deliverable that is also
 * the scoreboard — it lands second. Temporal changes (since-last-look) and
 * synthesis (IntelligenceCard) are secondary.
 *
 * ADR-215 Phase 4: the cockpit zone is visually distinguished from the task
 * list below it — section label + subtle tint + zone padding — so the operator
 * reads it as "glance zone" vs "manage zone" without needing tabs. Single
 * vertical scroll preserved per ADR-205 F2 (the whole point of the merge).
 *
 * Invariants preserved from ADR-198 §3 (Briefing):
 *   - B2: composed by selection, not duplication
 *   - I2: no embedding of foreign substrate; links only
 *   - I1: no component holds state; substrate is authoritative
 */

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
    <section
      aria-label="Cockpit"
      className="border-b border-border/60 bg-muted/20"
    >
      <div className="flex items-baseline justify-between px-6 pt-5 pb-2">
        <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
          Cockpit
        </h2>
        <span className="text-[10px] text-muted-foreground/40">
          What needs you · book · since last look · intelligence
        </span>
      </div>
      <div className="flex flex-col gap-6 px-6 pb-6">
        {/* ADR-206 Deliverables-first ordering: proposals → money-truth → since-last-look → synthesis */}
        <NeedsMePane onOpenChatDraft={handleOpenChatDraft} />
        <SnapshotPane isDayZero={false} />
        <SinceLastLookPane />
        <IntelligenceCard />
      </div>
    </section>
  );
}
