'use client';

/**
 * CockpitRenderer — ADR-228 four-face cockpit.
 *
 * The cockpit is the operation, rendered. Four faces, fixed order:
 *   1. Mandate         — what we're trying to do, with what permissions
 *   2. Money truth     — where the account stands right now
 *   3. Performance     — how we're doing against the mandate
 *   4. Tracking        — what's in motion
 *
 * Order is structural: you cannot read performance without knowing what
 * was being attempted (Mandate first); you cannot read what's in motion
 * without knowing the ground-truth state (Money truth before Tracking).
 * Bundles cannot reorder; they fill each face with their domain's shape
 * via `cockpit.{mandate,money_truth,performance,tracking}` declarations
 * in SURFACES.yaml.
 *
 * Singular implementation: replaces the deleted six-pane registry from
 * ADR-225 (pane components + KERNEL_DEFAULT_COCKPIT_PANES + resolveCockpitPanes
 * + tabs.work.list.cockpit_panes). Each face is imported directly; there
 * is no registry dispatch for the cockpit. The compositor seam (resolveMiddle,
 * resolveChrome) survives unchanged for /work detail and chrome composition.
 */

import { CockpitProvider } from './CockpitContext';
import { CockpitHeader } from './CockpitHeader';
import { MoneyTruthFace } from './faces/MoneyTruthFace';
import { PerformanceFace } from './faces/PerformanceFace';
import { TrackingFace } from './faces/TrackingFace';
import { useComposition, getProgramSections } from '@/lib/compositor';
import { dispatchComponent } from './registry';

interface CockpitRendererProps {
  /**
   * Chat-draft handler. The Mandate face uses this for skeleton-state
   * authoring CTA. Other faces don't currently consume it but we keep
   * the context in place for future use.
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function CockpitRenderer({ onOpenChatDraft }: CockpitRendererProps) {
  const handleOpenChatDraft = onOpenChatDraft ?? (() => { /* no-op */ });
  const { data: composition } = useComposition();
  const programSections = getProgramSections(composition);
  const hasProgramSections = programSections.length > 0;

  return (
    <CockpitProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section aria-label="Cockpit" className="border-b border-border/60">
        {/* Layer 1 — Common header. Always present, no bundle override.
            Mandate title + summary + autonomy posture (ADR-243 Phase A). */}
        <CockpitHeader />

        {/* Layer 2 — Singular dispatch: program_sections XOR four-face stack.
            No dual path. When the active bundle declares program_sections,
            those sections render (ordered, independent components). When
            no bundle is active or no sections declared, the kernel-default
            four-face stack renders instead. MandateFace is removed from the
            kernel stack — CockpitHeader covers mandate + autonomy for all
            workspaces (ADR-243 Phase B cleanup). */}
        {hasProgramSections ? (
          <div className="flex flex-col gap-4 px-6 py-6 bg-muted/20">
            {programSections.map((section) =>
              dispatchComponent({ kind: section.kind }, {})
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4 px-6 py-6 bg-muted/20">
            <MoneyTruthFace />
            <PerformanceFace />
            <TrackingFace />
          </div>
        )}
      </section>
    </CockpitProvider>
  );
}
