/**
 * Composition resolver — ADR-225 §4.
 *
 * 4-tier match resolution (most specific first, first match wins within tier):
 *   Tier 1: task_slug exact match
 *   Tier 2: output_kind + condition (e.g., output_kind=external_action AND
 *           condition.emits_proposal=true)
 *   Tier 3: output_kind alone
 *   Tier 4: agent_role / agent_class
 *
 * No match → null. Caller falls through to kernel-default rendering
 * (the existing kind-aware middles continue to render, per Phase 2's
 * implementation refinement: kernel-defaults stay where they are; bundle
 * middles override).
 */

import type { MiddleDecl } from './types';

export interface ResolutionContext {
  task: {
    slug: string;
    output_kind?: string | null;
    [key: string]: unknown; // additional fields used by condition matching
  };
  agent?: {
    role?: string | null;
    class?: string | null;
    agent_class?: string | null;
  } | null;
}

/**
 * Match a task against bundle-supplied middles. Returns the highest-
 * specificity match, or null if no bundle middle applies.
 */
export function resolveMiddle(
  ctx: ResolutionContext,
  middles: MiddleDecl[],
): MiddleDecl | null {
  if (!middles || middles.length === 0) return null;

  // Tier 1: task_slug
  for (const m of middles) {
    if (m.match.task_slug && m.match.task_slug === ctx.task.slug) return m;
  }
  // Tier 2: output_kind + condition
  for (const m of middles) {
    if (
      m.match.output_kind &&
      m.match.output_kind === ctx.task.output_kind &&
      m.match.condition &&
      Object.keys(m.match.condition).length > 0
    ) {
      if (matchCondition(ctx.task, m.match.condition)) return m;
    }
  }
  // Tier 3: output_kind alone
  for (const m of middles) {
    if (
      m.match.output_kind &&
      m.match.output_kind === ctx.task.output_kind &&
      (!m.match.condition || Object.keys(m.match.condition).length === 0)
    ) {
      return m;
    }
  }
  // Tier 4: agent_role / agent_class
  for (const m of middles) {
    if (m.match.agent_role && ctx.agent?.role === m.match.agent_role) return m;
    const cls = ctx.agent?.class ?? ctx.agent?.agent_class;
    if (m.match.agent_class && cls === m.match.agent_class) return m;
  }

  return null;
}

/**
 * Check whether a task's fields satisfy the condition map. Each condition
 * key maps to an expected value; the task must have that value for ALL
 * keys to match. Missing keys count as non-matches.
 */
function matchCondition(
  task: ResolutionContext['task'],
  condition: Record<string, unknown>,
): boolean {
  for (const [key, expected] of Object.entries(condition)) {
    if (task[key] !== expected) return false;
  }
  return true;
}
