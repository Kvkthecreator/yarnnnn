'use client';

/**
 * SupervisorSurface — the Supervisor app's pane (ADR-656 §7).
 *
 * THE FIRST COMPOSED SURFACE IN YARNNN: its shape is DECLARED (the sections
 * below) rather than mirrored from one substrate concern. That is the register
 * ADR-435 declined to name and ADR-653 D3.a promoted, and this is its first
 * tenant — which is what makes the promotion load-bearing rather than
 * decorative.
 *
 * ⭐ IT REDIRECTS TO NOTHING, which is the test ADR-435 set and the last
 * composition (Home) failed: its six slots each deep-linked to a mirror that
 * already owned the concept. Here, Files shows files, Chat shows ONE
 * conversation, Notifications shows what already happened — and none of them
 * answers *what is underway*.
 *
 * THE THREE BANDS (APP-BUILDER-UX §2.2, the part that survived the re-scope):
 *   1. what this is      — the name and the one-line claim
 *   2. who is minding it — the resident, named
 *   3. the work          — the declared sections
 *
 * ⚠️ BAND 2 IS THE RESTING STATE ONLY. "Supervisor looks after this" is a
 * complete, reassuring sentence — someone is on it and there is nothing to do.
 * The working and raising states (§4) need the resident read and are not built;
 * the discipline they encode is already here in band 3's copy, which says
 * "Nothing is waiting on you" rather than "No items".
 */

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import {
  SupervisorSection,
  type SupervisorSectionDecl,
  type SupervisorStateData,
} from '@/components/supervisor/SupervisorSection';
import { Working } from '@/components/shared/Working';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

/**
 * The app's declared sections.
 *
 * ⚠️ DECLARED, not hardcoded rendering: the surface renders whatever this list
 * says, through the dispatch — which is the whole difference between a composed
 * surface and a bespoke one. A kind this client cannot draw renders the honest
 * amber miss rather than a blank.
 *
 * ⭐ Ordered by URGENCY, not by size. What is waiting on the member comes
 * first because band 3's job is to answer "what do I do next"; the decisions
 * note is last because it is reference, not a call to act.
 */
const SECTIONS: SupervisorSectionDecl[] = [
  { kind: 'needs-you', title: 'Waiting on you' },
  { kind: 'threads', title: 'Underway' },
  { kind: 'note', title: 'What we decided' },
];

export function SupervisorSurface() {
  const [data, setData] = useState<SupervisorStateData | null>(null);
  const [failed, setFailed] = useState(false);
  const { navigateToSurface } = useSurfacePreferences();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await api.supervisor.state();
        if (cancelled) return;
        // Defensive: a read path never trusts the served shape (house style).
        setData({
          needs_you: Array.isArray(result?.needs_you) ? result.needs_you : [],
          threads: Array.isArray(result?.threads) ? result.threads : [],
          note: result?.note ?? null,
        });
      } catch {
        if (cancelled) return;
        setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Opening a thread is the ONE act this surface has, and it is a navigation
  // rather than a mutation — the supervisor does the work of no thread.
  const openLane = useCallback(
    (laneId: string) => {
      navigateToSurface('chat', { lane: laneId });
    },
    [navigateToSurface],
  );

  if (failed) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          Couldn&apos;t read what&apos;s underway just now.
        </div>
      </div>
    );
  }
  // ADR-651 — the ONE way to say wait, self-bounding at 6s and 30s.
  if (!data) return <Working label="Loading…" fill />;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Band 1 — the visible claim. */}
      <header className="border-b border-border/60 px-5 py-4">
        <h1 className="text-[15px] font-semibold text-foreground">Supervisor</h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          What is underway, and what needs you.
        </p>
      </header>

      {/* Band 2 — who is minding it. Resting: calm, not absent. */}
      <div className="border-b border-border/60 bg-muted/20 px-5 py-2.5">
        <p className="text-[13px] text-foreground/80">Supervisor looks after this.</p>
      </div>

      {/* Band 3 — the declared sections. */}
      <div className="flex-1 space-y-5 px-5 py-4">
        {SECTIONS.map((section) => (
          <SupervisorSection
            key={section.kind}
            section={section}
            data={data}
            onOpenLane={openLane}
          />
        ))}
      </div>
    </div>
  );
}
