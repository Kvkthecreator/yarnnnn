'use client';

/**
 * useFileOrganizeVerbs — the ONE shared implementation of the operator's file
 * organize verbs (Rename / Move to… / Move to Trash), extracted from the Files
 * page so every surface that opens a file can offer the same three verbs against
 * the same backend, with the same optimistic model (ADR-400 Amendment 1 /
 * ADR-422 D2 / ADR-446).
 *
 * Why a hook, not inlined per surface: the verbs were born inside the Files page,
 * closed over its tree-refresh + selection state. Once files open into Studio
 * (ADR-446), the Studio surface needs the identical verbs — so the organize
 * LOGIC (modals + API calls + optimistic feedback + the carve pre-empt) lives
 * here, and each surface supplies only its own AFTER-effect via `onAfterMutate`.
 * Singular Implementation: the Files page and Studio call the same code; a fix
 * to the rename path (or the ADR-422 inbound/uploads carve) reaches both.
 *
 * The optimistic model (Windows-Explorer, ratified ADR-400): the verbs are NOT
 * defensively greyed. The operator invokes them; `carveGuard` pre-empts the
 * obvious carve (system/ + machine-config) with a nice modal, and the backend is
 * authoritative for the rest (403 → honest toast). The FE offers the action; the
 * backend decides. Inherits the ADR-422 D2 fix automatically — an uploaded file
 * under inbound/uploads/ IS organizable, so it renames/moves from any surface.
 *
 * Surface contract:
 *   const { verbs, modals } = useFileOrganizeVerbs({
 *     onAfterMutate: (newPath) => { ... },  // newPath = the file's new location,
 *                                           //   or null when it was trashed.
 *   });
 *   // spread `verbs` into a FileContextMenu / FileVerbs bundle, or call
 *   // verbs.onRename({ path, name }) directly from a surface-bar action.
 *   // render {modals} once at the end of the surface JSX.
 */

import { useCallback, useState } from 'react';
import { api, APIError } from '@/lib/api/client';
import { operatorCanOrganize, organizeBlockedReason } from '@/lib/workspace/ownership';
import { useFeedback } from '@/contexts/FeedbackContext';
import { MoveToFolderModal } from '@/components/workspace/MoveToFolderModal';
import { RenameModal } from '@/components/workspace/RenameModal';
import type { WorkspaceTreeNode } from '@/types';

export interface FileOrganizeTarget {
  path: string;
  name: string;
}

export interface UseFileOrganizeVerbsOptions {
  /**
   * Called after a successful mutation with the file's NEW path (`null` when the
   * file was moved to Trash) and the file's OLD path. The surface uses it to
   * re-point / refresh:
   *   - Files page: reload the explorer + re-select `newPath` (or clear
   *     selection when the trashed file WAS the selected one — hence `oldPath`).
   *   - Studio: re-point ?studio.file to `newPath`, or fall to the start state
   *     on null (the trashed artifact is gone).
   */
  onAfterMutate?: (newPath: string | null, oldPath: string) => void;
  /**
   * The workspace folder tree for the Move picker. Pass it when the surface
   * ALREADY holds the tree (the Files explorer) so we don't double-fetch; omit
   * it and the hook lazy-fetches its own lean tree on the first Move-open (the
   * Studio case, which holds no tree).
   */
  moveRoots?: WorkspaceTreeNode[];
}

export interface FileOrganizeVerbs {
  onRename: (t: FileOrganizeTarget) => void;
  onMove: (t: FileOrganizeTarget) => void;
  onDelete: (t: FileOrganizeTarget) => void;
  /**
   * Commit a move directly (from → destFolder), bypassing the picker modal —
   * the drag-and-drop fast path. `onMove` is the deliberate (modal) path; this
   * is the gesture path. Same API call, same optimistic feedback + onAfterMutate.
   */
  commitMove: (fromPath: string, destFolder: string) => Promise<void>;
}

export function useFileOrganizeVerbs(
  opts: UseFileOrganizeVerbsOptions = {},
): { verbs: FileOrganizeVerbs; modals: React.ReactNode } {
  const { onAfterMutate, moveRoots: providedRoots } = opts;
  const { confirm, runAction } = useFeedback();

  const [renameTarget, setRenameTarget] = useState<FileOrganizeTarget | null>(null);
  const [moveTarget, setMoveTarget] = useState<FileOrganizeTarget | null>(null);

  // The Move picker needs the workspace folder tree (WorkspaceTreeNode[]). When
  // the surface already holds it (Files explorer via `moveRoots`), use that; else
  // lazy-fetch our own lean tree on the first Move-open — a surface (e.g. Studio)
  // that never moves never pays for it. The modal lazy-navigates these nodes.
  const [fetchedRoots, setFetchedRoots] = useState<WorkspaceTreeNode[] | null>(null);
  const loadMoveRoots = useCallback(async () => {
    try {
      const roots = await api.workspace.getRoots();
      const subtrees = await Promise.all(
        roots.map(async (r) => {
          if (!r.exists) return { root: r, tree: [] as WorkspaceTreeNode[] };
          const tree = await api.workspace.getTree(r.path).catch(() => [] as WorkspaceTreeNode[]);
          return { root: r, tree };
        }),
      );
      // Present each real root as a folder node carrying its subtree — enough for
      // the picker to navigate into (it only walks folder children).
      const nodes: WorkspaceTreeNode[] = subtrees.map(({ root, tree }) => ({
        name: root.display_name || root.name,
        path: root.path,
        type: 'folder',
        children: tree,
      }));
      setFetchedRoots(nodes);
    } catch {
      setFetchedRoots([]); // an empty picker still lets the operator cancel cleanly
    }
  }, []);

  // Pre-empt the obvious carve (system/ + machine-config) with a plain,
  // macOS-style modal before we call the backend. Returns true if blocked.
  // inbound/uploads/ is NOT a carve (ADR-422 D2) — the operator owns uploads.
  const carveGuard = useCallback(
    async (path: string): Promise<boolean> => {
      if (operatorCanOrganize(path)) return false;
      const { title, body } = organizeBlockedReason(path);
      await confirm({ title, body, confirmLabel: 'OK', cancelLabel: '' });
      return true;
    },
    [confirm],
  );

  const onRename = useCallback(
    async (t: FileOrganizeTarget) => {
      if (await carveGuard(t.path)) return;
      setRenameTarget(t);
    },
    [carveGuard],
  );

  const commitRename = useCallback(
    async (t: FileOrganizeTarget, nextLeaf: string) => {
      const parent = t.path.slice(0, t.path.lastIndexOf('/'));
      const newPath = `${parent}/${nextLeaf}`;
      if (newPath === t.path) return;
      try {
        const r = await runAction(() => api.documents.move(t.path, newPath), {
          pending: 'Renaming…',
          success: 'Renamed',
          error: (e) =>
            e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Rename failed' : 'Rename failed',
        });
        onAfterMutate?.(r?.path ?? newPath, t.path);
      } catch {
        /* error toast already surfaced; stop (don't refresh on failure) */
      }
    },
    [runAction, onAfterMutate],
  );

  const onMove = useCallback(
    async (t: FileOrganizeTarget) => {
      if (await carveGuard(t.path)) return;
      // Fetch our own tree only if the surface didn't provide one.
      if (!providedRoots && fetchedRoots === null) void loadMoveRoots();
      setMoveTarget(t);
    },
    [carveGuard, providedRoots, fetchedRoots, loadMoveRoots],
  );

  const commitMove = useCallback(
    async (fromPath: string, destFolder: string) => {
      const leaf = fromPath.slice(fromPath.lastIndexOf('/') + 1);
      const newPath = destFolder.endsWith('/') ? `${destFolder}${leaf}` : `${destFolder}/${leaf}`;
      if (newPath === fromPath) return;
      try {
        const r = await runAction(() => api.documents.move(fromPath, newPath), {
          pending: 'Moving…',
          success: 'Moved',
          error: (e) =>
            e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Move failed' : 'Move failed',
        });
        onAfterMutate?.(r?.path ?? newPath, fromPath);
      } catch {
        /* error toast already surfaced; stop */
      }
    },
    [runAction, onAfterMutate],
  );

  const onDelete = useCallback(
    async (t: FileOrganizeTarget) => {
      if (await carveGuard(t.path)) return;
      // ADR-448: the load-bearing check — if other files were made FROM this one
      // (the derived_from reference edge), say so before the operator confirms.
      // A warning, never a block: delete stays reversible trash, and dependents
      // keep working from history. Best-effort — a lookup failure warns nothing.
      let dependentsLine = '';
      try {
        const deps = await api.documents.dependents(t.path);
        if (deps.count > 0) {
          dependentsLine =
            deps.count === 1
              ? ' One other file was made from this one — it keeps its history, but its live reference will point at the Trash.'
              : ` ${deps.count} other files were made from this one — they keep their history, but their live references will point at the Trash.`;
        }
      } catch {
        /* legibility is best-effort */
      }
      const ok = await confirm({
        title: `Move “${t.name}” to Trash?`,
        body: `It stays recoverable — you can restore it from Trash any time.${dependentsLine}`,
        confirmLabel: 'Move to Trash',
        danger: true,
      });
      if (!ok) return;
      try {
        await runAction(() => api.documents.delete(t.path), {
          pending: 'Moving to Trash…',
          success: 'Moved to Trash',
          error: (e) =>
            e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Delete failed' : 'Delete failed',
        });
        onAfterMutate?.(null, t.path); // trashed — the file is gone
      } catch {
        /* error toast already surfaced; stop */
      }
    },
    [carveGuard, confirm, runAction, onAfterMutate],
  );

  const modals = (
    <>
      <MoveToFolderModal
        target={moveTarget}
        roots={providedRoots ?? fetchedRoots ?? []}
        canOrganize={operatorCanOrganize}
        onClose={() => setMoveTarget(null)}
        onMove={async (destFolder) => {
          const t = moveTarget;
          setMoveTarget(null);
          if (t) await commitMove(t.path, destFolder);
        }}
      />
      <RenameModal
        target={renameTarget}
        onClose={() => setRenameTarget(null)}
        onSubmit={async (nextLeaf) => {
          const t = renameTarget;
          setRenameTarget(null);
          if (t) await commitRename(t, nextLeaf);
        }}
      />
    </>
  );

  return { verbs: { onRename, onMove, onDelete, commitMove }, modals };
}
