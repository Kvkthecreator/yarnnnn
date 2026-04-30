/**
 * Reviewer decisions parser — canonical FE parser for the verdict log.
 *
 * Consumers (post-ADR-241):
 *   - DecisionsStream (web/components/work/details/DecisionsStream.tsx)
 *     — full Stream archetype on /work
 *   - PerformanceFace calibration aggregate (via aggregateReviewerCalibration)
 *
 * Pre-ADR-241 the Stream consumer lived at
 * web/components/agents/reviewer/DecisionsStreamPane.tsx; that surface
 * collapsed into TP per ADR-241 D3 and the consumer relocated.
 *
 * Decisions live in `/workspace/review/decisions.md` as append-only blocks
 * per ADR-194 v2 Phase 2a:
 *
 *   --- decision ---
 *   timestamp: <iso>
 *   reviewer_identity: human:<uuid> | ai:reviewer-sonnet-v1 | reviewer-layer:observed | …
 *   decision: approve | reject | defer
 *   action_type: <e.g., trading.submit_bracket_order>
 *   proposal_id: <uuid>
 *   reasoning: <multi-line>
 *
 * Tolerant parser — missing fields become null; malformed blocks are
 * skipped silently. Never throws.
 */

export type DecisionVerdict = 'approve' | 'reject' | 'defer';
export type IdentityKind = 'human' | 'ai' | 'impersonated' | 'observed' | 'unknown';

export interface ReviewerDecision {
  raw: string;
  timestamp: string | null;
  identity: string | null;
  identityKind: IdentityKind;
  decision: DecisionVerdict | null;
  actionType: string | null;
  proposalId: string | null;
  reasoning: string | null;
}

export function parseDecisions(content: string): ReviewerDecision[] {
  if (!content) return [];
  const blocks = content.split(/\n?---\s*decision\s*---\n/i).filter(Boolean);
  const decisions: ReviewerDecision[] = [];
  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const timestamp = extractField(trimmed, 'timestamp');
    const identity = extractField(trimmed, 'reviewer_identity');
    const decision = (extractField(trimmed, 'decision') ?? '').toLowerCase();
    const actionType = extractField(trimmed, 'action_type');
    const proposalId = extractField(trimmed, 'proposal_id');
    const reasoning = extractReasoning(trimmed);
    decisions.push({
      raw: trimmed,
      timestamp,
      identity,
      identityKind: classifyIdentity(identity),
      decision:
        decision === 'approve' || decision === 'reject' || decision === 'defer'
          ? (decision as DecisionVerdict)
          : null,
      actionType,
      proposalId,
      reasoning,
    });
  }
  // Newest at top — append-only log means later lines = newer entries.
  return decisions.reverse();
}

function extractField(block: string, key: string): string | null {
  const re = new RegExp(`^\\s*${key}:\\s*(.+?)\\s*$`, 'm');
  const m = block.match(re);
  return m ? m[1].trim() : null;
}

function extractReasoning(block: string): string | null {
  const m = block.match(/reasoning:\s*([\s\S]+)$/i);
  if (!m) return null;
  return m[1].trim();
}

function classifyIdentity(identity: string | null): IdentityKind {
  if (!identity) return 'unknown';
  if (identity.startsWith('human:')) return 'human';
  if (identity.startsWith('ai:')) return 'ai';
  if (identity.startsWith('impersonated:')) return 'impersonated';
  if (identity.startsWith('reviewer-layer:')) return 'observed';
  return 'unknown';
}

/** Short action label, e.g. "trading.submit_bracket_order" → "Trading · Submit bracket order". */
export function formatActionType(action: string | null | undefined): string {
  if (!action) return '—';
  const [provider, ...rest] = action.split('.');
  if (!provider || rest.length === 0) return action;
  const tool = rest.join('.').replace(/_/g, ' ');
  return `${capitalize(provider)} · ${capitalize(tool)}`;
}

function capitalize(s: string): string {
  return s.length > 0 ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

/** Human-readable identity label. */
export function identityLabel(identity: string | null | undefined): string {
  if (!identity) return 'Reviewer';
  if (identity.startsWith('human:')) return 'You';
  if (identity.startsWith('ai:')) return 'AI Reviewer';
  if (identity.startsWith('impersonated:')) return 'Admin (impersonated)';
  if (identity === 'reviewer-layer:observed') return 'Reviewer (observing)';
  return identity;
}

/** Relative-time label, e.g. "3m ago", "2h ago", "yesterday". */
export function formatRelativeTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return 'yesterday';
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString();
}

// ---------------------------------------------------------------------------
// Reviewer calibration aggregate (ADR-239)
// ---------------------------------------------------------------------------
//
// Per ADR-239 D1+D2: PerformanceFace's previous inline parseDecisions
// returned this shape directly from raw markdown. The new layering is:
//   parseDecisions(content) → ReviewerDecision[]  (canonical parser)
//   aggregateReviewerCalibration(decisions) → ReviewerCalibration
//
// Pure transformation. No I/O, no React. Composes with parseDecisions
// at call sites:
//   const calib = aggregateReviewerCalibration(parseDecisions(content));
//
// Note: ADR-239's drafting found that PerformanceFace's inline parser
// was looking for a stale format (`## YYYY-MM-DDTHH... — action` headings
// + `verdict:` field) that the canonical writer
// (`api/services/reviewer_audit.py` per ADR-194 v2 Phase 2a) never
// produces. The canonical write format is `--- decision ---` blocks
// with `decision:` field. PerformanceFace's calibration display has
// been quietly rendering empty/zero state for that reason. ADR-239
// fixes the bug by routing aggregation through the canonical parser.

export interface ReviewerCalibration {
  /** Counts within the 7-day rolling window. */
  approves: number;
  rejects: number;
  defers: number;
  /** Total within the 7-day rolling window. */
  total: number;
  /** Most recent decision timestamp regardless of window. Null if no decisions parseable. */
  lastDecisionAt: Date | null;
  /** Approves / total within the window. Null when total is 0. */
  ratio: number | null;
}

/**
 * Aggregate a parsed decisions list into a 7-day rolling-window calibration.
 * Mirrors the prior PerformanceFace inline aggregation intent — counts +
 * approval ratio over the last 7 days + most-recent decision timestamp
 * across the full list.
 */
export function aggregateReviewerCalibration(
  decisions: ReviewerDecision[],
): ReviewerCalibration {
  const calib: ReviewerCalibration = {
    approves: 0,
    rejects: 0,
    defers: 0,
    total: 0,
    lastDecisionAt: null,
    ratio: null,
  };
  const cutoff = Date.now() - 7 * 24 * 3600 * 1000;
  for (const d of decisions) {
    if (!d.timestamp || !d.decision) continue;
    const ts = new Date(d.timestamp);
    if (Number.isNaN(ts.getTime())) continue;
    // Track most-recent timestamp regardless of window.
    if (!calib.lastDecisionAt || ts > calib.lastDecisionAt) {
      calib.lastDecisionAt = ts;
    }
    // Skip out-of-window entries for the count totals.
    if (ts.getTime() < cutoff) continue;
    if (d.decision === 'approve') calib.approves += 1;
    if (d.decision === 'reject') calib.rejects += 1;
    if (d.decision === 'defer') calib.defers += 1;
    calib.total += 1;
  }
  if (calib.total > 0) {
    calib.ratio = calib.approves / calib.total;
  }
  return calib;
}
