'use client';

/**
 * ADR-013: Unified Workspace Panel
 * ADR-022: Chat-First Architecture - drawer for detailed views
 *
 * Single panel with tabbed navigation for Context, Work, and Outputs.
 * Also handles deliverable detail/review views opened from chat.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Maximize2, Minimize2, Layers, Calendar, FileText, ChevronLeft } from 'lucide-react';
import { useSurface } from '@/contexts/SurfaceContext';
import { cn } from '@/lib/utils';
import { ContextSurface } from './ContextSurface';
import { ScheduleSurface } from './ScheduleSurface';
import { OutputsSurface } from './OutputsSurface';
import { OutputDetailView } from './OutputDetailView';
import { DeliverableDetail } from '@/components/deliverables/DeliverableDetail';
import { VersionReview } from '@/components/deliverables/VersionReview';
import type { ExpandLevel, SurfaceType } from '@/types/surfaces';

type TabType = 'context' | 'work' | 'outputs';

interface TabConfig {
  id: TabType;
  label: string;
  icon: React.ReactNode;
  surfaceType: SurfaceType;
}

const TABS: TabConfig[] = [
  { id: 'context', label: 'Context', icon: <Layers className="w-4 h-4" />, surfaceType: 'context' },
  { id: 'work', label: 'Work', icon: <Calendar className="w-4 h-4" />, surfaceType: 'schedule' },
  { id: 'outputs', label: 'Outputs', icon: <FileText className="w-4 h-4" />, surfaceType: 'output' },
];

const EXPAND_HEIGHTS: Record<ExpandLevel, string> = {
  peek: '35vh',
  half: '55vh',
  full: '92vh',
};

export function WorkspacePanel() {
  const { state, closeSurface, setExpand, openSurface } = useSurface();
  const [activeTab, setActiveTab] = useState<TabType>('work');
  const [detailView, setDetailView] = useState<{ type: 'output' | 'work'; id: string } | null>(null);

  // ADR-022: Check if this is a deliverable/review view from chat
  const isDeliverableView = state.data?.deliverableId && !state.data?.mode;
  const isReviewView = state.data?.deliverableId && state.data?.mode === 'review';

  // Sync active tab with surface type when opened externally
  useEffect(() => {
    if (state.type) {
      const tab = TABS.find(t => t.surfaceType === state.type);
      if (tab) {
        setActiveTab(tab.id);
      }
      // If opened with specific data (e.g., workId), show detail view
      // Skip if it's a deliverable view (handled separately)
      if (!state.data?.deliverableId) {
        if (state.data?.workId) {
          setDetailView({ type: 'output', id: state.data.workId });
        } else if (state.data?.ticketId) {
          setDetailView({ type: 'output', id: state.data.ticketId });
        }
      }
    }
  }, [state.type, state.data]);

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setDetailView(null); // Clear detail view when switching tabs
    // Update surface type for consistency
    const tabConfig = TABS.find(t => t.id === tab);
    if (tabConfig && state.isOpen) {
      openSurface(tabConfig.surfaceType, undefined, state.expandLevel);
    }
  };

  const handleViewOutput = useCallback((workId: string) => {
    setDetailView({ type: 'output', id: workId });
  }, []);

  const handleBackFromDetail = useCallback(() => {
    setDetailView(null);
  }, []);

  const cycleExpand = () => {
    const levels: ExpandLevel[] = ['half', 'full'];
    const currentIndex = levels.indexOf(state.expandLevel);
    const nextIndex = (currentIndex + 1) % levels.length;
    setExpand(levels[nextIndex]);
  };

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && state.isOpen) {
        if (detailView) {
          setDetailView(null);
        } else {
          closeSurface();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.isOpen, closeSurface, detailView]);

  // Handle review completion
  const handleReviewApproved = useCallback(() => {
    closeSurface();
  }, [closeSurface]);

  // Handle deliverable review navigation
  const handleReviewFromDetail = useCallback((versionId: string) => {
    if (state.data?.deliverableId) {
      openSurface('output', {
        deliverableId: state.data.deliverableId,
        versionId,
        mode: 'review',
      }, 'full');
    }
  }, [state.data?.deliverableId, openSurface]);

  const renderContent = () => {
    // ADR-022: Deliverable review view (full-screen like)
    if (isReviewView && state.data?.deliverableId) {
      return (
        <VersionReview
          deliverableId={state.data.deliverableId}
          versionId={state.data.versionId}
          onClose={closeSurface}
          onApproved={handleReviewApproved}
        />
      );
    }

    // ADR-022: Deliverable detail view
    if (isDeliverableView && state.data?.deliverableId) {
      return (
        <DeliverableDetail
          deliverableId={state.data.deliverableId}
          onBack={closeSurface}
          onReview={handleReviewFromDetail}
        />
      );
    }

    // If viewing a work output detail, show that
    if (detailView) {
      return (
        <OutputDetailView
          workId={detailView.id}
          onBack={handleBackFromDetail}
        />
      );
    }

    // Otherwise show tab content
    switch (activeTab) {
      case 'context':
        return <ContextSurface data={state.data} />;
      case 'work':
        return <ScheduleSurface data={state.data} onViewOutput={handleViewOutput} />;
      case 'outputs':
        return <OutputsSurface onViewOutput={handleViewOutput} />;
      default:
        return null;
    }
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
            className="fixed inset-0 bg-black/20 z-40 lg:hidden"
            onClick={closeSurface}
          />

          {/* Panel - Bottom drawer on mobile, side panel on desktop */}
          <motion.div
            initial={{ y: '100%', x: 0 }}
            animate={{ y: 0, x: 0 }}
            exit={{ y: '100%', x: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={cn(
              // Mobile: bottom drawer
              'fixed inset-x-0 bottom-0 z-50',
              'lg:inset-x-auto lg:top-0 lg:right-0 lg:bottom-0',
              'lg:w-[420px] lg:max-w-[90vw]',
              'bg-background border-t lg:border-t-0 lg:border-l border-border',
              'rounded-t-2xl lg:rounded-none shadow-2xl',
              'flex flex-col'
            )}
            style={{
              height: typeof window !== 'undefined' && window.innerWidth >= 1024
                ? '100%'
                : EXPAND_HEIGHTS[state.expandLevel]
            }}
          >
            {/* Drag Handle - mobile only */}
            <div className="flex justify-center py-2 cursor-grab active:cursor-grabbing lg:hidden">
              <div className="w-10 h-1 bg-muted-foreground/30 rounded-full" />
            </div>

            {/* Header with tabs */}
            <div className="border-b border-border">
              {/* Top row: title + actions */}
              <div className="flex items-center justify-between px-4 py-2">
                <div className="flex items-center gap-2">
                  {(detailView || isDeliverableView) && !isReviewView && (
                    <button
                      onClick={detailView ? handleBackFromDetail : closeSurface}
                      className="p-1.5 -ml-1.5 hover:bg-muted rounded-md transition-colors"
                      aria-label="Back"
                    >
                      <ChevronLeft size={18} />
                    </button>
                  )}
                  <span className="font-medium text-sm">
                    {isReviewView ? 'Review' : isDeliverableView ? 'Deliverable' : detailView ? 'Output' : 'Workspace'}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={cycleExpand}
                    className="p-2 hover:bg-muted rounded-md transition-colors lg:hidden"
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

              {/* Tab bar - hide when viewing detail or deliverable */}
              {!detailView && !isDeliverableView && !isReviewView && (
                <div className="flex px-2">
                  {TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => handleTabChange(tab.id)}
                      className={cn(
                        'flex items-center gap-1.5 px-3 py-2 text-sm font-medium',
                        'border-b-2 transition-colors',
                        activeTab === tab.id
                          ? 'border-primary text-primary'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      )}
                    >
                      {tab.icon}
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto overscroll-contain">
              {renderContent()}
            </div>

            {/* Bottom safe area for mobile */}
            <div className="h-safe-area-inset-bottom lg:hidden" />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
