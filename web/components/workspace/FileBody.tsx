'use client';

/**
 * FileBody — THE one file renderer dispatcher (ADR-436).
 *
 * Since ADR-436, FileBody is a THIN DISPATCHER: it resolves the file to its
 * viewer app (`resolveApp`) and mounts that app's frame-agnostic renderer. The
 * per-type rendering lives in `components/workspace/viewers` (seven named apps
 * behind the `APPS` table), not in a monolithic switch here.
 *
 * An app is a RENDERER; FileBody + its mounts own the FRAME. FileBody itself is
 * frame-neutral — it draws the app into a `space-y-4` block with an optional
 * card height. The document chrome (header, verbs) belongs to the MOUNT
 * (`ContentViewer`, `ArtifactCard`, `FileOpenModal`), never here.
 *
 * Mounts today (ADR-436 §5):
 *   - ContentViewer  — the Files/Recents document chrome
 *   - ArtifactCard   — the inline chat card (render-on-write)
 *   - FileOpenModal  — chat-open, the explicit-open frame (ADR-436 §7)
 *
 * ADR-236: this RENDERS. It never edits — chat is the conversational
 * mutation surface, and an app SURFACE (ADR-571: prose → Text, .html →
 * Docs/Studio) is the cursor path. `compact` is a display hint (trims
 * heights), not a fork.
 */

import { resolveApp } from '@/lib/file-types/apps';
import { cn } from '@/lib/utils';
import type { WorkspaceFile } from '@/types';

// Re-export the signed-URL hook from its shared home so existing importers
// (`ContentViewer`, `RevisionHistoryPanel`, …) keep one import path. The single
// definition lives in `viewers/blob` (ADR-427 D4: the one `content_url`
// consumer, where the minted-capability retirement will land).
export { useSignedBlobUrl } from '@/components/workspace/viewers/blob';

// The tier-1 IDENTITY inference case is owned by the Markdown app now (ADR-436
// §4). `inferenceTarget` is retained as a thin shim for any external caller.
export function inferenceTarget(path: string): 'identity' | null {
  return path === '/workspace/persona/IDENTITY.md' ? 'identity' : null;
}

interface FileBodyProps {
  file: WorkspaceFile;
  /** Trim intrinsic heights for an inline card mount. Display hint, not a fork. */
  compact?: boolean;
  className?: string;
}

export function FileBody({ file, compact = false, className }: FileBodyProps) {
  const { renderer: Renderer } = resolveApp(file.path, file.content_type);
  return (
    <div className={cn('space-y-4', className)}>
      <Renderer file={file} compact={compact} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// FileActions is DELETED (2026-08-20).
// ---------------------------------------------------------------------------
//
// It rendered two buttons — Open and Download — bolted into the preview
// header of three different mounts. Both are gone, for two different reasons:
//
//   DOWNLOAD became a RIGHT-CLICK VERB (`FileVerbs.downloadFor`), following the
//   cloud-provider convention every operator already has in their hands
//   (Dropbox · Drive · OneDrive all put Download in the context menu). It is
//   now reachable from every surface the verb bundle is threaded to, instead of
//   only from the two headers that happened to mount this component. The
//   `download={filename}` fix from 1069fe3 travelled with it and is gated —
//   the href is a signed `workspace-cas` URL and the CAS is keyed by CONTENT
//   ADDRESS, so a bare `download` saves the blob as a 64-char SHA.
//
//   OPEN was deleted outright rather than rehomed. It opened the blob in a new
//   browser tab — answering "what does this file look like?" with a second
//   copy of the answer the pane DIRECTLY BESIDE IT was already rendering. A
//   verb whose result is already on screen is not a verb. (`Open With ▸` in the
//   context menu is a different act: it routes the file to a yarnnn APP —
//   Studio, Docs, Text — and it stays.)
//
// The chat surface's FileOpenModal, which mounted this and has no context menu
// of its own, keeps its "Open in Files" link — one door, to where the verbs
// live, instead of a second smaller copy of them.
