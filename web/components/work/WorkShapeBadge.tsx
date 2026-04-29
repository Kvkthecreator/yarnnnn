/**
 * WorkShapeBadge — Renders a recurrence's cadence as a user-facing label.
 *
 * Derives Recurring vs One-time from the recurrence's `schedule` field. A
 * recurrence with a schedule is Recurring; one without (or with "on-demand")
 * is One-time. ADR-231 sunset internal mode/output_kind plumbing — the badge
 * speaks shape × cadence, not legacy task abstractions.
 */

import { cn } from '@/lib/utils';
import { recurrenceLabel } from '@/types';

interface WorkShapeBadgeProps {
  schedule: string | undefined | null;
  className?: string;
}

export function WorkShapeBadge({ schedule, className }: WorkShapeBadgeProps) {
  const label = recurrenceLabel(schedule);
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
