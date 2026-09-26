'use client';

/**
 * useNeedsYou — the ONE client reader of "what is waiting on me" (ADR-670 D5).
 *
 * Three sources, composed once:
 *   - pending proposals — `api.proposals.list('pending')`
 *   - unresolved mentions of the viewer — `api.mentions.list` (ADR-605)
 *   - runs WAITING on the viewer — read from `useRuns`, never fetched again
 *
 * Every mount that shows what needs the member reads THIS store: the bell's
 * To do, Notifications → To do (its mention queue and the proposal body, which
 * Reach → Leaving also mounts), and Chat's index. Before ADR-670 each of those
 * fetched its own copy, and three derivations of one question disagreed by
 * construction: the bell never showed a waiting run, and the Supervisor never
 * showed a pending proposal. One store cannot disagree with itself.
 *
 * The shape is `useRuns`'s: a module-level snapshot, a listener set, one fetch
 * shared by every mount (concurrent refreshes share one request, and a refresh
 * asked for DURING a fetch runs once more after it, so a caller that just
 * changed something never reads the answer from before its change).
 *
 * FRESHNESS moved here from the bell, so it is not lost when the bell is not
 * the one mounted:
 *   - a poll floor (60 s, skipped while the tab is hidden) — `action_proposals`
 *     is not published to realtime, so the floor is how a proposal arrives;
 *   - realtime INVALIDATION on `session_messages` INSERT — a mention badges in
 *     seconds. The push is a signal, never content (the ADR-575 shape); RLS on
 *     the socket's own token is the filter.
 *   - ADR-637: VISITING a conversation advances its read cursor server-side
 *     (the lane read), so the mount that reads a lane calls `refreshNeedsYou()`
 *     after it — the visit discharges the mention, and this list must follow.
 *
 * ⭐ `setAuth` BEFORE `subscribe()` (ADR-575 D7): without the member's token the
 * socket joins as anon, RLS yields nothing, and the channel reports SUBSCRIBED
 * while delivering zero rows — the poll floor is what makes that a slow badge
 * rather than a dead one.
 *
 * Attention is DERIVED, NEVER STORED (DP29): nothing here writes. Resolving a
 * mention is ADR-637's cursor; `dischargeMention` only drops the rows the
 * cursor now covers so they do not linger until the next read.
 */

import { useEffect, useMemo, useState } from 'react';
import type { RealtimeChannel } from '@supabase/supabase-js';
import { api, type Run } from '@/lib/api/client';
import { createClient } from '@/lib/supabase/client';
import { resolveAccessToken } from '@/lib/realtime/access-token';
import { useRuns } from '@/lib/runs/useRuns';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

type ProposalsResponse = Awaited<ReturnType<typeof api.proposals.list>>;
/** One pending proposal — the served shape, whole (the decision modal reads it). */
export type PendingProposal = ProposalsResponse['proposals'][number];
/** Who is set to decide pending proposals (ADR-211 D7). */
export type ProposalOccupant = ProposalsResponse['current_occupant'];
/** One unresolved mention of the viewer (ADR-605). */
export type MentionRow = Awaited<ReturnType<typeof api.mentions.list>>['mentions'][number];

/** The widest mount's read — Notifications → To do lists every pending one. */
const PROPOSAL_LIMIT = 100;
const MENTION_LIMIT = 20;
/** The poll floor — the bell's own interval, moved here with the fetch. */
const POLL_MS = 60_000;
const DEBOUNCE_MS = 750;

interface Snapshot {
  proposals: PendingProposal[] | null;
  occupant: ProposalOccupant | null;
  mentions: MentionRow[] | null;
}

let snapshot: Snapshot = { proposals: null, occupant: null, mentions: null };
const listeners = new Set<(s: Snapshot) => void>();
let mounts = 0;
let channel: RealtimeChannel | null = null;
let cancelJoin: (() => void) | null = null;
let debounce: ReturnType<typeof setTimeout> | null = null;
let poll: ReturnType<typeof setInterval> | null = null;
let inflight: Promise<void> | null = null;
let again = false;

function publish(next: Snapshot) {
  snapshot = next;
  listeners.forEach((l) => l(snapshot));
}

async function fetchOnce(): Promise<void> {
  const [p, m] = await Promise.allSettled([
    api.proposals.list('pending', PROPOSAL_LIMIT),
    // allSettled: an API deployed without the endpoint degrades to no mention
    // rows, never a broken bell (ADR-605's own degrade, kept).
    api.mentions.list(MENTION_LIMIT),
  ]);
  publish({
    proposals: p.status === 'fulfilled' ? p.value.proposals ?? [] : snapshot.proposals ?? [],
    occupant: p.status === 'fulfilled' ? p.value.current_occupant ?? null : snapshot.occupant,
    mentions: m.status === 'fulfilled' ? m.value.mentions ?? [] : snapshot.mentions ?? [],
  });
}

/**
 * Re-read what needs the viewer. Call it after anything that changes the
 * answer: a proposal decided, a mention dismissed, a conversation visited.
 * With nothing mounted it does nothing — the first mount reads anyway.
 */
export function refreshNeedsYou(): Promise<void> {
  if (mounts === 0) return Promise.resolve();
  if (inflight) {
    again = true;
    return inflight;
  }
  inflight = fetchOnce()
    .catch(() => {
      /* each source already degraded inside allSettled */
    })
    .finally(() => {
      inflight = null;
      if (again) {
        again = false;
        void refreshNeedsYou();
      }
    });
  return inflight;
}

/**
 * ADR-637 — a mention was discharged (visited, or dismissed through the
 * cursor). Drop every row that cursor now covers, locally and at once; the
 * next read re-derives the truth either way.
 */
export function dischargeMention(conversationId: string, sequence: number): void {
  if (!snapshot.mentions) return;
  publish({
    ...snapshot,
    mentions: snapshot.mentions.filter(
      (r) => r.conversation_id !== conversationId || r.sequence > sequence,
    ),
  });
}

/**
 * Does this run wait on the viewer? A run WAITING on `{kind: 'member'}` waits
 * on its own member — the one it runs as (`services/runs.py::raise_due` opens
 * it that way). Today that is the only kind; a kind that names someone else
 * is not the viewer's until it says so.
 */
export function waitsOnViewer(run: Run, viewerId: string | null | undefined): boolean {
  return (
    run.state === 'waiting' &&
    (run.waiting_on?.kind ?? 'member') === 'member' &&
    Boolean(viewerId) &&
    run.user_id === viewerId
  );
}

function bump() {
  if (debounce) clearTimeout(debounce);
  debounce = setTimeout(() => {
    debounce = null;
    void refreshNeedsYou();
  }, DEBOUNCE_MS);
}

function join(): () => void {
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
      .channel('needs-you-invalidation')
      .on(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        'postgres_changes' as any,
        { event: 'INSERT', schema: 'public', table: 'session_messages' },
        bump,
      )
      .subscribe();
  })();
  return () => {
    cancelled = true;
  };
}

function start() {
  cancelJoin = join();
  poll = setInterval(() => {
    if (typeof document === 'undefined' || document.visibilityState === 'visible') {
      void refreshNeedsYou();
    }
  }, POLL_MS);
  void refreshNeedsYou();
}

function stop() {
  cancelJoin?.();
  cancelJoin = null;
  try {
    channel?.unsubscribe();
  } catch {
    /* best-effort */
  }
  channel = null;
  if (debounce) clearTimeout(debounce);
  debounce = null;
  if (poll) clearInterval(poll);
  poll = null;
}

export interface NeedsYou {
  /** Pending proposals, newest first as served. Empty until the first read. */
  proposals: PendingProposal[];
  /** Who decides them (ADR-211 D7), or null when unknown. */
  occupant: ProposalOccupant | null;
  /** Mentions no visit has discharged yet (ADR-637). */
  mentions: MentionRow[];
  /** Runs due and waiting on the viewer (ADR-666 D4). */
  waitingRuns: Run[];
  /** How many things wait on the viewer, across all three. */
  count: number;
  /** Proposals and mentions have been read at least once. */
  loaded: boolean;
  refresh: () => Promise<void>;
}

export function useNeedsYou(): NeedsYou {
  const [state, setState] = useState<Snapshot>(snapshot);
  const { runs } = useRuns();
  const { userId } = useSurfacePreferences();

  useEffect(() => {
    listeners.add(setState);
    mounts += 1;
    if (mounts === 1) start();
    else setState(snapshot);
    return () => {
      listeners.delete(setState);
      mounts -= 1;
      if (mounts === 0) stop();
    };
  }, []);

  const waitingRuns = useMemo(
    () => (runs ?? []).filter((r) => waitsOnViewer(r, userId)),
    [runs, userId],
  );

  const proposals = state.proposals ?? [];
  const mentions = state.mentions ?? [];
  return {
    proposals,
    occupant: state.occupant,
    mentions,
    waitingRuns,
    count: proposals.length + mentions.length + waitingRuns.length,
    loaded: state.proposals !== null && state.mentions !== null,
    refresh: refreshNeedsYou,
  };
}
