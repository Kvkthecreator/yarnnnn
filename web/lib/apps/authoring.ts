/**
 * Authoring apps — the residency declaration (ADR-467 D1).
 *
 * An authoring app (the ADR-440 class — Studio today, IMAGES when ADR-468
 * builds) declares the RESIDENT agent its bound lane carries by default. This
 * is the one-directional coupling ratified by ADR-467: the app pins the
 * colleague; the colleague is never confined to the app (chat with Designer
 * anywhere, hire your own based on it — ADR-440 D3 + the `bound_only`
 * removal both stand).
 *
 * Residency is a creation-time default made legible — the lane row persists
 * the agent, the lane stays the mind. This table replaces the hardcoded
 * `agent: 'designer'` strings that lived at the create sites: the fact now
 * has one declared home instead of N string literals.
 *
 * The kernel roster itself has NO residency column — the open surface (chat)
 * offers the cast with no default (ADR-467 D2), so residency is an app-layer
 * fact, declared beside the apps, not on the agents.
 */

export interface AuthoringAppRegistration {
  id: string;
  /** The kernel agent slug this app's bound lane carries by default. */
  resident: string;
}

export const AUTHORING_APPS: Record<string, AuthoringAppRegistration> = {
  studio: { id: 'studio', resident: 'designer' },
  // IMAGES (ADR-468) adds its row when it ships: { id: 'images', resident: 'designer' }
};
