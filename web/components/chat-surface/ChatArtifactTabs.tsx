'use client';

import { cn } from '@/lib/utils';
import type { ChatArtifactId, ChatArtifactTab } from './chatArtifactTypes';

interface ChatArtifactTabsProps {
  tabs: ChatArtifactTab[];
  activeId: ChatArtifactId;
  onSelect: (id: ChatArtifactId) => void;
}

export function ChatArtifactTabs({ tabs, activeId, onSelect }: ChatArtifactTabsProps) {
  return (
    <nav
      aria-label="Chat surfaces"
      className="mx-auto flex max-w-full items-center gap-1 overflow-x-auto rounded-xl border border-border bg-background p-1 shadow-sm"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.id === activeId;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelect(tab.id)}
            className={cn(
              'flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors sm:px-4',
              active
                ? 'bg-foreground text-background'
                : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
