'use client';

/**
 * pane-layout — the ONE contract for a multi-pane surface's housing.
 *
 * ## The claim
 *
 * A surface that shows more than one pane at a time answers three questions:
 * *how much room do I have* (the ladder), *which panes are showing* (the
 * toggles), and *how wide is each* (the widths). Before this module those three
 * questions had **six** answers between four surfaces, and the divergence was
 * invisible to every check — the same shape as the pane-spine drift
 * (AUTHORING.md §"The pane"), one rung further out:
 *
 *  - the ladder: `useWorkbenchWidth` (Studio · Text · Desk) vs `CHAT_TWO_COLUMN_MIN_PX`
 *    = 600 hand-rolled in Chat;
 *  - the toggles: Studio `useState(false)` · Text `useState(true)` · Chat and
 *    Files none at all — and Studio/Text's only rendered at ONE rung of four;
 *  - the widths: three independent pointer-drag handlers with three key
 *    schemes (`yarnnn:shell:chat-drawer-width`, `yarnnn:pane-shell:nav-width:*`,
 *    `studio.navWidth`), three min/max bands, and two different pointer APIs.
 *
 * Three spellings of one rule is how the shell and the surface came to disagree
 * about what a tablet is (rule 15's own lesson). This module is the single home.
 *
 * ## The model: three slots, one rule each
 *
 *      ┌────────┬──────────────────────┬────────┐
 *      │  rail  │        canvas        │  side  │
 *      └────────┴──────────────────────┴────────┘
 *
 * **`canvas` is the subject and never yields** — it is the artifact, the
 * conversation, the thing the member came for. It has no toggle and no width of
 * its own: it takes what the chrome leaves (rule 15, generalized).
 *
 * **`rail` and `side` are chrome.** Each is independently *hideable* and
 * *resizable*, and folds in a declared order as room runs out.
 *
 * **A slot a surface does not compose is ABSENT, not broken.** Text has no rail;
 * Chat has no side. Absence is a property of the surface's grain, and it is
 * legitimate — the pane-spine rule's asymmetry ("absence is legitimate;
 * re-ordering never is") holds identically for the housing. What is never
 * legitimate is a second spelling of the ladder, the toggle, or the width.
 *
 * ## Why px and not %
 *
 * Every width here is px, clamped to a band, and additionally clamped against
 * the MEASURED container at render. A percentage survives a window resize by
 * staying proportional, which sounds right and is wrong at the small end: 30%
 * of a 1400px monitor is a comfortable 420px rail, and 30% of an 900px window
 * is a 270px rail beside a 630px canvas — the crush this ladder exists to
 * prevent, arriving through the member's own setting. A px width clamped to
 * `container / 3` cannot do that: the member's choice is honoured wherever it
 * fits and quietly bounded where it does not.
 *
 * ## Why the state is here and not in `useSurfacePreferences`
 *
 * That store answers *which surfaces are open and where the windows are* — the
 * OS's business, synced to the server so a fresh device inherits a desktop.
 * Pane widths are a property of one surface on one screen: a 520px rail chosen
 * on a 27" monitor is actively wrong on the laptop the member opens next. Local
 * by nature, so localStorage only — keyed per (workspace, user) through
 * `shellStateSuffix`, the ONE key-forming helper, so pane state scopes exactly
 * like every other piece of shell state and never leaks across a workspace
 * switch.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  MOBILE_BREAKPOINT_PX,
  PANE_FULL_LABELS_PX,
  PANE_SINGLE_PX,
  PANE_THREE_COLUMN_PX,
  shellStateSuffix,
} from '@/lib/shell/surface-preferences';

// ----------------------------------------------------------------------------
// The ladder
// ----------------------------------------------------------------------------

/** The live rung of the collapse ladder, widest → narrowest. */
export type PaneRung = 'full' | 'condensed' | 'two-pane' | 'single-pane';

/** Which of the three slots a surface is talking about. `canvas` is not a
 *  member: it has no toggle and no width, by construction. */
export type PaneSlot = 'rail' | 'side';

export interface PaneLadder {
  rung: PaneRung;
  /** Measured container width in px, or null before the first measurement.
   *  Callers clamping a persisted width against real room need the number. */
  measuredWidth: number | null;
  /** Three real columns fit side by side. */
  threeColumn: boolean;
  /** The side slot is an OVERLAY over the canvas, not a column beside it. */
  sideIsOverlay: boolean;
  /** One pane at a time, switched by the bottom tab bar. */
  singlePane: boolean;
  /** Verbs wear their full text labels. */
  fullLabels: boolean;
}

/** Derive the rung from a measured width. Exported for the gate, which asserts
 *  BEHAVIOUR at each boundary rather than pinning a spelling. */
export function rungForWidth(width: number): PaneRung {
  if (width < PANE_SINGLE_PX) return 'single-pane';
  if (width < PANE_THREE_COLUMN_PX) return 'two-pane';
  if (width < PANE_FULL_LABELS_PX) return 'condensed';
  return 'full';
}

/** Expand a rung into the flags surfaces branch on, so no caller re-derives
 *  "does this rung mean three columns" and gets it subtly different. */
export function ladderFromRung(
  rung: PaneRung,
  measuredWidth: number | null = null,
): PaneLadder {
  return {
    rung,
    measuredWidth,
    threeColumn: rung === 'full' || rung === 'condensed',
    sideIsOverlay: rung === 'two-pane',
    singlePane: rung === 'single-pane',
    fullLabels: rung === 'full',
  };
}

/**
 * Observe a surface's own width and report which rung is live.
 *
 * Returns a CALLBACK REF, and that is load-bearing. The first spelling of this
 * hook took a `RefObject` and observed it in a `useEffect([ref])`. It shipped
 * green — tsc, build, and 33 gate assertions — and never measured once, because
 * a surface returns its start state before it returns the workbench: at the
 * effect's only run `ref.current` was null, it bailed, and a stable `ref`
 * identity meant it never re-ran. The rung sat at its roomy default forever.
 * A callback ref cannot fail that way — React calls it with the node at attach
 * and null at detach, however many render branches precede the element.
 *
 * SSR-safe: reports the ROOMIEST rung until first measurement, so markup is
 * stable through hydration and never flashes the collapsed layout. Withhold,
 * never guess.
 */
export function usePaneLadder(): [(node: HTMLElement | null) => void, PaneLadder] {
  const [width, setWidth] = useState<number | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const setNode = useCallback((node: HTMLElement | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (!node) return;
    const measure = () => {
      const w = node.clientWidth;
      // Zero means "not laid out yet" (display:none, pre-paint), not
      // "infinitely narrow" — collapsing on it would flash on every mount.
      if (w > 0) setWidth(w);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(node);
    observerRef.current = ro;
  }, []);

  useEffect(() => () => observerRef.current?.disconnect(), []);

  return [setNode, ladderFromRung(width == null ? 'full' : rungForWidth(width), width)];
}

// ----------------------------------------------------------------------------
// Slot width — one band, one store, one drag
// ----------------------------------------------------------------------------

/** The band every resizable slot lives in.
 *
 *  MIN is the width below which a slot is a sliver that cannot show its own
 *  content — hiding it is the honest gesture, and that is what the toggle is
 *  for. MAX is a backstop; the real ceiling is the container clamp below, which
 *  is what actually protects the canvas. */
export const PANE_MIN_PX = 180;
export const PANE_MAX_PX = 560;

/** A slot may never take more than this share of the container, whatever the
 *  member persisted. This — not MAX — is the rule that keeps the canvas
 *  legible: a 520px rail chosen on a 27" monitor must not carry into an 800px
 *  window and re-create the crush through member state. */
export const PANE_MAX_SHARE = 1 / 3;

/** Resting widths, per slot. A rail lists subjects (names, timestamps); a side
 *  pane holds controls and a conversation, and wants a little more. */
export const PANE_DEFAULT_PX: Record<PaneSlot, number> = { rail: 288, side: 380 };

const WIDTH_KEY_PREFIX = 'yarnnn:pane:width:';
const SHOWN_KEY_PREFIX = 'yarnnn:pane:shown:';

const isBrowser = () => typeof window !== 'undefined' && typeof localStorage !== 'undefined';

/** The ONE key shape for pane state: prefix · surface · slot · (workspace,user).
 *  Scoped through `shellStateSuffix` so pane state cannot survive a workspace
 *  switch — the same rule the dock and window state already follow. */
function paneKey(prefix: string, surface: string, slot: PaneSlot, userId: string): string {
  return `${prefix}${surface}:${slot}:${shellStateSuffix(userId)}`;
}

/** Clamp a width to the band AND to the container's share ceiling. The single
 *  clamp — callers never re-spell it. */
export function clampPaneWidth(width: number, measuredWidth: number | null): number {
  const ceiling = measuredWidth == null
    ? PANE_MAX_PX
    : Math.min(PANE_MAX_PX, Math.floor(measuredWidth * PANE_MAX_SHARE));
  // A container narrower than 3×MIN cannot honour MIN and the share ceiling at
  // once. MIN wins: a slot at its floor is usable, a slot below it is a sliver.
  return Math.max(PANE_MIN_PX, Math.min(Math.max(ceiling, PANE_MIN_PX), Math.round(width)));
}

export interface PaneSlotState {
  /** Is the slot showing? Composes the toggle's `aria-expanded` and its label. */
  shown: boolean;
  toggle: () => void;
  /** The width to render, already clamped against the live container. */
  width: number;
  /** Begin a drag. Wire to the divider's `onPointerDown`. */
  startResize: (e: React.PointerEvent) => void;
  /** True while a drag is in flight — surfaces suppress transitions with it. */
  resizing: boolean;
}

/**
 * One slot's show/hide + width, persisted per (surface, slot, workspace, user).
 *
 * @param surface  the surface's slug — the persistence namespace
 * @param slot     which slot; picks the resting default
 * @param userId   scopes the key; null/'' before the user is known, in which
 *   case nothing is read or written — the resting defaults apply and the
 *   member's choice starts persisting as soon as the id arrives.
 * @param ladder   the live ladder, for the container clamp
 * @param opts.defaultShown  resting visibility (default true)
 * @param opts.edge  which edge the divider sits on. `'start'` = the slot is
 *   LEFT of its divider (a rail: dragging right grows it). `'end'` = the slot
 *   is RIGHT of its divider (a side pane: dragging left grows it).
 */
export function usePaneSlot(
  surface: string,
  slot: PaneSlot,
  userId: string | null,
  ladder: PaneLadder,
  opts: { defaultShown?: boolean; edge?: 'start' | 'end' } = {},
): PaneSlotState {
  const { defaultShown = true, edge = slot === 'rail' ? 'start' : 'end' } = opts;

  const [shown, setShown] = useState(defaultShown);
  const [width, setWidth] = useState(PANE_DEFAULT_PX[slot]);
  const [resizing, setResizing] = useState(false);
  /** Has the member's own choice (persisted or clicked) taken over? Until it
   *  has, a caller may still move `defaultShown` — a surface whose resting
   *  visibility depends on what it opened (Studio: a deck wants its strip, a
   *  document does not) can only know that after the artifact loads. Once the
   *  member has chosen, the default never fights them again. */
  const memberChose = useRef(false);

  // Hydrate once the user is known. Persisted state is a CACHE of the member's
  // choice, never a source of truth about what fits — the clamp at read time is
  // what makes a stale width from a bigger monitor harmless.
  useEffect(() => {
    if (!userId || !isBrowser()) return;
    try {
      const w = localStorage.getItem(paneKey(WIDTH_KEY_PREFIX, surface, slot, userId));
      if (w) {
        const n = Number(w);
        if (Number.isFinite(n)) setWidth(n);
      }
      const s = localStorage.getItem(paneKey(SHOWN_KEY_PREFIX, surface, slot, userId));
      if (s === '0' || s === '1') {
        memberChose.current = true;
        setShown(s === '1');
      }
    } catch {
      // storage unavailable (private browsing) — resting defaults apply
    }
  }, [surface, slot, userId]);

  // Follow a MOVING default until the member has chosen. Depending on `shown`
  // here would make this a feedback loop; it depends only on the default, so it
  // fires exactly when the caller's resting answer actually changes.
  useEffect(() => {
    if (!memberChose.current) setShown(defaultShown);
  }, [defaultShown]);

  const toggle = useCallback(() => {
    memberChose.current = true;
    setShown((v) => {
      const next = !v;
      if (userId && isBrowser()) {
        try {
          localStorage.setItem(
            paneKey(SHOWN_KEY_PREFIX, surface, slot, userId),
            next ? '1' : '0',
          );
        } catch {}
      }
      return next;
    });
  }, [surface, slot, userId]);

  // The drag. Pointer events (not mouse) so a stylus and a trackpad behave the
  // same, and `setPointerCapture` so a fast drag that leaves the divider still
  // tracks — the failure mode of the three window-listener spellings this
  // replaces was a drag that silently detached when the pointer outran it.
  const startResize = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      const el = e.currentTarget as HTMLElement;
      el.setPointerCapture?.(e.pointerId);
      const startX = e.clientX;
      const startW = width;
      setResizing(true);

      const onMove = (ev: PointerEvent) => {
        const delta = edge === 'start' ? ev.clientX - startX : startX - ev.clientX;
        setWidth(clampPaneWidth(startW + delta, ladder.measuredWidth));
      };
      const onUp = () => {
        el.releasePointerCapture?.(e.pointerId);
        el.removeEventListener('pointermove', onMove);
        el.removeEventListener('pointerup', onUp);
        el.removeEventListener('pointercancel', onUp);
        setResizing(false);
        // Persist the settled width. Read through the setter so what is stored
        // is what is rendered, never a stale closure value.
        setWidth((w) => {
          if (userId && isBrowser()) {
            try {
              localStorage.setItem(
                paneKey(WIDTH_KEY_PREFIX, surface, slot, userId),
                String(w),
              );
            } catch {}
          }
          return w;
        });
      };

      el.addEventListener('pointermove', onMove);
      el.addEventListener('pointerup', onUp);
      el.addEventListener('pointercancel', onUp);
    },
    [edge, width, ladder.measuredWidth, surface, slot, userId],
  );

  return {
    shown,
    toggle,
    // Clamp on every render, not only on drag: the container can change width
    // under a persisted value (window resize, drawer open) and the stored number
    // must never win over the room actually available.
    width: clampPaneWidth(width, ladder.measuredWidth),
    startResize,
    resizing,
  };
}

/**
 * Is a slot actually rendered as a COLUMN right now?
 *
 * The composition of the two rules, in one place, because branching on
 * `shown && threeColumn` at each call site is exactly how Studio and Text came
 * to disagree about when a toggle should exist. Below the three-column rung a
 * slot is an overlay or a tab, never a column — so a member's `shown` choice
 * governs the column, and the rung governs whether there is a column at all.
 */
export function slotIsColumn(ladder: PaneLadder, state: PaneSlotState): boolean {
  return ladder.threeColumn && state.shown;
}

export { MOBILE_BREAKPOINT_PX };
