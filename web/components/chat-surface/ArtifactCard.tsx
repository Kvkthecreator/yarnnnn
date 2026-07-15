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
 * ── THE CITATION TILE (ADR-443 amendment 2026-07-15, operator-corrected) ───
 *
 * Preview depth follows ownership. A surface-owned format (ADR-451
 * `resolveSurfaceApplication` — .html → Studio, arrivals excepted) does NOT
 * get an inline working render: chat CITES Studio's file. The card is the
 * Studio-recents tile (the operator's reference): a small scaled thumbnail
 * (`ArtifactThumb`) + name + meta, the whole tile ONE click target — "Open in
 * Studio". Succinct, minimal, the boundary legible.
 *
 * ── THE TILE IS THE DEFAULT, THE RENDER IS THE EXCEPTION (2026-07-16) ─────
 *
 * The amendment's rule ("depth follows ownership") assumed *unclaimed* was one
 * thing. It isn't: `.md` is chat's own prose-substrate, but `.svg`/`.png`/
 * `.pdf`/`.csv` are unclaimed too, and they took the `.md` branch — a chart
 * benched at full row width in a transcript (operator receipt, 2026-07-16).
 *
 * So the axis is restated one notch more precisely, in the amendment's own
 * asset/dividend vocabulary: **the full render is for chat's own working
 * material; everything else is CITED.** `.md` renders inline because reading it
 * IS the thinking-work (ADR-454's asset class). Every other format — owned or
 * not — is a thing chat MADE, and a made thing gets a tile: thumbnail, name,
 * attribution, one click target. Ownership hasn't stopped mattering; it now
 * decides the tile's DESTINATION ("Open in Studio" vs the chat-open modal),
 * not whether there's a tile.
 *
 * That collapses the fall-through: the tile is the default and the render is
 * the exception, so a new format lands as a tile rather than as a 360px
 * surprise. The dispatch stays HERE at the file-type altitude — mounts still
 * only declare card-vs-none (ADR-443 §3) — and the per-type thumb TECHNIQUE
 * (iframe / img / glyph) lives in `ArtifactThumb`, not in this mount.
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
import { ArtifactThumb } from '@/components/shared/ArtifactThumb';
import {
  describeViewerApplication,
  isConversationalSubstrate,
  resolveSurfaceApplication,
} from '@/lib/file-types';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

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

  // The depth rule (see header). Chat's own working material renders inline;
  // everything else is a made thing and is CITED as a tile. The card ASKS the
  // predicate — it never resolves the viewer kind itself; that stays FileBody's
  // (test_lane_artifacts::test_the_file_body_is_the_only_kind_switch). Both
  // reads key off the extension, known before the file loads, so the card's
  // shape never flickers on arrival.
  const isChatsOwnMaterial = isConversationalSubstrate(path, file?.content_type);
  // Ownership no longer decides IF there's a tile — it decides where the tile
  // GOES: an owned format opens in its app, an unowned one in the chat frame.
  const owningApp = resolveSurfaceApplication(path, file?.content_type);

  if (!isChatsOwnMaterial) {
    if (notFound) {
      return (
        <div className="max-w-[300px] rounded-xl border border-border bg-background/60 px-3 py-4 text-center text-xs text-muted-foreground">
          <FileQuestion className="mx-auto mb-2 h-5 w-5 opacity-40" />
          This file is no longer at {relPath}.
        </div>
      );
    }
    const openLabel = owningApp ? `Open in ${owningApp.label}` : 'Open';
    return (
      <>
        <button
          type="button"
          onClick={() =>
            owningApp
              ? navigateToSurface(owningApp.surface, { [owningApp.param]: path })
              : setOpenInModal(true)
          }
          title={`${openLabel} — ${relPath}`}
          className="group block w-full max-w-[300px] rounded-xl border border-border bg-background/60 p-2 text-left transition-colors hover:bg-muted/20"
        >
          <ArtifactThumb file={file} />
          <span className="mt-2 flex items-center gap-1.5">
            <FileIcon filename={filename} size="sm" />
            <span className="min-w-0 truncate text-sm font-medium">{filename}</span>
          </span>
          <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
            {verbLabel}
            {attribution ? ` · ${attribution}` : ''}
          </span>
          <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-primary">
            <ExternalLink className="h-3 w-3" />
            {openLabel}
          </span>
        </button>
        {/* ADR-436 §7 — the chat-open mount, for a tile with no owning app. */}
        {openInModal && <FileOpenModal path={path} onClose={() => setOpenInModal(false)} />}
      </>
    );
  }

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
        <button
          type="button"
          onClick={() => setOpenInModal(true)}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Maximize2 className="h-3 w-3" />
          Open
        </button>
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

      {/* ADR-436 §7 — the chat-open mount: the artifact in its own frame. */}
      {openInModal && <FileOpenModal path={path} onClose={() => setOpenInModal(false)} />}
    </div>
  );
}
