'use client';

/**
 * AgentsSurface — deliberately EMPTY (ADR-599, 2026-08-24, operator ruling).
 *
 * The free-floating colleague roster (Thinker · Researcher · Designer-as-
 * colleague · Critic) and the member-agent machinery ("Make one", manifests,
 * skills) are DELETED — not hidden — until the roster returns as app-paired
 * agents on the ADR-596 scaffold (identity ⊕ character ⊕ engine; authority,
 * clock and judgment on grants, declarations, and gates — never on beings).
 *
 * What agents exist today are APP RESIDENTS (ADR-598): Designer at Slides,
 * Editor at Text, Keeper at Strings — each met at its own desk, none offered
 * for hire. The roster's question ("who do you want to work with?") currently
 * has no population, and this surface says so honestly rather than rendering
 * furniture as colleagues.
 *
 * The surface stays mounted (the shell registers it; the route is real) so
 * the empty state is a STATEMENT, not a 404 — the ADR-572 lesson: a refusal
 * documented only in canon is invisible; the surface has to say it where the
 * absence is felt.
 */

import { Users } from 'lucide-react';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';

export function AgentsSurface() {
  useWindowCrumb('agents', []);

  return (
    <div className="h-full grid place-items-center px-6">
      <div className="max-w-md text-center space-y-3">
        <div className="mx-auto w-10 h-10 rounded-full bg-muted grid place-items-center">
          <Users className="w-5 h-5 text-muted-foreground" />
        </div>
        <h2 className="text-sm font-medium">No agents to hire yet</h2>
        <p className="text-xs text-muted-foreground leading-relaxed">
          The colleagues you work with today live in their apps — Designer in
          Slides, Editor in Text, Keeper in Strings. A roster of agents you can
          hire and name will return here once the agent-and-app scaffolding
          settles.
        </p>
      </div>
    </div>
  );
}
