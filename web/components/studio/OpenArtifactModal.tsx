'use client';

/**
 * OpenArtifactModal — the Studio's "Open…" file browser (ADR-459 follow-on).
 *
 * A thin config of the shared `WorkspacePickerModal` (2026-07-20 collapse): the
 * hand-rolled portal + recursive `PickerRow` this file used to carry is DELETED
 * and now lives once in `WorkspacePicker`. This file supplies only what's
 * act-specific — the copy, the openable predicate, and the ADR-459 leaf naming.
 *
 * What's openable is NOT a Studio-local rule — it's ADR-451's
 * `resolveSurfaceApplication`, the same registry that routes the Files surface's
 * open verb (Finder → PowerPoint). The Studio never hardcodes ".html": it asks
 * the OS which app owns the type, and shows what it owns. Rows are named by
 * ADR-459's rule — what the artifact IS (its titleized meaning folder), never
 * its `.html` storage encoding. This modal is a COMPOSITION (one operator act:
 * open my work), so it reads like a Mac.
 */

import type { WorkspaceTreeNode } from '@/types';
import { resolveSurfaceApplication } from '@/lib/file-types';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { studioShapeStyle } from './studioShapes';
import { artifactNameFromPath, kindGuessFromPath } from './artifactNaming';

interface OpenArtifactModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the chosen artifact's workspace path. */
  onOpen: (path: string) => void;
}

/** True iff this file is one the Studio owns — asked of the OS's type→app
 *  registry (ADR-451), never of a local extension test. */
function isOpenable(node: WorkspaceTreeNode): boolean {
  return node.type === 'file' && resolveSurfaceApplication(node.path)?.surface === 'studio';
}

export function OpenArtifactModal({ open, onClose, onOpen }: OpenArtifactModalProps) {
  return (
    <WorkspacePickerModal
      open={open}
      mode="file"
      title="Open…"
      subtitle="Pick something you’ve made"
      confirmLabel="Open"
      emptyMessage="Nothing to open yet — hit New to make something."
      selectable={isOpenable}
      leaf={{
        label: (node) => artifactNameFromPath(node.path),
        icon: (node) => {
          const style = studioShapeStyle(kindGuessFromPath(node.path));
          return { Glyph: style.icon, className: style.color };
        },
      }}
      onClose={onClose}
      onConfirm={(path) => onOpen(path)}
    />
  );
}
