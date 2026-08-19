'use client';

/**
 * StudioBlockInsertMenu — the MOUSE insert route on `paged` (deck / web).
 *
 * Why this exists, given ADR-506 D1 made Insert a DOOR onto the '/' gesture:
 * because on `paged` there is no longer a '/' to be a door onto. ADR-505 D4's
 * justification for a universal slash cited "Figma Slides, Pitch and Gamma in
 * the deck class" — and two of those three are false: Figma Slides binds '/' to
 * CURSOR CHAT, and Pitch's quick menu is Cmd+K and says explicitly that it is
 * not slash. Of seven slide editors surveyed only Gamma ships a block-insert
 * slash, and Gamma is a card/document hybrid rather than a spatial canvas.
 *
 * The durable finding underneath, which is what this component is built on:
 * the slash appears where there is a TEXT CARET IN A LINEAR FLOW, and a visible
 * mouse affordance is UNIVERSAL — no surveyed tool ships slash as the sole or
 * primary insert route (Notion documents the '+' first, Gamma its insert bar as
 * "Option 1", Gutenberg its '+' inserter). Studio had it exactly inverted on
 * paged: ADR-505 D4 deleted the gutter and left '/' the ONLY block-insert route,
 * so ten of thirteen kinds were mouse-unreachable on a deck.
 *
 * TWO MOUNTS, ONE MENU — deliberately, and not a second mechanism:
 *   · the TOOLBAR button is the DISCOVERY route (visible without knowing);
 *   · the RIGHT-CLICK row is the LOCATED route (fast, at the thing you mean).
 * PowerPoint's ribbon is discoverable but not located; a context menu is located
 * but invisible. Shipping only one repeats a failure this canon already made —
 * the button alone is a route nobody finds where they are looking, the menu
 * alone is the slash's invisibility in another costume.
 *
 * It renders rows and reports a pick. Choosing the target and landing the
 * fragment stay with the surface, so both mounts and the flow palette still sit
 * on ONE write path (ADR-443 D2 — never an eighth operation).
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { BlockRow, groupBlockRows, type BlockRowItem } from './blockRows';
import { ArrangementThumb } from './ArrangementThumb';
import type { StudioArrangement, StudioVocabulary } from './StudioToolbar';

interface StudioBlockInsertMenuProps {
  vocabulary: StudioVocabulary | null;
  /** ADR-579 D6 — a toolbar verb door filters to its group; null = full list. */
  verb?: 'add' | 'new' | null;
  /** Viewport point to anchor at (the toolbar button's rect, or the
   *  right-click point already mapped to the page by the canvas). */
  x: number;
  y: number;
  /** Names where the block will land, so the member is never guessing. */
  targetLabel: string;
  onPick: (kind: string, label: string, fragment: string) => void;
  onClose: () => void;
  /** ADR-579 D6.a — the NEW door carries BOTH grains: when the surface passes
   *  this, the menu renders the New-‹noun› arrangement gallery under the block
   *  rows (page grain inside the verb's one door, never a sibling button). */
  pageSection?: {
    noun: string;
    arrangements: StudioArrangement[];
    onPick: (fragment: string, label: string) => void;
  };
}

export function StudioBlockInsertMenu({
  vocabulary,
  verb = null,
  x,
  y,
  targetLabel,
  onPick,
  onClose,
  pageSection,
}: StudioBlockInsertMenuProps) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [clamped, setClamped] = useState<{ left: number; top: number } | null>(null);
  const items: BlockRowItem[] = vocabulary?.blocks ?? [];

  // Measured clamp, not a guessed constant — the same correction the block menu
  // needed. The list is long and the anchor may be near the bottom of the
  // window, so the menu must be placed against its REAL height.
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8;
    setClamped({
      left: Math.max(MARGIN, Math.min(x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(y, window.innerHeight - height - MARGIN)),
    });
  }, [x, y, items.length]);

  // Dismissal, including the iframe blind spot: the canvas is a sandboxed,
  // opaque-origin frame, so a click or an Escape inside it never reaches these
  // parent listeners. The runtime bridges both out (yarnnn-canvas-press and
  // yarnnn-canvas-escape) — without the bridge this menu could only be closed
  // by clicking the thin chrome around the canvas.
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const onFrame = (e: MessageEvent) => {
      const t = (e.data as { type?: string } | null)?.type;
      // Scroll joins press and Escape: this menu is anchored to a point in the
      // page, and the canvas scrolling underneath it moves what that point
      // meant. The parent's own scroll listener is deaf to the iframe's
      // scroller (opaque origin), so the runtime's report is the only route.
      if (t === 'yarnnn-canvas-press' || t === 'yarnnn-canvas-escape' || t === 'yarnnn-scroll-pos') {
        onClose();
      }
    };
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', close);
    window.addEventListener('message', onFrame);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', close);
      window.removeEventListener('message', onFrame);
    };
  }, [onClose]);

  // An empty vocabulary means the registry has not answered yet. Render nothing
  // rather than an empty bordered box that must be dismissed (the ADR-482 D9
  // rule: a menu with no acts is not a menu).
  if (items.length === 0) return null;

  const left = clamped?.left ?? x;
  const top = clamped?.top ?? y;

  return (
    <div
      ref={boxRef}
      style={{ left, top }}
      className="fixed z-50 max-h-[calc(100vh-16px)] w-72 overflow-y-auto rounded-md border border-border bg-popover p-1 shadow-md"
      onMouseDown={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* The target is NAMED, and so is the VERB (ADR-579 D6.a — this menu is
          a verb's own door, so the header speaks the verb). On a spatial
          surface "insert" without a stated destination is the ambiguity that
          makes members undo and retry — the same reason ADR-466 D5 forewarns
          an arrangement that would move content to a new page. */}
      <p className="px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        {verb === 'add' ? 'Add' : verb === 'new' ? 'New' : 'Insert'} — into {targetLabel}
      </p>
      {/* ADR-579 D4 — the same provenance grouping the flow palette renders
          (one grouping module — the ADR-506 D3 one-list rule extended to the
          grouping, so the doors cannot drift apart). A verb door shows ONLY
          its own group: a door labeled New that offered Add rows would be the
          label lying (the D6.a defect this recut removes). */}
      {groupBlockRows(items).filter((g) => !verb || g.key === verb).map((g) => (
        <div key={g.key}>
          {/* Under a verb door the group header would repeat the door's own
              name — render it only on the (legacy) verb-less mount. */}
          {!verb && (
            <p className="px-2 pb-0.5 pt-1.5 text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
              {g.label}
            </p>
          )}
          {g.items.map((b) => (
            <BlockRow
              key={b.kind}
              item={b}
              active={false}
              onPick={() => onPick(b.kind, b.label, b.fragment)}
            />
          ))}
        </div>
      ))}
      {/* ADR-579 D6.a — the page grain, inside the New door. One verb, one
          door, two grains (grain lives inside the door, ADR-579 D2). */}
      {pageSection && pageSection.arrangements.length > 0 && (
        <div>
          <p className="px-2 pb-0.5 pt-1.5 text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
            New {pageSection.noun}
          </p>
          <div className="grid grid-cols-2 gap-1.5 p-1">
            {pageSection.arrangements.map((a) => (
              <button
                key={a.slug}
                type="button"
                onClick={() => pageSection.onPick(a.fragment, a.label)}
                title={a.description}
                className="flex flex-col gap-1 rounded-md border border-transparent p-1.5 text-left hover:border-border hover:bg-muted/20"
              >
                <ArrangementThumb areas={a.areas} fragment={a.fragment} />
                <span className="truncate text-[11px]">{a.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
