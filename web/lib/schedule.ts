/**
 * Schedule cadence classification — ADR-243.
 *
 * Extends the binary `recurrenceLabel(schedule)` helper (which returns
 * `'Recurring' | 'One-time'` for the badge on /work) into the three-way
 * temporal taxonomy used by /schedule's list sections.
 *
 *   recurring — recurrence has a non-empty schedule (anything other than
 *               null/empty/'on-demand'). Cadence-driven.
 *   reactive  — no schedule AND shape === 'action'. Fires on platform
 *               events; not a cadence.
 *   one-time  — no schedule AND shape !== 'action'. Goal-mode; runs
 *               once and completes.
 */

import type { Recurrence } from '@/types';

export type CadenceCategory = 'recurring' | 'reactive' | 'one-time';

/** Section render order on /schedule. */
export const CADENCE_ORDER: readonly CadenceCategory[] = [
  'recurring',
  'reactive',
  'one-time',
] as const;

export const CADENCE_LABELS: Record<CadenceCategory, { title: string; description: string }> = {
  recurring: {
    title: 'Recurring',
    description: 'Runs on a cadence (daily, weekly, custom).',
  },
  reactive: {
    title: 'Reactive',
    description: 'Fires on platform events — no fixed cadence.',
  },
  'one-time': {
    title: 'One-time',
    description: 'Runs once and completes.',
  },
};

/**
 * Classify a recurrence by its temporal flavor.
 * Mirrors the `recurrenceLabel()` rule for "recurring" so the badge on /work
 * and the section on /schedule stay in agreement.
 */
export function cadenceCategory(recurrence: Recurrence): CadenceCategory {
  const schedule = recurrence.schedule?.trim().toLowerCase();
  if (schedule && schedule !== 'on-demand') return 'recurring';
  if (recurrence.shape === 'action') return 'reactive';
  return 'one-time';
}

/**
 * Humanize a schedule string for display in list rows.
 * Cron expressions are recognized loosely; everything else is title-cased.
 * Reactive and one-time recurrences pass an empty/undefined schedule and
 * get rendered with their cadence-category label by the caller, not here.
 */
export function humanizeSchedule(schedule: string | undefined | null): string {
  if (!schedule) return '';
  const s = schedule.trim();
  if (!s) return '';
  // Plain words (daily, weekly, hourly, monthly, every-monday, ...)
  if (/^[a-z][a-z0-9-]*$/i.test(s)) {
    return s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ');
  }
  // Cron-like: 5 fields → "Custom"
  if (/^(\*|[\d\/,-]+)(\s+(\*|[\d\/,-]+)){4}$/.test(s)) return 'Custom';
  return s;
}
