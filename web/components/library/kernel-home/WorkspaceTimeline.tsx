'use client';

/**
 * WorkspaceTimeline — the Home front page's Timeline slot (ADR-408 D5.1).
 *
 * Kernel-universal: renders for EVERY workspace from the three attributed
 * act ledgers (ADR-209 revisions + execution invocations + ADR-307
 * proposals), merged server-side into one chronological stream
 * (GET /api/workspace/timeline). Programs do NOT declare this slot.
 *
 * The commons made legible: every row is an attributed act — WHO
 * (attribution module + PrincipalBadge, the single actor primitive),
 * WHAT KIND (revision / invocation / proposal glyph), WHAT (title;
 * revisions deep-link to the Files surface), WHEN (relative time).
 * Proposal rows carry their status and, once decided, the witness
 * ("witnessed by <label>" from decided_by — the ADR-405 witness dial
 * rendered as narrative). Self-hides when the workspace has no acts yet
 * (sibling kernel-slot contract, ADR-312 D2). ~15 rows visible with a
 * subtle "show more" expanding to the fetched window.
 */

import { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { api } from '@/lib/api/client';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';
import { formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';
import { formatRelativeTimestamp } from '@/lib/content-shapes/decisions';
// Shared row grammar (ADR-340 D8 one body — the Notifications workbench and
// this slot render the same primitives at different depths, ADR-410 D5).
import {
  KindGlyph,
  rowTitle,
  secondaryLine,
  type TimelineEntry,
} from '@/lib/workspace/timeline-rows';
import { cn } from '@/lib/utils';

const FETCH_LIMIT = 40;
const COMPACT_LIMIT = 15;

export function WorkspaceTimeline() {
  const [entries, setEntries] = useState<TimelineEntry[] | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .timeline(FETCH_LIMIT)
      .then((r) => {
        if (!cancelled) setEntries(r.entries ?? []);
      })
      .catch(() => {
        // Load failure → empty, self-hides (sibling pattern).
        if (!cancelled) setEntries([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Self-hide: loading or empty renders nothing (honest cold-start Home).
  if (!entries || entries.length === 0) return null;

  const shown = expanded ? entries : entries.slice(0, COMPACT_LIMIT);
  const overflow = entries.length - shown.length;

  return (
    <section
      aria-label="Workspace timeline"
      className="rounded-lg border border-border/60 bg-card/50"
    >
      <header className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40">
        <History className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <h2 className="text-sm font-medium text-foreground">Timeline</h2>
        <span className="hidden sm:block text-[11px] text-muted-foreground/60 truncate">
          What&apos;s happened across the workspace — every actor, attributed.
        </span>
      </header>
      <ul className="divide-y divide-border/30">
        {shown.map((entry, i) => {
          const secondary = secondaryLine(entry, {
            witnessLabel: formatAuthorLabelOrSystem,
          });
          const title = rowTitle(entry);
          return (
            <li
              key={entry.proposal_id ?? `${entry.kind}-${entry.at ?? ''}-${entry.path ?? entry.slug ?? ''}-${i}`}
              className="flex items-center gap-2.5 px-4 py-2.5"
            >
              <KindGlyph entry={entry} />
              <span className="flex-1 min-w-0">
                {entry.kind === 'revision' && entry.path ? (
                  // Revisions deep-link into the Files surface (sibling
                  // pattern — the front page glances, Files is where you dwell).
                  <SurfaceLink
                    to="files"
                    params={{ path: entry.path }}
                    className="block text-sm text-foreground truncate hover:underline underline-offset-2"
                  >
                    {title}
                  </SurfaceLink>
                ) : (
                  <span className="block text-sm text-foreground truncate">{title}</span>
                )}
                {secondary && (
                  <span
                    className={cn(
                      'block text-[11px] truncate',
                      secondary.destructive
                        ? 'text-destructive/70'
                        : 'text-muted-foreground/50',
                    )}
                  >
                    {secondary.text}
                  </span>
                )}
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <PrincipalBadge authoredBy={entry.actor} fallbackToSystem size={12} />
                {entry.at && (
                  <span className="text-[11px] text-muted-foreground/50 tabular-nums">
                    {formatRelativeTimestamp(entry.at)}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {overflow > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="block w-full px-4 py-2 text-left text-[11px] text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-colors border-t border-border/30"
        >
          Show {overflow} more
        </button>
      )}
    </section>
  );
}
