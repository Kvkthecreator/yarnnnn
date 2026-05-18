/**
 * DaySeparator — Feed timeline date anchor (ADR-289).
 *
 * The Feed is asynchronous and multi-day; without date anchors a stack
 * of timestamp-only rows reads as a confusing log. Renders as a small
 * centered label between adjacent invocation cards / events whose
 * created_at days differ.
 *
 * Pure presentation — derived at render time from FeedUnit.timestamp.
 */

'use client';

interface DaySeparatorProps {
  date: Date;
}

export function DaySeparator({ date }: DaySeparatorProps) {
  const today = new Date();
  const sameDay =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();

  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();

  let label: string;
  if (sameDay) {
    label = 'Today';
  } else if (isYesterday) {
    label = 'Yesterday';
  } else {
    label = date.toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
    });
  }

  return (
    <div className="flex items-center gap-2 my-2 px-1">
      <div className="flex-1 h-px bg-border/40" />
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
        {label}
      </span>
      <div className="flex-1 h-px bg-border/40" />
    </div>
  );
}
