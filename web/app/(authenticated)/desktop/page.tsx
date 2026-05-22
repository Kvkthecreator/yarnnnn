'use client';

/**
 * Desktop page — ADR-297 D17 Agent OS boot route.
 *
 * The authenticated landing route. Login auth-callback + middleware
 * redirect operators here. SurfaceViewport reads the open-surfaces
 * registry and either restores last-session windows or shows the
 * Desktop empty state with the context-aware welcome copy.
 *
 * This page renders nothing — the entire view is driven by
 * SurfaceViewport (mounted inside AuthenticatedLayout > ShellCompositor).
 * The page exists purely so Next.js recognizes `/desktop` as a route;
 * the actual rendering happens in the shell.
 *
 * Per ADR-297 D17 §1: Desktop is the always-rendered background layer
 * of the authenticated viewport. The empty-state copy + windows + FAB
 * all live inside SurfaceViewport's unified Desktop wrapper. This page
 * file is a route-recognition stub, nothing more.
 */

export default function DesktopPage() {
  // SurfaceViewport handles everything. Render nothing here — the
  // children fallback inside SurfaceViewport (for non-atomic
  // pathnames) used to fire and show this page's content; D17
  // changes that path so /desktop is treated as the canonical
  // Desktop route and the unified Desktop wrapper renders instead.
  return null;
}
