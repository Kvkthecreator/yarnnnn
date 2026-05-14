/**
 * Money-truth content shape — `_money_truth.md` + `_money_truth_summary.md`.
 *
 * Per the P&L unification refactor (2026-05-12, supersedes the legacy
 * `performance.ts` shape that parsed flat YAML keys never emitted by the
 * backend). The backend reconciler in `api/services/outcomes/ledger.py`
 * writes JSON frontmatter — this parser reads that JSON shape.
 *
 * Per ADR-245 D5 the WRITE_CONTRACT is `live_aggregate` — only the system
 * outcomes ledger writes; operators never edit through L3. Per ADR-273 D2
 * the canonical L3 reading `_money_truth.md`'s balance/headline portion is
 * `TraderMoneyTruth` (the alpha-trader program component); `TraderExpectancy`
 * consumes the `by_signal` subfield. The legacy kernel `MoneyTruthFace`
 * fallback (which rendered both) was deleted in ADR-273 Phase 2.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'money_truth' as const;
export const PATH_GLOB =
  '**/context/{*/_money_truth.md,_money_truth_summary.md}';
export const WRITE_CONTRACT = 'live_aggregate' as const;
export const CANONICAL_L3 = 'TraderMoneyTruth' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types — match the JSON frontmatter shape `outcomes/ledger.py` writes
// ---------------------------------------------------------------------------

export interface RollingWindow {
  count: number;
  value_cents: number;
  wins: number;
  losses: number;
}

export interface SignalState extends RollingWindow {
  rolling_7d?: RollingWindow;
  rolling_30d?: RollingWindow;
  rolling_90d?: RollingWindow;
}

export interface MoneyTruthMeta {
  domain?: string;
  last_reconciled_at?: string;
  totals?: {
    reconciled_event_count: number;
    aggregate_value_cents: number;
    currency: string;
  };
  by_action_type?: Record<string, RollingWindow>;
  by_signal?: Record<string, SignalState>;
  rolling_7d?: RollingWindow;
  rolling_30d?: RollingWindow;
  rolling_90d?: RollingWindow;
  // Cross-domain summary file (`_money_truth_summary.md`) has a different
  // shape — `generated_at` + `domains` + `aggregate`. Both shapes share
  // these optional fields; consumers branch on presence of `domain` (single)
  // vs `domains` (cross-domain rollup).
  generated_at?: string;
  domains?: Record<string, {
    totals?: {
      reconciled_event_count: number;
      aggregate_value_cents: number;
      currency: string;
    };
    rolling_7d?: RollingWindow;
    rolling_30d?: RollingWindow;
    rolling_90d?: RollingWindow;
    last_reconciled_at?: string;
  }>;
  aggregate?: {
    totals?: {
      reconciled_event_count: number;
      aggregate_value_cents: number;
      currency: string;
      domains_covered?: number;
    };
    rolling_7d?: RollingWindow;
    rolling_30d?: RollingWindow;
    rolling_90d?: RollingWindow;
  };
}

// ---------------------------------------------------------------------------
// Pure parser — JSON frontmatter (ledger.py writes JSON, not YAML)
// ---------------------------------------------------------------------------

export function parse(content: string): MoneyTruthMeta {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return {};
  try {
    const parsed = JSON.parse(fm[1].trim());
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as MoneyTruthMeta;
    }
    return {};
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// Helpers — gross/cost/net derivation
// ---------------------------------------------------------------------------

/**
 * Format cents as a signed dollar string. Positive shows "+$X.XX",
 * negative "-$X.XX", zero "$0.00".
 */
export function formatCents(cents: number | undefined | null): string {
  if (cents === undefined || cents === null) return '$0.00';
  const sign = cents > 0 ? '+' : cents < 0 ? '-' : '';
  const abs = Math.abs(cents) / 100;
  return `${sign}$${abs.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Derive (gross, cost, net) for a rolling window. Cost is not currently
 * tracked in `_money_truth.md` frontmatter (cost-truth integration deferred
 * to follow-on); for now gross == net and cost is undefined. The shape is
 * here so consumers can branch on `cost === undefined` to render "cost not
 * tracked" or hide the cost column until the integration lands.
 */
export interface NetMetrics {
  gross_cents: number;
  cost_cents: number | undefined;
  net_cents: number;
}

export function deriveNetMetrics(window: RollingWindow | undefined): NetMetrics {
  const gross = window?.value_cents ?? 0;
  return {
    gross_cents: gross,
    cost_cents: undefined,
    net_cents: gross,
  };
}

/**
 * Win rate as a 0..1 float, or undefined if window is empty.
 */
export function winRate(window: RollingWindow | undefined): number | undefined {
  if (!window || window.count === 0) return undefined;
  const decided = window.wins + window.losses;
  if (decided === 0) return undefined;
  return window.wins / decided;
}

/**
 * Get per-signal entries sorted by absolute value_cents desc (biggest
 * contributors first). Empty array if by_signal is absent.
 */
export function signalEntries(
  meta: MoneyTruthMeta,
): Array<[string, SignalState]> {
  const bySignal = meta.by_signal ?? {};
  return Object.entries(bySignal).sort(
    ([, a], [, b]) =>
      Math.abs(b.value_cents ?? 0) - Math.abs(a.value_cents ?? 0),
  );
}
