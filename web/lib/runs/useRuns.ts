'use client';

/**
 * useRuns — the ONE client reader of the run ledger (ADR-666).
 *
 * Every mount that shows runs — the Supervisor's cockpit, the shell's run tray
 * — reads THIS store: one fetch of `GET /api/runs`, one realtime subscription,
 * shared by however many components are mounted. Two readers of one ledger
 * would be free to disagree about whether a run is still going, which is the
 * two-authorities defect ADR-637 ended for attention.
 *
 * LIVE (ADR-666 D6). `runs` is published to realtime (migration 262); a run's
 * steps land as UPDATEs while it goes. The push is an INVALIDATION signal,
 * never content — any change refetches the list (debounced), the ADR-575
 * shape. RLS on the socket's own token is the filter: a member hears only the
 * runs of workspaces they belong to.
 *
 * ⭐ `setAuth` BEFORE `subscribe()` — ADR-575 D7. Without the member's token
 * the socket joins as anon, RLS yields nothing, and the channel reports
 * SUBSCRIBED while delivering zero rows. That silent failure is why the
 * store ALSO polls while anything is live: the floor that makes a dead socket
 * a slow cockpit rather than a frozen one.
 */

import { useEffect, useState } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { api, isLiveRun, type Run } from '@/lib/api/client';
import { createClient } from '@/lib/supabase/client';
import { resolveAccessToken } from '@/lib/realtime/access-token';

/** How many runs the store holds — enough for "running now" and a day of
 *  "recently"; the declaration's detail reads its own. */
const LIST_LIMIT = 40;
const DEBOUNCE_MS = 400;
/** The poll floor while a run is live — the socket's safety net. */
const LIVE_POLL_MS = 15_000;

interface Snapshot {
  runs: Run[] | null;
  failed: boolean;
}

let snapshot: Snapshot = { runs: null, failed: false };
const listeners = new Set<(s: Snapshot) => void>();
let mounts = 0;
let channel: RealtimeChannel | null = null;
let debounce: ReturnType<typeof setTimeout> | null = null;
let poll: ReturnType<typeof setInterval> | null = null;
let inflight: Promise<void> | null = null;

function publish(next: Snapshot) {
  snapshot = next;
  listeners.forEach((l) => l(snapshot));
}

/** Refetch the ledger now. Concurrent calls share one request. */
export function refreshRuns(): Promise<void> {
  if (inflight) return inflight;
  inflight = api.runs
    .list({ limit: LIST_LIMIT })
    .then(
      (rows) => publish({ runs: Array.isArray(rows) ? rows : [], failed: false }),
      () => publish({ runs: snapshot.runs ?? [], failed: snapshot.runs === null }),
    )
    .finally(() => {
      inflight = null;
      armPoll();
    });
  return inflight;
}

function armPoll() {
  const live = (snapshot.runs ?? []).some(isLiveRun);
  if (live && !poll && mounts > 0) {
    poll = setInterval(() => void refreshRuns(), LIVE_POLL_MS);
  } else if ((!live || mounts === 0) && poll) {
    clearInterval(poll);
    poll = null;
  }
}

function bump() {
  if (debounce) clearTimeout(debounce);
  debounce = setTimeout(() => {
    debounce = null;
    void refreshRuns();
  }, DEBOUNCE_MS);
}

function subscribe() {
  const supabase = createClient();
  let cancelled = false;
  void (async () => {
    try {
      const token = await resolveAccessToken(supabase);
      if (token) supabase.realtime.setAuth(token);
    } catch {
      /* the poll floor covers a socket that cannot authenticate */
    }
    if (cancelled || mounts === 0) return;
    channel = supabase
      .channel('runs-invalidation')
      .on(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        'postgres_changes' as any,
        { event: '*', schema: 'public', table: 'runs' },
        bump,
      )
      .subscribe();
  })();
  return () => {
    cancelled = true;
  };
}

function unsubscribe() {
  try {
    channel?.unsubscribe();
  } catch {
    /* best-effort */
  }
  channel = null;
  if (debounce) clearTimeout(debounce);
  debounce = null;
  armPoll();
}

let cancelJoin: (() => void) | null = null;

export function useRuns(): Snapshot & { refresh: () => Promise<void> } {
  const [state, setState] = useState<Snapshot>(snapshot);

  useEffect(() => {
    listeners.add(setState);
    mounts += 1;
    if (mounts === 1) {
      cancelJoin = subscribe();
      void refreshRuns();
    } else {
      setState(snapshot);
    }
    return () => {
      listeners.delete(setState);
      mounts -= 1;
      if (mounts === 0) {
        cancelJoin?.();
        cancelJoin = null;
        unsubscribe();
      }
    };
  }, []);

  return { ...state, refresh: refreshRuns };
}
