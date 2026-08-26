/**
 * useSessionMessagesRealtime — Supabase Realtime subscription on session_messages.
 *
 * FOUNDATIONS v8.4 Axiom 1 fourth sub-clause: substrate is the bus the
 * runtime Loop runs over. The Reviewer + System Agent write to substrate
 * (session_messages, decisions.md, etc.) during cron-fired Loop wake-ups
 * while the operator-human is absent. The operator-in-real-time embodiment
 * needs to SEE those writes when they next attend to the cockpit —
 * otherwise the autonomous-Loop legibility commitment in ADR-260
 * ("real-time visible handoffs") is structurally undelivered.
 *
 * Why a hook (and not a one-off poll inside NarrativeContext):
 *   - Push-based via Supabase Realtime — operator sees substrate writes
 *     as they happen, not on next chat-turn (the pre-hardening behavior).
 *   - Same primitive reusable for action_proposals (Queue refresh) and
 *     agent_runs (Activity surfaces) — each gets its own hook calling
 *     the same shape against its own table.
 *   - RLS-aware: Supabase Realtime respects the policies on
 *     session_messages; the subscription only emits rows the operator
 *     is authorized to see.
 *
 * Singular Implementation: this is THE FE consumer of autonomous-write
 * events on session_messages. NarrativeContext's prior chat-turn-driven
 * refresh model is supplemented (not replaced) — initial history fetch
 * still loads on mount; the realtime subscription handles delta updates
 * while the page is open.
 *
 * Scope: subscribes to INSERTs only. Updates (e.g., post-completion
 * tool_history population on streaming messages) flow through the
 * existing reducer mutations from sendMessage's stream handler; the
 * realtime channel intentionally does not double-handle those.
 */

import { useEffect, useRef } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/client';
import { resolveAccessToken } from '@/lib/realtime/access-token';

export interface SessionMessageRow {
  id: string;
  session_id: string;
  role: string;
  content: string;
  sequence_number: number;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

export interface UseSessionMessagesRealtimeOptions {
  /**
   * The session_id to subscribe to. When null/undefined the subscription
   * is torn down (or never opened). Re-mounting with a new session_id
   * cleanly closes the old channel and opens a new one.
   */
  sessionId: string | null | undefined;

  /**
   * Called for every INSERT on session_messages matching the session_id
   * filter. Caller is responsible for de-duplicating against optimistic
   * UI state (e.g., the user's own message added via sendMessage's
   * ADD_MESSAGE dispatch BEFORE the realtime echo arrives — drop the
   * echo if the row id already exists in local state).
   */
  onInsert: (row: SessionMessageRow) => void;

  /**
   * Optional: called when the subscription transitions to SUBSCRIBED.
   * Useful for clearing "stale data" warnings or triggering a one-shot
   * gap-fill fetch to cover the window between page-load history-fetch
   * and subscription open.
   */
  onSubscribed?: () => void;

  /**
   * Optional: called on subscription errors. The hook auto-reconnects
   * via Supabase's built-in retry; this callback is observability only.
   */
  onError?: (err: unknown) => void;
}

/**
 * Subscribe to INSERT events on session_messages filtered to one session.
 *
 * Lifecycle:
 *   - sessionId becomes a string → open channel, register postgres_changes
 *     handler, call onSubscribed when state==SUBSCRIBED
 *   - sessionId becomes null/changes → close channel
 *   - component unmounts → close channel
 *
 * The hook holds the channel in a ref so re-renders don't re-subscribe.
 */
export function useSessionMessagesRealtime(
  opts: UseSessionMessagesRealtimeOptions,
): void {
  const { sessionId, onInsert, onSubscribed, onError } = opts;
  const channelRef = useRef<RealtimeChannel | null>(null);

  // Refs for the callbacks so the effect's identity is stable on
  // sessionId changes only, not on every render that produces a new
  // closure. Same pattern as React's useEvent (forthcoming).
  const onInsertRef = useRef(onInsert);
  const onSubscribedRef = useRef(onSubscribed);
  const onErrorRef = useRef(onError);
  onInsertRef.current = onInsert;
  onSubscribedRef.current = onSubscribed;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!sessionId) {
      // Tear down any prior channel; don't open a new one.
      if (channelRef.current) {
        try {
          channelRef.current.unsubscribe();
        } catch (err) {
          // Best-effort cleanup
          // eslint-disable-next-line no-console
          console.warn('[useSessionMessagesRealtime] cleanup failed:', err);
        }
        channelRef.current = null;
      }
      return;
    }

    const supabase = createClient();
    const channelName = `session-messages:${sessionId}`;

    // ⭐ ADR-575 D7 — the socket needs the USER's token, not the anon apikey.
    //
    // Realtime re-checks RLS per subscriber using the JWT the SOCKET carries.
    // This table's policy resolves `auth.uid()`, which is NULL for anon, so
    // without `setAuth` the channel reports `"Subscribed to PostgreSQL"` and
    // then silently delivers nothing. Found while driving the Text surface
    // (ADR-575) — the same omission was latent HERE first, and this hook is
    // where the pattern was copied from, so it is fixed at the source rather
    // than only in the new tenant.
    //
    // Set BEFORE subscribing — see the file-revisions hook for why the race
    // matters: the losing side is the silent one, and it resolves from cache
    // locally while failing on a cold load.
    // Sequenced, not fire-and-forget: the intent above was right, but
    // `.then()` beside the join lets `.subscribe()` run first on a cold load
    // (measured 2026-08-26 in the sibling bell hook — the socket carried
    // `apikey` and no `access_token`). Await the token, THEN join.
    let cancelled = false;
    let channel: RealtimeChannel | null = null;

    void (async () => {
      const token = await resolveAccessToken(supabase);
      if (token) supabase.realtime.setAuth(token);
      if (cancelled) return;

      channel = supabase
      .channel(channelName)
      .on(
        // The Supabase Realtime API uses a string literal here; the
        // @supabase/supabase-js types accept it as a generic event name.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        'postgres_changes' as any,
        {
          event: 'INSERT',
          schema: 'public',
          table: 'session_messages',
          filter: `session_id=eq.${sessionId}`,
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (payload: any) => {
          try {
            const row = payload?.new as SessionMessageRow | undefined;
            if (row && row.id) {
              onInsertRef.current(row);
            }
          } catch (err) {
            onErrorRef.current?.(err);
          }
        },
      )
      .subscribe((status: string, err?: Error) => {
        if (status === 'SUBSCRIBED') {
          onSubscribedRef.current?.();
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          onErrorRef.current?.(err ?? new Error(`channel status: ${status}`));
        }
      });

      channelRef.current = channel;
    })();

    return () => {
      cancelled = true;
      try {
        channel?.unsubscribe();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[useSessionMessagesRealtime] cleanup failed:', err);
      }
      channelRef.current = null;
    };
  }, [sessionId]);
}
