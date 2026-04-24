/**
 * Workspace state surface marker parsing — ADR-165 v8, ADR-215 Phase 5.
 *
 * `/chat` has ONE structured modal driven by a YARNNN-emitted marker:
 *
 *   <!-- workspace-state: {"lead":"overview","reason":"..."} -->   → Overview modal
 *
 * The onboarding marker (`<!-- onboarding -->`) was retired by ADR-190
 * (onboarding became conversational) and its corresponding modal was
 * deleted by ADR-215 Phase 5. Only `stripOnboardingMeta` remains, for
 * display hygiene on historical messages that may still carry the marker.
 *
 * The workspace-state marker is an HTML comment appended as the LAST line
 * of an assistant message. The chat client parses every new assistant
 * message, opens the Overview modal if a directive is present, and strips
 * both markers from the rendered body.
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
// Onboarding marker — retired emission (ADR-190 + ADR-215 Phase 5)
// =============================================================================
//
// YARNNN no longer emits `<!-- onboarding -->` — onboarding became
// conversational in ADR-190. The corresponding OnboardingModal was deleted
// in ADR-215 Phase 5 (violated R2 for updates / R3 for substrate).
//
// `stripOnboardingMeta` remains for display hygiene: historical messages in
// older sessions may still carry the marker, and chat rendering should
// scrub it from the rendered body regardless.

// Matches `<!-- onboarding -->` on its own line at the end of a message.
const ONBOARDING_RE = /\n*<!--\s*onboarding\s*-->\s*$/;

export function stripOnboardingMeta(content: string | null | undefined): string {
  if (!content) return '';
  const match = content.match(ONBOARDING_RE);
  if (!match) return content;
  return content.slice(0, match.index ?? 0).trimEnd();
}
