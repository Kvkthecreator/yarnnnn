'use client';

/**
 * RecentRevisions — the Files "Recents" view (ADR-329 Amendment 2, 2026-06-19).
 *
 * Thin wrapper over the shared <RecentsView> (extracted 2026-06-25). This is the
 * Files surface's center-pane empty state: the workspace-wide recency view that
 * fills the pane when no node is selected (Finder's Recents). It and the Home
 * front-page Recents now render the IDENTICAL component (icon/list view + shared
 * file-type icons + the per-operator view toggle) — Singular Implementation, one
 * recency renderer. The Files mount passes `onSelectPath` because selection here
 * is component state (the page owns it, never a URL write per ADR-297 D19.2).
 *
 * Reads the ADR-209 revision chain (workspace_file_versions) via
 * GET /api/workspace/recent-revisions. Layer-1-only (ADR-328 D6).
 */

import { RecentsView } from './RecentsView';
import type { FileVerbs } from './FileContextMenu';

interface RecentRevisionsProps {
  /** Navigate to a file path (the page owns selection + URL sync). */
  onSelectPath: (path: string) => void;
  /** ADR-400: the operator's file verbs → right-click menu on the main panel. */
  verbs?: FileVerbs;
}

export function RecentRevisions({ onSelectPath, verbs }: RecentRevisionsProps) {
  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <RecentsView limit={30} onSelectPath={onSelectPath} verbs={verbs} />
    </div>
  );
}
