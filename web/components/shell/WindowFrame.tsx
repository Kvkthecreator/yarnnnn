'use client';

/**
 * WindowFrame — ADR-297 D14 + D15.
 *
 * D14 shipped the visible window chrome (32px title bar + close ×).
 * D15 makes the frame a real window-manager window: drag-to-move on
 * the title bar, resize from any edge or corner, raise-on-click,
 * absolute z-stacking.
 *
 * The frame is positionless in single-window (mobile) mode — the
 * parent applies width/height/flex-fill. In multi-window (desktop)
 * mode the parent absolutely-positions us using `style` from
 * windowStates[slug].
 *
 * Title bar shows the surface NAME only. The in-window LOCATOR (the
 * "Agents › Reviewer" position crumb) is NOT rendered here — it moved to
 * the GlobalLocatorStrip (2026-06-26), the one always-visible OS "you are
 * here" indicator, so the locator survives canvas mode where this title
 * bar is suppressed (chromeless, below).
 *
 * ADR-358 (2026-06-23): `chromeless` mode. In CANVAS layout the single
 * full-bleed surface beside chat reads as a canvas pane, not a windowed
 * app — so the title bar (traffic-lights + name) and the window border /
 * rounding are suppressed. The surface body fills the frame edge-to-edge.
 * Used by SurfaceViewport's single-surface branch when layoutMode is
 * canvas; mobile single-surface keeps the frame (ADR-297 D15.2).
 */

import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { X, Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  clampWindowState,
  WINDOW_MIN_WIDTH,
  WINDOW_MIN_HEIGHT,
  type WindowState,
} from '@/lib/shell/surface-preferences';
import { WINDOW_Z_BASE } from '@/lib/shell/z-tiers';

interface WindowFrameProps {
  title: string;
  isForegrounded: boolean;
  /** Click-to-raise dispatcher. Called on any mousedown within the
   *  frame (body, title bar, edges) so the window comes to front. */
  onRaise: () => void;
  onClose: () => void;
  /** D19.1 (2026-05-22): macOS-style traffic-light minimize. Called
   *  by the yellow button. When omitted, the minimize button is
   *  hidden (e.g. single-window/mobile mode). */
  onMinimize?: () => void;
  /** D19.1: macOS-style traffic-light maximize/zoom toggle. Called
   *  by the green button. When omitted, the maximize button is
   *  hidden. */
  onMaximize?: () => void;
  /** D15 multi-window mode: window geometry to apply (absolute
   *  position + width/height). When omitted, the frame fills its
   *  parent (single-window/mobile mode). */
  windowState?: WindowState;
  /** D15: viewport size for clamping during drag/resize. */
  viewportWidth?: number;
  viewportHeight?: number;
  /** D15: emits geometry updates from drag + resize. */
  onWindowStateChange?: (state: WindowState) => void;
  /** D15: whether drag/resize affordances are active. Disabled in
   *  single-window/mobile mode. */
  interactive?: boolean;
  /** ADR-358: canvas-mode full-bleed. Suppresses the title bar +
   *  border/rounding so the surface reads as a canvas pane, not a
   *  windowed app. Implies non-interactive (no chrome to drag). */
  chromeless?: boolean;
  children: React.ReactNode;
}

type DragMode =
  | 'move'
  | 'resize-n'
  | 'resize-s'
  | 'resize-e'
  | 'resize-w'
  | 'resize-ne'
  | 'resize-nw'
  | 'resize-se'
  | 'resize-sw';

interface DragSession {
  mode: DragMode;
  startX: number;
  startY: number;
  origin: WindowState;
}

const VIEWPORT_PADDING_FOR_CLAMP = 16;

export function WindowFrame({
  title,
  isForegrounded,
  onRaise,
  onClose,
  onMinimize,
  onMaximize,
  windowState,
  viewportWidth,
  viewportHeight,
  onWindowStateChange,
  interactive = false,
  chromeless = false,
  children,
}: WindowFrameProps) {
  const dragRef = useRef<DragSession | null>(null);
  // D19.1: traffic-light hover state — when the operator hovers the
  // cluster, even background windows light up so they can target the
  // buttons without raising first (matches macOS).
  const [trafficHovered, setTrafficHovered] = useState(false);

  // Compute style for multi-window (absolute) vs single-window (fill).
  const frameStyle: CSSProperties = windowState && interactive
    ? {
        position: 'absolute',
        top: windowState.y,
        left: windowState.x,
        width: windowState.width,
        height: windowState.height,
        zIndex: WINDOW_Z_BASE + windowState.z, // D18 z-tier baseline; capped via WINDOW_Z_MAX
      }
    : {};

  // Drag/resize handler chain — installed on document during a session
  // and torn down on mouseup, so it captures even if the cursor moves
  // outside the frame.
  useEffect(() => {
    if (!interactive) return;

    const onMouseMove = (e: MouseEvent) => {
      const sess = dragRef.current;
      if (!sess || !windowState || !onWindowStateChange) return;
      const dx = e.clientX - sess.startX;
      const dy = e.clientY - sess.startY;
      const o = sess.origin;
      let next: WindowState = { ...o };

      switch (sess.mode) {
        case 'move':
          next = { ...o, x: o.x + dx, y: o.y + dy };
          break;
        case 'resize-n':
          next = { ...o, y: o.y + dy, height: o.height - dy };
          break;
        case 'resize-s':
          next = { ...o, height: o.height + dy };
          break;
        case 'resize-e':
          next = { ...o, width: o.width + dx };
          break;
        case 'resize-w':
          next = { ...o, x: o.x + dx, width: o.width - dx };
          break;
        case 'resize-ne':
          next = { ...o, y: o.y + dy, width: o.width + dx, height: o.height - dy };
          break;
        case 'resize-nw':
          next = { ...o, x: o.x + dx, y: o.y + dy, width: o.width - dx, height: o.height - dy };
          break;
        case 'resize-se':
          next = { ...o, width: o.width + dx, height: o.height + dy };
          break;
        case 'resize-sw':
          next = { ...o, x: o.x + dx, width: o.width - dx, height: o.height + dy };
          break;
      }

      // Enforce min dimensions BEFORE clamping (so a resize that would
      // shrink past min just locks at min, anchored opposite edge).
      if (next.width < WINDOW_MIN_WIDTH) {
        const diff = WINDOW_MIN_WIDTH - next.width;
        next.width = WINDOW_MIN_WIDTH;
        if (sess.mode.includes('w')) next.x -= diff;
      }
      if (next.height < WINDOW_MIN_HEIGHT) {
        const diff = WINDOW_MIN_HEIGHT - next.height;
        next.height = WINDOW_MIN_HEIGHT;
        if (sess.mode.includes('n')) next.y -= diff;
      }

      if (viewportWidth && viewportHeight) {
        next = clampWindowState(
          next,
          viewportWidth,
          viewportHeight,
          VIEWPORT_PADDING_FOR_CLAMP
        );
      }

      onWindowStateChange(next);
    };

    const onMouseUp = () => {
      dragRef.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [interactive, windowState, viewportWidth, viewportHeight, onWindowStateChange]);

  const startDrag = useCallback(
    (mode: DragMode, e: React.MouseEvent) => {
      if (!interactive || !windowState) return;
      e.preventDefault();
      e.stopPropagation();
      dragRef.current = {
        mode,
        startX: e.clientX,
        startY: e.clientY,
        origin: windowState,
      };
      // Raise on drag-start.
      onRaise();
      document.body.style.cursor =
        mode === 'move'
          ? 'grabbing'
          : mode === 'resize-n' || mode === 'resize-s'
          ? 'ns-resize'
          : mode === 'resize-e' || mode === 'resize-w'
          ? 'ew-resize'
          : mode === 'resize-ne' || mode === 'resize-sw'
          ? 'nesw-resize'
          : 'nwse-resize';
      document.body.style.userSelect = 'none';
    },
    [interactive, windowState, onRaise]
  );

  // Click-anywhere-to-raise (D15 §4, robustness fix D18.2 2026-05-22).
  // Use mousedown in the CAPTURE phase so the raise fires before any
  // descendant `onMouseDown` handler can `stopPropagation()` or
  // `preventDefault()` and swallow the event. The bubbling-phase
  // `onMouseDown` listener (pre-D18.2) was empirically unreliable
  // against scrollable inner content + nested buttons — operator-
  // observed (KVK 2026-05-22): "I can only grab the title bar; body
  // clicks don't raise the window." Capture-phase fires unconditionally
  // on every mousedown within the frame; matches macOS behavior
  // (clicking anywhere in a background window raises it).
  const handleFrameMouseDownCapture = useCallback(() => {
    if (!isForegrounded) onRaise();
  }, [isForegrounded, onRaise]);

  return (
    <div
      onMouseDownCapture={handleFrameMouseDownCapture}
      style={frameStyle}
      className={cn(
        'flex flex-col overflow-hidden bg-background transition-shadow',
        // ADR-358 chromeless (canvas): no border, rounding, or shadow —
        // the surface fills its container as a flat pane.
        !chromeless && 'rounded-lg border shadow-sm',
        // Single-window mode: fill the parent.
        !interactive && 'h-full w-full',
        chromeless
          ? 'border-transparent'
          : isForegrounded
            ? 'border-border shadow-md'
            : 'border-border/60'
      )}
    >
      {/* Title bar — drag handle in multi-window mode. D19.1: macOS-
          shaped chrome. Traffic-lights (close/minimize/maximize) on the
          LEFT, title centered. Background windows dim the title text;
          traffic-lights turn neutral gray unless hovered or the window
          is foregrounded. ADR-358: suppressed entirely in chromeless
          (canvas) mode. */}
      {!chromeless && (
      <div
        onMouseDown={(e) => {
          // Only initiate drag when clicking the bar itself, not the
          // traffic-light buttons (each button stops propagation).
          if ((e.target as HTMLElement).closest('button')) return;
          startDrag('move', e);
        }}
        className={cn(
          'relative flex h-8 shrink-0 items-center border-b border-border bg-muted/30 px-3',
          interactive && 'cursor-grab active:cursor-grabbing select-none'
        )}
      >
        {/* Traffic-lights cluster (LEFT). Each button is 12px circle;
            cluster total ~46px wide including gaps. Stop both mousedown
            and click propagation so the cluster doesn't initiate drag. */}
        <div
          onMouseEnter={() => setTrafficHovered(true)}
          onMouseLeave={() => setTrafficHovered(false)}
          className="flex shrink-0 items-center gap-1.5"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <TrafficLightButton
            tone="close"
            isForegrounded={isForegrounded}
            isClusterHovered={trafficHovered}
            label={`Close ${title}`}
            onClick={onClose}
            glyph={<X className="h-2 w-2 text-black/70" strokeWidth={2.5} />}
          />
          {onMinimize && (
            <TrafficLightButton
              tone="minimize"
              isForegrounded={isForegrounded}
              isClusterHovered={trafficHovered}
              label={`Minimize ${title}`}
              onClick={onMinimize}
              glyph={<Minus className="h-2 w-2 text-black/70" strokeWidth={2.5} />}
            />
          )}
          {onMaximize && (
            <TrafficLightButton
              tone="maximize"
              isForegrounded={isForegrounded}
              isClusterHovered={trafficHovered}
              label={`Zoom ${title}`}
              onClick={onMaximize}
              glyph={<Plus className="h-2 w-2 text-black/70" strokeWidth={2.5} />}
            />
          )}
        </div>

        {/* Centered surface title — absolutely positioned so traffic-
            lights don't shift it. macOS-shaped; dims on background windows.
            The in-window LOCATOR (the "Agents › Reviewer" position) is no
            longer rendered here — it moved to the GlobalLocatorStrip (the
            one always-visible OS "you are here" indicator, 2026-06-26), so
            the locator survives canvas mode where this title bar is
            suppressed (chromeless, ADR-358). */}
        <div
          className={cn(
            'absolute inset-x-0 flex items-center justify-center gap-1 px-16 text-xs font-medium',
            isForegrounded ? 'text-foreground/80' : 'text-muted-foreground/50',
          )}
        >
          <span className="pointer-events-none truncate">{title}</span>
        </div>
      </div>
      )}

      {/* Surface body. */}
      <div className="flex-1 min-h-0 overflow-hidden">{children}</div>

      {/* D15 resize handles — eight, one per edge + corner. Only
          rendered when interactive (multi-window mode). The handles
          are absolutely-positioned thin tracks at the frame edges. */}
      {interactive && windowState && (
        <>
          {/* Edges */}
          <div
            onMouseDown={(e) => startDrag('resize-n', e)}
            className="absolute left-2 right-2 top-0 h-1 cursor-ns-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-s', e)}
            className="absolute left-2 right-2 bottom-0 h-1 cursor-ns-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-w', e)}
            className="absolute top-2 bottom-2 left-0 w-1 cursor-ew-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-e', e)}
            className="absolute top-2 bottom-2 right-0 w-1 cursor-ew-resize"
            aria-hidden
          />
          {/* Corners */}
          <div
            onMouseDown={(e) => startDrag('resize-nw', e)}
            className="absolute top-0 left-0 h-2 w-2 cursor-nwse-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-ne', e)}
            className="absolute top-0 right-0 h-2 w-2 cursor-nesw-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-sw', e)}
            className="absolute bottom-0 left-0 h-2 w-2 cursor-nesw-resize"
            aria-hidden
          />
          <div
            onMouseDown={(e) => startDrag('resize-se', e)}
            className="absolute bottom-0 right-0 h-2 w-2 cursor-nwse-resize"
            aria-hidden
          />
        </>
      )}
    </div>
  );
}

// =============================================================================
// TrafficLightButton — macOS-style traffic-light (D19.1, 2026-05-22)
// =============================================================================
//
// Three colored 12px circles in the title bar's left cluster: red close,
// yellow minimize, green maximize. macOS-faithful styling:
//
//   - Foregrounded window: full color (red/yellow/green) by default.
//   - Background window: neutral gray by default; light up to full color
//     when the operator hovers the cluster (lets them target a button
//     without raising the window first).
//   - Hover-on-self: glyph appears (×, −, +). Otherwise just colored
//     circle with no glyph (matches macOS).
//   - Click stops propagation so the title-bar drag handler doesn't fire.

type TrafficTone = 'close' | 'minimize' | 'maximize';

const TONE_COLOR: Record<TrafficTone, string> = {
  close: 'bg-[#ff5f57] hover:bg-[#ff5f57]',
  minimize: 'bg-[#febc2e] hover:bg-[#febc2e]',
  maximize: 'bg-[#28c840] hover:bg-[#28c840]',
};

const TONE_RING: Record<TrafficTone, string> = {
  close: 'ring-[#ff5f57]/30',
  minimize: 'ring-[#febc2e]/30',
  maximize: 'ring-[#28c840]/30',
};

function TrafficLightButton({
  tone,
  isForegrounded,
  isClusterHovered,
  label,
  onClick,
  glyph,
}: {
  tone: TrafficTone;
  isForegrounded: boolean;
  isClusterHovered: boolean;
  label: string;
  onClick: () => void;
  glyph: React.ReactNode;
}) {
  // Full-color iff foregrounded OR cluster is being hovered (macOS rule).
  const showColor = isForegrounded || isClusterHovered;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onMouseDown={(e) => e.stopPropagation()}
      aria-label={label}
      title={label}
      className={cn(
        'group flex h-3 w-3 items-center justify-center rounded-full transition-colors ring-1',
        showColor ? TONE_COLOR[tone] : 'bg-muted-foreground/25',
        showColor ? TONE_RING[tone] : 'ring-transparent',
      )}
    >
      {/* Glyph only on hover of the button itself (macOS convention). */}
      <span className="opacity-0 group-hover:opacity-100 transition-opacity">
        {glyph}
      </span>
    </button>
  );
}
