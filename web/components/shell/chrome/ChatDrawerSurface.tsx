'use client';

/**
 * ChatDrawerSurface — ADR-297 D16 chrome surface
 * (region: floating-overlay, archetype: input, visibility: summon).
 *
 * The universal chat affordance. Mounts both the persistent FAB
 * (bottom-center, viewport-fixed) and the slide-over drawer body
 * (conditionally rendered on drawerOpen from ShellChromeContext).
 *
 * Replaces the D11 Phase C `ChatComposerSurface` (bottom-strip
 * composer, always visible). D16 §6 enumerates the full set of
 * deletions that accompany this surface; see ADR-297 §D16.
 */

import { ChatFAB } from './ChatFAB';
import { ChatDrawer } from './ChatDrawer';
import { useShellChrome } from '../ShellChromeContext';

export function ChatDrawerSurface() {
  const { drawerOpen, closeDrawer } = useShellChrome();
  return (
    <>
      <ChatFAB />
      <ChatDrawer open={drawerOpen} onClose={closeDrawer} />
    </>
  );
}
