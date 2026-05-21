'use client';

/**
 * Desktop — ADR-297 D13 empty state.
 *
 * Rendered by SurfaceViewport when the open-surfaces registry is
 * empty. This is the operator's "no surface foregrounded" view —
 * deliberately quiet, with the top-center dock-bar still visible
 * (mounted by ShellCompositor independently) and a single
 * empty-state line nudging the operator to summon something.
 *
 * macOS metaphor: this is the empty desktop wallpaper. The Dock is
 * still there; clicking a Dock icon opens a surface. The desktop is
 * not a navigation destination — it's the absence of an open
 * application.
 *
 * D13 ships the minimum-viable empty state — a centered prompt with
 * affordances pointing to the launcher (top-center icon) and to
 * pinning. A future ADR may promote the desktop to a first-class
 * kernel surface with operator-customizable wallpaper, pinned-files,
 * etc.; D13 deliberately does NOT do that.
 */

import { LayoutGrid } from 'lucide-react';

export function Desktop() {
  return (
    <div className="flex h-full w-full items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-muted/40 text-muted-foreground">
          <LayoutGrid className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-medium text-foreground mb-1">
          Nothing open
        </h2>
        <p className="text-sm text-muted-foreground">
          Click an icon in the top dock to open a surface, or use the
          launcher (the grid icon) to browse every surface in the
          workspace.
        </p>
      </div>
    </div>
  );
}
