'use client';

/**
 * ChatFAB — ADR-297 D16 universal chat affordance.
 *
 * The single persistent FAB at viewport bottom-center that summons
 * the universal chat drawer. Floats above all open surface windows
 * (z-stacked higher than the window manager's z-baseline of 10 + N).
 *
 * Per ADR-297 §D16:
 *   - One FAB, viewport-fixed, bottom-center.
 *   - 48px circle, MessageCircle icon (lucide).
 *   - Filled style when drawer is open; outline style when closed.
 *   - Click toggles drawerOpen via ShellChromeContext.
 *   - No keyboard shortcut in v1 (operator request can pull forward).
 *   - Safe-area inset honored for iOS.
 */

import { MessageCircle } from 'lucide-react';
import { useShellChrome } from '../ShellChromeContext';
import { cn } from '@/lib/utils';

export function ChatFAB() {
  const { drawerOpen, toggleDrawer } = useShellChrome();

  return (
    <button
      type="button"
      onClick={toggleDrawer}
      aria-label={drawerOpen ? 'Close conversation' : 'Open conversation'}
      title={drawerOpen ? 'Close conversation' : 'Ask YARNNN'}
      // z-index: 60 — sits above windows (10 + max-stack), the
      // launcher overlay (z-50), and the drawer's backdrop (z-40)
      // but below the drawer body itself when open (z-50).
      // Actually we want the FAB to stay visible even with the
      // drawer open (so operators can quickly close via the same
      // button) — so we use z-50, same tier as the drawer, but
      // hide-when-drawer-open isn't desired. Use z-60.
      className={cn(
        'fixed left-1/2 -translate-x-1/2 z-[60] flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all hover:shadow-xl active:scale-95',
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
  );
}
