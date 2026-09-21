'use client';

/**
 * RevisionFootnote — shared "Updated X by Y" line for workspace concept cards.
 *
 * Per ADR-266 D7. Reads ADR-209 revision metadata and renders a single
 * muted line under the card title. Intentionally minimal: one line,
 * never wraps, never blocks layout. Returns null when no revision is
 * available (graceful degradation).
 */

import { useTranslations } from 'next-intl';

import type { WorkspaceRevisionSummary } from '@/types';

type T = ReturnType<typeof useTranslations<'workspaceSettings.revision'>>;

function relativeTime(iso: string, t: T): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  if (Number.isNaN(then)) return '';
  const sec = Math.max(0, Math.round((now - then) / 1000));
  if (sec < 60) return t('time.justNow');
  const min = Math.round(sec / 60);
  if (min < 60) return t('time.minutes', { n: min });
  const hr = Math.round(min / 60);
  if (hr < 24) return t('time.hours', { n: hr });
  const days = Math.round(hr / 24);
  if (days < 7) return t('time.days', { n: days });
  const weeks = Math.round(days / 7);
  if (weeks < 5) return t('time.weeks', { n: weeks });
  const months = Math.round(days / 30);
  return t('time.months', { n: months });
}

/** Map ADR-209 authored_by taxonomy (operator | yarnnn:* | agent:* |
 *  reviewer:* | system:*) to a short operator-facing label. */
function authorLabel(authoredBy: string, t: T): string {
  if (authoredBy === 'operator') return t('author.you');
  if (authoredBy.startsWith('yarnnn:')) return t('author.yarnnn');
  // ADR-381/251 relabel-keep-slug: `freddie:` slug → operator-facing "Freddie".
  if (authoredBy.startsWith('freddie:')) return t('author.freddie');
  if (authoredBy.startsWith('agent:')) return authoredBy.slice('agent:'.length);
  if (authoredBy.startsWith('system:bundle-fork')) return t('author.programActivation');
  if (authoredBy.startsWith('system:')) return t('author.system');
  return authoredBy;
}

export function RevisionFootnote({
  revision,
  className,
}: {
  revision: WorkspaceRevisionSummary | null;
  className?: string;
}) {
  const t = useTranslations('workspaceSettings.revision');
  if (!revision) return null;
  const when = relativeTime(revision.created_at, t);
  const who = authorLabel(revision.authored_by, t);
  return (
    <p className={`text-[11px] text-muted-foreground/60 ${className ?? ''}`}>
      {t('line', { when, who })}
    </p>
  );
}
