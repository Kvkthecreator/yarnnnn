/**
 * Reviewer decisions content shape — `/workspace/review/decisions.md`.
 *
 * Migrated from `web/lib/reviewer-decisions.ts` by ADR-244 Phase 2.
 *
 * Per ADR-244 D5 the WRITE_CONTRACT is `narrative` — Reviewer-layer
 * (`api/services/reviewer_audit.py`) writes append-only decision blocks
 * per ADR-194 v2 Phase 2a; operator never edits through L3. The
 * canonical L3 (DecisionsStream per ADR-241 D3) renders the Stream
 * archetype as read-only.
 *
 * Lifted-from history: `web/lib/reviewer-decisions.ts` (ADR-239) →
 * here (ADR-244 Phase 2).
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-244 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'decisions' as const;
export const PATH_GLOB = '**/review/decisions.md';
export const WRITE_CONTRACT = 'narrative' as const;
export const CANONICAL_L3 = 'DecisionsStream' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Pure parser
// ---------------------------------------------------------------------------

export function parse(content: string): ReviewerDecision[] {
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
  return decisions.reverse();
}

/** Legacy alias — back-compat for `parseDecisions` import name. */
export const parseDecisions = parse;

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

// ---------------------------------------------------------------------------
// Pure formatters
// ---------------------------------------------------------------------------

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

export function identityLabel(identity: string | null | undefined): string {
  if (!identity) return 'Reviewer';
  if (identity.startsWith('human:')) return 'You';
  if (identity.startsWith('ai:')) return 'AI Reviewer';
  if (identity.startsWith('impersonated:')) return 'Admin (impersonated)';
  if (identity === 'reviewer-layer:observed') return 'Reviewer (observing)';
  return identity;
}

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

export interface ReviewerCalibration {
  approves: number;
  rejects: number;
  defers: number;
  total: number;
  lastDecisionAt: Date | null;
  ratio: number | null;
}

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
    if (!calib.lastDecisionAt || ts > calib.lastDecisionAt) {
      calib.lastDecisionAt = ts;
    }
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
