'use client';

/**
 * SelectionGesture — the judged act, at the selection (ADR-612 D1).
 *
 * ONE affordance for the metered act, identical in every app. It appears when
 * a selection settles, sits beside the selection, and leaves when the
 * selection clears. Text mounts it today; Slides adopts this component rather
 * than re-inventing it (ADR-612 §6).
 *
 * ## Why it anchors to the SELECTION and never to the pointer
 *
 * lane-frame §6 refuses pointer/mouse telemetry. That refusal is about the
 * pointer as a FOCUS SIGNAL — inferring what the member cares about from where
 * the cursor sits, and sending that up the wire. This component sends nothing:
 * the coordinates are a rendering input, computed in the browser, and what
 * eventually crosses the wire is the selection the member deliberately made
 * (ADR-609's anchor).
 *
 * The anchor choice is what keeps that true, and it is not a detail. A
 * selection has a rect on touch, where a pointer has no position at all — so
 * anchoring to the cursor would be dead on touch and jittery on mouse, the
 * exact two failure modes the refusal names. Anchoring to the selection is
 * immune to both.
 *
 * ## Where it sits, and why not simply "at the end"
 *
 * The first cut anchored to the selection's END POINT. Driven, that reads
 * wrong: a multi-line selection ends at the LAST line's x — often far left and
 * mid-paragraph — so the door landed on top of the prose below the selection,
 * covering the very text the member was reading. It also sat inside the
 * reading column, which is where the eye is.
 *
 * It now hangs in the MARGIN beside the selection, vertically at the
 * selection's end, and only falls back to below-the-end when there is no
 * margin to hang in (a narrow viewport). The selection is highlighted; the
 * door does not need to point at it, it needs to not cover it.
 *
 * It renders and REPORTS. The mount owns what the gesture means.
 */

import { useMemo } from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

/** The selection's box in viewport coordinates, plus its END line — what the
 *  canvas reports (`EditorView.coordsAtPos` over both ends). */
export interface SelectionAnchor {
  left: number;
  right: number;
  top: number;
  bottom: number;
  endLeft: number;
  endTop: number;
  endBottom: number;
}

/** Width reserved for the door when deciding whether the margin fits it. */
const DOOR_W = 108;
const DOOR_H = 34;
const GAP = 8;

export function SelectionGesture({
  anchor,
  label,
  onClick,
  pending = false,
  className,
}: {
  /** Null while nothing is selected — the act has no subject, so no door. */
  anchor: SelectionAnchor | null;
  /** What the member will act on, in their words. The SAME noun the composer
   *  chip shows after the click (ADR-612 D2: the chip names the grain, and
   *  whatever it names is what gets anchored). */
  label: string;
  onClick: () => void;
  /** A turn is in flight for this selection. The door STAYS — vanishing at the
   *  moment of the click is what made the act feel like it went nowhere — and
   *  says it is working (ADR-612 D4). */
  pending?: boolean;
  className?: string;
}) {
  const style = useMemo(() => {
    if (!anchor) return undefined;
    if (typeof window === 'undefined') return { left: anchor.right + GAP, top: anchor.endTop };

    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Vertically: level with the selection's END, clamped into the viewport so
    // a selection running off-screen still shows its door.
    const top = Math.max(GAP, Math.min(anchor.endTop, vh - DOOR_H - GAP));

    // Preferred: the right margin, clear of the reading column.
    if (anchor.right + GAP + DOOR_W < vw) {
      return { left: anchor.right + GAP, top };
    }
    // Then the left margin.
    if (anchor.left - GAP - DOOR_W > 0) {
      return { left: anchor.left - GAP - DOOR_W, top };
    }
    // No margin (narrow viewport): fall back to below the selection's end,
    // clamped — it covers prose, but an unreachable door is worse.
    const below = anchor.endBottom + GAP;
    const flip = below + DOOR_H > vh;
    return {
      left: Math.min(Math.max(anchor.endLeft, GAP), vw - DOOR_W - GAP),
      ...(flip
        ? { bottom: `calc(100vh - ${anchor.endTop}px + ${GAP}px)` }
        : { top: below }),
    };
  }, [anchor]);

  if (!anchor) return null;

  return (
    <button
      type="button"
      // The pointer must not reach the canvas: a mousedown here would collapse
      // the very selection this acts on, so the door would dismiss itself.
      onMouseDown={(e) => e.preventDefault()}
      onClick={pending ? undefined : onClick}
      disabled={pending}
      style={style}
      title={
        pending
          ? `Rewriting ${label}…`
          : `Rewrite ${label} — opens the chat with it as the target`
      }
      aria-label={pending ? `Rewriting ${label}` : `Rewrite ${label}`}
      aria-busy={pending || undefined}
      className={cn(
        'fixed z-50 inline-flex items-center gap-1.5 rounded-md border border-border',
        'bg-popover px-2.5 py-1.5 text-xs font-medium text-foreground shadow-md',
        pending ? 'cursor-default opacity-90' : 'hover:bg-muted',
        className,
      )}
    >
      {pending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Sparkles className="h-3.5 w-3.5" />
      )}
      {pending ? 'Rewriting…' : 'Rewrite'}
    </button>
  );
}
