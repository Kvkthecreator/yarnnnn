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

import { useEffect, useState } from 'react';
import {
  Copy, ClipboardPaste, CopyPlus, Trash2, Type,
  ArrowUp, ArrowDown, ChevronsUp, ChevronsDown, ChevronRight, Sparkles, SearchCheck, Link2, History,
} from 'lucide-react';
import type { StudioContextTarget } from './StudioCanvas';
import { TURN_INTO_KINDS } from './StudioDesignTab';

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
   *  and insertion fragment from it, so the menu never restates the registry. */
  blocks?: Array<{ kind: string; label: string; fragment: string }>;
  /** Move the block one position earlier in its flow — document order, and it
   *  says so. */
  onMoveUp: () => void;
  onMoveDown: () => void;
  /** ADR-471 D-d: z earned its token, so Bring forward/backward are finally
   *  honest verbs — stacking order among POSITIONED blocks (target.positioned
   *  gates the rows; nudgeZ backstops the op side). */
  onBringForward: () => void;
  onBringBackward: () => void;
  /** Metered (D6): both SEED the composer and send nothing. */
  onRewrite: () => void;
  onCheck: () => void;
  /** The two rows no reference can ship (D3) — a block has an address, and the
   *  revision chain joins by that same id. */
  onCopyLink: () => void;
  onHistory: () => void;
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
  onTurnInto, blocks, onMoveUp, onMoveDown, onBringForward, onBringBackward, onRewrite, onCheck,
  onCopyLink, onHistory, mode, hasClipboard,
}: StudioBlockMenuProps) {
  const [turnOpen, setTurnOpen] = useState(false);
  // Dismissal. NOTE the parent-window blind spot: the Studio canvas is a
  // SANDBOXED IFRAME, so a click on the artifact fires in the frame's own
  // document and these parent listeners never hear it. The canvas's point
  // message closes the menu for that case (StudioSurface.onPoint) — these
  // cover the parent chrome (rails, panels, toolbar) plus Escape, a second
  // right-click elsewhere, and any scroll (a menu anchored to a point is a lie
  // once the point moves).
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('click', close);
    window.addEventListener('contextmenu', close);
    window.addEventListener('resize', close);
    window.addEventListener('scroll', close, true); // capture: any scroller
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('click', close);
      window.removeEventListener('contextmenu', close);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  const run = (fn: () => void) => { fn(); onClose(); };
  const hasBlock = !!target.blockId;
  // ADR-482 D5: `paged` is the affirmative test — an unresolved mode withholds
  // enclosure-shaped rows rather than guessing them on (the D3 principle).
  const isPaged = mode === 'paged';

  // The legal conversions for THIS block (ADR-456 W2 + ADR-479 D5): a text kind
  // that isn't already what it is, and never a citation — `convertBlock`
  // refuses a block carrying data-ref (flattening would bake a live reference
  // into prose), so offering it would be a row the op declines.
  const turnIntoKinds =
    hasBlock && target.blockKind && !target.dataRef
      && TURN_INTO_KINDS.includes(target.blockKind)
      ? TURN_INTO_KINDS
          .filter((k) => k !== target.blockKind)
          .map((k) => (blocks ?? []).find((b) => b.kind === k))
          .filter((b): b is { kind: string; label: string; fragment: string } => !!b)
      : [];

  // The canvas is an iframe: its coordinates are frame-local. The caller passes
  // them already mapped to the page.
  const left = typeof window !== 'undefined' ? Math.min(target.x, window.innerWidth - 250) : target.x;
  const top = typeof window !== 'undefined' ? Math.min(target.y, window.innerHeight - 330) : target.y;

  // ADR-482 D9: no block and nothing to paste = no menu. Every row is gated, so
  // this state would otherwise paint an empty bordered box — chrome that
  // appears, says nothing, and must be dismissed. A menu with no acts is not a
  // menu; the right-click simply does nothing, which is the honest answer.
  if (!hasBlock && !hasClipboard) return null;

  return (
    <div
      className="fixed z-50 min-w-[228px] rounded-md border border-border bg-popover py-1 shadow-md"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
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
          {SEP}
          <Row icon={<CopyPlus className={ICO} />} onClick={() => run(onDuplicate)} shortcut="⌘D">
            Duplicate
          </Row>
          <Row icon={<Trash2 className={ICO} />} onClick={() => run(onDelete)} shortcut="⌫">
            Delete
          </Row>
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
                      key={b.kind}
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
