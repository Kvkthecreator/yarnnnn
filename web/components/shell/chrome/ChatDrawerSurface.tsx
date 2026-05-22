'use client';

/**
 * ChatDrawerSurface — ADR-297 D16 + D17 chrome surface
 * (region: floating-overlay, archetype: input, visibility: summon).
 *
 * D17 (2026-05-22): only the drawer mounts here. The FAB moved into
 * the Desktop layer (web/components/shell/Desktop.tsx) per D17 §7,9 —
 * the FAB is a desktop-level affordance (it belongs on the desktop
 * wallpaper); the drawer is a temporary overlay that covers content.
 * Different homes; different responsibilities.
 *
 * Pre-D17 this surface mounted both ChatFAB + ChatDrawer. Post-D17
 * ChatFAB.tsx is DELETED (Singular Implementation — body inlined into
 * Desktop.tsx); ChatDrawerSurface shrinks to drawer-only.
 */

import { ChatDrawer } from './ChatDrawer';
import { useShellChrome } from '../ShellChromeContext';

export function ChatDrawerSurface() {
  const { drawerOpen, closeDrawer } = useShellChrome();
  return <ChatDrawer open={drawerOpen} onClose={closeDrawer} />;
}
