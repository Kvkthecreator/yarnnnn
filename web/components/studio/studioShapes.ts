/**
 * studioShapes — the Studio's shape PRESENTATION (icon · accent).
 *
 * ADR-459: the shape's IDENTITY (slug + label) is no longer guessed here — it
 * is LIFTED server-side from the artifact's own `data-template` root attr and
 * served on each row (`kind` + `kind_label`). The layout IS the file (ADR-443
 * R2), so a renamed artifact (`ir-deck-v3.html`) now reads its correct kind;
 * the old stem-matcher said "File".
 *
 * What remains here is the part the server has no business holding: the GLYPH
 * and the ACCENT. Keyed by the served slug — an OPAQUE STRING (ADR-459 D3,
 * mirroring `AppId = string` per ADR-436), so a bundle-shipped layout that this
 * table has no icon for still renders with its correct served label and a
 * neutral glyph. The kernel names the slot; the program fills the value
 * (ADR-222). Adding an icon for a new shape is one row here — and NOT adding
 * one is a soft, honest fallback rather than a wrong label.
 */

import {
  FileText, Presentation, Newspaper, LayoutTemplate, Image as ImageGlyph,
  File as FileGlyph,
} from 'lucide-react';

export interface StudioShapeStyle {
  icon: typeof FileText;
  /** Tailwind text-color class for the glyph — one accent per shape. */
  color: string;
}

/** Icon + accent per known shape slug. Presentation only — never a label. */
const SHAPE_STYLES: Record<string, StudioShapeStyle> = {
  document: { icon: FileText, color: 'text-sky-500' },
  deck: { icon: Presentation, color: 'text-amber-500' },
  article: { icon: Newspaper, color: 'text-violet-500' },
  page: { icon: LayoutTemplate, color: 'text-emerald-500' },
  // ADR-482 D7: the IMAGES stage (ADR-472) had no row, so it fell to the
  // neutral glyph everywhere this table is read — correct by the fallback's
  // design, but the shape is known and deserves its own mark.
  image: { icon: ImageGlyph, color: 'text-rose-500' },
};

const UNSTYLED: StudioShapeStyle = {
  icon: FileGlyph,
  color: 'text-muted-foreground',
};

/** The glyph + accent for a served kind slug. An unknown slug (a bundle's own
 *  layout) degrades to a neutral file glyph — its LABEL still reads correctly,
 *  because the label comes from the server, not from this table. */
export function studioShapeStyle(kind: string | null | undefined): StudioShapeStyle {
  if (!kind) return UNSTYLED;
  return SHAPE_STYLES[kind] ?? UNSTYLED;
}
