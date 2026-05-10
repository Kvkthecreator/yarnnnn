/**
 * Schedule cadence classification — ADR-243 + Phase I post-merge sweep
 * (2026-05-10).
 *
 * Phase I: per ADR-261 D1 there is no `shape` field on a recurrence —
 * a recurrence is `{slug, schedule, prompt}`. The legacy 3-way taxonomy
 * (recurring / reactive / one-time) which distinguished reactive from
 * one-time via the now-deleted `shape === 'action'` axis collapses to
 * a 2-way split:
 *
 *   recurring — recurrence has a non-empty schedule. Cadence-driven.
 *   reactive  — recurrence has no schedule. Fires on event (operator
 *               via FireInvocation, proposal arrival, etc.).
 *
 * The `one-time` category is folded into `reactive` — operator-facing,
 * both shapes "fire when triggered, not on a clock," and the prompt
 * itself encodes whether the work is repeatable.
 */

import type { Recurrence } from '@/types';

export type CadenceCategory = 'recurring' | 'reactive';

/** Section render order on /schedule. */
export const CADENCE_ORDER: readonly CadenceCategory[] = [
  'recurring',
  'reactive',
] as const;

export const CADENCE_LABELS: Record<CadenceCategory, { title: string; description: string }> = {
  recurring: {
    title: 'Recurring',
    description: 'Runs on a cadence (daily, weekly, custom).',
  },
  reactive: {
    title: 'Reactive',
    description: 'Fires on event — operator trigger, proposal arrival, or named via the recurrence prompt.',
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
  return 'reactive';
}

/**
 * Humanize a schedule string for display in list rows.
 * Cron expressions are recognized loosely; everything else is title-cased.
 * Reactive recurrences pass an empty/undefined schedule and get rendered
 * with their cadence-category label by the caller, not here.
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
