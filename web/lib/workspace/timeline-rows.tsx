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
 *
 * ⭐ ADR-660 — the words live in the catalog, not in this module: a
 * module-level word table is evaluated at import, before any member's
 * language is known. The grammar is a HOOK (`useTimelineRows`), so a row's
 * whole sentence is one ICU message (`{who} updated {what}`) rather than a
 * concatenation that fixes English word order.
 */

import { useTranslations } from 'next-intl';
import { FilePenLine, Zap, Hexagon, UserPlus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useProposalLabels } from '@/lib/proposal-labels';
import { cn } from '@/lib/utils';

/** The catalog namespace the timeline grammar's words live under. */
export const TIMELINE_ROWS_NS = 'supervisor.timeline';

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
  if (entry.kind === 'membership') {
    // ADR-608 — a colleague joined the commons.
    return <UserPlus className="h-3 w-3 text-muted-foreground/60 shrink-0" />;
  }
  return <Hexagon className="h-3 w-3 text-muted-foreground/60 shrink-0" />;
}

/** The path's basename — revision rows title on the file, path as secondary. */
export function basename(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

/** ADR-410 D4 — the engine enum values that carry an operator word. The wake-
 * source / trigger values ride in invocation `detail` strings ("judgment ·
 * cron_tick"); they never render verbatim. A token absent from here degrades
 * to its de-underscored spelling. */
const ENUM_TOKENS: readonly string[] = [
  'cron_tick',
  'addressed',
  'proposal_arrival',
  'substrate_event',
  'manual_fire',
];

/** The proposal / invocation status values the catalog names. */
const STATUS_TOKENS: readonly string[] = [
  'pending',
  'approved',
  'executed',
  'rejected',
  'expired',
  'failed',
  'success',
  'skipped',
];

/**
 * The shared timeline grammar, worded. One hook so the bell, the workbench
 * and the boundary ledger cannot drift into three spellings of one row.
 */
export function useTimelineRows() {
  const t = useTranslations(TIMELINE_ROWS_NS);
  const { actionLabel } = useProposalLabels();

  const humanizeDetail = (detail: string): string =>
    detail
      .split('·')
      .map((part) => {
        const token = part.trim();
        return ENUM_TOKENS.includes(token) ? t(`enum.${token}`) : token.replace(/_/g, ' ');
      })
      .filter(Boolean)
      .join(' · ');

  const statusWord = (status: string): string =>
    STATUS_TOKENS.includes(status) ? t(`status.${status}`) : status.replace(/_/g, ' ');

  /** Proposal rows carry structured `primitive`/`family` — map them to operator
   *  words via the shared labeler (ADR-410 D4: primitive slugs never render). */
  const proposalLabel = (entry: {
    primitive?: string | null;
    family?: string | null;
  }): string => {
    if (!entry.primitive) return t('anAction');
    return actionLabel({
      primitive: entry.primitive,
      family: entry.family ?? undefined,
    });
  };

  /** The row's secondary line: revision → path; proposal → status (+ witness);
   *  invocation → humanized detail with a subtle status. The witness label is
   *  resolved by the CALLER (viewer-aware where the mount has a viewer). */
  const secondaryLine = (
    entry: TimelineEntry,
    opts?: { witnessLabel?: (decidedBy: string) => string },
  ): { text: string; destructive: boolean } | null => {
    if (entry.kind === 'revision') {
      return entry.path ? { text: entry.path, destructive: false } : null;
    }
    if (entry.kind === 'proposal') {
      const parts: string[] = [];
      if (entry.status) parts.push(statusWord(entry.status));
      if (entry.decided_by) {
        // ADR-405: the after-the-fact witness, attributed.
        const label = opts?.witnessLabel
          ? opts.witnessLabel(entry.decided_by)
          : entry.decided_by;
        parts.push(t('witnessedBy', { who: label }));
      }
      if (entry.detail) parts.push(humanizeDetail(entry.detail));
      return parts.length > 0 ? { text: parts.join(' · '), destructive: false } : null;
    }
    // invocation — status subtly, failed reads destructive.
    const parts: string[] = [];
    if (entry.status) parts.push(statusWord(entry.status));
    if (entry.detail) parts.push(humanizeDetail(entry.detail));
    return parts.length > 0
      ? { text: parts.join(' · '), destructive: entry.status === 'failed' }
      : null;
  };

  const rowTitle = (entry: TimelineEntry): string => {
    if (entry.kind === 'revision' && entry.path) return basename(entry.path);
    if (entry.kind === 'proposal') return proposalLabel(entry);
    return entry.title ?? entry.slug ?? entry.kind;
  };

  /** ADR-410 D4 — the actor-first prose line ("‹who› updated ‹file›",
   *  "‹who› ran ‹Title›", "‹who› proposed ‹Action›"). The `who` label is
   *  viewer-resolved by the mount (resolveActorForViewer). Shared by the bell
   *  and the Notifications workbench — one grammar, N mounts. */
  const actorLine = (
    entry: {
      kind: string;
      title?: string | null;
      path?: string | null;
      slug?: string | null;
      primitive?: string | null;
      family?: string | null;
    },
    who: string,
  ): string => {
    if (entry.kind === 'revision') {
      const base = basename(entry.path || entry.title || '') || t('aFile');
      return t('updated', { who, what: base });
    }
    if (entry.kind === 'proposal') {
      return t('proposed', { who, what: proposalLabel(entry) });
    }
    if (entry.kind === 'membership') {
      // ADR-608 — the server's title IS the sentence tail ("joined the
      // workspace"); the viewer layer resolved `who`.
      return t('membership', { who, tail: entry.title || t('joinedWorkspace') });
    }
    const title = (entry.title || entry.slug || t('work'))
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
    return t('ran', { who, what: title });
  };

  return { humanizeDetail, secondaryLine, rowTitle, actorLine };
}
