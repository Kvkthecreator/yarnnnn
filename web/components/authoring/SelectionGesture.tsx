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
 * ## What "the margin" is measured AGAINST (2026-08-27, driven)
 *
 * The rule above was right and its measurement was wrong. The first
 * implementation asked whether the door fits between the selection's right
 * edge and the VIEWPORT edge — which is true almost always, because a viewport
 * is much wider than a reading column. So for a SHORT, MID-LINE selection (the
 * commonest case: "rewrite these three words") the door was placed at
 * `selection.right + gap` — squarely on the rest of the sentence.
 *
 * Driven in production it covered "italic and code." in Text and the word
 * "thesis" in Slides. Same defect as the one this section already records,
 * rotated 90°: the earlier fix corrected the selection's BOX, this one corrects
 * what the box is compared against.
 *
 * The margin is the space outside the CONTENT — the reading column in Text, the
 * slide's rendered box in Slides — so the caller passes `contentLeft` /
 * `contentRight`. Without them the door has no way to tell a margin from the
 * middle of a paragraph, and it must not guess: absent bounds it goes BELOW the
 * selection rather than beside it, which covers a line the member is not
 * reading instead of the one they are.
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
  /** The CONTENT's horizontal bounds in viewport coordinates — the reading
   *  column (Text) or the rendered slide (Slides). The margin is measured
   *  against THESE, never against the viewport: a viewport is far wider than a
   *  column, so "it fits before the window edge" is true even when the space
   *  is the rest of the member's own sentence. Omitted → no margin is claimed
   *  and the door goes below the selection (see the header note). */
  contentLeft?: number;
  contentRight?: number;
  /** ADR-616 D4 — the HOUSING's horizontal bounds: the canvas column the
   *  artifact is rendered in, in viewport coordinates. `contentLeft/Right` say
   *  where the artifact ends; these say where the space to hang in ends. With
   *  a Properties pane open, the room to the right of a letterboxed deck stage
   *  belongs to the PANE, and the door is `position: fixed` so nothing clips
   *  it — measuring the fit against `window.innerWidth` put it on top of the
   *  pane. This is the outer half of the defect `5abdce9` fixed on the inside
   *  (it taught the runtime to report the content box, because measuring
   *  against the IFRAME put the door past the canvas for the same reason).
   *  Omitted → the viewport, exactly as before. */
  hostLeft?: number;
  hostRight?: number;
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

    // The room available is the HOUSING's, not the window's (D4).
    const vw = typeof anchor.hostRight === 'number' ? anchor.hostRight : window.innerWidth;
    const vLeft = typeof anchor.hostLeft === 'number' ? anchor.hostLeft : 0;
    const vh = window.innerHeight;

    // Vertically: level with the selection's END, clamped into the viewport so
    // a selection running off-screen still shows its door.
    const top = Math.max(GAP, Math.min(anchor.endTop, vh - DOOR_H - GAP));

    // The margin is OUTSIDE the content, not merely inside the window. A door
    // that clears the viewport edge can still sit on the rest of the sentence
    // — that was the defect (see the header note), and the content bounds are
    // what tell the two apart. No bounds → claim no margin.
    const cRight = anchor.contentRight;
    const cLeft = anchor.contentLeft;
    const haveBounds = typeof cRight === 'number' && typeof cLeft === 'number';

    if (haveBounds) {
      // Preferred: the right margin — beyond where the content ends, and only
      // if the window still has room for the door there.
      const right = Math.max(anchor.right, cRight as number) + GAP;
      if (right + DOOR_W < vw) return { left: right, top };
      // Then the left margin, on the far side of the content.
      const left = Math.min(anchor.left, cLeft as number) - GAP - DOOR_W;
      if (left > vLeft) return { left, top };
    }
    // No margin to hang in (a narrow viewport, or a caller that declared no
    // content bounds): fall back to below the selection's end, clamped. That
    // covers a line, but it is a line BELOW what the member is reading rather
    // than the remainder of their own sentence — and an unreachable door is
    // worse than either.
    const below = anchor.endBottom + GAP;
    const flip = below + DOOR_H > vh;
    return {
      left: Math.min(Math.max(anchor.endLeft, vLeft + GAP), vw - DOOR_W - GAP),
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
