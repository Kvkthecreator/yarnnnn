/**
 * proposal-labels — the SINGLE operator-language labeler for gated
 * actions (ADR-340 P4, Stage-1 eval finding F3).
 *
 * The Stage-1 legibility evaluation found proposal rows rendering the
 * primitive slug ("platform_trading_submit_order · capital ·
 * trade-proposal") at the exact moment of highest consequence — the
 * operator's concept is "a trade wants my approval." It also found TWO
 * parallel label implementations (KernelDecisionQueue.actionLabel +
 * ProposalCard.formatProposalLabel). This module consolidates both per
 * Singular Implementation; all proposal-rendering sites (Home decision
 * slot, chat ProposalCard, AttentionCenter) import from here.
 *
 * Label shapes (ADR-307 family-shaped rendering):
 *   substrate → "Save a change · {path}"   (the diff is the content;
 *               the path is the operator-meaningful identifier)
 *   capital   → known-primitive verb phrase ("Submit a trade order"),
 *               falling back to "{Provider} · {de-jargoned tool}"
 *   kernel    → known-primitive verb phrase ("Run a task now", …)
 *
 * ⭐ ADR-660 — this module is evaluated at import, before any member's
 * language is known, so it holds no words: it resolves a proposal to a
 * catalog KEY (plus its arguments) and the COMPONENT words it, through
 * `useProposalLabels` below. A fallback derived from an unknown primitive
 * (a newer roster) carries no catalog entry and rides as `fallback`.
 */

import { useTranslations } from 'next-intl';
import { useAuthorLabel } from '@/lib/workspace/useAuthorLabel';

/** The catalog namespace the label keys below live under. */
export const PROPOSAL_LABEL_NS = 'supervisor.proposalLabel';

export interface ProposalLike {
  primitive: string;
  family?: 'capital' | 'external-write' | 'substrate' | string;
  decision_context?: Record<string, unknown> | null;
}

/**
 * A label the caller words. `key` names a catalog entry under
 * PROPOSAL_LABEL_NS; `fallback` is an already-humanized spelling for a
 * primitive the catalog does not name. `path` rides along when the row is a
 * substrate write (the whole sentence is the catalog's `withPath`, never a
 * concatenation).
 */
export interface ProposalLabelRef {
  key?: string;
  fallback?: string;
  path?: string;
}

/** Known primitives the catalog names. Extend here, never at a call site. */
const KNOWN_PRIMITIVES: readonly string[] = [
  'WriteFile',
  'EditFile',
  'DeleteFile',
  'MoveFile',
  'Schedule',
  'ManageRecurrence',
  'FireInvocation',
  // Capital platform tools — the highest-consequence rows get explicit
  // verb phrases rather than de-jargoned fallbacks.
  'platform_trading_submit_order',
  'platform_trading_cancel_order',
  'platform_commerce_create_product',
  'platform_commerce_update_product',
  'platform_commerce_create_discount',
  // External-write audience sends (ADR-307 2026-06-19 / ADR-304 amendment).
  'platform_slack_send_to_channel',
  'platform_notion_create_page',
  'platform_notion_append_block',
  'platform_email_send',
  'platform_email_send_bulk',
];

const cap = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** Resolve a gated action to a catalog key (+ args). Words nothing itself. */
export function proposalActionLabelRef(p: ProposalLike): ProposalLabelRef {
  if (p.family === 'substrate') {
    const dc = (p.decision_context ?? {}) as Record<string, unknown>;
    const path = (dc.path as string) ?? ((dc.diff as { path?: string } | undefined)?.path) ?? '';
    const key = KNOWN_PRIMITIVES.includes(p.primitive) ? p.primitive : 'substrateDefault';
    return path ? { key, path } : { key };
  }
  if (KNOWN_PRIMITIVES.includes(p.primitive)) return { key: p.primitive };
  // Unknown platform tool: "{Provider} · {De-jargoned tool}"
  if (p.primitive.startsWith('platform_')) {
    const [provider, ...rest] = p.primitive.replace(/^platform_/, '').split('_');
    const tool = rest.join(' ');
    return { fallback: tool ? `${cap(provider)} · ${cap(tool)}` : cap(provider) };
  }
  // Unknown kernel primitive: de-camel-cased title case.
  const base = p.primitive.includes('_')
    ? p.primitive.replace(/_/g, ' ')
    : p.primitive.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
  return { fallback: cap(base) };
}

/**
 * ADR-408 D5.2 — act-vs-agent disambiguation. A pending proposal queued by an
 * agent is queued by that agent's WITNESS DIAL (ADR-405: autonomy = witness
 * timing), not by a permission failure. True when the proposal's `source` IS
 * an agent act (operator/system-sourced rows carry no dial story).
 */
export function isAgentQueued(source: string | null | undefined): boolean {
  if (!source) return false;
  return (
    source.startsWith('freddie:') ||
    source.startsWith('reviewer:') ||
    source.startsWith('agent:')
  );
}

/**
 * The ONE hook that words a proposal label. Every mount (chat ProposalCard,
 * the To-do queue, AttentionCenter) calls this rather than spelling a verb.
 */
export function useProposalLabels() {
  const t = useTranslations(PROPOSAL_LABEL_NS);
  // The agent label routes through the shared attribution vocabulary — never
  // a parallel actor-label map.
  const { authorLabelOrSystem } = useAuthorLabel();

  /** A gated action's operator-language label. */
  const actionLabel = (p: ProposalLike): string => {
    const ref = proposalActionLabelRef(p);
    const verb = ref.key === undefined ? (ref.fallback ?? '') : t(ref.key);
    return ref.path ? t('withPath', { verb, path: ref.path }) : verb;
  };

  /** The witness-dial line, or null when the row carries no dial story. */
  const queuedByDialLine = (source: string | null | undefined): string | null =>
    isAgentQueued(source) ? t('queuedByDial', { who: authorLabelOrSystem(source) }) : null;

  return { actionLabel, queuedByDialLine };
}
