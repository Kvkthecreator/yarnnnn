'use client';

import { FileText, List } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PlatformTabSwitcherProps {
  activeTab: 'sources' | 'context';
  onTabChange: (tab: 'sources' | 'context') => void;
  sourcesLabel?: string;
  sourcesIcon?: React.ReactNode;
  contextLabel?: string;
  contextIcon?: React.ReactNode;
  className?: string;
}

export function PlatformTabSwitcher({
  activeTab,
  onTabChange,
  sourcesLabel = 'Sources',
  sourcesIcon = <List className="w-4 h-4" />,
  contextLabel = 'Synced content',
  contextIcon = <FileText className="w-4 h-4" />,
  className,
}: PlatformTabSwitcherProps) {
  return (
    <div className={cn('inline-flex items-center border border-border rounded-lg p-1 bg-muted/20 w-fit', className)}>
      <button
        onClick={() => onTabChange('sources')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
          activeTab === 'sources'
            ? 'bg-background text-foreground shadow-sm'
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
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        {contextIcon}
        {contextLabel}
      </button>
    </div>
  );
}
