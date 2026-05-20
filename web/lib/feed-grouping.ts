/**
 * feed-grouping — group session_messages into Feed render units.
 *
 * ADR-289 D6: the FeedTimeline groups rows by `metadata.invocation_id`.
 * Every row produced during one Reviewer cycle shares an invocation id (per
 * ADR-289 D2 + D4 + D5); this helper folds the flat message list into a
 * render-ready list of typed units.
 *
 * Render units (chronological order preserved):
 *   - operator-event   : a `role='user'` message rendered as a standalone
 *                        marker row. When the user message shares an
 *                        invocation_id with subsequent Reviewer rows, the
 *                        marker carries a pointer "opened conversation
 *                        with Reviewer →" linking into the drawer.
 *   - invocation-card  : a group of rows sharing one invocation_id whose
 *                        cycle was NOT operator-addressed (i.e. autonomous
 *                        Reviewer wake). Contains the Reviewer's verdict
 *                        body + 0..N consequential System Agent action
 *                        narrations.
 *   - addressed-card   : a group of rows sharing one invocation_id whose
 *                        cycle was operator-addressed. Operator's user row
 *                        is hoisted out as a separate operator-event
 *                        marker per Option B (chronological flow); the
 *                        card carries only Reviewer reply + actions.
 *   - standalone-event : a row with no invocation_id (file events, system
 *                        events, capability transitions, balance warnings,
 *                        proposal chips). Compact typed-row treatment.
 *
 * Day separators are NOT inserted at the grouping layer — they're a render
 * concern derived from `created_at` at component level (cheap to compute).
 *
 * The function is pure — no React, no state, idempotent over the same
 * input ordering.
 */

import type { TPMessage, NarrativePulse } from '@/types/desk';

// ---------------------------------------------------------------------------
// Render unit types
// ---------------------------------------------------------------------------

export type FeedUnit =
  | OperatorEventUnit
  | InvocationCardUnit
  | StandaloneEventUnit;

export interface OperatorEventUnit {
  kind: 'operator-event';
  /** Stable id for React keys — the operator's session_messages row id. */
  id: string;
  /** The operator message. */
  message: TPMessage;
  /** True when this user message shares its invocation_id with at least
   *  one downstream Reviewer/system_agent row. Drives the
   *  "opened conversation with Reviewer →" affordance. */
  ledToInvocation: boolean;
  /** The invocation_id when ledToInvocation is true, else undefined.
   *  Used by the operator-event marker to deep-link the drawer to the
   *  specific addressed exchange. */
  invocationId?: string;
  /** ISO timestamp of the message (drives chronological sort). */
  timestamp: Date;
}

export interface InvocationCardUnit {
  kind: 'invocation-card';
  /** Stable id for React keys — the invocation_id itself. */
  id: string;
  /** The invocation atom id per ADR-289 D2. */
  invocationId: string;
  /** Trigger pulse of the cycle. Drives header presentation. Inferred
   *  from the first non-user row in the group (the Reviewer reply or
   *  the earliest system_agent narration). */
  pulse: NarrativePulse;
  /** When true, the cycle was operator-addressed — the operator's user
   *  row has been hoisted to its own OperatorEventUnit upstream of this
   *  card. The card itself shows Reviewer reply + actions only. */
  isAddressed: boolean;
  /** The Reviewer verdict row, if present. Carries the reasoning body
   *  that becomes the card's headline content. */
  verdict?: TPMessage;
  /** System Agent action narration rows produced during the cycle.
   *  Render as nested action list inside the card when expanded. */
  actions: TPMessage[];
  /** ISO timestamp of the earliest row in the group (drives
   *  chronological sort of the timeline). */
  timestamp: Date;
}

export interface StandaloneEventUnit {
  kind: 'standalone-event';
  /** Stable id for React keys — the session_messages row id. */
  id: string;
  /** The standalone message. */
  message: TPMessage;
  /** ISO timestamp of the message. */
  timestamp: Date;
}

// ---------------------------------------------------------------------------
// Legacy mirror-refresh narration filter (ADR-289 Phase 2a, 2026-05-20)
// ---------------------------------------------------------------------------
//
// Pre-Phase-2a `surface_reviewer_actions` emitted System Agent narration for
// every consequential Reviewer-directed action including mirror-refresh
// fetches (SyncPlatformState; FireInvocation of mechanical recurrences like
// track-positions / track-regime / track-universe / track-orders). Phase 2a
// silences these at the BE emit boundary going forward. This client-side
// filter discards rows already on disk that were written under the pre-fix
// policy, so the operator's feed doesn't show "SyncPlatformState: 1 written,
// 0 unchanged" historical noise.
//
// Transient by design — legacy data will roll off with the alpha reset cycle.
// Strict pattern match on the known narration prefixes to avoid hiding
// anything else.
const LEGACY_MIRROR_REFRESH_PATTERNS: RegExp[] = [
  /SyncPlatformState\b/,                          // ADR-264 mirror primitive
  /^Firing recurrence on Reviewer's direction\.\s*(TrackPositions|TrackOrders|TrackRegime|TrackUniverse|TrackAccount)/,
  /^(TrackPositions|TrackOrders|TrackRegime|TrackUniverse|TrackAccount):/,
];

function isLegacyMirrorRefreshRow(msg: TPMessage): boolean {
  // Only system_agent narrations are subject to the legacy filter.
  // Operator user messages, Reviewer verdicts, user-authored Agent
  // outputs, and orphan system events are never filtered.
  if (msg.role !== 'system_agent') return false;
  const content = msg.content ?? '';
  return LEGACY_MIRROR_REFRESH_PATTERNS.some((re) => re.test(content));
}

// ---------------------------------------------------------------------------
// Grouping
// ---------------------------------------------------------------------------

/**
 * Fold a flat message list into a chronologically-ordered list of Feed
 * render units. Pure function — output depends only on input.
 *
 * Ordering rules:
 *  - Operator events sort by their own timestamp.
 *  - Invocation cards sort by the timestamp of the EARLIEST row in the
 *    group (so an addressed card lands near the operator marker that
 *    triggered it; an autonomous wake lands at the time the Reviewer
 *    first emitted into the cycle).
 *  - Standalone events sort by their own timestamp.
 *
 * The output preserves a deterministic stable order across re-renders
 * with the same input — React's reconciler stays happy.
 *
 * ADR-289 Phase 2a: rows matching LEGACY_MIRROR_REFRESH_PATTERNS are
 * skipped at the grouping boundary so pre-fix mirror-refresh narrations
 * already on disk don't surface in the Feed.
 */
export function groupFeedMessages(messages: TPMessage[]): FeedUnit[] {
  if (messages.length === 0) return [];

  // Pass 0 — drop legacy mirror-refresh narrations (Phase 2a).
  const filtered = messages.filter((m) => !isLegacyMirrorRefreshRow(m));
  if (filtered.length === 0) return [];

  // Pass 1 — bucket rows by invocation_id (or 'standalone' for no id).
  const groups = new Map<string, TPMessage[]>();
  const standalone: TPMessage[] = [];

  for (const msg of filtered) {
    const id = msg.narrative?.invocationId;
    if (!id) {
      standalone.push(msg);
      continue;
    }
    const bucket = groups.get(id);
    if (bucket) bucket.push(msg);
    else groups.set(id, [msg]);
  }

  // Pass 2 — for each group, decide whether the cycle was operator-
  // addressed. If so, hoist the operator's user row out as its own
  // OperatorEventUnit; the remaining rows form an InvocationCardUnit.
  // If not, the whole group is an InvocationCardUnit and any user rows
  // inside (rare/unexpected) stay in the card.
  const units: FeedUnit[] = [];

  for (const [invocationId, rows] of Array.from(groups.entries())) {
    // Stable in-group ordering by timestamp ascending.
    const sorted = [...rows].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    // Find the operator's user row (if any) — addressed cycles have
    // exactly one; autonomous cycles have zero.
    const userRow = sorted.find((m) => m.role === 'user');
    const isAddressed = Boolean(userRow);

    if (isAddressed && userRow) {
      // Hoist the operator user row out as a standalone marker.
      units.push({
        kind: 'operator-event',
        id: userRow.id,
        message: userRow,
        ledToInvocation: true,
        invocationId,
        timestamp: userRow.timestamp,
      });

      const nonUserRows = sorted.filter((m) => m.id !== userRow.id);
      if (nonUserRows.length > 0) {
        units.push(buildInvocationCard(invocationId, nonUserRows, true));
      }
    } else {
      units.push(buildInvocationCard(invocationId, sorted, false));
    }
  }

  // Pass 3 — emit standalone units for orphan rows. Operator messages
  // with no invocation_id become operator-event markers with
  // ledToInvocation=false. All other roles become standalone-event rows.
  for (const msg of standalone) {
    if (msg.role === 'user') {
      units.push({
        kind: 'operator-event',
        id: msg.id,
        message: msg,
        ledToInvocation: false,
        timestamp: msg.timestamp,
      });
    } else {
      units.push({
        kind: 'standalone-event',
        id: msg.id,
        message: msg,
        timestamp: msg.timestamp,
      });
    }
  }

  // Final chronological sort.
  units.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  return units;
}

function buildInvocationCard(
  invocationId: string,
  rows: TPMessage[],
  isAddressed: boolean,
): InvocationCardUnit {
  // The earliest row drives the card's timestamp.
  const earliest = rows.reduce((acc, m) => (m.timestamp < acc.timestamp ? m : acc), rows[0]);

  // Pulse: prefer the verdict row's pulse, else the first row's pulse,
  // else default to 'reactive' (autonomous cycles always have a pulse).
  const verdict = rows.find((m) => m.role === 'reviewer');
  const pulseFromVerdict = verdict?.narrative?.pulse;
  const pulseFromFirst = rows[0]?.narrative?.pulse;
  const pulse: NarrativePulse = pulseFromVerdict ?? pulseFromFirst ?? 'reactive';

  const actions = rows.filter((m) => m.role !== 'reviewer');

  return {
    kind: 'invocation-card',
    id: invocationId,
    invocationId,
    pulse,
    isAddressed,
    verdict,
    actions,
    timestamp: earliest.timestamp,
  };
}

// ---------------------------------------------------------------------------
// Day separator derivation
// ---------------------------------------------------------------------------

/**
 * Given a chronological list of FeedUnits, return an interleaved list
 * where each unit is preceded by a day-separator sentinel when its
 * day differs from the previous unit's day. Pure function.
 */
export type FeedRow =
  | { kind: 'day-separator'; id: string; date: Date }
  | FeedUnit;

export function interleaveDaySeparators(units: FeedUnit[]): FeedRow[] {
  if (units.length === 0) return [];
  const out: FeedRow[] = [];
  let lastDayKey = '';
  for (const unit of units) {
    const d = unit.timestamp;
    const dayKey = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    if (dayKey !== lastDayKey) {
      out.push({
        kind: 'day-separator',
        id: `day-${dayKey}`,
        date: new Date(d.getFullYear(), d.getMonth(), d.getDate()),
      });
      lastDayKey = dayKey;
    }
    out.push(unit);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Conversation drawer filter
// ---------------------------------------------------------------------------

/**
 * Filter the flat message list to addressed-cycle rows only. Used by
 * the Conversation surface (drawer on /feed; right-panel on /work,
 * /agents, /context, /workspace) — the Conversation renders the chat-
 * shaped exchange between operator and addressee, not the broader
 * operations timeline.
 *
 * Three inclusion paths (any one is sufficient):
 *   1. Role is `user` — operator messages are always conversation.
 *   2. `narrative.pulse === 'addressed'` — explicit pulse tag.
 *   3. `narrative.invocationId` matches the invocation_id of any user
 *      row in the session (defense-in-depth per ADR-289 Phase 2a). If
 *      the operator addressed an invocation cycle, every other row
 *      sharing that invocation_id belongs to the conversation by
 *      construction — even if its own pulse is mis-tagged (e.g.,
 *      pre-Phase-2a Reviewer reply hardcoded pulse='reactive'). The
 *      invocation_id grouping primitive wins over pulse-tag accuracy
 *      because pulse is an emitter-set field that can drift; invocation
 *      grouping is structural.
 *
 * Legacy mirror-refresh narrations are NOT additionally filtered here —
 * groupFeedMessages already handles that at the Feed-surface boundary;
 * mirror-refresh rows on the Conversation surface are rare enough
 * (operator's addressed-cycle Reviewer rarely fires SyncPlatformState
 * within an addressed turn) to leave the rendering to MessageDispatch.
 */
export function filterAddressedMessages(messages: TPMessage[]): TPMessage[] {
  // Pass 1 — collect invocation_ids that have at least one user row.
  // These are the "addressed-cycle" invocation atoms by construction.
  const addressedInvocations = new Set<string>();
  for (const m of messages) {
    if (m.role === 'user' && m.narrative?.invocationId) {
      addressedInvocations.add(m.narrative.invocationId);
    }
  }

  // Pass 2 — filter using the three inclusion paths.
  return messages.filter((m) => {
    if (m.role === 'user') return true;
    if (m.narrative?.pulse === 'addressed') return true;
    const invId = m.narrative?.invocationId;
    if (invId && addressedInvocations.has(invId)) return true;
    return false;
  });
}
