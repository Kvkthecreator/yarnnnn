/**
 * Composition resolver — ADR-225 §4 + Phase 3, amended by ADR-228.
 *
 * Two resolution functions, sharing the 4-tier match semantics:
 *   - resolveMiddle — content-area middle (Phase 2)
 *   - resolveChrome — chrome (metadata + actions) (Phase 3)
 *
 * (resolveCockpitPanes deleted by ADR-228 — the cockpit no longer
 * dispatches a flat pane sequence; see `CockpitRenderer.tsx` for the
 * four-face render.)
 *
 * 4-tier match resolution (most specific first, first match wins within tier):
 *   Tier 1: task_slug exact match
 *   Tier 2: output_kind + condition (e.g., output_kind=external_action AND
 *           condition.emits_proposal=true)
 *   Tier 3: output_kind alone
 *   Tier 4: agent_role / agent_class
 *
 * Per ADR-225 Phase 3: kernel defaults are themselves component
 * declarations registered in `LIBRARY_COMPONENTS`. The resolver doesn't
 * distinguish kernel from bundle; both are dispatched by `kind` through
 * the same renderer.
 */

import type { ChromeDecl, MiddleDecl } from './types';
import { KERNEL_DEFAULT_CHROME } from './kernel-defaults';

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

// ---------------------------------------------------------------------------
// resolveChrome — ADR-225 Phase 3
// ---------------------------------------------------------------------------

/**
 * Resolve chrome (metadata + actions) for a task. Pattern parallels
 * resolveMiddle: try bundle middles first; on a match with a `chrome`
 * field, use that (with kernel-default fall-in for missing parts);
 * otherwise return the kernel default for the task's output_kind.
 *
 * Both `metadata` and `actions` are independently optional on the
 * bundle's ChromeDecl — partial overrides are honored, missing parts
 * inherit from the kernel default.
 */
export function resolveChrome(
  ctx: ResolutionContext,
  middles: MiddleDecl[],
): ChromeDecl {
  const kindKey = ctx.task.output_kind ?? 'produces_deliverable';
  const kernelDefault = KERNEL_DEFAULT_CHROME[kindKey] ?? KERNEL_DEFAULT_CHROME.produces_deliverable;

  const matched = resolveMiddle(ctx, middles);
  if (matched?.chrome) {
    return {
      metadata: matched.chrome.metadata ?? kernelDefault.metadata,
      actions: matched.chrome.actions ?? kernelDefault.actions,
    };
  }
  return kernelDefault;
}

