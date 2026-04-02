'use client';

/**
 * TaskTreeNav — Left panel tree navigation for the unified task surface.
 *
 * Tasks as expandable tree items, each with virtual children:
 * Output (default), Task Definition, Deliverable Spec, Run History.
 */

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Circle,
  FileText,
  Target,
  Clock,
  Plus,
  ListChecks,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Task } from '@/types';

export type TaskView = 'output' | 'task-definition' | 'deliverable' | 'run-history';

interface TaskTreeNavProps {
  tasks: Task[];
  selectedSlug: string | null;
  selectedView: TaskView;
  filter: string | null;
  onFilterChange: (filter: string | null) => void;
  onSelectTask: (slug: string, view?: TaskView) => void;
  onSelectView: (view: TaskView) => void;
  onCreateTask?: () => void;
}

const VIEW_ITEMS: { id: TaskView; label: string; icon: typeof FileText }[] = [
  { id: 'output', label: 'Output', icon: FileText },
  { id: 'task-definition', label: 'Task Definition', icon: ListChecks },
  { id: 'deliverable', label: 'Deliverable Spec', icon: Target },
  { id: 'run-history', label: 'Run History', icon: Clock },
];

export function TaskTreeNav({
  tasks,
  selectedSlug,
  selectedView,
  filter,
  onFilterChange,
  onSelectTask,
  onSelectView,
  onCreateTask,
}: TaskTreeNavProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    // Auto-expand selected task
    if (selectedSlug) return { [selectedSlug]: true };
    return {};
  });

  const filtered = filter ? tasks.filter(t => t.status === filter) : tasks;

  const toggleExpand = (slug: string) => {
    setExpanded(prev => ({ ...prev, [slug]: !prev[slug] }));
  };

  const handleTaskClick = (slug: string) => {
    // Expand and select output view
    setExpanded(prev => ({ ...prev, [slug]: true }));
    onSelectTask(slug, 'output');
  };

  const statusCounts = {
    all: tasks.length,
    active: tasks.filter(t => t.status === 'active').length,
    paused: tasks.filter(t => t.status === 'paused').length,
  };

  return (
    <div className="flex flex-col h-full text-sm">
      {/* Compact filter pills */}
      <div className="flex gap-1 px-3 py-2 border-b border-border shrink-0">
        {[
          { key: null, label: 'All', count: statusCounts.all },
          { key: 'active', label: 'Active', count: statusCounts.active },
          { key: 'paused', label: 'Paused', count: statusCounts.paused },
        ].map(f => (
          <button
            key={f.key ?? 'all'}
            onClick={() => onFilterChange(f.key)}
            className={cn(
              'px-2 py-0.5 text-[11px] font-medium rounded-full transition-colors',
              filter === f.key
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {f.label} {f.count > 0 && <span className="opacity-50">{f.count}</span>}
          </button>
        ))}
      </div>

      {/* Task tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {filtered.length === 0 && (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            {tasks.length === 0 ? 'No tasks yet' : 'No matching tasks'}
          </div>
        )}

        {filtered.map(task => {
          const isSelected = task.slug === selectedSlug;
          const isExpanded = expanded[task.slug] || isSelected;
          const statusColor =
            task.status === 'active' ? 'fill-green-500 text-green-500' :
            task.status === 'paused' ? 'fill-amber-500 text-amber-500' :
            task.status === 'completed' ? 'fill-blue-500 text-blue-500' :
            'text-muted-foreground';

          return (
            <div key={task.slug}>
              {/* Task row */}
              <button
                onClick={() => handleTaskClick(task.slug)}
                className={cn(
                  'w-full flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-accent rounded-sm',
                  isSelected && 'bg-accent/50'
                )}
              >
                <button
                  onClick={(e) => { e.stopPropagation(); toggleExpand(task.slug); }}
                  className="p-0.5 shrink-0"
                >
                  {isExpanded
                    ? <ChevronDown className="w-3 h-3 text-muted-foreground" />
                    : <ChevronRight className="w-3 h-3 text-muted-foreground" />
                  }
                </button>
                <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
                <span className="truncate flex-1">{task.title}</span>
                {task.schedule && (
                  <span className="text-[10px] text-muted-foreground/50 shrink-0">{task.schedule}</span>
                )}
              </button>

              {/* Virtual children */}
              {isExpanded && (
                <div className="ml-4">
                  {VIEW_ITEMS.map(item => {
                    const Icon = item.icon;
                    const isViewSelected = isSelected && selectedView === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          onSelectTask(task.slug);
                          onSelectView(item.id);
                        }}
                        className={cn(
                          'w-full flex items-center gap-2 px-3 py-1 text-left text-sm rounded-sm hover:bg-accent',
                          isViewSelected
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground'
                        )}
                      >
                        <Icon className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* New task button */}
      {onCreateTask && (
        <div className="px-3 py-2 border-t border-border shrink-0">
          <button
            onClick={onCreateTask}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-accent rounded-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            New task
          </button>
        </div>
      )}
    </div>
  );
}
