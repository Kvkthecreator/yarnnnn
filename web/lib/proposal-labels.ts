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
 */

export interface ProposalLike {
  primitive: string;
  family?: 'capital' | 'substrate' | string;
  decision_context?: Record<string, unknown> | null;
}

// Known primitives → the operator verb phrase. Merged from the two
// pre-consolidation maps; extend here, never inline at a call site.
const PRIMITIVE_LABELS: Record<string, string> = {
  WriteFile: 'Save a workspace change',
  EditFile: 'Edit a workspace file',
  DeleteFile: 'Delete a workspace file',
  MoveFile: 'Move a workspace file',
  Schedule: 'Change a schedule',
  ManageRecurrence: 'Change a schedule',
  FireInvocation: 'Run a task now',
  RuntimeDispatch: 'Generate an asset',
  InferContext: 'Update your context',
  // Capital platform tools — the highest-consequence rows get explicit
  // verb phrases rather than de-jargoned fallbacks.
  platform_trading_submit_order: 'Submit a trade order',
  platform_trading_cancel_order: 'Cancel a trade order',
  platform_commerce_create_product: 'Create a product',
  platform_commerce_update_product: 'Update a product',
  platform_commerce_create_discount: 'Create a discount',
};

const cap = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** Operator-language label for a gated action. */
export function proposalActionLabel(p: ProposalLike): string {
  if (p.family === 'substrate') {
    const dc = (p.decision_context ?? {}) as Record<string, unknown>;
    const path = (dc.path as string) ?? ((dc.diff as { path?: string } | undefined)?.path) ?? '';
    const verb = PRIMITIVE_LABELS[p.primitive] ?? 'Save a workspace change';
    return path ? `${verb} · ${path}` : verb;
  }
  if (PRIMITIVE_LABELS[p.primitive]) return PRIMITIVE_LABELS[p.primitive];
  // Unknown platform tool: "{Provider} · {De-jargoned tool}"
  if (p.primitive.startsWith('platform_')) {
    const [provider, ...rest] = p.primitive.replace(/^platform_/, '').split('_');
    const tool = rest.join(' ');
    return tool ? `${cap(provider)} · ${cap(tool)}` : cap(provider);
  }
  // Unknown kernel primitive: de-camel-cased title case.
  const base = p.primitive.includes('_')
    ? p.primitive.replace(/_/g, ' ')
    : p.primitive.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
  return cap(base);
}
