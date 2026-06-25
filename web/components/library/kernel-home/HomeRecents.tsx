'use client';

/**
 * HomeRecents — the Home front page's "Recents" slot (ADR-369 §D4 slot #3 + §D6).
 *
 * Thin wrapper over the shared <RecentsView> (extracted 2026-06-25). The
 * operator asked for a consistent Finder/Explorer view between the Files-recents
 * and the Home-recents — so this and the Files mount now render the IDENTICAL
 * component (icon/list view + shared file-type icons + per-operator view toggle,
 * default icon). Singular Implementation: one recency renderer, two mounts.
 *
 * Same DATA SOURCE as the Files Recents (the ADR-209 revision chain via
 * `api.workspace.recentRevisions`). DISTINCT from KernelRecentArtifacts
 * (ADR-369 §D6): Recents = broad recent substrate changes; recent artifacts =
 * the narrow set of delivered outputs.
 *
 * Home-mount specifics:
 *   - `hideWhenEmpty` — kernel-slot contract (self-hide when nothing yet,
 *     ADR-312 D2), instead of the Files center-pane cold-start empty state.
 *   - no `onSelectPath` — RecentsView deep-links each row to the Files surface
 *     (the front page glances; the explorer is where you dwell).
 *   - a front-page glance loads fewer rows than the Files explorer (which loads 30).
 */

import { RecentsView } from '@/components/workspace/RecentsView';

export function HomeRecents() {
  return (
    <RecentsView
      limit={12}
      hideWhenEmpty
      subtitle="recent changes across your workspace"
    />
  );
}
