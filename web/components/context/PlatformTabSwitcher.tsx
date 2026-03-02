'use client';

import { FileText, List } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PlatformTabSwitcherProps {
  activeTab: 'sources' | 'context';
  onTabChange: (tab: 'sources' | 'context') => void;
  sourcesLabel?: string;
  sourcesIcon?: React.ReactNode;
}

export function PlatformTabSwitcher({
  activeTab,
  onTabChange,
  sourcesLabel = 'Sources',
  sourcesIcon = <List className="w-4 h-4" />,
}: PlatformTabSwitcherProps) {
  return (
    <div className="flex items-center border border-border rounded-lg p-0.5 w-fit mb-6">
      <button
        onClick={() => onTabChange('sources')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
          activeTab === 'sources'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        {sourcesIcon}
        {sourcesLabel}
      </button>
      <button
        onClick={() => onTabChange('context')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
          activeTab === 'context'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        <FileText className="w-4 h-4" />
        Context
      </button>
    </div>
  );
}
