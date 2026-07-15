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
 * ── OPENING (ADR-436 §7 — supersedes the redirect-only stance) ────────────
 *
 * The card is bounded (height + fade). "Open" gives the artifact its own frame
 * via `FileOpenModal` (the chat-open mount) — NOT a teleport to Files. This
 * supersedes the prior "Open in Files hands off to the real window" stance:
 * once the renderer is frame-agnostic, opening in place is cheap and honest.
 * "Open in Files" remains as a secondary handoff.
 *
 * PRESERVED: "we do not build a window manager." The modal uses the existing
 * overlay primitive (PropertiesModal pattern), not a new surface window. The
 * window=surface invariant (ADR-297 D15) is untouched.
 *
 * The card sits OUTSIDE the assistant bubble at full row width — a bubble's
 * `max-w-[85%]` is too narrow for a rendered document, and an artifact is not
 * speech.
 *
 * ── QUICK LOOK (ADR-443 amendment 2026-07-15 — the seam-contract spine) ────
 *
 * Preview depth follows ownership. A surface-owned format (ADR-451
 * `resolveSurfaceApplication` — .html → Studio, arrivals excepted) renders
 * Quick-Look-grade: a tighter bounded glance, no in-place expansion, and
 * "Open in Studio" as the celebrated primary action (header + footer strip).
 * Unclaimed formats (.md — the asset class chat itself works) keep the full
 * bounded render with Show more, byte-identical to pre-amendment. The
 * dispatch lives HERE at the file-type altitude — mounts still only declare
 * card-vs-none (ADR-443 §3).
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Maximize2,
  FileQuestion,
  Loader2,
  PencilLine,
  Plus,
} from 'lucide-react';
import { FileBody } from '@/components/workspace/FileBody';
import { FileIcon } from '@/components/workspace/FileIcon';
import { FileOpenModal } from '@/components/chat-surface/FileOpenModal';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { describeViewerApplication, resolveSurfaceApplication } from '@/lib/file-types';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

/** Collapsed height of the preview body before the fade + "Show more". */
const COLLAPSED_MAX_PX = 360;
/** Quick-Look height for a surface-owned file (ADR-443 amendment 2026-07-15):
 *  a glance at another app's file, never a full working render. */
const QUICKLOOK_MAX_PX = 240;

interface ArtifactCardProps {
  /** Absolute workspace path, as returned by the primitive (`/workspace/…`). */
  path: string;
  /** The verb that produced it — WriteFile (created) vs EditFile (revised). */
  verb?: string;
  /** Who the lane wrote as, e.g. "you via Gemini Pro". */
  attribution?: string;
}

export function ArtifactCard({ path, verb, attribution }: ArtifactCardProps) {
  // ADR-436 §6: the shared file-load hook (was a hand-written getFile machine).
  const { file, loading, notFound, error } = useFileLoad(path);
  const [expanded, setExpanded] = useState(false);
  // ADR-436 §7: the chat-open mount — the artifact opens in its own frame.
  const [openInModal, setOpenInModal] = useState(false);
  const { navigateToSurface } = useSurfacePreferences();

  const filename = path.split('/').pop() || path;
  // The path the operator reads — the `/workspace/` root is plumbing (ADR-244 D7).
  const relPath = path.replace(/^\/workspace\//, '');
  const VerbIcon = verb === 'EditFile' ? PencilLine : Plus;
  const verbLabel = verb === 'EditFile' ? 'Revised' : 'Wrote';

  // ADR-443 amendment (2026-07-15, the seam-contract spine): preview depth
  // follows ownership. A surface-owned format (ADR-451 registry — .html →
  // Studio, arrivals excepted) renders Quick-Look-grade: bounded glance, no
  // expansion, the owning app as the celebrated primary action. Chat glances
  // at another app's file; it doesn't bench it. Unclaimed formats (.md — the
  // asset class chat itself works) keep the full render, byte-identical.
  const owningApp = resolveSurfaceApplication(path, file?.content_type);
  const openInOwningApp = () => {
    if (owningApp) navigateToSurface(owningApp.surface, { [owningApp.param]: path });
  };

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
        {owningApp ? (
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setOpenInModal(true)}
              className="inline-flex items-center rounded-md border border-border p-1 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
              aria-label="Preview"
              title="Preview"
            >
              <Maximize2 className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={openInOwningApp}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:bg-primary/90"
            >
              <ExternalLink className="h-3 w-3" />
              Open in {owningApp.label}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setOpenInModal(true)}
            className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          >
            <Maximize2 className="h-3 w-3" />
            Open
          </button>
        )}
      </div>

      {/* ── body: the one shared viewer, bounded ── */}
      {loading && (
        <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Opening {filename}…
        </div>
      )}

      {notFound && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          <FileQuestion className="mx-auto mb-2 h-5 w-5 opacity-40" />
          This file is no longer at {relPath}.
        </div>
      )}

      {error && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          Couldn’t open this file. It’s still in the workspace — try Files.
        </div>
      )}

      {!loading && !notFound && !error && file && (
        <>
          <div
            className={cn(
              'relative px-3 py-3',
              (owningApp || !expanded) && 'overflow-hidden',
            )}
            style={
              owningApp
                ? { maxHeight: QUICKLOOK_MAX_PX }
                : !expanded
                  ? { maxHeight: COLLAPSED_MAX_PX }
                  : undefined
            }
          >
            <FileBody file={file} compact />
            {(owningApp || !expanded) && (
              // The fade is decorative and must not eat clicks on the body.
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-background to-transparent" />
            )}
          </div>
          {owningApp ? (
            // Quick Look never expands in place — the footer strip IS the
            // handoff to the owning app (the celebrated affordance).
            <button
              onClick={openInOwningApp}
              className="flex w-full items-center justify-center gap-1 border-t border-border/60 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted/30 hover:text-foreground"
            >
              <ExternalLink className="h-3 w-3" /> Open in {owningApp.label}
            </button>
          ) : (
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
          )}
        </>
      )}

      {/* ADR-436 §7 — the chat-open mount: the artifact in its own frame. */}
      {openInModal && <FileOpenModal path={path} onClose={() => setOpenInModal(false)} />}
    </div>
  );
}
