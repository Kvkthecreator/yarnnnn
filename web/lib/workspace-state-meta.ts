/**
 * Workspace state surface marker parsing — ADR-165 v7.
 *
 * TP emits an HTML comment at the end of an assistant message when it wants
 * the chat client to open the workspace state surface with a specific lead
 * view:
 *
 *   <!-- workspace-state: {"lead":"context","reason":"identity is empty"} -->
 *
 * This module parses that comment (if present), returns the markdown body
 * with the comment stripped, and exposes the parsed directive so the chat
 * surface can react to it. Same pattern as ADR-162's inference-meta marker.
 *
 * The marker is a TP→client directive, not a tool result. TP decides when
 * the surface should open based on workspace_state signals in working memory.
 * The frontend never guesses — it just executes what TP asks for.
 *
 * v7 (2026-04-09): `empty` lead dissolved into `context`. "Add context" is
 * a peer lens alongside briefing/recent/gaps. The gate behavior (cold-start
 * lock) is a property of workspace state (`isEmpty`), not a property of the
 * lens value. TP still emits `lead=context` on the first turn for an empty
 * workspace; the frontend renders it with the switcher hidden because
 * `isEmpty` is true, not because the lens name is special.
 */

export type WorkspaceStateLead =
  | 'context'    // ContextSetup (cold-start capture on empty, peer re-entry otherwise)
  | 'briefing'   // What changed since the user was last here
  | 'recent'     // What's currently running
  | 'gaps';      // Coverage gaps — domain agents without tasks, missing context

export interface WorkspaceStateDirective {
  /** Which view the surface should open in. */
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

const META_COMMENT_RE = /\n*<!--\s*workspace-state:\s*(\{[\s\S]*?\})\s*-->\s*$/;

const VALID_LEADS: ReadonlySet<WorkspaceStateLead> = new Set<WorkspaceStateLead>([
  'context',
  'briefing',
  'recent',
  'gaps',
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

  const match = content.match(META_COMMENT_RE);
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
