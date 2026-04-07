/**
 * WorkModeBadge — Renders a task's mode as a user-facing label.
 *
 * ADR-163: The schema has three modes (recurring | goal | reactive). The
 * surface has two (Recurring | One-time). Users see two. The execution
 * layer still uses three because goal has the revision loop and reactive
 * has dispatch-and-done semantics (see ADR-149).
 *
 * This component is the ONLY place modes get rendered in the UI. Every
 * other component that needs to show a mode should use this.
 */

import { cn } from '@/lib/utils';
import { taskModeLabel } from '@/types';

interface WorkModeBadgeProps {
  mode: string | undefined | null;
  className?: string;
}

export function WorkModeBadge({ mode, className }: WorkModeBadgeProps) {
  const label = taskModeLabel(mode);
  const isRecurring = label === 'Recurring';

  return (
    <span
      className={cn(
        'text-[10px] rounded-full px-1.5 py-0.5 font-medium',
        isRecurring
          ? 'bg-blue-500/10 text-blue-600'
          : 'bg-purple-500/10 text-purple-600',
        className,
      )}
    >
      {label}
    </span>
  );
}
