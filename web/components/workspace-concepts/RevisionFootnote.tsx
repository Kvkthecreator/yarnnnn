'use client';

/**
 * RevisionFootnote — shared "Updated X by Y" line for workspace concept cards.
 *
 * Per ADR-266 D7. Reads ADR-209 revision metadata and renders a single
 * muted line under the card title. Intentionally minimal: one line,
 * never wraps, never blocks layout. Returns null when no revision is
 * available (graceful degradation).
 */

import type { WorkspaceRevisionSummary } from '@/types';

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  if (Number.isNaN(then)) return '';
  const sec = Math.max(0, Math.round((now - then) / 1000));
  if (sec < 60) return 'just now';
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.round(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  const months = Math.round(days / 30);
  return `${months}mo ago`;
}

/** Map ADR-209 authored_by taxonomy (operator | yarnnn:* | agent:* |
 *  reviewer:* | system:*) to a short operator-facing label. */
function authorLabel(authoredBy: string): string {
  if (authoredBy === 'operator') return 'you';
  if (authoredBy.startsWith('yarnnn:')) return 'YARNNN';
  if (authoredBy.startsWith('reviewer:')) return 'Reviewer';
  if (authoredBy.startsWith('agent:')) return authoredBy.slice('agent:'.length);
  if (authoredBy.startsWith('system:bundle-fork')) return 'program activation';
  if (authoredBy.startsWith('system:')) return 'system';
  return authoredBy;
}

export function RevisionFootnote({
  revision,
  className,
}: {
  revision: WorkspaceRevisionSummary | null;
  className?: string;
}) {
  if (!revision) return null;
  const when = relativeTime(revision.created_at);
  const who = authorLabel(revision.authored_by);
  return (
    <p className={`text-[11px] text-muted-foreground/60 ${className ?? ''}`}>
      Updated {when} by {who}
    </p>
  );
}
