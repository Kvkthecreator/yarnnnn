'use client';

/**
 * ActivityLedger — the Notifications workbench's ACTIVITY body (ADR-410 D5).
 *
 * The breadth mount of the ONE "what happened" derivation: the workspace
 * timeline (GET /api/workspace/timeline — the three attributed act ledgers,
 * ADR-408 D5.1). Bell = glance (peer-first head), Home slot = ambient,
 * THIS = the workbench: actor/kind/date filters + full history via the
 * endpoint's `before` cursor. Three depths, one source (ADR-367 tiering).
 *
 * It replaced the chat-narrative FeedSurface mount: post-ADR-407-Phase-4
 * the chat session is the viewer's PRIVATE thread, so a chat-derived
 * "Activity" showed the viewer their own turns and hid peers/agents — the
 * structural obsolescence ADR-410 §1 documents.
 *
 * Unlike the bell, the workbench shows EVERY act — including the viewer's
 * own, resolved to "You" (a workbench is where you audit the whole commons;
 * the bell's peer-only filter is a demand-attention rule, not a reading
 * rule). Rendering rides the shared timeline-row grammar + the viewer
 * resolution layer (ADR-412 D6); DP29: everything here is derived at read
 * time, nothing is stored.
 *
 * ADR-415 (2026-07-08): Activity is now the ONE "what happened" surface. The
 * dissolved Channels surface's Out (emissions) ledger folds in here as a
 * DIRECTION LENS — a Timeline/Out toggle. Timeline = the interior three-ledger
 * view (kind/actor/date filters). Out = EmissionsView (GET /api/emissions:
 * operator-addressing sends — channel · status · destination · did-it-land).
 * Out swaps the body wholesale rather than mapping emissions into revision
 * rows, because the delivery detail IS the value of Out (a unified row grammar
 * would gut it). Channels' In pane was retired — inbound writes already appear
 * in the timeline as attributed revisions.
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api/client';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';
import { formatLedgerTime, formatAbsolute } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { EmissionsView } from '@/components/context/EmissionsView';
import {
  useActorForViewer,
  useWorkspaceRoster,
} from '@/lib/workspace/viewer';
import {
  KindGlyph,
  useTimelineRows,
  type TimelineEntry,
} from '@/lib/workspace/timeline-rows';
import { useAuthorLabel } from '@/lib/workspace/useAuthorLabel';
import { cn } from '@/lib/utils';
import { Working } from '@/components/shared/Working';

const PAGE_SIZE = 60;

/** Operator words for the act kinds (never the engine enum — ADR-410 D4).
 *  ADR-660: the rows hold catalog KEYS — this table is evaluated at import,
 *  before any member's language is known. */
const KIND_FILTERS: Array<{ key: 'all' | TimelineEntry['kind']; labelKey: string }> = [
  { key: 'all', labelKey: 'kindAll' },
  { key: 'revision', labelKey: 'kindRevision' },
  { key: 'invocation', labelKey: 'kindInvocation' },
  { key: 'proposal', labelKey: 'kindProposal' },
];

// ADR-415 — the direction lens: the interior timeline vs the outbound
// emissions ledger (the dissolved Channels Out pane, re-homed).
type DirectionLens = 'timeline' | 'out';
const DIRECTION_LENSES: Array<{ key: DirectionLens; labelKey: string }> = [
  { key: 'timeline', labelKey: 'lensTimeline' },
  { key: 'out', labelKey: 'lensOut' },
];

// ADR-489 D2 — the weight lens (Axiom 9 rendering-weight taxonomy, derived
// server-side per entry). Default hides housekeeping (machine bookkeeping —
// index regens, `_*.yaml` state); the complete attributed record stays one
// click away. Missing weight reads material (fail-open).
type WeightLens = 'matters' | 'all';
const WEIGHT_LENSES: Array<{ key: WeightLens; labelKey: string }> = [
  { key: 'matters', labelKey: 'weightMatters' },
  { key: 'all', labelKey: 'weightAll' },
];

export function ActivityLedger() {
  const t = useTranslations('supervisor.activity');
  const { userId } = useSurfacePreferences();
  const roster = useWorkspaceRoster();
  // ADR-660 — the shared row grammar reads the catalog, so it is a hook.
  const { actorLine, secondaryLine } = useTimelineRows();
  const resolveActorForViewer = useActorForViewer();
  const { authorLabelOrSystem } = useAuthorLabel();

  // ADR-415 — Timeline (the three interior ledgers) vs Out (emissions).
  const [lens, setLens] = useState<DirectionLens>('timeline');

  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const [kindFilter, setKindFilter] = useState<'all' | TimelineEntry['kind']>('all');
  const [actorFilter, setActorFilter] = useState<string>('all');
  const [weightLens, setWeightLens] = useState<WeightLens>('matters');
  // Date filter = a jump of the `before` cursor (history from that day back).
  const [beforeDate, setBeforeDate] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const before = beforeDate ? `${beforeDate}T23:59:59.999Z` : undefined;
    api.workspace
      .timeline(PAGE_SIZE, before)
      .then((r) => {
        if (cancelled) return;
        setEntries(r.entries ?? []);
        setHasMore(!!r.has_more);
      })
      .catch(() => {
        if (!cancelled) {
          setEntries([]);
          setHasMore(false);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [beforeDate]);

  const loadMore = async () => {
    const oldest = entries[entries.length - 1]?.at;
    if (!oldest || loadingMore) return;
    setLoadingMore(true);
    try {
      const r = await api.workspace.timeline(PAGE_SIZE, oldest);
      setEntries((prev) => {
        const seen = new Set(prev.map((e) => e.id));
        return [...prev, ...(r.entries ?? []).filter((e) => !seen.has(e.id))];
      });
      setHasMore(!!r.has_more);
    } catch {
      setHasMore(false);
    } finally {
      setLoadingMore(false);
    }
  };

  // Viewer-resolved rows (ADR-412 D6 — "You" / peer names / agent labels).
  const resolved = useMemo(
    () =>
      entries.map((e) => ({
        e,
        who: resolveActorForViewer(e.actor, e.actor_id, userId, roster),
        actorKey: e.actor_id ?? e.actor ?? 'unknown',
      })),
    [entries, userId, roster, resolveActorForViewer],
  );

  // Actor filter options — derived from the loaded window (membership-shaped,
  // no separate store).
  const actorOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const { who, actorKey } of resolved) {
      if (!map.has(actorKey)) map.set(actorKey, who.label);
    }
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [resolved]);

  const visible = resolved.filter(({ e, actorKey, who }) => {
    // ADR-405 D4 / ADR-608 — you are not told about your own arrival. Scoped
    // to membership ONLY: this ledger is the full attributed record, so a
    // viewer's own file changes and runs must still show. The bell applies the
    // same rule peer-wide by construction (AttentionCenter — peer-first).
    if (e.kind === 'membership' && who.isSelf) return false;
    if (weightLens === 'matters' && e.weight === 'housekeeping') return false;
    if (kindFilter !== 'all' && e.kind !== kindFilter) return false;
    if (actorFilter !== 'all' && actorKey !== actorFilter) return false;
    return true;
  });

  return (
    <div className="flex h-full flex-col">
      {/* Filter bar. ADR-415 — the direction lens (Timeline / Out) leads;
          the timeline-specific filters (kind / actor / date, ADR-410 D5) show
          only in the Timeline lens (Out is the emissions ledger, a different
          shape). Kind + actor filter the loaded window client-side; the date
          jumps the server cursor. */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-6 py-2.5">
        <div className="flex items-center gap-1" role="group" aria-label={t('groupDirection')}>
          {DIRECTION_LENSES.map((l) => (
            <button
              key={l.key}
              type="button"
              onClick={() => setLens(l.key)}
              className={cn(
                'rounded-md px-2 py-1 text-[11px] transition-colors',
                lens === l.key
                  ? 'bg-foreground font-medium text-background'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
              )}
            >
              {t(l.labelKey)}
            </button>
          ))}
        </div>
        {lens === 'timeline' && (
          <>
            <span aria-hidden className="h-4 w-px bg-border/60" />
            <div className="flex items-center gap-1" role="group" aria-label={t('groupWeight')}>
              {WEIGHT_LENSES.map((w) => (
                <button
                  key={w.key}
                  type="button"
                  onClick={() => setWeightLens(w.key)}
                  className={cn(
                    'rounded-md px-2 py-1 text-[11px] transition-colors',
                    weightLens === w.key
                      ? 'bg-muted font-medium text-foreground'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )}
                >
                  {t(w.labelKey)}
                </button>
              ))}
            </div>
            <span aria-hidden className="h-4 w-px bg-border/60" />
            <div className="flex items-center gap-1" role="group" aria-label={t('groupKind')}>
              {KIND_FILTERS.map((k) => (
                <button
                  key={k.key}
                  type="button"
                  onClick={() => setKindFilter(k.key)}
                  className={cn(
                    'rounded-md px-2 py-1 text-[11px] transition-colors',
                    kindFilter === k.key
                      ? 'bg-muted font-medium text-foreground'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )}
                >
                  {t(k.labelKey)}
                </button>
              ))}
            </div>
            <select
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              aria-label={t('filterActor')}
              className="h-7 rounded-md border border-border bg-background px-1.5 text-[11px] text-foreground"
            >
              <option value="all">{t('everyone')}</option>
              {actorOptions.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              {t('upTo')}
              <input
                type="date"
                value={beforeDate}
                onChange={(e) => setBeforeDate(e.target.value)}
                aria-label={t('filterDate')}
                className="h-7 rounded-md border border-border bg-background px-1.5 text-[11px] text-foreground"
              />
            </label>
            {(kindFilter !== 'all' || actorFilter !== 'all' || beforeDate || weightLens !== 'matters') && (
              <button
                type="button"
                onClick={() => {
                  setKindFilter('all');
                  setActorFilter('all');
                  setBeforeDate('');
                  setWeightLens('matters');
                }}
                className="text-[11px] text-primary hover:underline"
              >
                {t('clear')}
              </button>
            )}
          </>
        )}
      </div>

      {/* ADR-415 — the Out lens is the emissions ledger (a different data
          source + row shape); it swaps the body wholesale. */}
      {lens === 'out' ? (
        <div className="flex-1 overflow-y-auto p-6">
          <EmissionsView />
        </div>
      ) : (
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <Working label={t('reading')} fill className="py-12" />
        ) : visible.length === 0 ? (
          <p className="px-6 py-8 text-sm text-muted-foreground">
            {entries.length > 0 ? t('emptyFiltered') : t('emptyYet')}
          </p>
        ) : (
          <ul className="divide-y divide-border/30">
            {visible.map(({ e, who }) => {
              const secondary = secondaryLine(e, {
                witnessLabel: (d) =>
                  resolveActorForViewer(d, null, userId, roster).label ||
                  authorLabelOrSystem(d),
              });
              const line = actorLine(e, who.label);
              return (
                <li
                  key={e.id}
                  className={cn(
                    'flex items-center gap-2.5 px-6 py-2.5',
                    // ADR-489 — housekeeping stays legible but recedes.
                    e.weight === 'housekeeping' && 'opacity-60',
                  )}
                >
                  <KindGlyph entry={e} />
                  <span className="flex-1 min-w-0">
                    {e.kind === 'revision' && e.path ? (
                      <SurfaceLink
                        to="files"
                        params={{ path: e.path }}
                        className="block truncate text-sm text-foreground hover:underline underline-offset-2"
                      >
                        {line}
                      </SurfaceLink>
                    ) : (
                      <span className="block truncate text-sm text-foreground">{line}</span>
                    )}
                    {secondary && (
                      <span
                        className={cn(
                          'block truncate text-[11px]',
                          secondary.destructive
                            ? 'text-destructive/70'
                            : 'text-muted-foreground/50',
                        )}
                      >
                        {secondary.text}
                      </span>
                    )}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {/* Icon only — the actor line already names the actor
                        viewer-resolved; the badge's generic label would
                        contradict it on member rows ("You via …" vs
                        "Member (via …)"). */}
                    <PrincipalBadge authoredBy={e.actor} fallbackToSystem showLabel={false} size={12} />
                    {e.at && (
                      <span
                        className="text-[11px] tabular-nums text-muted-foreground/50"
                        title={formatAbsolute(e.at)}
                      >
                        {formatLedgerTime(e.at)}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        )}

        {!loading && hasMore && (
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className="block w-full border-t border-border/30 px-6 py-2.5 text-left text-[11px] text-muted-foreground/70 transition-colors hover:bg-muted/30 hover:text-foreground disabled:opacity-50"
          >
            {loadingMore ? t('loadingMore') : t('loadOlder')}
          </button>
        )}
      </div>
      )}
    </div>
  );
}
