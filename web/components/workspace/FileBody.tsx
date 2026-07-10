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
 * ADR-236: this RENDERS. It never edits — chat is the canonical mutation
 * surface. `compact` is a display hint (trims heights), not a fork.
 */

import { Download, ExternalLink } from 'lucide-react';
import { resolveApp } from '@/lib/file-types/apps';
import { useSignedBlobUrl } from '@/components/workspace/viewers/blob';
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
// FileActions — "open with your computer" (the degenerate Open With, ADR-329)
// ---------------------------------------------------------------------------

export function FileActions({ contentUrl }: { contentUrl: string }) {
  const { url, loading } = useSignedBlobUrl(contentUrl);
  const disabled = loading || !url;
  return (
    <div className="flex items-center gap-2 shrink-0">
      <a
        href={disabled ? undefined : url}
        target="_blank"
        rel="noreferrer"
        aria-disabled={disabled}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground',
          disabled && 'pointer-events-none opacity-50'
        )}
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Open
      </a>
      <a
        href={disabled ? undefined : url}
        download
        aria-disabled={disabled}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground',
          disabled && 'pointer-events-none opacity-50'
        )}
      >
        <Download className="w-3.5 h-3.5" />
        Download
      </a>
    </div>
  );
}
