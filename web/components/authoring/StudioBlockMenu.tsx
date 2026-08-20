'use client';

/**
 * StudioBlockMenu — the canvas right-click menu (ADR-462).
 *
 * D1: every row is a SECOND ENTRANCE to an op that already exists — never a
 * second write path, never an eighth operation (ADR-443 D2). The duplication
 * with the Design tab and the toolbar is deliberate and ratified (ADR-367 D3's
 * macOS tiered-access principle): right-click is the fast path, the Design tab
 * is the dwell, one implementation underneath.
 *
 * D4: the free/metered line is the thing this component makes VISIBLE. A row
 * that spends a metered lane turn wears the `AI` badge; a free row wears
 * nothing (silence is the signal — most of the menu is free, so marking the
 * exception is cheaper than marking the rule). The badge means METERED, not
 * MUTATING: `Check this…` writes nothing and is badged, because it costs a turn.
 *
 * This is NOT `FileContextMenu` reused: that contract is file-shaped (path,
 * name, file verbs) and a block is not a file. It borrows its dismissal
 * behaviour and its visual conventions, and nothing else.
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  Copy, ClipboardPaste, CopyPlus, Plus, Trash2, Type,
  ArrowUp, ArrowDown, ChevronsUp, ChevronsDown, ChevronRight, MessageSquare, PenLine, Sparkles, SearchCheck, Link2, History,
} from 'lucide-react';
import type { StudioContextTarget } from './StudioCanvas';
import { isConvertible, turnIntoTargets } from './StudioDesignTab';
import { categorizeBlockRows, type BlockCategory } from './blockRows';
import { BlockThumb } from './BlockThumb';
import { HEADING_RUNGS } from '../workspace/viewers/projection';

export interface StudioBlockMenuProps {
  target: StudioContextTarget;
  onClose: () => void;
  /** Mechanical, free — each already exists (ADR-462 D1). */
  onCopy: () => void;
  onPaste: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  /** ADR-479 D5 — Turn into is BLOCK-scoped, so unlike Re-arrange it belongs in
   *  this menu; it was merely wired lazily (it opened the Design tab and left
   *  the member to find the picker). Now it offers the legal kinds inline, in
   *  one gesture. The caller runs the same `convertBlock` op the Design tab
   *  runs — a second entrance, never a second write path (ADR-462 D1). */
  onTurnInto: (kind: string, label: string, fragment: string) => void;
  /** The served block vocabulary — the submenus resolve each kind's label and
   *  insertion fragment from it, so the menu never restates the registry.
   *  ADR-539 D2: rows carry `convertible` + `cites`; the menu reads them off
   *  the row (the New/Add tiers partition by `cites` via the ONE grouping
   *  module — never a hand list). */
  blocks?: Array<{
    kind: string;
    label: string;
    fragment: string;
    convertible?: boolean;
    cites?: 'none' | 'source' | 'picture' | 'fragment';
    tier?: 'text' | 'object';
  }>;
  /** ADR-539 D3 — the served rung set (falls back to the runtime's pinned copy). */
  headingRungs?: number[];
  /** ADR-541 D4 — how many blocks the right-clicked block stands in for: 0/1 =
   *  just itself; >1 = it is a member of the live set (range or ⇧-click), so
   *  the set-taking rows act on all N and SAY so, and the single-subject rows
   *  withdraw with the one notice. Derived by the surface from the SAME
   *  arity the pane reads — one derivation, two doors. */
  setCount?: number;
  /** Move the block one position earlier in its flow — document order, and it
   *  says so. */
  onMoveUp: () => void;
  onMoveDown: () => void;
  /** ADR-471 D-d: z earned its token, so Bring forward/backward are finally
   *  honest verbs — stacking order among POSITIONED blocks (target.positioned
   *  gates the rows; nudgeZ backstops the op side). */
  onBringForward: () => void;
  onBringBackward: () => void;
  /** Metered (D6): each SEEDS the composer and sends nothing. `onAsk` is the
   *  open question (relocated here 2026-07-24 when the Properties block-verb
   *  section was deleted — this menu became its only mount): it seeds "About
   *  the ‹kind› block…" with the selection's id + text and flips to Chat. Not
   *  a rewrite-with-an-adjective, so it does not violate D6's two-verb
   *  reasoning — it is the third DISTINCT act, an ask rather than an edit. */
  onRewrite: () => void;
  onCheck: () => void;
  onAsk: () => void;
  /** The two rows no reference can ship (D3) — a block has an address, and the
   *  revision chain joins by that same id. */
  onCopyLink: () => void;
  onHistory: () => void;
  /** ADR-579 D6.a — the LOCATED half of the paged mouse insert route: the
   *  New ▸ / Add ▸ tiers render the served vocabulary INLINE (label-only, the
   *  fast path for a member who knows what they want) and land each pick
   *  through the surface's one insert landing. Absent on flow (the caret
   *  answers there), so the tiers simply do not render. */
  onInsertKind?: (kind: string, label: string, fragment: string) => void;
  /** ADR-482 D5: the layout's composition mode. The menu was mode-BLIND — it
   *  offered Move up/down against a continuous prose surface where a block is
   *  an ANNOTATION, not an enclosure (ADR-480 D2), so reordering "blocks" asks
   *  the member to think in a unit the medium no longer has. Rows whose meaning
   *  depends on the enclosure are withdrawn on flow; rows that act on an
   *  addressable REGION (copy, duplicate, delete, turn-into, the AI acts,
   *  link, history) are kept, because addressing survives the dissolution.
   *  Undefined until the registry answers — treated as flow, matching the
   *  chrome's show-less default (ADR-482 D3). */
  mode?: 'flow' | 'paged';
  /** ADR-482 D9: is there a block on the in-memory clipboard? `Paste here` was
   *  the only unconditional row, so an empty-canvas right-click rendered a
   *  menu of one act that could not happen. A paste offer requires something
   *  to paste. */
  hasClipboard?: boolean;
  /** ADR-586 D6 — the toolbar's contextual [Update] opens THIS menu with the
   *  Update tier already expanded (a verb door opens its verb's contents —
   *  ADR-579 D6.a's law, kept). One definition of the block acts, two mounts. */
  initialOpen?: 'update';
}

function Row({
  icon, children, onClick, meter, shortcut,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
  meter?: boolean;
  shortcut?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] ${
        meter ? 'hover:bg-amber-50 dark:hover:bg-amber-950/30' : 'hover:bg-accent'
      }`}
    >
      <span className={meter ? 'text-amber-700 dark:text-amber-500' : 'text-muted-foreground'}>
        {icon}
      </span>
      <span className="truncate">{children}</span>
      {meter && (
        // The badge: ochre, a filled dot, the word AI. Three redundant signals
        // carry the line (group header + badge + hue) because it must be
        // impossible to miss at a glance or mistake at speed (D4).
        <span className="ml-auto inline-flex items-center gap-1 rounded-[3px] border border-amber-300/70 bg-amber-50 px-1 py-[1px] text-[9px] font-semibold tracking-wide text-amber-700 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-500">
          <span className="h-[5px] w-[5px] rounded-full bg-current" />
          AI
        </span>
      )}
      {!meter && shortcut && (
        <span className="ml-auto text-[10.5px] tabular-nums text-muted-foreground/60">
          {shortcut}
        </span>
      )}
    </button>
  );
}

/** ADR-586 D4 as DECIDED — a tier is a FLYOUT, not an inline expansion.
 *
 *  D4 specified "nested panels measure themselves and FLIP (left of the anchor
 *  near the right edge, above near the bottom)". The first build substituted
 *  inline tiers and recorded a positioning note arguing they were strictly more
 *  robust (no detached panel can run off an edge). That is true of the EDGE and
 *  false of the MENU: an inline tier changes the parent's height, so the whole
 *  box re-clamps and JUMPS out from under the pointer — the 2026-08-19
 *  click-pass measured it moving 125→352px tall and 647→421 top on one open.
 *  A flyout leaves the parent where the member right-clicked, which is what
 *  every reference menu (Figma, Finder, PowerPoint) does.
 *
 *  The flip is MEASURED, never guessed: render at the anchor, read the real
 *  rect, then flip left / shift up only when the panel would leave the viewport.
 *  Clamping stays as the backstop for a panel taller than the viewport itself.
 *
 *  NARROW SCREENS KEEP THE INLINE TIER. A flyout needs a pointer and room
 *  beside the parent; a phone has neither, and the sheet housing (D5) is a
 *  drill, not a hover surface. Under the breakpoint this renders exactly what
 *  it rendered before — deliberately lower scope, one component, no second
 *  mechanism for callers to pick between.
 */
const FLYOUT_MIN_WIDTH = 168;

function Flyout({
  open, children, inline,
}: {
  open: boolean;
  children: React.ReactNode;
  /** True under the narrow breakpoint: render as the old inline tier. */
  inline: boolean;
}) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    if (!open || inline) { setPos(null); return; }
    const el = panelRef.current;
    // Anchor on the ROW BUTTON, not the wrapper. The wrapper's rect happens to
    // equal the button's only because this panel is `fixed` and so contributes
    // no height — an invariant held by a CSS property declared elsewhere, which
    // is exactly the kind of coupling that breaks silently later. Ask for the
    // element we actually mean.
    const row = el?.parentElement?.querySelector(':scope > button');
    if (!el || !row) return;
    const r = row.getBoundingClientRect();
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8;
    // Horizontal: open to the RIGHT of the parent row; flip LEFT when the panel
    // would cross the right edge. Flipping is preferred over clamping so the
    // panel never overlaps the menu it came from.
    const right = r.right - 2;
    const left = right + width + MARGIN > window.innerWidth ? r.left - width + 2 : right;
    // Vertical: top-align with the row, then shift UP by the overflow so the
    // whole panel fits. Clamp at MARGIN for a panel taller than the viewport
    // (it scrolls internally via max-height).
    const over = r.top + height + MARGIN - window.innerHeight;
    const top = over > 0 ? Math.max(MARGIN, r.top - over) : r.top;
    setPos({ left: Math.max(MARGIN, left), top });
  }, [open, inline]);

  if (!open) return null;
  if (inline) {
    return <div className="mt-0.5 border-l-2 border-border/60 pl-1">{children}</div>;
  }
  return (
    <div
      ref={panelRef}
      className="fixed z-[60] max-h-[calc(100vh-16px)] overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md"
      style={{
        left: pos?.left ?? -9999,
        top: pos?.top ?? -9999,
        minWidth: FLYOUT_MIN_WIDTH,
        // Pre-measure paint is off-screen rather than at the anchor: a panel
        // that paints at the wrong edge and corrects is a visible jump.
        visibility: pos ? 'visible' : 'hidden',
      }}
    >
      {children}
    </div>
  );
}

const SEP = <div className="my-1 h-px bg-border" />;
const ICO = 'h-3.5 w-3.5';

export function StudioBlockMenu({
  target, onClose, onCopy, onPaste, onDuplicate, onDelete, setCount,
  onTurnInto, blocks, headingRungs, onMoveUp, onMoveDown, onBringForward, onBringBackward, onRewrite, onCheck, onAsk,
  onCopyLink, onHistory, onInsertKind, mode, hasClipboard, initialOpen,
}: StudioBlockMenuProps) {
  const [turnOpen, setTurnOpen] = useState(false);
  // ADR-579 D5 two-tier — the verb tiers (one open at a time). ADR-586 D6:
  // the toolbar's contextual Update mounts this menu with its tier expanded.
  const [updateOpen, setUpdateOpen] = useState(initialOpen === 'update');
  const [askOpen, setAskOpen] = useState(false);
  // ADR-586 D4 — the located insert tiers are the CATEGORIES (one open at a
  // time), replacing the ADR-579 New ▸/Add ▸ provenance pair.
  const [insertOpen, setInsertOpen] = useState<BlockCategory | null>(null);
  // ADR-586 D4/D5 — the tier housing. Flyouts need a pointer and room BESIDE
  // the parent; under the narrow breakpoint neither exists, so tiers stay
  // inline there (the same lower-scope call D5 makes for the sheet). Measured
  // once per open: the menu closes on resize, so it cannot go stale.
  const [inlineTiers] = useState<boolean>(
    () => typeof window !== 'undefined' && window.innerWidth < 640,
  );
  // Dismissal. NOTE the parent-window blind spot: the Studio canvas is a
  // SANDBOXED IFRAME, so a click on the artifact fires in the frame's own
  // document and these parent listeners never hear it. The canvas's point
  // message closes the menu for that case (StudioSurface.onPoint) — these
  // cover the parent chrome (rails, panels, toolbar), a second right-click
  // elsewhere, and any scroll (a menu anchored to a point is a lie once the
  // point moves).
  //
  // ESCAPE IS THE SAME BLIND SPOT, and the parent-window listener below did NOT
  // cover it despite this comment once claiming so: a right-click leaves focus
  // INSIDE the frame, so the member's Escape fires in the frame's document and
  // `window.addEventListener('keydown', …)` here never runs. The menu could only
  // be dismissed with the mouse. The runtime now bridges the key out as
  // `yarnnn-canvas-escape` (the `yarnnn-canvas-press` shape); both routes are
  // kept because focus may legitimately be on either side — the parent listener
  // still serves a menu opened while focus is in the parent chrome.
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const onFrameKey = (e: MessageEvent) => {
      const t = (e.data as { type?: string } | null)?.type;
      // SCROLL IS THE SAME BLIND SPOT as Escape. The capture-phase `scroll`
      // listener below cannot hear the iframe's own scroller (opaque origin),
      // so a menu anchored to a point stayed pinned while the block it names
      // travelled away — exactly the lie the scroll listener exists to prevent,
      // and it was only ever prevented for parent-side scrollers. The runtime
      // already reports in-frame scrolling for the canvas's position restore;
      // this listens to the same message.
      if (t === 'yarnnn-canvas-escape' || t === 'yarnnn-scroll-pos') onClose();
    };
    window.addEventListener('click', close);
    window.addEventListener('contextmenu', close);
    window.addEventListener('resize', close);
    window.addEventListener('scroll', close, true); // capture: any scroller
    window.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrameKey);
    return () => {
      window.removeEventListener('click', close);
      window.removeEventListener('contextmenu', close);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrameKey);
    };
  }, [onClose]);

  const run = (fn: () => void) => { fn(); onClose(); };
  const hasBlock = !!target.blockId;
  // ADR-482 D5: `paged` is the affirmative test — an unresolved mode withholds
  // enclosure-shaped rows rather than guessing them on (the D3 principle).
  const isPaged = mode === 'paged';
  // ADR-525 D5 — the ENCLOSURE verbs (Duplicate/Delete) read the runtime's tier.
  // This menu already refused Move up/down on flow with the right reasoning
  // ("reordering is an enclosure verb"), but kept Duplicate/Delete — the same
  // unit verbs ADR-521 D6 retired from the keyboard for the same reason. Turn
  // into STAYS: it is structure-tier (ADR-521 D2), reachable from a caret, and
  // is Docs' own affordance. The AI rows stay too — they act on text.
  const isTextTier = target.tier === 'text';
  // ADR-541 D4 — is the right-clicked block standing in for a live set?
  const inSet = (setCount ?? 0) > 1;

  // The legal conversions for THIS block (ADR-456 W2 + ADR-479 D5): a text kind
  // that isn't already what it is, and never a citation — `convertBlock`
  // refuses a block carrying data-ref (flattening would bake a live reference
  // into prose), so offering it would be a row the op declines.
  // ADR-487 D1: one target list, two mounts — heading expands to its level
  // targets. The menu cannot know the block's current TAG (the selection
  // message carries kind, not tag), so it passes null: the current level is
  // offered and lands as a convertBlock no-op, never a lie about capability.
  // ADR-539 D2 — convertibility is read off the served row, not a hand-list;
  // this menu and the pane now consult the SAME declaration by construction.
  const turnIntoKinds =
    hasBlock && target.blockKind && !target.dataRef
      && isConvertible(blocks, target.blockKind)
      ? turnIntoTargets(blocks ?? [], headingRungs ?? [...HEADING_RUNGS], target.blockKind, null)
      : [];

  // The canvas is an iframe: its coordinates are frame-local. The caller passes
  // them already mapped to the page.
  //
  // The vertical clamp is MEASURED, not assumed. It used to be a static
  // `innerHeight - 330`, a guess at the COLLAPSED height — but "Turn into"
  // expands its targets INLINE, inside this same box (up to 7 rows for a prose
  // block ≈ +170px). Nothing re-clamped on expansion and the box has no
  // max-height, so a right-click in the lower third of the window pushed the
  // expanded rows below the viewport, unreachable and unscrollable. Measuring
  // the real box and re-running when `turnOpen` changes keeps the whole menu on
  // screen at whatever height it actually is.
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [clamped, setClamped] = useState<{ left: number; top: number } | null>(null);
  // The tier state as ONE scalar dep — and only where a tier can change the
  // box's height (the inline housing). On a pointer screen it is a constant,
  // so opening a flyout never re-clamps the parent.
  const tierDeps = inlineTiers
    ? `${turnOpen}|${insertOpen}|${updateOpen}|${askOpen}`
    : '';
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8; // never flush against the edge
    setClamped({
      left: Math.max(MARGIN, Math.min(target.x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(target.y, window.innerHeight - height - MARGIN)),
    });
    // ADR-586 D4 (flyout recut): on a pointer screen the tier state must NOT
    // re-clamp the parent — a flyout does not change the parent's height, and
    // re-clamping on open is exactly what MOVED the menu out from under the
    // pointer (measured 647→421 top on one open, 2026-08-19). The INLINE
    // housing DOES still grow the box, so there the tier state must re-clamp.
    // One dep list of FIXED LENGTH (a conditional array is a React violation):
    // `tierDeps` collapses to a constant where a tier cannot change the height.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- tierDeps is the guarded projection
  }, [target.x, target.y, turnIntoKinds.length, tierDeps]);

  // First paint uses the raw point (with the old conservative guard) so the menu
  // never flashes at 0,0; the layout effect corrects it before the browser
  // paints, then again whenever the submenu changes the height.
  const left = clamped?.left
    ?? (typeof window !== 'undefined' ? Math.min(target.x, window.innerWidth - 250) : target.x);
  const top = clamped?.top
    ?? (typeof window !== 'undefined' ? Math.min(target.y, window.innerHeight - 330) : target.y);

  // ADR-482 D9: a menu with no acts is not a menu — an empty bordered box that
  // appears, says nothing, and must be dismissed. The rule stands; what counts
  // as "an act" grew. On `paged`, Insert is now a real act available on bare
  // canvas (it lands on the current page), and it is precisely the case a
  // right-click on an empty slide SHOULD serve — so suppressing here would
  // re-hide the route this pass exists to give the mouse back. On flow the row
  // is absent, so the original condition is what still decides.
  const hasInsert = !!onInsertKind && isPaged;
  if (!hasBlock && !hasClipboard && !hasInsert) return null;

  return (
    <div
      ref={boxRef}
      className="fixed z-50 max-h-[calc(100vh-16px)] min-w-[228px] overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* The CATEGORY tiers lead on `paged`, and only on paged — the LOCATED
          half of the mouse insert route that replaced '/' there. On `flow`
          the tiers are absent: the caret IS the insertion point and '/' still
          answers. ADR-586 D4: the tiers are the SAME categories the toolbar
          door renders (Components · Text · Media · Data — the one derivation,
          never a hand list; Slide stays with the toolbar door, this menu's
          grain is the located block). Each tier expands a compact thumbnail
          grid and lands through the surface's one insert landing. The whole
          box RE-MEASURES when a tier opens (the clamp's deps), so an
          expansion near the bottom repositions upward — accommodative, not
          pushed off-screen. */}
      {onInsertKind && isPaged && (
        <>
          {categorizeBlockRows(blocks ?? [], 'paged').map((g) => {
            const opened = insertOpen === g.key;
            const toggle = () => {
              setInsertOpen((v) => (v === g.key ? null : g.key));
              setUpdateOpen(false); setAskOpen(false);
            };
            return (
              <div
                key={g.key}
                className="relative"
                // Hover opens the tier on a pointer screen — the reference
                // behaviour (Figma/Finder). Click still works and is the only
                // route when tiers are inline. Hover never CLOSES: leaving
                // toward the panel would dismiss what you are reaching for.
                onMouseEnter={inlineTiers ? undefined : () => {
                  setInsertOpen(g.key); setUpdateOpen(false); setAskOpen(false);
                }}
              >
                <button
                  type="button"
                  onClick={toggle}
                  className={`flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-accent ${opened && !inlineTiers ? 'bg-accent' : ''}`}
                >
                  <span className="text-muted-foreground"><Plus className={ICO} /></span>
                  <span className="truncate">{g.label}</span>
                  <ChevronRight
                    className={`ml-auto h-3.5 w-3.5 text-muted-foreground/60 transition-transform ${opened && inlineTiers ? 'rotate-90' : ''}`}
                  />
                </button>
                <Flyout open={opened} inline={inlineTiers}>
                  <div className={`grid grid-cols-3 gap-1 ${inlineTiers ? 'mt-0.5 p-1 pl-2' : 'w-[228px] p-1'}`}>
                    {g.items.map((b) => (
                      <button
                        key={b.kind}
                        type="button"
                        title={b.description}
                        onClick={() => run(() => onInsertKind(b.kind, b.label, b.fragment))}
                        className="flex flex-col gap-0.5 rounded border border-transparent p-1 text-left hover:border-border hover:bg-accent"
                      >
                        <BlockThumb kind={b.kind} />
                        <span className="truncate text-[10px]">{b.label}</span>
                      </button>
                    ))}
                  </div>
                </Flyout>
              </div>
            );
          })}
          {(hasBlock || hasClipboard) && SEP}
        </>
      )}
      {hasBlock && (
        <Row icon={<Copy className={ICO} />} onClick={() => run(onCopy)} shortcut="⌘C">Copy</Row>
      )}
      {/* ADR-482 D9: Paste here was the ONE ungated row, so a right-click on
          empty canvas produced a one-item menu offering to paste a block
          clipboard that is usually empty — the operator saw it "a lot of the
          time" precisely because everything else had correctly hidden itself.
          A paste needs something TO paste; gating on the clipboard makes the
          menu honest, and an empty right-click now yields no menu at all
          rather than a menu of one impossible act. */}
      {hasClipboard && (
        <Row icon={<ClipboardPaste className={ICO} />} onClick={() => run(onPaste)} shortcut="⌘V">
          Paste here
        </Row>
      )}
      {hasBlock && (
        <>
          {/* ADR-525 D5 — the unit verbs are withheld on the text tier: on flow
              a paragraph is an annotation, not an enclosure, and ⌘D/⌫ already
              belong to the platform there (ADR-521 D6). Objects keep them. */}
          {!isTextTier && (
            <>
              {SEP}
              {/* ADR-541 D4 — over a live set these rows take the WHOLE set
                  (the surface's handlers expand to one N-block revision), so
                  the row says the count instead of implying one block. */}
              <Row
                icon={<CopyPlus className={ICO} />}
                onClick={() => run(onDuplicate)}
                shortcut="⌘D"
              >
                {inSet ? `Duplicate ${setCount} blocks` : 'Duplicate'}
              </Row>
              <Row icon={<Trash2 className={ICO} />} onClick={() => run(onDelete)} shortcut="⌫">
                {inSet ? `Delete ${setCount} blocks` : 'Delete'}
              </Row>
            </>
          )}
          {SEP}
          {/* ADR-579 D5, two-tier (operator-ratified): the verb rows ARE the
              menu's top tier — Update and Ask expand inline (the same pattern
              the convert submenu uses), so the flat menu stays short and the
              triad reads at a glance. Every wired handler is unchanged: a
              tier is chrome, never a second write path (ADR-462 D1). The seam
              inside each verb is WHO — the badge marks the colleague's paid
              acts (ADR-462 D4); plumbing above stays unlabeled. */}
          <div
            className="relative"
            onMouseEnter={inlineTiers ? undefined : () => {
              setUpdateOpen(true); setAskOpen(false); setInsertOpen(null);
            }}
          >
          <button
            type="button"
            onClick={() => { setUpdateOpen((v) => !v); setAskOpen(false); setInsertOpen(null); }}
            className={`flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-accent ${updateOpen && !inlineTiers ? 'bg-accent' : ''}`}
          >
            <span className="text-muted-foreground"><PenLine className={ICO} /></span>
            <span className="truncate">Update</span>
            <ChevronRight
              className={`ml-auto h-3.5 w-3.5 text-muted-foreground/60 transition-transform ${updateOpen && inlineTiers ? 'rotate-90' : ''}`}
            />
          </button>
          <Flyout open={updateOpen} inline={inlineTiers}>
            <div className={inlineTiers ? '' : 'min-w-[196px]'}>
              {/* ADR-479 D5 — Turn into, in one gesture. Shown only when the
                  conversion is LEGAL: a text kind, and never a citation (a
                  figure or table wears data-ref on its own root, and
                  flattening it would bake a live reference into prose — the
                  op refuses, so the menu must not offer). */}
              {turnIntoKinds.length > 0 && (
                <div
                  className="relative"
                  onMouseEnter={inlineTiers ? undefined : () => setTurnOpen(true)}
                >
                  <button
                    type="button"
                    onClick={() => setTurnOpen((v) => !v)}
                    className={`flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-accent ${turnOpen && !inlineTiers ? 'bg-accent' : ''}`}
                  >
                    <span className="text-muted-foreground"><Type className={ICO} /></span>
                    <span className="truncate">Turn into</span>
                    <ChevronRight className="ml-auto h-3.5 w-3.5 text-muted-foreground/60" />
                  </button>
                  <Flyout open={turnOpen} inline={inlineTiers}>
                    <div className={inlineTiers ? '' : 'min-w-[160px]'}>
                      {turnIntoKinds.map((b) => (
                        <button
                          key={b.key}
                          type="button"
                          onClick={() => run(() => onTurnInto(b.kind, b.label, b.fragment))}
                          className="flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-accent"
                        >
                          <span className="truncate">{b.label}</span>
                        </button>
                      ))}
                    </div>
                  </Flyout>
                </div>
              )}
              {/* Move up/down is DOCUMENT order; Bring forward/backward is
                  Z-ORDER on a POSITIONED block (ADR-471 D-d). PAGED only for
                  reordering (ADR-482 D5 — on flow a block is an annotation,
                  not an enclosure). ADR-541 D4: the single-subject rows
                  withdraw over a set and SAY so once. */}
              {inSet && (isPaged || target.positioned) && (
                <p className="px-2 py-[5px] text-[10px] leading-snug text-muted-foreground">
                  Move and stacking act on one block at a time ({setCount} selected).
                </p>
              )}
              {isPaged && !inSet && (
                <>
                  <Row icon={<ArrowUp className={ICO} />} onClick={() => run(onMoveUp)}>
                    Move up
                  </Row>
                  <Row icon={<ArrowDown className={ICO} />} onClick={() => run(onMoveDown)}>
                    Move down
                  </Row>
                </>
              )}
              {target.positioned && !inSet && (
                <>
                  <Row icon={<ChevronsUp className={ICO} />} onClick={() => run(onBringForward)}>
                    Bring forward
                  </Row>
                  <Row icon={<ChevronsDown className={ICO} />} onClick={() => run(onBringBackward)}>
                    Bring backward
                  </Row>
                </>
              )}
              {/* D6: Rewrite SEEDS the composer and sends nothing — a head
                  start on a sentence, not a button. Shorter/longer/sharper
                  are things the member TYPES (no rewrites-with-adjectives). */}
              <Row icon={<Sparkles className={ICO} />} onClick={() => run(onRewrite)} meter>
                Rewrite…
              </Row>
            </div>
          </Flyout>
          </div>
          {/* ASK — neither row lands a revision; both produce an ANSWER in
              the pane (the badge means METERED, not MUTATING — ADR-462 D4,
              now structural). The old mechanism-named header is retired per
              ADR-579 D3. */}
          <div
            className="relative"
            onMouseEnter={inlineTiers ? undefined : () => {
              setAskOpen(true); setUpdateOpen(false); setInsertOpen(null);
            }}
          >
          <button
            type="button"
            onClick={() => { setAskOpen((v) => !v); setUpdateOpen(false); setInsertOpen(null); }}
            className={`flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-amber-50 dark:hover:bg-amber-950/30 ${askOpen && !inlineTiers ? 'bg-amber-50 dark:bg-amber-950/30' : ''}`}
          >
            <span className="text-amber-700 dark:text-amber-500"><MessageSquare className={ICO} /></span>
            <span className="truncate">Ask</span>
            <ChevronRight
              className={`ml-auto h-3.5 w-3.5 text-muted-foreground/60 transition-transform ${askOpen && inlineTiers ? 'rotate-90' : ''}`}
            />
          </button>
          <Flyout open={askOpen} inline={inlineTiers}>
            <div className={inlineTiers ? '' : 'min-w-[176px]'}>
              <Row icon={<SearchCheck className={ICO} />} onClick={() => run(onCheck)} meter>
                Check this…
              </Row>
              {/* The open question — the third distinct act (see the prop
                  doc): seeds the selection reference and flips to Chat. */}
              <Row icon={<MessageSquare className={ICO} />} onClick={() => run(onAsk)} meter>
                Ask about this…
              </Row>
            </div>
          </Flyout>
          </div>
          {SEP}
          <div className="px-2 pb-[3px] pt-[6px] text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
            This block
          </div>
          <Row icon={<Link2 className={ICO} />} onClick={() => run(onCopyLink)}>
            Copy link to block
          </Row>
          <Row icon={<History className={ICO} />} onClick={() => run(onHistory)}>
            History
          </Row>
        </>
      )}
    </div>
  );
}
