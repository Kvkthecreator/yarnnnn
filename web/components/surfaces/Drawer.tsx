'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Drawer component - swipe-up on mobile, side panel on desktop
 */

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence, PanInfo } from 'framer-motion';
import { X, Maximize2, Minimize2, ChevronDown } from 'lucide-react';
import { useSurface } from '@/contexts/SurfaceContext';
import { cn } from '@/lib/utils';
import type { ExpandLevel } from '@/types/surfaces';

const EXPAND_HEIGHTS: Record<ExpandLevel, string> = {
  peek: '35vh',
  half: '55vh',
  full: '92vh',
};

const SURFACE_TITLES: Record<string, string> = {
  output: 'Output',
  context: 'Context',
  schedule: 'Schedules',
  export: 'Export',
};

interface DrawerProps {
  children: React.ReactNode;
}

export function Drawer({ children }: DrawerProps) {
  const { state, closeSurface, setExpand } = useSurface();
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && state.isOpen) {
        closeSurface();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.isOpen, closeSurface]);

  const handleDragEnd = (_: unknown, info: PanInfo) => {
    const velocity = info.velocity.y;
    const offset = info.offset.y;

    // Fast swipe down = close
    if (velocity > 500 || offset > 150) {
      if (state.expandLevel === 'full') {
        setExpand('half');
      } else {
        closeSurface();
      }
      return;
    }

    // Fast swipe up = expand
    if (velocity < -500 || offset < -150) {
      if (state.expandLevel === 'half') {
        setExpand('full');
      } else if (state.expandLevel === 'peek') {
        setExpand('half');
      }
      return;
    }
  };

  const cycleExpand = () => {
    const levels: ExpandLevel[] = ['half', 'full'];
    const currentIndex = levels.indexOf(state.expandLevel);
    const nextIndex = (currentIndex + 1) % levels.length;
    setExpand(levels[nextIndex]);
  };

  return (
    <AnimatePresence>
      {state.isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={closeSurface}
          />

          {/* Drawer */}
          <motion.div
            ref={drawerRef}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={0.2}
            onDragEnd={handleDragEnd}
            className={cn(
              'fixed inset-x-0 bottom-0 z-50',
              'bg-background border-t border-border rounded-t-2xl shadow-2xl',
              'flex flex-col',
              'touch-none' // Prevent scroll interference
            )}
            style={{ height: EXPAND_HEIGHTS[state.expandLevel] }}
          >
            {/* Drag Handle */}
            <div className="flex justify-center py-3 cursor-grab active:cursor-grabbing">
              <div className="w-10 h-1 bg-muted-foreground/30 rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">
                  {state.type ? SURFACE_TITLES[state.type] : 'Surface'}
                </span>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={cycleExpand}
                  className="p-2 hover:bg-muted rounded-md transition-colors"
                  aria-label={state.expandLevel === 'full' ? 'Minimize' : 'Maximize'}
                >
                  {state.expandLevel === 'full' ? (
                    <Minimize2 size={16} />
                  ) : (
                    <Maximize2 size={16} />
                  )}
                </button>
                <button
                  onClick={closeSurface}
                  className="p-2 hover:bg-muted rounded-md transition-colors"
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto overscroll-contain">
              {children}
            </div>

            {/* Bottom safe area for mobile */}
            <div className="h-safe-area-inset-bottom" />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/**
 * Desktop side panel variant (for screens >= 1024px)
 * Used when we want side-by-side view
 */
export function SidePanel({ children }: DrawerProps) {
  const { state, closeSurface } = useSurface();

  // Close on escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && state.isOpen) {
        closeSurface();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.isOpen, closeSurface]);

  return (
    <AnimatePresence>
      {state.isOpen && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className={cn(
            'fixed top-0 right-0 bottom-0 z-40',
            'w-[480px] max-w-[90vw]',
            'bg-background border-l border-border shadow-2xl',
            'flex flex-col'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <span className="font-medium">
              {state.type ? SURFACE_TITLES[state.type] : 'Surface'}
            </span>
            <button
              onClick={closeSurface}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto">
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
