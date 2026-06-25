'use client';

/**
 * ProgramCockpit — the program-shaped operating cockpit (ADR-369 §D5, the
 * additive "‹Program›" tab of the split Home surface).
 *
 * ADR-369 re-splits ADR-312's one-composition Home along the kernel-shaped vs
 * program-shaped seam. This body holds the PROGRAM-shaped slots — declared by
 * the active program via SURFACES.yaml `home.program_sections` and rendered
 * through the compositor seam (dispatched by section `kind`). It mounts ONLY
 * when a program is active (the tab is additive — see HomeRenderer), so a
 * Layer-1 operator never faces this view (ADR-312's cold-start virtue preserved).
 *
 * Head: the ADR-350 StandingBand RELOCATES here from Home's head (ADR-369 §D5,
 * amends ADR-367 §D4). The standing obligation is program-derived
 * (budget→pace × mandate→output kind+volume × bar — ADR-344/DP30), so under the
 * shape axis it is program-shaped. Singular Implementation: StandingBand is the
 * SAME zero-prop self-hiding body that also mounts in the Notifications resolve
 * pane (one body, two mounts) — ADR-369 moves the Home mount here, it does not
 * fork the component.
 *
 * §D5: Home is the calm front page; the program tab is the dense operating
 * cockpit ("robust and detailed, acts in place"). ADR-367's "acts in place"
 * principle spans both tabs — the program tab acts in place on its own
 * consequential affordances (its program-section components own that).
 */

import { dispatchComponent } from '../registry';
import { StandingBand } from '@/components/queue/StandingBand';

interface ProgramCockpitProps {
  /** The active program's `home.program_sections` (ordered hero + entities). */
  programSections: Array<{ kind: string; order: number }>;
}

export function ProgramCockpit({ programSections }: ProgramCockpitProps) {
  return (
    <div className="flex flex-col gap-4 px-4 py-5 sm:px-6 sm:py-6 bg-muted/20">
      {/* §D5 — Standing obligation at the cockpit head: what the operation is on
          the hook for (owed-vs-actual + the Reviewer's standing intent).
          Relocated from Home (ADR-367 §D4 → ADR-369 §D5). Reads persona/
          governance substrate, never writes it (ADR-320); self-hides when
          empty. */}
      <StandingBand />

      {/* Slots #2 + #4 — program-declared ground-truth hero + live entities,
          dispatched through the compositor seam by `kind`. */}
      {programSections.map((section, i) => (
        <div key={`${section.kind}-${i}`}>
          {dispatchComponent({ kind: section.kind }, {})}
        </div>
      ))}
    </div>
  );
}
