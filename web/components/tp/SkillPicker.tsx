'use client';

/**
 * ADR-025: Skills (Slash Commands)
 * SkillPicker - Autocomplete dropdown for slash commands
 *
 * Shows when user types "/" in TPBar input, filters as they type
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Sparkles, Zap, ChevronRight } from 'lucide-react';
import { useSkills } from '@/hooks/useSkills';
import { cn } from '@/lib/utils';
import type { Skill, SkillTier } from '@/types';

interface SkillPickerProps {
  query: string; // The text after "/"
  onSelect: (command: string) => void;
  onClose: () => void;
  isOpen: boolean;
}

const TIER_CONFIG: Record<SkillTier, { label: string; icon: typeof Sparkles; className: string }> = {
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

export function SkillPicker({ query, onSelect, onClose, isOpen }: SkillPickerProps) {
  const { skills, filterSkills, isLoading } = useSkills();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // Filter skills based on query
  const filteredSkills = filterSkills(query);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const items = listRef.current.querySelectorAll('[data-skill-item]');
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
          setSelectedIndex((prev) => Math.min(prev + 1, filteredSkills.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
        case 'Tab':
          e.preventDefault();
          if (filteredSkills[selectedIndex]) {
            onSelect(filteredSkills[selectedIndex].command);
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [isOpen, filteredSkills, selectedIndex, onSelect, onClose]
  );

  // Add keyboard listener
  useEffect(() => {
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  // Group filtered skills by tier
  const groupedSkills: { tier: SkillTier; skills: Skill[] }[] = [];
  const coreSkills = filteredSkills.filter((s) => s.tier === 'core');
  const betaSkills = filteredSkills.filter((s) => s.tier === 'beta');

  if (coreSkills.length > 0) {
    groupedSkills.push({ tier: 'core', skills: coreSkills });
  }
  if (betaSkills.length > 0) {
    groupedSkills.push({ tier: 'beta', skills: betaSkills });
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
          <span>Skills</span>
          {query && (
            <>
              <ChevronRight className="w-3 h-3" />
              <span className="text-foreground font-medium">/{query}</span>
            </>
          )}
        </div>
      </div>

      {/* Skill list */}
      <div ref={listRef} className="max-h-64 overflow-y-auto p-1">
        {isLoading ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            Loading skills...
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            No matching skills
          </div>
        ) : (
          groupedSkills.map(({ tier, skills: tierSkills }) => {
            const config = TIER_CONFIG[tier];
            const TierIcon = config.icon;

            return (
              <div key={tier}>
                {/* Tier header */}
                <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  <TierIcon className={cn('w-3 h-3', config.className)} />
                  <span>{config.label}</span>
                </div>

                {/* Skills in tier */}
                {tierSkills.map((skill) => {
                  flatIndex++;
                  const isSelected = flatIndex === selectedIndex;
                  const itemIndex = flatIndex;

                  return (
                    <button
                      key={skill.command}
                      data-skill-item
                      onClick={() => onSelect(skill.command)}
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
                            {skill.command}
                          </span>
                          {tier === 'beta' && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 font-medium">
                              Beta
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {skill.description}
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
