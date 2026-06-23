'use client';

/**
 * ChatDrawer — the operator command channel (ADR-297 D16 + ADR-316).
 *
 * The chat the operator addresses, summoned by the FAB. Hosts:
 *   - Persona header (yarnnn icon + persona name + "Viewing: X" subtitle
 *     + close ×)
 *   - Scrollable addressed-conversation timeline (ConversationPanel,
 *     filtered to pulse='addressed' intrinsically)
 *   - Composer input at the bottom (inside ConversationPanel)
 *
 * ADR-316 — TWO LAYOUT MODES, one component:
 *   - DESKTOP (≥640px): a dockable RAIL. A flex sibling of the window
 *     area (ShellCompositor's `main` flex row). Opening it REDUCES the
 *     surface area; it never occludes the surface. So "Viewing: X" is
 *     honest — the surface stays co-visible and reflows. Width is the
 *     posture dial (narrow=supervise, wide=author): default 400px,
 *     resizable 320–720px via left-edge drag, persisted to localStorage.
 *   - MOBILE (<640px): a full-screen overlay (split is impossible).
 *     "Viewing: X" degrades to a breadcrumb.
 *
 * The conversation body is identical across both modes; only the outer
 * frame differs. surfaceOverride (→ agent context) + the "Viewing: X"
 * label both read the window manager's `foregrounded` slug — one signal,
 * shared operator↔agent↔surface meta-awareness (D16 §5, ADR-186).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { ConversationPanel } from '@/components/tp/ConversationPanel';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { useViewport } from '@/lib/shell/useViewport';
import { Z_DRAWER_BACKDROP, Z_DRAWER_BODY } from '@/lib/shell/z-tiers';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useComposition } from '@/lib/compositor/useComposition';
import { cn } from '@/lib/utils';

const DRAWER_WIDTH_KEY = 'yarnnn:shell:chat-drawer-width';
const DRAWER_MIN = 320;
const DRAWER_MAX = 720;
const DRAWER_DEFAULT = 400;

// ADR-316 §5 — the posture dial. The rail's resting width expresses the
// operator's posture on the foregrounded surface: WIDE when authoring (the
// conversation IS the work — Home + the constitution mirrors), NARROW when
// supervising (the operator mostly reads the surface, occasionally types —
// the Queue + time-shaped reads). This is only the DEFAULT: once the
// operator drags, their explicit width is persisted and wins everywhere
// (Singular width store — one localStorage key, not per-surface state).
const AUTHOR_WIDTH = 520;
const SUPERVISE_WIDTH = 360;
// Surfaces where the conversation leads the work → wider default.
const AUTHOR_SURFACES = new Set([
  'home',
  'mandate',
  'principles',
  'identity',
  'expected-output',
]);
// Surfaces where reading the surface leads and chat is a side-channel →
// narrower default. Everything not named here falls to DRAWER_DEFAULT.
const SUPERVISE_SURFACES = new Set([
  'queue',
  'feed',
  'activity',
  'recurrence',
  'files',
]);

function posturalDefaultWidth(foregrounded: string | null): number {
  if (foregrounded && AUTHOR_SURFACES.has(foregrounded)) return AUTHOR_WIDTH;
  if (foregrounded && SUPERVISE_SURFACES.has(foregrounded)) return SUPERVISE_WIDTH;
  return DRAWER_DEFAULT;
}

/**
 * The operator's explicit width, if they've ever dragged the rail. Null
 * when unset → the postural default applies. Returns a clamped number on
 * the client, null on the server (SSR safety).
 */
function loadStoredWidth(): number | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(DRAWER_WIDTH_KEY);
  if (!raw) return null;
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return null;
  return Math.max(DRAWER_MIN, Math.min(DRAWER_MAX, n));
}

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function ChatDrawer({ open, onClose }: ChatDrawerProps) {
  const { isMobile } = useViewport();
  const personaName = useReviewerPersona();
  // ADR-297 D16 §5 + navigation enactment (2026-05-30): the surface the
  // operator is viewing is the WINDOW MANAGER's foregrounded slug — not
  // the legacy DeskContext surface. One source feeds both the agent's
  // context payload (surfaceOverride → sendMessage) AND the visible
  // "Viewing: X" label, so operator ↔ agent ↔ surface share meta-
  // awareness through the chat channel by construction.
  const { foregrounded } = useSurfacePreferences();
  const { data: composition } = useComposition();
  const viewingTitle = foregrounded
    ? composition.surfaces.find((s) => s.slug === foregrounded)?.title ?? null
    : null;
  // The override handed to the agent: the atomic surface the operator is
  // looking at. Undefined when on the Desktop (no foregrounded surface).
  const surfaceOverride = foregrounded
    ? { type: 'atomic' as const, slug: foregrounded }
    : undefined;
  // `explicitWidth` is the operator's dragged width (null until they drag).
  // The RESOLVED width is explicitWidth ?? posturalDefaultWidth(foregrounded)
  // — so an un-dragged rail widens on authoring surfaces and narrows on
  // supervise surfaces, while a dragged width is honored everywhere.
  const [explicitWidth, setExplicitWidth] = useState<number | null>(null);
  const dragging = useRef(false);
  const width = explicitWidth ?? posturalDefaultWidth(foregrounded);

  // Hydrate the operator's explicit width from localStorage on mount.
  useEffect(() => {
    setExplicitWidth(loadStoredWidth());
  }, []);

  // Escape-to-close.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Drag-to-resize (desktop only). Drag left edge of drawer to widen.
  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isMobile) return;
      e.preventDefault();
      dragging.current = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [isMobile]
  );

  useEffect(() => {
    if (isMobile) return;
    let latest = explicitWidth ?? posturalDefaultWidth(foregrounded);
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const next = Math.max(DRAWER_MIN, Math.min(DRAWER_MAX, window.innerWidth - e.clientX));
      latest = next;
      // Dragging promotes the width to an EXPLICIT operator choice — from
      // here on it overrides the postural default on every surface.
      setExplicitWidth(next);
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      try {
        window.localStorage.setItem(DRAWER_WIDTH_KEY, String(latest));
      } catch {}
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, [explicitWidth, foregrounded, isMobile]);

  // D18.1: always render the wrapper; toggle opacity + pointer-events
  // based on `open`. The drawer body stays mounted across open/close
  // cycles (preserves ConversationPanel state — scroll position,
  // attachment uploads in flight, etc.). Backdrop and body fade over
  // ~150ms via CSS transition. Eliminates the snap-dim flicker
  // operator-observed (KVK 2026-05-22).
  //
  // D18.2 follow-up (2026-05-22): `backdrop-blur-[1px]` removed from the
  // backdrop element. Chromium drops the GPU compositor layer for
  // elements at opacity:0 + dimensions, and re-creating a layer with
  // `backdrop-filter` on the next open caused a paint flash visible
  // as a 1-frame flicker. The 1px blur was barely perceptible anyway;
  // a slightly stronger bg dim covers the same intent. Operator-
  // observed re-open flicker now gone.

  // ADR-316: the conversation body is identical across desktop-rail and
  // mobile-overlay modes; only the OUTER frame differs (flex sibling that
  // reduces the surface vs. fixed overlay that covers it). Factor the body
  // once, wrap it per mode.
  const body = (
    <div className="flex-1 min-w-0 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background shrink-0">
            <div className="flex items-center gap-2">
              <img
                src="/assets/logos/circleonly_yarnnn_1.svg"
                alt=""
                className="w-5 h-5"
              />
              <div className="flex flex-col">
                <span className="text-sm font-medium">
                  {personaName ?? 'Reviewer'}
                </span>
                <span className="text-[10px] text-muted-foreground/60 -mt-0.5">
                  {viewingTitle ? `Viewing: ${viewingTitle}` : 'Desktop'}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
              aria-label="Close conversation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Conversation body — composer + addressed timeline.
              surfaceOverride flows from the window manager's foregrounded
              surface per D16 §5 + navigation enactment, so YARNNN knows
              the operator is "asking about {current surface}" when they
              summon chat from any window. Same signal drives the
              "Viewing: X" header above — shared meta-awareness. */}
          {/* Conversation body — composer + addressed timeline. */}
          <div className="flex-1 min-h-0">
            <ConversationPanel
              surfaceOverride={surfaceOverride}
              plusMenuActions={[]}
              placeholder={`Ask ${personaName ?? 'YARNNN'}…`}
              showCommandPicker={true}
              showInputDivider={true}
            />
          </div>
    </div>
  );

  // ADR-316 — MOBILE: full-screen overlay (split is impossible <640px).
  // Keeps the fixed-position + backdrop + slide-in transition from the
  // pre-ADR-316 drawer. The "Viewing: X" label degrades to a breadcrumb
  // here because the surface cannot be co-visible.
  if (isMobile) {
    return (
      <>
        <div
          className={cn(
            'fixed inset-0 bg-background transition-opacity duration-150',
            open ? 'opacity-100' : 'opacity-0 pointer-events-none',
          )}
          style={{ zIndex: Z_DRAWER_BACKDROP }}
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          className={cn(
            'fixed inset-0 flex bg-background transition-transform duration-150',
            open ? 'translate-x-0' : 'translate-x-full pointer-events-none',
          )}
          style={{ zIndex: Z_DRAWER_BODY }}
          role="dialog"
          aria-hidden={!open}
          aria-label={`Conversation with ${personaName ?? 'Reviewer'}`}
        >
          {body}
        </div>
      </>
    );
  }

  // ADR-316 — DESKTOP: a dockable command RAIL. A flex sibling of the
  // window area (mounted by ShellCompositor's `main` flex row). When open
  // it occupies `width`px and the surface area reflows into the remaining
  // space — it never overlays the surface. When closed it collapses to
  // zero width (animated) and the FAB re-summons it. The drag handle on
  // the left edge is the posture dial (narrow = supervise, wide = author).
  return (
    <div
      className={cn(
        'h-full flex bg-background border-l border-border shadow-xl overflow-hidden transition-[width] duration-150',
        open ? '' : 'pointer-events-none',
      )}
      style={{ width: open ? width : 0 }}
      role="dialog"
      aria-hidden={!open}
      aria-label={`Conversation with ${personaName ?? 'Reviewer'}`}
    >
      {/* Drag handle — left edge of the rail. Drag left to widen. */}
      <div
        onMouseDown={onMouseDown}
        className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
        title="Drag to resize"
      />
      {body}
    </div>
  );
}
