'use client';

/**
 * MentionQueue — unresolved mentions of the viewer (ADR-605; ADR-492 D3's
 * To-do second source, workbench mount).
 *
 * Derived, never stored: the rows come from `GET /api/mentions` (cast ∩
 * visibility window ∩ the write-time stamp on the message row). ADR-637:
 * membership keys on ONE per-conversation READ cursor, and VISITING the
 * conversation advances it server-side — so "Open conversation" below IS the
 * discharge, no second call needed. "Dismiss" is the same cursor for the
 * mention you know you needn't read; it is an alternative to visiting, never
 * the only way out (the pre-637 shape, which stranded rows for a week).
 */

import { useCallback, useEffect, useState } from 'react';
import { AtSign } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

interface MentionRow {
  conversation_id: string;
  conversation_name: string;
  sequence: number;
  at: string | null;
  excerpt: string;
  author: string;
}

export function MentionQueue() {
  const [rows, setRows] = useState<MentionRow[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [resolving, setResolving] = useState<string | null>(null);
  const { navigateToSurface } = useSurfacePreferences();

  const load = useCallback(async () => {
    try {
      const res = await api.mentions.list(20);
      setRows(res.mentions || []);
    } catch {
      // An API without the endpoint yet (deploy skew) degrades to no rows —
      // the queue below still renders; never a broken pane.
      setRows([]);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const dismiss = useCallback(
    async (m: MentionRow) => {
      const key = `${m.conversation_id}:${m.sequence}`;
      setResolving(key);
      try {
        await api.mentions.markRead(m.conversation_id, m.sequence);
        // Optimistic local clear of everything the cursor now covers.
        setRows((prev) =>
          prev.filter(
            (r) => r.conversation_id !== m.conversation_id || r.sequence > m.sequence,
          ),
        );
      } catch {
        // Leave the row — a mention whose cursor failed to advance is still
        // unread; the next load re-derives the truth.
      } finally {
        setResolving(null);
      }
    },
    [],
  );

  if (!loaded || rows.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <AtSign className="h-3.5 w-3.5" />
        Mentions
      </div>
      <div className="space-y-2">
        {rows.map((m) => {
          const key = `${m.conversation_id}:${m.sequence}`;
          return (
            <div
              key={key}
              className="flex items-center justify-between gap-3 rounded-lg border border-border p-3"
            >
              <div className="min-w-0">
                <div className="text-sm">
                  <span className="font-medium">{m.author}</span> mentioned you in{' '}
                  <span className="font-medium">{m.conversation_name}</span>
                  {m.at && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {formatRelativeTime(m.at)}
                    </span>
                  )}
                </div>
                {m.excerpt && (
                  <div className="mt-0.5 truncate text-xs text-muted-foreground">
                    {m.excerpt}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    navigateToSurface('chat', { lane: m.conversation_id })
                  }
                  className="rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted transition-colors"
                >
                  Open conversation
                </button>
                <button
                  type="button"
                  disabled={resolving === key}
                  onClick={() => dismiss(m)}
                  title="Clear without opening"
                  className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
                >
                  Dismiss
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
