'use client';

import { cn } from '@/lib/utils';
import type { CommandDeskWindowDefinition, CommandDeskWindowId } from './commandDeskTypes';

interface CommandDeskDockProps {
  windows: CommandDeskWindowDefinition[];
  focusedWindowId: CommandDeskWindowId;
  minimizedWindowIds: CommandDeskWindowId[];
  onSelect: (id: CommandDeskWindowId) => void;
}

export function CommandDeskDock({
  windows,
  focusedWindowId,
  minimizedWindowIds,
  onSelect,
}: CommandDeskDockProps) {
  return (
    <nav
      aria-label="Command desk windows"
      className="absolute bottom-4 left-1/2 z-40 hidden -translate-x-1/2 items-center gap-1 rounded-lg border border-border/80 bg-background/90 px-2 py-1.5 shadow-lg backdrop-blur lg:flex"
    >
      {windows.map((window) => {
        const Icon = window.icon;
        const selected = focusedWindowId === window.id && !minimizedWindowIds.includes(window.id);
        const minimized = minimizedWindowIds.includes(window.id);

        return (
          <button
            key={window.id}
            type="button"
            onClick={() => onSelect(window.id)}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-medium transition-colors',
              selected
                ? 'bg-foreground text-background'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              minimized && 'border border-dashed border-border'
            )}
            title={minimized ? `Restore ${window.title}` : `Focus ${window.title}`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{window.title}</span>
          </button>
        );
      })}
    </nav>
  );
}
