'use client';

/**
 * Inline plus-menu for chat input bar.
 *
 * Replaces the paperclip (image upload) button with a contextual `+` button
 * that opens a compact popover of per-surface actions. Image upload is one
 * action inside the menu.
 *
 * See docs/design/INLINE-PLUS-MENU.md
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Plus, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PlusMenuAction {
  id: string;
  label: string;
  icon: LucideIcon;
  onSelect: () => void;
}

interface PlusMenuProps {
  actions: PlusMenuAction[];
  disabled?: boolean;
}

export function PlusMenu({ actions, disabled }: PlusMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open]);

  const handleSelect = useCallback(
    (action: PlusMenuAction) => {
      action.onSelect();
      setOpen(false);
    },
    []
  );

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
        className={cn(
          'shrink-0 p-3 transition-colors',
          open
            ? 'text-primary'
            : 'text-muted-foreground hover:text-foreground',
          'disabled:opacity-50'
        )}
        aria-label="More actions"
      >
        <Plus
          className={cn(
            'w-5 h-5 transition-transform duration-150',
            open && 'rotate-45'
          )}
        />
      </button>

      {open && (
        <div
          ref={menuRef}
          className={cn(
            'absolute bottom-full left-0 mb-2 z-50',
            'bg-background border border-border rounded-xl shadow-lg',
            'overflow-hidden min-w-[200px]',
            'animate-in fade-in slide-in-from-bottom-2 duration-150'
          )}
        >
          <div className="p-1">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  onClick={() => handleSelect(action)}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-sm',
                    'transition-colors',
                    'hover:bg-muted text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{action.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
