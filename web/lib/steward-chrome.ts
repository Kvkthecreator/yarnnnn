/**
 * The steward chrome gate — ADR-454 D3 (2026-07-13, the ambient steward).
 *
 * Gates the system agent's PERSONA CHROME (the "Ask Freddie" FAB + the
 * ChatDrawer rail), NOT the steward function. Freddie keeps waking,
 * deriving, placing, and arbitrating; its presence in the experience is
 * the attributed ledger rows (ADR-410 actor-first), not fronted chat.
 * Deliberately distinct from the backend `AGENT_ENABLED` gate (ADR-375
 * §6), which turns the steward FUNCTION off.
 *
 * Hide-not-delete (the CONNECTOR_CAPTURE_ENABLED posture): the drawer
 * body, NarrativeContext, the A1 thread machinery, and the addressed-wake
 * backend path all stay intact. Flipping this one const re-lights the
 * chrome.
 */
export const STEWARD_CHROME_ENABLED = false;
