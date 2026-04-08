'use client';

import { Minus, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CommandDeskWindowDefinition, CommandDeskWindowId } from './commandDeskTypes';

interface CommandDeskWindowProps {
  window: CommandDeskWindowDefinition;
  focused: boolean;
  minimized: boolean;
  onFocus: (id: CommandDeskWindowId) => void;
  onMinimize: (id: CommandDeskWindowId) => void;
  onClose?: (id: CommandDeskWindowId) => void;
  mobile?: boolean;
}

export function CommandDeskWindow({
  window,
  focused,
  minimized,
  onFocus,
  onMinimize,
  onClose,
  mobile = false,
}: CommandDeskWindowProps) {
  const Icon = window.icon;

  if (minimized && !mobile) return null;

  return (
    <section
      aria-label={window.title}
      onMouseDown={() => onFocus(window.id)}
      className={cn(
        'flex min-h-0 flex-col overflow-hidden rounded-lg border bg-background shadow-lg transition-all',
        focused ? 'border-foreground/20 shadow-xl' : 'border-border/80 shadow-md',
        mobile ? 'relative min-h-[340px] w-full' : 'absolute',
        !mobile && window.desktopClassName,
        !mobile && focused && 'z-[60]',
        mobile && window.id === 'tp-chat' && 'min-h-[520px]'
      )}
    >
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-muted/20 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            {window.eyebrow && (
              <p className="truncate text-[9px] font-medium uppercase tracking-wide text-muted-foreground/60">
                {window.eyebrow}
              </p>
            )}
            <h2 className="truncate text-xs font-medium">{window.title}</h2>
          </div>
        </div>
        {!mobile && (
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onMinimize(window.id);
              }}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label={`Minimize ${window.title}`}
            >
              <Minus className="h-3.5 w-3.5" />
            </button>
            {onClose && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onClose(window.id);
                }}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label={`Close ${window.title}`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {window.content}
      </div>
    </section>
  );
}
