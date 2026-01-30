'use client';

/**
 * ADR-014: Top Bar with Minimal Chrome
 * Minimal top bar replacing the sidebar
 */

import { Brain, Calendar, FileText } from 'lucide-react';
import { ProjectSelector } from './ProjectSelector';
import { UserMenu } from './UserMenu';
import { WorkStatus } from './WorkStatus';
import { useSurface } from '@/contexts/SurfaceContext';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/utils';

interface TopBarProps {
  email?: string;
}

export function TopBar({ email }: TopBarProps) {
  const { openSurface, state: surfaceState } = useSurface();
  const isDesktop = useMediaQuery('(min-width: 768px)');

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0 sticky top-0 z-40">
      {/* Left section: Logo + Project + Work Status */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <span className="text-xl font-brand">yarnnn</span>

        {/* Project Selector */}
        <ProjectSelector />

        {/* Work Status (ADR-016) */}
        <WorkStatus />
      </div>

      {/* Right section: Surface buttons + User */}
      <div className="flex items-center gap-2">
        {/* Surface quick-access buttons (desktop only) */}
        {isDesktop && (
          <div className="flex items-center gap-1 mr-2">
            <button
              onClick={() => openSurface('context')}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md transition-colors",
                surfaceState.isOpen && surfaceState.type === 'context'
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title="View context/memories"
            >
              <Brain className="w-4 h-4" />
              <span className="hidden lg:inline">Context</span>
            </button>

            <button
              onClick={() => openSurface('schedule')}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md transition-colors",
                surfaceState.isOpen && surfaceState.type === 'schedule'
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title="View schedules"
            >
              <Calendar className="w-4 h-4" />
              <span className="hidden lg:inline">Schedule</span>
            </button>

            <button
              onClick={() => openSurface('output')}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md transition-colors",
                surfaceState.isOpen && surfaceState.type === 'output'
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title="View outputs/work"
            >
              <FileText className="w-4 h-4" />
              <span className="hidden lg:inline">Outputs</span>
            </button>
          </div>
        )}

        {/* User Menu */}
        <UserMenu email={email} />
      </div>
    </header>
  );
}
