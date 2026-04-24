/**
 * Reviewer decisions parser — shared across `/agents?agent=reviewer`
 * (DecisionsStreamPane) and the Snapshot overlay on /chat (Recent tab).
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
