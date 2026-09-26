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
 *
 * ADR-670 D5 — the rows are read from `useNeedsYou`, the ONE client reader of
 * what is waiting on the member; this queue no longer fetches its own copy, so
 * it cannot disagree with the bell about which mentions still want you.
 */

import { useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';
import { AtSign } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useFeedback } from '@/contexts/FeedbackContext';
import { dischargeMention, useNeedsYou, type MentionRow } from '@/lib/attention/useNeedsYou';

export function MentionQueue() {
  const t = useTranslations('supervisor.mentions');
  const { runAction } = useFeedback();
  const { mentions: rows, loaded, refresh } = useNeedsYou();
  const [resolving, setResolving] = useState<string | null>(null);
  const { navigateToSurface } = useSurfacePreferences();

  const dismiss = useCallback(
    async (m: MentionRow) => {
      const key = `${m.conversation_id}:${m.sequence}`;
      setResolving(key);
      try {
        // The row correctly SURVIVES a failure (an unadvanced cursor is still
        // unread) — but it did so in silence, so a failed dismiss looked like
        // a click that missed. The row still stays; now it says why.
        await runAction(() => api.mentions.markRead(m.conversation_id, m.sequence), {
          error: t('couldNotClear'),
        });
        // Clear everything the cursor now covers — in the one store, so the
        // bell's To do drops the same rows at the same moment.
        dischargeMention(m.conversation_id, m.sequence);
        void refresh();
      } catch {
        // Leave the row — a mention whose cursor failed to advance is still
        // unread; the next load re-derives the truth.
      } finally {
        setResolving(null);
      }
    },
    [runAction, t, refresh],
  );

  if (!loaded || rows.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <AtSign className="h-3.5 w-3.5" />
        {t('heading')}
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
                  {/* ADR-660 — one ICU message, not a verb joined to its
                      objects: Korean puts the conversation before the verb. */}
                  {t.rich('line', {
                    author: m.author,
                    conversation: m.conversation_name,
                    name: (chunks) => <span className="font-medium">{chunks}</span>,
                  })}
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
                  onClick={() => {
                    dischargeMention(m.conversation_id, m.sequence);
                    navigateToSurface('chat', { lane: m.conversation_id });
                  }}
                  className="rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted transition-colors"
                >
                  {t('openConversation')}
                </button>
                <button
                  type="button"
                  disabled={resolving === key}
                  onClick={() => dismiss(m)}
                  title={t('dismissTitle')}
                  className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
                >
                  {t('dismiss')}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
