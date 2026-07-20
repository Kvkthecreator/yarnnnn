'use client';

/**
 * StudioSlashPalette — the '/' block palette (ADR-456 W2, the Notion gesture).
 *
 * Opens when the edit runtime reports a '/' typed ANYWHERE — mid-sentence, mid-
 * word, or on an empty line. The '/' lands as ordinary text and the caret never
 * leaves the document: what the member types after it IS this palette's filter,
 * mirrored in over `filter` (there is no input here to focus — stealing focus
 * would end the edit the gesture depends on).
 *
 * Because every typed '/' opens it, DISMISSAL is load-bearing: Esc, a click in
 * either document (the runtime reports the in-frame one — this component's own
 * document listener is blind to the iframe), a caret that leaves the run, and a
 * filter that matches nothing all close it. Typing a URL must never strand a
 * menu over the text.
 *
 * The palette lists EVERY kind (ADR-466 D4 — insert is provenance-shaped, in
 * one place): the plain kinds drop a fragment, chart seeds the lane, and the
 * picker-backed kinds (figure/table/gallery) open the StudioCitablePicker at
 * the same anchor — the located insertion point rides through, so the cited
 * block lands where the member was pointing. `Media ▾` retired with this.
 *
 * The palette EXECUTES nothing itself — the surface routes the pick.
 */

import { useEffect, useMemo, useRef } from 'react';
import {
  AlignLeft,
  BarChart3,
  CheckSquare,
  ChevronRight,
  Code,
  Heading1,
  Image as ImageIcon,
  List,
  type LucideIcon,
  Minus,
  MessageSquareQuote,
  Quote,
  Table as TableIcon,
  Type,
} from 'lucide-react';
import type { StudioVocabulary } from './StudioToolbar';

/** kind → glyph. The kernel vocabulary ships no icon field (and shouldn't — an
 *  icon is presentation), so the mapping lives here. An unmapped kind falls back
 *  to the generic block glyph rather than rendering a hole. */
const SLASH_ICONS: Record<string, LucideIcon> = {
  prose: Type,
  text: Type,
  heading: Heading1,
  callout: MessageSquareQuote,
  quote: Quote,
  checklist: CheckSquare,
  list: List,
  bullets: List,
  divider: Minus,
  toggle: ChevronRight,
  code: Code,
  chart: BarChart3,
  figure: ImageIcon,
  gallery: ImageIcon,
  table: TableIcon,
};
const FALLBACK_ICON: LucideIcon = AlignLeft;

interface StudioSlashPaletteProps {
  vocabulary: StudioVocabulary | null;
  /** The run typed after the '/', mirrored from the in-document caret. */
  filter: string;
  /** Anchor within the canvas wrapper (already clamped by the surface). */
  left: number;
  top: number;
  /** Index of the highlighted row — owned by the surface, since the document
   *  (not this component) has the keyboard while the palette is open. */
  highlight: number;
  onHighlight: (i: number) => void;
  onPick: (kind: string, label: string, fragment: string) => void;
  onClose: () => void;
  /** Reports the filtered rows up so the surface's Enter can pick the
   *  highlighted one without duplicating the filter logic. */
  onItemsChange: (items: Array<{ kind: string; label: string; fragment: string }>) => void;
}

export function StudioSlashPalette({
  vocabulary,
  filter,
  left,
  top,
  highlight,
  onHighlight,
  onPick,
  onClose,
  onItemsChange,
}: StudioSlashPaletteProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  const items = useMemo(() => {
    const all = vocabulary?.blocks ?? [];
    const q = filter.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (b) => b.label.toLowerCase().includes(q) || b.kind.toLowerCase().includes(q),
    );
  }, [vocabulary, filter]);

  useEffect(() => {
    onItemsChange(items);
  }, [items, onItemsChange]);

  // A filter that matches nothing is prose, not a gesture — dismiss so a typed
  // URL ("http://…") never strands a menu over the text.
  useEffect(() => {
    if (filter.length > 0 && items.length === 0) onClose();
  }, [filter, items.length, onClose]);

  // Click-away in the PARENT document (the chrome around the canvas). A click on
  // the content itself is reported by the runtime — this listener cannot hear it
  // across the iframe boundary.
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [onClose]);

  if (items.length === 0) return null;

  return (
    <div
      ref={rootRef}
      style={{ left, top }}
      className="absolute z-30 w-72 rounded-md border border-border bg-background p-1 shadow-lg"
    >
      <div className="max-h-72 overflow-y-auto">
        {items.map((b, i) => {
          const Icon = SLASH_ICONS[b.kind] ?? FALLBACK_ICON;
          return (
            <button
              key={b.kind}
              type="button"
              // mousedown would fire the runtime's click-away first and close us.
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onPick(b.kind, b.label, b.fragment)}
              onMouseEnter={() => onHighlight(i)}
              className={`flex w-full items-start gap-2.5 rounded px-2 py-1.5 text-left ${
                i === highlight ? 'bg-muted/60' : 'hover:bg-muted/30'
              }`}
            >
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border bg-muted/30">
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-medium">{b.label}</span>
                <span className="block text-[10px] leading-snug text-muted-foreground">
                  {b.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
