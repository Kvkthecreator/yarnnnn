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
 *   2. The "nothing open" state — shown ONLY when zero windows are
 *      mounted because the member closed (or minimized) everything. A boot with nothing
 *      to restore never shows it: the shell foregrounds Chat instead
 *      (ADR-670 D1, the boot decision in useSurfacePreferences).
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
import { useTranslations } from 'next-intl';
import { LayoutGrid } from 'lucide-react';
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

export function Desktop({ hasWindows, children }: DesktopProps) {
  const { layoutMode } = useShellChrome();
  const { setDesktopBounds, booted } = useSurfacePreferences();
  const t = useTranslations('shell.desktopEmpty');
  const ref = useRef<HTMLDivElement>(null);
  // ADR-358 — in CANVAS the window area is NOT a desktop with a floating
  // window on wallpaper; it is ONE primary surface filling the column. So
  // the desktop's gray wallpaper + padding are dropped (the surface fills
  // edge-to-edge) and the empty-state copy is suppressed when a surface is
  // mounted. In DESKTOP the wallpaper + padding + empty-state are the
  // ADR-297 D17 desktop, unchanged.
  const canvasFill = layoutMode === 'canvas' && hasWindows;

  // ADR-316: report the Desktop's own measured box to the window manager
  // so window geometry (cascade / maximize / drag-clamp) is relative to
  // the Desktop — below the top bar and locator strip — not the raw
  // viewport. ResizeObserver keeps geometry correct as the viewport resizes.
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
      {/* The "nothing open" state renders only when no windows are mounted,
          and only after the boot decision (`booted`, ADR-670 D1): a boot with
          nothing to restore foregrounds Chat, so this is reached only when the
          member closed (or minimized) everything. Gating on the boot (not merely the
          restore) also keeps a refresh of a workspace with open windows from
          flashing it before they remount (the 2026-07-13 hydration fix). */}
      {booted && !hasWindows && (
        <div className="absolute inset-0 flex items-center justify-center px-6 pointer-events-none">
          <div className="max-w-md text-center pointer-events-auto">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-muted/40 text-muted-foreground">
              <LayoutGrid className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-medium text-foreground mb-1">
              {t('nothingOpenTitle')}
            </h2>
            <p className="text-sm text-muted-foreground">{t('nothingOpenBody')}</p>
          </div>
        </div>
      )}

      {/* Windows render on top of the Desktop layer (absolute-positioned
          children passed in by SurfaceViewport). */}
      {children}

    </div>
  );
}
