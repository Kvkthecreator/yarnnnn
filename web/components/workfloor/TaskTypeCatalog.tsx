'use client';

/**
 * TaskTypeCatalog — ADR-145 Gate 3: Deliverable type catalog grid.
 *
 * Shows available task types as cards grouped by category.
 * Clicking a card fires onSelectType callback to pre-fill chat.
 * Used as workfloor TasksTab empty state and via "+ Add deliverable" button.
 */

import { useState, useEffect } from 'react';
import { Loader2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { roleBadgeColor, roleDisplayName } from '@/lib/agent-identity';
import type { TaskType } from '@/types';

// Category display config
const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  intelligence: { label: 'Intelligence', color: 'text-blue-600 dark:text-blue-400' },
  operations: { label: 'Operations', color: 'text-amber-600 dark:text-amber-400' },
  platform: { label: 'Platform', color: 'text-teal-600 dark:text-teal-400' },
  content: { label: 'Content', color: 'text-purple-600 dark:text-purple-400' },
  tracking: { label: 'Tracking', color: 'text-pink-600 dark:text-pink-400' },
};

// Schedule badge labels
const SCHEDULE_LABELS: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  biweekly: 'Bi-weekly',
  monthly: 'Monthly',
  'on-demand': 'On demand',
};

function PipelinePreview({ steps }: { steps: Array<{ agent_type: string; step: string }> }) {
  if (!steps || steps.length === 0) return null;
  return (
    <div className="flex items-center gap-1 text-[9px] text-muted-foreground/50">
      {steps.map((s, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ArrowRight className="w-2.5 h-2.5" />}
          <span className={cn('px-1.5 py-0.5 rounded-sm', roleBadgeColor(s.agent_type))}>
            {s.step}
          </span>
        </span>
      ))}
    </div>
  );
}

function TypeCard({
  type,
  onSelect,
}: {
  type: TaskType;
  onSelect: (typeKey: string, displayName: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(type.type_key, type.display_name)}
      className="text-left p-3 rounded-lg border border-border/50 hover:border-primary/30 hover:bg-primary/5 transition-all group"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p className="text-xs font-medium group-hover:text-primary transition-colors leading-tight">
          {type.display_name}
        </p>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground/60 shrink-0">
          {SCHEDULE_LABELS[type.default_schedule] || type.default_schedule}
        </span>
      </div>
      <p className="text-[10px] text-muted-foreground/50 leading-relaxed mb-2 line-clamp-2">
        {type.description}
      </p>
      <div className="flex items-center justify-between">
        <PipelinePreview steps={type.pipeline_summary} />
        {type.requires_platform && (
          <span className="text-[8px] px-1 py-0.5 rounded bg-muted/50 text-muted-foreground/40">
            requires {type.requires_platform}
          </span>
        )}
      </div>
    </button>
  );
}

export function TaskTypeCatalog({
  onSelectType,
  compact = false,
}: {
  onSelectType: (typeKey: string, displayName: string) => void;
  compact?: boolean;
}) {
  const [types, setTypes] = useState<TaskType[]>([]);
  const [categories, setCategories] = useState<Array<{ key: string; display_name: string }>>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.tasks.listTypes()
      .then(res => {
        setTypes(res.types || []);
        setCategories(res.categories || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const filtered = selectedCategory
    ? types.filter(t => t.category === selectedCategory)
    : types;

  return (
    <div className="space-y-3">
      {!compact && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">
            What do you want delivered?
          </p>
          <p className="text-[10px] text-muted-foreground/40">
            Pick a deliverable type or describe what you need in chat
          </p>
        </div>
      )}

      {/* Category filter */}
      <div className="flex gap-1 flex-wrap">
        <button
          onClick={() => setSelectedCategory(null)}
          className={cn(
            'px-2 py-0.5 text-[10px] rounded-md transition-colors',
            !selectedCategory ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground/40 hover:text-muted-foreground/70'
          )}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat.key}
            onClick={() => setSelectedCategory(cat.key === selectedCategory ? null : cat.key)}
            className={cn(
              'px-2 py-0.5 text-[10px] rounded-md transition-colors',
              selectedCategory === cat.key
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground/40 hover:text-muted-foreground/70'
            )}
          >
            {CATEGORY_LABELS[cat.key]?.label || cat.display_name}
          </button>
        ))}
      </div>

      {/* Card grid */}
      <div className={cn(
        'grid gap-2',
        compact ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'
      )}>
        {filtered.map(type => (
          <TypeCard key={type.type_key} type={type} onSelect={onSelectType} />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-[10px] text-muted-foreground/30 text-center py-3">
          No deliverable types in this category
        </p>
      )}
    </div>
  );
}
