/**
 * WorkModeBadge — Renders a task's cadence as a user-facing label.
 *
 * Derives Recurring vs One-time from the task's `schedule` field, not
 * the internal `mode`. A task with a schedule is Recurring; a task
 * without one (or with "on-demand") is One-time. The execution mode
 * (recurring/goal/reactive) is an internal concern — users never see it.
 */

import { cn } from '@/lib/utils';
import { taskModeLabel } from '@/types';

interface WorkModeBadgeProps {
  schedule: string | undefined | null;
  className?: string;
}

export function WorkModeBadge({ schedule, className }: WorkModeBadgeProps) {
  const label = taskModeLabel(schedule);
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
