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
  /** ADR-539 D1 — what the kind cites, served on the vocabulary row. */
  cites?: 'none' | 'source' | 'picture';
  /** ADR-539 D1 — the served interaction tier (ADR-525 D1's vocabulary). */
  tier?: 'text' | 'object';
}

export type BlockFamily = 'prose' | 'composed' | 'cited';

/**
 * ADR-580 D2 — a kind's FAMILY derives from fields the registry already
 * declares (the ADR-539 D1 discipline: a derivation cannot drift, a hand
 * column can). cited = it cites the workspace; composed = a standalone object
 * minted from thin air; prose = the caret's units.
 */
export function blockFamily(b: BlockRowItem): BlockFamily {
  if ((b.cites ?? 'none') !== 'none') return 'cited';
  return b.tier === 'object' ? 'composed' : 'prose';
}

export interface BlockRowGroup {
  key: 'new' | 'add';
  label: string;
  items: BlockRowItem[];
}

/**
 * ADR-579 D4 (taking ADR-506 §7's named-not-taken deferral): the ONE grouping
 * every door renders — the `/` palette on flow, the verb menus, and the
 * right-click tiers. Grouped by PROVENANCE (ADR-466 D4), derived from the
 * served row's `cites` (ADR-539 D2) — never a hand-kept kind list, so the
 * grouping cannot drift from the registry.
 *
 * ADR-580 D3 — the MEDIUM orders the families inside NEW: on `paged` the
 * deck's native units lead (composed → prose); on `flow` the caret's units
 * lead (prose → composed). Ordering and labeling only, NEVER subsetting —
 * ADR-506 D3's refusal stands: every kind stays reachable from every door on
 * every medium. The third provenance — with the colleague, "from inference" —
 * arrives with ADR-579 D7 and gets its slot here when it does. Labels name
 * the VERB, never the mechanism (ADR-579 D3).
 */
export function groupBlockRows(
  items: BlockRowItem[],
  medium?: 'paged' | 'flow' | null,
): BlockRowGroup[] {
  const prose = items.filter((b) => blockFamily(b) === 'prose');
  const composed = items.filter((b) => blockFamily(b) === 'composed');
  const cited = items.filter((b) => blockFamily(b) === 'cited');
  // A stable partition: served order survives WITHIN each family; the medium
  // decides which family leads. Both families are always present — this is
  // an order, not a filter.
  const newItems = medium === 'paged' ? [...composed, ...prose] : [...prose, ...composed];
  return [
    { key: 'new' as const, label: 'New', items: newItems },
    { key: 'add' as const, label: 'Add — from the workspace', items: cited },
  ].filter((g) => g.items.length > 0);
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
