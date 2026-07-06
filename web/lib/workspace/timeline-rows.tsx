'use client';

/**
 * Timeline row primitives — the ONE render grammar for workspace-timeline
 * entries (ADR-408 D5.1 source; ADR-340 D8 one-body discipline).
 *
 * Extracted from the Home Timeline slot (WorkspaceTimeline) when ADR-410 D5
 * re-mounted the Notifications workbench on the same derivation: the glyph,
 * title, and secondary-line grammar are shared; each mount picks its own
 * depth (Home slot = ambient glance, workbench = filters + full history,
 * bell = peer-first head).
 *
 * ADR-410 D4 vocabulary: internal enum words (wake-source values, mode
 * slugs) are mapped to operator words HERE, at the shared layer — no mount
 * renders an engine enum.
 */

import { FilePenLine, Zap, Hexagon } from 'lucide-react';
import { api } from '@/lib/api/client';
import { proposalActionLabel } from '@/lib/proposal-labels';
import { cn } from '@/lib/utils';

export type TimelineEntry = Awaited<
  ReturnType<typeof api.workspace.timeline>
>['entries'][number];

/** Kind glyph — the act's class at a glance (mirrors sibling icon grammar:
 * revisions = the Files pen, invocations = a run, proposals = the ProposalCard
 * hexagon). */
export function KindGlyph({ entry }: { entry: TimelineEntry }) {
  if (entry.kind === 'revision') {
    return <FilePenLine className="h-3 w-3 text-muted-foreground/60 shrink-0" />;
  }
  if (entry.kind === 'invocation') {
    return (
      <Zap
        className={cn(
          'h-3 w-3 shrink-0',
          entry.status === 'failed' ? 'text-destructive/70' : 'text-muted-foreground/60',
        )}
      />
    );
  }
  return <Hexagon className="h-3 w-3 text-muted-foreground/60 shrink-0" />;
}

/** The path's basename — revision rows title on the file, path as secondary. */
export function basename(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

/** ADR-410 D4 — engine enum → operator word. The wake-source / trigger
 * values ride in invocation `detail` strings ("judgment · cron_tick");
 * they never render verbatim. */
const ENUM_WORDS: Record<string, string> = {
  cron_tick: 'scheduled',
  addressed: 'addressed',
  proposal_arrival: 'proposal',
  substrate_event: 'substrate change',
  manual_fire: 'run manually',
};

export function humanizeDetail(detail: string): string {
  return detail
    .split('·')
    .map((part) => {
      const token = part.trim();
      return ENUM_WORDS[token] ?? token.replace(/_/g, ' ');
    })
    .filter(Boolean)
    .join(' · ');
}

/** The row's secondary line: revision → path; proposal → status (+ witness);
 * invocation → humanized detail with a subtle status. The witness label is
 * resolved by the CALLER (viewer-aware where the mount has a viewer). */
export function secondaryLine(
  entry: TimelineEntry,
  opts?: { witnessLabel?: (decidedBy: string) => string },
): { text: string; destructive: boolean } | null {
  if (entry.kind === 'revision') {
    return entry.path ? { text: entry.path, destructive: false } : null;
  }
  if (entry.kind === 'proposal') {
    const parts: string[] = [];
    if (entry.status) parts.push(entry.status);
    if (entry.decided_by) {
      // ADR-405: the after-the-fact witness, attributed.
      const label = opts?.witnessLabel
        ? opts.witnessLabel(entry.decided_by)
        : entry.decided_by;
      parts.push(`witnessed by ${label}`);
    }
    if (entry.detail) parts.push(humanizeDetail(entry.detail));
    return parts.length > 0 ? { text: parts.join(' · '), destructive: false } : null;
  }
  // invocation — status subtly, failed reads destructive.
  const parts: string[] = [];
  if (entry.status) parts.push(entry.status);
  if (entry.detail) parts.push(humanizeDetail(entry.detail));
  return parts.length > 0
    ? { text: parts.join(' · '), destructive: entry.status === 'failed' }
    : null;
}

/** The timeline's proposal title arrives as "primitive (family)" — map it to
 * operator words via the shared labeler (ADR-410 D4: primitive slugs never
 * render). */
export function proposalTitleFromTimeline(title: string | null | undefined): string {
  if (!title) return 'an action';
  const m = title.match(/^(.*?)\s*\(([\w-]+)\)\s*$/);
  const primitive = m ? m[1] : title;
  const family = m ? m[2] : undefined;
  return proposalActionLabel({ primitive, family });
}

export function rowTitle(entry: TimelineEntry): string {
  if (entry.kind === 'revision' && entry.path) return basename(entry.path);
  if (entry.kind === 'proposal') return proposalTitleFromTimeline(entry.title);
  return entry.title ?? entry.slug ?? entry.kind;
}

/** ADR-410 D4 — the actor-first prose line ("‹who› updated ‹file›",
 * "‹who› ran ‹Title›", "‹who› proposed ‹Action›"). The `who` label is
 * viewer-resolved by the mount (resolveActorForViewer). Shared by the bell
 * and the Notifications workbench — one grammar, N mounts. */
export function actorLine(
  entry: {
    kind: string;
    title?: string | null;
    path?: string | null;
    slug?: string | null;
  },
  who: string,
): string {
  if (entry.kind === 'revision') {
    const base = basename(entry.path || entry.title || '') || 'a file';
    return `${who} updated ${base}`;
  }
  if (entry.kind === 'proposal') {
    return `${who} proposed: ${proposalTitleFromTimeline(entry.title)}`;
  }
  const title = (entry.title || entry.slug || 'work')
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return `${who} ran ${title}`;
}
