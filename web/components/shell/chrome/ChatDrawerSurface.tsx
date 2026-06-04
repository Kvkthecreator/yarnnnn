'use client';

/**
 * ChatDrawerSurface — chrome surface for the chat command rail
 * (region: main-rail, archetype: input, visibility: summon).
 *
 * ADR-316 (2026-06-04): region flips floating-overlay → main-rail. The
 * chat is the command-line OVER the active surface — a dockable rail
 * (desktop) that reduces the surface area, degrading to a full-screen
 * overlay only on mobile. ShellCompositor mounts this as a flex sibling
 * of SurfaceViewport inside `main`. The ChatDrawer component owns both
 * layout modes; this wrapper just threads open/close state.
 *
 * D17 (2026-05-22): the FAB lives in the Desktop layer
 * (web/components/shell/Desktop.tsx), not here — it's a desktop-level
 * affordance. ChatFAB.tsx is DELETED (Singular Implementation).
 */

import { ChatDrawer } from './ChatDrawer';
import { useShellChrome } from '../ShellChromeContext';

export function ChatDrawerSurface() {
  const { drawerOpen, closeDrawer } = useShellChrome();
  return <ChatDrawer open={drawerOpen} onClose={closeDrawer} />;
}
