'use client';

/**
 * DEPRECATED: ADR-037 supersedes this with ChatFirstDesk
 *
 * This component (ADR-023: Supervisor Desk Architecture) is kept for
 * backwards compatibility but is no longer the primary layout.
 *
 * Use ChatFirstDesk instead for the chat-first experience.
 *
 * @deprecated Use ChatFirstDesk from '@/components/desk/ChatFirstDesk'
 */

import { Loader2 } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { SurfaceRouter } from './SurfaceRouter';
import { TPDrawer } from '@/components/tp/TPDrawer';

export function Desk() {
  const { surface, isLoading, error } = useDesk();

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Main surface area - takes remaining space */}
      <main className="flex-1 overflow-hidden">
        <SurfaceRouter surface={surface} />
      </main>

      {/* TP Drawer - right side panel (desktop) or full-screen overlay (mobile) */}
      <TPDrawer />
    </div>
  );
}
