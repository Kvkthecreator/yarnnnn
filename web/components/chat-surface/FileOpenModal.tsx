'use client';

/**
 * FileOpenModal — the chat-open mount (ADR-436 §7).
 *
 * Opening an artifact from a chat lane gives it its OWN frame — a modal-like
 * overlay around the shared `FileBody` renderer — rather than teleporting the
 * member to the Files surface. This supersedes the ArtifactCard "redirect to
 * Files" stance (ADR-436 D5): "redirect to Files" was a workaround for not
 * having a clean mount model; once the renderer is frame-agnostic (ADR-436),
 * a chat-open mount is cheap and honest — the artifact opens where the member
 * is looking, carrying its attribution.
 *
 * ── PRESERVES "we do not build a window manager" ──────────────────────────
 * This uses the EXISTING modal primitive (backdrop + Escape + centered card —
 * the PropertiesModal pattern), NOT a new window in the surface window manager.
 * The window-manager invariant (window = surface, ADR-297 D15) is untouched.
 *
 * ── RENDERS, NEVER EDITS (ADR-236) ────────────────────────────────────────
 * Full-size FileBody (not `compact`) + Open-in-Files handoff + Download. To
 * change the file, the member asks the lane.
 *
 * The exact frame (modal here vs. a dedicated surface) is a layout-ADR decision
 * (ADR-436 §8 / D6). The modal is the honest first mount; the app registry is
 * mount-agnostic, so a later layout ADR can reframe this without touching apps.
 */

import { useEffect } from 'react';
import { ExternalLink, FileQuestion, Loader2, X } from 'lucide-react';
import { FileBody, FileActions } from '@/components/workspace/FileBody';
import { FileMeta } from '@/components/workspace/FileMeta';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

interface FileOpenModalProps {
  /** Absolute workspace path, or null when closed. */
  path: string | null;
  onClose: () => void;
}

export function FileOpenModal({ path, onClose }: FileOpenModalProps) {
  useEffect(() => {
    if (!path) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [path, onClose]);

  // The hook is called unconditionally with '' when closed (no fetch fires for
  // a falsy path — getFile short-circuits upstream); the `if (!path)` guard
  // below governs render. Keeps hook order stable across open/close.
  const { file, loading, notFound, error } = useFileLoad(path || '');

  if (!path) return null;
  const filename = path.split('/').pop() || path;
  const relPath = path.replace(/^\/workspace\//, '');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 mx-4 flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-lg">
        {/* ── header: identity + verbs ── */}
        <div className="flex items-start gap-2 border-b border-border bg-muted/20 px-4 py-3">
          <div className="min-w-0 flex-1">
            {file ? (
              <FileMeta
                file={file}
                iconSize="md"
                trailing={<span className="truncate" title={relPath}>{relPath}</span>}
              />
            ) : (
              <span className="truncate text-sm font-medium">{filename}</span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {file?.content_url && <FileActions contentUrl={file.content_url} />}
            <SurfaceLink
              to="files"
              params={{ path }}
              onClick={onClose}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              <ExternalLink className="h-3 w-3" />
              Open in Files
            </SurfaceLink>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* ── body: the one shared viewer, full-size ── */}
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Opening {filename}…
            </div>
          )}
          {notFound && (
            <div className="py-16 text-center text-sm text-muted-foreground">
              <FileQuestion className="mx-auto mb-2 h-6 w-6 opacity-40" />
              This file is no longer at {relPath}.
            </div>
          )}
          {error && (
            <div className="py-16 text-center text-sm text-muted-foreground">
              Couldn’t open this file. It’s still in the workspace — try Files.
            </div>
          )}
          {!loading && !notFound && !error && file && <FileBody file={file} />}
        </div>
      </div>
    </div>
  );
}
