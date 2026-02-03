'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Main desk container - routes to current surface
 */

import { Loader2 } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { SurfaceRouter } from './SurfaceRouter';
import { TPBar } from '@/components/tp/TPBar';

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
    <div className="h-full flex flex-col">
      {/* Main surface area */}
      <div className="flex-1 overflow-hidden">
        <SurfaceRouter surface={surface} />
      </div>

      {/* TP floating bar */}
      <TPBar />
    </div>
  );
}
