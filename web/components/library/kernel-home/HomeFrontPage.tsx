'use client';

/**
 * HomeFrontPage — the kernel-shaped front page (ADR-369 §D4, the default "Home"
 * tab of the split Home surface).
 *
 * ADR-369 re-splits ADR-312's one-composition Home into two internal tabs along
 * the kernel-shaped vs program-shaped seam (the layout/component seam the code
 * already drew). This body holds the KERNEL-shaped slots — rendered identically
 * for every workspace regardless of program, the most learnable possible
 * default. The program-shaped slots (ground-truth hero, live entities, the
 * relocated standing band) live in ProgramCockpit (the additive program tab).
 *
 * §D4 order — a calm Layer-1 front page ordered "what needs me / what's
 * been happening":
 *   #1 Constitution band  — HomeHeader (kernel, always). Mandate one-liner +
 *                           autonomy posture. Shape tiebreaker (§D1): declaring
 *                           a mandate is "Layer 2" in the product story, but the
 *                           band's RENDERING shape is kernel-generic, so it
 *                           stays on Home.
 *   #2 Decision queue     — KernelDecisionQueue (kernel-universal; ADR-307).
 *                           Acts in place via the shared proposal modal
 *                           (ADR-367, preserved) — the first substantive
 *                           section: what needs your OK.
 *   #3 Timeline           — WorkspaceTimeline (kernel-universal; ADR-408 D5.1).
 *                           ONE chronological, attributed stream across the
 *                           three act ledgers (revisions + invocations +
 *                           proposals) — the commons made legible: every
 *                           actor, attributed.
 *   #4 Recents (visual)   — HomeRecents (kernel; ADR-369 §D4/§D6). A card glance
 *                           of recent attributed substrate changes — the
 *                           Files-recents data source, visualized. Distinct from
 *                           recent artifacts (§D6).
 *   #5 Recent artifacts   — KernelRecentArtifacts (kernel-universal). Delivered
 *                           outputs ("the dividends").
 *   #6 Judgment trail     — KernelJudgmentTrail (kernel-universal). The
 *                           Reviewer's recent calls.
 *
 * Each kernel slot self-hides when its substrate is empty, so the cold-start
 * Home stays honest (constitution-band CTA + only the slots with content yet).
 *
 * Singular Implementation: these are the SAME slot components ADR-312/367
 * wired — ADR-369 moves their mounts here (out of HomeRenderer) and reorders
 * per §D4; it does not rebuild them.
 */

import { ArrowRight } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { HomeHeader } from '../HomeHeader';
import { KernelDecisionQueue } from './KernelDecisionQueue';
import { WorkspaceTimeline } from './WorkspaceTimeline';
import { KernelRecentArtifacts } from './KernelRecentArtifacts';
import { KernelJudgmentTrail } from './KernelJudgmentTrail';
import { HomeRecents } from './HomeRecents';
import type { api } from '@/lib/api/client';

type HomeBundle = Awaited<ReturnType<typeof api.workspace.getHomeBundle>>;

interface HomeFrontPageProps {
  /** The ADR-312 home-bundle (primes every kernel slot). Null → slots self-fetch. */
  bundle: HomeBundle | null;
  /** When true, the cold-start CTA shows (no program activated, nothing yet). */
  showActivationCTA: boolean;
  activeProgramSlug: string | null;
}

export function HomeFrontPage({
  bundle,
  showActivationCTA,
  activeProgramSlug,
}: HomeFrontPageProps) {
  return (
    <>
      {/* #1 — Constitution band (kernel, always; shape tiebreaker §D1) */}
      <HomeHeader
        initialMandate={bundle?.mandate}
        initialAutonomy={bundle?.autonomy_yaml}
      />

      <div className="flex flex-col gap-5 px-4 py-5 sm:px-6 sm:py-6 bg-muted/20">
        {/* #2 — Decision queue (kernel-universal; self-hides). ADR-367: acts in
            place — rows open the shared proposal modal (approve/reject through
            the ADR-307 gate) without leaving Home. */}
        <KernelDecisionQueue initialProposals={bundle?.proposals} />

        {/* #3 — Timeline: the workspace's one chronological attributed act
            stream (revisions + invocations + proposals; ADR-408 D5.1).
            Self-hides. */}
        <WorkspaceTimeline />

        {/* #4 — Recents (visual): recent attributed substrate changes, the
            Files-recents data visualized (ADR-369 §D4/§D6). Self-hides. */}
        <HomeRecents />

        {/* #5 — Recent artifacts (kernel-universal; self-hides) */}
        <KernelRecentArtifacts initialArtifacts={bundle?.recent_artifacts} />

        {/* #6 — Judgment trail (kernel-universal; self-hides) */}
        <KernelJudgmentTrail initialContent={bundle?.judgment_log} />

        {/* Cold-start CTA — only when there is nothing else to show */}
        {showActivationCTA && (
          <UnactivatedHomeCTA activeProgramSlug={activeProgramSlug} />
        )}
      </div>
    </>
  );
}

/**
 * UnactivatedHomeCTA — the cold-start home's empty state (ADR-312 D6).
 * The home doubles as onboarding: a bare kernel (no program activated, no
 * universal substrate yet) renders the "activate a program" affordance.
 *
 * Renders ONLY when no program is activated (see showActivationCTA in
 * HomeRenderer). An activated program shows its sections on the program tab +
 * the kernel-universal slots here, so there is no dead-end Home.
 */
function UnactivatedHomeCTA({ activeProgramSlug }: { activeProgramSlug: string | null }) {
  // Defensive: this component only mounts when activeProgramSlug is null. The
  // prop is retained for type clarity at the call site.
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
        <SurfaceLink
          to="setup"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          Get set up
          <ArrowRight className="h-3.5 w-3.5" />
        </SurfaceLink>
      </div>
    </div>
  );
}
