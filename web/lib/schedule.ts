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
    description: 'Runs when something happens — you ask, a decision comes in, or a scheduled prompt calls for it.',
  },
};

/**
 * Schedule shape accepted across the FE — single string, list of strings,
 * or null/undefined. Per ADR-268, list-form represents multiple fires per
 * day on a single recurrence (e.g. `track-universe` snapshots open + mid +
 * close). All FE consumers normalize via the helpers below; no caller
 * directly destructures the field.
 */
export type ScheduleValue = string | string[] | undefined | null;

/**
 * Reduce a list-or-string schedule to the first non-empty member as a
 * string. Used internally by the display + classification helpers.
 * Returns null when the value is empty/missing.
 */
function _firstScheduleString(schedule: ScheduleValue): string | null {
  if (!schedule) return null;
  if (Array.isArray(schedule)) {
    for (const s of schedule) {
      if (typeof s === 'string' && s.trim()) return s.trim();
    }
    return null;
  }
  const s = String(schedule).trim();
  return s ? s : null;
}

/**
 * Classify a recurrence by its temporal flavor.
 * Mirrors the `recurrenceLabel()` rule for "recurring" so the badge on /work
 * and the section on /schedule stay in agreement.
 * ADR-268: handles both string and list-of-strings.
 */
export function cadenceCategory(recurrence: Recurrence): CadenceCategory {
  const first = _firstScheduleString(recurrence.schedule)?.toLowerCase();
  if (first && first !== 'on-demand') return 'recurring';
  return 'reactive';
}

/**
 * Humanize a schedule string for display in list rows.
 * Cron expressions are recognized loosely; everything else is title-cased.
 * Reactive recurrences pass an empty/undefined schedule and get rendered
 * with their cadence-category label by the caller, not here.
 *
 * ADR-268: list-form returns a count-suffixed shape ("3× daily" plus the
 * first member humanized) so the operator sees the multi-fire intent at
 * a glance without the row growing unbounded.
 */
/**
 * Title-case a recurrence/execution slug for display.
 * "pre-ship-audit" → "Pre Ship Audit", "addressed" → "Addressed".
 * Used by the Usage tab spend breakdown + any surface listing raw slugs.
 */
export function humanizeSlug(slug: string): string {
  return slug
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function humanizeSchedule(schedule: ScheduleValue): string {
  if (Array.isArray(schedule)) {
    const filtered = schedule.filter((s): s is string => typeof s === 'string' && !!s.trim());
    if (filtered.length === 0) return '';
    if (filtered.length === 1) return _humanizeOne(filtered[0]);
    // Multi-fire: "3× · first humanized" — compact, surfaces intent
    return `${filtered.length}× · ${_humanizeOne(filtered[0])}`;
  }
  return _humanizeOne(schedule);
}

function _humanizeOne(schedule: string | undefined | null): string {
  if (!schedule) return '';
  const s = schedule.trim();
  if (!s) return '';
  // ADR-268: @-prefixed semantic — pass through cleanly (operator-readable).
  if (s.startsWith('@')) return s;
  // Plain words (daily, weekly, hourly, monthly, every-monday, ...)
  if (/^[a-z][a-z0-9-]*$/i.test(s)) {
    return s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ');
  }
  // Cron-like: 5 fields → "Custom"
  if (/^(\*|[\d\/,-]+)(\s+(\*|[\d\/,-]+)){4}$/.test(s)) return 'Custom';
  return s;
}

/**
 * The canonical display reducer for ADR-268 list-or-string schedules.
 * Use this anywhere you'd previously have rendered `{task.schedule}`
 * directly. Returns "" when the schedule is missing.
 */
export function scheduleDisplay(schedule: ScheduleValue): string {
  return humanizeSchedule(schedule);
}
