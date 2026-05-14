'use client';

/**
 * CockpitRenderer — ADR-273 program-section-only dispatch.
 *
 * Post-ADR-273 Phase 2 the cockpit is two visual layers:
 *
 *   Layer 1 — CockpitHeader (kernel-general, always rendered)
 *               mandate title + summary + autonomy posture, read from
 *               /workspace/context/_shared/{MANDATE.md, AUTONOMY.md}.
 *               Surface stays present on every workspace whether or not
 *               a program is activated.
 *
 *   Layer 2 — program_sections (program-specific) OR UnactivatedCTA.
 *               When the active bundle's SURFACES.yaml declares
 *               cockpit.program_sections[], each section renders in
 *               `order` sequence below CockpitHeader. When no program
 *               is activated (active_program_slug == null), the
 *               UnactivatedCockpitCTA renders an explicit "Activate a
 *               program from Settings → Workspace" affordance instead.
 *
 * Singular implementation per ADR-273 D2:
 *   - The legacy four-face fallback (MoneyTruthFace / PerformanceFace /
 *     TrackingFace / MandateFace) was DELETED in this phase. These were
 *     never rendered for any workspace with an active program; for the
 *     no-program-activated state they were placeholder noise rather than
 *     a useful operator surface.
 *   - getProgramSections() returning empty + no active_program_slug =>
 *     the operator hasn't picked a program yet => render the activation
 *     CTA. There is no third path.
 *   - getProgramSections() returning empty + active_program_slug present
 *     would mean an activated program declares no cockpit sections; we
 *     render the activation banner as a graceful empty state (this should
 *     not happen for any shipped program but is the safest fallback).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { CockpitProvider } from './CockpitContext';
import { CockpitHeader } from './CockpitHeader';
import { useComposition, getProgramSections } from '@/lib/compositor';
import { dispatchComponent } from './registry';
import { api } from '@/lib/api/client';

interface CockpitRendererProps {
  /**
   * Chat-draft handler. Forwarded into CockpitContext so any future
   * cockpit section can call sendMessage() without prop-drilling.
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function CockpitRenderer({ onOpenChatDraft }: CockpitRendererProps) {
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
        // operator can still navigate to Settings → Workspace.
      } finally {
        if (!cancelled) setStateLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hasProgramSections]);

  return (
    <CockpitProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section aria-label="Cockpit" className="border-b border-border/60">
        <CockpitHeader />
        {hasProgramSections ? (
          <div className="flex flex-col gap-4 px-6 py-6 bg-muted/20">
            {programSections.map((section) =>
              dispatchComponent({ kind: section.kind }, {})
            )}
          </div>
        ) : stateLoaded ? (
          <UnactivatedCockpitCTA activeProgramSlug={activeProgramSlug} />
        ) : null}
      </section>
    </CockpitProvider>
  );
}

/**
 * UnactivatedCockpitCTA — replaces the deleted four-face fallback.
 *
 * Two states:
 *   - active_program_slug == null: operator has not picked a program;
 *     deep-link to Settings → Workspace where the program picker lives.
 *   - active_program_slug != null: program activated but its SURFACES.yaml
 *     declares no cockpit.program_sections (unlikely but defensive). Show
 *     a milder message acknowledging the activation.
 */
function UnactivatedCockpitCTA({ activeProgramSlug }: { activeProgramSlug: string | null }) {
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
              ? 'This program does not declare a cockpit dashboard. Configure your operation from Settings → Workspace, or use the chat to set things up.'
              : 'YARNNN runs your operations through programs — pre-shipped templates that bring a domain-shaped workspace (mandate, agents, recurrences, context structure). Activate one to see your operation rendered here.'}
          </p>
          <Link
            href="/settings?tab=workspace"
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
