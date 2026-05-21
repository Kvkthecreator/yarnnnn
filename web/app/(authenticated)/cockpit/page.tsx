'use client';

/**
 * /cockpit — atomic Cockpit surface (ADR-297 D1, 13th kernel surface).
 *
 * Renders the live operating dashboard via CockpitRenderer (preserves
 * ADR-228 four-face stack + ADR-273 program-section overrides intact).
 * Replaces what was the dashboard tab of the now-dissolved /work surface.
 */

import { CockpitRenderer } from '@/components/library/CockpitRenderer';
import { useNarrative } from '@/contexts/NarrativeContext';

export default function CockpitPage() {
  const { sendMessage } = useNarrative();
  return (
    <div className="h-full overflow-y-auto">
      <CockpitRenderer onOpenChatDraft={sendMessage} />
    </div>
  );
}
