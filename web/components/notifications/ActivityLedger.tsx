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
 * structural obsolescence ADR-410 §1 documents. FeedSurface itself survives
 * at its Channels In mount (the boundary crossing-ledger).
 *
 * Unlike the bell, the workbench shows EVERY act — including the viewer's
 * own, resolved to "You" (a workbench is where you audit the whole commons;
 * the bell's peer-only filter is a demand-attention rule, not a reading
 * rule). Rendering rides the shared timeline-row grammar + the viewer
 * resolution layer (ADR-412 D6); DP29: everything here is derived at read
 * time, nothing is stored.
 */

import { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import {
  resolveActorForViewer,
  useWorkspaceRoster,
} from '@/lib/workspace/viewer';
import {
  KindGlyph,
  actorLine,
  secondaryLine,
  type TimelineEntry,
} from '@/lib/workspace/timeline-rows';
import { formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 60;

/** Operator words for the act kinds (never the engine enum — ADR-410 D4). */
const KIND_FILTERS: Array<{ key: 'all' | TimelineEntry['kind']; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'revision', label: 'File changes' },
  { key: 'invocation', label: 'Runs' },
  { key: 'proposal', label: 'Decisions' },
];

export function ActivityLedger() {
  const { userId } = useSurfacePreferences();
  const roster = useWorkspaceRoster();

  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const [kindFilter, setKindFilter] = useState<'all' | TimelineEntry['kind']>('all');
  const [actorFilter, setActorFilter] = useState<string>('all');
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
    [entries, userId, roster],
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

  const visible = resolved.filter(({ e, actorKey }) => {
    if (kindFilter !== 'all' && e.kind !== kindFilter) return false;
    if (actorFilter !== 'all' && actorKey !== actorFilter) return false;
    return true;
  });

  return (
    <div className="flex h-full flex-col">
      {/* Filter bar — actor / kind / date (ADR-410 D5). Kind + actor filter
          the loaded window client-side; the date jumps the server cursor. */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-6 py-2.5">
        <div className="flex items-center gap-1" role="group" aria-label="Filter by kind">
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
              {k.label}
            </button>
          ))}
        </div>
        <select
          value={actorFilter}
          onChange={(e) => setActorFilter(e.target.value)}
          aria-label="Filter by actor"
          className="h-7 rounded-md border border-border bg-background px-1.5 text-[11px] text-foreground"
        >
          <option value="all">Everyone</option>
          {actorOptions.map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          Up to
          <input
            type="date"
            value={beforeDate}
            onChange={(e) => setBeforeDate(e.target.value)}
            aria-label="Show history up to a date"
            className="h-7 rounded-md border border-border bg-background px-1.5 text-[11px] text-foreground"
          />
        </label>
        {(kindFilter !== 'all' || actorFilter !== 'all' || beforeDate) && (
          <button
            type="button"
            onClick={() => {
              setKindFilter('all');
              setActorFilter('all');
              setBeforeDate('');
            }}
            className="text-[11px] text-primary hover:underline"
          >
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : visible.length === 0 ? (
          <p className="px-6 py-8 text-sm text-muted-foreground">
            Nothing here{entries.length > 0 ? ' under these filters' : ' yet'} —
            every attributed act across the workspace (file changes, runs,
            decisions) shows up in this ledger.
          </p>
        ) : (
          <ul className="divide-y divide-border/30">
            {visible.map(({ e, who }) => {
              const secondary = secondaryLine(e, {
                witnessLabel: (d) =>
                  resolveActorForViewer(d, null, userId, roster).label ||
                  formatAuthorLabelOrSystem(d),
              });
              const line = actorLine(e, who.label);
              return (
                <li key={e.id} className="flex items-center gap-2.5 px-6 py-2.5">
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
                    <PrincipalBadge authoredBy={e.actor} fallbackToSystem size={12} />
                    {e.at && (
                      <span className="text-[11px] tabular-nums text-muted-foreground/50">
                        {new Date(e.at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
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
            {loadingMore ? 'Loading…' : 'Load older activity'}
          </button>
        )}
      </div>
    </div>
  );
}
