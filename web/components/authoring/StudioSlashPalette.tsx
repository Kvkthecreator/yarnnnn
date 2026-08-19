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
import type { StudioVocabulary } from './StudioToolbar';
// ONE rendered list, two mounts (this palette on flow; the native Insert menu
// on paged). The icon map moved with it — see blockRows.tsx.
import { BlockRow, groupBlockRows } from './blockRows';

interface StudioSlashPaletteProps {
  vocabulary: StudioVocabulary | null;
  /** ADR-579 D6 — a toolbar verb door filters to its group; null = full list. */
  verb?: 'add' | 'new' | null;
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
  verb = null,
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

  // ADR-579 D4 — the one provenance grouping (New · Add), shared with the
  // paged mount. Filtering searches across both groups; the FLAT list reported
  // up is the grouped order, so the keyboard index and the rendered rows can
  // never disagree.
  const groups = useMemo(() => {
    const all = vocabulary?.blocks ?? [];
    const q = filter.trim().toLowerCase();
    const matched = q
      ? all.filter(
          (b) => b.label.toLowerCase().includes(q) || b.kind.toLowerCase().includes(q),
        )
      : all;
    // The slash exists on FLOW only (ADR-509), so the medium is a constant
    // here: prose leads (ADR-581 D3).
    return groupBlockRows(matched, 'flow').filter((g) => !verb || g.key === verb);
  }, [vocabulary, filter, verb]);
  const items = useMemo(() => groups.flatMap((g) => g.items), [groups]);

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
        {(() => {
          // Running flat index across groups — the highlight is an index into
          // the flat list this component reports up via onItemsChange.
          let flat = -1;
          return groups.map((g) => (
            <div key={g.key}>
              <p className="px-2 pb-0.5 pt-1.5 text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
                {g.label}
              </p>
              {g.items.map((b) => {
                flat += 1;
                const i = flat;
                return (
                  <BlockRow
                    key={b.kind}
                    item={b}
                    active={i === highlight}
                    scrollIntoViewWhenActive
                    onPick={() => onPick(b.kind, b.label, b.fragment)}
                    onHover={() => onHighlight(i)}
                  />
                );
              })}
            </div>
          ));
        })()}
      </div>
    </div>
  );
}
