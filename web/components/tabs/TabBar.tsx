'use client';

/**
 * ADR-022: Tab-Based Supervision Architecture
 *
 * Tab bar component - displays open tabs with close buttons.
 * Supports reordering via drag and drop.
 */

import { useCallback } from 'react';
import { X, Loader2, AlertCircle } from 'lucide-react';
import { useTabs } from '@/contexts/TabContext';
import { TAB_ICONS, TabStatus } from '@/lib/tabs';
import { cn } from '@/lib/utils';

export function TabBar() {
  const { tabs, activeTabId, setActiveTab, closeTab } = useTabs();

  const handleTabClick = useCallback((tabId: string) => {
    setActiveTab(tabId);
  }, [setActiveTab]);

  const handleCloseClick = useCallback((e: React.MouseEvent, tabId: string) => {
    e.stopPropagation();
    closeTab(tabId);
  }, [closeTab]);

  // Status indicator
  const StatusIndicator = ({ status }: { status: TabStatus }) => {
    if (status === 'loading') {
      return <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />;
    }
    if (status === 'error') {
      return <AlertCircle className="w-3 h-3 text-destructive" />;
    }
    if (status === 'unsaved') {
      return <span className="w-2 h-2 rounded-full bg-amber-500" />;
    }
    return null;
  };

  return (
    <div className="flex items-center h-10 bg-muted/30 border-b border-border overflow-x-auto">
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTabId;
        const icon = TAB_ICONS[tab.type];

        return (
          <div
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={cn(
              "group flex items-center gap-2 h-full px-3 border-r border-border cursor-pointer transition-colors min-w-0",
              "hover:bg-muted/50",
              isActive
                ? "bg-background border-b-2 border-b-primary -mb-px"
                : "bg-transparent"
            )}
          >
            {/* Icon */}
            <span className="text-sm shrink-0">{icon}</span>

            {/* Title */}
            <span className={cn(
              "text-sm truncate max-w-[120px]",
              isActive ? "text-foreground font-medium" : "text-muted-foreground"
            )}>
              {tab.title}
            </span>

            {/* Status indicator */}
            <StatusIndicator status={tab.status} />

            {/* Close button */}
            {tab.closeable && (
              <button
                onClick={(e) => handleCloseClick(e, tab.id)}
                className={cn(
                  "p-0.5 rounded hover:bg-muted-foreground/20 transition-opacity",
                  "opacity-0 group-hover:opacity-100",
                  isActive && "opacity-100"
                )}
              >
                <X className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            )}
          </div>
        );
      })}

      {/* New tab button (future - for now just spacer) */}
      <div className="flex-1" />
    </div>
  );
}
