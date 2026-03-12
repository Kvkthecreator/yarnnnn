'use client';

/**
 * ADR-025: Slash Commands
 * CommandPicker - Autocomplete dropdown for slash commands
 *
 * Shows when user types "/" in TPBar input, filters as they type
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Sparkles, Zap, ChevronRight } from 'lucide-react';
import { useCommands } from '@/hooks/useCommands';
import { cn } from '@/lib/utils';
import type { SlashCommand, CommandTier } from '@/types';

interface CommandPickerProps {
  query: string; // The text after "/"
  onSelect: (command: string) => void;
  onClose: () => void;
  isOpen: boolean;
}

const TIER_CONFIG: Record<CommandTier, { label: string; icon: typeof Sparkles; className: string }> = {
  core: {
    label: 'Core',
    icon: Zap,
    className: 'text-primary',
  },
  beta: {
    label: 'Beta',
    icon: Sparkles,
    className: 'text-amber-500',
  },
};

export function CommandPicker({ query, onSelect, onClose, isOpen }: CommandPickerProps) {
  const { commands, filterCommands, isLoading } = useCommands();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // Filter commands based on query
  const filtered = filterCommands(query);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const items = listRef.current.querySelectorAll('[data-command-item]');
      const selectedItem = items[selectedIndex] as HTMLElement | undefined;
      if (selectedItem) {
        selectedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
        case 'Tab':
          e.preventDefault();
          if (filtered[selectedIndex]) {
            onSelect(filtered[selectedIndex].command);
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [isOpen, filtered, selectedIndex, onSelect, onClose]
  );

  // Add keyboard listener
  useEffect(() => {
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  // Group filtered commands by tier
  const grouped: { tier: CommandTier; commands: SlashCommand[] }[] = [];
  const coreCommands = filtered.filter((s) => s.tier === 'core');
  const betaCommands = filtered.filter((s) => s.tier === 'beta');

  if (coreCommands.length > 0) {
    grouped.push({ tier: 'core', commands: coreCommands });
  }
  if (betaCommands.length > 0) {
    grouped.push({ tier: 'beta', commands: betaCommands });
  }

  // Calculate flat index for selection
  let flatIndex = -1;

  return (
    <div
      className={cn(
        'absolute bottom-full left-0 right-0 mb-2',
        'bg-background border border-border rounded-xl shadow-lg',
        'overflow-hidden',
        'animate-in fade-in slide-in-from-bottom-2 duration-150'
      )}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Zap className="w-3 h-3" />
          <span>Commands</span>
          {query && (
            <>
              <ChevronRight className="w-3 h-3" />
              <span className="text-foreground font-medium">/{query}</span>
            </>
          )}
        </div>
      </div>

      {/* Command list */}
      <div ref={listRef} className="max-h-64 overflow-y-auto p-1">
        {isLoading ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            Loading commands...
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            No matching commands
          </div>
        ) : (
          grouped.map(({ tier, commands: tierCommands }) => {
            const config = TIER_CONFIG[tier];
            const TierIcon = config.icon;

            return (
              <div key={tier}>
                {/* Tier header */}
                <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  <TierIcon className={cn('w-3 h-3', config.className)} />
                  <span>{config.label}</span>
                </div>

                {/* Commands in tier */}
                {tierCommands.map((cmd) => {
                  flatIndex++;
                  const isSelected = flatIndex === selectedIndex;
                  const itemIndex = flatIndex;

                  return (
                    <button
                      key={cmd.command}
                      data-command-item
                      onClick={() => onSelect(cmd.command)}
                      onMouseEnter={() => setSelectedIndex(itemIndex)}
                      className={cn(
                        'w-full flex items-start gap-3 px-3 py-2 rounded-lg text-left',
                        'transition-colors',
                        isSelected
                          ? 'bg-primary/10 text-foreground'
                          : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-medium text-foreground">
                            {cmd.command}
                          </span>
                          {tier === 'beta' && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 font-medium">
                              Beta
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {cmd.description}
                        </p>
                      </div>
                      {isSelected && (
                        <div className="shrink-0 text-[10px] text-muted-foreground mt-1">
                          Enter ↵
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Footer hint */}
      <div className="px-3 py-1.5 border-t border-border bg-muted/30 text-[10px] text-muted-foreground">
        <span className="mr-3">↑↓ Navigate</span>
        <span className="mr-3">↵ Select</span>
        <span>Esc Close</span>
      </div>
    </div>
  );
}
