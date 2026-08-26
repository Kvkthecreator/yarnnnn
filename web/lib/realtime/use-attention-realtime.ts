/**
 * useAttentionRealtime — push invalidation for the bell (Layer-1 G3,
 * ADR-593 §6 / phase 4's first mount).
 *
 * The bell polled at 60s, so a mention could take a minute to badge. This
 * hook is the THIRD tenant of the realtime primitive (the ADR-575 pattern:
 * use-session-messages-realtime → use-file-revisions-realtime → here), and
 * it is deliberately an INVALIDATION signal, never content — the ADR-575
 * Part-D benchmark lesson (Notion pushes a version number; the client
 * refetches what went stale). On any event the caller re-runs its existing
 * derivation; nothing new is stored, DP29 holds.
 *
 * What it can subscribe to is bounded by what is PUBLISHED:
 *   - `session_messages` (publication since migration 008-era; RLS since 228
 *     is cast ∩ visibility window) → mentions + conversation acts arrive
 *     per-viewer. No table filter: RLS on the socket's JWT IS the filter —
 *     the subscriber receives only rows they may read.
 *   - `workspace_file_versions` (published by migration 240, which refuses
 *     to publish with RLS off) → substrate revisions.
 * `action_proposals` and `execution_events` are NOT published — those
 * classes stay on the poll floor, and this hook does not pretend otherwise
 * (publishing more tables is a migration with the mig-240 RLS ceremony, not
 * an FE change).
 *
 * ⭐ The socket carries the USER's token (`setAuth` BEFORE subscribe) — the
 * ADR-575 D7 lesson: without it the channel reports SUBSCRIBED and silently
 * delivers nothing, because RLS resolves auth.uid() as NULL for anon.
 *
 * Events are debounced (trailing) so a burst — a streamed turn's rows, a
 * multi-file write — costs one refetch, not one per row.
 */

import { useEffect, useRef } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/client';
import { resolveAccessToken } from '@/lib/realtime/access-token';

const DEBOUNCE_MS = 750;

export interface UseAttentionRealtimeOptions {
  /** When false, no subscription opens (e.g. no userId resolved yet). */
  enabled: boolean;
  /** Called (debounced) when any published attention-relevant row lands.
   *  The caller re-runs its existing derivation — invalidation, never data. */
  onActivity: () => void;
}

export function useAttentionRealtime(opts: UseAttentionRealtimeOptions): void {
  const { enabled, onActivity } = opts;
  const channelRef = useRef<RealtimeChannel | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onActivityRef = useRef(onActivity);
  onActivityRef.current = onActivity;

  useEffect(() => {
    if (!enabled) return;

    const supabase = createClient();
    const bump = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        try {
          onActivityRef.current();
        } catch {
          // The next poll tick is the floor; an invalidation callback
          // failure must never take the channel down.
        }
      }, DEBOUNCE_MS);
    };

    // `setAuth` MUST land BEFORE `subscribe()`, so the whole join is sequenced
    // behind the session read — the same shape use-file-revisions-realtime
    // already uses, and for the same reason. Fire-and-forget beside the join
    // is a race whose losing side is SILENT: the socket joins with the anon
    // apikey, `auth.uid()` is NULL, RLS on session_messages yields nothing,
    // and the channel reports SUBSCRIBED while delivering zero rows.
    //
    // It loses on a COLD load (the session resolves from the network) and wins
    // warm (resolved from cache) — so it works in local dev and fails in
    // production. Measured 2026-08-26: the socket joined with `apikey` and no
    // `access_token`, and a mention took ~10s (the poll), not the "seconds"
    // G3 claims.
    let cancelled = false;
    let channel: RealtimeChannel | null = null;

    void (async () => {
      const token = await resolveAccessToken(supabase);
      if (token) supabase.realtime.setAuth(token);
      if (cancelled) return;

      channel = supabase
        .channel('attention-invalidation')
        .on(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'postgres_changes' as any,
          { event: 'INSERT', schema: 'public', table: 'session_messages' },
          bump,
        )
        .on(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'postgres_changes' as any,
          { event: 'INSERT', schema: 'public', table: 'workspace_file_versions' },
          bump,
        )
        .subscribe();

      channelRef.current = channel;
    })();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      try {
        channel?.unsubscribe();
      } catch {
        // best-effort cleanup
      }
      channelRef.current = null;
    };
  }, [enabled]);
}
