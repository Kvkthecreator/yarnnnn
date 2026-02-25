'use client';

import * as React from 'react';
import { useState, useEffect, useRef } from 'react';
import {
  Mail,
  Slack,
  FileCode,
  Calendar,
  ChevronDown,
  Check,
  X,
  Filter,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * ADR-033 Phase 3: Platform Filter Component
 *
 * Reusable dropdown for filtering by platform.
 * Used in Context Browser and Deliverable List surfaces.
 */

export type PlatformFilterValue = 'all' | 'slack' | 'notion' | 'gmail' | 'calendar';

interface PlatformFilterProps {
  value: PlatformFilterValue;
  onChange: (value: PlatformFilterValue) => void;
  /** Available platforms to show in dropdown (defaults to all) */
  availablePlatforms?: PlatformFilterValue[];
  /** Optional counts per platform */
  counts?: Partial<Record<PlatformFilterValue, number>>;
  /** Compact mode for smaller spaces */
  compact?: boolean;
  className?: string;
}

const PLATFORM_CONFIG: Record<
  Exclude<PlatformFilterValue, 'all'>,
  { icon: React.ReactNode; label: string; color: string }
> = {
  slack: {
    icon: <Slack className="w-3.5 h-3.5" />,
    label: 'Slack',
    color: 'text-purple-500',
  },
  notion: {
    icon: <FileCode className="w-3.5 h-3.5" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
  },
  gmail: {
    icon: <Mail className="w-3.5 h-3.5" />,
    label: 'Gmail',
    color: 'text-red-500',
  },
  calendar: {
    icon: <Calendar className="w-3.5 h-3.5" />,
    label: 'Calendar',
    color: 'text-blue-500',
  },
};

export function PlatformFilter({
  value,
  onChange,
  availablePlatforms = ['all', 'slack', 'notion', 'gmail', 'calendar'],
  counts,
  compact = false,
  className,
}: PlatformFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getLabel = () => {
    if (value === 'all') return 'All platforms';
    return PLATFORM_CONFIG[value]?.label || value;
  };

  const getIcon = () => {
    if (value === 'all') return <Filter className="w-3.5 h-3.5" />;
    return PLATFORM_CONFIG[value]?.icon;
  };

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md',
          'bg-background hover:bg-muted transition-colors',
          value !== 'all' && 'border-primary/50 bg-primary/5'
        )}
      >
        {getIcon()}
        {!compact && <span>{getLabel()}</span>}
        {value !== 'all' && !compact && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onChange('all');
            }}
            className="ml-1 p-0.5 hover:bg-muted rounded"
          >
            <X className="w-3 h-3" />
          </button>
        )}
        <ChevronDown
          className={cn('w-3.5 h-3.5 transition-transform', isOpen && 'rotate-180')}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-background border border-border rounded-md shadow-lg z-50 py-1">
          {/* All option */}
          <button
            onClick={() => {
              onChange('all');
              setIsOpen(false);
            }}
            className={cn(
              'w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center justify-between gap-2',
              value === 'all' && 'bg-muted/50'
            )}
          >
            <span className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-muted-foreground" />
              All platforms
            </span>
            {value === 'all' && <Check className="w-3.5 h-3.5 text-primary" />}
          </button>

          <div className="border-t border-border my-1" />

          {/* Platform options */}
          {availablePlatforms
            .filter((p) => p !== 'all')
            .map((platform) => {
              const config = PLATFORM_CONFIG[platform as Exclude<PlatformFilterValue, 'all'>];
              if (!config) return null;

              const count = counts?.[platform];

              return (
                <button
                  key={platform}
                  onClick={() => {
                    onChange(platform);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center justify-between gap-2',
                    value === platform && 'bg-muted/50'
                  )}
                >
                  <span className={cn('flex items-center gap-2', config.color)}>
                    {config.icon}
                    {config.label}
                    {count !== undefined && (
                      <span className="text-xs text-muted-foreground">({count})</span>
                    )}
                  </span>
                  {value === platform && <Check className="w-3.5 h-3.5 text-primary" />}
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}

/**
 * Chip-style platform filter for inline use
 */
export function PlatformFilterChips({
  value,
  onChange,
  availablePlatforms = ['all', 'slack', 'notion', 'gmail', 'calendar'],
  counts,
  className,
}: Omit<PlatformFilterProps, 'compact'>) {
  return (
    <div className={cn('flex items-center gap-1.5 flex-wrap', className)}>
      {/* All chip */}
      <button
        onClick={() => onChange('all')}
        className={cn(
          'px-2 py-1 text-xs rounded-md transition-colors',
          value === 'all'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted hover:bg-muted/80 text-muted-foreground'
        )}
      >
        All{counts?.all !== undefined && ` (${counts.all})`}
      </button>

      {/* Platform chips */}
      {availablePlatforms
        .filter((p) => p !== 'all')
        .map((platform) => {
          const config = PLATFORM_CONFIG[platform as Exclude<PlatformFilterValue, 'all'>];
          if (!config) return null;

          const count = counts?.[platform];

          return (
            <button
              key={platform}
              onClick={() => onChange(platform)}
              className={cn(
                'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors',
                value === platform
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80 text-muted-foreground'
              )}
            >
              {config.icon}
              {config.label}
              {count !== undefined && ` (${count})`}
            </button>
          );
        })}
    </div>
  );
}
