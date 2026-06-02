/**
 * Composition resolver — ADR-225 §4 + Phase I (post-merge sweep, 2026-05-10).
 *
 * Two resolution functions, sharing the simplified match semantics:
 *   - resolveMiddle — content-area middle (Phase 2)
 *   - resolveChrome — chrome (metadata + actions) (Phase 3)
 *
 * (resolveCockpitPanes deleted by ADR-228 — the Home no longer
 * dispatches a flat pane sequence; see `HomeRenderer.tsx` for the
 * program-section render. Cockpit renamed → Home by ADR-312 D1.)
 *
 * Match resolution (Phase I — collapsed from 4 tiers to 1):
 *   Tier 1: task_slug exact match
 *
 * The legacy Tier 2 (output_kind + condition), Tier 3 (output_kind alone),
 * and Tier 4 (agent_role / agent_class) are deleted per ADR-261 D1's "one
 * execution shape" principle and ADR-262 §6.1's resolution: every
 * recurrence's substrate lives at /workspace/reports/{slug}/{date}/output.md
 * (per CONVENTIONS topology) and renders through the universal middle. A
 * bundle that wants to override the universal middle for a specific
 * recurrence does so by naming its slug in SURFACES.yaml.
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
    [key: string]: unknown; // additional fields for future condition matching
  };
  agent?: {
    role?: string | null;
    class?: string | null;
    agent_class?: string | null;
  } | null;
}

/**
 * Match a task against bundle-supplied middles. Returns the slug-matched
 * middle, or null if no bundle middle applies.
 */
export function resolveMiddle(
  ctx: ResolutionContext,
  middles: MiddleDecl[],
): MiddleDecl | null {
  if (!middles || middles.length === 0) return null;
  for (const m of middles) {
    if (m.match.task_slug && m.match.task_slug === ctx.task.slug) return m;
  }
  return null;
}

// ---------------------------------------------------------------------------
// resolveChrome — ADR-225 Phase 3 + Phase I
// ---------------------------------------------------------------------------

/**
 * Resolve chrome (metadata + actions) for a task. Try bundle middles
 * first; on a slug-match with a `chrome` field, use that (with
 * kernel-default fall-in for missing parts); otherwise return the
 * universal kernel default.
 *
 * Both `metadata` and `actions` are independently optional on the
 * bundle's ChromeDecl — partial overrides are honored, missing parts
 * inherit from the kernel default.
 */
export function resolveChrome(
  ctx: ResolutionContext,
  middles: MiddleDecl[],
): ChromeDecl {
  const matched = resolveMiddle(ctx, middles);
  if (matched?.chrome) {
    return {
      metadata: matched.chrome.metadata ?? KERNEL_DEFAULT_CHROME.metadata,
      actions: matched.chrome.actions ?? KERNEL_DEFAULT_CHROME.actions,
    };
  }
  return KERNEL_DEFAULT_CHROME;
}


/**
 * getProgramSections — ADR-243 Phase B; key renamed by ADR-312 D2.
 *
 * Returns the ordered list of program sections from the active
 * composition when the bundle declares `home.program_sections`.
 * Returns an empty array when the key is absent (the Home renders its
 * constitution-band CTA instead — ADR-312 D6).
 *
 * Sections are sorted ascending by `order` so SURFACES.yaml authoring
 * order doesn't have to match visual order.
 */
export function getProgramSections(
  composition: import('./types').SurfacesResponse,
): Array<{ kind: string; order: number }> {
  const home = composition.composition.tabs?.work?.list?.home as
    | { program_sections?: Array<{ kind: string; order: number }> }
    | undefined;
  const sections = home?.program_sections ?? [];
  return [...sections].sort((a, b) => a.order - b.order);
}
