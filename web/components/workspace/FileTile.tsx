'use client';

/**
 * FileTile — the ONE Finder icon-view tile (Finder-parity, 2026-07-09).
 *
 * Before this, three grids drew file tiles their own way: RecentsView's IconGrid
 * (roomy h-24 real thumbnails), ContentViewer's folder listing (a tiny h-8 glyph,
 * no preview zone), and the detail preview frame (a different radius + ground).
 * The same file looked different depending on which code path rendered it — the
 * biggest "not-native" tell. This is the single tile: one geometry, one preview
 * zone, one radius, one ground. Both the Recents grid and the folder-listing icon
 * view render it (Singular Implementation).
 *
 * A tile has three parts, top-down like Finder: a dominant square-ish PREVIEW
 * (real thumbnail when the caller has the material, else the branded format
 * glyph — folders get the sky Folder glyph), a truncated NAME, and one line of
 * SUBTEXT (relative time, or attribution). Selection + hover live on the tile
 * shell; system files (`_*`) dim.
 *
 * The preview radius + ground are the tokens standardized across the surface:
 * TILE_PREVIEW_RADIUS / TILE_PREVIEW_GROUND. FileBody imports the same tokens so
 * the card and the detail view frame a file identically (the SVG-in-card vs
 * SVG-in-detail mismatch the audit flagged).
 */

import { useEffect, useState } from 'react';
import { Folder } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { FileIcon } from './FileIcon';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

// ── Shared preview tokens — the single radius + ground for every file preview,
// tile OR detail. Import these anywhere a file is framed; don't hand-write the
// classes (that's how the four-radii drift happened). rounded-lg reads right for
// Finder's gently-cornered icons; bg-muted/40 is the one neutral ground.
export const TILE_PREVIEW_RADIUS = 'rounded-lg';
export const TILE_PREVIEW_GROUND = 'bg-muted/40';

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']);

function fileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
}
function fileExt(path: string): string {
  return (fileName(path).split('.').pop() || '').toLowerCase();
}

/**
 * The material a tile needs to draw a REAL thumbnail (vs the format glyph).
 * Recents has it from the revision feed; the folder listing doesn't (tree nodes
 * carry no blob), so those tiles fall to the glyph — same geometry, no preview.
 */
export interface TileThumb {
  /** Image blob → resolved to a signed URL and drawn as a cover thumbnail. */
  content_url?: string | null;
  /** Format hint (unused for now; kept for future viewer routing). */
  content_type?: string | null;
  /** Short text snippet for md/txt → a mini-page card. */
  preview?: string | null;
  /** Inline SVG lives in the text column (no blob) — draw it as the thumbnail. */
  svgText?: string | null;
}

/** Resolve an image blob's content_url → signed URL, then render a cover
 * thumbnail. Absolute/data/blob URLs render directly. Falls back to the format
 * glyph while loading or on error (the tile never looks broken). */
function ThumbImage({ contentUrl, filename }: { contentUrl: string; filename: string }) {
  const [url, setUrl] = useState<string>('');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (/^(https?:|data:|blob:)/i.test(contentUrl)) { setUrl(contentUrl); return; }
    let cancelled = false;
    api.documents.blobUrl(contentUrl)
      .then((r) => { if (!cancelled) setUrl(r.url); })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [contentUrl]);
  if (failed || !url) return <FileIcon filename={filename} size="2xl" />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={filename} className="h-full w-full rounded-lg object-cover" onError={() => setFailed(true)} />;
}

/** The per-format preview: real image thumbnail · inline SVG · md/txt snippet
 * card · branded format glyph otherwise. */
function Preview({ path, thumb }: { path: string; thumb?: TileThumb }) {
  const ext = fileExt(path);
  const name = fileName(path);

  if (IMAGE_EXTS.has(ext) && thumb?.content_url) {
    return <ThumbImage contentUrl={thumb.content_url} filename={name} />;
  }
  // Inline SVG (no blob — the markup lives in the text column). Render it
  // sandboxed-by-scale so the card matches the detail view's star.
  if (ext === 'svg' && thumb?.svgText) {
    return (
      <span
        className="flex h-full w-full items-center justify-center overflow-hidden p-2 [&_svg]:h-full [&_svg]:w-auto [&_svg]:max-w-full"
        dangerouslySetInnerHTML={{ __html: thumb.svgText }}
      />
    );
  }
  if (thumb?.preview && (ext === 'md' || ext === 'txt')) {
    // A content-snippet card — the first real lines of the doc, like a mini page.
    return (
      <span className="flex h-full w-full flex-col gap-0.5 overflow-hidden rounded-lg bg-background/70 px-2 py-1.5 text-left">
        <span className="line-clamp-4 text-[9px] leading-[1.35] text-muted-foreground">
          {thumb.preview}
        </span>
      </span>
    );
  }
  return <FileIcon filename={name} size="2xl" />;
}

export interface FileTileProps {
  path: string;
  /** 'folder' draws the sky Folder glyph; 'file' draws a preview/glyph. */
  kind: 'file' | 'folder';
  /** One line of subtext under the name — relative time, or attribution node. */
  subtext?: React.ReactNode;
  /** Thumbnail material (Recents supplies it; folder listing omits it). */
  thumb?: TileThumb;
  selected?: boolean;
  /** De-emphasize machine-config `_*` files (kept, not hidden — ADR-320). */
  dim?: boolean;
  /**
   * Click dispatch, mirroring the two Recents mounts:
   *   onClick   → the Files/folder mount owns selection (component state).
   *   linkTo    → the Home mount has no selection; the tile deep-links to the
   *               Files surface (SurfaceLink). Provide one or the other.
   */
  onClick?: () => void;
  linkTo?: string;
  onContextMenu?: (e: React.MouseEvent) => void;
  title?: string;
  /** Trailing actions overlay (the touch kebab — ADR-400 touch parity). Rendered
   *  top-right so it doesn't disturb the centered card; absent on desktop. */
  actions?: React.ReactNode;
}

export function FileTile({
  path, kind, subtext, thumb, selected = false, dim = false,
  onClick, linkTo, onContextMenu, title, actions,
}: FileTileProps) {
  const name = fileName(path);
  const shellClass = cn(
    'group relative flex flex-col items-center gap-1.5 rounded-lg border p-2.5 text-center transition-colors',
    selected
      ? 'border-primary/50 bg-primary/10 ring-1 ring-primary/40'
      : 'border-transparent hover:border-border/70 hover:bg-muted/40',
    dim && !selected && 'opacity-70',
  );
  // The touch kebab overlay (absent on desktop — `actions` is only supplied on
  // a coarse pointer). Top-right so the centered card is undisturbed.
  const actionsOverlay = actions ? (
    <span className="absolute right-1 top-1 z-10">{actions}</span>
  ) : null;

  const inner = (
    <>
      {/* Preview zone — the dominant mass, Finder-style. One radius, one ground. */}
      <span
        className={cn(
          'flex h-24 w-full items-center justify-center overflow-hidden transition-colors',
          TILE_PREVIEW_RADIUS,
          selected ? 'bg-primary/10' : cn(TILE_PREVIEW_GROUND, 'group-hover:bg-muted/60'),
        )}
      >
        {kind === 'folder'
          ? <Folder className="h-10 w-10 text-sky-600" />
          : <Preview path={path} thumb={thumb} />}
      </span>
      <span className={cn(
        'mt-0.5 w-full truncate text-xs font-medium text-foreground',
        dim && !selected && 'text-muted-foreground',
      )}>
        {name}
      </span>
      {subtext !== undefined && (
        <span className="w-full truncate text-[10px] text-muted-foreground/70">
          {subtext}
        </span>
      )}
    </>
  );

  // Home mount → a deep-link into Files; Files/folder mount → a button.
  if (linkTo && !onClick) {
    return (
      <SurfaceLink to="files" params={{ path: linkTo }} className={shellClass} title={title ?? path} onContextMenu={onContextMenu}>
        {actionsOverlay}
        {inner}
      </SurfaceLink>
    );
  }
  return (
    <button type="button" onClick={onClick} onContextMenu={onContextMenu} title={title ?? path} className={shellClass}>
      {actionsOverlay}
      {inner}
    </button>
  );
}
