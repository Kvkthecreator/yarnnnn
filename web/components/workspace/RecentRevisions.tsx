'use client';

/**
 * RecentRevisions — the Files "Recents" view (ADR-329 Amendment 2, 2026-06-19).
 *
 * Thin wrapper over the shared <RecentsView>: the Files surface's centre-pane
 * empty state, the workspace-wide recency view that fills the pane when nothing
 * is open (Finder's Recents).
 *
 * It is a FILE BROWSER, not a set of links — a grid/list of files gathered by
 * recency rather than by folder — so it carries the IDENTICAL click grammar the
 * folder listing carries (2026-08-20): single click selects, ⌘/Ctrl toggles,
 * shift ranges, double click opens, Escape/background clears, coarse pointer
 * opens on one tap. The props below are the same contract `ContentViewer` takes,
 * threaded straight through: the renderer reports the intent, the SURFACE
 * applies the grammar.
 *
 * Reads the ADR-209 revision chain (workspace_file_versions) via
 * GET /api/workspace/recent-revisions. Layer-1-only (ADR-328 D6).
 */

import { RecentsView } from './RecentsView';
import type { FileVerbs } from './FileContextMenu';
import type { FileClickIntent } from '@/types';

interface RecentRevisionsProps {
  /** The click, reported as an intent. The surface decides what it means. */
  onNavigate: (path: string, e?: FileClickIntent) => void;
  /** The picked SET — every member rings. */
  selection?: readonly string[];
  /** Publish the RECENCY order, so a shift-range runs over what is drawn. */
  onPublishOrder?: (paths: string[]) => void;
  /** A click on the grid's empty ground clears the selection. */
  onClearSelection?: () => void;
  /** A right-click outside the selection re-scopes it to that row. */
  onSelectRow?: (path: string) => void;
  /** ADR-400: the operator's file verbs → right-click menu on the main panel. */
  verbs?: FileVerbs;
}

export function RecentRevisions({
  onNavigate,
  selection,
  onPublishOrder,
  onClearSelection,
  onSelectRow,
  verbs,
}: RecentRevisionsProps) {
  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <RecentsView
        limit={30}
        onNavigate={onNavigate}
        selection={selection}
        onPublishOrder={onPublishOrder}
        onClearSelection={onClearSelection}
        onSelectRow={onSelectRow}
        verbs={verbs}
      />
    </div>
  );
}
