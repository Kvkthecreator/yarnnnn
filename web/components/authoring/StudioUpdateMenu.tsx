'use client';

/**
 * StudioUpdateMenu — THE update door (ADR-589).
 *
 * The mirror of StudioBlockInsertMenu, re-interpreted for the question Update
 * actually asks. Add's rail partitions the CATALOG ("what kind of thing do I
 * want"); Update's rail is the SELECTION LADDER ("which of the nested things
 * under my cursor am I shaping"), because for Update the target is the hard
 * part and the act set is determined once the target is known.
 *
 * Two panes, same geometry as Add: rail left, that rung's acts right. Picking a
 * rung RE-TARGETS the selection (D1) — which is how `document` stays reachable
 * with a block selected.
 *
 * The ladder is never subset (D2): every rung renders every time, and a rung
 * that cannot be entered right now is GREYED WITH ITS REASON rather than
 * hidden. `document` is therefore always the top rung — the fix for the door
 * that used to open on a slide gallery and give the artifact's own typography,
 * palette and design system no entrance at all (D3).
 *
 * A set adds NO rung (D4, inherited from ADR-519 D4.1 — the set is STATE, not a
 * scope); it shows as the withdrawal sentence over the acts.
 *
 * It renders and REPORTS. Every act calls the op the Properties pane already
 * calls — a second entrance, never a second write path (ADR-462 D1), and the
 * pane stays the dwell that carries the full set (D5).
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { LayoutTemplate, Sparkles, Type, SlidersHorizontal, Palette } from 'lucide-react';
import { ArrangementThumb } from './ArrangementThumb';
import { buildLadder, initialRung, type LadderAncestor, type LadderRung } from './updateLadder';
import type { PaneScope } from './selection';
import {
  arrangementCarryNote,
  type StudioArrangement,
  type StudioSelection,
} from './StudioToolbar';

export interface StudioUpdateMenuProps {
  /** Anchor point (the toolbar button's rect). */
  x: number;
  y: number;
  selection: StudioSelection | null;
  /** `scopeOf(...)` for the current selection — read, never re-derived. */
  scope: PaneScope;
  ancestors: LadderAncestor[];
  mode: 'flow' | 'paged';
  pageNoun: string;
  artifactLabel: string;
  setCount: number;
  /** The page-grain gallery (re-arrange), unchanged from the old door. */
  arrangements: StudioArrangement[];
  currentArrange: string | null;
  carriedCount: number | null;
  groupCount: number | null;
  onApplyArrangement: (a: StudioArrangement) => void;
  /** Re-target: the member picked a rung that is not the current selection. */
  onRetarget: (rung: LadderRung) => void;
  /** Open the block-acts menu for the selected block (the object rung's acts
   *  are ALREADY one menu — this door routes to it rather than restating it). */
  onBlockActs: (at: { x: number; y: number }) => void;
  /** Flip the Properties pane open at this scope — the dwell (D5). */
  onOpenPane: (scope: PaneScope) => void;
  onClose: () => void;
}

const ROW =
  'flex w-full items-center gap-2 rounded px-2 py-[5px] text-left text-[12.5px] hover:bg-accent';
const ICO = 'h-3.5 w-3.5';

export function StudioUpdateMenu({
  x, y, selection, scope, ancestors, mode, pageNoun, artifactLabel, setCount,
  arrangements, currentArrange, carriedCount, groupCount,
  onApplyArrangement, onRetarget, onBlockActs, onOpenPane, onClose,
}: StudioUpdateMenuProps) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [clamped, setClamped] = useState<{ left: number; top: number } | null>(null);
  // D5's narrow housing, measured once per open (the ADR-586 D5 fork, same
  // rule: the door closes on resize, so the measure cannot go stale).
  const [sheet] = useState<boolean>(
    () => typeof window !== 'undefined' && window.innerWidth < 640,
  );

  const rungs = buildLadder({
    selection, scope, ancestors, mode, pageNoun, artifactLabel, setCount,
  });
  const [active, setActive] = useState<string | null>(null);
  const activeKey = active ?? initialRung(rungs)?.key ?? rungs[0]?.key ?? null;
  const activeRung = rungs.find((r) => r.key === activeKey) ?? null;

  useLayoutEffect(() => {
    if (sheet) return;
    const el = boxRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8;
    setClamped({
      left: Math.max(MARGIN, Math.min(x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(y, window.innerHeight - height - MARGIN)),
    });
  }, [x, y, activeKey, sheet]);

  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    // The canvas is an opaque-origin iframe: a click or Escape inside it never
    // reaches these listeners. The runtime bridges both out (ADR-586 D4's
    // dismissal contract, shared with the insert door).
    const onFrame = (e: MessageEvent) => {
      const t = (e.data as { type?: string } | null)?.type;
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

  const pick = (r: LadderRung) => {
    if (r.reason) return; // greyed: stated, not clickable (D2)
    setActive(r.key);
    if (!r.current) onRetarget(r);
  };

  const railEl = (
    <div
      className={
        sheet
          ? 'flex shrink-0 gap-1 overflow-x-auto border-b border-border/60 p-1'
          : 'w-[124px] shrink-0 overflow-y-auto border-r border-border/60 p-1'
      }
    >
      {rungs.map((r) => {
        const on = r.key === activeKey;
        return (
          <button
            key={r.key}
            type="button"
            onClick={() => pick(r)}
            title={r.reason ?? `Shape the ${r.label}`}
            aria-disabled={!!r.reason}
            className={`${sheet ? 'shrink-0 whitespace-nowrap' : 'w-full'} rounded px-2 py-[5px] text-left text-[12.5px] ${
              r.reason
                ? 'cursor-default text-muted-foreground/45'
                : on
                  ? 'bg-accent font-medium'
                  : 'hover:bg-accent'
            }`}
          >
            <span className="truncate">{r.label}</span>
          </button>
        );
      })}
    </div>
  );

  /** The acts for the active rung. Each routes to the op that already exists —
   *  the door is an entrance (D5). */
  const acts = (() => {
    if (!activeRung) return null;
    const openDwell = (s: PaneScope) => () => { onOpenPane(s); onClose(); };

    if (activeRung.scope === 'page' && !activeRung.reason) {
      return (
        <div className="p-1">
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Change this {pageNoun} to
          </p>
          <div className="grid grid-cols-2 gap-1.5 p-0.5">
            {arrangements.map((a) => {
              const note = arrangementCarryNote(a, carriedCount, pageNoun, groupCount);
              const current = currentArrange === a.slug;
              return (
                <button
                  key={a.slug}
                  type="button"
                  title={
                    note
                      ? `${a.description} — this ${pageNoun}'s content moves to a new content ${pageNoun} after it.`
                      : a.description
                  }
                  onClick={() => { onApplyArrangement(a); onClose(); }}
                  className={`flex flex-col gap-1 rounded-md border p-1.5 text-left hover:bg-muted/20 ${
                    current ? 'border-indigo-400' : 'border-transparent hover:border-border'
                  }`}
                >
                  <ArrangementThumb areas={a.areas} fragment={a.fragment} />
                  <span className="truncate text-[11px]">{a.label}</span>
                  {note && (
                    <span className="truncate text-[9px] leading-tight text-amber-600 dark:text-amber-500">
                      {note}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <button type="button" className={ROW} onClick={openDwell('page')}>
            <span className="text-muted-foreground"><SlidersHorizontal className={ICO} /></span>
            <span className="truncate">Layout &amp; background…</span>
          </button>
        </div>
      );
    }

    if (activeRung.scope === 'document') {
      return (
        <div className="p-1">
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            This artifact
          </p>
          <button type="button" className={ROW} onClick={openDwell('document')}>
            <span className="text-muted-foreground"><Type className={ICO} /></span>
            <span className="truncate">Typography…</span>
          </button>
          <button type="button" className={ROW} onClick={openDwell('document')}>
            <span className="text-muted-foreground"><Palette className={ICO} /></span>
            <span className="truncate">Palette &amp; design system…</span>
          </button>
        </div>
      );
    }

    if (activeRung.scope === 'object' && !activeRung.reason) {
      return (
        <div className="p-1">
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {activeRung.label}
          </p>
          {setCount > 1 && (
            <p className="px-2 py-[5px] text-[10px] leading-snug text-muted-foreground">
              Identity, position, layout and style apply to one object at a time
              ({setCount} selected).
            </p>
          )}
          {/* The object rung's acts ARE the block-acts menu — one definition,
              two mounts (ADR-586 D6). Restating them here would be the second
              write path ADR-462 D1 forbids. */}
          <button
            type="button"
            className={ROW}
            onClick={(e) => {
              const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
              onClose();
              onBlockActs({ x: r.left, y: r.bottom + 4 });
            }}
          >
            <span className="text-muted-foreground"><Sparkles className={ICO} /></span>
            <span className="truncate">Move, turn into, rewrite…</span>
          </button>
          <button type="button" className={ROW} onClick={openDwell('object')}>
            <span className="text-muted-foreground"><SlidersHorizontal className={ICO} /></span>
            <span className="truncate">Align, position &amp; style…</span>
          </button>
        </div>
      );
    }

    if (activeRung.scope === 'container' && !activeRung.reason) {
      return (
        <div className="p-1">
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {activeRung.label}
          </p>
          <button type="button" className={ROW} onClick={openDwell('container')}>
            <span className="text-muted-foreground"><LayoutTemplate className={ICO} /></span>
            <span className="truncate">Layout &amp; measures…</span>
          </button>
        </div>
      );
    }

    if (activeRung.scope === 'range' && !activeRung.reason) {
      return (
        <div className="p-1">
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Text selection
          </p>
          <button type="button" className={ROW} onClick={openDwell('range')}>
            <span className="text-muted-foreground"><Type className={ICO} /></span>
            <span className="truncate">Marks &amp; turn into…</span>
          </button>
        </div>
      );
    }

    // A greyed rung is still SELECTABLE as a reading: it says why it is empty.
    return (
      <p className="p-3 text-[11.5px] leading-snug text-muted-foreground">
        {activeRung.reason}
      </p>
    );
  })();

  return (
    <div
      ref={boxRef}
      className={
        sheet
          ? 'fixed inset-x-0 bottom-0 z-50 flex max-h-[70vh] flex-col rounded-t-lg border-t border-border bg-popover shadow-lg'
          : 'fixed z-50 flex max-h-[min(26rem,calc(100vh-16px))] w-[24rem] flex-col rounded-md border border-border bg-popover shadow-md'
      }
      style={sheet ? undefined : { left: clamped?.left ?? x, top: clamped?.top ?? y }}
      onMouseDown={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* The target is NAMED, exactly as the insert door names its landing. */}
      <p className="shrink-0 border-b border-border/60 px-2.5 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
        Update — {activeRung?.label ?? 'this artifact'}
      </p>
      <div className={`flex min-h-0 flex-1 ${sheet ? 'flex-col' : ''}`}>
        {railEl}
        <div className="min-w-0 flex-1 overflow-y-auto">{acts}</div>
      </div>
    </div>
  );
}
