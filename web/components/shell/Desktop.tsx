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

import { LayoutGrid, MessageCircle } from 'lucide-react';
import { useShellChrome } from './ShellChromeContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
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
 * empty AND their kept set is exactly the default `['feed']`.
 * Anything else is treated as "returning operator who closed
 * everything" (more concise empty-state copy).
 */
function useIsFirstTime(): boolean {
  const { kept, open, windowStates } = useSurfacePreferences();
  if (open.length > 0) return false;
  if (Object.keys(windowStates).length > 0) return false;
  // Default-kept set is ['feed']. If the operator has modified it
  // (added or removed surfaces), they've used the workspace before.
  if (kept.length !== 1 || kept[0] !== 'feed') return false;
  return true;
}

export function Desktop({ hasWindows, children }: DesktopProps) {
  const { toggleDrawer, drawerOpen } = useShellChrome();
  const isFirstTime = useIsFirstTime();

  return (
    <div className="relative h-full w-full bg-muted/30 p-3 sm:p-4 overflow-hidden">
      {/* Empty-state copy renders only when no windows are mounted.
          Context-aware: first-time operators get a richer welcome with
          an arrow pointer; returning operators get a concise hint. */}
      {!hasWindows && (
        <div className="absolute inset-0 flex items-center justify-center px-6 pointer-events-none">
          <div className="max-w-md text-center pointer-events-auto">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-muted/40 text-muted-foreground">
              <LayoutGrid className="h-5 w-5" />
            </div>
            {isFirstTime ? (
              <>
                <h2 className="text-lg font-medium text-foreground mb-1">
                  Welcome to YARNNN
                </h2>
                <p className="text-sm text-muted-foreground">
                  Click the launcher (the grid icon{' '}
                  <span aria-hidden className="inline-flex items-center -mt-0.5 align-middle">
                    <LayoutGrid className="inline h-3 w-3" />
                  </span>
                  ) in the top bar to see all surfaces, or click a pinned
                  icon in the dock above to open it.
                </p>
              </>
            ) : (
              <>
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

      {/* ChatFAB — D17 §7: lives on the Desktop layer, NOT viewport-fixed.
          Z-stack below windows (z 5; windows start at z 10 per D15)
          so when windows cover the bottom-center area, the FAB is
          hidden underneath. D15 bounds-clamping reserves a bottom-
          center strip so the FAB remains reachable even with many
          open windows. */}
      <button
        type="button"
        onClick={toggleDrawer}
        aria-label={drawerOpen ? 'Close conversation' : 'Open conversation'}
        title={drawerOpen ? 'Close conversation' : 'Ask YARNNN'}
        className={cn(
          'absolute left-1/2 -translate-x-1/2 z-[5] flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all hover:shadow-xl active:scale-95',
          drawerOpen
            ? 'bg-foreground text-background hover:bg-foreground/90'
            : 'bg-background text-foreground border border-border hover:bg-muted'
        )}
        style={{
          bottom: 'max(1.5rem, env(safe-area-inset-bottom, 0px) + 0.75rem)',
        }}
      >
        <MessageCircle className="h-5 w-5" />
      </button>
    </div>
  );
}
