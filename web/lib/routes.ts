// Cockpit nav per ADR-205 Phase 4 F1 (chat-first landing) + ADR-214 (four-tab
// consolidation, 2026-04-23).
// See docs/adr/ADR-214-agents-page-consolidation.md and
// docs/adr/ADR-198-surface-archetypes.md for surface archetypes.
//
// HOME_ROUTE = /chat. A brand-new workspace has no authored agents and no
// authored tasks — the user's first meaningful action is conversational.
// Landing on /chat re-aligns with ADR-189's authored-team moat.
//
// Current nav (ADR-214): Chat | Work | Agents | Files
// /review deleted; Reviewer lives at /agents?agent=reviewer.
// /team retains a redirect stub for bookmark symmetry (ADR-201 reversed).
// /overview is a redirect stub (ADR-205 F2 merged its Briefing content into
// /work as BriefingStrip).
export const HOME_ROUTE = "/chat";
export const HOME_LABEL = "Chat";
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const AGENTS_ROUTE = "/agents"; // ADR-214 — canonical (reverses ADR-201 /team rename).
export const CONTEXT_ROUTE = "/context";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
