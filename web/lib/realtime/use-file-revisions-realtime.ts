/**
 * useFileRevisionsRealtime — a document learns about other principals' writes
 * WHEN THEY HAPPEN, not by colliding with them (ADR-575).
 *
 * ## Why this exists
 *
 * Text's conflict banner was being refined for three decisions (ADR-572 D5,
 * D7, D10) without anyone asking why it fires so often. It fires because the
 * surface had no way to hear about a peer's write: whole-document CAS, no
 * subscription, so the FIRST notice of a concurrent edit was a 409 at save
 * time. Notion's members never see that screen, and the reason is not their
 * block model — it is that rendering a record SUBSCRIBES the client to it.
 * Their MessageStore pushes a **version number** on commit and the client
 * answers with a targeted refetch (`syncRecordValues`).
 *
 * That is exactly this hook: **the push is an invalidation signal, never
 * content.** The payload carries `path`/`authored_by`/`created_at` — no file
 * bytes cross the socket. The subscriber decides what to refetch.
 *
 * ## Why it is a second hook and not a generalization
 *
 * `use-session-messages-realtime.ts` is the same shape against a different
 * table, and its own header says the primitive is "reusable for each [table],
 * each gets its own hook calling the same shape against its own table." This
 * follows that instruction literally rather than inventing a generic
 * subscribe-to-anything helper — the filter, the row type and the
 * own-write rule are all table-specific, and a generic version would carry
 * none of them.
 *
 * ## The own-write rule (the non-obvious part)
 *
 * Every autosave the member makes INSERTs a revision row, which comes straight
 * back down this channel. Without a filter the editor would announce the
 * member's own typing as a peer edit, two seconds after every pause — the
 * surface accusing you of editing behind your own back. So the caller passes
 * the revision ids it has already accounted for (`isOwnWrite`), and echoes are
 * dropped. This mirrors the de-duplication contract the session-messages hook
 * states for optimistic UI.
 *
 * REQUIRES migration 240 — `workspace_file_versions` in the `supabase_realtime`
 * publication. Without it this hook subscribes cleanly and receives NOTHING,
 * which is the failure mode that reads as "realtime is wired and quiet".
 * RLS ("Members view workspace file versions") is evaluated per subscriber, so
 * the channel can only emit rows the member could already read.
 */

import { useEffect, useRef } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/client';
import { resolveAccessToken } from '@/lib/realtime/access-token';

export interface FileRevisionRow {
  id: string;
  path: string;
  authored_by: string;
  created_at: string;
  workspace_id?: string | null;
  /** Present on the row; carried so a caller can advance its CAS base. */
  parent_version_id?: string | null;
}

export interface UseFileRevisionsRealtimeOptions {
  /**
   * Absolute workspace path (`/workspace/…`). Null/undefined tears the
   * subscription down; changing it closes the old channel and opens a new one.
   */
  path: string | null | undefined;

  /**
   * A revision landed on this path that the caller did NOT author. Called once
   * per foreign INSERT — the invalidation signal. The caller refetches; this
   * hook never fetches for it.
   */
  onForeignRevision: (row: FileRevisionRow) => void;

  /**
   * Is this revision one the caller already knows about (its own save's echo)?
   * Returning true drops the event. Without this the member's own autosave
   * would be announced back to them as somebody else's edit.
   */
  isOwnWrite?: (row: FileRevisionRow) => boolean;

  /** Observability only — the client auto-reconnects via Supabase's retry. */
  onError?: (err: unknown) => void;
}

export function useFileRevisionsRealtime(
  opts: UseFileRevisionsRealtimeOptions,
): void {
  const { path, onForeignRevision, isOwnWrite, onError } = opts;
  const channelRef = useRef<RealtimeChannel | null>(null);

  // Callbacks through refs so the effect re-runs on `path` ONLY. A render that
  // produces a new closure must not tear down and reopen the channel — that
  // would drop events in the gap and, on a surface that re-renders on every
  // keystroke, would reopen the socket continuously.
  const onForeignRef = useRef(onForeignRevision);
  const isOwnRef = useRef(isOwnWrite);
  const onErrorRef = useRef(onError);
  onForeignRef.current = onForeignRevision;
  isOwnRef.current = isOwnWrite;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!path) {
      if (channelRef.current) {
        try {
          channelRef.current.unsubscribe();
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn('[useFileRevisionsRealtime] cleanup failed:', err);
        }
        channelRef.current = null;
      }
      return;
    }

    const supabase = createClient();
    // The path is the identity here (there is no per-file id on the client),
    // so it is the channel name too. Encoded because a workspace path contains
    // `/` and may contain characters a channel topic should not carry raw.
    const channelName = `file-revisions:${encodeURIComponent(path)}`;

    // ⭐ ADR-575 D7 — HAND THE SOCKET THE USER'S TOKEN.
    //
    // Realtime re-checks this table's RLS per subscriber, and it does so using
    // the JWT the SOCKET carries — not the one the REST calls carry. Without
    // `setAuth` the socket connects with the anon apikey, `auth.uid()` is NULL
    // inside the policy, `workspace_id IN (owned ∪ granted)` matches nothing,
    // and every row is dropped **silently**: the channel still reports
    // `"Subscribed to PostgreSQL"` with the correct filter and simply never
    // delivers.
    //
    // Measured on production before this line existed: the `phx_join` frame
    // carried no `access_token`, a peer write landed as a real revision row,
    // and the client received only Phoenix heartbeats.
    //
    // `setAuth` MUST land before `subscribe()`, so the whole join is sequenced
    // behind the session read. Calling it fire-and-forget beside the join is a
    // race whose losing side is the silent one — it would work locally, where
    // the session resolves from cache, and fail on a cold load.
    let cancelled = false;
    let channel: RealtimeChannel | null = null;

    void (async () => {
      try {
        const token = await resolveAccessToken(supabase);
        if (token) supabase.realtime.setAuth(token);
      } catch (err) {
        onErrorRef.current?.(err);
      }
      if (cancelled) return;

      channel = supabase
        .channel(channelName)
        .on(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'postgres_changes' as any,
          {
            event: 'INSERT',
            schema: 'public',
            table: 'workspace_file_versions',
            // Server-side filter: this client is told about ONE file. Filtering
            // in the callback instead would ship every workspace revision to
            // every open editor and discard them locally.
            filter: `path=eq.${path}`,
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (payload: any) => {
            try {
              const row = payload?.new as FileRevisionRow | undefined;
              if (!row?.id) return;
              if (isOwnRef.current?.(row)) return; // the member's own echo
              onForeignRef.current(row);
            } catch (err) {
              onErrorRef.current?.(err);
            }
          },
        )
        .subscribe((status: string, err?: Error) => {
          if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
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
        console.warn('[useFileRevisionsRealtime] cleanup failed:', err);
      }
      channelRef.current = null;
    };
  }, [path]);
}
