'use client';

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * IDE-style tab bar for switching between chat and output views.
 * Chat tab is always first and cannot be closed.
 */

import { MessageSquare, FileText, X, GitBranch } from 'lucide-react';
import { useTabs } from '@/contexts/TabContext';
import { cn } from '@/lib/utils';
import type { Tab } from '@/lib/tabs';

// Icons for different tab types
const TAB_ICONS: Record<string, React.ReactNode> = {
  chat: <MessageSquare className="w-3.5 h-3.5" />,
  deliverable: <FileText className="w-3.5 h-3.5" />,
  version: <GitBranch className="w-3.5 h-3.5" />,
  document: <FileText className="w-3.5 h-3.5" />,
};

export function TabBar() {
  const { tabs, activeTabId, setActiveTab, closeTab } = useTabs();

  const handleClose = (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation();
    closeTab(tabId);
  };

  return (
    <div className="h-9 bg-muted/30 border-b border-border flex items-end overflow-x-auto">
      {tabs.map((tab) => (
        <TabItem
          key={tab.id}
          tab={tab}
          isActive={tab.id === activeTabId}
          onClick={() => setActiveTab(tab.id)}
          onClose={(e) => handleClose(e, tab.id)}
        />
      ))}
    </div>
  );
}

interface TabItemProps {
  tab: Tab;
  isActive: boolean;
  onClick: () => void;
  onClose: (e: React.MouseEvent) => void;
}

function TabItem({ tab, isActive, onClick, onClose }: TabItemProps) {
  const icon = TAB_ICONS[tab.type] || TAB_ICONS.document;

  return (
    <button
      onClick={onClick}
      className={cn(
        'group relative flex items-center gap-1.5 px-3 h-8 text-xs font-medium',
        'border-r border-border transition-colors',
        'hover:bg-background/50',
        isActive
          ? 'bg-background text-foreground border-b-0 -mb-px'
          : 'text-muted-foreground'
      )}
    >
      {/* Active indicator */}
      {isActive && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-primary" />
      )}

      {/* Icon */}
      <span className={cn(isActive ? 'text-primary' : 'text-muted-foreground')}>
        {icon}
      </span>

      {/* Title */}
      <span className="truncate max-w-[120px]">{tab.title}</span>

      {/* Dirty indicator */}
      {tab.isDirty && (
        <span className="w-1.5 h-1.5 rounded-full bg-primary" />
      )}

      {/* Close button (not for chat) */}
      {tab.isClosable !== false && (
        <button
          onClick={onClose}
          className={cn(
            'ml-1 p-0.5 rounded hover:bg-muted transition-colors',
            'opacity-0 group-hover:opacity-100',
            isActive && 'opacity-50'
          )}
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </button>
  );
}
