/**
 * studioShapes — the ONE Studio shape taxonomy (icon · label · accent).
 *
 * Every Studio artifact is an `.html` file, so the shared FileIcon (which keys
 * on extension) can't tell a deck from a document — it would render every
 * recent as the same violet BookOpen. The MEANINGFUL distinction is the
 * artifact's TEMPLATE (document · deck · article · page), and the template is
 * carried by the basename at creation (`operation/…/deck.html`, the ADR-452
 * meaning-placed name).
 *
 * This helper resolves a shape from a path/basename so the start state's recents
 * can show what KIND of thing each artifact is — by name (the shape label) and
 * visually (a per-shape icon + accent). Co-located with the Studio because the
 * shape taxonomy is the Studio's, not the filesystem's; adding a fifth shape is
 * one row here, matching the served STUDIO_LAYOUTS registry.
 */

import { FileText, Presentation, Newspaper, LayoutTemplate, File as FileGlyph } from 'lucide-react';

export interface StudioShapeMeta {
  /** The template slug (document · deck · article · page), or 'file' when unknown. */
  slug: string;
  /** Human label for the shape ("Deck"), shown under the recent's name. */
  label: string;
  icon: typeof FileText;
  /** Tailwind text-color class for the glyph — one accent per shape. */
  color: string;
}

const SHAPES: Record<string, StudioShapeMeta> = {
  document: { slug: 'document', label: 'Document', icon: FileText, color: 'text-sky-500' },
  deck: { slug: 'deck', label: 'Deck', icon: Presentation, color: 'text-amber-500' },
  article: { slug: 'article', label: 'Article', icon: Newspaper, color: 'text-violet-500' },
  page: { slug: 'page', label: 'Page', icon: LayoutTemplate, color: 'text-emerald-500' },
};

const UNKNOWN: StudioShapeMeta = {
  slug: 'file',
  label: 'File',
  icon: FileGlyph,
  color: 'text-muted-foreground',
};

/** Resolve a Studio shape from an artifact path or basename.
 *  Matches on the basename stem: `…/deck.html` → deck; a renamed artifact
 *  (`ir-deck-v3.html`) falls to UNKNOWN — its thumbnail still tells the story,
 *  and the label reads "File" honestly rather than guessing. */
export function studioShapeFromPath(path: string): StudioShapeMeta {
  const base = (path.split('/').pop() ?? path).toLowerCase();
  const stem = base.replace(/\.[a-z0-9]+$/i, '');
  return SHAPES[stem] ?? UNKNOWN;
}
