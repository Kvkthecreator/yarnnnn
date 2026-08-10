'use client';

/**
 * SelectionBreadcrumb — the ancestor chain at the selection (AUTHORING.md
 * Phase 3 §3): the same chain the Esc-walk climbs (block → container → … →
 * page), rendered as a clickable crumb over the canvas so the walk is
 * visible and pointable. Paged media only — flow's chain is caret → block →
 * clear (no page unit, no containers by derivation, ADR-481 D1), too
 * shallow to earn chrome.
 *
 * Labels are operator words (structureLabels — the one vocabulary seam);
 * the crumb never says "div". Clicking an ancestor SELECTS it — the same
 * parent selection path the navigator's structure tree uses (ADR-511 D3) —
 * so the crumb adds no new op, only a new reach into existing ones
 * (AUTHORING.md rule 7). The innermost segment is the current selection:
 * named, not clickable.
 *
 * ADR-519 D4.1 — over a ⇧-click SET the innermost segment is the COUNT and the
 * chain climbs from the members' SHARED parent. A set has no single innermost
 * rung — that is what makes it a set — so naming the primary's own ancestry
 * would be the same staleness the pane withdrew: five objects boxed on canvas
 * while the crumb reads "› heading". The shared parent is real and is what D4
 * asked the chrome to name; everything below the divergence point is not the
 * set's ancestry and is dropped.
 */

import { useMemo } from 'react';
import { labelForElement, STRUCTURAL_PAGE_SEL } from './structureLabels';
import type { StudioSelection } from './StudioToolbar';

/** The minimal element surface the climb needs — DOM in the app, stubs in
 *  the gate. */
export interface ClimbableElement {
  parentElement: ClimbableElement | null;
  tagName: string;
  getAttribute(name: string): string | null;
  hasAttribute(name: string): boolean;
}

/** Walk from the selected element UP to its page (exclusive), collecting the
 *  identity-carrying containers between them, outermost first. The selection
 *  floor is the attribution floor (ADR-511 D3): only elements with
 *  `data-block-id` are chain segments; unaddressed wrappers are transparent,
 *  exactly as the navigator's structure tree treats them. Blocks are leaves,
 *  so nothing above the start carries `data-block` — but the guard stays, in
 *  case a legacy artifact nests one. */
export function climbChain(el: ClimbableElement, pageEl: ClimbableElement): ClimbableElement[] {
  const containers: ClimbableElement[] = [];
  let cur = el.parentElement;
  while (cur && cur !== pageEl) {
    if (cur.getAttribute('data-block-id') && !cur.hasAttribute('data-block')) {
      containers.unshift(cur);
    }
    cur = cur.parentElement;
  }
  return containers;
}

interface CrumbSegment {
  /** null → the page segment (selected by index, not id). */
  blockId: string | null;
  label: string;
  kind: string | null;
  current: boolean;
}

function pageNoun(layout: string, index: number): string {
  return layout === 'deck' ? `Slide ${index + 1}` : `Section ${index + 1}`;
}

/** ADR-519 D4.1 — the deepest container that encloses EVERY member of a set.
 *  The set's honest ancestry: a set has no single innermost rung (that is what
 *  makes it a set), but it does have a shared parent, and D4 named it as the
 *  thing the chrome should show. Returns null when the members share nothing
 *  below the page — then the page IS the shared parent and the chain says so. */
export function sharedChain(
  chains: ClimbableElement[][],
): ClimbableElement[] {
  if (!chains.length) return [];
  const [first, ...rest] = chains;
  const shared: ClimbableElement[] = [];
  for (let i = 0; i < first.length; i++) {
    if (rest.every((c) => c[i] === first[i])) shared.push(first[i]);
    else break; // the chains diverge here — everything below is not shared
  }
  return shared;
}

export function SelectionBreadcrumb({
  html,
  layout,
  selection,
  groupIds,
  blockLabels,
  onSelectPage,
  onSelectNode,
}: {
  /** The artifact's SOURCE html (load-normalized — containers carry identity). */
  html: string;
  layout: string;
  selection: StudioSelection;
  /** ADR-519 D4.1 — the ⇧-click set. Over a set the chain names the SHARED
   *  parent and the count, never the primary's own label: the innermost rung
   *  is a single subject and a set does not have one. Length < 2 = no set. */
  groupIds?: string[];
  /** ADR-544 D4 — the served kind→label map. The crumb says the registry's
   *  word ("Text"), never the substrate's attribute ("prose"), and an Area
   *  reads as its role + place ("Body (left)"), never its authored name. */
  blockLabels?: Record<string, string>;
  /** Select a page by index — the navigator's page-select path. */
  onSelectPage: (index: number) => void;
  /** Select a container/block — the navigator's structure-tree path. */
  onSelectNode: (node: { blockId: string; label: string; kind: string | null }) => void;
}) {
  const { pageIndex, segments } = useMemo((): {
    pageIndex: number | null;
    segments: CrumbSegment[];
  } => {
    const none = { pageIndex: null, segments: [] as CrumbSegment[] };
    if (typeof window === 'undefined' || !html) return none;
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const pages = Array.from(doc.querySelectorAll(STRUCTURAL_PAGE_SEL));

    // A page-grain selection: the chain is just the page.
    const selectedPageIndex = selection.slideIndex ?? selection.pageIndex;
    if (!selection.blockId) {
      if (selectedPageIndex == null || !pages[selectedPageIndex]) return none;
      return {
        pageIndex: selectedPageIndex,
        segments: [
          { blockId: null, label: pageNoun(layout, selectedPageIndex), kind: null, current: true },
        ],
      };
    }

    const esc =
      typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(selection.blockId) : selection.blockId;
    const el = doc.querySelector(`[data-block-id="${esc}"]`);
    if (!el) return none;
    const pageEl = el.closest(STRUCTURAL_PAGE_SEL);
    if (!pageEl) return none;
    const idx = pages.indexOf(pageEl);
    if (idx < 0) return none;

    const chain = climbChain(el as unknown as ClimbableElement, pageEl as unknown as ClimbableElement);
    const seg = (node: Element, current: boolean): CrumbSegment => ({
      blockId: node.getAttribute('data-block-id'),
      label: labelForElement(node, blockLabels),
      kind: node.getAttribute('data-block'),
      current,
    });

    // ADR-519 D4.1 — over a SET the chain names the shared parent and the
    // count. The primary's own ancestry below the shared parent is not the
    // set's ancestry, and its label is not the set's label: showing either is
    // the same staleness the pane withdrew (the crumb would read "› heading"
    // while five objects are boxed). One member is a selection, not a set.
    const ids = groupIds ?? [];
    if (ids.length > 1) {
      const members = ids
        .map((id) => {
          const e = typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(id) : id;
          return doc.querySelector(`[data-block-id="${e}"]`);
        })
        .filter((e): e is Element => !!e && !!e.closest(STRUCTURAL_PAGE_SEL));
      // A set spanning pages has no shared page, so it has no chain to draw.
      const samePage = members.length > 1 && members.every((m) => m.closest(STRUCTURAL_PAGE_SEL) === pageEl);
      if (samePage) {
        const shared = sharedChain(
          members.map((m) =>
            climbChain(m as unknown as ClimbableElement, pageEl as unknown as ClimbableElement),
          ),
        );
        return {
          pageIndex: idx,
          segments: [
            { blockId: null, label: pageNoun(layout, idx), kind: null, current: false },
            ...shared.map((c) => seg(c as unknown as Element, false)),
            { blockId: null, label: `${ids.length} objects`, kind: null, current: true },
          ],
        };
      }
    }

    return {
      pageIndex: idx,
      segments: [
        { blockId: null, label: pageNoun(layout, idx), kind: null, current: false },
        ...chain.map((c) => seg(c as unknown as Element, false)),
        seg(el, true),
      ],
    };
  }, [html, layout, groupIds, blockLabels, selection.blockId, selection.slideIndex, selection.pageIndex]);

  if (!segments.length) return null;

  return (
    <div
      // Over the canvas, bottom-left (the status-bar corner), under the slash
      // palette's layer. pointer-events only on itself — the canvas around it
      // stays live.
      className="pointer-events-auto absolute bottom-2 left-2 z-20 flex max-w-[70%] items-center gap-1 overflow-hidden rounded-md border border-border bg-background/90 px-2 py-1 text-[11px] shadow-sm backdrop-blur"
    >
      {segments.map((s, i) => (
        <span key={`${s.blockId ?? 'page'}-${i}`} className="flex min-w-0 items-center gap-1">
          {i > 0 && <span className="shrink-0 text-muted-foreground/40">›</span>}
          {s.current ? (
            <span className="truncate font-medium text-foreground">{s.label}</span>
          ) : (
            <button
              type="button"
              onClick={() =>
                s.blockId == null
                  ? pageIndex != null && onSelectPage(pageIndex)
                  : onSelectNode({ blockId: s.blockId, label: s.label, kind: s.kind })
              }
              title={`Select the ${s.label}`}
              className={`truncate transition-colors hover:text-foreground ${
                s.blockId != null && s.kind == null
                  ? 'text-emerald-700 dark:text-emerald-500' // containers — the navigator's own color
                  : 'text-muted-foreground'
              }`}
            >
              {s.label}
            </button>
          )}
        </span>
      ))}
    </div>
  );
}
