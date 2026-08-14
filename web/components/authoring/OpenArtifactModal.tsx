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

import { useEffect, useState } from 'react';

import { api } from '@/lib/api/client';
import type { WorkspaceTreeNode } from '@/types';
import { FileText } from 'lucide-react';
import { isArtifactCandidate, resolveSurfaceApplication } from '@/lib/file-types';
import { documentName } from '@/components/text/TextSurface';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { studioShapeStyle } from './studioShapes';
import { artifactNameFromPath, kindGuessFromPath } from './artifactNaming';

/** A prose document names itself by its LEAF (ADR-571), not by its folder. */
const isProsePath = (p: string) => /\.(md|markdown|txt)$/i.test(p);

/** Apps whose artifacts appear in the served `/studio/artifacts` index — the
 *  HTML-authoring apps. A prose app (ADR-571) has no row there and scopes by
 *  the type registry alone. */
const SERVED_INDEX_APPS = new Set(['docs', 'studio', 'images']);

interface OpenArtifactModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the chosen artifact's workspace path. */
  onOpen: (path: string) => void;
  /** ADR-473 D4: the asking app's surface slug — the picker browses only the
   *  artifacts that app OWNS (Preview's Open dialog does not offer `.sketch`).
   *  Studio and IMAGES both author `.html`, so extension cannot separate them;
   *  ownership comes from each artifact's declared type. */
  appSlug: string;
}

/** True iff this file is one the ASKING APP owns — put to the OS's type→app
 *  registry (ADR-451, ADR-473 D2), never to a local extension test.
 *
 *  ADR-473: the app is a parameter now, because Studio and IMAGES both author
 *  `.html` and each must browse only its own artifacts (Preview's Open dialog
 *  does not offer `.sketch`). A candidate whose kind hasn't been resolved falls
 *  to the default app — the pre-ADR-473 behavior. */
export function OpenArtifactModal({ open, onClose, onOpen, appSlug }: OpenArtifactModalProps) {
  // The set of paths this app owns, from the SERVED artifact list (which
  // already carries each artifact's lifted `kind` — no extra content reads,
  // and ownership stays the kernel's answer, not a client-side guess).
  const [owned, setOwned] = useState<Set<string> | null>(null);
  useEffect(() => {
    if (!open) return;
    // ADR-571: the served artifact index is the HTML-artifact index (types
    // lifted from `data-template`), so an app whose medium is PROSE has no
    // row in it. Such an app scopes by the type registry alone — which is
    // the stronger answer anyway (it is the same one `openPath` uses).
    if (!SERVED_INDEX_APPS.has(appSlug)) {
      setOwned(null);
      return;
    }
    let live = true;
    api.studio
      .artifacts(appSlug)
      .then((res) => {
        if (live) setOwned(new Set(res.artifacts.map((a) => a.path)));
      })
      .catch(() => {
        /* Fall back to "every artifact candidate": a failed scoping call must
           not make the member's own work unopenable. */
        if (live) setOwned(null);
      });
    return () => {
      live = false;
    };
  }, [open, appSlug]);

  /** True iff this file is one the ASKING APP owns — put to the OS's type→app
   *  registry (ADR-451, ADR-473 D2), never to a local extension test. */
  const isOpenable = (node: WorkspaceTreeNode): boolean => {
    if (node.type !== 'file' || !isArtifactCandidate(node.path)) return false;
    // The registry's answer first: the app that OWNS this file's type must be
    // the app asking. Without this an html-authoring app would offer prose
    // (and Text would offer decks) the moment `isArtifactCandidate` widened.
    if (resolveSurfaceApplication(node.path)?.surface !== appSlug) return false;
    return owned ? owned.has(node.path) : true;
  };

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
        // ADR-571: the NAME rule is the app's, not one hardcoded rule.
        // Docs titleizes the meaning FOLDER because its leaf is a type
        // marker (`document.html`); a prose document's leaf IS its name,
        // so the folder rule labelled every row "Documents" / "Uploads"
        // (found by driving the picker, 2026-08-15).
        label: (node) =>
          isProsePath(node.path)
            ? documentName(node.path)
            : artifactNameFromPath(node.path),
        icon: (node) => {
          if (isProsePath(node.path)) {
            return { Glyph: FileText, className: 'text-sky-600 dark:text-sky-400' };
          }
          const style = studioShapeStyle(kindGuessFromPath(node.path));
          return { Glyph: style.icon, className: style.color };
        },
      }}
      onClose={onClose}
      onConfirm={(path) => onOpen(path)}
    />
  );
}
