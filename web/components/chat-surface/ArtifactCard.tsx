'use client';

/**
 * ArtifactCard — the second mount of the one shared viewer (2026-07-09).
 *
 * When a lane's WriteFile/EditFile lands, the member sees WHAT it made — not
 * a verb name in a footer. The card is a bounded frame around `FileBody`, the
 * same component the Files surface mounts. Same dispatch, same type table, one
 * renderer.
 *
 * ── WHAT THIS IS AND IS NOT ───────────────────────────────────────────────
 *
 * This is the Artifacts model, not Canvas. The card RENDERS and OPENS; it never
 * edits (ADR-236: chat is the canonical mutation surface — `SubstrateEditor`
 * was deleted). To change the file, the member asks the lane.
 *
 * It reinforces the ADR-411 lane contract rather than violating it: the
 * transcript stays private to the lane; the WORK lands in a shared, attributed
 * file. The card is a pointer to that file, with its attribution on it. It is
 * the contract rendered.
 *
 * ── LAYOUT ────────────────────────────────────────────────────────────────
 *
 * Bounded height + fade, never a scroll trap inside a scroll container: the
 * body is clipped at `--artifact-max` with a gradient mask, and "Open in Files"
 * hands off to the real window. Side-by-side is achieved by the EXISTING window
 * manager (ADR-297 D15 — open Files beside Chat and drag), never by nesting a
 * second pane inside the chat window. We do not build a window manager.
 *
 * The card sits OUTSIDE the assistant bubble at full row width — a bubble's
 * `max-w-[85%]` is too narrow for a rendered document, and an artifact is not
 * speech.
 */

import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, FileQuestion, Loader2, PencilLine, Plus } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { FileBody } from '@/components/workspace/FileBody';
import { FileIcon } from '@/components/workspace/FileIcon';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { describeViewerApplication } from '@/lib/file-types';
import { cn } from '@/lib/utils';
import type { WorkspaceFile } from '@/types';

/** Collapsed height of the preview body before the fade + "Show more". */
const COLLAPSED_MAX_PX = 360;

interface ArtifactCardProps {
  /** Absolute workspace path, as returned by the primitive (`/workspace/…`). */
  path: string;
  /** The verb that produced it — WriteFile (created) vs EditFile (revised). */
  verb?: string;
  /** Who the lane wrote as, e.g. "you via Gemini Pro". */
  attribution?: string;
}

export function ArtifactCard({ path, verb, attribution }: ArtifactCardProps) {
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'missing' | 'error'>('loading');
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    api.workspace
      .getFile(path)
      .then((data) => {
        if (cancelled) return;
        setFile(data);
        setState('ready');
      })
      .catch((err) => {
        if (cancelled) return;
        setState(err instanceof APIError && err.status === 404 ? 'missing' : 'error');
      });
    return () => { cancelled = true; };
  }, [path]);

  const filename = path.split('/').pop() || path;
  // The path the operator reads — the `/workspace/` root is plumbing (ADR-244 D7).
  const relPath = path.replace(/^\/workspace\//, '');
  const VerbIcon = verb === 'EditFile' ? PencilLine : Plus;
  const verbLabel = verb === 'EditFile' ? 'Revised' : 'Wrote';

  return (
    <div className="rounded-xl border border-border bg-background/60 overflow-hidden">
      {/* ── header: what it is, where it lives, who made it ── */}
      <div className="flex items-start gap-2 border-b border-border/60 bg-muted/20 px-3 py-2">
        <FileIcon filename={filename} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="truncate text-sm font-medium">{filename}</span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <VerbIcon className="h-3 w-3" />
              {verbLabel}
            </span>
            <span className="truncate" title={relPath}>{relPath}</span>
            {file && <span>{describeViewerApplication(file.path, file.content_type)}</span>}
            {attribution && <span>· {attribution}</span>}
          </div>
        </div>
        <SurfaceLink
          to="files"
          params={{ path }}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <ExternalLink className="h-3 w-3" />
          Open in Files
        </SurfaceLink>
      </div>

      {/* ── body: the one shared viewer, bounded ── */}
      {state === 'loading' && (
        <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Opening {filename}…
        </div>
      )}

      {state === 'missing' && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          <FileQuestion className="mx-auto mb-2 h-5 w-5 opacity-40" />
          This file is no longer at {relPath}.
        </div>
      )}

      {state === 'error' && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          Couldn’t open this file. It’s still in the workspace — try Files.
        </div>
      )}

      {state === 'ready' && file && (
        <>
          <div
            className={cn('relative px-3 py-3', !expanded && 'overflow-hidden')}
            style={!expanded ? { maxHeight: COLLAPSED_MAX_PX } : undefined}
          >
            <FileBody file={file} compact />
            {!expanded && (
              // The fade is decorative and must not eat clicks on the body.
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-background to-transparent" />
            )}
          </div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex w-full items-center justify-center gap-1 border-t border-border/60 py-1.5 text-[11px] text-muted-foreground hover:bg-muted/30 hover:text-foreground"
          >
            {expanded ? (
              <><ChevronUp className="h-3 w-3" /> Show less</>
            ) : (
              <><ChevronDown className="h-3 w-3" /> Show more</>
            )}
          </button>
        </>
      )}
    </div>
  );
}
