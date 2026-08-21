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
  /**
   * True when the target is a FOLDER (2026-08-21). A folder verb is a FAN-OUT
   * over the subtree, not one act — since ADR-588 a folder is a marker row plus
   * whatever files share its path prefix, so there is no single row to rename,
   * move, or archive. The three verbs below therefore take a DIFFERENT backend
   * route when this is set (`folder/move`, `folder/trash`), and report the
   * honest partial the fan produces.
   *
   * OPTIONAL and absent-means-file, deliberately. Four of the five surfaces
   * that call this hook (Studio ×2, Text ×2) open FILES and can never hold a
   * folder target; requiring the flag would make them all restate a fact their
   * surface guarantees. Only the Files browser, which shows both, sets it.
   */
  isFolder?: boolean;
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
  /** ADR-514 D1 — derive a sibling copy (kernel-resolved name + derived_from). */
  onDuplicate: (t: FileOrganizeTarget) => void;
  /**
   * Commit a move directly (from → destFolder), bypassing the picker modal —
   * the drag-and-drop fast path. `onMove` is the deliberate (modal) path; this
   * is the gesture path. Same API call, same optimistic feedback + onAfterMutate.
   */
  commitMove: (fromPath: string, destFolder: string, isFolder?: boolean) => Promise<void>;
  /** Move a SET into one folder — reports which half landed (ADR-553 D2). */
  commitMoveMany: (
    fromPaths: string[],
    destFolder: string,
  ) => Promise<{ moved: string[]; failed: string[] }>;
}

export function useFileOrganizeVerbs(
  opts: UseFileOrganizeVerbsOptions = {},
): { verbs: FileOrganizeVerbs; modals: React.ReactNode } {
  const { onAfterMutate, moveRoots: providedRoots } = opts;
  const { confirm, runAction } = useFeedback();

  const [renameTarget, setRenameTarget] = useState<FileOrganizeTarget | null>(null);
  const [moveTarget, setMoveTarget] = useState<FileOrganizeTarget | null>(null);

  // The Move picker needs the workspace folder tree (WorkspaceTreeNode[]). When
  // the surface already holds it (Files explorer via `moveRoots`), pass it down so
  // we don't double-fetch. Otherwise pass NOTHING and let `WorkspacePicker` do its
  // own lazy fetch — it owns that grammar once (2026-07-20 collapse). This hook
  // used to carry a second, byte-identical copy of the getRoots+getTree walk; it
  // also handed the modal a non-undefined `[]` while that fetch was in flight,
  // which read as "No folders to move into." instead of the picker's "Looking…".
  // Deleting the copy fixes both.

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

  // ADR-514 D1: duplicate is a DERIVATION, resolved kernel-side. The FE names
  // only the source — the free `-copy` name and the derived_from edge are the
  // primitive's to write (the pre-514 Studio version probed for a free name in
  // the browser, capped at 5, and recorded no origin at all).
  const onDuplicate = useCallback(
    async (t: FileOrganizeTarget) => {
      if (await carveGuard(t.path)) return;
      try {
        const r = await runAction(() => api.documents.duplicate(t.path), {
          pending: 'Duplicating…',
          success: 'Duplicated',
          error: (e) =>
            e instanceof APIError
              ? (e.data as { detail?: string })?.detail || 'Duplicate failed'
              : 'Duplicate failed',
        });
        // Land on the copy — the macOS gesture (the duplicate becomes current).
        if (r?.new_path) onAfterMutate?.(r.new_path, t.path);
      } catch {
        /* error toast already surfaced; stop */
      }
    },
    [carveGuard, runAction, onAfterMutate],
  );

  /**
   * The report a FAN-OUT owes the operator (2026-08-21).
   *
   * A folder act can only PARTIALLY land: `operator_can_organize` refuses
   * system/, raw inbound/, and _*.yaml/_*.json leaves, so a folder holding any
   * of those keeps them. Silently moving 38 of 40 and saying "Moved" is the
   * incorrect-success shape — the operator believes their folder is empty and
   * two files of theirs are still sitting in it.
   *
   * The backend already composes this sentence (it holds the enumeration), so
   * this returns the server's own message rather than re-deriving it here. Two
   * places building the same sentence from the same numbers is how they drift.
   */
  const fanReport = (r: { message?: string } | undefined, fallback: string) =>
    r?.message || fallback;

  const commitRename = useCallback(
    async (t: FileOrganizeTarget, nextLeaf: string) => {
      const parent = t.path.slice(0, t.path.lastIndexOf('/'));
      const newPath = `${parent}/${nextLeaf}`;
      if (newPath === t.path) return;
      try {
        // A folder rename is the fan-out with a new leaf — the SAME act as a
        // folder move, addressed differently, so it takes the same route. One
        // implementation means the two verbs cannot drift apart.
        const r = t.isFolder
          ? await runAction(() => api.documents.moveFolder(t.path, newPath), {
              pending: 'Renaming folder…',
              success: (res) => fanReport(res, 'Renamed'),
              error: (e) =>
                e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Rename failed' : 'Rename failed',
            })
          : await runAction(() => api.documents.move(t.path, newPath), {
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
      setMoveTarget(t);
    },
    [carveGuard],
  );

  const commitMove = useCallback(
    async (fromPath: string, destFolder: string, isFolder = false) => {
      const leaf = fromPath.replace(/\/+$/, '').slice(fromPath.replace(/\/+$/, '').lastIndexOf('/') + 1);
      const newPath = destFolder.endsWith('/') ? `${destFolder}${leaf}` : `${destFolder}/${leaf}`;
      if (newPath === fromPath) return;
      try {
        const r = isFolder
          ? await runAction(() => api.documents.moveFolder(fromPath, newPath), {
              pending: 'Moving folder…',
              success: (res) => fanReport(res, 'Moved'),
              error: (e) =>
                e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Move failed' : 'Move failed',
            })
          : await runAction(() => api.documents.move(fromPath, newPath), {
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

  /**
   * Move a SET into one folder (ADR-553 D2).
   *
   * A loop over `commitMove`, deliberately — the substrate has no bulk move,
   * and inventing one would need partial-failure semantics the single mover
   * already has. What this adds is HONEST REPORTING: moves are
   * non-transactional (ADR-337 D3 writes then tombstones, per file), so a set
   * can half-land, and the member must be told which half.
   *
   * Sequential, not parallel: N concurrent writes against one folder race on
   * `destination_exists`, and the loser's 409 would read as a random failure.
   */
  const commitMoveMany = useCallback(
    async (fromPaths: string[], destFolder: string) => {
      const moved: string[] = [];
      const failed: string[] = [];
      for (const from of fromPaths) {
        const leaf = from.slice(from.lastIndexOf('/') + 1);
        const newPath = destFolder.endsWith('/') ? `${destFolder}${leaf}` : `${destFolder}/${leaf}`;
        if (newPath === from) continue;
        try {
          await api.documents.move(from, newPath);
          moved.push(newPath);
        } catch {
          failed.push(leaf);
        }
      }
      if (moved.length) onAfterMutate?.(moved[moved.length - 1], fromPaths[0]);
      return { moved, failed };
    },
    [onAfterMutate],
  );

  /**
   * Move a FOLDER to Trash — the fan-out (2026-08-21).
   *
   * Two things it owes the operator that the file path does not:
   *
   *   THE SIZE, IN THE CONFIRM. The menu label already carried the count
   *   ("Move to Trash (40 items)"); the confirm restates it, because a
   *   consequence this large should be named at the moment of consent and not
   *   only at the moment of pointing.
   *
   *   THE CARVE, NAMED BEFORE CONSENT. If some children are managed by the
   *   system they will stay put, and the operator must know that BEFORE they
   *   agree — otherwise they accept "delete this folder" and get a folder that
   *   is still there with two files in it. The preflight already knows; asking
   *   afterwards would be a report, not a choice.
   */
  const onDeleteFolder = useCallback(
    async (t: FileOrganizeTarget) => {
      if (await carveGuard(t.path)) return;
      let pre: { count: number; locked: string[]; too_large: boolean } | null = null;
      try {
        pre = await api.documents.folderPreflight(t.path);
      } catch {
        /* the confirm still asks; the backend remains authoritative */
      }
      if (pre?.too_large) {
        await confirm({
          title: `“${t.name}” is too large to move at once`,
          body: 'This folder holds more items than a single action can move. Move some of its contents first.',
          confirmLabel: 'OK',
          cancelLabel: '',
        });
        return;
      }
      const n = pre?.count ?? 0;
      const lockedCount = pre?.locked.length ?? 0;
      const lockedLine = lockedCount
        ? ` ${lockedCount} item${lockedCount === 1 ? ' is' : 's are'} managed by the system and will stay where ${lockedCount === 1 ? 'it is' : 'they are'}.`
        : '';
      const ok = await confirm({
        title: `Move “${t.name}” to Trash?`,
        body:
          `${n} item${n === 1 ? '' : 's'} inside will move too. `
          + `They stay recoverable — you can restore the whole folder from Trash.${lockedLine}`,
        confirmLabel: 'Move to Trash',
        danger: true,
      });
      if (!ok) return;
      try {
        await runAction(() => api.documents.trashFolder(t.path), {
          pending: 'Moving to Trash…',
          success: (res) => fanReport(res, 'Moved to Trash'),
          error: (e) =>
            e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Delete failed' : 'Delete failed',
        });
        onAfterMutate?.(null, t.path);
      } catch {
        /* error toast already surfaced; stop */
      }
    },
    [carveGuard, confirm, runAction, onAfterMutate],
  );

  const onDelete = useCallback(
    async (t: FileOrganizeTarget) => {
      if (t.isFolder) return onDeleteFolder(t);
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
    [carveGuard, confirm, runAction, onAfterMutate, onDeleteFolder],
  );

  const modals = (
    <>
      <MoveToFolderModal
        target={moveTarget}
        roots={providedRoots}
        canOrganize={operatorCanOrganize}
        onClose={() => setMoveTarget(null)}
        onMove={async (destFolder) => {
          const t = moveTarget;
          setMoveTarget(null);
          // The target carries its own kind — a folder move takes the fan-out
          // route, a file move the single mover. One modal, two acts.
          if (t) await commitMove(t.path, destFolder, t.isFolder);
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

  return { verbs: { onRename, onMove, onDelete, onDuplicate, commitMove, commitMoveMany }, modals };
}
