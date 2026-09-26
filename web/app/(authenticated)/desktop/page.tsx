'use client';

/**
 * Desktop page — ADR-297 D17 Agent OS boot route.
 *
 * The authenticated landing route. Login auth-callback + middleware
 * redirect members here. SurfaceViewport reads the open-surfaces
 * registry and restores last-session windows; with nothing to restore,
 * the shell foregrounds Chat (ADR-670 D1).
 *
 * This page renders nothing — the entire view is driven by
 * SurfaceViewport (mounted inside AuthenticatedLayout > ShellCompositor).
 * The page exists purely so Next.js recognizes `/desktop` as a route;
 * the actual rendering happens in the shell.
 *
 * Per ADR-297 D17 §1: Desktop is the always-rendered background layer
 * of the authenticated viewport. The "nothing open" state and the
 * windows live inside SurfaceViewport's unified Desktop wrapper. This page
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
