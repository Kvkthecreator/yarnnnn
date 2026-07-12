'use client';

/**
 * Desktop — ADR-297 D17 always-rendered desktop layer.
 *
 * The Desktop is the persistent background of the authenticated
 * viewport. Always rendered. Windows float above it via D15 multi-
 * window mode. The Desktop layer owns:
 *
 *   1. The padded background (bg-muted/30) that's visible wherever
 *      windows don't cover it.
 *   2. The empty-state content — context-aware welcome copy shown
 *      ONLY when zero windows are mounted (first-time operator OR
 *      returning operator who closed everything).
 *   3. The ChatFAB at bottom-center (D17 §7 — was viewport-fixed in
 *      D16; D17 moves it into the Desktop layer so it belongs to the
 *      desktop, not on top of windows).
 *
 * The actual window mounting + positioning lives in SurfaceViewport;
 * Desktop is a thin presentational layer that SurfaceViewport composes
 * its window children on top of.
 *
 * Per ADR-297 D13/D17: Desktop is a load-bearing concept (the
 * operator's "home"), not just an empty-state component. Pre-D17 the
 * <Desktop /> component was rendered conditionally only when no
 * windows were open, and the padded gray wrapper around windows was a
 * separate inline JSX — two code paths for what should be one
 * conceptual surface. D17 unifies them.
 */

import { useEffect, useRef } from 'react';
import { LayoutGrid, FileText, MessageSquare, ArrowRight } from 'lucide-react';
import { FreddieAvatar } from '@/components/freddie/FreddieAvatar';
import { useShellChrome } from './ShellChromeContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_FAB } from '@/lib/shell/z-tiers';
import { cn } from '@/lib/utils';

interface DesktopProps {
  /** Whether any windows are currently mounted on top of the Desktop.
   *  Drives empty-state visibility — copy renders only when no windows. */
  hasWindows: boolean;
  /** Window content from SurfaceViewport, absolute-positioned on top of
   *  the Desktop layer. */
  children?: React.ReactNode;
}

/**
 * Detect first-time operator vs returning-with-empty-registry.
 * First-time = the operator has never opened a window; their
 * windowStates registry is empty AND their open-surfaces registry is
 * empty AND their kept set is exactly the default `['home']`.
 * Anything else is treated as "returning operator who closed
 * everything" (more concise empty-state copy).
 */
function useIsFirstTime(): boolean {
  const { kept, open, windowStates } = useSurfacePreferences();
  if (open.length > 0) return false;
  if (Object.keys(windowStates).length > 0) return false;
  // Default-kept set is ['chat'] (ADR-435 — Home deleted; was ['home'] and,
  // before that, ['channels']/['context']/['feed'] through the dissolved-Channels
  // lineage). Legacy kept entries naming any of those are normalized → 'chat' on
  // read (surface-preferences.ts), so an old default reads as ['chat'] and isn't
  // misclassified. If the operator modified the set (added/removed surfaces),
  // they've used the workspace.
  if (kept.length !== 1) return false;
  if (kept[0] !== 'chat') return false;
  return true;
}

export function Desktop({ hasWindows, children }: DesktopProps) {
  const { toggleDrawer, drawerOpen, layoutMode } = useShellChrome();
  const { setDesktopBounds, foregrounded, navigateToSurface } = useSurfacePreferences();
  const isFirstTime = useIsFirstTime();
  // ADR-412 amendment (2026-07-08) + ADR-447 (2026-07-12) — hide the Freddie
  // rail FAB while a surface that OWNS its own chat is foregrounded: `chat`
  // (Altitude 2 — the member's model-pinned helper threads) and `studio` (the
  // authoring app's bound lane, ADR-440, now the right column). ADR-412 D1
  // kept Freddie's rail (A1) summonable over EVERY surface; the carve is
  // surfaces with a first-class chat of their own, where a second chat entry
  // point (the A1 rail floating over the surface's own lane) reads as two
  // competing "chat" affordances on one screen. The rail stays reachable from
  // any other surface; this only suppresses the redundant summon here. Freddie
  // stays addressable — the drawer, if already open, is unaffected.
  const onOwnChatSurface = foregrounded === 'chat' || foregrounded === 'studio';
  const ref = useRef<HTMLDivElement>(null);
  // ADR-358 — in CANVAS the window area is NOT a desktop with a floating
  // window on wallpaper; it is ONE primary surface filling the column. So
  // the desktop's gray wallpaper + padding are dropped (the surface fills
  // edge-to-edge) and the empty-state copy is suppressed when a surface is
  // mounted. The FAB stays (chat can be closed + re-summoned in either
  // mode). In DESKTOP the wallpaper + padding + empty-state are the
  // ADR-297 D17 desktop, unchanged.
  const canvasFill = layoutMode === 'canvas' && hasWindows;

  // ADR-316: report the Desktop's own measured box to the window manager
  // so window geometry (cascade / maximize / drag-clamp) is relative to
  // the Desktop — which the command rail (chat) reduces as a flex sibling
  // — not the raw viewport. ResizeObserver fires on rail open/close/drag
  // and on viewport resize, keeping geometry correct as the rail moves.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const report = () => setDesktopBounds(el.clientWidth, el.clientHeight);
    report();
    const ro = new ResizeObserver(report);
    ro.observe(el);
    return () => ro.disconnect();
  }, [setDesktopBounds]);

  return (
    <div
      ref={ref}
      className={cn(
        'relative h-full w-full overflow-hidden',
        // ADR-358 — canvas fills with one surface: no wallpaper, no
        // padding. Desktop keeps the gray padded wallpaper (D17).
        canvasFill ? 'bg-background' : 'bg-muted/30 p-3 sm:p-4',
      )}
    >
      {/* Empty-state copy renders only when no windows are mounted.
          Context-aware: a first-time operator gets a cold-start that teaches
          the moat (durable, attributed memory) and invites the first
          substrate-creating act (ADR-437 D3 — the empty state is the demo,
          not a wizard); a returning operator gets a concise "nothing open"
          hint. Neither points at program activation — a program is an
          anytime hire, not a setup step (ADR-414 D5). */}
      {!hasWindows && (
        <div className="absolute inset-0 flex items-center justify-center px-6 pointer-events-none">
          <div className="max-w-md text-center pointer-events-auto">
            {isFirstTime ? (
              <>
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-muted/40 text-muted-foreground">
                  <FileText className="h-5 w-5" />
                </div>
                <h2 className="text-lg font-medium text-foreground mb-1">
                  This workspace is a commons — and it&rsquo;s yours
                </h2>
                <p className="text-sm text-muted-foreground">
                  Drop in a file or tell the system agent what you&rsquo;re
                  working on. Everything that lands here is placed, attributed,
                  and recallable — by you, your team, and any AI you connect.
                </p>
                <div className="mt-5 flex items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => navigateToSurface('files')}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Add your first file
                    <ArrowRight className="h-3 w-3" />
                  </button>
                  <button
                    type="button"
                    onClick={() => navigateToSurface('chat')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted/30 transition-colors"
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                    Talk to your agent
                  </button>
                </div>
                <p className="mt-4 text-[11px] text-muted-foreground/70">
                  Working with others? Invite them from Workspace Settings —
                  they join the same attributed commons.
                </p>
              </>
            ) : (
              <>
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-muted/40 text-muted-foreground">
                  <LayoutGrid className="h-5 w-5" />
                </div>
                <h2 className="text-lg font-medium text-foreground mb-1">
                  Nothing open
                </h2>
                <p className="text-sm text-muted-foreground">
                  Click an icon in the top dock to open a surface, or use
                  the launcher (the grid icon) to browse every surface in
                  the workspace.
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Windows render on top of the Desktop layer (absolute-positioned
          children passed in by SurfaceViewport). */}
      {children}

      {/* ChatFAB — D19.5.1 (2026-05-22):
            • Position: viewport-fixed bottom-RIGHT (was Desktop-fixed
              bottom-center pre-D19.5.1). macOS-faithful — matches the
              Messages compose button shape: floats at viewport-bottom-
              right regardless of which window is foregrounded.
            • Z-tier: Z_FAB (150) — above windows + above drawer
              backdrop. Pre-D19.5.1 the FAB sat at z=5 inside the
              Desktop layer and got covered by every window. Operator-
              felt bug ("the floating chat button on the bottom
              actually isn't floating"). Now genuinely floats.
            • Hide-when-drawer-open: when drawer is open the FAB is
              redundant (drawer header has its own X). Hide via
              opacity-0 + pointer-events-none so clicks on the right
              edge fall through to whatever's behind. Eliminates the
              "FAB-covered-by-drawer-body" stacking awkwardness.
            • FAB_RESERVED reserved-zone in window clamping DELETED
              (was needed when FAB was Desktop-fixed bottom-center and
              z=5; with viewport-fixed + z=150 the windows can extend
              fully and the FAB still wins). Singular Implementation. */}
      <button
        type="button"
        onClick={toggleDrawer}
        aria-label={drawerOpen ? 'Close conversation' : 'Open conversation'}
        title={drawerOpen ? 'Close conversation' : 'Ask Freddie'}
        className={cn(
          // The FAB is now Freddie's face (the system agent, ADR-412 —
          // the rail is Freddie's voice). A light framed disc so the
          // full-color mark reads (its dark-slate hair would vanish on the
          // old black `bg-foreground` disc); ring for definition on the
          // gray wallpaper.
          'fixed flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all hover:shadow-xl active:scale-95 overflow-hidden',
          'bg-background ring-1 ring-border hover:bg-muted',
          // Hidden while the drawer is already open (redundant with its
          // own X) OR while a surface that owns its own chat is foregrounded
          // (chat, studio — see onOwnChatSurface above).
          (drawerOpen || onOwnChatSurface) && 'opacity-0 pointer-events-none',
        )}
        style={{
          right: 'max(1.5rem, env(safe-area-inset-right, 0px) + 0.75rem)',
          bottom: 'max(1.5rem, env(safe-area-inset-bottom, 0px) + 0.75rem)',
          zIndex: Z_FAB,
        }}
      >
        {/* animate={false}: still at rest — motion is Freddie's working
            tell (blink + bolt-pulse), so a resting FAB must not imply
            Freddie is always working. */}
        <FreddieAvatar animate={false} className="h-8 w-8" />
      </button>
    </div>
  );
}
