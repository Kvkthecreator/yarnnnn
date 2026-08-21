'use client';

/**
 * MoveToFolderModal — the folder-picker for the operator's "Move to…" verb
 * (ADR-400 Q2). Replaces the old `window.prompt('Move to folder…')` — the
 * operator NEVER types a raw workspace path ("move to shouldn't be a URL path
 * input"). Instead they pick a destination FOLDER from a tree, the way
 * Finder/Explorer's "Move to…" works.
 *
 * A thin config of the shared `WorkspacePickerModal` (2026-07-20 collapse): the
 * hand-rolled portal + recursive `FolderRow` this file used to carry is DELETED
 * and now lives once in `WorkspacePicker` (folder mode). This file supplies only
 * what's Move-specific — the "moving X" copy, the organizable + not-current-
 * parent predicate, and the destination footer hint.
 *
 * Only folders are selectable (you move a file INTO a folder). The current
 * parent is rejected (moving there is a no-op), and any folder the operator
 * can't organize into (system/ + machine-config parents) renders disabled —
 * pre-empting the backend 403 with a greyed row.
 *
 * This is also the keyboard/accessibility path for the drag-and-drop the tree
 * offers directly — drag is the fast gesture (it does NOT go through this
 * modal), this modal is the deliberate one.
 */

import { useMemo } from 'react';
import type { WorkspaceTreeNode } from '@/types';
import { WorkspacePickerModal } from './WorkspacePicker';

interface MoveToFolderModalProps {
  /** The file OR FOLDER being moved (null = closed). `isFolder` (2026-08-21)
   *  makes the picker refuse a destination INSIDE the thing being moved — see
   *  `folderSelectable` below. */
  target: { path: string; name: string; isFolder?: boolean } | null;
  /** The workspace root nodes (same tree the explorer renders). Omit it and the
   *  picker lazy-fetches its own — the surface that holds no tree (Studio) pays
   *  nothing until the first Move-open, and gets an honest "Looking…" while it
   *  loads instead of a premature "no folders". */
  roots?: WorkspaceTreeNode[];
  /** True iff the operator may organize into this destination path. */
  canOrganize: (path: string) => boolean;
  onClose: () => void;
  /** Called with the chosen destination FOLDER path. */
  onMove: (destFolder: string) => void | Promise<void>;
}

export function MoveToFolderModal({ target, roots, canOrganize, onClose, onMove }: MoveToFolderModalProps) {
  // The file's current parent — moving there is a no-op, so reject it.
  const currentParent = useMemo(
    () => (target ? target.path.slice(0, target.path.lastIndexOf('/')) : null),
    [target],
  );

  if (!target) return null;

  /**
   * SELF-CONTAINMENT (2026-08-21). Moving a folder into itself, or into one of
   * its own descendants, is not a move — the fan-out would write each file to a
   * path still under the prefix it is walking. The backend refuses it (400), but
   * a refusal the operator only meets AFTER choosing is a dead end wearing a
   * live affordance: they picked a destination the picker offered.
   *
   * So the picker refuses it by CONSTRUCTION: the moved folder and everything
   * under it are unselectable, with the reason on the row. Files are unaffected
   * — a file has no descendants, so the prefix test can never match one.
   */
  const selfPrefix = target.isFolder ? `${target.path.replace(/\/+$/, '')}/` : null;
  const isInsideSelf = (path: string) =>
    !!selfPrefix && (path === target.path.replace(/\/+$/, '') || path.startsWith(selfPrefix));

  // A folder is selectable iff the operator can organize into it, it's not the
  // target's current parent, and it is not the target itself or inside it.
  // Probe organize-reach with a synthetic child path.
  const folderSelectable = (node: WorkspaceTreeNode) =>
    canOrganize(`${node.path}/x`) && node.path !== currentParent && !isInsideSelf(node.path);

  return (
    <WorkspacePickerModal
      open={!!target}
      mode="folder"
      title="Move to…"
      subtitle={`Moving “${target.name}”`}
      confirmLabel="Move here"
      emptyMessage="No folders to move into."
      roots={roots}
      selectable={folderSelectable}
      folderDisabledTitle={(node) =>
        node.path === currentParent
          ? `${target.isFolder ? 'The folder' : 'The file'} is already here`
          : isInsideSelf(node.path)
            ? 'A folder can’t be moved inside itself'
            : !canOrganize(`${node.path}/x`)
              ? 'This folder is managed by the system'
              : undefined
      }
      canConfirm={(sel) =>
        sel !== currentParent && canOrganize(`${sel}/x`) && !isInsideSelf(sel)
      }
      footerHint={(sel) =>
        sel ? (
          <>Into <span className="font-mono">{sel.replace(/^\/workspace\//, '')}</span></>
        ) : (
          'Pick a destination folder'
        )
      }
      onClose={onClose}
      onConfirm={(destFolder) => onMove(destFolder)}
    />
  );
}
