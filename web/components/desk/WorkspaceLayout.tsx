'use client';

/**
 * ADR-091: Workspace Layout & Navigation Architecture
 *
 * Shared layout for all chat-first workspace pages:
 * - /dashboard (global TP — no deliverable scope)
 * - /deliverables/[id] (deliverable workspace — scoped TP)
 *
 * Layout:
 * - Header: identity chip + breadcrumb + controls + drawer trigger
 * - Main: chat area (full width, full height)
 * - Drawer: slides from right, overlays content, 480px on desktop / full width on mobile
 *
 * The identity chip is the user's primary signal for "which agent am I talking to."
 * It must always be visible and never ambiguous.
 */

import { useState, useEffect, useCallback } from 'react';
import { X, PanelRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface WorkspacePanelTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface WorkspaceIdentity {
  /** Icon element shown in the identity chip */
  icon: React.ReactNode;
  /** Primary label — "Thinking Partner" or deliverable title */
  label: string;
  /** Optional badge shown next to label — e.g. mode badge "[Rec]" */
  badge?: React.ReactNode;
}

interface WorkspaceLayoutProps {
  /** Identity chip shown in the header — differentiates global TP from deliverable workspace */
  identity: WorkspaceIdentity;
  /** Optional breadcrumb/back nav shown to the left of the identity chip */
  breadcrumb?: React.ReactNode;
  /** Optional controls shown to the right of the header (pause, settings, etc.) */
  headerControls?: React.ReactNode;
  /** The chat area — messages + input bar */
  children: React.ReactNode;
  /** Drawer tabs. If empty, drawer trigger is hidden. */
  panelTabs?: WorkspacePanelTab[];
  /** Default open state for the drawer */
  panelDefaultOpen?: boolean;
}

export function WorkspaceLayout({
  identity,
  breadcrumb,
  headerControls,
  children,
  panelTabs = [],
  panelDefaultOpen = false,
}: WorkspaceLayoutProps) {
  const [drawerOpen, setDrawerOpen] = useState(panelDefaultOpen);
  const [activeTab, setActiveTab] = useState<string>(panelTabs[0]?.id ?? '');

  const hasDrawerTabs = panelTabs.length > 0;
  const activeDrawerContent = panelTabs.find((t) => t.id === activeTab)?.content;

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  // Close drawer on Escape key
  useEffect(() => {
    if (!drawerOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDrawer();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [drawerOpen, closeDrawer]);

  return (
    <div className="h-full flex flex-col">
      {/* Header — CSS grid: left (breadcrumb) | center (identity) | right (controls) */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {breadcrumb}
        </div>

        {/* Center: identity chip */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-muted-foreground shrink-0">{identity.icon}</span>
          <span className="font-medium truncate">{identity.label}</span>
          {identity.badge && <span className="shrink-0">{identity.badge}</span>}
        </div>

        <div className="flex items-center gap-2 shrink-0 justify-end">
          {headerControls}
          {hasDrawerTabs && (
            <button
              onClick={() => setDrawerOpen(!drawerOpen)}
              className={cn(
                'flex items-center gap-1.5 p-2 rounded-md transition-colors text-muted-foreground hover:text-foreground hover:bg-muted',
                drawerOpen && 'bg-muted text-foreground'
              )}
              title={drawerOpen ? 'Close drawer' : 'Open drawer'}
            >
              <PanelRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Body: chat area (full width) */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {children}
      </div>

      {/* Drawer overlay */}
      {hasDrawerTabs && (
        <>
          {/* Backdrop */}
          <div
            className={cn(
              'fixed inset-0 z-40 bg-black/20 transition-opacity duration-300',
              drawerOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
            )}
            onClick={closeDrawer}
          />

          {/* Drawer */}
          <div
            className={cn(
              'fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-background border-l border-border shadow-xl',
              'w-full sm:w-[480px]',
              'transition-transform duration-300 ease-out',
              drawerOpen ? 'translate-x-0' : 'translate-x-full'
            )}
          >
            {/* Tab bar + close button */}
            <div className="flex items-center border-b border-border shrink-0">
              <div className="flex-1 flex overflow-x-auto">
                {panelTabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'px-3 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2',
                      activeTab === tab.id
                        ? 'border-primary text-foreground'
                        : 'border-transparent text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <button
                onClick={closeDrawer}
                className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md mx-1 shrink-0 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto">
              {activeDrawerContent}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
