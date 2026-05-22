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
 * Reconciliation with per-surface PageHeader (D14 carryover): title
 * bar shows the surface name only; the per-surface PageHeader inside
 * `children` continues to render breadcrumb + actions.
 */

import { useCallback, useEffect, useRef, type CSSProperties } from 'react';
import { X } from 'lucide-react';
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
  windowState,
  viewportWidth,
  viewportHeight,
  onWindowStateChange,
  interactive = false,
  children,
}: WindowFrameProps) {
  const dragRef = useRef<DragSession | null>(null);

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

  // Click-anywhere-to-raise (D15 §4). Use mousedown so it fires before
  // any drag/resize handlers and before button clicks inside the body.
  const handleFrameMouseDown = useCallback(() => {
    if (!isForegrounded) onRaise();
  }, [isForegrounded, onRaise]);

  return (
    <div
      onMouseDown={handleFrameMouseDown}
      style={frameStyle}
      className={cn(
        'flex flex-col overflow-hidden rounded-lg border bg-background shadow-sm transition-shadow',
        // Single-window mode: fill the parent.
        !interactive && 'h-full w-full',
        isForegrounded ? 'border-border shadow-md' : 'border-border/60'
      )}
    >
      {/* Title bar — drag handle in multi-window mode. */}
      <div
        onMouseDown={(e) => {
          // Only initiate drag when clicking the bar itself, not the
          // close button (the button has its own stopPropagation).
          if ((e.target as HTMLElement).closest('button')) return;
          startDrag('move', e);
        }}
        className={cn(
          'flex h-8 shrink-0 items-center justify-between border-b border-border bg-muted/30 px-3',
          interactive && 'cursor-grab active:cursor-grabbing select-none'
        )}
      >
        <div className="text-xs font-medium text-foreground/80 truncate pointer-events-none">
          {title}
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          onMouseDown={(e) => e.stopPropagation()}
          aria-label={`Close ${title}`}
          title={`Close ${title}`}
          className="rounded p-0.5 text-muted-foreground/70 transition-colors hover:bg-destructive/15 hover:text-destructive"
        >
          <X className="h-3 w-3" />
        </button>
      </div>

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
