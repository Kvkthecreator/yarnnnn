'use client';

/**
 * SelectionGesture — the judged act, at the selection (ADR-612 D1).
 *
 * ONE affordance for the metered act, identical in every app. It appears when
 * a selection settles, sits at the selection's end, and leaves when the
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
 * anchoring to the cursor would have been dead on touch and jittery on mouse,
 * the exact two failure modes the refusal names. Anchoring to the selection is
 * immune to both.
 *
 * It renders and REPORTS. The mount owns what the gesture means.
 */

import { useMemo } from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Where the selection ends, in viewport coordinates — what the canvas
 *  reports (`EditorView.coordsAtPos` for prose; a DOMRect elsewhere). */
export interface SelectionAnchor {
  left: number;
  top: number;
  bottom: number;
}

export function SelectionGesture({
  anchor,
  label,
  onClick,
  className,
}: {
  /** Null while nothing is selected — the act has no subject, so no door. */
  anchor: SelectionAnchor | null;
  /** What the member will act on, in their words. The SAME noun the composer
   *  chip shows after the click (ADR-612 D2: the chip names the grain, and
   *  whatever it names is what gets anchored). */
  label: string;
  onClick: () => void;
  className?: string;
}) {
  // Flip above the selection when there is no room below, and clamp to the
  // viewport's left edge — the SlashMenu precedent. A door that opens
  // off-screen is a door the member cannot use.
  const style = useMemo(() => {
    if (!anchor) return undefined;
    const H = 44;
    const below =
      typeof window !== 'undefined' ? window.innerHeight - anchor.bottom : H;
    const flip = below < H && anchor.top > below;
    const left =
      typeof window !== 'undefined'
        ? Math.min(Math.max(anchor.left, 8), window.innerWidth - 140)
        : anchor.left;
    return flip
      ? { left, bottom: `calc(100vh - ${anchor.top}px + 6px)` }
      : { left, top: anchor.bottom + 6 };
  }, [anchor]);

  if (!anchor) return null;

  return (
    <button
      type="button"
      // The pointer must not reach the canvas: a mousedown here would collapse
      // the very selection this acts on, so the door would dismiss itself.
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      style={style}
      title={`Rewrite ${label} — opens the chat with it as the target`}
      aria-label={`Rewrite ${label}`}
      className={cn(
        'fixed z-50 inline-flex items-center gap-1.5 rounded-md border border-border',
        'bg-popover px-2.5 py-1.5 text-xs font-medium text-foreground shadow-md',
        'hover:bg-muted',
        className,
      )}
    >
      <Sparkles className="h-3.5 w-3.5" />
      Rewrite
    </button>
  );
}
