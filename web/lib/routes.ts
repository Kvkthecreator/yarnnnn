// Cockpit nav per ADR-205 Phase 4 F1 (chat-first landing).
// See docs/adr/ADR-205-primitive-collapse.md §Frontend Phase 4+5 and
// docs/adr/ADR-198-surface-archetypes.md for surface archetypes.
//
// HOME_ROUTE = /chat. ADR-205 dissolves most of what /overview surfaced
// (pre-scaffolded roster intelligence). A brand-new workspace has no
// authored agents and no authored tasks — the user's first meaningful
// action is conversational. Landing on /chat re-aligns with ADR-189's
// authored-team moat and matches how users actually validate work.
//
// Current nav (post-ADR-205 F1): Chat | Work | Context | Team | Review
// /overview remains reachable by direct URL until ADR-205 F2 merges its
// Briefing content into /work (BriefingStrip component) and deletes the route.
// Legacy /agents redirects to /team per ADR-201 migration bridge.
export const HOME_ROUTE = "/chat";
export const HOME_LABEL = "Chat";
export const OVERVIEW_ROUTE = "/overview"; // deprecated — ADR-205 F2 will delete
export const CHAT_ROUTE = "/chat";
export const WORK_ROUTE = "/work";
export const TEAM_ROUTE = "/team"; // Renamed from AGENTS_ROUTE by ADR-201.
export const CONTEXT_ROUTE = "/context";
export const REVIEW_ROUTE = "/review";

export function isHomeRoute(pathname: string): boolean {
  return pathname === HOME_ROUTE || pathname.startsWith(`${HOME_ROUTE}/`);
}
