'use client';

/**
 * /sources — atomic Sources surface (ADR-338 D4.1).
 *
 * The standing-watch "drivers" view (ADR-338 D2 — register: os-config). Renders
 * the active program's web/RSS watch sources (_sources.yaml) via the
 * kernel-library SourcesCard: the operator's declared source list (editable)
 * paired with per-source observed health from the distilled signal substrate
 * (_watch_signal.yaml) — the Check-7 declared-vs-observed shape.
 *
 * Declaring a watch source changes what the operation PERCEIVES — above the
 * consent line (ADR-338 D3), so it gets first-class surface rather than living
 * only as hand-edited YAML in Files. Empty when no active bundle declares a
 * watch (honest empty state; uploads + websearch remain context-in).
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { SourcesCard } from '@/components/workspace-concepts/SourcesCard';

export default function SourcesPage() {
  return (
    <SurfacePage
      iconKey="rss"
      title="Sources"
      summary="Your standing watch — the web/RSS feeds the operation reads on cadence. Declared sources, paired with what was last observed from each. A portfolio of attention, not a crawler."
    >
      <SourcesCard variant="full" />
    </SurfacePage>
  );
}
