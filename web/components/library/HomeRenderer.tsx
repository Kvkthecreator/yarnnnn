'use client';

/**
 * HomeRenderer — renamed from CockpitRenderer by ADR-312 D1; six-slot
 * composition wired 2026-06-04 (ADR-312 D2 amendment).
 *
 * The Home is a composition over the workspace's present constituents
 * (ADR-312 §1–2). The kernel owns the six-slot set + order; it renders
 * the three KERNEL-UNIVERSAL slots itself (from kernel substrate, every
 * workspace, program or not) and lets the PROGRAM declare the two
 * program-shaped slots. Absent constituents self-hide — honest Home.
 *
 *   #1 Constitution band  — HomeHeader (kernel, always). Mandate one-liner
 *                           + autonomy posture from _shared/{MANDATE.md,
 *                           _autonomy.yaml}.
 *   #3 Decision queue      — KernelDecisionQueue (kernel-universal). Pending
 *                           gated actions (action_proposals / ADR-307).
 *                           Surfaced HIGH — the most operator-urgent glance.
 *   #2 Ground-truth hero   } program_sections (program-declared via
 *   #4 Live entities       } SURFACES.yaml home.program_sections[]). The
 *                           program's hero + entity expression. Generic
 *                           contract (ADR-312 D3/D4); no kernel default.
 *   #5 Recent artifacts    — KernelRecentArtifacts (kernel-universal).
 *                           Delivered outputs across the workspace.
 *   #6 Judgment trail      — KernelJudgmentTrail (kernel-universal). Recent
 *                           Reviewer decisions from persona/judgment_log.md.
 *
 * ADR-312 D2 amendment (2026-06-04): slots #3/#5/#6 read kernel-universal
 * substrate (proposals, delivered outputs, decisions) and have no reason
 * to be program-gated. The kernel renders them directly — closing the
 * defect where an activated-but-section-less program (or bare kernel)
 * showed a near-empty Home. Each kernel slot self-hides when its substrate
 * is empty, so the cold-start Home stays honest (constitution CTA + only
 * the universal slots that have content yet).
 *
 * Singular implementation per ADR-273 D2 (preserved):
 *   - The legacy four-face fallback (MoneyTruthFace / PerformanceFace /
 *     TrackingFace / MandateFace) stays DELETED. The constitution-band CTA
 *     handles the no-mandate cold start, not a de-activated trader board.
 *   - The CTA now renders ONLY when there is genuinely nothing to show —
 *     no program sections AND no activation yet. With a program activated,
 *     the program sections render; the kernel slots render regardless.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { HomeProvider } from './HomeContext';
import { HomeHeader } from './HomeHeader';
import { useComposition, getProgramSections } from '@/lib/compositor';
import { dispatchComponent } from './registry';
import { KernelDecisionQueue } from './kernel-home/KernelDecisionQueue';
import { KernelRecentArtifacts } from './kernel-home/KernelRecentArtifacts';
import { KernelJudgmentTrail } from './kernel-home/KernelJudgmentTrail';
import { api } from '@/lib/api/client';

interface HomeRendererProps {
  /**
   * Chat-draft handler. Forwarded into HomeContext so any home slot
   * component can call sendMessage() without prop-drilling.
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function HomeRenderer({ onOpenChatDraft }: HomeRendererProps) {
  const handleOpenChatDraft = onOpenChatDraft ?? (() => { /* no-op */ });
  const { data: composition } = useComposition();
  const programSections = getProgramSections(composition);
  const hasProgramSections = programSections.length > 0;

  // Read activation state only when no program_sections are declared —
  // the CTA is the only branch that needs the slug. Avoids an extra
  // network round-trip for the common activated path.
  const [activeProgramSlug, setActiveProgramSlug] = useState<string | null>(null);
  const [stateLoaded, setStateLoaded] = useState(false);
  useEffect(() => {
    if (hasProgramSections) {
      setStateLoaded(true);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const state = await api.workspace.getState();
        if (!cancelled) setActiveProgramSlug(state.active_program_slug);
      } catch {
        // Network failure: render activation CTA optimistically — the
        // operator can still navigate to the Program surface.
      } finally {
        if (!cancelled) setStateLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hasProgramSections]);

  // The activation CTA renders ONLY when there is genuinely nothing to
  // show in Layer 2 — no program sections AND no activated program. With a
  // program activated, the program sections render; either way the three
  // kernel-universal slots render below (each self-hides when empty).
  const showActivationCTA = !hasProgramSections && stateLoaded && !activeProgramSlug;

  return (
    <HomeProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section aria-label="Home" className="border-b border-border/60">
        {/* Slot #1 — Constitution band (kernel, always) */}
        <HomeHeader />

        <div className="flex flex-col gap-4 px-4 py-5 sm:px-6 sm:py-6 bg-muted/20">
          {/* Slot #3 — Decision queue (kernel-universal; self-hides) */}
          <KernelDecisionQueue />

          {/* Slots #2 + #4 — program-declared hero + entities */}
          {hasProgramSections &&
            programSections.map((section) =>
              dispatchComponent({ kind: section.kind }, {})
            )}

          {/* Slot #5 — Recent artifacts (kernel-universal; self-hides) */}
          <KernelRecentArtifacts />

          {/* Slot #6 — Judgment trail (kernel-universal; self-hides) */}
          <KernelJudgmentTrail />

          {/* Cold-start CTA — only when there is nothing else to show */}
          {showActivationCTA && (
            <UnactivatedHomeCTA activeProgramSlug={activeProgramSlug} />
          )}
        </div>
      </section>
    </HomeProvider>
  );
}

/**
 * UnactivatedHomeCTA — the cold-start home's empty state (ADR-312 D6).
 * The home doubles as onboarding: a bare kernel (no program activated, no
 * universal substrate yet) renders the "activate a program" affordance.
 *
 * Post ADR-312 D2 amendment (2026-06-04) this renders ONLY when no program
 * is activated. An activated program always shows its sections + the
 * kernel-universal slots, so the prior "program activated but declares no
 * home dashboard" branch is gone — there is no dead-end Home anymore.
 */
function UnactivatedHomeCTA({ activeProgramSlug }: { activeProgramSlug: string | null }) {
  // Defensive: this component only mounts when activeProgramSlug is null
  // (see showActivationCTA in HomeRenderer). The prop is retained for type
  // clarity at the call site.
  void activeProgramSlug;
  return (
    <div className="rounded-lg border border-dashed border-border/60 bg-card/50 px-6 py-8">
      <div className="max-w-xl">
        <h3 className="text-base font-medium text-foreground mb-2">
          No program activated yet
        </h3>
        <p className="text-sm text-muted-foreground mb-4">
          YARNNN runs your operations through programs — pre-shipped templates
          that bring a domain-shaped workspace (mandate, agents, recurrences,
          context structure). Get set up to see your operation rendered here.
        </p>
        {/* ADR-331 D6: the home empty-state CTA points to the guided /setup
            sequence (activate · author · connect · bring in reality), not the
            /program reference drawer. Home only POINTS to setup; it never grows
            setup chrome. */}
        <Link
          href="/setup"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          Get set up
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
