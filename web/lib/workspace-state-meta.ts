/**
 * Workspace state surface marker parsing — ADR-165 v8.
 *
 * `/chat` has TWO structured modals with TWO independent markers:
 *
 *   <!-- workspace-state: {"lead":"overview","reason":"..."} -->   → Overview modal
 *   <!-- onboarding -->                                             → Onboarding modal
 *
 * TP emits at most one of these per message. Both markers are HTML comments
 * appended as the LAST line of an assistant message. The chat client parses
 * both on every new assistant message, opens the matching modal if present,
 * and strips both markers from the rendered message body.
 *
 * v8 (2026-04-09): Onboarding split from workspace-state — they were the
 * same marker in v7 (`lead=context`) but conflated diagnostic with capture.
 * The two modals now have distinct markers, distinct parsers, and distinct
 * lifecycles. Lead enum changed: `context | briefing | recent | gaps` →
 * `overview | flags | recap | activity`. No backwards-compat shim — legacy
 * markers silently no-op on parse.
 *
 * Same parsing approach as ADR-162's inference-meta marker.
 */

// =============================================================================
// Workspace state marker (Overview modal)
// =============================================================================

export type WorkspaceStateLead =
  | 'overview'   // Readiness — workspace capability mirror (identity/brand/team/work/knowledge/platforms)
  | 'flags'      // Attention — gaps + signals TP wants to flag
  | 'recap'      // Last session — cross-session memory (AWARENESS.md, summaries)
  | 'activity';  // Activity — recent runs + coming up

export interface WorkspaceStateDirective {
  /** Which tab the Overview modal should open in. */
  lead: WorkspaceStateLead;
  /** Optional one-liner TP can pass to explain why it opened the surface. */
  reason?: string;
}

export interface ParsedWorkspaceStateContent {
  /** The markdown body with the workspace-state comment stripped. */
  body: string;
  /** Parsed directive, or null if no marker was present. */
  directive: WorkspaceStateDirective | null;
}

const WORKSPACE_STATE_RE = /\n*<!--\s*workspace-state:\s*(\{[\s\S]*?\})\s*-->\s*$/;

const VALID_LEADS: ReadonlySet<WorkspaceStateLead> = new Set<WorkspaceStateLead>([
  'overview',
  'flags',
  'recap',
  'activity',
]);

/**
 * Parse and strip the workspace-state HTML comment from a TP message.
 *
 * Returns the markdown body (comment removed) and the parsed directive.
 * If the content has no marker, `directive` is null and `body` is unchanged.
 */
export function parseWorkspaceStateMeta(
  content: string | null | undefined,
): ParsedWorkspaceStateContent {
  if (!content) return { body: '', directive: null };

  const match = content.match(WORKSPACE_STATE_RE);
  if (!match) {
    return { body: content, directive: null };
  }

  let directive: WorkspaceStateDirective | null = null;
  try {
    const parsed = JSON.parse(match[1]) as WorkspaceStateDirective;
    if (parsed && VALID_LEADS.has(parsed.lead)) {
      directive = parsed;
    }
  } catch {
    directive = null;
  }

  const body = content.slice(0, match.index ?? 0).trimEnd();
  return { body, directive };
}

/**
 * Strip the workspace-state marker from message content for display.
 * Convenience wrapper around parseWorkspaceStateMeta when only the body is
 * needed (e.g., inline render sites in ChatPanel).
 */
export function stripWorkspaceStateMeta(content: string | null | undefined): string {
  return parseWorkspaceStateMeta(content).body;
}

// =============================================================================
// Onboarding marker (Onboarding modal)
// =============================================================================

export interface ParsedOnboardingContent {
  /** The markdown body with the onboarding comment stripped. */
  body: string;
  /** True if an onboarding marker was present. */
  present: boolean;
}

// Matches `<!-- onboarding -->` on its own line at the end of a message.
// The marker carries no JSON payload — its presence alone is the directive.
const ONBOARDING_RE = /\n*<!--\s*onboarding\s*-->\s*$/;

/**
 * Parse and strip the onboarding HTML comment from a TP message.
 *
 * Returns the markdown body (comment removed) and whether the marker was present.
 */
export function parseOnboardingMeta(
  content: string | null | undefined,
): ParsedOnboardingContent {
  if (!content) return { body: '', present: false };

  const match = content.match(ONBOARDING_RE);
  if (!match) {
    return { body: content, present: false };
  }

  const body = content.slice(0, match.index ?? 0).trimEnd();
  return { body, present: true };
}

/**
 * Strip the onboarding marker from message content for display.
 * Convenience wrapper. Chainable with stripWorkspaceStateMeta.
 */
export function stripOnboardingMeta(content: string | null | undefined): string {
  return parseOnboardingMeta(content).body;
}
