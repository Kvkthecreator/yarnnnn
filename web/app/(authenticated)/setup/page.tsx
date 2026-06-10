'use client';

/**
 * /setup — the guided first-boot Sequence surface (ADR-331 D1/D2).
 *
 * macOS Setup Assistant: thin, guided, ordered, re-enterable. Renders the
 * SetupSequence over `api.workspace.getState()` — the SAME composition the
 * `/program` reference drawer (System Settings) presents random-access. One
 * substrate, two presentation registers; no stored wizard state.
 *
 * This is the first-run redirect target (auth/callback) and the Home
 * empty-state CTA destination. Summon-only after first run.
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import { SurfacePage } from '@/components/shell/SurfacePage';
import { SetupSequence } from '@/components/library/SetupSequence';

export default function SetupPage() {
  return (
    <SurfacePage
      iconKey="rocket"
      title="Setup"
      summary="Activate a program, author your constitution, connect platforms, bring in your reality — in order, or out of order. Each step is done the moment your workspace says so."
    >
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        }
      >
        <SetupSequence />
      </Suspense>
    </SurfacePage>
  );
}
