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
  ArrowUp, ArrowDown, ChevronsUp, ChevronsDown, ChevronRight, MessageSquare, Sparkles, SearchCheck, Link2, History,
} from 'lucide-react';
import type { StudioContextTarget } from './StudioCanvas';
import { isConvertible, turnIntoTargets } from './StudioDesignTab';
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
  /** The served block vocabulary — the submenu resolves each legal kind's label
   *  and insertion fragment from it, so the menu never restates the registry.
   *  ADR-539 D2: rows carry `convertible`; the menu reads it off the row. */
  blocks?: Array<{ kind: string; label: string; fragment: string; convertible?: boolean }>;
  /** ADR-539 D3 — the served rung set (falls back to the runtime's pinned copy). */
  headingRungs?: number[];
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
  /** Open the native block-insert menu at this right-click point — the LOCATED
   *  half of the paged mouse insert route. Absent on flow (the caret answers
   *  there), so the row simply does not render. */
  onInsert?: () => void;
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

const SEP = <div className="my-1 h-px bg-border" />;
const ICO = 'h-3.5 w-3.5';

export function StudioBlockMenu({
  target, onClose, onCopy, onPaste, onDuplicate, onDelete,
  onTurnInto, blocks, headingRungs, onMoveUp, onMoveDown, onBringForward, onBringBackward, onRewrite, onCheck, onAsk,
  onCopyLink, onHistory, onInsert, mode, hasClipboard,
}: StudioBlockMenuProps) {
  const [turnOpen, setTurnOpen] = useState(false);
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
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8; // never flush against the edge
    setClamped({
      left: Math.max(MARGIN, Math.min(target.x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(target.y, window.innerHeight - height - MARGIN)),
    });
  }, [target.x, target.y, turnOpen, turnIntoKinds.length]);

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
  const hasInsert = !!onInsert && isPaged;
  if (!hasBlock && !hasClipboard && !hasInsert) return null;

  return (
    <div
      ref={boxRef}
      className="fixed z-50 max-h-[calc(100vh-16px)] min-w-[228px] overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* INSERT leads on `paged`, and only on paged. This is the LOCATED half
          of the mouse insert route that replaced '/' there: the toolbar button
          is discoverable, this is fast and lands at the thing you right-clicked.
          On `flow` the row is absent — the caret IS the insertion point and '/'
          still answers there, so a row here would be a third door to the same
          act on the one medium that never needed it.
          First, because inserting CREATES and every row below acts on something
          that already exists. */}
      {onInsert && isPaged && (
        <>
          <Row icon={<Plus className={ICO} />} onClick={() => run(onInsert)}>
            Insert block…
          </Row>
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
              <Row
                icon={<CopyPlus className={ICO} />}
                onClick={() => run(onDuplicate)}
                shortcut="⌘D"
              >
                Duplicate
              </Row>
              <Row icon={<Trash2 className={ICO} />} onClick={() => run(onDelete)} shortcut="⌫">
                Delete
              </Row>
            </>
          )}
          {SEP}
          {/* ADR-479 D5 — Turn into, in one gesture. Shown only when the
              conversion is LEGAL: a text kind, and never a citation (a figure
              or table wears data-ref on its own root, and flattening it would
              bake a live reference into prose — the op refuses, so the menu
              must not offer). A row that offers what the op will refuse is the
              same class of lie D4 deleted. */}
          {turnIntoKinds.length > 0 && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setTurnOpen((v) => !v)}
                className="flex w-full items-center gap-2 px-2 py-[5px] text-left text-[12.5px] hover:bg-accent"
              >
                <span className="text-muted-foreground"><Type className={ICO} /></span>
                <span className="truncate">Turn into</span>
                <ChevronRight className="ml-auto h-3.5 w-3.5 text-muted-foreground/60" />
              </button>
              {turnOpen && (
                <div className="mt-0.5 border-l-2 border-border/60 pl-1">
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
              )}
            </div>
          )}
        </>
      )}
      {/* Re-arrange is GONE from this menu (ADR-479 D4). Every other row here
          acts on the block you right-clicked; Re-arrange acts on the PAGE
          containing it — a scope violation, and the reason the row was wired to
          `menuOpenDesign` (which only switches tabs). The gallery it pointed at
          was deleted 2026-07-21 as a duplicate of the toolbar's, so the row had
          become a hint nothing listens for (the ADR-477 D10 defect). The
          toolbar's page-scoped button is the one mount. */}
      {/* Move up/down is DOCUMENT order and says so. Bring forward/backward is
          Z-ORDER — the token arrived (ADR-471 D-d: composed visuals made
          blocks overlap on purpose), so the frame-gated rows ADR-462 D3 scored
          are finally honest: they appear only on a POSITIONED block (the
          DOM-side gate travels in the target), and the op writes --yz. */}
      {/* ADR-482 D5: PAGED only. Reordering is an enclosure verb — it moves a
          block past its neighbours in a sequence of them. On flow the member
          edits one continuous surface and moves text by selecting and typing,
          the way every writing tool works; offering "move this block up" there
          asks them to think in a unit ADR-480 D2 dissolved into an annotation.
          The op survives (it is still reachable structurally); the menu simply
          stops advertising it where it does not describe the medium. */}
      {hasBlock && isPaged && (
        <>
          <Row icon={<ArrowUp className={ICO} />} onClick={() => run(onMoveUp)}>
            Move up
          </Row>
          <Row icon={<ArrowDown className={ICO} />} onClick={() => run(onMoveDown)}>
            Move down
          </Row>
        </>
      )}
      {hasBlock && target.positioned && (
        <>
          <Row icon={<ChevronsUp className={ICO} />} onClick={() => run(onBringForward)}>
            Bring forward
          </Row>
          <Row icon={<ChevronsDown className={ICO} />} onClick={() => run(onBringBackward)}>
            Bring backward
          </Row>
        </>
      )}
      {hasBlock && (
        <>
          {SEP}
          <div className="px-2 pb-[3px] pt-[6px] text-[9.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
            Write with AI
          </div>
          {/* D6: BOTH seed the composer and send nothing — the row is a head
              start on a sentence, not a button. Shorter/longer/sharper are
              things the member TYPES, which is why there are two rows and not
              four: `Make shorter` and `Expand this` were rewrites with a
              pre-typed adjective. */}
          <Row icon={<Sparkles className={ICO} />} onClick={() => run(onRewrite)} meter>
            Rewrite…
          </Row>
          <Row icon={<SearchCheck className={ICO} />} onClick={() => run(onCheck)} meter>
            Check this…
          </Row>
          {/* The open question — the third distinct act (see the prop doc):
              seeds the selection reference and flips to Chat. */}
          <Row icon={<MessageSquare className={ICO} />} onClick={() => run(onAsk)} meter>
            Ask about this…
          </Row>
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
