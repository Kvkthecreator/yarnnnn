/**
 * Snapshot overlay marker parsing — ADR-215 Phase 6.
 *
 * `/chat` has ONE structured overlay driven by a YARNNN-emitted marker:
 *
 *   <!-- snapshot: {"lead":"mandate|review|recent","reason":"..."} -->   → Snapshot modal
 *
 * The marker is an HTML comment appended as the LAST line of an assistant
 * message. The chat client parses every new assistant message, opens the
 * Snapshot overlay on the named tab if present, and strips the marker
 * from the rendered body.
 *
 * History:
 *   - ADR-215 Phase 5 retired the `<!-- onboarding -->` marker (onboarding
 *     became conversational per ADR-190). `stripOnboardingMeta` retained
 *     for display hygiene on historical messages.
 *   - ADR-215 Phase 6 renamed the workspace-state marker → snapshot, with
 *     a new lead enum (mandate|review|recent) reflecting the three-tab
 *     reframe of the overlay.
 *
 * Same parsing approach as ADR-162's inference-meta marker.
 */

// =============================================================================
// Snapshot marker (Snapshot overlay)
// =============================================================================

export type SnapshotLead =
  | 'mandate'  // Primary-Action declaration — what the operator has committed to.
  | 'review'   // Review standard — Reviewer principles + recent verdicts.
  | 'recent';  // Recent — pending proposals + last runs + cross-session note.

export interface SnapshotDirective {
  /** Which tab the Snapshot overlay should open in. */
  lead: SnapshotLead;
  /** Optional one-liner YARNNN can pass to explain why it opened the overlay. */
  reason?: string;
}

export interface ParsedSnapshotContent {
  /** The markdown body with the snapshot comment stripped. */
  body: string;
  /** Parsed directive, or null if no marker was present. */
  directive: SnapshotDirective | null;
}

const SNAPSHOT_RE = /\n*<!--\s*snapshot:\s*(\{[\s\S]*?\})\s*-->\s*$/;

const VALID_LEADS: ReadonlySet<SnapshotLead> = new Set<SnapshotLead>([
  'mandate',
  'review',
  'recent',
]);

/**
 * Parse and strip the snapshot HTML comment from a YARNNN message.
 *
 * Returns the markdown body (comment removed) and the parsed directive.
 * If the content has no marker, `directive` is null and `body` is unchanged.
 */
export function parseSnapshotMeta(
  content: string | null | undefined,
): ParsedSnapshotContent {
  if (!content) return { body: '', directive: null };

  const match = content.match(SNAPSHOT_RE);
  if (!match) {
    return { body: content, directive: null };
  }

  let directive: SnapshotDirective | null = null;
  try {
    const parsed = JSON.parse(match[1]) as SnapshotDirective;
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
 * Strip the snapshot marker from message content for display.
 * Convenience wrapper when only the body is needed (e.g., inline render
 * sites in ChatPanel).
 */
export function stripSnapshotMeta(content: string | null | undefined): string {
  return parseSnapshotMeta(content).body;
}

// =============================================================================
// Onboarding marker — retired emission (ADR-190 + ADR-215 Phase 5)
// =============================================================================
//
// YARNNN no longer emits `<!-- onboarding -->` — onboarding became
// conversational in ADR-190. The corresponding OnboardingModal was deleted
// in ADR-215 Phase 5 (violated R2 for updates / R3 for substrate).
//
// `stripOnboardingMeta` remains for display hygiene: historical messages
// in older sessions may still carry the marker, and chat rendering should
// scrub it from the rendered body regardless.

const ONBOARDING_RE = /\n*<!--\s*onboarding\s*-->\s*$/;

export function stripOnboardingMeta(content: string | null | undefined): string {
  if (!content) return '';
  const match = content.match(ONBOARDING_RE);
  if (!match) return content;
  return content.slice(0, match.index ?? 0).trimEnd();
}
