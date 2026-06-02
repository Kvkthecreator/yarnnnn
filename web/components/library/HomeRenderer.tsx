'use client';

/**
 * HomeRenderer — renamed from CockpitRenderer by ADR-312 D1.
 *
 * The Home is a composition over the workspace's present constituents
 * (ADR-312 §1–2). Post-ADR-273 it renders two visual layers; ADR-312 P4
 * reshapes Layer 2 into the six-slot kernel home contract. P3 (this
 * commit) is a pure rename — the structure below is preserved verbatim
 * from CockpitRenderer.
 *
 *   Layer 1 — HomeHeader (the Constitution band, slot #1; kernel-general,
 *               always rendered) — mandate one-liner + autonomy posture,
 *               read from /workspace/context/_shared/{MANDATE.md,
 *               _autonomy.yaml}. Present on every workspace whether or not
 *               a program is activated.
 *
 *   Layer 2 — program_sections (program-specific) OR UnactivatedHomeCTA.
 *               When the active bundle's SURFACES.yaml declares
 *               home.program_sections[], each section renders in `order`
 *               sequence below HomeHeader. When no program is activated
 *               (active_program_slug == null), the UnactivatedHomeCTA
 *               renders an explicit "Activate a program" affordance —
 *               this is the honest Phase-1 cold-start home (ADR-312 D6).
 *
 * Singular implementation per ADR-273 D2 (preserved):
 *   - The legacy four-face fallback (MoneyTruthFace / PerformanceFace /
 *     TrackingFace / MandateFace) was DELETED in ADR-273. ADR-312 confirms
 *     the deletion — the cold-start home is the constitution-band CTA, not
 *     a de-activated trader dashboard.
 *   - getProgramSections() returning empty + no active_program_slug =>
 *     the operator hasn't picked a program yet => render the activation
 *     CTA. There is no third path.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { HomeProvider } from './HomeContext';
import { HomeHeader } from './HomeHeader';
import { useComposition, getProgramSections } from '@/lib/compositor';
import { dispatchComponent } from './registry';
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

  return (
    <HomeProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section aria-label="Home" className="border-b border-border/60">
        <HomeHeader />
        {hasProgramSections ? (
          <div className="flex flex-col gap-4 px-6 py-6 bg-muted/20">
            {programSections.map((section) =>
              dispatchComponent({ kind: section.kind }, {})
            )}
          </div>
        ) : stateLoaded ? (
          <UnactivatedHomeCTA activeProgramSlug={activeProgramSlug} />
        ) : null}
      </section>
    </HomeProvider>
  );
}

/**
 * UnactivatedHomeCTA — the cold-start home's constitution-band empty state
 * (ADR-312 D6). The home doubles as onboarding: a bare kernel renders the
 * "declare what this workspace is for / activate a program" affordance.
 *
 * Two states:
 *   - active_program_slug == null: operator has not picked a program;
 *     deep-link to the Program surface where the picker lives.
 *   - active_program_slug != null: program activated but its SURFACES.yaml
 *     declares no home.program_sections (unlikely but defensive). Show a
 *     milder message acknowledging the activation.
 */
function UnactivatedHomeCTA({ activeProgramSlug }: { activeProgramSlug: string | null }) {
  const hasActivation = !!activeProgramSlug;
  return (
    <div className="px-6 py-8 bg-muted/20">
      <div className="rounded-lg border border-dashed border-border/60 bg-card/50 px-6 py-8">
        <div className="max-w-xl">
          <h3 className="text-base font-medium text-foreground mb-2">
            {hasActivation
              ? `Program activated — ${activeProgramSlug}`
              : 'No program activated yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {hasActivation
              ? 'This program does not declare a home dashboard. Configure your operation from the Program surface, or use the chat to set things up.'
              : 'YARNNN runs your operations through programs — pre-shipped templates that bring a domain-shaped workspace (mandate, agents, recurrences, context structure). Activate one to see your operation rendered here.'}
          </p>
          <Link
            href="/program"
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            {hasActivation ? 'Manage program' : 'Activate a program'}
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}
