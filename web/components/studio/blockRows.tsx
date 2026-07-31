'use client';

/**
 * blockRows — the ONE rendered list of insertable block kinds.
 *
 * Two mounts read it, and that is the whole point (ADR-462 D1's rule, applied
 * to insert): the `/` palette on `flow`, and the native Insert menu on `paged`.
 * One list means a kind added to the served vocabulary appears in both doors
 * without a second edit, and neither door can silently drift into offering a
 * different set — the drift that made per-type subsetting a trap (ADR-506 D3).
 *
 * This module renders rows and nothing else. Choosing a target, landing the
 * fragment, and the picker-backed branches all stay with the surface, so there
 * is still exactly ONE write path underneath both doors.
 */

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

/** kind → glyph. The kernel vocabulary ships no icon field (and shouldn't — an
 *  icon is presentation), so the mapping lives here. An unmapped kind falls back
 *  to the generic block glyph rather than rendering a hole. */
export const BLOCK_ICONS: Record<string, LucideIcon> = {
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

export const FALLBACK_BLOCK_ICON: LucideIcon = AlignLeft;

export interface BlockRowItem {
  kind: string;
  label: string;
  fragment: string;
  description?: string;
}

interface BlockRowProps {
  item: BlockRowItem;
  /** Highlighted by keyboard (the palette) or by pointer (either mount). */
  active: boolean;
  /** Scroll the active row into view — the palette's list scrolls at ~6 rows
   *  while the vocabulary ships 13+, and the highlight can be driven by keys
   *  the list itself never sees. `nearest` only scrolls when actually needed,
   *  so pointer hovering never yanks the list. */
  scrollIntoViewWhenActive?: boolean;
  onPick: () => void;
  onHover?: () => void;
}

export function BlockRow({
  item,
  active,
  scrollIntoViewWhenActive,
  onPick,
  onHover,
}: BlockRowProps) {
  const Icon = BLOCK_ICONS[item.kind] ?? FALLBACK_BLOCK_ICON;
  return (
    <button
      type="button"
      ref={
        active && scrollIntoViewWhenActive
          ? (el) => el?.scrollIntoView({ block: 'nearest' })
          : undefined
      }
      // mousedown would fire the runtime's click-away first and close the menu
      // before the click lands — true for both mounts, since both live in the
      // parent document while the press may be reported from the frame.
      onMouseDown={(e) => e.preventDefault()}
      onClick={onPick}
      onMouseEnter={onHover}
      className={`flex w-full items-start gap-2.5 rounded px-2 py-1.5 text-left ${
        active ? 'bg-muted/60' : 'hover:bg-muted/30'
      }`}
    >
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border bg-muted/30">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-xs font-medium">{item.label}</span>
        {item.description && (
          <span className="block text-[10px] leading-snug text-muted-foreground">
            {item.description}
          </span>
        )}
      </span>
    </button>
  );
}
