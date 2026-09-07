'use client';

/**
 * BoundaryLedger — Reach's CROSSED pane (ADR-642 D2).
 *
 * The workspace timeline under its BOUNDARY lens: the same three attributed
 * ledgers the Activity workbench reads, filtered at the query to the acts
 * that crossed the workspace boundary. Arrived = a retained raw observation
 * (a capture, a standing retention). Left = a `_publish.yaml` receipt (a
 * member-clicked send) or a decided proposal of a boundary family (approved
 * = left; rejected = refused). A LENS, never a second log (Axiom 9): the
 * rows render through the shared `timeline-rows` grammar, the actor resolves
 * through the same viewer layer, the cursor is the same `before`.
 *
 * What is different here is the RECEIPT line under a publish row — the
 * platform's answer, whether a reader can reach it (ADR-628 D7), and the
 * read-back verdict where the tenant mechanizes it (D8). A stage with
 * neither a receipt nor a refusal is served as unresolved, never as fine.
 */

import { useEffect, useMemo, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, ShieldX } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatAbsolute, formatLedgerTime } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { resolveActorForViewer, useWorkspaceRoster } from '@/lib/workspace/viewer';
import { KindGlyph, actorLine, secondaryLine, type TimelineEntry } from '@/lib/workspace/timeline-rows';
import { formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 60;

type Direction = 'arrived' | 'left' | 'refused' | 'decided';

/** Which way the act crossed. Derived from the row, never stored. */
function directionOf(e: TimelineEntry): Direction {
  if (e.kind === 'revision') {
    return e.path?.endsWith('/_publish.yaml') ? 'left' : 'arrived';
  }
  if (e.kind === 'proposal') {
    const s = (e.status ?? '').toLowerCase();
    if (s === 'approved' || s === 'executed' || s === 'applied') return 'left';
    if (s === 'rejected' || s === 'refused' || s === 'denied') return 'refused';
    return 'decided';
  }
  return 'decided';
}

const DIRECTION_META: Record<Direction, { label: string; className: string; Icon: typeof ArrowUpRight }> = {
  arrived: { label: 'arrived', className: 'text-teal-600 dark:text-teal-400', Icon: ArrowDownLeft },
  left: { label: 'left', className: 'text-cyan-600 dark:text-cyan-400', Icon: ArrowUpRight },
  refused: { label: 'refused', className: 'text-muted-foreground', Icon: ShieldX },
  decided: { label: 'decided', className: 'text-muted-foreground', Icon: ArrowUpRight },
};

/** The platform a receipt names, in the member's words. */
function platformWord(p?: string | null): string {
  if (!p) return 'the platform';
  if (p === 'wordpress') return 'WordPress';
  if (p === 'slack') return 'Slack';
  return p.charAt(0).toUpperCase() + p.slice(1);
}

function ReceiptLine({ receipt }: { receipt: NonNullable<TimelineEntry['receipt']> }) {
  const r = receipt as {
    platform?: string;
    url?: string | null;
    status?: string | null;
    publicly_readable?: boolean | null;
    read_back?: string | null;
    read_back_detail?: string | null;
    channel?: string | null;
    folded?: boolean | null;
  };
  const where = r.channel ? `${platformWord(r.platform)} ${r.channel}` : platformWord(r.platform);
  return (
    <div className="mt-1 space-y-0.5 text-[11px]">
      <div className="flex flex-wrap items-center gap-x-2 text-muted-foreground">
        <span>
          {r.status === 'draft' ? 'Draft saved on' : 'Sent to'} {where}
        </span>
        {r.url && (
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="truncate underline hover:text-foreground"
          >
            open
          </a>
        )}
      </div>
      {/* ADR-628 D7 — the platform accepted it, but can a reader reach it? */}
      {r.publicly_readable === false && (
        <p className="text-amber-600">Live on the site, but no reader can reach it yet — the site is private or unlaunched.</p>
      )}
      {/* ADR-628 D8 — the read-back verdict, where the tenant mechanizes it. */}
      {r.read_back === 'matched' && <p className="text-muted-foreground/80">Read back from {platformWord(r.platform)}: matches what was sent.</p>}
      {r.read_back === 'differs' && (
        <p className="text-amber-600">
          Read back from {platformWord(r.platform)}: stored differently than sent{r.read_back_detail ? ` (${r.read_back_detail})` : ''}.
        </p>
      )}
      {r.read_back === 'unreadable' && (
        <p className="text-amber-600">Could not read it back from {platformWord(r.platform)}{r.read_back_detail ? ` — ${r.read_back_detail}` : ''}.</p>
      )}
      {r.folded && <p className="text-muted-foreground/70">Long — readers see “Show more”.</p>}
    </div>
  );
}

export function BoundaryLedger() {
  const { userId } = useSurfacePreferences();
  const roster = useWorkspaceRoster();

  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.workspace
      .timeline(PAGE_SIZE, undefined, 'boundary')
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
  }, []);

  const loadMore = async () => {
    const oldest = entries[entries.length - 1]?.at;
    if (!oldest || loadingMore) return;
    setLoadingMore(true);
    try {
      const r = await api.workspace.timeline(PAGE_SIZE, oldest, 'boundary');
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

  const rows = useMemo(
    () =>
      entries.map((e) => ({
        e,
        who: resolveActorForViewer(e.actor, e.actor_id, userId, roster),
        direction: directionOf(e),
      })),
    [entries, userId, roster],
  );

  if (loading) {
    return (
      <div className="p-6">
        <div className="h-24 rounded-md bg-muted/30 animate-pulse" />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-border/60 px-6 py-10 text-center">
          <p className="text-sm font-medium text-foreground/80">Nothing has crossed yet</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            When a connection captures something, or you send a file out, it appears here with its receipt.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <ul className="divide-y divide-border/40">
        {rows.map(({ e, who, direction }) => {
          const meta = DIRECTION_META[direction];
          const line = secondaryLine(e, { witnessLabel: (d) => formatAuthorLabelOrSystem(d) });
          return (
            <li key={e.id} className="flex items-start gap-3 px-6 py-3">
              <span
                className={cn('mt-0.5 inline-flex w-16 shrink-0 items-center gap-1 text-[10px] font-medium uppercase tracking-wide', meta.className)}
                title={meta.label}
              >
                <meta.Icon className="h-3 w-3" aria-hidden />
                {meta.label}
              </span>
              <span className="mt-1 shrink-0"><KindGlyph entry={e} /></span>
              <div className="min-w-0 flex-1">
                <p className={cn('text-sm', who.isSelf ? 'text-foreground' : 'text-foreground/90')}>
                  {actorLine(e, who.label)}
                </p>
                {line && (
                  <p className={cn('truncate text-[11px]', line.destructive ? 'text-destructive' : 'text-muted-foreground')}>
                    {line.text}
                  </p>
                )}
                {e.receipt && <ReceiptLine receipt={e.receipt} />}
              </div>
              <span className="shrink-0 text-[11px] text-muted-foreground/60" title={formatAbsolute(e.at)}>
                {formatLedgerTime(e.at)}
              </span>
            </li>
          );
        })}
      </ul>
      {hasMore && (
        <div className="px-6 py-4">
          <button
            type="button"
            onClick={() => void loadMore()}
            disabled={loadingMore}
            className="text-xs text-primary hover:underline disabled:opacity-50"
          >
            {loadingMore ? 'Loading…' : 'Earlier'}
          </button>
        </div>
      )}
    </div>
  );
}
