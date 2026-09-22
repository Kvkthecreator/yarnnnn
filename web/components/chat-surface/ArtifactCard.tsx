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
 *
 * ── SPEECH STAYS PRIMARY (2026-08-18, operator-observed) ──────────────────
 *
 * The inline `.md` render had grown to outweigh the message it accompanies:
 * a full-row 360px document next to an 85%-width muted bubble, arriving
 * mid-stream — the member's eyes landed on the file and never read the words.
 * Three calibrations, none of which revisit the depth rule above:
 *
 *   - `streaming` (mount-passed): while the turn is still streaming, the card
 *     holds its HEADER only — the write is visible the moment it lands (the
 *     lane contract rendered, 2026-07-09), but the render unfolds on turn end.
 *     A side effect worth keeping: the file body prefetches during the
 *     stream, so the unfold is usually instant.
 *   - collapsed height 360 → 240px: enough to read the document's opening and
 *     know what it is; not enough to drown the reply.
 *   - "Show more" is BOUNDED (70vh, internal scroll): an unbounded expand
 *     made the transcript itself a mile of document, with "Show less"
 *     stranded past it. Full-length reading lives in the Open modal.
 *
 * ── THE SHAPE ARRIVES BEFORE THE FILE (2026-09-17) ────────────────────────
 *
 * `streaming` above holds the header while the BODY loads; `pending` is the
 * step before it — the write has not landed at all. A long compose showed the
 * member tool rows, then silence, then a finished card: the output's shape was
 * the LAST thing to arrive, when it is the thing that tells them whether to
 * stop the turn.
 *
 * The two claims are kept apart on purpose, and the asymmetry is the point:
 *   - pending  — path from the call's ARGUMENTS. "This is being written."
 *   - settled  — path from the call's RESULT. "This exists; open it."
 * Only the second may be persisted, opened, or counted. A pending card that
 * never settles is DROPPED at turn end (LanePanel's `onDone`), because a card
 * for a file that does not exist is the one failure this component must never
 * produce — it is the same rule that keeps `DeleteFile` off `LANE_ARTIFACT_VERBS`.
 */

import { useState } from 'react';
import { useTranslations } from 'next-intl';
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

/** Collapsed height of the preview body before the fade + "Show more".
 *  Sized to coexist with speech, not to replace the Open modal (see header). */
const COLLAPSED_MAX_PX = 240;

interface ArtifactCardProps {
  /** Absolute workspace path, as returned by the primitive (`/workspace/…`). */
  path: string;
  /** The verb that produced it — WriteFile (created) vs EditFile (revised). */
  verb?: string;
  /** Who the lane wrote as, e.g. "you via Gemini Pro". */
  attribution?: string;
  /** The turn that produced this card is still streaming: hold the tile
   *  posture (header only) and unfold the render when it ends (see header). */
  streaming?: boolean;
  /** The write has STARTED but not landed (2026-09-17). The file does not
   *  exist yet, so the card announces its SHAPE and nothing more: no load, no
   *  "Open" (there is nothing to open), no "no longer at this path" (it was
   *  never there). It settles into an ordinary card when the write lands. */
  pending?: boolean;
}

export function ArtifactCard({
  path,
  verb,
  attribution,
  streaming = false,
  pending = false,
}: ArtifactCardProps) {
  const t = useTranslations('chat.artifact');
  // ADR-436 §6: the shared file-load hook (was a hand-written getFile machine).
  // `cachedFirst`: this mount re-mounts on every post-turn transcript resync
  // (row identities swap local→DB); a card already read must not respin.
  const { file, loading, notFound, error } = useFileLoad(path, { cachedFirst: true });
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

  // ── PENDING: the shape, and only the shape ──────────────────────────────
  // The file does not exist yet, so every branch below would be a lie: the
  // loader would report an error, `notFound` would say it is "no longer at"
  // a path it was never at, and "Open" would 404. This returns BEFORE all of
  // them. It sits after the hooks, never inside a condition, so the hook
  // order is identical on the pending and settled renders — the card settles
  // in place rather than remounting and losing its prefetch.
  if (pending) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-background/40 px-3 py-2">
        <div className="flex items-start gap-2">
          <FileIcon filename={filename} size="sm" />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-foreground/80">{filename}</div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                {verb === 'EditFile' ? 'Revising' : 'Writing'}
              </span>
              <span className="truncate" title={relPath}>{relPath}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
            {file && <span>{describeViewerApplication(file.path, file.content_type, file.view)}</span>}
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
      {/* Mid-stream the body stays folded (header-only tile) — the load below
          still runs, so the unfold on turn end is usually instant. */}
      {!streaming && loading && (
        <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Opening {filename}…
        </div>
      )}

      {!streaming && notFound && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          <FileQuestion className="mx-auto mb-2 h-5 w-5 opacity-40" />
          This file is no longer at {relPath}.
        </div>
      )}

      {!streaming && error && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          Couldn’t open this file. It’s still in the workspace — try Files.
        </div>
      )}

      {!streaming && !loading && !notFound && !error && file && (
        <>
          {/* Expanded is BOUNDED: the card scrolls internally at 70vh so the
              transcript never becomes the document. "Show less" stays below,
              reachable without scrolling the document back down. */}
          <div
            className={cn(
              'relative px-3 py-3',
              !expanded && 'overflow-hidden',
              expanded && 'max-h-[70vh] overflow-y-auto',
            )}
            style={!expanded ? { maxHeight: COLLAPSED_MAX_PX } : undefined}
          >
            <FileBody file={file} compact />
            {!expanded && (
              // The fade is decorative and must not eat clicks on the body.
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-background to-transparent" />
            )}
          </div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex w-full items-center justify-center gap-1 border-t border-border/60 py-1.5 text-[11px] text-muted-foreground hover:bg-muted/30 hover:text-foreground"
          >
            {expanded ? (
              <><ChevronUp className="h-3 w-3" /> {t('showLess')}</>
            ) : (
              <><ChevronDown className="h-3 w-3" /> {t('showMore')}</>
            )}
          </button>
        </>
      )}

      {/* ADR-436 §7 — the chat-open mount: the artifact in its own frame. */}
      {openInModal && <FileOpenModal path={path} onClose={() => setOpenInModal(false)} />}
    </div>
  );
}
